"""Assemble B8.6g feature datasets and readiness/quality matrices.

Inputs:
    All B8.6g family feature tables, B8.6d OOF predictions, B8.6f N300 v2
    candidate design, B8.6f feature acquisition register, and B8.6g schema.
Outputs:
    b86g_feature_family_readiness.csv, b86g_n150_feature_dataset.csv,
    b86g_n300_candidate_feature_dataset.csv, b86g_feature_coverage_matrix.csv,
    and b86g_feature_quality_checks.csv.
Saved metrics:
    N150/N300 feature coverage, source/proxy status by family, row-count and
    duplicate checks, plausible numeric range checks, null coverage, forbidden
    target/leakage token checks, status distributions, and feature-version
    validation. Final feature datasets contain no target-derived columns,
    raster paths, output paths, local WBGT, hazard/risk score, observed-truth
    fields, or System A/B coupling fields.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86g_cell_geometry import load_cell_sets
from v12_b86g_source_inventory import DEFAULT_CONFIG, load_config, output_path, read_csv, write_csv


@dataclass(frozen=True)
class FeatureReadinessResult:
    """Feature readiness result."""

    status: str
    n150_shape: tuple[int, int]
    n300_shape: tuple[int, int]
    families_with_usable_coverage: int


FAMILY_TABLES = {
    "pedestrian-accessible shaded fraction": "pedestrian_shade_features_path",
    "connected shade corridor / shade continuity": "shade_corridor_features_path",
    "overhead geometry shape descriptors": "overhead_geometry_features_path",
    "sunlit-hot-pocket area fraction": "hot_pocket_proxy_features_path",
    "local boundary / edge context": "edge_context_features_path",
    "neighbourhood-scale context": "neighbourhood_context_features_path",
    "tree/building shadow interaction": "tree_building_interaction_features_path",
    "canyon orientation / height roughness": "canyon_orientation_features_path",
    "typology-specific geometry": "typology_geometry_features_path",
}

FAMILY_FEATURE_COLUMNS = {
    "pedestrian-accessible shaded fraction": ["ped_access_shade_frac", "ped_access_shade_frac_proxy", "ped_access_shade_length_m", "ped_access_shade_length_m_proxy", "ped_access_denominator_m"],
    "connected shade corridor / shade continuity": ["shade_corridor_continuity_idx", "max_connected_shade_length_m", "shade_gap_count"],
    "overhead geometry shape descriptors": ["overhead_patch_count", "overhead_total_area_m2", "overhead_mean_patch_area_m2", "overhead_edge_density", "overhead_total_area_proxy"],
    "sunlit-hot-pocket area fraction": ["sunlit_hot_pocket_proxy_frac", "open_high_svf_low_shade_frac"],
    "local boundary / edge context": ["water_edge_contact_frac", "park_edge_contact_frac", "hardscape_edge_contact_frac"],
    "neighbourhood-scale context": ["neighbourhood_shade_mean", "neighbourhood_overhead_frac", "neighbourhood_open_frac"],
    "tree/building shadow interaction": ["tree_building_overlap_proxy", "tree_near_tall_building_frac"],
    "canyon orientation / height roughness": ["canyon_axis_orientation_deg", "height_roughness_iqr_m", "height_asymmetry_idx"],
    "typology-specific geometry": ["typology_geometry_class", "typology_shade_interaction", "typology_support_count"],
}

HIGH_PRIORITY_FAMILIES = {
    "pedestrian-accessible shaded fraction",
    "connected shade corridor / shade continuity",
    "overhead geometry shape descriptors",
    "sunlit-hot-pocket area fraction",
    "tree/building shadow interaction",
    "canyon orientation / height roughness",
}

FORBIDDEN_DATASET_TOKENS = [
    "tmrt",
    "delta_tmrt",
    "wbgt",
    "risk",
    "hazard",
    "score",
    "rank",
    "output_path",
    "raster",
    "solweig",
    "qgis",
    "observed",
    "official",
]


def load_family_tables(config: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """Load all family feature tables."""
    return {family: read_csv(output_path(config, key)) for family, key in FAMILY_TABLES.items()}


def coverage_for(frame: pd.DataFrame, cell_ids: set[str], columns: list[str]) -> float:
    """Return row coverage for a family over a cell subset."""
    subset = frame.loc[frame["cell_id"].astype(str).isin(cell_ids)]
    present = [column for column in columns if column in subset.columns]
    if subset.empty or not present:
        return 0.0
    return float(subset[present].notna().any(axis=1).mean())


def non_null_feature_count(frame: pd.DataFrame, columns: list[str]) -> int:
    """Count family feature columns with at least one non-null value."""
    present = [column for column in columns if column in frame.columns]
    if not present:
        return 0
    return int(frame[present].notna().any(axis=0).sum())


def family_source_status(family: str, frame: pd.DataFrame) -> str:
    """Summarize source status for one family."""
    status_columns = [column for column in frame.columns if column.endswith("_source_status") or column.endswith("_status")]
    if not status_columns:
        return "COMPUTED" if non_null_feature_count(frame, FAMILY_FEATURE_COLUMNS[family]) else "NOT_AVAILABLE"
    statuses = sorted({str(value) for column in status_columns for value in frame[column].dropna().astype(str).unique()})
    if not statuses:
        return "UNKNOWN"
    if any("NOT_AVAILABLE" not in status and "BLOCKED" not in status for status in statuses):
        return "|".join(statuses)
    return statuses[0]


def family_proxy_status(family: str, frame: pd.DataFrame) -> str:
    """Classify whether a family is vector, proxy, mixed, or unavailable."""
    status = family_source_status(family, frame).upper()
    feature_cols = [column for column in FAMILY_FEATURE_COLUMNS[family] if column in frame.columns]
    if not feature_cols or not frame[feature_cols].notna().any(axis=None):
        return "NOT_AVAILABLE"
    if family in {
        "sunlit-hot-pocket area fraction",
        "tree/building shadow interaction",
        "canyon orientation / height roughness",
        "typology-specific geometry",
        "local boundary / edge context",
        "neighbourhood-scale context",
    }:
        return "PROXY_ONLY"
    if "PROXY" in status:
        if "VECTOR_DERIVED" in status:
            return "STRONG_COMPACT_VECTOR_PROXY"
        return "PROXY_ONLY"
    if "COMPACT_VECTOR_DERIVED" in status:
        return "VECTOR_DERIVED_COMPACT"
    return "DIRECT_OR_COMPACT"


def readiness_frames(config: dict[str, Any], tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build family readiness and feature coverage matrices."""
    n150_cells, n300_cells = load_cell_sets(config)
    n150_set = set(n150_cells)
    n300_set = set(n300_cells)
    register = read_csv(config["b86f_feature_acquisition_register_path"])
    register_priority = dict(zip(register["feature_family"].astype(str), register["priority"].astype(str)))
    rows = []
    for family, frame in tables.items():
        columns = FAMILY_FEATURE_COLUMNS[family]
        n150_cov = coverage_for(frame, n150_set, columns)
        n300_cov = coverage_for(frame, n300_set, columns)
        count = non_null_feature_count(frame, columns)
        source_status = family_source_status(family, frame)
        proxy_status = family_proxy_status(family, frame)
        if count == 0:
            blocked = "required vector/compact source not available"
            computed_status = "NOT_AVAILABLE"
        elif "BLOCKED" in source_status or "NOT_AVAILABLE" in source_status:
            blocked = source_status
            computed_status = "PARTIAL"
        elif proxy_status in {"PROXY_ONLY", "STRONG_COMPACT_VECTOR_PROXY"}:
            blocked = "proxy-only; requires formal feature-upgraded retest before promotion"
            computed_status = "COMPUTED_PROXY"
        else:
            blocked = ""
            computed_status = "COMPUTED"
        production_status = "candidate_after_retest" if count and n150_cov >= 0.8 else "not_ready"
        recommended = (
            "use in B8.6g2/B8.6f2 diagnostic retest"
            if count and n150_cov >= 0.8
            else "acquire missing vector source before retest"
        )
        rows.append(
            {
                "feature_family": family,
                "priority": register_priority.get(family, "unknown"),
                "b86g_computability_status": computed_status,
                "n150_coverage_fraction": n150_cov,
                "n300_coverage_fraction": n300_cov,
                "n_non_null_features": count,
                "source_status": source_status,
                "proxy_status": proxy_status,
                "production_candidate_status": production_status,
                "blocked_reason": blocked,
                "computed_columns": "|".join([column for column in columns if column in frame.columns and frame[column].notna().any()]),
                "missing_columns": "|".join([column for column in columns if column not in frame.columns or not frame[column].notna().any()]),
                "recommended_next_action": recommended,
            }
        )
    readiness = pd.DataFrame(rows)
    coverage = readiness[
        [
            "feature_family",
            "n150_coverage_fraction",
            "n300_coverage_fraction",
            "n_non_null_features",
            "source_status",
            "proxy_status",
            "production_candidate_status",
            "blocked_reason",
            "recommended_next_action",
        ]
    ].copy()
    return readiness, coverage


