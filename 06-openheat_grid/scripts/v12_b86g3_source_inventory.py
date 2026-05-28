"""Discover B8.6g3 compact/vector candidate sources.

Inputs:
    B8.6g3 config source-discovery roots under data/, inputs/, outputs/,
    outputs/v12*, outputs/v10*, outputs/v11*, configs/, and docs/.
Outputs:
    b86g3_source_inventory.csv.
Saved metrics:
    Path, extension, row/column counts when safe, geometry type, CRS, useful
    columns, source category, read/safety status, source confidence, and a
    true-vector support flag. Raster-like files, raw SOLWEIG outputs, raw
    archive roots, QGIS/local execution roots, svfs.zip, N300 manifests/runners,
    AOI/B9 products, WBGT/risk/hazard outputs, and System A/B coupling outputs
    are not read.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86g3_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    config_list,
    discover_candidate_paths,
    extension_key,
    inspect_path,
    load_config,
    output_path,
    write_csv,
)


@dataclass(frozen=True)
class SourceInventoryResult:
    """B8.6g3 source inventory result."""

    status: str
    sources_scanned: int
    safe_sources: int
    true_vector_candidate_sources: int


CATEGORY_TERMS = {
    "connected_shade_corridor": [
        "connected_shade",
        "shade_corridor",
        "continuity",
        "max_connected",
        "shade_gap",
        "connectivity",
        "network",
    ],
    "pedestrian_network": ["footway", "footpath", "walkway", "pedestrian", "path", "sidewalk"],
    "covered_walkway": ["covered_walkway", "covered", "shelter", "sheltered", "pedestrian_bridge"],
    "overhead_geometry": ["overhead", "viaduct", "elevated_rail", "elevated_road", "pedestrian_bridge", "covered_walkway"],
    "building_canyon": ["building", "height", "hdb3d", "ura_building", "manual_height", "canyon", "orientation"],
    "tree_building_interaction": ["tree", "canopy", "gvi", "ndvi", "building"],
    "water_park_road_edge": ["water", "river", "park", "road", "hardscape", "impervious", "edge"],
}


def tokens(text: str) -> set[str]:
    """Tokenize text for conservative source-category matching."""
    return set(re.split(r"[^a-z0-9]+", text.lower().replace("_", " ")))


def text_has(text: str, term: str) -> bool:
    """Return true when term appears as a token or phrase."""
    lowered = text.lower()
    if "_" in term:
        return term in lowered
    parts = tokens(lowered)
    return term in parts or f"{term}s" in parts


def source_text(row: pd.Series) -> str:
    """Return searchable metadata text for a source row."""
    return " ".join(
        str(row.get(column, ""))
        for column in ["path", "extension", "geometry_type", "useful_columns", "read_status", "safety_status"]
    ).lower()


def vector_like(row: pd.Series) -> bool:
    """Return true for direct vector geometry sources."""
    ext = str(row.get("extension", "")).lower()
    geometry = str(row.get("geometry_type", "")).strip()
    return ext in {".geojson", ".gpkg", ".shp"} or bool(geometry)


def compact_vector_table(row: pd.Series) -> bool:
    """Return true for compact vector-derived tables with cell IDs."""
    ext = str(row.get("extension", "")).lower()
    columns = str(row.get("useful_columns", "")).lower()
    path = str(row.get("path", "")).lower()
    if ext not in {".csv", ".csv.gz", ".parquet"}:
        return False
    if "cell_id" not in columns:
        return False
    return any(term in f"{path} {columns}" for term in ["overhead", "building", "water", "park", "road", "shade", "tree", "canyon"])


def source_categories(row: pd.Series) -> list[str]:
    """Assign broad B8.6g3 true-vector source categories."""
    text = source_text(row)
    if str(row.get("extension", "")).lower() == ".md" or str(row.get("path", "")).lower().startswith(("docs/", "configs/")):
        return ["docs_or_config_spec"]
    matches: list[str] = []
    for category, terms in CATEGORY_TERMS.items():
        if any(text_has(text, term) for term in terms):
            matches.append(category)
    return matches or ["unclassified_compact_source"]


def source_confidence(row: pd.Series, categories: list[str]) -> str:
    """Assign a conservative source-confidence tier."""
    safety = str(row.get("safety_status", ""))
    read_status = str(row.get("read_status", ""))
    if safety != "SAFE_TO_INSPECT":
        return "not_inspected_by_guardrail"
    if "READ_FAILED" in read_status:
        return "low_read_failed"
    if vector_like(row) and any(category not in {"docs_or_config_spec", "unclassified_compact_source"} for category in categories):
        return "high_direct_vector_metadata"
    if compact_vector_table(row):
        return "medium_compact_vector_derived_table"
    if str(row.get("extension", "")).lower() == ".md":
        return "doc_spec_only"
    return "low_or_context_only"


def can_support_true_vector(row: pd.Series, categories: list[str]) -> str:
    """Return yes/no for source-backed true-vector feature support."""
    if str(row.get("safety_status", "")) != "SAFE_TO_INSPECT":
        return "no"
    if "docs_or_config_spec" in categories:
        return "no"
    if vector_like(row):
        return "yes"
    if compact_vector_table(row) and any(category in categories for category in ["overhead_geometry", "building_canyon", "water_park_road_edge"]):
        return "yes"
    return "no"


def normalize_inventory(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Add B8.6g3 source-review classifications to raw path metadata."""
    output_rows: list[dict[str, Any]] = []
    for row in rows:
        series = pd.Series(row)
        categories = source_categories(series)
        output_rows.append(
            {
                **row,
                "source_category": "|".join(categories),
                "source_confidence": source_confidence(series, categories),
                "can_support_true_vector_feature": can_support_true_vector(series, categories),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(output_rows)


def run(config_path: Path = DEFAULT_CONFIG) -> SourceInventoryResult:
    """Run source discovery and write b86g3_source_inventory.csv."""
    config = load_config(config_path)
    allowed = set(config_list(config, "allowed_extensions"))
    rows = []
    for path in discover_candidate_paths(config):
        if extension_key(path) not in allowed:
            continue
        metadata = inspect_path(path, config)
        rows.append(metadata)
    inventory = normalize_inventory(rows)
    write_csv(inventory, output_path(config, "source_inventory_path"))
    safe_sources = int(inventory["safety_status"].astype(str).eq("SAFE_TO_INSPECT").sum()) if not inventory.empty else 0
    true_sources = int(inventory["can_support_true_vector_feature"].astype(str).eq("yes").sum()) if not inventory.empty else 0
    return SourceInventoryResult(
        status="B86G3_SOURCE_INVENTORY_PASS" if not inventory.empty else "B86G3_SOURCE_INVENTORY_EMPTY",
        sources_scanned=len(inventory),
        safe_sources=safe_sources,
        true_vector_candidate_sources=true_sources,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Search allowed compact/vector extensions and write B8.6g3 source "
            "inventory. Does not read raster-like files or create execution, "
            "AOI/B9, WBGT, hazard/risk, or System A/B outputs."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
