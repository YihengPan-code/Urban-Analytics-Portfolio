"""Audit B8.6e N300 v1 and create a role-balanced B8.6f N300 v2 design.

Inputs:
    B8.6e targeted N300 v1 candidate design, B8.6e failure summaries, current
    F5 N150 labels, N150 compact feature matrix, and the compact candidate
    universe declared in the B8.6f config.
Outputs:
    b86f_n300_design_v1_audit.csv, b86f_n300_role_quota_plan.csv,
    b86f_targeted_n300_design_v2.csv, and
    b86f_targeted_n300_design_review.md.
Saved metrics:
    Role quota availability, selected role mix, spatial-bin mix, typology mix,
    nearest-anchor and nearest-neutral distributions, sparse-feature-space
    counts, and coverage of B8.6e weak bins. This is a candidate design only:
    no SOLWEIG manifest, QGIS runner, raster I/O, AOI-wide prediction, B9,
    WBGT, hazard, risk, or System A/B coupling output is created.
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
    add_spatial_bin,
    as_float,
    candidate_universe,
    current_cell_features,
    current_label_cells,
    fmt,
    input_path,
    load_config,
    md_table,
    nearest_reference_rows,
    output_path,
    read_csv,
    safe_numeric_feature_columns,
    write_csv,
    write_text,
)


@dataclass(frozen=True)
class N300DesignResult:
    """N300 design review result."""

    status: str
    selected_rows: int
    quota_roles: int
    current_cells: int


ROLE_ORDER = [
    "typology_gap_fill",
    "spatial_gap_fill",
    "anchor_like_replication",
    "neutral_boundary_replication",
    "sparse_feature_space",
    "control_cell",
]


def v1_audit(config: dict[str, Any]) -> pd.DataFrame:
    """Audit B8.6e v1 role/spatial/typology mix."""
    v1 = read_csv(input_path(config, "b86e_n300_v1_path"))
    rows: list[dict[str, Any]] = []
    total = max(1, len(v1))
    role_counts = v1.get("expected_role", pd.Series(dtype=str)).astype(str).value_counts()
    for role, count in role_counts.items():
        target = int(config["n300_role_quota"].get(role, 0))
        rows.append(
            {
                "audit_dimension": "primary_role",
                "value": role,
                "count": int(count),
                "share": float(count / total),
                "target_count_in_v2": target,
                "verdict": "overrepresented_in_v1" if role == "typology_gap_fill" and count > target else "review",
            }
        )
    for spatial_bin, count in v1.get("spatial_bin", pd.Series(dtype=str)).astype(str).value_counts().items():
        rows.append(
            {
                "audit_dimension": "spatial_bin",
                "value": spatial_bin,
                "count": int(count),
                "share": float(count / total),
                "target_count_in_v2": np.nan,
                "verdict": "coverage_context",
            }
        )
    for typology, count in v1.get("typology", pd.Series(dtype=str)).astype(str).value_counts().head(12).items():
        rows.append(
            {
                "audit_dimension": "typology",
                "value": typology,
                "count": int(count),
                "share": float(count / total),
                "target_count_in_v2": np.nan,
                "verdict": "coverage_context",
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        top_role = role_counts.index[0] if len(role_counts) else "none"
        out["v1_headline"] = (
            f"N300 v1 is candidate-design only; dominant role={top_role}; "
            "B8.6f rebalances quotas across anchor, neutral, spatial, sparse, and controls."
        )
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def eligible_candidate_pool(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, set[str]]:
    """Return eligible candidate rows beyond current N150 labelled cells."""
    current_cells = current_label_cells(config)
    universe = candidate_universe(config)
    current = current_cell_features(config)
    pool = universe.loc[~universe["cell_id"].astype(str).isin(current_cells)].copy()
    if "eligible" in pool.columns:
        eligible = pool["eligible"].astype(str).str.lower().isin({"true", "1", "yes", "nan"}) | pool["eligible"].isna()
        pool = pool.loc[eligible].copy()
    pool = add_spatial_bin(pool, reference=current)
    return pool.reset_index(drop=True), current.reset_index(drop=True), current_cells


def weak_sets(config: dict[str, Any]) -> tuple[set[str], set[tuple[str, str]], set[str]]:
    """Load weak spatial bins and weak typology-spatial pairs."""
    spatial = read_csv(input_path(config, "b86e_spatial_failure_path"))
    cross = read_csv(input_path(config, "b86e_typology_spatial_path"))
    weak_bins = set(
        spatial.loc[
            (pd.to_numeric(spatial["Spearman"], errors="coerce") < float(config["spatial_failure_spearman_threshold"]))
            | (pd.to_numeric(spatial["top10pct_overlap"], errors="coerce") < float(config["spatial_failure_top10_threshold"])),
            "spatial_bin",
        ].astype(str)
    )
    weak_cross = set(
        zip(
            cross.loc[cross["failure_label"].astype(str).ne("not-flagged"), "typology"].astype(str),
            cross.loc[cross["failure_label"].astype(str).ne("not-flagged"), "spatial_bin"].astype(str),
        )
    )
    problem_typologies = set(cross.loc[cross["failure_label"].astype(str).ne("not-flagged"), "typology"].astype(str))
    return weak_bins, weak_cross, problem_typologies


def attach_distances(config: dict[str, Any], pool: pd.DataFrame, current: pd.DataFrame) -> pd.DataFrame:
    """Attach nearest N150, anchor, and neutral distances for candidate scoring."""
    combined = pd.concat([pool, current], ignore_index=True, sort=False)
    features = safe_numeric_feature_columns(combined, min_non_null=20)
    out = pool.copy()
    n150 = nearest_reference_rows(out, current, features, top_n=1)
    if not n150.empty:
        out = out.merge(
            n150[["cell_id", "nearest_cell_id", "feature_space_distance"]].rename(
                columns={"nearest_cell_id": "nearest_n150_cell", "feature_space_distance": "nearest_n150_distance"}
            ),
            on="cell_id",
            how="left",
        )
    anchor_ref = current.loc[current["cell_id"].astype(str).isin(set(config["anchor_cells"]))].copy()
    neutral_ref = current.loc[current["cell_id"].astype(str).isin(set(config["known_neutral_cells"]))].copy()
    anchor = nearest_reference_rows(out, anchor_ref, features, top_n=1) if not anchor_ref.empty else pd.DataFrame()
    neutral = nearest_reference_rows(out, neutral_ref, features, top_n=1) if not neutral_ref.empty else pd.DataFrame()
    if not anchor.empty:
        out = out.merge(
            anchor[["cell_id", "nearest_cell_id", "feature_space_distance"]].rename(
                columns={"nearest_cell_id": "nearest_anchor_cell", "feature_space_distance": "nearest_anchor_distance"}
            ),
            on="cell_id",
            how="left",
        )
    if not neutral.empty:
        out = out.merge(
            neutral[["cell_id", "nearest_cell_id", "feature_space_distance"]].rename(
                columns={"nearest_cell_id": "nearest_neutral_cell", "feature_space_distance": "nearest_neutral_distance"}
            ),
            on="cell_id",
            how="left",
        )
    out["nearest_n150_distance_percentile"] = pd.to_numeric(out.get("nearest_n150_distance"), errors="coerce").rank(pct=True)
    out["nearest_anchor_distance_percentile"] = pd.to_numeric(out.get("nearest_anchor_distance"), errors="coerce").rank(pct=True)
    out["nearest_neutral_distance_percentile"] = pd.to_numeric(out.get("nearest_neutral_distance"), errors="coerce").rank(pct=True)
    for column in ["nearest_n150_cell", "nearest_anchor_cell", "nearest_neutral_cell"]:
        if column not in out.columns:
            out[column] = ""
    return out


def role_scores(config: dict[str, Any], frame: pd.DataFrame) -> pd.DataFrame:
    """Score candidate rows for each role quota."""
    weak_bins, weak_cross, problem_typologies = weak_sets(config)
    out = frame.copy()
    typology = out.get("typology_label", pd.Series("unknown", index=out.index)).astype(str)
    spatial = out.get("spatial_bin", pd.Series("unknown", index=out.index)).astype(str)
    weak_pair = [pair in weak_cross for pair in zip(typology, spatial)]
    weak_bin = spatial.isin(weak_bins)
    problem_typology = typology.isin(problem_typologies)
    n150_pct = pd.to_numeric(out["nearest_n150_distance_percentile"], errors="coerce").fillna(0.0)
    anchor_pct = pd.to_numeric(out["nearest_anchor_distance_percentile"], errors="coerce").fillna(1.0)
    neutral_pct = pd.to_numeric(out["nearest_neutral_distance_percentile"], errors="coerce").fillna(1.0)
    overhead = pd.to_numeric(out.get("overhead_fraction_total", pd.Series(0.0, index=out.index)), errors="coerce").fillna(0.0)
    shade = pd.to_numeric(out.get("shade_fraction_overhead_sens", pd.Series(0.0, index=out.index)), errors="coerce").fillna(0.0)
    svf = pd.to_numeric(out.get("svf", pd.Series(0.0, index=out.index)), errors="coerce").fillna(0.0)
    contrast = (overhead > 0.05) | ((shade > 0.65) & (svf > 0.45)) | ((shade < 0.25) & (svf > 0.65))
    out["eligible_typology_gap_fill"] = pd.Series(weak_pair, index=out.index) | problem_typology
    out["score_typology_gap_fill"] = (
        pd.Series(weak_pair, index=out.index).astype(float) * 60
        + problem_typology.astype(float) * 25
        + weak_bin.astype(float) * 10
        + n150_pct * 10
    )
    out["eligible_spatial_gap_fill"] = weak_bin
    out["score_spatial_gap_fill"] = weak_bin.astype(float) * 65 + n150_pct * 20 + contrast.astype(float) * 15
    out["eligible_anchor_like_replication"] = anchor_pct <= 0.35
    out["score_anchor_like_replication"] = (1.0 - anchor_pct) * 85 + weak_bin.astype(float) * 10 + contrast.astype(float) * 5
    out["eligible_neutral_boundary_replication"] = neutral_pct <= 0.35
    out["score_neutral_boundary_replication"] = (1.0 - neutral_pct) * 85 + weak_bin.astype(float) * 10 + contrast.astype(float) * 5
    out["eligible_sparse_feature_space"] = n150_pct >= float(config["candidate_sparse_distance_percentile"])
    out["score_sparse_feature_space"] = n150_pct * 100 + weak_bin.astype(float) * 10
    issue_score = (
        out["eligible_typology_gap_fill"].astype(float)
        + out["eligible_anchor_like_replication"].astype(float)
        + out["eligible_neutral_boundary_replication"].astype(float)
        + out["eligible_sparse_feature_space"].astype(float)
    )
    out["eligible_control_cell"] = issue_score <= 1
    out["score_control_cell"] = (1.0 - (n150_pct - 0.5).abs()) * 60 + (~problem_typology).astype(float) * 20
    out["coverage_gap"] = [
        coverage_gap_text(row, weak_bins, weak_cross, problem_typologies) for _, row in out.iterrows()
    ]
    out["overall_score"] = out[[f"score_{role}" for role in ROLE_ORDER]].max(axis=1)
    return out


def coverage_gap_text(row: pd.Series, weak_bins: set[str], weak_cross: set[tuple[str, str]], problem_typologies: set[str]) -> str:
    """Build a pipe-delimited coverage-gap rationale field."""
    typology = str(row.get("typology_label", "unknown"))
    spatial = str(row.get("spatial_bin", "unknown"))
    gaps: list[str] = []
    if spatial in weak_bins:
        gaps.append("weak_spatial_bin")
    if (typology, spatial) in weak_cross:
        gaps.append("weak_typology_spatial_bin")
    if typology in problem_typologies:
        gaps.append("problem_typology")
    if as_float(row.get("nearest_n150_distance_percentile"), 0.0) >= 0.90:
        gaps.append("sparse_feature_space")
    if as_float(row.get("nearest_anchor_distance_percentile"), 1.0) <= 0.35:
        gaps.append("anchor_like_neighbour")
    if as_float(row.get("nearest_neutral_distance_percentile"), 1.0) <= 0.35:
        gaps.append("neutral_boundary_like_neighbour")
    return "|".join(dict.fromkeys(gaps)) if gaps else "control_cell"


def secondary_roles(row: pd.Series, primary_role: str) -> str:
    """Return secondary roles for a selected candidate."""
    roles = [
        role for role in ROLE_ORDER if role != primary_role and bool(row.get(f"eligible_{role}", False))
    ]
    return "|".join(roles) if roles else "none"


def rationale_for(row: pd.Series, primary_role: str) -> str:
    """Build a plain rationale for a selected candidate."""
    gap = str(row.get("coverage_gap", "control_cell")).replace("|", "; ")
    spatial = str(row.get("spatial_bin", "unknown"))
    typology = str(row.get("typology_label", "unknown"))
    return f"{primary_role}; {gap}; {typology} in {spatial}; candidate design only."


def learning_value(row: pd.Series, primary_role: str) -> str:
    """Assign expected learning value without making production claims."""
    if primary_role in {"anchor_like_replication", "neutral_boundary_replication", "typology_gap_fill"}:
        return "high_diagnostic_learning_value"
    if primary_role in {"spatial_gap_fill", "sparse_feature_space"}:
        return "medium_high_diagnostic_learning_value"
    return "control_balance_learning_value"


def select_role_balanced_design(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Select exactly the B8.6f role-balanced additional candidate-design cells if possible."""
    pool, current, current_cells = eligible_candidate_pool(config)
    scored = role_scores(config, attach_distances(config, pool, current))
    selected_parts: list[pd.DataFrame] = []
    selected_ids: set[str] = set()
    plan_rows: list[dict[str, Any]] = []
    quota = {role: int(config["n300_role_quota"][role]) for role in ROLE_ORDER}
    for role in ROLE_ORDER:
        eligible = scored.loc[
            (~scored["cell_id"].astype(str).isin(selected_ids)) & scored[f"eligible_{role}"].astype(bool)
        ].copy()
        eligible = eligible.sort_values([f"score_{role}", "overall_score", "cell_id"], ascending=[False, False, True])
        target = quota[role]
        take = eligible.head(target).copy()
        if not take.empty:
            take["primary_role"] = role
            take["role_selection_score"] = take[f"score_{role}"]
            selected_ids.update(take["cell_id"].astype(str).tolist())
            selected_parts.append(take)
        plan_rows.append(
            {
                "primary_role": role,
                "target_count": target,
                "available_before_deconflict": int(scored[f"eligible_{role}"].astype(bool).sum()),
                "selected_before_reallocation": int(len(take)),
                "deficit_after_primary_selection": int(max(0, target - len(take))),
                "reallocation_rule": "fill_from_highest_scored_unselected_nearest_justified_role_if_needed",
            }
        )
    selected = pd.concat(selected_parts, ignore_index=True) if selected_parts else pd.DataFrame()
    target_total = int(config["n300_target_additional_count"])
    if len(selected) < target_total:
        remaining = scored.loc[~scored["cell_id"].astype(str).isin(set(selected["cell_id"].astype(str)))].copy()
        remaining = remaining.sort_values(["overall_score", "nearest_n150_distance_percentile", "cell_id"], ascending=[False, False, True])
        needed = target_total - len(selected)
        fill = remaining.head(needed).copy()
        if not fill.empty:
            fill["primary_role"] = fill.apply(best_role_for_row, axis=1)
            fill["role_selection_score"] = fill.apply(lambda row: row.get(f"score_{row['primary_role']}", row["overall_score"]), axis=1)
            selected = pd.concat([selected, fill], ignore_index=True)
    selected = selected.head(target_total).copy()
    selected.insert(0, "selected_priority_rank", range(1, len(selected) + 1))
    selected["typology"] = selected.get("typology_label", pd.Series("unknown", index=selected.index)).astype(str)
    selected["secondary_roles"] = selected.apply(lambda row: secondary_roles(row, str(row["primary_role"])), axis=1)
    selected["rationale"] = selected.apply(lambda row: rationale_for(row, str(row["primary_role"])), axis=1)
    selected["expected_learning_value"] = selected.apply(lambda row: learning_value(row, str(row["primary_role"])), axis=1)
    selected["sampling_boundary"] = "candidate_design_only_not_N300_run_ready"
    selected["claim_boundary"] = CLAIM_BOUNDARY
    selected["nearest_n150_distance"] = pd.to_numeric(selected["nearest_n150_distance"], errors="coerce")
    selected["nearest_n150_distance_percentile"] = pd.to_numeric(selected["nearest_n150_distance_percentile"], errors="coerce")
    final_counts = selected["primary_role"].value_counts().to_dict() if not selected.empty else {}
    plan = pd.DataFrame(plan_rows)
    plan["final_selected_count"] = plan["primary_role"].map(final_counts).fillna(0).astype(int)
    plan["final_deficit_or_surplus"] = plan["final_selected_count"] - plan["target_count"]
    plan["claim_boundary"] = CLAIM_BOUNDARY
    columns = [
        "cell_id",
        "selected_priority_rank",
        "primary_role",
        "secondary_roles",
        "rationale",
        "spatial_bin",
        "typology",
        "nearest_anchor_cell",
        "nearest_neutral_cell",
        "nearest_n150_distance",
        "nearest_n150_distance_percentile",
        "coverage_gap",
        "expected_learning_value",
        "sampling_boundary",
        "claim_boundary",
    ]
    return selected.loc[:, columns].copy(), plan, len(current_cells)


