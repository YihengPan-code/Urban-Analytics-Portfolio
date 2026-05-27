"""Audit B8.6e compact feature gaps and feature-space domain distances.

Inputs:
    B8.6e failure/audit outputs, B8.6c safe and rejected feature catalogs,
    B8.6c hardened dataset, and N150 candidate universe compact table.
Outputs:
    b86e_feature_coverage_matrix.csv, b86e_feature_gap_register.csv, and
    b86e_domain_distance_metrics.csv.
Saved metrics:
    Safe/rejected feature coverage by family, actionable missing-feature
    register, robust feature-space nearest-neighbour distances by spatial
    holdout, anchor/neutral nearest-neighbour diagnostics, and candidate-universe
    nearest-neighbour context. No target-derived feature is used.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86e_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    add_spatial_bin,
    cell_feature_frame,
    full_safe_compact_columns,
    input_path,
    load_config,
    nearest_reference_rows,
    numeric_columns,
    output_path,
    read_csv,
    robust_scaled_values,
    safe_feature_catalog,
    write_csv,
)


@dataclass(frozen=True)
class FeatureGapResult:
    """Feature-gap audit result."""

    status: str
    feature_gap_rows: int
    distance_rows: int
    partial_or_missing_families: int


FEATURE_FAMILIES = [
    "pedestrian-accessible shaded fraction",
    "connected shade corridor / shade continuity",
    "overhead geometry shape descriptors",
    "sunlit-hot-pocket area fraction",
    "local boundary / edge context",
    "neighbourhood-scale context",
    "tree/building shadow interaction",
    "canyon orientation / height roughness",
    "typology-specific geometry",
    "safe coordinate-context diagnostic",
]

FAMILY_TOKENS = {
    "pedestrian-accessible shaded fraction": ["pedestrian", "shelter", "shade_fraction", "covered_walkway"],
    "connected shade corridor / shade continuity": ["corridor", "continuity", "connected"],
    "overhead geometry shape descriptors": ["overhead_area", "overhead_fraction", "viaduct", "pedestrian_bridge", "covered_walkway"],
    "sunlit-hot-pocket area fraction": ["sunlit", "hot_pocket", "open_pixel", "svf", "shade_fraction_umep"],
    "local boundary / edge context": ["distance_to_water", "distance_to_park", "edge", "boundary"],
    "neighbourhood-scale context": ["park_distance", "large_park_distance", "water_distance", "land_use"],
    "tree/building shadow interaction": ["tree", "building", "shade", "dsm"],
    "canyon orientation / height roughness": ["orientation", "roughness", "height_p90", "height_max", "dsm"],
    "typology-specific geometry": ["typology", "land_use_hint"],
    "safe coordinate-context diagnostic": ["centroid_x", "centroid_y", "spatial"],
}


def feature_coverage_matrix(config: dict[str, Any]) -> pd.DataFrame:
    """Summarize safe/rejected compact feature coverage by gap family."""
    safe = safe_feature_catalog(config)
    rejected = read_csv(input_path(config, "b86c_rejected_feature_catalog_path"))
    rows: list[dict[str, Any]] = []
    for family in FEATURE_FAMILIES:
        tokens = FAMILY_TOKENS[family]
        safe_mask = safe["dataset_column"].astype(str).str.lower().apply(lambda value: any(token in value for token in tokens))
        rejected_mask = rejected["dataset_column"].astype(str).str.lower().apply(
            lambda value: any(token in value for token in tokens)
        )
        safe_features = sorted(safe.loc[safe_mask, "dataset_column"].astype(str).unique())
        rejected_features = sorted(rejected.loc[rejected_mask, "dataset_column"].astype(str).unique())
        if family == "safe coordinate-context diagnostic":
            currently_available = "partial"
        elif safe_features:
            currently_available = "partial" if family in {"connected shade corridor / shade continuity", "sunlit-hot-pocket area fraction"} else "yes"
        else:
            currently_available = "no"
        rows.append(
            {
                "feature_family": family,
                "currently_available": currently_available,
                "safe_feature_count": len(safe_features),
                "rejected_or_metadata_feature_count": len(rejected_features),
                "example_safe_features": "|".join(safe_features[:8]),
                "example_rejected_or_metadata_features": "|".join(rejected_features[:8]),
                "coverage_note": "Compact table coverage only; this is not causal feature importance.",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def feature_gap_register(config: dict[str, Any], coverage: pd.DataFrame) -> pd.DataFrame:
    """Build the actionable feature-gap register."""
    spatial = read_csv(output_path(config, "spatial_holdout_failure_summary"))
    cross = read_csv(output_path(config, "typology_spatial_cross_failure"))
    anchor = read_csv(output_path(config, "anchor_underprediction_context"))
    neutral = read_csv(output_path(config, "neutral_false_promotion_context"))
    worst_bins = "|".join(spatial.head(3)["spatial_bin"].astype(str).tolist()) if not spatial.empty else "unknown"
    worst_cross = "|".join(
        (cross.head(3)["typology"].astype(str) + "@" + cross.head(3)["spatial_bin"].astype(str)).tolist()
    ) if not cross.empty else "unknown"
    anchor_headline = (
        f"{anchor.sort_values('mean_abs_error', ascending=False).iloc[0]['cell_id']} anchor underprediction"
        if not anchor.empty
        else "no anchor context"
    )
    neutral_headline = (
        f"{neutral.sort_values('false_promotion_rate', ascending=False).iloc[0]['cell_id']} false-promotion context"
        if not neutral.empty
        else "no neutral context"
    )
    evidence_common = (
        f"Worst spatial bins: {worst_bins}; worst typology-spatial cells: {worst_cross}; "
        f"{anchor_headline}; {neutral_headline}."
    )
    rows: list[dict[str, Any]] = []
    settings = {
        "pedestrian-accessible shaded fraction": ("partial", "yes", "yes", "yes", "high", "B8.6f safe physical feature upgrade"),
        "connected shade corridor / shade continuity": ("no", "no", "yes", "yes", "high", "targeted feature acquisition / B8.6f preflight"),
        "overhead geometry shape descriptors": ("partial", "yes", "yes", "yes", "medium-high", "B8.6f safe physical feature upgrade"),
        "sunlit-hot-pocket area fraction": ("partial", "yes", "unknown", "yes", "high", "external compact feature acquisition"),
        "local boundary / edge context": ("partial", "yes", "yes", "yes", "medium", "B8.6f safe physical feature upgrade"),
        "neighbourhood-scale context": ("partial", "yes", "yes", "yes", "medium", "targeted N300 design"),
        "tree/building shadow interaction": ("partial", "yes", "yes", "yes", "high", "B8.6f engineered feature probe"),
        "canyon orientation / height roughness": ("partial", "yes", "yes", "yes", "medium-high", "B8.6f feature acquisition"),
        "typology-specific geometry": ("partial", "yes", "yes", "yes", "medium", "targeted N300 typology balance"),
        "safe coordinate-context diagnostic": ("partial", "yes", "yes", "no", "diagnostic-only", "diagnostic only; not production predictor"),
    }
    for family in FEATURE_FAMILIES:
        row_cov = coverage.loc[coverage["feature_family"].eq(family)].iloc[0]
        current, compact, vector, requires_new, benefit, lane = settings[family]
        if row_cov["currently_available"] == "yes" and current != "no":
            current = "yes" if family not in {"tree/building shadow interaction", "canyon orientation / height roughness"} else "partial"
        rows.append(
            {
                "feature_family": family,
                "currently_available": current,
                "computable_from_existing_compact_tables": compact,
                "computable_from_existing_vector_tables_without_raster": vector,
                "requires_new_data_or_processing": requires_new,
                "expected_benefit": benefit,
                "evidence_from_failure_audit": evidence_common,
                "recommended_lane": lane,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def safe_candidate_numeric_features(config: dict[str, Any], candidate: pd.DataFrame) -> list[str]:
    """Return safe raw candidate-universe numeric features from the B8.6c catalog."""
    safe = safe_feature_catalog(config)
    subset = safe.loc[safe["source_table"].astype(str).eq("n150_candidate_universe")].copy()
    columns = [column for column in subset["column_name"].astype(str) if column in candidate.columns]
    return numeric_columns(candidate, columns)


def distance_metrics(config: dict[str, Any]) -> pd.DataFrame:
    """Compute robust feature-space domain distance diagnostics."""
    joined = read_csv(output_path(config, "failure_joined_dataset"))
    cells = add_spatial_bin(cell_feature_frame(config))
    feature_cols = numeric_columns(cells, full_safe_compact_columns(config, cells, include_coordinate=False))
    rows: list[dict[str, Any]] = []

    for spatial_bin, test in cells.groupby("spatial_bin", dropna=False):
        train = cells.loc[~cells["cell_id"].astype(str).isin(set(test["cell_id"].astype(str)))]
        nearest = nearest_reference_rows(test, train, feature_cols, top_n=1)
        if not nearest.empty:
            nearest["scope"] = "spatial_holdout_train_like_nearest"
            nearest["spatial_bin"] = spatial_bin
            rows.extend(nearest.to_dict("records"))

    current_dist = pd.DataFrame(rows)
    if not current_dist.empty:
        all_dist = current_dist["feature_space_distance"].dropna()
        current_dist["distance_percentile"] = current_dist["feature_space_distance"].rank(pct=True)
        sparse_cut = float(all_dist.quantile(0.90)) if len(all_dist) else float("nan")
        current_dist["sparse_feature_space_flag"] = current_dist["feature_space_distance"] >= sparse_cut
        rows = current_dist.to_dict("records")

    anchor_cells = set(config["anchor_cells"])
    neutral_cells = set(config["known_neutral_cells"])
    for label, references in [("anchor_like_nearest_neighbours", anchor_cells), ("neutral_like_nearest_neighbours", neutral_cells)]:
        ref = cells.loc[cells["cell_id"].astype(str).isin(references)].copy()
        qry = cells.loc[~cells["cell_id"].astype(str).isin(references)].copy()
        nearest = nearest_reference_rows(qry, ref, feature_cols, top_n=1)
        if not nearest.empty:
            nearest["scope"] = label
            nearest["reference_role"] = "anchor" if "anchor" in label else "neutral_boundary"
            rows.extend(nearest.sort_values("feature_space_distance").head(60).to_dict("records"))

    candidate = read_csv(input_path(config, "candidate_universe_path"))
    current_cells = set(cells["cell_id"].astype(str))
    candidate_features = safe_candidate_numeric_features(config, candidate)
    if candidate_features:
        ref = candidate.loc[candidate["cell_id"].astype(str).isin(current_cells)].copy()
        pool = candidate.loc[~candidate["cell_id"].astype(str).isin(current_cells)].copy()
        nearest = nearest_reference_rows(pool, ref, candidate_features, top_n=1)
        if not nearest.empty:
            nearest["scope"] = "candidate_universe_to_current_n150_nearest"
            nearest["distance_percentile"] = nearest["feature_space_distance"].rank(pct=True)
            nearest["sparse_feature_space_flag"] = nearest["distance_percentile"] >= float(
                config["targeted_sampling"]["sparse_distance_percentile"]
            )
            rows.extend(nearest.sort_values("distance_percentile", ascending=False).head(250).to_dict("records"))

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def run(config_path: Path = DEFAULT_CONFIG) -> FeatureGapResult:
    """Run feature-gap and domain-distance audit."""
    config = load_config(config_path)
    coverage = feature_coverage_matrix(config)
    gaps = feature_gap_register(config, coverage)
    distances = distance_metrics(config)
    write_csv(coverage, output_path(config, "feature_coverage_matrix"))
    write_csv(gaps, output_path(config, "feature_gap_register"))
    write_csv(distances, output_path(config, "domain_distance_metrics"))
    partial_missing = int(gaps["currently_available"].astype(str).isin({"no", "partial"}).sum())
    return FeatureGapResult(
        status="B86E_FEATURE_GAP_AUDIT_READY",
        feature_gap_rows=len(gaps),
        distance_rows=len(distances),
        partial_or_missing_families=partial_missing,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run B8.6e feature-gap and domain-distance audit.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
