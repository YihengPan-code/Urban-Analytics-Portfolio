"""Run B8.6g2 feature-family ablation diagnostics.

Inputs:
    b86g2_modeling_dataset.csv, b86g2_feature_set_registry.csv,
    b86g2_combined_pipeline_metrics.csv, and B8.6g feature schema.
Outputs:
    b86g2_feature_ablation_metrics.csv and
    b86g2_proxy_vs_vector_feature_comparison.csv.
Saved metrics:
    Family drop-one deltas for spatial holdout, neutral false-promotion,
    anchor underprediction, and top-k support; plus proxy/vector compact
    feature-set comparison under blocked validation families.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86g2_common import (
    CLAIM_BOUNDARY,
    COMBO_COLS,
    DEFAULT_CONFIG,
    WEAK_SPLITS,
    b86g_feature_schema,
    feature_columns_for_set,
    load_config,
    metric_group_summary,
    output_path,
    read_csv,
    selected_two_stage_combo,
    write_csv,
)
from v12_b86g2_two_stage_models import evaluate_two_stage_with_features


@dataclass(frozen=True)
class AblationResult:
    """Ablation result."""

    status: str
    ablation_rows: int
    comparison_rows: int


ABLATION_FAMILIES = {
    "pedestrian_shade": "pedestrian-accessible shaded fraction",
    "overhead_geometry": "overhead geometry shape descriptors",
    "hot_pocket_proxy": "sunlit-hot-pocket area fraction",
    "edge_context": "local boundary / edge context",
    "neighbourhood_context": "neighbourhood-scale context",
    "tree_building_interaction": "tree/building shadow interaction",
    "canyon_roughness": "canyon orientation / height roughness",
    "typology_geometry": "typology-specific geometry",
}


def schema_family_map(config: dict[str, Any]) -> dict[str, str]:
    """Map feature name to B8.6g feature family."""
    schema = b86g_feature_schema(config)
    return {str(row["feature_name"]): str(row["feature_family"]) for _, row in schema.iterrows()}


def ablation_variants(full_features: list[str], family_map: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Build full and drop-family feature variants."""
    variants: dict[str, dict[str, Any]] = {
        "full_b86g_all_safe_numeric": {
            "features": full_features,
            "removed_family_key": "none",
            "removed_feature_family": "none",
            "removed_feature_count": 0,
        }
    }
    for key, family in ABLATION_FAMILIES.items():
        family_cols = [column for column in full_features if family_map.get(column) == family]
        if not family_cols:
            continue
        remaining = [column for column in full_features if column not in family_cols]
        variants[f"drop_{key}"] = {
            "features": remaining,
            "removed_family_key": key,
            "removed_feature_family": family,
            "removed_feature_count": len(family_cols),
        }
    return variants


def best_combo_per_feature_set(combined: pd.DataFrame, feature_set: str, config: dict[str, Any]) -> dict[str, Any]:
    """Select the best combo within one feature set."""
    subset = combined.loc[combined["feature_set"].astype(str).eq(feature_set)].copy()
    return selected_two_stage_combo(subset, config) if not subset.empty else {}


