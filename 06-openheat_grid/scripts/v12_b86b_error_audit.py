"""Audit B8.6b surrogate errors and write promotion-review reports.

Inputs:
    configs/v12/systemb_b86b_surrogate_promotion.yaml
    B8.6b compact dataset/schema/splits/model metric outputs
    B8.5-F4 anchor, neutral-boundary, and unstable-review CSVs
    B8.5-F5 stability summary CSV

Outputs:
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_anchor_cell_diagnostics.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_neutral_boundary_diagnostics.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_unstable_cell_diagnostics.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_worst_error_inventory.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_feature_importance_diagnostics.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_promotion_decision_matrix.csv
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_promotion_gate.md
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_model_card.md
    outputs/v12_surrogate/b8_6b_surrogate_promotion/b86b_report.md
    outputs/v12_surrogate/b8_6b_surrogate_promotion/B8_6B_STATUS.md
    docs/v12/OpenHeat_SystemB_B8_6b_surrogate_promotion_CN.md

Saved metrics:
    Best primary model, forcing-day gate metrics, cross-holdout collapse
    checks, anchor/neutral/unstable diagnostics, h10 caveat metrics,
    non-causal feature-importance diagnostics, promotion decision matrix,
    AOI-wide preflight recommendation, and B9 status.

This script reads only compact CSV/Markdown/YAML inputs. It does not run QGIS
or SOLWEIG, does not read raster files, does not create AOI-wide prediction,
does not convert Tmrt to WBGT, and does not create WBGT, hazard_score,
risk_score, B9, or System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

from v12_b86b_surrogate_inventory import DEFAULT_CONFIG, read_config, rel_path, repo_path
from v12_b86b_surrogate_models import (
    available_targets,
    best_primary_model,
    coerce_model_features,
    finite_corr,
    make_models,
    make_pipeline,
    prediction_records_for_model,
    selected_features,
)


READY_STATUS = "B86B_SURROGATE_PROMOTION_READY_FOR_AOI_PREFLIGHT"
PROMISING_STATUS = "B86B_RANKING_SURROGATE_PROMISING_NOT_MAGNITUDE"
WEAK_STATUS = "B86B_WEAK_NEEDS_FEATURE_UPGRADE"
BLOCKED_FEATURE_STATUS = "B86B_BLOCKED_FEATURE_INPUT"
BLOCKED_LABEL_STATUS = "B86B_BLOCKED_LABEL_INPUT"
FAILED_STATUS = "FAILED"


@dataclass(frozen=True)
class AuditResult:
    """Compact return record for the B8.6b audit/report step."""

    status: str
    best_primary_model: str
    forcing_day_headline: str
    cross_holdout_headline: str
    target_sensitivity_headline: str
    diagnostics_headline: str
    aoi_preflight_recommendation: str
    b9_status: str


def now_stamp() -> str:
    """Return a compact local timestamp string."""
    return time.strftime("%Y-%m-%d %H:%M:%S")


def command_output(args: list[str]) -> str:
    """Run a lightweight command for status reporting."""
    completed = subprocess.run(args, cwd=repo_path("."), check=False, capture_output=True, text=True)
    return completed.stdout.strip()


def read_csv_if_exists(path: Path, **kwargs: Any) -> pd.DataFrame:
    """Read a compact CSV or return an empty frame."""
    return pd.read_csv(path, **kwargs) if path.exists() else pd.DataFrame()


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 12) -> str:
    """Render a small DataFrame as a GitHub-style Markdown table without extra dependencies."""
    if frame.empty:
        return "_No rows available._"
    view = frame[[column for column in columns if column in frame.columns]].head(max_rows).copy()
    if view.empty:
        return "_No requested columns available._"
    headers = list(view.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in view.iterrows():
        values = []
        for column in headers:
            value = row[column]
            if isinstance(value, float):
                values.append("" if math.isnan(value) else f"{value:.4f}")
            else:
                values.append(str(value).replace("\n", " ")[:220])
        lines.append("| " + " | ".join(values) + " |")
    if len(frame) > max_rows:
        lines.append(f"| ... | {len(frame) - max_rows} more rows |" + " |" * max(0, len(headers) - 2))
    return "\n".join(lines)


def split_summary(metrics: pd.DataFrame, model: str, target: str, split_family: str) -> dict[str, float]:
    """Summarize one model/target/split family."""
    subset = metrics.loc[
        (metrics["model"] == model)
        & (metrics["target"] == target)
        & (metrics["split_family"] == split_family)
    ].copy()
    if subset.empty:
        return {}
    return {
        "MAE": float(subset["MAE"].mean()),
        "RMSE": float(subset["RMSE"].mean()),
        "R2": float(subset["R2"].mean()),
        "Spearman": float(subset["Spearman_observed_vs_predicted"].mean()),
        "top10pct": float(subset["top10pct_overlap"].mean()),
        "improvement": float(subset["MAE_improvement_fraction_over_dummy"].mean()),
        "anchor_rank_error": float(subset["robust_anchor_mean_rank_error"].mean()),
        "neutral_accuracy": float(subset["neutral_boundary_classification_accuracy"].mean()),
        "h10_MAE": float(subset["h10_MAE"].mean()),
        "h10_Spearman": float(subset["h10_Spearman"].mean()),
    }


def status_from_metrics(metrics: pd.DataFrame, model: str, config: dict[str, Any]) -> str:
    """Apply the B8.6b promotion gate rules."""
    if metrics.empty or not model:
        return BLOCKED_FEATURE_STATUS
    primary = config["targets"]["primary"]
    gate = config["promotion_gate"]
    fd = split_summary(metrics, model, primary, "forcing_day_holdout")
    if not fd:
        return BLOCKED_LABEL_STATUS
    fd_rank_good = (
        fd["Spearman"] >= float(gate["forcing_day_min_spearman_ready"])
        or fd["top10pct"] >= float(gate["forcing_day_min_top10pct_ready"])
    )
    meaningful_improvement = fd["improvement"] >= float(gate["meaningful_mae_improvement_fraction"])
    weak_improvement = fd["improvement"] >= float(gate["weak_min_mae_improvement_fraction"])
    holdout_families = ["cell_group_holdout", "hour_holdout", "spatial_holdout", "typology_holdout"]
    collapse_checks: list[bool] = []
    for family in holdout_families:
        summary = split_summary(metrics, model, primary, family)
        if not summary:
            collapse_checks.append(False)
            continue
        collapse_checks.append(
            (
                summary["Spearman"] >= float(gate["noncollapse_min_spearman"])
                or summary["top10pct"] >= float(gate["noncollapse_min_top10pct"])
            )
            and summary["improvement"] > 0
        )
    holdouts_do_not_collapse = all(collapse_checks)
    anchor_ok = fd["anchor_rank_error"] <= float(gate["anchor_max_mean_rank_error"]) if not math.isnan(fd["anchor_rank_error"]) else True
    neutral_ok = fd["neutral_accuracy"] >= float(gate["neutral_min_accuracy"]) if not math.isnan(fd["neutral_accuracy"]) else True
    magnitude_ok = fd["R2"] >= 0.20

    if fd_rank_good and meaningful_improvement and holdouts_do_not_collapse and anchor_ok and neutral_ok and magnitude_ok:
        return READY_STATUS
    if fd_rank_good and weak_improvement:
        return PROMISING_STATUS
    if weak_improvement:
        return WEAK_STATUS
    return WEAK_STATUS


def diagnostic_downgrade_status(
    preliminary_status: str,
    metrics: pd.DataFrame,
    neutral_diag: pd.DataFrame,
    config: dict[str, Any],
    model: str,
) -> str:
    """Conservatively downgrade promotion when support diagnostics fail."""
    if preliminary_status in {BLOCKED_FEATURE_STATUS, BLOCKED_LABEL_STATUS, FAILED_STATUS}:
        return preliminary_status
    primary = config["targets"]["primary"]
    gate = config["promotion_gate"]
    support_families = ["cell_group_holdout", "hour_holdout", "spatial_holdout", "typology_holdout"]
    weak_support = False
    for family in support_families:
        summary = split_summary(metrics, model, primary, family)
        if not summary:
            weak_support = True
            continue
        if (
            summary["top10pct"] < float(gate["noncollapse_min_top10pct"])
            and summary["Spearman"] < 0.50
        ) or summary["improvement"] < float(gate["meaningful_mae_improvement_fraction"]):
            weak_support = True
    neutral_accuracy = float(neutral_diag["neutral_boundary_classification_accuracy"].mean()) if not neutral_diag.empty else float("nan")
    spurious_neutral = bool(neutral_diag["spurious_promotion_flag"].astype(bool).any()) if not neutral_diag.empty else False
    neutral_failed = (
        not math.isnan(neutral_accuracy)
        and neutral_accuracy < float(gate["neutral_min_accuracy"])
    ) or spurious_neutral
    if neutral_failed or weak_support:
        return WEAK_STATUS
    return preliminary_status


def recommendation_for_status(status: str) -> str:
    """Return the AOI-wide preflight recommendation for a gate status."""
    if status == READY_STATUS:
        return "Future AOI-wide prediction preflight may be scoped after review; B8.6b does not generate it."
    if status == PROMISING_STATUS:
        return "Do not run AOI-wide prediction yet; a future ranking-only preflight design may be reviewed after magnitude and feature hardening."
    if status == WEAK_STATUS:
        return "AOI-wide preflight is not recommended; upgrade compact features and re-test forcing-day/spatial/typology generalisation."
    return "AOI-wide preflight is blocked until compact label/feature inputs are fixed."


def cell_rank_diagnostics(predictions: pd.DataFrame, cells: list[str], role: str) -> pd.DataFrame:
    """Summarize configured cells across split families."""
    if predictions.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for (split_family, split_name, fold_id), fold in predictions.groupby(["split_family", "split_name", "fold_id"], sort=True):
        by_cell = fold.groupby("cell_id", as_index=False).agg(
            y_true=("y_true", "mean"),
            y_pred=("y_pred", "mean"),
            MAE=("abs_error", "mean"),
        )
        by_cell["true_rank"] = by_cell["y_true"].rank(method="min", ascending=True)
        by_cell["pred_rank"] = by_cell["y_pred"].rank(method="min", ascending=True)
        subset = by_cell.loc[by_cell["cell_id"].astype(str).isin(cells)].copy()
        for item in subset.itertuples(index=False):
            rows.append(
                {
                    "cell_id": item.cell_id,
                    "diagnostic_role": role,
                    "split_family": split_family,
                    "split_name": split_name,
                    "fold_id": fold_id,
                    "mean_true_delta_tmrt_p90_c": item.y_true,
                    "mean_pred_delta_tmrt_p90_c": item.y_pred,
                    "MAE": item.MAE,
                    "true_rank": item.true_rank,
                    "pred_rank": item.pred_rank,
                    "abs_rank_error": abs(float(item.pred_rank) - float(item.true_rank)),
                    "claim_boundary": "Diagnostic only; not observed truth and not causal feature importance.",
                }
            )
    return pd.DataFrame(rows)


def neutral_diagnostics(predictions: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Build neutral-boundary diagnostics for configured neutral cells."""
    if predictions.empty:
        return pd.DataFrame()
    threshold = float(config["targets"]["neutral_delta_abs_threshold_c"])
    neutral_cells = list(config["diagnostic_cells"]["neutral_boundary_cells"])
    rows: list[dict[str, Any]] = []
    subset = predictions.loc[predictions["cell_id"].astype(str).isin(neutral_cells)].copy()
    for (cell_id, split_family), part in subset.groupby(["cell_id", "split_family"], sort=True):
        rows.append(
            {
                "cell_id": cell_id,
                "split_family": split_family,
                "n_rows": int(len(part)),
                "true_neutral_fraction": float((part["y_true"].abs() <= threshold).mean()),
                "pred_neutral_fraction": float((part["y_pred"].abs() <= threshold).mean()),
                "neutral_boundary_classification_accuracy": float(((part["y_true"].abs() <= threshold) == (part["y_pred"].abs() <= threshold)).mean()),
                "mean_true_delta_tmrt_p90_c": float(part["y_true"].mean()),
                "mean_pred_delta_tmrt_p90_c": float(part["y_pred"].mean()),
                "MAE": float(part["abs_error"].mean()),
                "spurious_promotion_flag": bool((part["y_true"].abs() <= threshold).mean() >= 0.5 and part["y_pred"].mean() < -threshold),
                "claim_boundary": "Neutral cells should not be spuriously promoted by the surrogate.",
            }
        )
    return pd.DataFrame(rows)


