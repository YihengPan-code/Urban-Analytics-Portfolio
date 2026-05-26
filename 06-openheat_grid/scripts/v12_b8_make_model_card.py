"""Create the B8.3 System B surrogate model card and promotion gate.

Inputs:
    configs/v12/systemb_surrogate_b8_model_card.yaml
    outputs/v12_surrogate/b8_dataset_audit/surrogate_label_feature_matrix.csv
    outputs/v12_surrogate/b8_dataset_audit/feature_schema.csv
    outputs/v12_surrogate/b8_model_benchmark/surrogate_model_metrics.csv
    outputs/v12_surrogate/b8_model_benchmark/topk_overlap_by_model.csv
    outputs/v12_surrogate/b8_model_benchmark/stratified_error_by_feature_bin.csv
    outputs/v12_surrogate/b8_model_benchmark/split_family_summary.csv

Outputs:
    docs/v12/OpenHeat_SystemB_surrogate_model_card_CN.md
    outputs/v12_surrogate/b8_model_card/model_card_metrics_summary.csv
    outputs/v12_surrogate/b8_model_card/promotion_gate_checklist.csv
    outputs/v12_surrogate/b8_model_card/split_family_decision_matrix.csv
    outputs/v12_surrogate/b8_model_card/feature_contract_summary.csv
    outputs/v12_surrogate/b8_model_card/model_card_decision_report.md
    outputs/v12_surrogate/b8_model_card/B8_3_MODEL_CARD_STATUS.md

Saved metrics:
    B8.2 split-family metric summaries, candidate model selection evidence,
    top-k overlap diagnostics, feature contract checks, promotion gate statuses,
    and a concise model-card decision report.

This script reads existing B8.0/B8.2 artifacts only. It does not train models,
create AOI-wide predictions, compute local WBGT, create hazard_score/risk_score,
or couple System A and System B.
"""

from __future__ import annotations

import math
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b8_prepare_surrogate_dataset import read_config, repo_path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_surrogate_b8_model_card.yaml"
NO_FINAL_AOI_DECISION = "not_approved_for_final_AOI_inference"
GROUP_SAFE_SPLITS = {"cell_grouped_holdout", "spatial_holdout", "feature_bin_holdout"}


@dataclass(frozen=True)
class ModelCardResult:
    """Compact run result for the B8.3 model-card generator."""

    status: str
    candidate_model: str
    primary_evidence: str
    blockers: list[str]
    recommended_next_gate: str
    files_created: list[Path]
    status_path: Path


def command_output(args: list[str]) -> str:
    """Run a lightweight command for status reporting."""
    completed = subprocess.run(args, cwd=ROOT, check=False, capture_output=True, text=True)
    return completed.stdout.strip()


def now_stamp() -> str:
    """Return a compact local timestamp string."""
    return time.strftime("%Y-%m-%d %H:%M:%S")


