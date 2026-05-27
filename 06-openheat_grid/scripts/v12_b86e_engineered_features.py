"""Create safe compact engineered features for the B8.6e diagnostic probe.

Inputs:
    B8.6c hardened compact surrogate dataset, B8.6c safe feature catalog,
    B8.6e feature-gap/domain outputs, and the B8.6e config.
Outputs:
    b86e_safe_engineered_feature_catalog.csv and
    b86e_safe_engineered_feature_dataset.csv.
Saved metrics:
    Safe physical interaction features, compact heterogeneity proxies,
    coordinate quantile diagnostics, and feature-space nearest-neighbour
    diagnostics. Target-derived, path/status-derived, WBGT, hazard, risk, AOI,
    B9, and raster-derived-at-runtime features are rejected.
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
    full_safe_compact_columns,
    input_path,
    load_config,
    nearest_reference_rows,
    output_path,
    read_csv,
    robust_scaled_values,
    write_csv,
)


@dataclass(frozen=True)
class EngineeredFeatureResult:
    """Engineered feature result."""

    status: str
    rows: int
    engineered_features: int
    coordinate_diagnostics: int


def add_feature(catalog: list[dict[str, Any]], name: str, formula: str, source_columns: list[str], role: str) -> None:
    """Append one engineered-feature catalog row."""
    catalog.append(
        {
            "feature_name": name,
            "formula": formula,
            "source_columns": "|".join(source_columns),
            "predictor_allowed": role == "safe_physical",
            "coordinate_context_dependent": role == "coordinate_diagnostic",
            "diagnostic_only": role != "safe_physical",
            "feature_role": role,
            "rejection_reason": "" if role == "safe_physical" else "Diagnostic-only feature; not causal or production evidence.",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    )


def safe_product(out: pd.DataFrame, left: str, right: str, name: str) -> bool:
    """Create a numeric product feature if both source columns exist."""
    if left not in out.columns or right not in out.columns:
        return False
    left_values = pd.to_numeric(out[left], errors="coerce")
    right_values = pd.to_numeric(out[right], errors="coerce")
    if left_values.notna().sum() == 0 or right_values.notna().sum() == 0:
        return False
    out[name] = left_values * right_values
    return True


def add_interactions(dataset: pd.DataFrame, config: dict[str, Any], catalog: list[dict[str, Any]]) -> pd.DataFrame:
    """Add configured safe physical interactions."""
    out = dataset.copy()
    for name, pair in config["engineered_features"]["physical_interactions"].items():
        left, right = pair
        if name == "b86e__hardscape_x_low_shade":
            if left in out.columns and right in out.columns:
                out[name] = pd.to_numeric(out[left], errors="coerce") * (1.0 - pd.to_numeric(out[right], errors="coerce"))
                add_feature(catalog, name, f"{left} * (1 - {right})", [left, right], "safe_physical")
            continue
        if safe_product(out, left, right, name):
            add_feature(catalog, name, f"{left} * {right}", [left, right], "safe_physical")
    eps = float(config["engineered_features"].get("epsilon", 0.000001))
    if "overhead_fraction" in out.columns and "svf_or_open_sky" in out.columns:
        out["b86e__overhead_to_open_sky_ratio"] = pd.to_numeric(out["overhead_fraction"], errors="coerce") / (
            pd.to_numeric(out["svf_or_open_sky"], errors="coerce").abs() + eps
        )
        add_feature(
            catalog,
            "b86e__overhead_to_open_sky_ratio",
            "overhead_fraction / (abs(svf_or_open_sky) + epsilon)",
            ["overhead_fraction", "svf_or_open_sky"],
            "safe_physical",
        )
    if "shade_fraction" in out.columns:
        out["b86e__low_shade_fraction"] = 1.0 - pd.to_numeric(out["shade_fraction"], errors="coerce")
        add_feature(catalog, "b86e__low_shade_fraction", "1 - shade_fraction", ["shade_fraction"], "safe_physical")
    if "tree_or_gvi_fraction" in out.columns and "shade_fraction" in out.columns:
        out["b86e__tree_to_shade_balance"] = pd.to_numeric(out["tree_or_gvi_fraction"], errors="coerce") / (
            pd.to_numeric(out["shade_fraction"], errors="coerce").abs() + eps
        )
        add_feature(
            catalog,
            "b86e__tree_to_shade_balance",
            "tree_or_gvi_fraction / (abs(shade_fraction) + epsilon)",
            ["tree_or_gvi_fraction", "shade_fraction"],
            "safe_physical",
        )
    return out


def add_heterogeneity(dataset: pd.DataFrame, catalog: list[dict[str, Any]]) -> pd.DataFrame:
    """Add compact heterogeneity proxies when source columns are present."""
    out = dataset.copy()
    if {"cu__svf_umep_p90_open_v10", "cu__svf_umep_p10_open_v10"}.issubset(out.columns):
        out["b86e__svf_open_p90_p10_range_v10"] = (
            pd.to_numeric(out["cu__svf_umep_p90_open_v10"], errors="coerce")
            - pd.to_numeric(out["cu__svf_umep_p10_open_v10"], errors="coerce")
        )
        add_feature(
            catalog,
            "b86e__svf_open_p90_p10_range_v10",
            "cu__svf_umep_p90_open_v10 - cu__svf_umep_p10_open_v10",
            ["cu__svf_umep_p90_open_v10", "cu__svf_umep_p10_open_v10"],
            "safe_physical",
        )
    shade_cols = [f"cu__shade_fraction_umep_{hour:04d}_open_v10" for hour in range(800, 2000, 100)]
    present = [column for column in shade_cols if column in out.columns]
    if len(present) >= 3:
        values = out[present].apply(pd.to_numeric, errors="coerce")
        out["b86e__shade_open_hourly_range_v10"] = values.max(axis=1) - values.min(axis=1)
        add_feature(
            catalog,
            "b86e__shade_open_hourly_range_v10",
            "max(hourly open shade fractions) - min(hourly open shade fractions)",
            present,
            "safe_physical",
        )
    if {"cu__dsm_building_height_p90_m_v10", "cu__dsm_building_height_mean_m_v10"}.issubset(out.columns):
        out["b86e__building_height_p90_minus_mean_v10"] = (
            pd.to_numeric(out["cu__dsm_building_height_p90_m_v10"], errors="coerce")
            - pd.to_numeric(out["cu__dsm_building_height_mean_m_v10"], errors="coerce")
        )
        add_feature(
            catalog,
            "b86e__building_height_p90_minus_mean_v10",
            "cu__dsm_building_height_p90_m_v10 - cu__dsm_building_height_mean_m_v10",
            ["cu__dsm_building_height_p90_m_v10", "cu__dsm_building_height_mean_m_v10"],
            "safe_physical",
        )
    return out


def add_coordinate_diagnostics(dataset: pd.DataFrame, config: dict[str, Any], catalog: list[dict[str, Any]]) -> pd.DataFrame:
    """Add coordinate quantile bins as diagnostic-only features."""
    out = dataset.copy()
    bins = int(config["engineered_features"].get("coordinate_bins", 4))
    for source, name in [("centroid_x", "b86e__centroid_x_qbin"), ("centroid_y", "b86e__centroid_y_qbin")]:
        if source not in out.columns:
            continue
        cell_values = out.drop_duplicates("cell_id")[["cell_id", source]].copy()
        try:
            cell_values[name] = pd.qcut(pd.to_numeric(cell_values[source], errors="coerce"), q=bins, labels=False, duplicates="drop")
        except ValueError:
            cell_values[name] = 0
        cell_values[name] = cell_values[name].fillna(-1).astype(int).astype(str)
        out = out.drop(columns=[name], errors="ignore").merge(cell_values[["cell_id", name]], on="cell_id", how="left")
        add_feature(catalog, name, f"{source} quantile bin", [source], "coordinate_diagnostic")
    return out


def add_feature_space_diagnostics(dataset: pd.DataFrame, config: dict[str, Any], catalog: list[dict[str, Any]]) -> pd.DataFrame:
    """Add nearest-neighbour distance diagnostics by cell."""
    out = dataset.copy()
    cells = out.drop_duplicates("cell_id").copy()
    features = [
        column
        for column in full_safe_compact_columns(config, cells, include_coordinate=False)
        if column in cells.columns and pd.to_numeric(cells[column], errors="coerce").notna().sum() > 0
    ]
    if not features:
        return out
    scaled, _, _ = robust_scaled_values(cells, features)
    values = scaled.to_numpy(dtype=float)
    nn_distances: list[float] = []
    for idx, row in enumerate(values):
        distances = np.sqrt(np.sum((values - row) ** 2, axis=1))
        distances[idx] = np.inf
        nn_distances.append(float(np.min(distances)))
    cells["b86e__feature_space_nn_distance"] = nn_distances
    cells["b86e__feature_space_nn_distance_percentile"] = cells["b86e__feature_space_nn_distance"].rank(pct=True)
    out = out.merge(
        cells[["cell_id", "b86e__feature_space_nn_distance", "b86e__feature_space_nn_distance_percentile"]],
        on="cell_id",
        how="left",
    )
    add_feature(
        catalog,
        "b86e__feature_space_nn_distance",
        "nearest labelled-cell distance under robust-scaled safe compact features",
        features,
        "distance_diagnostic",
    )
    add_feature(
        catalog,
        "b86e__feature_space_nn_distance_percentile",
        "percentile of nearest labelled-cell distance",
        ["b86e__feature_space_nn_distance"],
        "distance_diagnostic",
    )
    return out


def build_engineered_dataset(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build engineered-feature dataset and catalog."""
    dataset = read_csv(input_path(config, "b86c_hardened_dataset_path"))
    catalog_rows: list[dict[str, Any]] = []
    out = add_interactions(dataset, config, catalog_rows)
    out = add_heterogeneity(out, catalog_rows)
    out = add_coordinate_diagnostics(out, config, catalog_rows)
    out = add_feature_space_diagnostics(out, config, catalog_rows)
    out["claim_boundary"] = CLAIM_BOUNDARY
    catalog = pd.DataFrame(catalog_rows)
    return out, catalog


def run(config_path: Path = DEFAULT_CONFIG) -> EngineeredFeatureResult:
    """Write engineered-feature dataset and catalog."""
    config = load_config(config_path)
    dataset, catalog = build_engineered_dataset(config)
    write_csv(catalog, output_path(config, "safe_engineered_feature_catalog"))
    write_csv(dataset, output_path(config, "safe_engineered_feature_dataset"))
    coordinate_count = int(catalog.get("coordinate_context_dependent", pd.Series(dtype=bool)).astype(bool).sum())
    return EngineeredFeatureResult(
        status="B86E_ENGINEERED_FEATURES_READY",
        rows=len(dataset),
        engineered_features=len(catalog),
        coordinate_diagnostics=coordinate_count,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Create B8.6e safe compact engineered features and diagnostics.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
