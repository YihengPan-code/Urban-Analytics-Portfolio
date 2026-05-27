"""Create a B8.6e targeted N300 candidate design, not an execution package.

Inputs:
    B8.6e spatial failure outputs, domain distance metrics, B8.6c/F5 current
    labelled cells, and N150 candidate universe compact table.
Outputs:
    b86e_targeted_n300_candidate_design.csv and
    b86e_targeted_n300_rationale.md.
Saved metrics:
    Up to 150 additional candidate cells with coverage-gap rationale, similar
    reference cells, priority rank, and expected role. This creates no SOLWEIG
    manifest, no QGIS runner, no AOI-wide predictions, and no B9 output.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86e_feature_gap_audit import safe_candidate_numeric_features
from v12_b86e_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    add_spatial_bin,
    cell_feature_frame,
    input_path,
    load_config,
    nearest_reference_rows,
    output_path,
    read_csv,
    write_csv,
    write_text,
)


@dataclass(frozen=True)
class TargetedSamplingResult:
    """Targeted sampling result."""

    status: str
    candidate_rows: int
    current_cells: int
    pool_cells: int


def candidate_pool(config: dict[str, Any]) -> tuple[pd.DataFrame, set[str], pd.DataFrame]:
    """Return eligible candidate pool beyond current N150 labelled cells."""
    candidate = read_csv(input_path(config, "candidate_universe_path"))
    labels = read_csv(input_path(config, "f5_pairwise_label_path"))
    current_cells = set(labels["cell_id"].astype(str).unique())
    current_reference = candidate.loc[candidate["cell_id"].astype(str).isin(current_cells)].copy()
    reference_bins = add_spatial_bin(cell_feature_frame(config))
    candidate = add_spatial_bin(candidate, reference=reference_bins)
    pool = candidate.loc[~candidate["cell_id"].astype(str).isin(current_cells)].copy()
    if "eligible" in pool.columns:
        pool = pool.loc[pool["eligible"].astype(str).str.lower().isin({"true", "1", "yes", "nan"}) | pool["eligible"].isna()].copy()
    return pool.reset_index(drop=True), current_cells, current_reference.reset_index(drop=True)


def weak_sets(config: dict[str, Any]) -> tuple[set[str], set[tuple[str, str]]]:
    """Load weak spatial and typology-spatial targets."""
    spatial = read_csv(output_path(config, "spatial_holdout_failure_summary"))
    cross = read_csv(output_path(config, "typology_spatial_cross_failure"))
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
    return weak_bins, weak_cross


def top_reference_strings(pool: pd.DataFrame, reference: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Attach top-three nearest current N150 reference cells."""
    nearest = nearest_reference_rows(pool, reference, features, top_n=3)
    if nearest.empty:
        pool["similar_reference_cells"] = ""
        pool["nearest_n150_distance"] = np.nan
        return pool
    refs = nearest.groupby("cell_id").agg(
        similar_reference_cells=("nearest_cell_id", lambda values: "|".join(values.astype(str).head(3))),
        nearest_n150_distance=("feature_space_distance", "min"),
    )
    out = pool.merge(refs, left_on="cell_id", right_index=True, how="left")
    return out