def best_role_for_row(row: pd.Series) -> str:
    """Return the highest-scored eligible role for fallback fill."""
    eligible_roles = [role for role in ROLE_ORDER if bool(row.get(f"eligible_{role}", False))]
    if not eligible_roles:
        return "control_cell"
    return max(eligible_roles, key=lambda role: as_float(row.get(f"score_{role}"), 0.0))


def review_text(design: pd.DataFrame, plan: pd.DataFrame, v1: pd.DataFrame) -> str:
    """Build the B8.6f N300 v2 review Markdown."""
    role_mix = design["primary_role"].value_counts().rename_axis("primary_role").reset_index(name="count")
    spatial_mix = design["spatial_bin"].value_counts().rename_axis("spatial_bin").reset_index(name="count")
    typology_mix = design["typology"].value_counts().rename_axis("typology").reset_index(name="count")
    anchor_mix = design["nearest_anchor_cell"].value_counts().rename_axis("nearest_anchor_cell").reset_index(name="count")
    neutral_mix = design["nearest_neutral_cell"].value_counts().rename_axis("nearest_neutral_cell").reset_index(name="count")
    sparse_count = int((pd.to_numeric(design["nearest_n150_distance_percentile"], errors="coerce") >= 0.90).sum())
    weak_bins = {"west_north", "west_south", "east_south", "east_north"}
    weak_coverage = design.loc[design["spatial_bin"].astype(str).isin(weak_bins), "spatial_bin"].value_counts().rename_axis("weak_spatial_bin").reset_index(name="selected_count")
    v1_role = v1.loc[v1["audit_dimension"].astype(str).eq("primary_role"), ["value", "count", "target_count_in_v2", "verdict"]]
    return f"""# B8.6f Targeted N300 Design v2 Review

This is a candidate design only. It is not a SOLWEIG manifest, QGIS runner,
N300 execution package, AOI-wide prediction, B9 output, WBGT output, hazard or
risk score, or System A/B coupling output.

## V1 Audit

{md_table(v1_role, ['value', 'count', 'target_count_in_v2', 'verdict'])}

## Role Quota Plan

{md_table(plan, ['primary_role', 'target_count', 'available_before_deconflict', 'selected_before_reallocation', 'final_selected_count', 'final_deficit_or_surplus'])}

## V2 Role Mix

{md_table(role_mix, ['primary_role', 'count'])}

## Spatial Bin Mix

{md_table(spatial_mix, ['spatial_bin', 'count'])}

## Typology Mix

{md_table(typology_mix, ['typology', 'count'], max_rows=15)}

## Nearest Anchor Distribution

{md_table(anchor_mix, ['nearest_anchor_cell', 'count'])}

## Nearest Neutral Distribution

{md_table(neutral_mix, ['nearest_neutral_cell', 'count'])}

## Sparse Feature-Space Count

Sparse feature-space candidates at nearest-N150 distance percentile >= 0.90:
{sparse_count}.

## Coverage Of B8.6e Worst Bins

{md_table(weak_coverage, ['weak_spatial_bin', 'selected_count'])}

## Claim Boundary

The v2 list is role-balanced review evidence only. It must not be treated as
an N300 SOLWEIG manifest, a QGIS runner, an AOI-wide prediction, B9 evidence,
local WBGT, hazard/risk scoring, observed truth, causal feature importance, or
System A/B coupling.
"""


def run(config_path: Path = DEFAULT_CONFIG) -> N300DesignResult:
    """Run B8.6f N300 v1 audit and role-balanced v2 candidate design."""
    config = load_config(config_path)
    v1 = v1_audit(config)
    design, plan, current_count = select_role_balanced_design(config)
    write_csv(v1, output_path(config, "n300_design_v1_audit"))
    write_csv(plan, output_path(config, "n300_role_quota_plan"))
    write_csv(design, output_path(config, "targeted_n300_design_v2"))
    write_text(review_text(design, plan, v1), output_path(config, "targeted_n300_design_review"))
    status = "B86F_N300_V2_BALANCED_READY" if len(design) == int(config["n300_target_additional_count"]) else "B86F_N300_V2_INCOMPLETE"
    return N300DesignResult(status=status, selected_rows=len(design), quota_roles=len(plan), current_cells=current_count)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Audit B8.6e N300 v1 and create B8.6f role-balanced N300 v2.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