def prepare_for_dataset(family: str, frame: pd.DataFrame) -> pd.DataFrame:
    """Rename method/status columns to stable dataset-safe names before merge."""
    out = frame.copy()
    out = out.drop(columns=["feature_version"], errors="ignore")
    rename = {}
    if family == "pedestrian-accessible shaded fraction" and "proxy_method" in out.columns:
        rename["proxy_method"] = "ped_access_proxy_method"
    if family == "sunlit-hot-pocket area fraction" and "proxy_method" in out.columns:
        rename["proxy_method"] = "hot_pocket_proxy_method"
    if family == "tree/building shadow interaction" and "interaction_method" in out.columns:
        rename["interaction_method"] = "tree_building_interaction_method"
    return out.rename(columns=rename)


def assemble_dataset(config: dict[str, Any], tables: dict[str, pd.DataFrame], cell_ids: list[str]) -> pd.DataFrame:
    """Merge feature family tables into a one-row-per-cell dataset."""
    dataset = pd.DataFrame({"cell_id": [str(cell_id) for cell_id in cell_ids]})
    for family, frame in tables.items():
        dataset = dataset.merge(prepare_for_dataset(family, frame), on="cell_id", how="left")
    dataset["feature_version"] = str(config["output_feature_version"])
    return dataset