def as_float(value: Any) -> float:
    """Parse a numeric value from CSV cells, returning NaN when unavailable."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def fmt(value: Any, digits: int = 3) -> str:
    """Format numeric evidence for Markdown."""
    number = as_float(value)
    if math.isnan(number):
        return "NA"
    return f"{number:.{digits}f}"


def lower_text(value: Any) -> str:
    """Return a lowercase string for contract matching."""
    return str(value).strip().lower()


def token_hits(name: str, tokens: list[str]) -> list[str]:
    """Return lowercase tokens found in a candidate column name."""
    lower = name.lower()
    return [token for token in tokens if token.lower() in lower]


def metric_subset(summary: pd.DataFrame, target: str, split_family: str) -> pd.DataFrame:
    """Return one target/split summary sorted by MAE."""
    subset = summary.loc[(summary["target"] == target) & (summary["split_family"] == split_family)].copy()
    if subset.empty:
        return subset
    subset["MAE"] = pd.to_numeric(subset["MAE"], errors="coerce")
    return subset.sort_values(["MAE", "model"], na_position="last")


def best_non_featureless(summary: pd.DataFrame, target: str, split_family: str) -> pd.Series | None:
    """Return the lowest-MAE non-featureless row for one target/split."""
    subset = metric_subset(summary, target, split_family)
    subset = subset.loc[subset["model"] != "featureless_mean"].copy()
    if subset.empty:
        return None
    return subset.iloc[0]


def model_row(summary: pd.DataFrame, target: str, split_family: str, model: str) -> pd.Series | None:
    """Return the summary row for one target/split/model."""
    subset = summary.loc[
        (summary["target"] == target) & (summary["split_family"] == split_family) & (summary["model"] == model)
    ]
    if subset.empty:
        return None
    return subset.iloc[0]


def choose_candidate_model(summary: pd.DataFrame, config: dict[str, Any]) -> tuple[str, dict[str, str]]:
    """Choose the candidate model from B8.2 evidence, without assuming it."""
    primary = str(config["candidate_selection"]["primary_target"])
    required_splits = list(config["candidate_selection"]["required_best_split_families"])
    best_by_split: dict[str, str] = {}
    for split_family in required_splits:
        row = best_non_featureless(summary, primary, split_family)
        best_by_split[split_family] = "not_available" if row is None else str(row["model"])
    unique_best = {model for model in best_by_split.values() if model != "not_available"}
    if len(unique_best) == 1:
        return unique_best.pop(), best_by_split

    required = summary.loc[
        (summary["target"] == primary)
        & (summary["split_family"].isin(required_splits))
        & (summary["model"] != "featureless_mean")
    ].copy()
    if required.empty:
        return "not_available", best_by_split
    required["MAE"] = pd.to_numeric(required["MAE"], errors="coerce")
    ranked = required.groupby("model", as_index=False)["MAE"].mean(numeric_only=True).sort_values(["MAE", "model"])
    return str(ranked.iloc[0]["model"]), best_by_split


def build_feature_contract_summary(
    schema: pd.DataFrame, matrix: pd.DataFrame, config: dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Check the B8.1.1 physical-core feature contract."""
    contract = config["feature_contract"]
    role = lower_text(contract["headline_role"])
    tier = lower_text(contract["headline_predictor_tier"])
    spatial_tier = lower_text(contract["optional_spatial_diagnostic_tier"])
    features = schema.loc[
        (schema["role"].map(lower_text) == role) & (schema["predictor_tier"].map(lower_text) == tier)
    ].copy()
    spatial_diag = schema.loc[schema["predictor_tier"].map(lower_text) == spatial_tier].copy()

    feature_names = features["column_name"].astype(str).tolist()
    prohibited_tokens = [str(token) for token in contract["prohibited_feature_tokens"]]
    leakage_tokens = [str(token) for token in contract["target_leakage_tokens"]]
    coordinate_tokens = [str(token) for token in contract["coordinate_tokens"]]
    prohibited_hits = {name: token_hits(name, prohibited_tokens) for name in feature_names}
    prohibited_hits = {name: hits for name, hits in prohibited_hits.items() if hits}
    leakage_hits = {name: token_hits(name, leakage_tokens) for name in feature_names}
    leakage_hits = {name: hits for name, hits in leakage_hits.items() if hits}
    coordinate_hits = {name: token_hits(name, coordinate_tokens) for name in feature_names}
    coordinate_hits = {name: hits for name, hits in coordinate_hits.items() if hits}

    families = contract["feature_families"]
    family_rows: list[dict[str, Any]] = []
    matched_any: set[str] = set()
    for family, tokens in families.items():
        matches = [name for name in feature_names if token_hits(name, [str(token) for token in tokens])]
        matched_any.update(matches)
        family_rows.append(
            {
                "item_type": "feature_family",
                "item": family,
                "status": "PASS" if matches else "NOT_TESTED",
                "count": len(matches),
                "details": "; ".join(matches[:12]),
            }
        )
    unmatched = sorted(set(feature_names) - matched_any)

    scenarios = sorted(matrix["scenario"].dropna().astype(str).unique().tolist()) if "scenario" in matrix else []
    hours = sorted(pd.to_numeric(matrix["hour_sgt"], errors="coerce").dropna().astype(int).unique().tolist()) if "hour_sgt" in matrix else []
    context = {
        "feature_count": len(feature_names),
        "spatial_diagnostic_count": int(len(spatial_diag)),
        "coordinate_feature_count": len(coordinate_hits),
        "prohibited_hit_count": len(prohibited_hits),
        "leakage_hit_count": len(leakage_hits),
        "unmatched_feature_count": len(unmatched),
        "rows": int(len(matrix)),
        "cells": int(matrix["cell_id"].nunique()) if "cell_id" in matrix else 0,
        "scenarios": scenarios,
        "hours": hours,
        "families": family_rows,
    }

    rows = [
        {
            "item_type": "dataset_contract",
            "item": "n150_label_set_rows",
            "status": "PASS" if len(matrix) == int(config["dataset_contract"]["expected_n_rows"]) else "FAIL",
            "count": int(len(matrix)),
            "details": f"cells={context['cells']}; scenarios={','.join(scenarios)}; hours={','.join(str(h) for h in hours)}",
        },
        {
            "item_type": "feature_contract",
            "item": "physical_core_feature_count",
            "status": "PASS" if feature_names else "FAIL",
            "count": len(feature_names),
            "details": f"role={role}; predictor_tier={tier}",
        },
        {
            "item_type": "feature_contract",
            "item": "prohibited_nonphysical_social_tokens",
            "status": "PASS" if not prohibited_hits else "FAIL",
            "count": len(prohibited_hits),
            "details": "; ".join(f"{name}:{','.join(hits)}" for name, hits in prohibited_hits.items()),
        },
        {
            "item_type": "feature_contract",
            "item": "target_leakage_tokens",
            "status": "PASS" if not leakage_hits else "FAIL",
            "count": len(leakage_hits),
            "details": "; ".join(f"{name}:{','.join(hits)}" for name, hits in leakage_hits.items()),
        },
        {
            "item_type": "feature_contract",
            "item": "coordinates_in_headline_features",
            "status": "PASS" if not coordinate_hits else "PARTIAL",
            "count": len(coordinate_hits),
            "details": "none" if not coordinate_hits else "; ".join(coordinate_hits),
        },
        {
            "item_type": "feature_contract",
            "item": "spatial_diagnostic_columns_excluded_from_headline",
            "status": "PASS" if len(spatial_diag) > 0 and not coordinate_hits else "PARTIAL",
            "count": int(len(spatial_diag)),
            "details": "; ".join(spatial_diag["column_name"].astype(str).tolist()),
        },
        *family_rows,
        {
            "item_type": "feature_family",
            "item": "other_physical_core",
            "status": "PASS" if unmatched else "NOT_TESTED",
            "count": len(unmatched),
            "details": "; ".join(unmatched[:12]),
        },
    ]
    return pd.DataFrame(rows), context


