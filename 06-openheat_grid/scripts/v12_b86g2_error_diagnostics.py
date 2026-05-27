"""Write B8.6g2 selected-workflow error diagnostics.

Inputs:
    b86g2_oof_predictions.csv, B8.6d OOF predictions, and B8.6f anchor/neutral
    failure context when available.
Outputs:
    b86g2_anchor_cell_diagnostics.csv,
    b86g2_neutral_boundary_diagnostics.csv,
    b86g2_unstable_cell_diagnostics.csv, and
    b86g2_worst_error_inventory.csv.
Saved metrics:
    Per-cell true mean delta, predicted mean delta, MAE, false promotion rate,
    false neutral rate, rank error, responsible feature set/model, and B8.6d
    comparison where available.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86g2_common import CLAIM_BOUNDARY, DEFAULT_CONFIG, load_config, output_path, read_csv, write_csv


@dataclass(frozen=True)
class DiagnosticsResult:
    """Diagnostics result."""

    status: str
    anchor_rows: int
    neutral_rows: int
    unstable_rows: int
    worst_rows: int


def baseline_cell_metrics(config: dict[str, Any]) -> pd.DataFrame:
    """Derive B8.6d selected OOF per-cell metrics for comparison."""
    try:
        b86d = read_csv(config["b86d_oof_predictions_path"])
    except FileNotFoundError:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for split_family, split_frame in b86d.groupby("split_family", dropna=False):
        by_cell = split_frame.groupby("cell_id", as_index=False).agg(
            b86d_n_rows=("row_id", "size"),
            b86d_mean_true_delta_tmrt_p90_c=("true_delta", "mean"),
            b86d_mean_pred_delta_tmrt_p90_c=("pred_combined_delta", "mean"),
            b86d_MAE=("combined_abs_error", "mean"),
            b86d_false_promotion_rate=("combined_false_promotion", "mean"),
            b86d_false_neutral_rate=("combined_false_neutral", "mean"),
        )
        by_cell["b86d_true_rank"] = by_cell["b86d_mean_true_delta_tmrt_p90_c"].rank(method="min", ascending=True)
        by_cell["b86d_pred_rank"] = by_cell["b86d_mean_pred_delta_tmrt_p90_c"].rank(method="min", ascending=True)
        by_cell["b86d_abs_rank_error"] = (by_cell["b86d_pred_rank"] - by_cell["b86d_true_rank"]).abs()
        by_cell["split_family"] = split_family
        rows.append(by_cell)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def near_zero_cells_from_b86f(config: dict[str, Any]) -> list[str]:
    """Load near-zero false-promotion context cells from B8.6f when available."""
    try:
        frame = read_csv(config["b86f_anchor_neutral_failure_path"])
    except FileNotFoundError:
        return []
    if "diagnostic_role" not in frame.columns:
        return []
    mask = frame["diagnostic_role"].astype(str).str.contains("near_zero", case=False, na=False)
    return sorted(frame.loc[mask, "cell_id"].astype(str).unique().tolist())


def per_cell_diagnostics(
    predictions: pd.DataFrame,
    cells: list[str],
    role: str,
    baseline: pd.DataFrame,
) -> pd.DataFrame:
    """Create per-cell split-family diagnostics for selected cells."""
    rows: list[pd.DataFrame] = []
    wanted = set(cells)
    selected = predictions.loc[predictions["cell_id"].astype(str).isin(wanted)].copy()
    if selected.empty:
        return pd.DataFrame()
    for split_family, split_frame in selected.groupby("split_family", dropna=False):
        by_cell = split_frame.groupby("cell_id", as_index=False).agg(
            n_rows=("row_id", "size"),
            mean_true_delta_tmrt_p90_c=("true_delta", "mean"),
            mean_pred_delta_tmrt_p90_c=("pred_combined_delta", "mean"),
            MAE=("combined_abs_error", "mean"),
            false_promotion_rate=("combined_false_promotion", "mean"),
            false_neutral_rate=("combined_false_neutral", "mean"),
            feature_set=("feature_set", "first"),
            classifier=("classifier", "first"),
            regressor=("regressor", "first"),
        )
        full_rank = split_frame.groupby("cell_id", as_index=False).agg(
            true=("true_delta", "mean"),
            pred=("pred_combined_delta", "mean"),
        )
        full_rank["true_rank"] = full_rank["true"].rank(method="min", ascending=True)
        full_rank["pred_rank"] = full_rank["pred"].rank(method="min", ascending=True)
        by_cell = by_cell.merge(
            full_rank[["cell_id", "true_rank", "pred_rank"]],
            on="cell_id",
            how="left",
        )
        by_cell["abs_rank_error"] = (by_cell["pred_rank"] - by_cell["true_rank"]).abs()
        by_cell["split_family"] = split_family
        by_cell["diagnostic_role"] = role
        rows.append(by_cell)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if not baseline.empty:
        out = out.merge(baseline, on=["cell_id", "split_family"], how="left")
        out["MAE_delta_vs_b86d"] = out["MAE"] - out["b86d_MAE"]
        out["MAE_improvement_vs_b86d"] = out["b86d_MAE"] - out["MAE"]
        out["false_promotion_delta_vs_b86d"] = out["false_promotion_rate"] - out["b86d_false_promotion_rate"]
        out["rank_error_delta_vs_b86d"] = out["abs_rank_error"] - out["b86d_abs_rank_error"]
    out["feature_set_model_responsible"] = out["feature_set"].astype(str) + "|" + out["classifier"].astype(str) + "|" + out[
        "regressor"
    ].astype(str)
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def neutral_cells(config: dict[str, Any]) -> list[str]:
    """Return known neutral plus B8.6f near-zero false-promotion cells."""
    cells = list(config["diagnostic_cells"]["known_neutral_cells"])
    cells.extend(near_zero_cells_from_b86f(config))
    return sorted(set(cells))


def worst_error_inventory(predictions: pd.DataFrame, max_rows: int = 100) -> pd.DataFrame:
    """Return highest absolute-error selected OOF rows."""
    columns = [
        "row_id",
        "cell_id",
        "forcing_day_id",
        "hour_sgt",
        "typology_label",
        "feature_set",
        "classifier",
        "regressor",
        "split_family",
        "split_name",
        "fold_id",
        "true_delta",
        "pred_combined_delta",
        "combined_abs_error",
        "true_class",
        "pred_stage1_class",
        "pred_stage2_delta",
        "combined_false_promotion",
        "combined_false_neutral",
    ]
    out = predictions.sort_values("combined_abs_error", ascending=False).loc[:, columns].head(max_rows).copy()
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def run(config_path: Path = DEFAULT_CONFIG) -> DiagnosticsResult:
    """Write selected-workflow diagnostics."""
    config = load_config(config_path)
    predictions = read_csv(output_path(config, "oof_predictions"))
    baseline = baseline_cell_metrics(config)
    anchors = per_cell_diagnostics(predictions, config["diagnostic_cells"]["anchor_cells"], "anchor_reference", baseline)
    neutrals = per_cell_diagnostics(predictions, neutral_cells(config), "known_neutral_or_near_zero_reference", baseline)
    unstable = per_cell_diagnostics(predictions, config["diagnostic_cells"]["unstable_cells"], "unstable_cell_reference", baseline)
    worst = worst_error_inventory(predictions)
    write_csv(anchors, output_path(config, "anchor_cell_diagnostics"))
    write_csv(neutrals, output_path(config, "neutral_boundary_diagnostics"))
    write_csv(unstable, output_path(config, "unstable_cell_diagnostics"))
    write_csv(worst, output_path(config, "worst_error_inventory"))
    return DiagnosticsResult("B86G2_DIAGNOSTICS_READY", len(anchors), len(neutrals), len(unstable), len(worst))


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Write B8.6g2 anchor, neutral, unstable, and worst-error diagnostics.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
