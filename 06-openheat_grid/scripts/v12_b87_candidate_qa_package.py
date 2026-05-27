"""Create the B8.7 human QA package for N300 candidates.

Inputs:
    B8.7 N300 design-freeze candidates, B8.7 feature coverage audit, B8.7
    true-vector source gap register, and B8.6g N300 feature dataset declared in
    the B8.7 config.
Outputs:
    b87_n300_manual_qa_checklist.csv and b87_n300_manual_qa_guide.md.
Saved metrics:
    Candidate-level QA priority, role/spatial/typology/anchor/neutral context,
    sparse feature-space risk, feature-coverage status, true-vector source
    missing flags, QA question, and recommended action. This package is for
    human review only and creates no SOLWEIG manifest, QGIS runner, raster I/O,
    AOI/B9 product, WBGT/hazard/risk/exposure/vulnerability score, observed
    truth, causal feature importance, Tmrt-to-WBGT conversion, or System A/B
    coupling output.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b87_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, as_float, load_config, output_path, read_csv, write_csv, write_text


@dataclass(frozen=True)
class CandidateQAPackageResult:
    """B8.7 candidate QA package result."""

    status: str
    checklist_rows: int
    high_priority_rows: int
    qa_path: str


SOURCE_REVIEW_ROLES = {"anchor_like_replication", "neutral_boundary_replication", "spatial_gap_fill", "sparse_feature_space"}


def source_missing_flags(gaps: pd.DataFrame) -> str:
    """Return pipe-delimited source gaps requiring human review."""
    flagged = gaps.loc[~gaps["source_status"].astype(str).eq("AVAILABLE_FOR_B86G3_REVIEW")].copy()
    if flagged.empty:
        return "none"
    return "|".join(flagged["source_category"].astype(str).tolist())


def feature_coverage_status(feature_audit: pd.DataFrame) -> str:
    """Return a concise feature coverage status for QA rows."""
    family_rows = feature_audit.loc[feature_audit["audit_scope"].astype(str).eq("feature_family")]
    not_available = family_rows.loc[family_rows["source_class"].astype(str).eq("not_available"), "feature_family"].astype(str).tolist()
    warn = family_rows.loc[family_rows["status"].astype(str).ne("PASS"), "feature_family"].astype(str).tolist()
    if not_available:
        return "missing_high_priority_source:" + "|".join(not_available)
    if warn:
        return "review_feature_coverage:" + "|".join(warn)
    return "complete_enough_for_design_review"


def qa_question(row: pd.Series, missing_flags: str) -> str:
    """Return the main human QA question for one candidate."""
    role = str(row.get("primary_role", ""))
    if role == "anchor_like_replication":
        return "Does this candidate genuinely replicate the intended anchor context without duplicating current N150 labels?"
    if role == "neutral_boundary_replication":
        return "Does this candidate help test neutral or near-zero false-promotion boundaries without overconcentrating one neutral group?"
    if role == "spatial_gap_fill":
        return "Does this candidate improve weak-bin spatial support, especially west_south/east-west balance?"
    if role == "typology_gap_fill":
        return "Does this candidate fill a feasible typology gap rather than reinforcing residential/transport concentration?"
    if role == "sparse_feature_space":
        return "Is the sparse/OOD feature-space position intentional and acceptable for a future execution precheck?"
    if "connected_shade_corridor" in missing_flags:
        return "Does this candidate require connected shade corridor evidence before any future execution precheck?"
    return "Does this candidate remain a useful control or baseline-like design case?"


def qa_priority(row: pd.Series, missing_flags: str) -> str:
    """Assign human QA priority."""
    role = str(row.get("primary_role", ""))
    flags = str(row.get("manual_qa_flags", ""))
    percentile = as_float(row.get("nearest_n150_distance_percentile"), 0.0)
    if role in SOURCE_REVIEW_ROLES or percentile >= 0.95 or "anchor" in flags or "neutral" in flags:
        return "high"
    if role == "typology_gap_fill" or flags != "none" or missing_flags != "none":
        return "medium"
    return "low"


def recommended_action(row: pd.Series, missing_flags: str) -> str:
    """Choose the candidate QA recommended action."""
    role = str(row.get("primary_role", ""))
    flags = str(row.get("manual_qa_flags", ""))
    if "overlap_with_n150" in flags:
        return "replace_candidate"
    if missing_flags != "none" and role in SOURCE_REVIEW_ROLES:
        return "needs_source_before_execution"
    if flags != "none":
        return "review"
    return "keep"


def checklist(config: dict[str, Any]) -> pd.DataFrame:
    """Build the manual QA checklist."""
    candidates = read_csv(output_path(config, "n300_design_freeze_candidates_path"))
    feature_audit = read_csv(output_path(config, "n300_feature_coverage_audit_path"))
    gaps = read_csv(output_path(config, "true_vector_source_gap_register_path"))
    missing_flags = source_missing_flags(gaps)
    coverage_status = feature_coverage_status(feature_audit)
    rows = []
    for _, row in candidates.iterrows():
        action = recommended_action(row, missing_flags)
        rows.append(
            {
                "cell_id": row.get("cell_id", ""),
                "primary_role": row.get("primary_role", ""),
                "spatial_bin": row.get("spatial_bin", ""),
                "typology": row.get("typology", ""),
                "nearest_anchor_cell": row.get("nearest_anchor_cell", ""),
                "nearest_neutral_cell": row.get("nearest_neutral_cell", ""),
                "nearest_n150_distance_percentile": row.get("nearest_n150_distance_percentile", ""),
                "feature_coverage_status": coverage_status,
                "true_vector_source_missing_flags": missing_flags,
                "qa_priority": qa_priority(row, missing_flags),
                "qa_question": qa_question(row, missing_flags),
                "recommended_action": action,
                "notes": row.get("manual_qa_flags", "none"),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def guide_text(config: dict[str, Any], checklist_frame: pd.DataFrame) -> str:
    """Create the manual QA guide Markdown."""
    high_count = int(checklist_frame["qa_priority"].astype(str).eq("high").sum())
    review_count = int((~checklist_frame["recommended_action"].astype(str).eq("keep")).sum())
    source_flags = sorted({flag for flags in checklist_frame["true_vector_source_missing_flags"].astype(str) for flag in flags.split("|") if flag and flag != "none"})
    return f"""# B8.7 N300 Manual QA Guide

