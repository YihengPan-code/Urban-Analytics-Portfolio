"""Diagnose B8.6c spatial, typology, anchor, neutral, unstable, and h10 failures.

Inputs:
    configs/v12/systemb_b86c_feature_hardening.yaml
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_feature_set_model_metrics.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_oof_prediction_audit.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion compact diagnostic CSVs
    B8.5-F4 compact anchor, neutral, and unstable cell CSVs

Outputs:
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_split_failure_summary.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_spatial_failure_inventory.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_typology_failure_inventory.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_anchor_failure_audit.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_neutral_boundary_audit.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_unstable_cell_audit.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_core_hour_h10_contrast.csv
    outputs/v12_surrogate/b8_6c_feature_hardening/b86c_feature_upgrade_recommendation.csv

Saved metrics:
    Best available primary OOF audit model, split-level weak-holdout summary,
    spatial-bin and typology-bin metrics, repeated cell-level rank/MAE errors,
    neutral-boundary confusion, h10 versus core-hour contrast, and feature
    upgrade recommendations with explicit failure-type labels.

This script reads compact CSV/Markdown/YAML inputs only. It does not run QGIS
or SOLWEIG, does not read raster files, does not open or copy svfs.zip, does
not create AOI-wide prediction, does not convert Tmrt to WBGT, and does not
create WBGT, hazard_score, risk_score, B9, or System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86c_feature_inventory import DEFAULT_CONFIG, read_config, repo_path
from v12_b86c_feature_set_models import finite_corr


@dataclass(frozen=True)
class FailureAuditResult:
    """Compact return record for the B8.6c failure-audit step."""

    status: str
    selected_feature_set: str
    selected_model: str
    split_failure_rows: int
    spatial_failure_headline: str
    typology_failure_headline: str
    anchor_neutral_unstable_headline: str


def read_csv_if_exists(path: Path, **kwargs: Any) -> pd.DataFrame:
    """Read a compact CSV or return an empty frame."""
    return pd.read_csv(path, **kwargs) if path.exists() else pd.DataFrame()


def primary_metrics(metrics: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Filter to primary target, non-dummy, primary-evidence feature sets."""
    if metrics.empty:
        return pd.DataFrame()
    return metrics.loc[
        (metrics["target"] == config["targets"]["primary"])
        & (metrics["model"] != "dummy_mean")
        & metrics["primary_evidence_allowed"].astype(bool)
    ].copy()


def select_oof_model(metrics: pd.DataFrame, oof: pd.DataFrame, config: dict[str, Any]) -> tuple[str, str]:
    """Select a model/feature set that is strong on supporting holdouts and present in OOF."""
    if metrics.empty or oof.empty:
        return "", ""
    allowed_pairs = set(zip(oof["feature_set"].astype(str), oof["model"].astype(str)))
    support = primary_metrics(metrics, config)
    support = support.loc[
        support["split_family"].isin(["cell_group_holdout", "spatial_holdout", "typology_holdout"])
        & support.apply(lambda row: (str(row["feature_set"]), str(row["model"])) in allowed_pairs, axis=1)
    ].copy()
    if support.empty:
        return "", ""
    grouped = support.groupby(["feature_set", "model"], as_index=False).agg(
        MAE=("MAE", "mean"),
        Spearman=("Spearman_observed_vs_predicted", "mean"),
        top10pct=("top10pct_overlap", "mean"),
        b86b_gain=("MAE_improvement_fraction_over_b86b_best", "mean"),
        anchor_mae=("robust_anchor_MAE", "mean"),
        neutral_accuracy=("neutral_boundary_classification_accuracy", "mean"),
    )
    grouped = grouped.sort_values(
        ["Spearman", "top10pct", "b86b_gain", "neutral_accuracy", "anchor_mae", "MAE"],
        ascending=[False, False, False, False, True, True],
    )
    best = grouped.iloc[0]
    return str(best["feature_set"]), str(best["model"])


def selected_oof(oof: pd.DataFrame, feature_set: str, model: str, config: dict[str, Any]) -> pd.DataFrame:
    """Return selected primary OOF predictions."""
    if oof.empty:
        return pd.DataFrame()
    return oof.loc[
        (oof["feature_set"].astype(str) == feature_set)
        & (oof["model"].astype(str) == model)
        & (oof["target"].astype(str) == config["targets"]["primary"])
    ].copy()