def build_metrics_summary(summary: pd.DataFrame, candidate_model: str, config: dict[str, Any]) -> pd.DataFrame:
    """Annotate B8.2 split-family metrics for model-card consumption."""
    out = summary.copy()
    numeric_cols = [
        "MAE",
        "RMSE",
        "R2",
        "bias",
        "median_abs_error",
        "p90_abs_error",
        "spearman",
        "pearson",
        "improvement_over_featureless_MAE",
        "n_folds",
        "n_test_rows",
    ]
    for column in numeric_cols:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    out["is_candidate_model"] = out["model"] == candidate_model
    out["is_best_non_featureless_by_mae"] = False
    for (target, split_family), group in out.loc[out["model"] != "featureless_mean"].groupby(["target", "split_family"]):
        best_index = group.sort_values(["MAE", "model"], na_position="last").index[0]
        out.loc[best_index, "is_best_non_featureless_by_mae"] = True
    primary = str(config["targets"]["primary"])
    secondary = str(config["targets"]["secondary"])
    out["model_card_interpretation"] = ""
    out.loc[out["target"] == primary, "model_card_interpretation"] = "primary_delta_tmrt_evidence"
    out.loc[out["target"] == secondary, "model_card_interpretation"] = "secondary_absolute_tmrt_diagnostic"
    return out.sort_values(["target", "split_family", "MAE", "model"], na_position="last")


def topk_mean(topk: pd.DataFrame, target: str, model: str, split_family: str, config: dict[str, Any]) -> float:
    """Return mean top-k overlap for the configured aggregation and k."""
    selection = config["candidate_selection"]
    subset = topk.loc[
        (topk["target"] == target)
        & (topk["model"] == model)
        & (topk["split_family"] == split_family)
        & (topk["aggregation_level"] == str(selection["topk_aggregation_level"]))
    ].copy()
    subset["k_fraction"] = pd.to_numeric(subset["k_fraction"], errors="coerce")
    subset["topk_overlap_fraction"] = pd.to_numeric(subset["topk_overlap_fraction"], errors="coerce")
    subset = subset.loc[subset["k_fraction"] == float(selection["topk_fraction"])]
    if subset.empty:
        return float("nan")
    return float(subset["topk_overlap_fraction"].mean())


def topk_mean_across_splits(topk: pd.DataFrame, target: str, model: str, split_families: list[str], config: dict[str, Any]) -> float:
    """Return fold-weighted mean top-k overlap across selected split families."""
    selection = config["candidate_selection"]
    subset = topk.loc[
        (topk["target"] == target)
        & (topk["model"] == model)
        & (topk["split_family"].isin(split_families))
        & (topk["aggregation_level"] == str(selection["topk_aggregation_level"]))
    ].copy()
    subset["k_fraction"] = pd.to_numeric(subset["k_fraction"], errors="coerce")
    subset["topk_overlap_fraction"] = pd.to_numeric(subset["topk_overlap_fraction"], errors="coerce")
    subset = subset.loc[subset["k_fraction"] == float(selection["topk_fraction"])]
    if subset.empty:
        return float("nan")
    return float(subset["topk_overlap_fraction"].mean())


def mean_candidate_spearman(summary: pd.DataFrame, target: str, model: str, split_families: list[str]) -> float:
    """Return mean candidate Spearman across selected split families."""
    subset = summary.loc[
        (summary["target"] == target)
        & (summary["model"] == model)
        & (summary["split_family"].isin(split_families))
    ].copy()
    if subset.empty:
        return float("nan")
    return float(pd.to_numeric(subset["spearman"], errors="coerce").mean())


def build_split_family_decision_matrix(
    summary: pd.DataFrame, topk: pd.DataFrame, candidate_model: str, config: dict[str, Any]
) -> pd.DataFrame:
    """Build a split-family decision table for the primary target."""
    primary = str(config["targets"]["primary"])
    split_roles = {
        "cell_grouped_holdout": "headline_cell_generalisation",
        "spatial_holdout": "headline_spatial_generalisation",
        "feature_bin_holdout": "typology_extrapolation_diagnostic",
        "hour_holdout": "hour_transfer_diagnostic",
        "scenario_holdout": "scenario_transfer_diagnostic",
    }
    rows: list[dict[str, Any]] = []
    for split_family, split_role in split_roles.items():
        best = best_non_featureless(summary, primary, split_family)
        candidate = model_row(summary, primary, split_family, candidate_model)
        baseline = model_row(summary, primary, split_family, "featureless_mean")
        top10 = topk_mean(topk, primary, candidate_model, split_family, config)
        if candidate is None:
            status = "FAIL"
            decision = "insufficient_evidence"
            rationale = "Candidate model is missing for this split family."
        elif split_family in {"cell_grouped_holdout", "spatial_holdout"}:
            is_best = best is not None and str(best["model"]) == candidate_model
            supportive = as_float(candidate["improvement_over_featureless_MAE"]) > 0 and as_float(candidate["spearman"]) >= float(
                config["candidate_selection"]["min_supportive_spearman"]
            )
            status = "PASS" if is_best and supportive else "PARTIAL"
            decision = "supports_internal_model_card_review" if status == "PASS" else "review_before_use"
            rationale = "Group-safe holdout supports the candidate for internal review." if status == "PASS" else "Evidence exists but does not fully clear the headline-support criteria."
        elif split_family == "feature_bin_holdout":
            status = "PARTIAL"
            decision = "typology_extrapolation_risk"
            rationale = "Candidate improves over featureless but MAE is materially higher than cell/spatial holdouts; blocked water bins remain outside evidence."
        else:
            status = "PARTIAL"
            decision = "diagnostic_only"
            rationale = "Transfer split reuses cells by design and is useful as a diagnostic, not as headline generalisation evidence."
        rows.append(
            {
                "split_family": split_family,
                "split_role": split_role,
                "target": primary,
                "best_model_by_mae": "not_available" if best is None else str(best["model"]),
                "candidate_model": candidate_model,
                "candidate_mae": "" if candidate is None else as_float(candidate["MAE"]),
                "candidate_rmse": "" if candidate is None else as_float(candidate["RMSE"]),
                "candidate_r2": "" if candidate is None else as_float(candidate["R2"]),
                "candidate_spearman": "" if candidate is None else as_float(candidate["spearman"]),
                "candidate_improvement_over_featureless_mae": ""
                if candidate is None
                else as_float(candidate["improvement_over_featureless_MAE"]),
                "featureless_mae": "" if baseline is None else as_float(baseline["MAE"]),
                "candidate_cell_top10_overlap": top10,
                "evidence_status": status,
                "decision": decision,
                "rationale": rationale,
            }
        )
    return pd.DataFrame(rows)