This guide supports human review of the B8.6f N300 v2 candidate design after
B8.6g2. It is not an execution package, not a SOLWEIG manifest, and not a QGIS
runner.

## QA Inputs

- Candidate checklist: `{config['n300_manual_qa_checklist_path']}`
- Candidate rows: {len(checklist_frame)}
- High-priority QA rows: {high_count}
- Non-keep recommended actions: {review_count}
- Source-review flags: {', '.join(source_flags) if source_flags else 'none'}

## Inspect Top Priority Candidates

Start with rows where `qa_priority=high`, then inspect rows where
`recommended_action` is `needs_source_before_execution`, `review`, or
`replace_candidate`. Confirm the candidate is absent from current N150 labels,
the role rationale is still sensible, and sparse-feature-space cases are
intentional rather than accidental outliers.

## Check Role Balance

Use the role, spatial, typology, anchor, neutral, sparse, and control audit CSVs
in the same output folder. Treat exact role quotas as fixed. Treat west_south,
TP_0037, TP_0433, neutral-group diversity, park_open_space/commercial
undercoverage, and residential/transport concentration as manual-review items.

## Check Connected Shade Corridor Source

Do not infer corridor continuity from centroid distance, nearest-cell distance,
or generic shade fraction. A valid future source must be pedestrian/covered
walkway/shade-network line or polygon geometry, or an equivalent vector-derived
compact connectivity table whose source is explicit.

## What Not To Do

- Do not run QGIS.
- Do not run SOLWEIG.
- Do not read, copy, create, or write raster files.
- Do not create an N300 execution manifest.
- Do not create AOI-wide prediction or B9 outputs.
- Do not create local WBGT, hazard_score, risk_score, exposure/vulnerability
  score, observed-truth, causal feature-importance, Tmrt-to-WBGT conversion, or
  System A/B coupling outputs.
"""


def run(config_path: Path = DEFAULT_CONFIG) -> CandidateQAPackageResult:
    """Run the B8.7 candidate QA package builder."""
    config = load_config(config_path)
    qa = checklist(config)
    write_csv(qa, output_path(config, "n300_manual_qa_checklist_path"))
    write_text(guide_text(config, qa), output_path(config, "n300_manual_qa_guide_path"))
    high = int(qa["qa_priority"].astype(str).eq("high").sum())
    return CandidateQAPackageResult(
        status="B87_MANUAL_QA_PACKAGE_READY",
        checklist_rows=len(qa),
        high_priority_rows=high,
        qa_path=str(config["n300_manual_qa_checklist_path"]),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Create B8.7 N300 human QA checklist and guide. No SOLWEIG, QGIS, "
            "raster, AOI/B9, WBGT, hazard/risk, manifest, or execution output."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