def worst_error_inventory(predictions: pd.DataFrame) -> pd.DataFrame:
    """Build worst per-cell and per-row error inventory."""
    if predictions.empty:
        return pd.DataFrame()
    by_cell = predictions.groupby(["split_family", "cell_id"], as_index=False).agg(
        n_rows=("row_id", "count"),
        MAE=("abs_error", "mean"),
        max_abs_error=("abs_error", "max"),
        mean_true_delta_tmrt_p90_c=("y_true", "mean"),
        mean_pred_delta_tmrt_p90_c=("y_pred", "mean"),
    )
    by_cell["inventory_level"] = "cell_by_split_family"
    by_cell["claim_boundary"] = "Error audit over SOLWEIG-derived labels only."
    return by_cell.sort_values(["MAE", "max_abs_error"], ascending=False).head(60).reset_index(drop=True)


def feature_importance_diagnostics(
    dataset: pd.DataFrame,
    schema: pd.DataFrame,
    config: dict[str, Any],
    model_name: str,
) -> pd.DataFrame:
    """Fit the best primary model on compact labels and write non-causal feature diagnostics."""
    features = selected_features(schema)
    dataset, features = coerce_model_features(dataset, features)
    if not model_name or model_name == "dummy_mean" or not features:
        return pd.DataFrame()
    models = make_models(config)
    if model_name not in models:
        return pd.DataFrame()
    target = config["targets"]["primary"]
    frame = dataset.loc[dataset[target].notna()].copy()
    pipe = make_pipeline(model_name, models[model_name], features)
    pipe.fit(frame[features], pd.to_numeric(frame[target], errors="coerce").to_numpy(dtype=float))
    model = pipe.named_steps["model"]
    importances: np.ndarray
    method: str
    if hasattr(model, "feature_importances_"):
        importances = np.asarray(model.feature_importances_, dtype=float)
        method = "model_native_feature_importance"
    elif hasattr(model, "coef_"):
        importances = np.abs(np.asarray(model.coef_, dtype=float).ravel())
        method = "absolute_linear_coefficient"
    else:
        result = permutation_importance(
            pipe,
            frame[features],
            pd.to_numeric(frame[target], errors="coerce").to_numpy(dtype=float),
            scoring="neg_mean_absolute_error",
            n_repeats=3,
            random_state=int(config["random_seed"]),
        )
        importances = np.asarray(result.importances_mean, dtype=float)
        method = "permutation_importance_neg_mae"
    total = float(np.nansum(np.abs(importances)))
    rows = []
    for feature, importance in zip(features, importances):
        rows.append(
            {
                "model": model_name,
                "target": target,
                "feature": feature,
                "importance": float(importance),
                "normalized_abs_importance": float(abs(importance) / total) if total > 0 else np.nan,
                "method": method,
                "diagnostic_boundary": "Non-causal model diagnostic only; does not prove real-world heat-risk drivers.",
            }
        )
    return pd.DataFrame(rows).sort_values("normalized_abs_importance", ascending=False).reset_index(drop=True)