def low_delta_top_overlap(frame: pd.DataFrame, fraction: float) -> float:
    """Compute low-delta top-fraction overlap by cell."""
    if frame.empty:
        return float("nan")
    by_cell = frame.groupby("cell_id", as_index=False).agg(y_true=("y_true", "mean"), y_pred=("y_pred", "mean"))
    k = max(1, int(math.ceil(fraction * len(by_cell))))
    true_top = set(by_cell.nsmallest(k, "y_true")["cell_id"].astype(str))
    pred_top = set(by_cell.nsmallest(k, "y_pred")["cell_id"].astype(str))
    return float(len(true_top & pred_top) / k)


def frame_metrics(frame: pd.DataFrame) -> dict[str, float]:
    """Compute compact metrics for an OOF frame."""
    if frame.empty:
        return {"MAE": np.nan, "RMSE": np.nan, "R2": np.nan, "Spearman": np.nan, "top10pct_overlap": np.nan}
    y_true = pd.to_numeric(frame["y_true"], errors="coerce").to_numpy(dtype=float)
    y_pred = pd.to_numeric(frame["y_pred"], errors="coerce").to_numpy(dtype=float)
    mae = float(np.mean(np.abs(y_pred - y_true)))
    rmse = float(math.sqrt(np.mean((y_pred - y_true) ** 2)))
    r2 = float(1 - np.sum((y_true - y_pred) ** 2) / np.sum((y_true - np.mean(y_true)) ** 2)) if len(y_true) > 1 and np.std(y_true) > 0 else np.nan
    return {
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
        "Spearman": finite_corr(y_true, y_pred, "spearman"),
        "top10pct_overlap": low_delta_top_overlap(frame, 0.10),
        "sign_accuracy": float(np.mean(np.sign(y_true) == np.sign(y_pred))),
    }


def failure_label(split_family: str, spearman: float, top10: float, improvement: float | None = None) -> str:
    """Classify a split failure type."""
    weak_rank = (math.isnan(spearman) or spearman < 0.50) and (math.isnan(top10) or top10 < 0.40)
    weak_gain = improvement is not None and not math.isnan(improvement) and improvement < 0.05
    if split_family == "spatial_holdout" and (weak_rank or weak_gain):
        return "spatial-bin-out-of-domain"
    if split_family == "typology_holdout" and (weak_rank or weak_gain):
        return "typology-out-of-domain"
    if split_family == "cell_group_holdout" and (weak_rank or weak_gain):
        return "missing-feature-likely"
    if split_family == "hour_holdout" and weak_rank:
        return "h10-low-sun-caveat"
    return "not-flagged"


def split_failure_summary(metrics: pd.DataFrame, feature_set: str, model: str, config: dict[str, Any]) -> pd.DataFrame:
    """Summarize selected feature-set/model metrics by split family."""
    subset = primary_metrics(metrics, config)
    subset = subset.loc[(subset["feature_set"].astype(str) == feature_set) & (subset["model"].astype(str) == model)].copy()
    if subset.empty:
        return pd.DataFrame()
    grouped = subset.groupby("split_family", as_index=False).agg(
        MAE=("MAE", "mean"),
        RMSE=("RMSE", "mean"),
        R2=("R2", "mean"),
        Spearman=("Spearman_observed_vs_predicted", "mean"),
        top10pct_overlap=("top10pct_overlap", "mean"),
        neutral_accuracy=("neutral_boundary_classification_accuracy", "mean"),
        robust_anchor_MAE=("robust_anchor_MAE", "mean"),
        h10_MAE=("h10_MAE", "mean"),
        h10_Spearman=("h10_Spearman", "mean"),
        b86b_best_MAE=("b86b_best_MAE", "mean"),
        improvement_vs_b86b_best=("MAE_improvement_fraction_over_b86b_best", "mean"),
    )
    grouped.insert(0, "model", model)
    grouped.insert(0, "feature_set", feature_set)
    grouped["failure_type"] = grouped.apply(
        lambda row: failure_label(
            str(row["split_family"]),
            float(row["Spearman"]) if pd.notna(row["Spearman"]) else np.nan,
            float(row["top10pct_overlap"]) if pd.notna(row["top10pct_overlap"]) else np.nan,
            float(row["improvement_vs_b86b_best"]) if pd.notna(row["improvement_vs_b86b_best"]) else np.nan,
        ),
        axis=1,
    )
    grouped["claim_boundary"] = "Weak split diagnostics over compact SOLWEIG-derived labels only."
    return grouped