def proxy_vector_comparison(combined: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Summarize proxy-only, vector-only, combined, and baseline feature sets."""
    comparison_sets = [
        "b86d_baseline_without_b86g",
        "b86g_proxy_features_only",
        "b86g_vector_derived_compact_only",
        "b86g_proxy_plus_vector_compact",
        "b86g_high_priority_only",
        "b86g_all_safe_numeric",
    ]
    rows: list[pd.DataFrame] = []
    for feature_set in comparison_sets:
        best = best_combo_per_feature_set(combined, feature_set, config)
        if not best:
            continue
        subset = combined.copy()
        for column in COMBO_COLS:
            subset = subset.loc[subset[column].astype(str).eq(str(best[column]))]
        grouped = metric_group_summary(subset, ["feature_set", "split_family"])
        grouped["selected_classifier"] = str(best["classifier"])
        grouped["selected_regressor"] = str(best["regressor"])
        grouped["comparison_role"] = feature_set
        rows.append(grouped)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if out.empty:
        return out
    baseline = out.loc[out["feature_set"].eq("b86d_baseline_without_b86g"), ["split_family", "Spearman", "top10pct_overlap"]]
    baseline = baseline.rename(columns={"Spearman": "baseline_Spearman", "top10pct_overlap": "baseline_top10pct_overlap"})
    out = out.merge(baseline, on="split_family", how="left")
    out["Spearman_delta_vs_rebuilt_baseline"] = out["Spearman"] - out["baseline_Spearman"]
    out["top10_delta_vs_rebuilt_baseline"] = out["top10pct_overlap"] - out["baseline_top10pct_overlap"]
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def run(config_path: Path = DEFAULT_CONFIG) -> AblationResult:
    """Run feature family ablation and proxy/vector comparison."""
    config = load_config(config_path)
    dataset = read_csv(output_path(config, "modeling_dataset"))
    registry = read_csv(output_path(config, "feature_set_registry"))
    combined = read_csv(output_path(config, "combined_pipeline_metrics"))
    best = selected_two_stage_combo(combined, config)
    selected_classifier = str(best.get("classifier", "logistic_regression"))
    selected_regressor = str(best.get("regressor", "ridge"))
    full_features = feature_columns_for_set(registry, dataset, "b86g_all_safe_numeric")
    family_map = schema_family_map(config)
    variants = ablation_variants(full_features, family_map)
    frames: list[pd.DataFrame] = []
    for variant_name, spec in variants.items():
        metrics, _ = evaluate_two_stage_with_features(
            dataset,
            spec["features"],
            variant_name,
            config,
            classifier_names=[selected_classifier],
            regressor_names=[selected_regressor],
            return_predictions=False,
        )
        grouped = metric_group_summary(metrics, ["feature_set", "split_family"])
        grouped["ablation_variant"] = variant_name
        grouped["removed_family_key"] = spec["removed_family_key"]
        grouped["removed_feature_family"] = spec["removed_feature_family"]
        grouped["removed_feature_count"] = spec["removed_feature_count"]
        grouped["selected_classifier"] = selected_classifier
        grouped["selected_regressor"] = selected_regressor
        frames.append(grouped)
    ablation = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not ablation.empty:
        full = ablation.loc[ablation["ablation_variant"].eq("full_b86g_all_safe_numeric")][
            ["split_family", "Spearman", "top10pct_overlap", "false_promotion_rate", "anchor_MAE"]
        ].rename(
            columns={
                "Spearman": "full_Spearman",
                "top10pct_overlap": "full_top10pct_overlap",
                "false_promotion_rate": "full_false_promotion_rate",
                "anchor_MAE": "full_anchor_MAE",
            }
        )
        ablation = ablation.merge(full, on="split_family", how="left")
        ablation["Spearman_delta_full_minus_variant"] = ablation["full_Spearman"] - ablation["Spearman"]
        ablation["top10_delta_full_minus_variant"] = ablation["full_top10pct_overlap"] - ablation["top10pct_overlap"]
        ablation["false_promotion_delta_variant_minus_full"] = (
            ablation["false_promotion_rate"] - ablation["full_false_promotion_rate"]
        )
        ablation["anchor_MAE_delta_variant_minus_full"] = ablation["anchor_MAE"] - ablation["full_anchor_MAE"]
        ablation["helps_spatial_holdout"] = (
            ablation["split_family"].eq("spatial_holdout")
            & (ablation["Spearman_delta_full_minus_variant"] >= 0.03)
            & ~ablation["ablation_variant"].eq("full_b86g_all_safe_numeric")
        )
        ablation["helps_neutral_false_promotion"] = (
            ablation["false_promotion_delta_variant_minus_full"] >= 0.01
        ) & ~ablation["ablation_variant"].eq("full_b86g_all_safe_numeric")
        ablation["helps_anchor_underprediction"] = (
            ablation["anchor_MAE_delta_variant_minus_full"] >= 0.03
        ) & ~ablation["ablation_variant"].eq("full_b86g_all_safe_numeric")
        ablation["helps_topk"] = (ablation["top10_delta_full_minus_variant"] >= 0.03) & ~ablation["ablation_variant"].eq(
            "full_b86g_all_safe_numeric"
        )
        ablation["claim_boundary"] = CLAIM_BOUNDARY
    comparison = proxy_vector_comparison(combined, config)
    write_csv(ablation, output_path(config, "feature_ablation_metrics"))
    write_csv(comparison, output_path(config, "proxy_vs_vector_feature_comparison"))
    return AblationResult("B86G2_ABLATION_READY", len(ablation), len(comparison))


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run B8.6g2 feature-family ablation and proxy/vector comparison.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
