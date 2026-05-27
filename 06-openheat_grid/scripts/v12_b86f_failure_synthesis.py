"""Synthesize B8.6d/B8.6e surrogate failure evidence for B8.6f.

Inputs:
    B8.6d selected two-stage metrics and OOF diagnostics, B8.6e spatial
    failure tables, anchor/neutral contexts, feature-gap register, and safe
    feature probe metrics declared in the B8.6f config.
Outputs:
    b86f_b86e_caveat_register.csv, b86f_failure_synthesis.csv,
    b86f_spatial_failure_decision_table.csv,
    b86f_anchor_neutral_failure_matrix.csv, and
    b86f_safe_feature_probe_verdict.csv.
Saved metrics:
    Spatial-bin failure modes, anchor underprediction and neutral false
    promotion evidence, blocker attribution, and a conservative verdict on the
    B8.6e safe-feature probe. No raster, QGIS, SOLWEIG, AOI-wide, WBGT,
    hazard, risk, B9, or System A/B coupling output is created.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86f_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    as_float,
    fmt,
    input_path,
    load_config,
    output_path,
    read_csv,
    write_csv,
)


@dataclass(frozen=True)
class FailureSynthesisResult:
    """Failure synthesis result."""

    status: str
    spatial_bins: int
    caveats: int
    anchor_neutral_rows: int


def caveat_register() -> pd.DataFrame:
    """Return the compact B8.6e caveat register required by B8.6f."""
    rows = [
        {
            "caveat_id": "safe_feature_probe_not_spatial_closure",
            "caveat_headline": "B8.6e safe physical engineered features did not close spatial_holdout.",
            "evidence": "Spatial-holdout Spearman delta was near zero and top-k worsened for safe_physical_engineered.",
            "interpretation": "Treat safe engineered features as diagnostic leads, not validated spatial closure.",
            "required_action": "Override over-optimistic B8.6e wording in B8.6f reports.",
        },
        {
            "caveat_id": "typology_gain_diagnostic_only",
            "caveat_headline": "Typology Spearman improvement is diagnostic, not production-ready.",
            "evidence": "Typology Spearman improved for safe_physical_engineered, but top-k overlap worsened materially.",
            "interpretation": "The signal may guide feature acquisition but cannot promote a surrogate.",
            "required_action": "Keep AOI-wide and B9 blocked.",
        },
        {
            "caveat_id": "coordinate_distance_diagnostic_only",
            "caveat_headline": "Coordinate and distance features are diagnostic-only.",
            "evidence": "Coordinate/distance variants remain explicitly dependent on spatial position or distance diagnostics.",
            "interpretation": "They can explain out-of-domain behavior but are not production predictors.",
            "required_action": "Do not use them as validated spatial-closure features.",
        },
        {
            "caveat_id": "n300_v1_role_skew",
            "caveat_headline": "N300 v1 is candidate-design only and too skewed to typology_gap_fill.",
            "evidence": "B8.6e v1 selected 150 candidate-design cells with a dominant typology_gap_fill role.",
            "interpretation": "B8.6f must rebalance roles before any future N300 precheck.",
            "required_action": "Create role-quota-balanced N300 v2; do not create a manifest or runner.",
        },
        {
            "caveat_id": "aoi_b9_blocked",
            "caveat_headline": "AOI-wide/B9 remains blocked.",
            "evidence": "Spatial holdout, anchor underprediction, and neutral false-promotion remain unresolved.",
            "interpretation": "B8.6f is a review/design/diagnostic lane only.",
            "required_action": "Do not create AOI-wide predictions, B9 outputs, WBGT, hazard, risk, or coupling output.",
        },
    ]
    out = pd.DataFrame(rows)
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def load_tables(config: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """Load failure evidence tables."""
    keys = {
        "split_metrics": "b86d_metrics_by_split_path",
        "spatial": "b86e_spatial_failure_path",
        "inventory": "b86e_spatial_bin_inventory_path",
        "cross": "b86e_typology_spatial_path",
        "anchor": "b86e_anchor_context_path",
        "neutral": "b86e_neutral_context_path",
        "feature_gaps": "b86e_feature_gap_register_path",
        "probe": "b86e_safe_feature_probe_path",
        "n300_v1": "b86e_n300_v1_path",
    }
    return {name: read_csv(input_path(config, key)) for name, key in keys.items()}


def spatial_decision_table(config: dict[str, Any], spatial: pd.DataFrame) -> pd.DataFrame:
    """Create a spatial-bin decision table from B8.6e/B8.6d evidence."""
    rows: list[dict[str, Any]] = []
    weak_spearman = float(config["spatial_failure_spearman_threshold"])
    weak_top10 = float(config["spatial_failure_top10_threshold"])
    for _, row in spatial.iterrows():
        spearman = as_float(row.get("Spearman"))
        top10 = as_float(row.get("top10pct_overlap"))
        mae = as_float(row.get("mean_abs_error"))
        fp_rate = as_float(row.get("false_promotion_rate"))
        failure = str(row.get("suspected_failure_type", "not-flagged"))
        blocker_parts: list[str] = []
        if spearman == spearman and spearman < weak_spearman:
            blocker_parts.append("feature_representation")
        if top10 == top10 and top10 < weak_top10:
            blocker_parts.append("sample_coverage")
        if "anchor-underprediction" in failure:
            blocker_parts.append("anchor_representation")
        if "neutral-false-promotion" in failure or (fp_rate == fp_rate and fp_rate >= float(config["neutral_false_promotion_warn_threshold"])):
            blocker_parts.append("neutral_boundary")
        if not blocker_parts:
            blocker_parts.append("diagnostic_monitor")
        if str(row["spatial_bin"]) == "east_north":
            headline = "Anchor-underprediction remains severe, led by TP_0857/TP_0542 context."
        elif str(row["spatial_bin"]) == "east_south":
            headline = "Water/neutral false-promotion and weak spatial transfer remain unresolved."
        elif str(row["spatial_bin"]) == "west_south":
            headline = "Very weak top-k support indicates coverage and feature-representation gaps."
        else:
            headline = "Very weak ranking plus neutral false-promotion indicates out-of-domain behavior."
        rows.append(
            {
                "spatial_bin": row["spatial_bin"],
                "n_rows": row.get("n_rows"),
                "n_cells": row.get("n_cells"),
                "mean_abs_error": mae,
                "Spearman": spearman,
                "top10pct_overlap": top10,
                "neutral_accuracy": row.get("neutral_accuracy"),
                "false_promotion_rate": fp_rate,
                "suspected_failure_type": failure,
                "dominant_blocker": "|".join(dict.fromkeys(blocker_parts)),
                "headline": headline,
                "b86f_decision": "keep_spatial_holdout_blocking_aoi_preflight",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    order = ["west_north", "west_south", "east_south", "east_north"]
    out = pd.DataFrame(rows)
    out["sort_order"] = out["spatial_bin"].map({name: idx for idx, name in enumerate(order)}).fillna(99)
    return out.sort_values("sort_order").drop(columns=["sort_order"])


def failure_synthesis_table(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Summarize top failure modes and whether they are coverage/feature/model issues."""
    spatial = tables["spatial"]
    cross = tables["cross"]
    anchor = tables["anchor"]
    neutral = tables["neutral"]
    feature_gaps = tables["feature_gaps"]
    weak_bins = "|".join(spatial["spatial_bin"].astype(str).tolist())
    worst_cross = (
        cross.loc[cross["failure_label"].astype(str).ne("not-flagged")]
        .sort_values(["n_cells", "mean_abs_error"], ascending=[False, False])
        .head(5)
    )
    anchor_spatial = anchor.loc[anchor["split_family"].astype(str).eq("spatial_holdout")].copy()
    neutral_bad = neutral.sort_values(["false_promotion_rate", "mean_abs_error"], ascending=False).head(8)
    high_gaps = feature_gaps.loc[feature_gaps["expected_benefit"].astype(str).str.contains("high", case=False, na=False)]
    rows = [
        {
            "failure_mode": "spatial-bin-out-of-domain",
            "evidence_source": "b86e_spatial_holdout_failure_summary",
            "evidence_headline": f"All reviewed spatial bins remain weak or caveated: {weak_bins}.",
            "affected_bins_or_cells": weak_bins,
            "blocker_interpretation": "feature_representation_and_sample_coverage",
            "model_form_interpretation": "Current model form is secondary until feature coverage improves.",
            "next_action": "Use B8.6g feature acquisition and B8.7-N300-PRE design review before AOI preflight.",
        },
        {
            "failure_mode": "anchor-underprediction",
            "evidence_source": "b86e_anchor_underprediction_context",
            "evidence_headline": "TP_0857, TP_0542, TP_0433, TP_0037, and TP_0141 remain required anchor checks.",
            "affected_bins_or_cells": "|".join(config["anchor_cells"]),
            "blocker_interpretation": "feature_representation_and_anchor_like_sample_coverage",
            "model_form_interpretation": "Regression shrinkage to neutral remains possible but should not be overfit away.",
            "next_action": "Add anchor-like replication quota and acquire shade/geometry continuity features.",
        },
        {
            "failure_mode": "neutral-false-promotion",
            "evidence_source": "b86e_neutral_false_promotion_context",
            "evidence_headline": "Known neutral and near-zero cells can be promoted as cooling under weak context.",
            "affected_bins_or_cells": "|".join(neutral_bad["cell_id"].astype(str).head(8).tolist()),
            "blocker_interpretation": "neutral_boundary_representation",
            "model_form_interpretation": "Two-stage neutral gate is useful but not sufficient.",
            "next_action": "Add neutral-boundary replication quota and abstention rules.",
        },
        {
            "failure_mode": "feature-distribution-shift",
            "evidence_source": "b86e_typology_spatial_cross_failure",
            "evidence_headline": "Typology-spatial combinations remain weak, especially residential and civic/transport gaps.",
            "affected_bins_or_cells": "|".join(
                f"{row.typology}@{row.spatial_bin}" for row in worst_cross.itertuples(index=False)
            ),
            "blocker_interpretation": "feature_representation",
            "model_form_interpretation": "Coordinate/distance diagnostics can describe shift but cannot validate closure.",
            "next_action": "Prioritize connected shade, hot-pocket fraction, edge context, and geometry descriptors.",
        },
        {
            "failure_mode": "target-role-mismatch",
            "evidence_source": "b86e_safe_feature_probe_metrics",
            "evidence_headline": "Typology Spearman can improve while top-k support worsens.",
            "affected_bins_or_cells": "typology_holdout",
            "blocker_interpretation": "target_role_and_ranking_support",
            "model_form_interpretation": "Ranking suitability must be judged separately from correlation.",
            "next_action": "Do not treat typology Spearman alone as promotion evidence.",
        },
        {
            "failure_mode": "sample-support-low",
            "evidence_source": "b86e_typology_spatial_cross_failure",
            "evidence_headline": "Sparse typology-spatial cells need targeted replication before model promotion.",
            "affected_bins_or_cells": "|".join(
                cross.loc[pd.to_numeric(cross["n_cells"], errors="coerce") < 3, "typology"].astype(str).head(8).tolist()
            ),
            "blocker_interpretation": "sample_coverage",
            "model_form_interpretation": "No random split should be used as main evidence.",
            "next_action": "Use role-balanced N300 v2 as candidate design only.",
        },
    ]
    out = pd.DataFrame(rows)
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def anchor_neutral_failure_matrix(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create a required anchor/neutral failure matrix."""
    anchor = tables["anchor"].copy()
    neutral = tables["neutral"].copy()
    inventory = tables["inventory"].copy()
    rows: list[dict[str, Any]] = []
    for cell_id in config["anchor_cells"]:
        subset = anchor.loc[anchor["cell_id"].astype(str).eq(cell_id)].copy()
        if not subset.empty:
            preferred = subset.loc[subset["split_family"].astype(str).eq("spatial_holdout")]
            record = preferred.sort_values("mean_abs_error", ascending=False).iloc[0] if not preferred.empty else subset.sort_values("mean_abs_error", ascending=False).iloc[0]
            severity = "high" if as_float(record.get("mean_abs_error")) >= float(config["anchor_underprediction_mae_threshold"]) else "medium"
            rows.append(
                {
                    "cell_id": cell_id,
                    "diagnostic_role": "anchor_reference",
                    "split_family": record.get("split_family"),
                    "spatial_bin": record.get("spatial_bin"),
                    "typology": record.get("typology"),
                    "mean_true_delta_tmrt_p90_c": record.get("mean_true_delta_tmrt_p90_c"),
                    "mean_predicted_delta_tmrt_p90_c": record.get("mean_predicted_delta_tmrt_p90_c"),
                    "mean_abs_error": record.get("mean_abs_error"),
                    "failure_rate": record.get("underprediction_rate_for_cooling"),
                    "failure_type": "anchor-underprediction",
                    "severity": severity,
                    "b86f_action": "replicate_anchor_like_context_and_keep_as_gate",
                }
            )
        else:
            rows.append(
                {
                    "cell_id": cell_id,
                    "diagnostic_role": "anchor_reference",
                    "split_family": "missing_context",
                    "spatial_bin": "",
                    "typology": "",
                    "mean_true_delta_tmrt_p90_c": np.nan,
                    "mean_predicted_delta_tmrt_p90_c": np.nan,
                    "mean_abs_error": np.nan,
                    "failure_rate": np.nan,
                    "failure_type": "anchor-context-missing",
                    "severity": "review",
                    "b86f_action": "keep_in_anchor_gate",
                }
            )
    known_neutrals = set(config["known_neutral_cells"])
    near_zero = neutral.sort_values(["false_promotion_rate", "mean_abs_error"], ascending=False).head(12)["cell_id"].astype(str)
    for cell_id in list(config["known_neutral_cells"]) + [item for item in near_zero if item not in known_neutrals][:6]:
        subset = neutral.loc[neutral["cell_id"].astype(str).eq(cell_id)].copy()
        if not subset.empty:
            record = subset.sort_values(["false_promotion_rate", "mean_abs_error"], ascending=False).iloc[0]
            severity = "high" if as_float(record.get("false_promotion_rate"), 0.0) >= 0.5 else "medium"
            role = "known_neutral_reference" if cell_id in known_neutrals else "near_zero_false_promotion_context"
            rows.append(
                {
                    "cell_id": cell_id,
                    "diagnostic_role": role,
                    "split_family": record.get("split_family"),
                    "spatial_bin": record.get("spatial_bin"),
                    "typology": record.get("typology"),
                    "mean_true_delta_tmrt_p90_c": record.get("mean_true_delta_tmrt_p90_c"),
                    "mean_predicted_delta_tmrt_p90_c": record.get("mean_predicted_delta_tmrt_p90_c"),
                    "mean_abs_error": record.get("mean_abs_error"),
                    "failure_rate": record.get("false_promotion_rate"),
                    "failure_type": "neutral-false-promotion",
                    "severity": severity,
                    "b86f_action": "replicate_neutral_boundary_and_abstain_when_promoted",
                }
            )
        else:
            inv = inventory.loc[inventory["cell_id"].astype(str).eq(cell_id)].head(1)
            rows.append(
                {
                    "cell_id": cell_id,
                    "diagnostic_role": "known_neutral_reference",
                    "split_family": "missing_context",
                    "spatial_bin": inv.iloc[0].get("spatial_bin", "") if not inv.empty else "",
                    "typology": inv.iloc[0].get("typology", "") if not inv.empty else "",
                    "mean_true_delta_tmrt_p90_c": np.nan,
                    "mean_predicted_delta_tmrt_p90_c": np.nan,
                    "mean_abs_error": np.nan,
                    "failure_rate": np.nan,
                    "failure_type": "neutral-context-missing",
                    "severity": "review",
                    "b86f_action": "keep_in_neutral_gate",
                }
            )
    out = pd.DataFrame(rows)
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def safe_feature_probe_verdict(config: dict[str, Any], probe: pd.DataFrame) -> pd.DataFrame:
    """Create conservative safe-feature probe verdict rows."""
    rows: list[dict[str, Any]] = []
    safe = probe.loc[probe["feature_variant"].astype(str).eq("safe_physical_engineered")].copy()
    for split in ["spatial_holdout", "cell_group_holdout", "typology_holdout"]:
        subset = safe.loc[safe["split_family"].astype(str).eq(split)]
        if subset.empty:
            continue
        row = subset.iloc[0]
        spearman_delta = as_float(row.get("Spearman_delta_vs_b86d"))
        top10_delta = as_float(row.get("top10_delta_vs_b86d"))
        if split == "typology_holdout" and spearman_delta > 0 and top10_delta < 0:
            verdict = "partial_diagnostic_spearman_gain_but_topk_worsened"
            headline = "Typology Spearman improved, but top-k support worsened; not production-ready."
        else:
            improved = spearman_delta > 0.05 and top10_delta >= 0
            verdict = "materially_improved" if improved else "not_improved"
            headline = f"{split} did not receive validated closure from safe physical engineered features."
        rows.append(
            {
                "verdict_topic": split,
                "feature_variant": "safe_physical_engineered",
                "MAE": row.get("MAE"),
                "Spearman": row.get("Spearman"),
                "top10pct_overlap": row.get("top10pct_overlap"),
                "Spearman_delta_vs_b86d": spearman_delta,
                "top10_delta_vs_b86d": top10_delta,
                "verdict": verdict,
                "headline": headline,
                "production_boundary": "diagnostic_only_not_validated_spatial_closure",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    coord = probe.loc[
        probe["feature_variant"].astype(str).str.contains("coordinate|distance", case=False, regex=True, na=False)
    ].copy()
    rows.append(
        {
            "verdict_topic": "coordinate_and_distance_features",
            "feature_variant": "coordinate_context_diagnostic|safe_physical_plus_distance_diagnostic",
            "MAE": np.nan,
            "Spearman": np.nan,
            "top10pct_overlap": np.nan,
            "Spearman_delta_vs_b86d": coord["Spearman_delta_vs_b86d"].map(as_float).max() if not coord.empty else np.nan,
            "top10_delta_vs_b86d": coord["top10_delta_vs_b86d"].map(as_float).min() if not coord.empty else np.nan,
            "verdict": "diagnostic_only",
            "headline": "Coordinate and distance features can diagnose spatial shift but cannot validate production closure.",
            "production_boundary": "diagnostic_only_not_production_predictors",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    )
    rows.append(
        {
            "verdict_topic": "overall_safe_feature_probe",
            "feature_variant": "b86e_probe",
            "MAE": np.nan,
            "Spearman": np.nan,
            "top10pct_overlap": np.nan,
            "Spearman_delta_vs_b86d": np.nan,
            "top10_delta_vs_b86d": np.nan,
            "verdict": "do_not_treat_as_validated_spatial_closure",
            "headline": "B8.6e safe features did not close spatial_holdout or cell_group, and typology gains remain diagnostic.",
            "production_boundary": "aoi_and_b9_blocked",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    )
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> FailureSynthesisResult:
    """Run and write all B8.6f failure synthesis outputs."""
    config = load_config(config_path)
    tables = load_tables(config)
    caveats = caveat_register()
    spatial_decisions = spatial_decision_table(config, tables["spatial"])
    synthesis = failure_synthesis_table(config, tables)
    anchor_neutral = anchor_neutral_failure_matrix(config, tables)
    probe_verdict = safe_feature_probe_verdict(config, tables["probe"])
    write_csv(caveats, output_path(config, "b86e_caveat_register"))
    write_csv(synthesis, output_path(config, "failure_synthesis"))
    write_csv(spatial_decisions, output_path(config, "spatial_failure_decision_table"))
    write_csv(anchor_neutral, output_path(config, "anchor_neutral_failure_matrix"))
    write_csv(probe_verdict, output_path(config, "safe_feature_probe_verdict"))
    return FailureSynthesisResult(
        status="B86F_FAILURE_SYNTHESIS_READY",
        spatial_bins=len(spatial_decisions),
        caveats=len(caveats),
        anchor_neutral_rows=len(anchor_neutral),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Synthesize B8.6d/B8.6e failure evidence for B8.6f.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