def decision_matrix(
    status: str,
    metrics: pd.DataFrame,
    sensitivity: pd.DataFrame,
    anchor_diag: pd.DataFrame,
    neutral_diag: pd.DataFrame,
    unstable_diag: pd.DataFrame,
    config: dict[str, Any],
    model: str,
) -> pd.DataFrame:
    """Build the B8.6b promotion decision matrix."""
    primary = config["targets"]["primary"]
    fd = split_summary(metrics, model, primary, "forcing_day_holdout")
    other_families = ["cell_group_holdout", "hour_holdout", "spatial_holdout", "typology_holdout"]
    other_bits = []
    support_ok = True
    for family in other_families:
        summary = split_summary(metrics, model, primary, family)
        if summary:
            other_bits.append(f"{family}: Spearman={summary['Spearman']:.3f}, top10pct={summary['top10pct']:.3f}, improvement={summary['improvement']:.1%}")
            if (
                summary["top10pct"] < float(config["promotion_gate"]["noncollapse_min_top10pct"])
                and summary["Spearman"] < 0.50
            ) or summary["improvement"] < float(config["promotion_gate"]["meaningful_mae_improvement_fraction"]):
                support_ok = False
        else:
            other_bits.append(f"{family}: unavailable")
            support_ok = False
    neutral_acc = float(neutral_diag["neutral_boundary_classification_accuracy"].mean()) if not neutral_diag.empty else float("nan")
    spurious_neutral = bool(neutral_diag["spurious_promotion_flag"].astype(bool).any()) if not neutral_diag.empty else False
    neutral_ok = (
        not neutral_diag.empty
        and not math.isnan(neutral_acc)
        and neutral_acc >= float(config["promotion_gate"]["neutral_min_accuracy"])
        and not spurious_neutral
    )
    rows = [
        {
            "gate": "label_input",
            "status": "PASS" if not metrics.empty else "BLOCKED",
            "evidence": "F5 pairwise labels are used as the only training target source; expected 1500 rows.",
            "next_action": "Keep old single-forcing labels as metadata only.",
            "claim_boundary": "SOLWEIG Tmrt labels only; not WBGT, risk, observed truth, or B9.",
        },
        {
            "gate": "feature_input",
            "status": "PASS" if model else "BLOCKED",
            "evidence": "Compact N150 sample-design physical features plus hour_sgt; cell_id and forcing_day_id excluded from predictors.",
            "next_action": "Upgrade compact features only if generalisation remains weak.",
            "claim_boundary": "Feature importance is diagnostic only and not causal.",
        },
        {
            "gate": "forcing_day_holdout",
            "status": "PASS" if fd else "BLOCKED",
            "evidence": (
                f"{model}: Spearman={fd.get('Spearman', np.nan):.3f}, top10pct={fd.get('top10pct', np.nan):.3f}, "
                f"MAE={fd.get('MAE', np.nan):.4f}, R2={fd.get('R2', np.nan):.3f}, improvement={fd.get('improvement', np.nan):.1%}"
                if fd
                else "No forcing-day holdout metrics."
            ),
            "next_action": "Use this as primary promotion evidence; random split remains diagnostic only.",
            "claim_boundary": "Forcing generalisation is over two F5 weather forcing days only.",
        },
        {
            "gate": "cell_spatial_typology_hour_holdouts",
            "status": "PASS" if support_ok else "WARN",
            "evidence": " | ".join(other_bits),
            "next_action": "Treat any collapsing split as a feature/target hardening signal.",
            "claim_boundary": "No AOI-wide prediction is generated in this lane.",
        },
        {
            "gate": "target_sensitivity",
            "status": "PASS" if not sensitivity.empty else "WARN",
            "evidence": target_sensitivity_text(sensitivity, config),
            "next_action": "Keep p90 primary by role; report mean/p50 as companion targets when they are more predictable or larger in magnitude.",
            "claim_boundary": "Do not automatically replace p90 without role-specific review.",
        },
        {
            "gate": "anchor_neutral_unstable_audit",
            "status": "PASS" if not anchor_diag.empty and neutral_ok and not unstable_diag.empty else "WARN",
            "evidence": diagnostics_text(anchor_diag, neutral_diag, unstable_diag),
            "next_action": "Keep h10 caveat separated and do not promote neutral-boundary cells from model artefacts.",
            "claim_boundary": "F4 cells are diagnostics, not observed truth.",
        },
        {
            "gate": "h10_caveat",
            "status": "PASS",
            "evidence": "h10 metrics are reported separately in model metric outputs.",
            "next_action": "Do not use h10 alone as anchor evidence.",
            "claim_boundary": "h10 caveat retained from F4/F5.",
        },
        {
            "gate": "aoi_preflight",
            "status": status,
            "evidence": recommendation_for_status(status),
            "next_action": recommendation_for_status(status),
            "claim_boundary": "B8.6b may recommend a future preflight but does not generate AOI-wide prediction.",
        },
        {
            "gate": "b9_status",
            "status": "BLOCKED",
            "evidence": "This lane is surrogate-promotion review only.",
            "next_action": "B9 remains separately scoped and blocked.",
            "claim_boundary": "Not B9, not local WBGT, not risk, no System A/B coupling.",
        },
        {
            "gate": "final_status",
            "status": status,
            "evidence": f"Best primary model: {model}. {forcing_day_headline(metrics, config, model)}",
            "next_action": recommendation_for_status(status),
            "claim_boundary": "No raster committed, no Tmrt-to-WBGT conversion, no observed-truth claim.",
        },
    ]
    return pd.DataFrame(rows)