def forbidden_columns(dataset: pd.DataFrame) -> list[str]:
    """Find forbidden target/leakage-like dataset columns."""
    bad: list[str] = []
    for column in dataset.columns:
        lowered = column.lower()
        if column in {"cell_id", "feature_version"}:
            continue
        if any(token in lowered for token in FORBIDDEN_DATASET_TOKENS):
            bad.append(column)
    return bad


def quality_checks(config: dict[str, Any], n150: pd.DataFrame, n300: pd.DataFrame, readiness: pd.DataFrame) -> pd.DataFrame:
    """Build feature quality checks."""
    rows: list[dict[str, Any]] = []
    expected_n150 = int(config.get("expected_n150_cell_count", 150))
    expected_n300 = int(config.get("expected_n300_candidate_count", 150))

    def add(check: str, status: str, evidence: str, severity: str = "info") -> None:
        rows.append({"check_name": check, "status": status, "severity": severity, "evidence": evidence})

    add("n150_row_count", "PASS" if len(n150) == expected_n150 else "FAIL", f"rows={len(n150)} expected={expected_n150}", "high")
    add("n300_row_count", "PASS" if len(n300) == expected_n300 else "FAIL", f"rows={len(n300)} expected={expected_n300}", "high")
    add("n150_duplicate_cell_id", "PASS" if not n150["cell_id"].duplicated().any() else "FAIL", f"duplicates={int(n150['cell_id'].duplicated().sum())}", "high")
    add("n300_duplicate_cell_id", "PASS" if not n300["cell_id"].duplicated().any() else "FAIL", f"duplicates={int(n300['cell_id'].duplicated().sum())}", "high")
    bad_n150 = forbidden_columns(n150)
    bad_n300 = forbidden_columns(n300)
    add("forbidden_column_tokens", "PASS" if not bad_n150 and not bad_n300 else "FAIL", f"n150={bad_n150}; n300={bad_n300}", "high")
    add(
        "feature_version_present",
        "PASS" if "feature_version" in n150.columns and "feature_version" in n300.columns else "FAIL",
        f"version={config['output_feature_version']}",
        "high",
    )
    fraction_columns = [column for column in n150.columns if column.endswith("_frac") or column.endswith("_fraction") or column.endswith("_idx")]
    out_of_range = []
    for column in fraction_columns:
        values = pd.to_numeric(pd.concat([n150[column], n300[column]], ignore_index=True), errors="coerce").dropna()
        if not values.empty and ((values < -0.000001) | (values > 1.000001)).any():
            out_of_range.append(column)
    add("numeric_fraction_ranges", "PASS" if not out_of_range else "WARN", f"out_of_range={out_of_range}", "medium")
    null_summary = readiness[["feature_family", "n150_coverage_fraction", "n300_coverage_fraction"]].to_dict("records")
    add("family_null_coverage", "PASS", str(null_summary), "info")
    status_columns = [column for column in n150.columns if column.endswith("_status")]
    status_bits = []
    for column in status_columns:
        counts = {str(key): int(value) for key, value in n150[column].fillna("NA").astype(str).value_counts().head(5).items()}
        status_bits.append(f"{column}:{counts}")
    add("source_status_distribution", "PASS", " | ".join(status_bits) if status_bits else "no status columns", "info")
    add("no_target_columns_used", "PASS" if not bad_n150 and not bad_n300 else "FAIL", "target/leakage token scan completed", "high")
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> FeatureReadinessResult:
    """Run B8.6g feature readiness assembly."""
    config = load_config(config_path)
    tables = load_family_tables(config)
    readiness, coverage = readiness_frames(config, tables)
    n150_cells, n300_cells = load_cell_sets(config)
    n150 = assemble_dataset(config, tables, n150_cells)
    n300 = assemble_dataset(config, tables, n300_cells)
    checks = quality_checks(config, n150, n300, readiness)
    write_csv(readiness, output_path(config, "feature_family_readiness_path"))
    write_csv(coverage, output_path(config, "feature_coverage_matrix_path"))
    write_csv(n150, output_path(config, "n150_feature_dataset_path"))
    write_csv(n300, output_path(config, "n300_candidate_feature_dataset_path"))
    write_csv(checks, output_path(config, "feature_quality_checks_path"))
    usable = int((readiness["n150_coverage_fraction"] >= 0.8).sum())
    status = "B86G_FEATURE_READINESS_PASS" if not checks["status"].eq("FAIL").any() else "B86G_FEATURE_READINESS_FAILED_CHECKS"
    return FeatureReadinessResult(status=status, n150_shape=n150.shape, n300_shape=n300.shape, families_with_usable_coverage=usable)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Assemble B8.6g feature datasets and readiness matrices.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