def score_candidates(config: dict[str, Any]) -> tuple[pd.DataFrame, int, int]:
    """Score candidate-universe rows for targeted N300 design."""
    pool, current_cells, reference = candidate_pool(config)
    if pool.empty:
        return pd.DataFrame(), len(current_cells), 0
    features = safe_candidate_numeric_features(config, pd.concat([pool, reference], ignore_index=True))
    weak_bins, weak_cross = weak_sets(config)
    pool = top_reference_strings(pool, reference, features)
    anchor_ref = reference.loc[reference["cell_id"].astype(str).isin(set(config["anchor_cells"]))].copy()
    neutral_ref = reference.loc[reference["cell_id"].astype(str).isin(set(config["known_neutral_cells"]))].copy()
    anchor_nearest = nearest_reference_rows(pool, anchor_ref, features, top_n=1) if not anchor_ref.empty else pd.DataFrame()
    neutral_nearest = nearest_reference_rows(pool, neutral_ref, features, top_n=1) if not neutral_ref.empty else pd.DataFrame()
    if not anchor_nearest.empty:
        pool = pool.merge(
            anchor_nearest[["cell_id", "nearest_cell_id", "feature_space_distance"]].rename(
                columns={"nearest_cell_id": "nearest_anchor_cell", "feature_space_distance": "anchor_distance"}
            ),
            on="cell_id",
            how="left",
        )
    if not neutral_nearest.empty:
        pool = pool.merge(
            neutral_nearest[["cell_id", "nearest_cell_id", "feature_space_distance"]].rename(
                columns={"nearest_cell_id": "nearest_neutral_cell", "feature_space_distance": "neutral_distance"}
            ),
            on="cell_id",
            how="left",
        )
    pool["nearest_n150_distance_percentile"] = pd.to_numeric(pool["nearest_n150_distance"], errors="coerce").rank(pct=True)
    sparse_cut = float(config["targeted_sampling"]["sparse_distance_percentile"])
    problem_tokens = [token.lower() for token in config["targeted_sampling"]["problem_typology_tokens"]]
    rows: list[dict[str, Any]] = []
    for _, row in pool.iterrows():
        typology = str(row.get("typology_label", "unknown"))
        spatial_bin = str(row.get("spatial_bin", "unknown"))
        gaps: list[str] = []
        score = 0.0
        role = "control_cell"
        if spatial_bin in weak_bins:
            score += 40.0
            gaps.append("weak_spatial_bin")
            role = "spatial_gap_fill"
        if (typology, spatial_bin) in weak_cross:
            score += 30.0
            gaps.append("weak_typology_spatial_bin")
            role = "typology_gap_fill"
        if pd.notna(row.get("anchor_distance")):
            anchor_score = max(0.0, 25.0 - float(row["anchor_distance"]))
            if anchor_score > 15.0:
                gaps.append("anchor_like_neighbour")
                role = "anchor_like_replication"
            score += anchor_score
        if pd.notna(row.get("neutral_distance")):
            neutral_score = max(0.0, 20.0 - float(row["neutral_distance"]))
            if neutral_score > 12.0 and role == "control_cell":
                gaps.append("neutral_boundary_like_neighbour")
                role = "neutral_boundary_replication"
            score += neutral_score
        if pd.notna(row.get("nearest_n150_distance_percentile")) and float(row["nearest_n150_distance_percentile"]) >= sparse_cut:
            score += 20.0
            gaps.append("sparse_feature_space")
            if role == "control_cell":
                role = "sparse_feature_space"
        overhead = float(pd.to_numeric(pd.Series([row.get("overhead_fraction_total")]), errors="coerce").iloc[0] or 0.0)
        shade = float(pd.to_numeric(pd.Series([row.get("shade_fraction_overhead_sens")]), errors="coerce").iloc[0] or 0.0)
        svf = float(pd.to_numeric(pd.Series([row.get("svf")]), errors="coerce").iloc[0] or 0.0)
        if overhead > 0.05 or (shade > 0.65 and svf > 0.45) or (shade < 0.25 and svf > 0.65):
            score += 15.0
            gaps.append("high_overhead_or_shade_svf_contrast")
        if any(token in typology.lower() for token in problem_tokens):
            score += 10.0
            gaps.append("problem_typology")
        rows.append(
            {
                "cell_id": row["cell_id"],
                "rationale": "; ".join(gaps) if gaps else "control candidate for coverage balance",
                "priority_score": score,
                "coverage_gap": "|".join(dict.fromkeys(gaps)) if gaps else "control_cell",
                "similar_reference_cells": row.get("similar_reference_cells", ""),
                "expected_role": role,
                "spatial_bin": spatial_bin,
                "typology": typology,
                "nearest_anchor_cell": row.get("nearest_anchor_cell", ""),
                "nearest_neutral_cell": row.get("nearest_neutral_cell", ""),
                "nearest_n150_distance": row.get("nearest_n150_distance", np.nan),
                "nearest_n150_distance_percentile": row.get("nearest_n150_distance_percentile", np.nan),
                "sampling_boundary": "candidate_design_only_not_N300_run_ready",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    scored = pd.DataFrame(rows).sort_values(
        ["priority_score", "nearest_n150_distance_percentile", "cell_id"],
        ascending=[False, False, True],
    )
    max_rows = int(config["targeted_sampling"]["max_additional_cells"])
    selected = scored.head(max_rows).copy()
    selected.insert(1, "selected_priority_rank", range(1, len(selected) + 1))
    return selected, len(current_cells), len(pool)


def rationale_text(design: pd.DataFrame, current_cells: int, pool_cells: int) -> str:
    """Build a short Markdown rationale for the targeted N300 candidate design."""
    if design.empty:
        headline = "Candidate universe did not support additional compact candidates beyond current N150."
    else:
        roles = design["expected_role"].value_counts().to_dict()
        role_text = ", ".join(f"{key}={value}" for key, value in roles.items())
        headline = f"Selected {len(design)} candidate-design cells from {pool_cells} non-current compact candidates. Role mix: {role_text}."
    return f"""# B8.6e Targeted N300 Candidate Design Rationale

{headline}

This is a sampling design only. It is not N300 run-ready, does not create a
SOLWEIG manifest, does not call QGIS or SOLWEIG, and does not create AOI-wide,
B9, WBGT, hazard, risk, or System A/B coupling outputs.

Current labelled cells: {current_cells}

Candidate pool beyond current labelled cells: {pool_cells}

Priority rules used: weak spatial bins, weak typology-spatial bins, anchor-like
nearest neighbours, neutral-boundary-like neighbours, sparse feature-space bins,
high-overhead/high-shade/high-SVF contrast, and problem typologies.
"""


def run(config_path: Path = DEFAULT_CONFIG) -> TargetedSamplingResult:
    """Write targeted N300 candidate design and rationale."""
    config = load_config(config_path)
    design, current_cells, pool_cells = score_candidates(config)
    write_csv(design, output_path(config, "targeted_n300_candidate_design"))
    write_text(rationale_text(design, current_cells, pool_cells), output_path(config, "targeted_n300_rationale"))
    status = "B86E_TARGETED_N300_DESIGN_READY" if not design.empty else "B86E_TARGETED_N300_NOT_SUPPORTED"
    return TargetedSamplingResult(status=status, candidate_rows=len(design), current_cells=current_cells, pool_cells=pool_cells)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Create B8.6e targeted N300 candidate-design CSV only.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