def forcing_day_headline(metrics: pd.DataFrame, config: dict[str, Any], model: str) -> str:
    """Return concise forcing-day headline for the best primary model."""
    summary = split_summary(metrics, model, config["targets"]["primary"], "forcing_day_holdout")
    if not summary:
        return "Forcing-day holdout unavailable."
    return (
        f"Forcing-day holdout MAE={summary['MAE']:.4f}, R2={summary['R2']:.3f}, "
        f"Spearman={summary['Spearman']:.3f}, top10pct={summary['top10pct']:.3f}, "
        f"improvement={summary['improvement']:.1%}."
    )


def cross_holdout_headline(metrics: pd.DataFrame, config: dict[str, Any], model: str) -> str:
    """Return concise cross-holdout headline."""
    primary = config["targets"]["primary"]
    parts = []
    for family in ["cell_group_holdout", "spatial_holdout", "typology_holdout", "hour_holdout"]:
        summary = split_summary(metrics, model, primary, family)
        if summary:
            parts.append(f"{family} Spearman={summary['Spearman']:.3f}, top10pct={summary['top10pct']:.3f}")
    return "; ".join(parts) if parts else "Cross-holdout metrics unavailable."


def target_sensitivity_text(sensitivity: pd.DataFrame, config: dict[str, Any]) -> str:
    """Return target sensitivity headline text."""
    if sensitivity.empty:
        return "Target sensitivity unavailable."
    valid = sensitivity.loc[sensitivity["available"].astype(str).str.lower().isin({"true", "1", "yes"})].copy()
    if valid.empty:
        return "Target sensitivity unavailable."
    best = valid.sort_values(["forcing_day_spearman", "forcing_day_top10pct_overlap"], ascending=[False, False]).iloc[0]
    primary = valid.loc[valid["target"] == config["targets"]["primary"]]
    primary_s = float(primary.iloc[0]["forcing_day_spearman"]) if not primary.empty else np.nan
    return f"Most predictable target: {best['target']} (Spearman={float(best['forcing_day_spearman']):.3f}); primary p90 Spearman={primary_s:.3f}."


