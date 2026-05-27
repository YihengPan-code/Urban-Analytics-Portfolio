"""Join B8.6g feature coverage to B8.6f failure contexts.

Inputs:
    B8.6g N150/N300 feature datasets, B8.6f anchor/neutral failure matrix,
    B8.6f failure synthesis, and B8.6g feature family readiness.
Outputs:
    b86g_failure_context_feature_join.csv.
Saved metrics:
    Feature coverage for anchor cells, known neutral cells, near-zero
    false-promotion cells, weak spatial bins, and typology contexts. This is a
    diagnostic join only; it creates no target, model, raster, QGIS/SOLWEIG,
    AOI-wide, B9, WBGT, hazard/risk, observed-truth, causal
    feature-importance, Tmrt-to-WBGT, or System A/B coupling output.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86g_feature_readiness import FAMILY_FEATURE_COLUMNS
from v12_b86g_source_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, load_config, output_path, read_csv, write_csv


@dataclass(frozen=True)
class FailureJoinResult:
    """Failure context join result."""

    status: str
    rows: int
    anchor_rows: int
    neutral_rows: int


HEADLINE_COLUMNS = [
    "ped_access_shade_frac_proxy",
    "sunlit_hot_pocket_proxy_frac",
    "overhead_total_area_m2",
    "tree_building_overlap_proxy",
    "height_roughness_iqr_m",
    "typology_geometry_class",
]


def coverage_flags(frame: pd.DataFrame) -> pd.DataFrame:
    """Add per-family non-null coverage flags to a feature frame."""
    out = frame.copy()
    for family, columns in FAMILY_FEATURE_COLUMNS.items():
        flag = family.lower().replace(" / ", "_").replace("-", "_").replace(" ", "_").replace("/", "_")
        present = [column for column in columns if column in out.columns]
        out[f"{flag}_covered"] = out[present].notna().any(axis=1) if present else False
    return out


def load_feature_union(config: dict[str, Any]) -> pd.DataFrame:
    """Load N150 and N300 feature datasets with membership labels."""
    n150 = read_csv(output_path(config, "n150_feature_dataset_path"))
    n150["dataset_membership"] = "N150_LABELLED"
    n300 = read_csv(output_path(config, "n300_candidate_feature_dataset_path"))
    n300["dataset_membership"] = "B86F_N300_V2_CANDIDATE"
    union = pd.concat([n150, n300], ignore_index=True)
    union = union.drop_duplicates("cell_id", keep="first")
    return coverage_flags(union)


def cell_context_rows(config: dict[str, Any], feature_union: pd.DataFrame) -> pd.DataFrame:
    """Create one row per B8.6f failure context cell."""
    failure = read_csv(config["b86f_anchor_neutral_matrix_path"])
    joined = failure.merge(feature_union, on="cell_id", how="left", suffixes=("", "_feature"))
    joined["row_type"] = "cell_failure_context"
    for column in HEADLINE_COLUMNS:
        if column not in joined.columns:
            joined[column] = pd.NA
    coverage_columns = [column for column in joined.columns if column.endswith("_covered")]
    joined["feature_family_coverage_count"] = joined[coverage_columns].sum(axis=1)
    joined["feature_family_coverage_fraction"] = joined["feature_family_coverage_count"] / max(len(coverage_columns), 1)
    keep = [
        "row_type",
        "cell_id",
        "diagnostic_role",
        "split_family",
        "spatial_bin",
        "typology",
        "failure_type",
        "severity",
        "dataset_membership",
        "feature_family_coverage_count",
        "feature_family_coverage_fraction",
    ] + coverage_columns + HEADLINE_COLUMNS
    out = joined[keep].copy()
    out["claim_boundary"] = CLAIM_BOUNDARY
    return out


def spatial_bin_summary_rows(config: dict[str, Any], cell_rows: pd.DataFrame) -> pd.DataFrame:
    """Create weak-spatial-bin summary rows from failure contexts."""
    coverage_columns = [column for column in cell_rows.columns if column.endswith("_covered")]
    rows: list[dict[str, Any]] = []
    failure_synthesis = read_csv(config["b86f_failure_synthesis_path"])
    affected = "|".join(failure_synthesis["affected_bins_or_cells"].fillna("").astype(str).tolist())
    weak_bins = sorted({part for part in affected.replace(",", "|").split("|") if part in {"west_north", "west_south", "east_south", "east_north"}})
    for spatial_bin in weak_bins:
        subset = cell_rows.loc[cell_rows["spatial_bin"].astype(str).eq(spatial_bin)]
        row: dict[str, Any] = {
            "row_type": "weak_spatial_bin_summary",
            "cell_id": "",
            "diagnostic_role": "weak_spatial_bin",
            "split_family": "",
            "spatial_bin": spatial_bin,
            "typology": "|".join(sorted(subset["typology"].dropna().astype(str).unique())) if not subset.empty else "",
            "failure_type": "spatial-bin-out-of-domain",
            "severity": "review",
            "dataset_membership": "failure_context_aggregate",
            "feature_family_coverage_count": subset["feature_family_coverage_count"].mean() if not subset.empty else 0,
            "feature_family_coverage_fraction": subset["feature_family_coverage_fraction"].mean() if not subset.empty else 0,
            "claim_boundary": CLAIM_BOUNDARY,
        }
        for column in coverage_columns:
            row[column] = bool(subset[column].mean() >= 0.8) if not subset.empty else False
        for column in HEADLINE_COLUMNS:
            row[column] = ""
        rows.append(row)
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> FailureJoinResult:
    """Run B8.6g failure-context feature join."""
    config = load_config(config_path)
    features = load_feature_union(config)
    cell_rows = cell_context_rows(config, features)
    bin_rows = spatial_bin_summary_rows(config, cell_rows)
    out = pd.concat([cell_rows, bin_rows], ignore_index=True, sort=False)
    write_csv(out, output_path(config, "failure_context_feature_join_path"))
    anchor = int(cell_rows["diagnostic_role"].astype(str).str.contains("anchor", case=False, na=False).sum())
    neutral = int(cell_rows["diagnostic_role"].astype(str).str.contains("neutral|near_zero", case=False, na=False, regex=True).sum())
    return FailureJoinResult(status="B86G_FAILURE_CONTEXT_JOIN_READY", rows=len(out), anchor_rows=anchor, neutral_rows=neutral)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Join B8.6g features to B8.6f failure contexts.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