def split_inventory(oof: pd.DataFrame, split_family: str) -> pd.DataFrame:
    """Build spatial or typology split-bin failure inventory."""
    subset = oof.loc[oof["split_family"].astype(str) == split_family].copy()
    rows: list[dict[str, Any]] = []
    for split_name, part in subset.groupby("split_name", sort=True):
        metrics = frame_metrics(part)
        failure = failure_label(split_family, metrics["Spearman"], metrics["top10pct_overlap"], None)
        rows.append(
            {
                "split_family": split_family,
                "split_name": split_name,
                "n_rows": int(len(part)),
                "n_cells": int(part["cell_id"].nunique()),
                **metrics,
                "failure_type": failure,
                "claim_boundary": "Split-bin diagnostic only; not AOI-wide prediction or observed truth.",
            }
        )
    return pd.DataFrame(rows)


def cell_rank_inventory(oof: pd.DataFrame, flag_column: str, role: str) -> pd.DataFrame:
    """Summarize repeated cell-level errors and rank errors for a diagnostic role."""
    if oof.empty or flag_column not in oof.columns:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for (split_family, split_name, fold_id), fold in oof.groupby(["split_family", "split_name", "fold_id"], sort=True):
        by_cell = fold.groupby("cell_id", as_index=False).agg(
            n_rows=("row_id", "count"),
            mean_true_delta_tmrt_p90_c=("y_true", "mean"),
            mean_pred_delta_tmrt_p90_c=("y_pred", "mean"),
            MAE=("abs_error", "mean"),
        )
        by_cell["true_rank"] = by_cell["mean_true_delta_tmrt_p90_c"].rank(method="min", ascending=True)
        by_cell["pred_rank"] = by_cell["mean_pred_delta_tmrt_p90_c"].rank(method="min", ascending=True)
        role_cells = set(fold.loc[fold[flag_column].astype(bool), "cell_id"].astype(str))
        subset = by_cell.loc[by_cell["cell_id"].astype(str).isin(role_cells)].copy()
        for item in subset.itertuples(index=False):
            bias = float(item.mean_pred_delta_tmrt_p90_c) - float(item.mean_true_delta_tmrt_p90_c)
            if role == "robust_priority_anchor" and bias > 0.20:
                failure_type = "anchor-underprediction"
            elif role == "unstable_review":
                failure_type = "target-role-mismatch" if abs(bias) > 0.20 else "unstable-cell-review"
            else:
                failure_type = "not-flagged"
            rows.append(
                {
                    "cell_id": item.cell_id,
                    "diagnostic_role": role,
                    "split_family": split_family,
                    "split_name": split_name,
                    "fold_id": fold_id,
                    "n_rows": int(item.n_rows),
                    "mean_true_delta_tmrt_p90_c": float(item.mean_true_delta_tmrt_p90_c),
                    "mean_pred_delta_tmrt_p90_c": float(item.mean_pred_delta_tmrt_p90_c),
                    "MAE": float(item.MAE),
                    "true_rank": float(item.true_rank),
                    "pred_rank": float(item.pred_rank),
                    "abs_rank_error": abs(float(item.pred_rank) - float(item.true_rank)),
                    "failure_type": failure_type,
                    "claim_boundary": "Cell diagnostic over SOLWEIG-derived labels only; not observed truth.",
                }
            )
    return pd.DataFrame(rows)