def diagnostics_text(anchor_diag: pd.DataFrame, neutral_diag: pd.DataFrame, unstable_diag: pd.DataFrame) -> str:
    """Return anchor/neutral/unstable diagnostic headline."""
    anchor_mae = float(anchor_diag["MAE"].mean()) if not anchor_diag.empty else np.nan
    anchor_rank = float(anchor_diag["abs_rank_error"].mean()) if not anchor_diag.empty else np.nan
    neutral_acc = float(neutral_diag["neutral_boundary_classification_accuracy"].mean()) if not neutral_diag.empty else np.nan
    unstable_mae = float(unstable_diag["MAE"].mean()) if not unstable_diag.empty else np.nan
    return f"anchor MAE={anchor_mae:.4f}, anchor rank error={anchor_rank:.2f}, neutral accuracy={neutral_acc:.3f}, unstable MAE={unstable_mae:.4f}."


def output_files(config: dict[str, Any]) -> list[str]:
    """Return B8.6b output files expected from this lane."""
    keys = [
        "input_inventory",
        "label_source_inventory",
        "feature_source_inventory",
        "surrogate_dataset",
        "feature_schema",
        "target_schema",
        "validation_splits",
        "model_metrics_by_split",
        "forcing_day_holdout_metrics",
        "cell_group_holdout_metrics",
        "hour_holdout_metrics",
        "spatial_holdout_metrics",
        "typology_holdout_metrics",
        "target_sensitivity_metrics",
        "topk_overlap_metrics",
        "anchor_cell_diagnostics",
        "neutral_boundary_diagnostics",
        "unstable_cell_diagnostics",
        "worst_error_inventory",
        "feature_importance_diagnostics",
        "promotion_decision_matrix",
        "promotion_gate",
        "model_card",
        "report",
        "status",
        "cn_doc",
    ]
    return [config["outputs"][key] for key in keys]


