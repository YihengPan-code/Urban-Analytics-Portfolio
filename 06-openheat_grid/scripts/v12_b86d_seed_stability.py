"""Run B8.6d seed stability for the selected two-stage workflow.

Inputs:
    - b86d_two_stage_dataset.csv
    - b86d_feature_set_registry.csv
    - b86d_combined_pipeline_metrics.csv
Outputs:
    - b86d_seed_stability_metrics.csv
Saved metrics:
    Mean/std/min/max over configured seeds for neutral accuracy, false
    promotion rate, Spearman, top10pct overlap, anchor MAE, and split-specific
    spatial/typology/cell-group metrics.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86d_common import CLAIM_BOUNDARY, DEFAULT_CONFIG, load_config, output_path, read_csv, write_csv
from v12_b86d_stage1_classifier import stage1_for_config
from v12_b86d_stage2_regressor import stage2_for_config
from v12_b86d_two_stage_pipeline import combine_predictions, combined_metric_rows, select_best_pipeline


@dataclass(frozen=True)
class SeedStabilityResult:
    """Seed stability result."""

    status: str
    rows: int
    selected_classifier: str
    selected_regressor: str


def selected_combo(config: dict[str, Any]) -> dict[str, Any]:
    """Select the primary-threshold combo from combined metrics."""
    metrics = read_csv(output_path(config, "combined_pipeline_metrics"))
    return select_best_pipeline(metrics, config)


def summarize_seed_metrics(seed_metrics: pd.DataFrame, best: dict[str, Any]) -> pd.DataFrame:
    """Summarize per-seed metrics into mean/std/min/max rows."""
    metric_map = {
        "neutral_accuracy": "accuracy",
        "false_promotion_rate": "false_promotion_rate",
        "Spearman": "Spearman_observed_vs_predicted",
        "top10pct_overlap": "top10pct_overlap",
        "anchor_MAE": "robust_anchor_MAE",
    }
    rows: list[dict[str, Any]] = []
    for split_family in ["overall", "cell_group_holdout", "spatial_holdout", "typology_holdout", "hour_holdout", "forcing_day_holdout"]:
        subset = seed_metrics if split_family == "overall" else seed_metrics.loc[seed_metrics["split_family"] == split_family]
        if subset.empty:
            continue
        per_seed = subset.groupby("seed", dropna=False).agg({source: "mean" for source in metric_map.values()}).reset_index()
        for metric_name, source in metric_map.items():
            values = pd.to_numeric(per_seed[source], errors="coerce").dropna()
            rows.append(
                {
                    "split_family": split_family,
                    "metric": metric_name,
                    "mean": float(values.mean()) if not values.empty else float("nan"),
                    "std": float(values.std(ddof=0)) if not values.empty else float("nan"),
                    "min": float(values.min()) if not values.empty else float("nan"),
                    "max": float(values.max()) if not values.empty else float("nan"),
                    "n_seeds": int(values.count()),
                    "selected_feature_set": best["feature_set"],
                    "selected_threshold_c": best["neutral_threshold_c"],
                    "selected_classifier": best["classifier"],
                    "selected_regressor": best["regressor"],
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> SeedStabilityResult:
    """Run seed stability for the selected workflow."""
    config = load_config(config_path)
    dataset = read_csv(output_path(config, "two_stage_dataset"))
    registry = read_csv(output_path(config, "feature_set_registry"))
    best = selected_combo(config)
    primary = config["targets"]["primary_target"]
    threshold = float(best["neutral_threshold_c"])
    seed_frames: list[pd.DataFrame] = []
    for seed in config["seed_stability_seeds"]:
        stage1_metrics, stage1_pred = stage1_for_config(
            dataset,
            registry,
            config,
            thresholds=[threshold],
            model_names=[str(best["classifier"])],
            feature_sets=[str(best["feature_set"])],
            seed=int(seed),
        )
        stage2_metrics, stage2_pred = stage2_for_config(
            dataset,
            registry,
            config,
            target=primary,
            thresholds=[threshold],
            model_names=[str(best["regressor"])],
            feature_sets=[str(best["feature_set"])],
            seed=int(seed),
        )
        if stage1_metrics.empty or stage2_metrics.empty or stage1_pred.empty or stage2_pred.empty:
            continue
        combined_pred = combine_predictions(stage1_pred, stage2_pred, primary)
        combined_metrics = combined_metric_rows(combined_pred, config)
        seed_frames.append(combined_metrics)
    all_seed_metrics = pd.concat(seed_frames, ignore_index=True) if seed_frames else pd.DataFrame()
    summary = summarize_seed_metrics(all_seed_metrics, best) if not all_seed_metrics.empty else pd.DataFrame()
    write_csv(summary, output_path(config, "seed_stability_metrics"))
    return SeedStabilityResult("B86D_SEED_STABILITY_READY", len(summary), str(best["classifier"]), str(best["regressor"]))


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run B8.6d seed stability for the selected two-stage workflow.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