def neutral_inventory(oof: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Build neutral-boundary confusion inventory."""
    if oof.empty or "neutral_boundary_flag" not in oof.columns:
        return pd.DataFrame()
    threshold = float(config["targets"]["neutral_delta_abs_threshold_c"])
    subset = oof.loc[oof["neutral_boundary_flag"].astype(bool)].copy()
    rows: list[dict[str, Any]] = []
    for (cell_id, split_family), part in subset.groupby(["cell_id", "split_family"], sort=True):
        true_neutral = part["y_true"].abs() <= threshold
        pred_neutral = part["y_pred"].abs() <= threshold
        accuracy = float((true_neutral == pred_neutral).mean()) if len(part) else np.nan
        spurious = bool(true_neutral.mean() >= 0.5 and part["y_pred"].mean() < -threshold)
        rows.append(
            {
                "cell_id": cell_id,
                "split_family": split_family,
                "n_rows": int(len(part)),
                "true_neutral_fraction": float(true_neutral.mean()),
                "pred_neutral_fraction": float(pred_neutral.mean()),
                "neutral_boundary_classification_accuracy": accuracy,
                "mean_true_delta_tmrt_p90_c": float(part["y_true"].mean()),
                "mean_pred_delta_tmrt_p90_c": float(part["y_pred"].mean()),
                "MAE": float(part["abs_error"].mean()),
                "spurious_promotion_flag": spurious,
                "failure_type": "neutral-boundary-confusion" if accuracy < 0.70 or spurious else "not-flagged",
                "claim_boundary": "Neutral-boundary diagnostic only; do not promote neutral cells from model artifacts.",
            }
        )
    return pd.DataFrame(rows)


def core_hour_h10_contrast(oof: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Compare h10 and core-hour model behavior."""
    if oof.empty:
        return pd.DataFrame()
    h10 = int(config["diagnostic_cells"]["h10_caveat_hour"])
    work = oof.copy()
    work["hour_class"] = np.where(pd.to_numeric(work["hour_sgt"], errors="coerce") == h10, "h10_low_sun_caveat", "core_hours")
    rows: list[dict[str, Any]] = []
    for (split_family, hour_class), part in work.groupby(["split_family", "hour_class"], sort=True):
        metrics = frame_metrics(part)
        rows.append(
            {
                "split_family": split_family,
                "hour_class": hour_class,
                "n_rows": int(len(part)),
                "n_cells": int(part["cell_id"].nunique()),
                **metrics,
                "failure_type": "h10-low-sun-caveat" if hour_class == "h10_low_sun_caveat" and metrics["MAE"] > 0.15 else "not-flagged",
                "claim_boundary": "h10 is caveated context and not anchor evidence by itself.",
            }
        )
    return pd.DataFrame(rows)


def feature_upgrade_recommendations(
    split_summary: pd.DataFrame,
    spatial: pd.DataFrame,
    typology: pd.DataFrame,
    anchor: pd.DataFrame,
    neutral: pd.DataFrame,
    unstable: pd.DataFrame,
    h10: pd.DataFrame,
) -> pd.DataFrame:
    """Write compact feature-upgrade recommendations."""
    rows: list[dict[str, Any]] = []
    weak_splits = split_summary.loc[split_summary["failure_type"] != "not-flagged"] if not split_summary.empty else pd.DataFrame()
    rows.append(
        {
            "recommendation_area": "spatial_typology_generalisation",
            "evidence": f"{len(weak_splits)} selected split families remain flagged.",
            "failure_types": "|".join(sorted(weak_splits["failure_type"].dropna().unique())) if not weak_splits.empty else "none",
            "recommendation": "Harden compact morphology/shade/overhead representation before AOI-wide preflight; B9 remains blocked.",
            "b86d_action": "Run B8.6d only as improved surrogate workflow review, not AOI-wide prediction.",
        }
    )
    rows.append(
        {
            "recommendation_area": "anchor_cells",
            "evidence": f"Anchor underprediction rows: {int((anchor.get('failure_type', pd.Series(dtype=str)) == 'anchor-underprediction').sum()) if not anchor.empty else 0}.",
            "failure_types": "anchor-underprediction",
            "recommendation": "Inspect missing overhead/shade/canyon descriptors for robust anchors, especially high-cooling cells.",
            "b86d_action": "Keep anchors as diagnostics; do not use h10 alone as evidence.",
        }
    )
    rows.append(
        {
            "recommendation_area": "neutral_boundary",
            "evidence": f"Neutral confusion rows: {int((neutral.get('failure_type', pd.Series(dtype=str)) == 'neutral-boundary-confusion').sum()) if not neutral.empty else 0}.",
            "failure_types": "neutral-boundary-confusion",
            "recommendation": "Preserve a neutral-boundary gate or two-stage workflow to avoid spuriously promoting near-zero cells.",
            "b86d_action": "Carry a two-stage pretest into B8.6d if it improves neutral and supporting holdouts.",
        }
    )
    rows.append(
        {
            "recommendation_area": "h10_caveat",
            "evidence": f"h10 caveat rows: {int((h10.get('failure_type', pd.Series(dtype=str)) == 'h10-low-sun-caveat').sum()) if not h10.empty else 0}.",
            "failure_types": "h10-low-sun-caveat",
            "recommendation": "Report h10 separately from core hours; do not treat h10 as anchor proof.",
            "b86d_action": "Evaluate core-hour and h10 metrics separately.",
        }
    )
    rows.append(
        {
            "recommendation_area": "unstable_review_cells",
            "evidence": f"Unstable review rows: {len(unstable)}.",
            "failure_types": "target-role-mismatch|missing-feature-likely",
            "recommendation": "Keep unstable cells as review inventory rather than promotion evidence.",
            "b86d_action": "Use unstable cells to audit label/feature role mismatch.",
        }
    )
    return pd.DataFrame(rows)


def headline(frame: pd.DataFrame, label: str) -> str:
    """Create a short failure headline."""
    if frame.empty:
        return f"{label}: unavailable."
    flagged = int((frame["failure_type"] != "not-flagged").sum()) if "failure_type" in frame.columns else 0
    return f"{label}: {flagged}/{len(frame)} rows flagged."


def run(config_path: Path = DEFAULT_CONFIG) -> FailureAuditResult:
    """Run B8.6c failure audits and write compact outputs."""
    config = read_config(config_path)
    metrics = read_csv_if_exists(repo_path(config["outputs"]["feature_set_model_metrics"]))
    oof = read_csv_if_exists(repo_path(config["outputs"]["oof_prediction_audit"]))
    feature_set, model = select_oof_model(metrics, oof, config)
    selected = selected_oof(oof, feature_set, model, config)

    split_summary = split_failure_summary(metrics, feature_set, model, config)
    spatial = split_inventory(selected, "spatial_holdout")
    typology = split_inventory(selected, "typology_holdout")
    anchor = cell_rank_inventory(selected, "robust_anchor_flag", "robust_priority_anchor")
    neutral = neutral_inventory(selected, config)
    unstable = cell_rank_inventory(selected, "unstable_review_flag", "unstable_review")
    h10 = core_hour_h10_contrast(selected, config)
    recommendations = feature_upgrade_recommendations(split_summary, spatial, typology, anchor, neutral, unstable, h10)

    split_summary.to_csv(repo_path(config["outputs"]["split_failure_summary"]), index=False)
    spatial.to_csv(repo_path(config["outputs"]["spatial_failure_inventory"]), index=False)
    typology.to_csv(repo_path(config["outputs"]["typology_failure_inventory"]), index=False)
    anchor.to_csv(repo_path(config["outputs"]["anchor_failure_audit"]), index=False)
    neutral.to_csv(repo_path(config["outputs"]["neutral_boundary_audit"]), index=False)
    unstable.to_csv(repo_path(config["outputs"]["unstable_cell_audit"]), index=False)
    h10.to_csv(repo_path(config["outputs"]["core_hour_h10_contrast"]), index=False)
    recommendations.to_csv(repo_path(config["outputs"]["feature_upgrade_recommendation"]), index=False)

    combined_headline = (
        f"{headline(anchor, 'anchors')} {headline(neutral, 'neutral')} {headline(unstable, 'unstable')}"
    )
    return FailureAuditResult(
        status="B86C_FAILURE_AUDIT_READY" if feature_set and model else "B86C_BLOCKED_INPUT",
        selected_feature_set=feature_set,
        selected_model=model,
        split_failure_rows=int(len(split_summary)),
        spatial_failure_headline=headline(spatial, "spatial"),
        typology_failure_headline=headline(typology, "typology"),
        anchor_neutral_unstable_headline=combined_headline,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Diagnose B8.6c spatial, typology, anchor, neutral-boundary, unstable-cell, and h10 failures."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6c YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
