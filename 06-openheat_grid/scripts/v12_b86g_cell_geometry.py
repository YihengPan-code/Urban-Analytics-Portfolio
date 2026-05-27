"""Build B8.6g N150/N300 cell geometry and compact base tables.

Inputs:
    B8.6g config, B8.6d OOF predictions, B8.6f N300 v2 candidate design,
    n150 sampling feature matrix, and the v12 candidate universe.
Outputs:
    b86g_cell_geometry_inventory.csv.
Saved metrics:
    N150/N300 membership, centroid availability, lon/lat availability, cell
    area, estimated 100 m cell width, geometry source, and geometry-dependent
    readiness. No raster, QGIS, SOLWEIG, AOI-wide prediction, B9, WBGT,
    hazard/risk, observed-truth, causal feature-importance, Tmrt-to-WBGT, or
    System A/B coupling output is created.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v12_b86g_source_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    load_config,
    output_path,
    read_csv,
    write_csv,
)


@dataclass(frozen=True)
class CellGeometryResult:
    """Cell geometry inventory result."""

    status: str
    n150_cells: int
    n300_cells: int
    geometry_ready_cells: int


def numeric(series: pd.Series) -> pd.Series:
    """Return a numeric copy of a series."""
    return pd.to_numeric(series, errors="coerce")


def unique_cell_ids(frame: pd.DataFrame) -> list[str]:
    """Return stable unique cell IDs from a frame."""
    return [str(value) for value in frame["cell_id"].dropna().astype(str).drop_duplicates().tolist()]


def load_cell_sets(config: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Load labelled N150 cells and B8.6f N300 v2 candidate cells."""
    oof = read_csv(config["b86d_oof_predictions_path"], usecols=["cell_id"])
    n300 = read_csv(config["b86f_n300_v2_path"], usecols=["cell_id"])
    return sorted(unique_cell_ids(oof)), sorted(unique_cell_ids(n300))


def first_present(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the first present column from a candidate list."""
    for column in candidates:
        if column in frame.columns:
            return column
    return None


def load_compact_base(config: dict[str, Any]) -> pd.DataFrame:
    """Create a compact cell-level base table for B8.6g feature builders."""
    candidate = read_csv(config["candidate_universe_path"])
    sampling = read_csv(config["n150_feature_matrix_path"])
    candidate = candidate.drop_duplicates("cell_id", keep="first")
    sampling = sampling.drop_duplicates("cell_id", keep="first")
    overlap = [column for column in sampling.columns if column != "cell_id" and column in candidate.columns]
    sampling_extra = sampling.drop(columns=overlap, errors="ignore")
    base = candidate.merge(sampling_extra, on="cell_id", how="left", suffixes=("", "_sampling"))
    if "typology_label" not in base.columns and "typology" in base.columns:
        base["typology_label"] = base["typology"]
    return base


def build_cell_geometry_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Build N150/N300 geometry readiness rows."""
    n150_cells, n300_cells = load_cell_sets(config)
    base = load_compact_base(config)
    wanted = pd.DataFrame({"cell_id": sorted(set(n150_cells).union(n300_cells))})
    geometry = wanted.merge(base, on="cell_id", how="left").copy()
    geometry["in_n150_labelled_set"] = geometry["cell_id"].isin(n150_cells)
    geometry["in_b86f_n300_v2_candidate_set"] = geometry["cell_id"].isin(n300_cells)
    geometry["centroid_x"] = numeric(geometry["centroid_x"]) if "centroid_x" in geometry.columns else np.nan
    geometry["centroid_y"] = numeric(geometry["centroid_y"]) if "centroid_y" in geometry.columns else np.nan
    if "lon" in geometry.columns:
        geometry["lon"] = numeric(geometry["lon"])
    else:
        geometry["lon"] = np.nan
    if "lat" in geometry.columns:
        geometry["lat"] = numeric(geometry["lat"])
    else:
        geometry["lat"] = np.nan
    if "cell_area_m2" in geometry.columns:
        geometry["cell_area_m2"] = numeric(geometry["cell_area_m2"])
    else:
        geometry["cell_area_m2"] = 10000.0
    geometry["cell_width_m_estimate"] = np.sqrt(geometry["cell_area_m2"])
    centroid_ready = geometry["centroid_x"].notna() & geometry["centroid_y"].notna()
    lonlat_ready = geometry["lon"].notna() & geometry["lat"].notna()
    geometry["geometry_source"] = np.where(
        centroid_ready,
        "candidate_universe_centroid",
        np.where(lonlat_ready, "candidate_universe_lonlat", "missing_geometry"),
    )
    geometry["geometry_status"] = np.where(
        centroid_ready,
        "CENTROID_READY",
        np.where(lonlat_ready, "LONLAT_ONLY", "GEOMETRY_BLOCKED"),
    )
    geometry["geometry_dependent_feature_status"] = np.where(
        centroid_ready,
        "READY_FOR_COMPACT_DISTANCE_CONTEXT",
        "BLOCKED_GEOMETRY_DEPENDENT_FEATURES",
    )
    if "typology_label" not in geometry.columns and "typology" in geometry.columns:
        geometry["typology_label"] = geometry["typology"]
    if "typology_label" not in geometry.columns:
        geometry["typology_label"] = ""
    output = geometry[
        [
            "cell_id",
            "in_n150_labelled_set",
            "in_b86f_n300_v2_candidate_set",
            "typology_label",
            "centroid_x",
            "centroid_y",
            "lon",
            "lat",
            "cell_area_m2",
            "cell_width_m_estimate",
            "geometry_source",
            "geometry_status",
            "geometry_dependent_feature_status",
        ]
    ].copy()
    output["claim_boundary"] = CLAIM_BOUNDARY
    return output


def run(config_path: Path = DEFAULT_CONFIG) -> CellGeometryResult:
    """Run B8.6g cell geometry inventory."""
    config = load_config(config_path)
    inventory = build_cell_geometry_inventory(config)
    write_csv(inventory, output_path(config, "cell_geometry_inventory_path"))
    n150 = int(inventory["in_n150_labelled_set"].sum())
    n300 = int(inventory["in_b86f_n300_v2_candidate_set"].sum())
    ready = int(inventory["geometry_status"].astype(str).eq("CENTROID_READY").sum())
    expected_n150 = int(config.get("expected_n150_cell_count", 150))
    expected_n300 = int(config.get("expected_n300_candidate_count", 150))
    status = "B86G_CELL_GEOMETRY_READY" if n150 == expected_n150 and n300 == expected_n300 and ready > 0 else "B86G_CELL_GEOMETRY_PARTIAL"
    return CellGeometryResult(status=status, n150_cells=n150, n300_cells=n300, geometry_ready_cells=ready)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Build B8.6g N150/N300 cell geometry inventory.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