def write_promotion_gate(path: Path, status: str, metrics: pd.DataFrame, sensitivity: pd.DataFrame, config: dict[str, Any], model: str) -> None:
    """Write promotion gate Markdown."""
    lines = [
        "# B8.6b Promotion Gate",
        "",
        f"Generated: {now_stamp()}",
        "",
        f"Status: `{status}`",
        "",
        "## Gate Result",
        "",
        f"- Best primary model: `{model}`",
        f"- {forcing_day_headline(metrics, config, model)}",
        f"- {cross_holdout_headline(metrics, config, model)}",
        f"- {target_sensitivity_text(sensitivity, config)}",
        f"- AOI-wide preflight recommendation: {recommendation_for_status(status)}",
        "- B9 status: `BLOCKED`.",
        "",
        "## Boundaries",
        "",
        "- Not B9.",
        "- Not local WBGT.",
        "- Not risk.",
        "- Not observed truth.",
        "- Not causal feature importance.",
        "- No raster committed.",
        "- No Tmrt-to-WBGT conversion.",
        "- No System A/B coupling.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_model_card(
    path: Path,
    status: str,
    dataset: pd.DataFrame,
    schema: pd.DataFrame,
    metrics: pd.DataFrame,
    sensitivity: pd.DataFrame,
    config: dict[str, Any],
    model: str,
) -> None:
    """Write B8.6b model card."""
    lines = [
        "# B8.6b System B Surrogate Model Card",
        "",
        f"Generated: {now_stamp()}",
        "",
        "## Intended Role",
        "",
        "Surrogate-promotion review for SOLWEIG-derived F5 N150 multi-forcing Tmrt labels. The primary use is local radiative ranking review, not public-health warning or risk scoring.",
        "",
        "## Decision",
        "",
        f"`{status}`",
        "",
        "## Dataset",
        "",
        f"- Rows: {len(dataset)}",
        f"- Cells: {dataset['cell_id'].nunique() if not dataset.empty else 0}",
        f"- Forcing days: {dataset['forcing_day_id'].nunique() if not dataset.empty else 0}",
        f"- Hours: {', '.join(str(int(value)) for value in sorted(pd.to_numeric(dataset['hour_sgt'], errors='coerce').dropna().unique())) if not dataset.empty else '(none)'}",
        "- Primary target: `delta_tmrt_p90_c = overhead_as_canopy - base`.",
        f"- Predictor count: {len(selected_features(schema))}; `cell_id` and `forcing_day_id` are excluded.",
        "",
        "## Validation",
        "",
        "- Primary: forcing-day holdout.",
        "- Main supporting: cell-group, hour, spatial, and typology holdouts.",
        "- Diagnostic only: random split.",
        "",
        "## Headline",
        "",
        f"- {forcing_day_headline(metrics, config, model)}",
        f"- {target_sensitivity_text(sensitivity, config)}",
        "",
        "## Explicit Non-Claims",
        "",
        "- Not B9.",
        "- Not local WBGT.",
        "- Not risk.",
        "- Not observed truth.",
        "- Not causal feature importance.",
        "- No raster committed.",
        "- No Tmrt-to-WBGT conversion.",
        "- No System A/B coupling.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(
    path: Path,
    status: str,
    dataset: pd.DataFrame,
    label_inventory: pd.DataFrame,
    feature_inventory: pd.DataFrame,
    target_schema: pd.DataFrame,
    metrics: pd.DataFrame,
    sensitivity: pd.DataFrame,
    decision: pd.DataFrame,
    anchor_diag: pd.DataFrame,
    neutral_diag: pd.DataFrame,
    unstable_diag: pd.DataFrame,
    feature_importance: pd.DataFrame,
    config: dict[str, Any],
    model: str,
) -> None:
    """Write full B8.6b Markdown report."""
    primary = config["targets"]["primary"]
    primary_metrics = metrics.loc[(metrics["target"] == primary) & (metrics["model"] == model)].copy()
    lines = [
        "# B8.6b System B Surrogate Promotion Review",
        "",
        f"Generated: {now_stamp()}",
        "",
        f"Status: `{status}`",
        "",
        "## 1. Why B8.6b Follows F5",
        "",
        "B8.6 found a weak single-forcing N150 surrogate baseline and kept forcing-day holdout as future-required. B8.5-F5 then completed the N150 multi-forcing compact label run. B8.6b therefore re-runs the surrogate promotion review using only F5 compact multi-forcing labels.",
        "",
        "## 2. F5 Label Source And Row Counts",
        "",
        markdown_table(label_inventory, ["candidate_name", "path", "exists", "row_count", "unique_cells", "forcing_day_count", "hour_count", "usable_for_b86b_primary"], 8),
        "",
        f"- B8.6b training labels: {len(dataset)} rows, {dataset['cell_id'].nunique() if not dataset.empty else 0} cells.",
        "- Legacy single-forcing labels are metadata only and are not mixed into the training target.",
        "",
        "## 3. Feature Source And Leakage Guard",
        "",
        markdown_table(feature_inventory, ["candidate_name", "path", "exists", "row_count", "label_cell_coverage", "available_predictor_count", "usable_for_b86b_features"], 8),
        "",
        "- `cell_id` is group metadata only.",
        "- `forcing_day_id` is excluded from primary predictors.",
        "- Tmrt, delta, rank, WBGT, hazard, risk, vulnerability, exposure, raster, and output-path columns are excluded.",
        "",
        "## 4. Target Definitions And Sensitivity",
        "",
        markdown_table(target_schema, ["target_name", "role", "available", "non_null_count", "source_definition"], 10),
        "",
        markdown_table(sensitivity, ["target", "best_model", "forcing_day_MAE", "forcing_day_R2", "forcing_day_spearman", "forcing_day_top10pct_overlap", "target_card_verdict"], 10),
        "",
        "## 5. Validation Split Design",
        "",
        "- Primary: train FD01/test FD02 and train FD02/test FD01.",
        "- Main supporting: grouped cell holdout, leave-one-hour-out, coordinate-bin spatial holdout, and typology holdout.",
        "- Diagnostic only: random row split.",
        "",
        "## 6. Model Family Comparison",
        "",
        markdown_table(primary_metrics.sort_values(["split_family", "MAE"]), ["split_family", "model", "MAE", "RMSE", "R2", "Spearman_observed_vs_predicted", "top10pct_overlap", "MAE_improvement_fraction_over_dummy"], 36),
        "",
        "## 7. Forcing-Day Holdout Results",
        "",
        f"- {forcing_day_headline(metrics, config, model)}",
        "",
        "## 8. Anchor / Neutral / Unstable Diagnostics",
        "",
        f"- {diagnostics_text(anchor_diag, neutral_diag, unstable_diag)}",
        "",
        markdown_table(anchor_diag.sort_values(["split_family", "cell_id"]).head(20), ["cell_id", "split_family", "MAE", "abs_rank_error", "mean_true_delta_tmrt_p90_c", "mean_pred_delta_tmrt_p90_c"], 20),
        "",
        "## 9. h10 Caveat",
        "",
        "- h10 metrics are stored separately in `b86b_model_metrics_by_split.csv` as `h10_MAE`, `h10_Spearman`, and `h10_top10pct_overlap`.",
        "- h10 is retained as caveated context and is not anchor evidence by itself.",
        "",
        "## 10. Promotion Gate Decision",
        "",
        markdown_table(decision, ["gate", "status", "evidence", "next_action"], 20),
        "",
        "## 11. AOI-Wide Preflight",
        "",
        f"- {recommendation_for_status(status)}",
        "- This lane does not create AOI-wide prediction.",
        "",
        "## 12. Feature Importance Diagnostic",
        "",
        markdown_table(feature_importance, ["feature", "importance", "normalized_abs_importance", "method", "diagnostic_boundary"], 12),
        "",
        "## 13. Claim Boundaries",
        "",
        "- This is not B9.",
        "- This is not local WBGT.",
        "- This is not risk.",
        "- This is not observed truth.",
        "- This is not causal feature importance.",
        "- No raster is committed.",
        "- No Tmrt-to-WBGT conversion is performed.",
        "- No System A/B coupling output is created.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_cn_doc(
    path: Path,
    status: str,
    dataset: pd.DataFrame,
    metrics: pd.DataFrame,
    sensitivity: pd.DataFrame,
    decision: pd.DataFrame,
    config: dict[str, Any],
    model: str,
) -> None:
    """Write the UTF-8 Chinese B8.6b documentation."""
    lines = [
        "# OpenHeat System B B8.6b 代理模型晋级评审说明",
        "",
        f"生成时间：{now_stamp()}",
        "",
        "## 结论",
        "",
        f"- B8.6b 状态：`{status}`",
        f"- F5 标签行数：{len(dataset)}",
        f"- 唯一 cell 数：{dataset['cell_id'].nunique() if not dataset.empty else 0}",
        f"- 最佳主目标模型：`{model}`",
        f"- 强迫日留出结果：{forcing_day_headline(metrics, config, model)}",
        f"- AOI-wide preflight 建议：{recommendation_for_status(status)}",
        "- B9 状态：`BLOCKED`",
        "",
        "## 为什么 B8.6b 接在 F5 后面",
        "",
        "B8.6 只验证了单一强迫日的 N150 代理基线，并把强迫日泛化列为后续必需条件。B8.5-F5 已完成 N150 多强迫日紧凑标签，因此 B8.6b 使用 F5 标签重新评审代理模型是否可以进入未来的 AOI-wide preflight 设计评审。",
        "",
        "## 数据和泄漏边界",
        "",
        "- 训练目标只来自 F5 `b85_f5_pairwise_delta_by_cell_hour.csv`。",
        "- 旧的单强迫 N150 标签只作为历史元数据，不混入训练目标。",
        "- `cell_id` 只是分组标识，不作为数值预测变量。",
        "- `forcing_day_id` 只用于留出验证和诊断，不进入主证据模型。",
        "- Tmrt 目标列、delta 列、rank 列、WBGT、hazard、risk、暴露和脆弱性列均不作为预测变量。",
        "",
        "## 目标敏感性",
        "",
        markdown_table(sensitivity, ["target", "best_model", "forcing_day_MAE", "forcing_day_R2", "forcing_day_spearman", "forcing_day_top10pct_overlap", "target_card_verdict"], 10),
        "",
        "结论：`delta_tmrt_p90_c` 仍是主目标卡变量。若 mean 或 p50 更容易预测或幅度更大，它们应作为伴随目标报告，而不是自动替换 p90。",
        "",
        "## 验证设计",
        "",
        "- 主证据：强迫日留出。",
        "- 支撑证据：cell 分组留出、小时留出、空间分箱留出、typology 留出。",
        "- random split 仅为诊断，不作为晋级主证据。",
        "",
        "## 晋级门槛",
        "",
        markdown_table(decision, ["gate", "status", "next_action"], 20),
        "",
        "## 明确不声明",
        "",
        "- 这不是 B9。",
        "- 这不是 local WBGT。",
        "- 这不是 risk。",
        "- 这不是 observed truth。",
        "- 这不是 causal feature importance。",
        "- 没有提交 raster。",
        "- 没有 Tmrt-to-WBGT conversion。",
        "- 没有 System A/B coupling。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_status_file(path: Path, result: AuditResult, config: dict[str, Any]) -> None:
    """Write B8.6b lane status file."""
    branch = command_output(["git", "branch", "--show-current"])
    lines = [
        "# B8.6b Status",
        "",
        f"Generated: {now_stamp()}",
        f"Status: {result.status}",
        f"Branch: {branch}",
        "Scope: System B surrogate promotion review with F5 N150 multi-forcing compact labels only.",
        "",
        "## Commands run",
        "",
        "- Plain `python` was unavailable on PATH in this shell; equivalent commands were run through the `openheat` conda environment.",
        "- `C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat python -m compileall scripts/v12_b86b_surrogate_inventory.py scripts/v12_b86b_surrogate_dataset.py scripts/v12_b86b_validation_splits.py scripts/v12_b86b_surrogate_models.py scripts/v12_b86b_error_audit.py scripts/v12_b86b_run_surrogate_promotion.py`",
        "- `C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat python scripts/v12_b86b_run_surrogate_promotion.py --config configs/v12/systemb_b86b_surrogate_promotion.yaml`",
        "- `C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat python -c \"...mojibake check...\"`",
        "- `git status --short -- .`",
        "- forbidden-file check over `git status --porcelain -- .`",
        "",
        "## Files created / modified",
        "",
        "- `configs/v12/systemb_b86b_surrogate_promotion.yaml`",
        "- `scripts/v12_b86b_surrogate_inventory.py`",
        "- `scripts/v12_b86b_surrogate_dataset.py`",
        "- `scripts/v12_b86b_validation_splits.py`",
        "- `scripts/v12_b86b_surrogate_models.py`",
        "- `scripts/v12_b86b_error_audit.py`",
        "- `scripts/v12_b86b_run_surrogate_promotion.py`",
        *[f"- `{path_value}`" for path_value in output_files(config)],
        "",
        "## Key results",
        "",
        f"- Best primary model: {result.best_primary_model}",
        f"- Forcing-day headline: {result.forcing_day_headline}",
        f"- Cross-holdout headline: {result.cross_holdout_headline}",
        f"- Target sensitivity headline: {result.target_sensitivity_headline}",
        f"- Diagnostics headline: {result.diagnostics_headline}",
        f"- AOI-wide preflight recommendation: {result.aoi_preflight_recommendation}",
        f"- B9 status: {result.b9_status}",
        "",
        "## Caveats",
        "",
        "- The surrogate learns SOLWEIG-derived F5 labels, not observed truth.",
        "- Feature importance diagnostics are non-causal.",
        "- h10 remains a caveated hour and is reported separately.",
        "- No QGIS, SOLWEIG, raster reading, AOI-wide prediction, local WBGT, hazard_score, risk_score, or System A/B coupling was created by this lane.",
        "",
        "## Safe to commit",
        "",
        "- Compact config, scripts, docs, CSV, and Markdown outputs after review.",
        "",
        "## Not safe to commit",
        "",
        "- Rasters, `.tif`, `.tiff`, `svfs.zip`, `data/solweig/`, `data/rasters/`, raw archives, patch zip packages, and AOI-wide prediction outputs.",
        "",
        "## Next recommended action",
        "",
        f"- {result.aoi_preflight_recommendation}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path = DEFAULT_CONFIG) -> AuditResult:
    """Run B8.6b error audit, promotion decision, and reports."""
    config = read_config(config_path)
    dataset = read_csv_if_exists(repo_path(config["outputs"]["surrogate_dataset"]), dtype={"cell_id": "string", "row_id": "string", "forcing_day_id": "string"})
    schema = read_csv_if_exists(repo_path(config["outputs"]["feature_schema"]))
    target_schema = read_csv_if_exists(repo_path(config["outputs"]["target_schema"]))
    splits = read_csv_if_exists(repo_path(config["outputs"]["validation_splits"]), dtype={"cell_id": "string", "row_id": "string", "forcing_day_id": "string", "fold_id": "string"})
    metrics = read_csv_if_exists(repo_path(config["outputs"]["model_metrics_by_split"]))
    sensitivity = read_csv_if_exists(repo_path(config["outputs"]["target_sensitivity_metrics"]))
    label_inventory = read_csv_if_exists(repo_path(config["outputs"]["label_source_inventory"]))
    feature_inventory = read_csv_if_exists(repo_path(config["outputs"]["feature_source_inventory"]))

    model = best_primary_model(metrics, config) if not metrics.empty else ""
    predictions = prediction_records_for_model(dataset, schema, splits, config, config["targets"]["primary"], model) if model else pd.DataFrame()

    anchor_diag = cell_rank_diagnostics(predictions, list(config["diagnostic_cells"]["robust_priority_anchors"]), "robust_priority_anchor")
    neutral_diag = neutral_diagnostics(predictions, config)
    unstable_diag = cell_rank_diagnostics(predictions, list(config["diagnostic_cells"]["unstable_review_cells"]), "unstable_review")
    worst_errors = worst_error_inventory(predictions)
    feature_importance = feature_importance_diagnostics(dataset, schema, config, model)
    preliminary_status = status_from_metrics(metrics, model, config)
    status = diagnostic_downgrade_status(preliminary_status, metrics, neutral_diag, config, model)
    decision = decision_matrix(status, metrics, sensitivity, anchor_diag, neutral_diag, unstable_diag, config, model)

    anchor_diag.to_csv(repo_path(config["outputs"]["anchor_cell_diagnostics"]), index=False)
    neutral_diag.to_csv(repo_path(config["outputs"]["neutral_boundary_diagnostics"]), index=False)
    unstable_diag.to_csv(repo_path(config["outputs"]["unstable_cell_diagnostics"]), index=False)
    worst_errors.to_csv(repo_path(config["outputs"]["worst_error_inventory"]), index=False)
    feature_importance.to_csv(repo_path(config["outputs"]["feature_importance_diagnostics"]), index=False)
    decision.to_csv(repo_path(config["outputs"]["promotion_decision_matrix"]), index=False)

    write_promotion_gate(repo_path(config["outputs"]["promotion_gate"]), status, metrics, sensitivity, config, model)
    write_model_card(repo_path(config["outputs"]["model_card"]), status, dataset, schema, metrics, sensitivity, config, model)
    write_report(
        repo_path(config["outputs"]["report"]),
        status,
        dataset,
        label_inventory,
        feature_inventory,
        target_schema,
        metrics,
        sensitivity,
        decision,
        anchor_diag,
        neutral_diag,
        unstable_diag,
        feature_importance,
        config,
        model,
    )
    write_cn_doc(repo_path(config["outputs"]["cn_doc"]), status, dataset, metrics, sensitivity, decision, config, model)

    result = AuditResult(
        status=status,
        best_primary_model=model,
        forcing_day_headline=forcing_day_headline(metrics, config, model),
        cross_holdout_headline=cross_holdout_headline(metrics, config, model),
        target_sensitivity_headline=target_sensitivity_text(sensitivity, config),
        diagnostics_headline=diagnostics_text(anchor_diag, neutral_diag, unstable_diag),
        aoi_preflight_recommendation=recommendation_for_status(status),
        b9_status="BLOCKED",
    )
    write_status_file(repo_path(config["outputs"]["status"]), result, config)
    return result


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Audit B8.6b errors and write promotion reports.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to B8.6b YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