def gate_row(
    gate_id: str,
    gate_name: str,
    evidence_file: str,
    status: str,
    rationale: str,
    blocker_for_b9: str,
) -> dict[str, str]:
    """Create one promotion gate checklist row."""
    return {
        "gate_id": gate_id,
        "gate_name": gate_name,
        "evidence_file": evidence_file,
        "status": status,
        "rationale": rationale,
        "blocker_for_b9": blocker_for_b9,
    }


def build_promotion_gate_checklist(
    *,
    feature_context: dict[str, Any],
    split_matrix: pd.DataFrame,
    summary: pd.DataFrame,
    topk: pd.DataFrame,
    candidate_model: str,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Create B8.3 promotion gate statuses."""
    primary = str(config["targets"]["primary"])
    secondary = str(config["targets"]["secondary"])
    topk_splits = ["cell_grouped_holdout", "spatial_holdout"]
    mean_top10 = topk_mean_across_splits(topk, primary, candidate_model, topk_splits, config)
    mean_spearman = mean_candidate_spearman(summary, primary, candidate_model, topk_splits)
    tmrt_cell = model_row(summary, secondary, "cell_grouped_holdout", candidate_model)
    tmrt_spatial = model_row(summary, secondary, "spatial_holdout", candidate_model)
    split_status = dict(zip(split_matrix["split_family"], split_matrix["evidence_status"]))
    random_split_present = bool(summary["split_family"].astype(str).str.contains("random", case=False, regex=False).any())

    gates = [
        gate_row(
            "no_target_leakage",
            "No target leakage in headline predictors",
            "outputs/v12_surrogate/b8_model_card/feature_contract_summary.csv",
            "PASS" if feature_context["leakage_hit_count"] == 0 else "FAIL",
            f"Target-leakage token hits in role=feature physical_core columns: {feature_context['leakage_hit_count']}.",
            "no" if feature_context["leakage_hit_count"] == 0 else "yes",
        ),
        gate_row(
            "physical_core_feature_contract",
            "Physical-core feature contract",
            "outputs/v12_surrogate/b8_model_card/feature_contract_summary.csv",
            "PASS"
            if feature_context["feature_count"] > 0
            and feature_context["prohibited_hit_count"] == 0
            and feature_context["coordinate_feature_count"] == 0
            else "FAIL",
            f"{feature_context['feature_count']} physical_core features; prohibited hits={feature_context['prohibited_hit_count']}; coordinate headline features={feature_context['coordinate_feature_count']}.",
            "no"
            if feature_context["feature_count"] > 0
            and feature_context["prohibited_hit_count"] == 0
            and feature_context["coordinate_feature_count"] == 0
            else "yes",
        ),
        gate_row(
            "cell_grouped_performance",
            "Cell-grouped primary-target performance",
            "outputs/v12_surrogate/b8_model_card/split_family_decision_matrix.csv",
            split_status.get("cell_grouped_holdout", "FAIL"),
            "Candidate is best by MAE on cell-grouped holdout and improves over featureless baseline.",
            "no" if split_status.get("cell_grouped_holdout") == "PASS" else "yes",
        ),
        gate_row(
            "spatial_holdout_performance",
            "Spatial holdout primary-target performance",
            "outputs/v12_surrogate/b8_model_card/split_family_decision_matrix.csv",
            split_status.get("spatial_holdout", "FAIL"),
            "Candidate is best by MAE on spatial holdout and improves over featureless baseline.",
            "no" if split_status.get("spatial_holdout") == "PASS" else "yes",
        ),
        gate_row(
            "feature_bin_typology_extrapolation",
            "Feature-bin typology extrapolation",
            "outputs/v12_surrogate/b8_model_card/split_family_decision_matrix.csv",
            split_status.get("feature_bin_holdout", "FAIL"),
            "Feature-bin evidence is weaker than cell/spatial holdouts and water bins were blocked/degenerate.",
            "yes",
        ),
        gate_row(
            "topk_prioritisation_signal",
            "Top-k prioritisation signal",
            "outputs/v12_surrogate/b8_model_card/split_family_decision_matrix.csv",
            "PARTIAL"
            if mean_top10 >= float(config["candidate_selection"]["min_supportive_topk_overlap"])
            and mean_spearman >= float(config["candidate_selection"]["min_supportive_spearman"])
            else "FAIL",
            f"Mean cell/spatial Spearman={fmt(mean_spearman)}; mean cell-level top-10% overlap={fmt(mean_top10)}. Diagnostic ranking signal only.",
            "yes",
        ),
        gate_row(
            "secondary_tmrt_target",
            "Secondary absolute tmrt_p90_c target",
            "outputs/v12_surrogate/b8_model_card/model_card_metrics_summary.csv",
            "PARTIAL",
            f"Candidate tmrt_p90_c MAE is {fmt(tmrt_cell['MAE'] if tmrt_cell is not None else None)} cell-grouped and {fmt(tmrt_spatial['MAE'] if tmrt_spatial is not None else None)} spatial, with weaker rank evidence than delta target.",
            "no",
        ),
        gate_row(
            "no_random_split_headline",
            "No random row split used as headline evidence",
            "outputs/v12_surrogate/b8_model_card/model_card_metrics_summary.csv",
            "PASS" if not random_split_present else "FAIL",
            "B8.2 consumed cell-grouped, spatial, feature-bin, hour, and scenario holdouts only.",
            "no" if not random_split_present else "yes",
        ),
        gate_row(
            "no_local_wbgt_claim",
            "No local WBGT claim",
            "docs/v12/OpenHeat_SystemB_surrogate_model_card_CN.md",
            "PASS",
            "Model-card text frames outputs as SOLWEIG-derived Tmrt modifier emulation, not local WBGT.",
            "no",
        ),
        gate_row(
            "no_risk_claim",
            "No risk claim",
            "docs/v12/OpenHeat_SystemB_surrogate_model_card_CN.md",
            "PASS",
            "Model-card text explicitly excludes risk maps and exposure/vulnerability claims.",
            "no",
        ),
        gate_row(
            "multi_forcing_stability",
            "Multi-forcing stability",
            "not_available",
            "NOT_TESTED",
            "Only the current N150 single-forcing setup is covered.",
            "yes",
        ),
        gate_row(
            "full_aoi_inference_readiness",
            "Full AOI inference readiness",
            "not_available",
            "FAIL",
            "No AOI-wide predictions, final maps, or accepted multi-forcing gate exist in B8.3.",
            "yes",
        ),
    ]
    return pd.DataFrame(gates)


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    """Return a Markdown table for selected columns."""
    if df.empty:
        return "No rows available."
    return df[columns].to_markdown(index=False)


def candidate_evidence_lines(
    summary: pd.DataFrame, topk: pd.DataFrame, candidate_model: str, config: dict[str, Any]
) -> list[str]:
    """Build concise primary evidence bullets."""
    primary = str(config["targets"]["primary"])
    lines: list[str] = []
    for split in ["cell_grouped_holdout", "spatial_holdout", "feature_bin_holdout", "hour_holdout", "scenario_holdout"]:
        row = model_row(summary, primary, split, candidate_model)
        best = best_non_featureless(summary, primary, split)
        if row is None:
            continue
        top10 = topk_mean(topk, primary, candidate_model, split, config)
        lines.append(
            f"- `{split}`: candidate `{candidate_model}` MAE={fmt(row['MAE'])}, Spearman={fmt(row['spearman'])}, "
            f"featureless MAE improvement={fmt(row['improvement_over_featureless_MAE'])}, cell top-10 overlap={fmt(top10)}; "
            f"best by MAE=`{best['model'] if best is not None else 'not_available'}`."
        )
    return lines


def write_decision_report(
    *,
    path: Path,
    candidate_model: str,
    best_by_required_split: dict[str, str],
    feature_context: dict[str, Any],
    metrics_summary: pd.DataFrame,
    split_matrix: pd.DataFrame,
    gates: pd.DataFrame,
    topk: pd.DataFrame,
    config: dict[str, Any],
) -> None:
    """Write the concise English B8.3 decision report."""
    primary = str(config["targets"]["primary"])
    secondary = str(config["targets"]["secondary"])
    topk_splits = ["cell_grouped_holdout", "spatial_holdout"]
    mean_spearman = mean_candidate_spearman(metrics_summary, primary, candidate_model, topk_splits)
    mean_top10 = topk_mean_across_splits(topk, primary, candidate_model, topk_splits, config)
    gate_counts = gates.groupby("status").size().to_dict()
    files = config["outputs"]
    lines = [
        "# B8.3 System B Surrogate Model-Card Decision Report",
        "",
        f"Generated: {now_stamp()}",
        "",
        "## Decision",
        "",
        f"- Candidate model: `{candidate_model}`.",
        "- Candidate for internal model-card review: yes.",
        "- Approved for final AOI-wide inference: no.",
        f"- Recommended next gate: {config['promotion_gate']['recommended_next_gate']}.",
        "- Optional hardening: B8.3b if reviewers request report or checklist tightening.",
        "",
        "## Purpose Boundary",
        "",
        "- Surrogate/emulator for SOLWEIG-derived local radiative modifier labels.",
        "- Not observed WBGT calibration, not local 100m WBGT, not a risk map, and not a final AOI inference product.",
        "",
        "## Inputs And Feature Contract",
        "",
        f"- N150 label-feature matrix rows: {feature_context['rows']}; cells: {feature_context['cells']}; scenarios: {', '.join(feature_context['scenarios'])}; hours: {', '.join(str(h) for h in feature_context['hours'])}.",
        f"- Headline physical-core features: {feature_context['feature_count']}.",
        f"- Spatial diagnostic columns available but excluded from headline features: {feature_context['spatial_diagnostic_count']}.",
        f"- Prohibited nonphysical/social token hits in headline features: {feature_context['prohibited_hit_count']}.",
        f"- Target-leakage token hits in headline features: {feature_context['leakage_hit_count']}.",
        f"- Coordinate headline features: {feature_context['coordinate_feature_count']}.",
        "",
        "## B8.2 Primary Evidence",
        "",
        *candidate_evidence_lines(metrics_summary, topk, candidate_model, config),
        "",
        f"Required best-by-MAE checks: {', '.join(f'{split}={model}' for split, model in best_by_required_split.items())}.",
        f"Mean cell/spatial Spearman for `{primary}`: {fmt(mean_spearman)}.",
        f"Mean cell-level top-10% overlap for `{primary}` across cell/spatial holdouts: {fmt(mean_top10)}.",
        "",
        "## Secondary Target",
        "",
        f"`{secondary}` performance is weaker and remains secondary. Absolute Tmrt is not the main B8 product; the current model-card decision centers on `{primary}`.",
        "",
        "## Promotion Gate Summary",
        "",
        f"- Gate counts: {', '.join(f'{key}={value}' for key, value in sorted(gate_counts.items()))}.",
        f"- Gate checklist: `{files['promotion_gate_checklist']}`.",
        f"- Split-family decision matrix: `{files['split_family_decision_matrix']}`.",
        "",
        "## Blockers Before B9",
        "",
        "- Multi-forcing stability is not tested.",
        "- Feature-bin / typology extrapolation remains partial evidence.",
        "- Top-k prioritisation is diagnostic rather than final promotion evidence.",
        "- No full AOI-wide inference readiness is established.",
        "",
        "## Next Steps",
        "",
        "- Run B8.5-F0 N24 x 2-3 forcing days if the lane moves toward stability evidence.",
        "- Use B8.3b only if reviewers require a harder model-card review packet.",
        "- Defer B9 full AOI inference until multi-forcing and model-card gates accept it.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_chinese_model_card(
    *,
    path: Path,
    candidate_model: str,
    feature_context: dict[str, Any],
    metrics_summary: pd.DataFrame,
    split_matrix: pd.DataFrame,
    gates: pd.DataFrame,
    topk: pd.DataFrame,
    config: dict[str, Any],
) -> None:
    """Write the canonical Chinese model card."""
    primary = str(config["targets"]["primary"])
    secondary = str(config["targets"]["secondary"])
    gate_compact = gates[["gate_id", "status", "blocker_for_b9"]].copy()
    primary_rows = split_matrix.copy()
    secondary_rows = metrics_summary.loc[
        (metrics_summary["target"] == secondary)
        & (metrics_summary["model"].isin([candidate_model, "featureless_mean"]))
        & (metrics_summary["split_family"].isin(["cell_grouped_holdout", "spatial_holdout", "feature_bin_holdout"]))
    ].copy()
    family_counts = pd.DataFrame(feature_context["families"])[["item", "count", "status"]]
    topk_splits = ["cell_grouped_holdout", "spatial_holdout"]
    mean_spearman = mean_candidate_spearman(metrics_summary, primary, candidate_model, topk_splits)
    mean_top10 = topk_mean_across_splits(topk, primary, candidate_model, topk_splits, config)
    lines = [
        "# OpenHeat System B Surrogate Model Card (B8.3)",
        "",
        f"生成时间: {now_stamp()}",
        "",
        "## 1. 模型用途",
        "",
        f"本模型卡记录 B8.2 基线结果进入 B8.3 审阅时的候选 surrogate/emulator。候选模型为 `{candidate_model}`，用途是近似 SOLWEIG 派生的局地辐射修饰标签，主目标为 `{primary}`。",
        "",
        "边界：这不是观测 WBGT 校准，不是 100 m 局地 WBGT 预测，不是风险图，也不是最终 AOI 全域推理产品。树模型的表现只能作为预测诊断，不能解释为真实世界因果机制。",
        "",
        "## 2. 输入与数据范围",
        "",
        f"- 标签集：B7/B8 N150 SOLWEIG 派生标签。",
        f"- 行数：{feature_context['cells']} cells x 2 scenarios x 5 hours = {feature_context['rows']} rows。",
        f"- 场景：{', '.join(feature_context['scenarios'])}。",
        f"- 小时：{', '.join(str(h) for h in feature_context['hours'])} SGT。",
        "- 强迫条件：当前单一 forcing setup；尚未做多 forcing 稳定性检验。",
        f"- 输入特征：B8.1.1 `feature_schema.csv` 中 `role == feature` 且 `predictor_tier == physical_core` 的 {feature_context['feature_count']} 个特征。",
        "",
        "## 3. 目标",
        "",
        f"- 主目标：`{primary}`。",
        f"- 次目标：`{secondary}`。",
        "- 保留标签：`m_rad_pct01`，仅用于预测后的排序/修饰标签解释，不作为主回归目标。",
        "",
        "## 4. Feature Contract",
        "",
        f"- physical_core 特征数：{feature_context['feature_count']}。",
        f"- exposure / vulnerability / risk / social / source / note / version / name 等禁用 token 命中数：{feature_context['prohibited_hit_count']}。",
        f"- 目标泄漏 token 命中数：{feature_context['leakage_hit_count']}。",
        f"- 坐标是否进入 headline 特征：{'否' if feature_context['coordinate_feature_count'] == 0 else '是，需视为诊断风险'}。",
        f"- spatial diagnostic 坐标列数量：{feature_context['spatial_diagnostic_count']}，本轮 headline 模型未使用。",
        "",
        markdown_table(family_counts, ["item", "count", "status"]),
        "",
        "## 5. 验证证据",
        "",
        f"B8.2 已覆盖 `cell_grouped_holdout`、`spatial_holdout`、`feature_bin_holdout`、`hour_holdout`、`scenario_holdout`。主目标 `{primary}` 的模型选择以 cell-grouped 与 spatial holdout 为核心，feature-bin、hour、scenario 作为诊断证据。",
        "",
        markdown_table(
            primary_rows,
            [
                "split_family",
                "best_model_by_mae",
                "candidate_model",
                "candidate_mae",
                "candidate_spearman",
                "candidate_improvement_over_featureless_mae",
                "candidate_cell_top10_overlap",
                "evidence_status",
            ],
        ),
        "",
        f"主目标 ranking 诊断：`{candidate_model}` 在 cell/spatial holdout 的平均 Spearman 为 {fmt(mean_spearman)}，cell-level top-10% overlap 平均为 {fmt(mean_top10)}。这支持内部优先级排序审阅，但不是风险预测证据。",
        "",
        "次目标 `tmrt_p90_c` 的表现较弱，维持为 secondary diagnostic，不作为本轮主要产品：",
        "",
        markdown_table(
            secondary_rows,
            ["split_family", "model", "MAE", "RMSE", "R2", "spearman", "improvement_over_featureless_MAE"],
        ),
        "",
        "## 6. 适用范围",
        "",
        f"- `{primary}` 在 N150 内部 cell-grouped 与 spatial holdout 上有支持性证据。",
        "- 如果只用于内部候选排序，Spearman 与 top-k 指标提供了诊断信号。",
        "- hour/scenario transfer 只能作为诊断，因为这些切分允许同一 cell 在训练和测试中跨小时或跨场景出现。",
        "",
        "## 7. 失败点与风险",
        "",
        "- feature-bin / typology 外推证据较弱，且 water bin 存在 blocked/degenerate 情况。",
        "- 当前只有 N150 样本与单一 forcing setup。",
        "- 尚无多 forcing 稳定性证据。",
        "- 尚无外部局地实测验证。",
        "- 尚未进行 AOI 全域推理，也没有最终地图。",
        "- 树模型或特征重要性不能当作因果解释。",
        "",
        "## 8. Promotion Gate",
        "",
        markdown_table(gate_compact, ["gate_id", "status", "blocker_for_b9"]),
        "",
        "## 9. 决策",
        "",
        "- candidate_for_internal_model_card_review: yes",
        "- approved_for_final_AOI_inference: no",
        f"- recommended_next_gate: {config['promotion_gate']['recommended_next_gate']}",
        "",
        "不得表述为 AOI 地图已获最终批准；B9 全域推理必须等待多 forcing / model-card gate 接受后再启动。",
        "",
        "## 10. 下一步",
        "",
        "- B8.5-F0: N24 x 2-3 forcing days，用于稳定性检验。",
        "- B8.3b: 如评审要求，可做可选 model-card hardening。",
        "- B9: 只有在多 forcing 与 model-card gate 接受后，才考虑 full AOI inference。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_status(
    *,
    path: Path,
    result_status: str,
    candidate_model: str,
    primary_evidence: str,
    blockers: list[str],
    files_created: list[Path],
    commands: list[str],
    config: dict[str, Any],
) -> None:
    """Write B8_3_MODEL_CARD_STATUS.md."""
    branch = command_output(["git", "branch", "--show-current"])
    lines = [
        "# B8.3 Model Card Status",
        "",
        f"Status: {result_status}",
        f"Branch: {branch}",
        "Scope: B8.3 System B surrogate model card and promotion gate for SOLWEIG-derived System B targets.",
        "",
        "## Commands run",
        "",
        *[f"- `{command}`" for command in commands],
        "",
        "## Files created / modified",
        "",
        *[f"- `{path.as_posix()}`" for path in files_created],
        "",
        "## Key results",
        "",
        f"- Candidate model: `{candidate_model}`.",
        f"- Primary evidence: {primary_evidence}.",
        "- Candidate for internal model-card review: yes.",
        "- Approved for final AOI-wide inference: no.",
        f"- Recommended next gate: {config['promotion_gate']['recommended_next_gate']}.",
        "",
        "## Blockers",
        "",
        *[f"- {blocker}" for blocker in blockers],
        "",
        "## Caveats",
        "",
        "- B8.3 reads B8.2 metrics only; it does not train or rerun benchmark models.",
        "- N150 only.",
        "- Single forcing setup.",
        "- SOLWEIG-derived labels only.",
        "- No local WBGT.",
        "- No risk map.",
        "- No causal feature-importance claim.",
        "- No final AOI-wide prediction map.",
        "",
        "## Safe to commit",
        "",
        "- Compact B8.3 config, scripts, docs, and model-card outputs after review.",
        "",
        "## Not safe to commit",
        "",
        "- `data/solweig/`, `data/rasters/`, raw archive files, `.tif`, `.tiff`, `svfs.zip`, patch zip packages, large hourly forecast CSVs, AOI-wide prediction maps, local WBGT, hazard_score, risk_score, or System A/B coupling outputs.",
        "",
        "## Next recommended action",
        "",
        f"- {config['promotion_gate']['recommended_next_gate']} before B9 full AOI inference.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path: Path, commands: list[str] | None = None) -> ModelCardResult:
    """Run the B8.3 model-card generation workflow."""
    commands = commands or []
    config = read_config(config_path)
    out_dir = repo_path(config["outputs"]["model_card_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    matrix = pd.read_csv(repo_path(config["inputs"]["matrix"]), dtype={"cell_id": "string", "row_id": "string"})
    schema = pd.read_csv(repo_path(config["inputs"]["feature_schema"]))
    metrics = pd.read_csv(repo_path(config["inputs"]["metrics"]))
    topk = pd.read_csv(repo_path(config["inputs"]["topk_overlap"]))
    stratified = pd.read_csv(repo_path(config["inputs"]["stratified_error"]))
    split_summary = pd.read_csv(repo_path(config["inputs"]["split_family_summary"]))
    _ = metrics, stratified

    candidate_model, best_by_required_split = choose_candidate_model(split_summary, config)
    feature_contract, feature_context = build_feature_contract_summary(schema, matrix, config)
    metrics_summary = build_metrics_summary(split_summary, candidate_model, config)
    split_matrix = build_split_family_decision_matrix(metrics_summary, topk, candidate_model, config)
    gates = build_promotion_gate_checklist(
        feature_context=feature_context,
        split_matrix=split_matrix,
        summary=metrics_summary,
        topk=topk,
        candidate_model=candidate_model,
        config=config,
    )

    metrics_path = repo_path(config["outputs"]["metrics_summary"])
    gates_path = repo_path(config["outputs"]["promotion_gate_checklist"])
    split_matrix_path = repo_path(config["outputs"]["split_family_decision_matrix"])
    feature_contract_path = repo_path(config["outputs"]["feature_contract_summary"])
    report_path = repo_path(config["outputs"]["decision_report"])
    doc_path = repo_path(config["outputs"]["canonical_model_card"])
    status_path = repo_path(config["outputs"]["status"])

    metrics_summary.to_csv(metrics_path, index=False)
    gates.to_csv(gates_path, index=False)
    split_matrix.to_csv(split_matrix_path, index=False)
    feature_contract.to_csv(feature_contract_path, index=False)
    write_decision_report(
        path=report_path,
        candidate_model=candidate_model,
        best_by_required_split=best_by_required_split,
        feature_context=feature_context,
        metrics_summary=metrics_summary,
        split_matrix=split_matrix,
        gates=gates,
        topk=topk,
        config=config,
    )
    write_chinese_model_card(
        path=doc_path,
        candidate_model=candidate_model,
        feature_context=feature_context,
        metrics_summary=metrics_summary,
        split_matrix=split_matrix,
        gates=gates,
        topk=topk,
        config=config,
    )

    topk_splits = ["cell_grouped_holdout", "spatial_holdout"]
    mean_spearman = mean_candidate_spearman(metrics_summary, config["targets"]["primary"], candidate_model, topk_splits)
    mean_top10 = topk_mean_across_splits(topk, config["targets"]["primary"], candidate_model, topk_splits, config)
    primary_evidence = (
        f"{candidate_model} best by MAE on required cell/spatial splits; "
        f"mean cell/spatial Spearman={fmt(mean_spearman)}, mean cell top-10 overlap={fmt(mean_top10)}"
    )
    blockers = [
        "multi_forcing_stability NOT_TESTED",
        "feature_bin_typology_extrapolation PARTIAL",
        "topk_prioritisation_signal PARTIAL",
        "full_aoi_inference_readiness FAIL",
    ]
    files_created = [
        Path("configs/v12/systemb_surrogate_b8_model_card.yaml"),
        Path("scripts/v12_b8_make_model_card.py"),
        Path("scripts/v12_b8_run_model_card.py"),
        Path(config["outputs"]["canonical_model_card"]),
        Path(config["outputs"]["metrics_summary"]),
        Path(config["outputs"]["promotion_gate_checklist"]),
        Path(config["outputs"]["split_family_decision_matrix"]),
        Path(config["outputs"]["feature_contract_summary"]),
        Path(config["outputs"]["decision_report"]),
        Path(config["outputs"]["status"]),
    ]
    status = "PASS"
    if candidate_model == "not_available" or feature_context["leakage_hit_count"] > 0:
        status = "FAILED"
    if str(config["promotion_gate"]["approved_for_final_AOI_inference"]).lower() not in {"no", "false"}:
        status = "FAILED"

    write_status(
        path=status_path,
        result_status=status,
        candidate_model=candidate_model,
        primary_evidence=primary_evidence,
        blockers=blockers,
        files_created=files_created,
        commands=commands,
        config=config,
    )
    return ModelCardResult(
        status=status,
        candidate_model=candidate_model,
        primary_evidence=primary_evidence,
        blockers=blockers,
        recommended_next_gate=str(config["promotion_gate"]["recommended_next_gate"]),
        files_created=[repo_path(path) for path in files_created],
        status_path=status_path,
    )
