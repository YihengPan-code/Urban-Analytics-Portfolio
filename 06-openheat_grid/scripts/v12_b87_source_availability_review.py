"""Review true-vector and vector-derived source availability for B8.7/B8.6g3.

Inputs:
    B8.7 config source-discovery roots plus compact/vector source candidates
    under data/, inputs/, outputs/, outputs/v12*, outputs/v10*, outputs/v11*,
    configs/, and docs/.
Outputs:
    b87_true_vector_source_inventory.csv, b87_true_vector_source_gap_register.csv,
    and per-category source review CSVs for connected shade corridor,
    pedestrian network, overhead geometry, building/canyon geometry, and
    tree/building interaction.
Saved metrics:
    Source-found status, path, extension, vector CRS, geometry type, row count,
    useful columns, read/safety status, feature family supported, B8.6g3 support
    flag, and caveats. The review does not read raster-like files, svfs.zip,
    raw SOLWEIG outputs, raw archive dumps, QGIS runners, AOI/B9 products, WBGT,
    hazard/risk scores, observed-truth sources, or System A/B coupling outputs.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b87_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    discover_candidate_paths,
    inspect_source,
    load_config,
    output_path,
    write_csv,
)


@dataclass(frozen=True)
class SourceAvailabilityResult:
    """B8.7 source availability review result."""

    status: str
    reviewed_sources: int
    connected_shade_status: str
    pedestrian_network_status: str
    overhead_status: str
    building_status: str
    tree_building_status: str


CATEGORY_CONFIG = {
    "connected_shade_corridor": {
        "feature_family_supported": "connected shade corridor / shade continuity",
        "output_key": "connected_shade_corridor_source_review_path",
        "terms": ["shade_corridor", "continuity", "connected_shade", "max_connected", "shade_gap", "covered", "covered_walkway", "walkway", "footpath", "pedestrian", "shelter", "bridge", "overhead_structures"],
    },
    "pedestrian_network": {
        "feature_family_supported": "pedestrian network or covered walkway shade source",
        "output_key": "pedestrian_network_source_review_path",
        "terms": ["covered", "covered_walkway", "walkway", "footpath", "pedestrian", "shelter", "pedestrian_bridge", "bridge", "overhead_structures"],
    },
    "overhead_geometry": {
        "feature_family_supported": "overhead geometry shape descriptors",
        "output_key": "overhead_geometry_source_review_path",
        "terms": ["overhead", "pedestrian_bridge", "viaduct", "elevated_rail", "elevated_road", "covered_walkway"],
    },
    "building_canyon": {
        "feature_family_supported": "building footprint / height / canyon orientation",
        "output_key": "building_canyon_source_review_path",
        "terms": ["building", "height", "canyon", "dsm", "hdb3d", "ura_building"],
    },
    "tree_building_interaction": {
        "feature_family_supported": "tree canopy / building interaction",
        "output_key": "tree_building_interaction_source_review_path",
        "terms": ["tree", "canopy", "gvi", "ndvi", "building"],
    },
    "water_park_road_hardscape_edge": {
        "feature_family_supported": "water/park/road/hardscape edge vectors",
        "output_key": "",
        "terms": ["water", "park", "road", "hardscape", "impervious", "edge"],
    },
}


def source_text(row: pd.Series) -> str:
    """Return searchable lower-case source metadata text."""
    return " ".join(str(row.get(column, "")) for column in ["path", "likely_role", "useful_columns", "geometry_type"]).lower()


def text_has_term(text: str, term: str) -> bool:
    """Return true for a search term without matching tree inside street."""
    if term.isalpha():
        tokens = set(re.split(r"[^a-z0-9]+", text.replace("_", " ")))
        return term in tokens or f"{term}s" in tokens
    return term in text


def text_has_any(text: str, terms: list[str]) -> bool:
    """Return true when any term appears in source text."""
    return any(text_has_term(text, term) for term in terms)


def category_matches(row: pd.Series, category: str) -> bool:
    """Return whether a source row appears relevant to a review category."""
    path = str(row.get("path", "")).lower()
    extension = str(row.get("extension", "")).lower()
    if extension == ".md" or path.startswith("docs/") or path.startswith("configs/"):
        return False
    text = source_text(row)
    terms = CATEGORY_CONFIG[category]["terms"]
    return text_has_any(text, terms)


def is_vector_like(row: pd.Series) -> bool:
    """Return true if source is direct vector or vector-like compact metadata."""
    ext = str(row.get("extension", "")).lower()
    geometry = str(row.get("geometry_type", ""))
    return ext in {".geojson", ".gpkg", ".shp"} or bool(geometry)


def is_underlying_geometry_source(row: pd.Series) -> bool:
    """Return true for source geometry rather than cell grids or summary tables."""
    path = str(row.get("path", "")).lower()
    columns = str(row.get("useful_columns", "")).lower()
    excluded = [
        "per_cell",
        "grid/",
        "toa_payoh_grid",
        "completeness_map",
        "qa_targets",
        "morphology",
        "hotspot",
        "ranking",
        "surrogate",
        "feature_dataset",
        "comparison",
        "sensitivity_rank",
        "final_figures",
    ]
    true_source_hint = any(token in path for token in ["overhead_structures", "overhead_candidates", "buildings_toapayoh", "manual_missing_buildings", "manual_split_buildings", "split_replaced_originals"])
    if "cell_id" in columns and not true_source_hint:
        return False
    return is_vector_like(row) and not any(token in path for token in excluded)


def has_non_centroid_connectivity_source(row: pd.Series) -> bool:
    """Return true for candidate sources that could support corridor connectivity review."""
    text = source_text(row)
    if "centroid" in text and not text_has_any(text, ["walkway", "footpath", "pedestrian", "covered_walkway", "shelter"]):
        return False
    if "not_available" in text and "shade_corridor" in text:
        return False
    return text_has_any(text, ["walkway", "footpath", "pedestrian", "covered_walkway", "shelter", "network", "continuity"])


def support_decision(row: pd.Series, category: str) -> tuple[str, str, str]:
    """Return support level, can-support flag, and caveat for one source/category."""
    text = source_text(row)
    vector = is_vector_like(row)
    underlying = is_underlying_geometry_source(row)
    if category == "connected_shade_corridor":
        if has_non_centroid_connectivity_source(row) and underlying:
            return (
                "PARTIAL_TRUE_VECTOR_SOURCE_FOUND",
                "yes",
                "usable for B8.6g3 source acquisition, but not a validated corridor-continuity metric until pedestrian/shade-network topology is checked",
            )
        if "shade_corridor" in text or "continuity" in text:
            return (
                "NOT_AVAILABLE_COMPACT_OUTPUT_ONLY",
                "no",
                "existing compact shade-corridor table records missing source status; do not infer continuity from centroid distance",
            )
        return ("NOT_AVAILABLE_REQUIRES_MANUAL_DATA", "no", "requires pedestrian/covered-walkway/shade-network line or polygon geometry")
    if category == "pedestrian_network":
        if text_has_any(text, ["covered", "covered_walkway", "walkway", "footpath", "pedestrian", "shelter", "bridge"]) and underlying:
            return ("PARTIAL_TRUE_VECTOR_SOURCE_FOUND", "yes", "review geometry coverage and whether it represents pedestrian-accessible shade network")
        return ("NOT_AVAILABLE_REQUIRES_MANUAL_DATA", "no", "requires pedestrian-network or covered-walkway source")
    if category == "overhead_geometry":
        if text_has_any(text, ["overhead", "pedestrian_bridge", "viaduct", "elevated", "covered_walkway"]) and (vector or "cell_id" in text):
            return ("AVAILABLE", "yes", "supports overhead geometry review; still diagnostic and not observed cooling truth")
        return ("NOT_AVAILABLE_REQUIRES_MANUAL_DATA", "no", "requires overhead geometry polygon/line source or compact vector-derived table")
    if category == "building_canyon":
        if text_has_any(text, ["building", "height", "hdb3d", "ura_building"]) and (vector or "height" in text):
            return ("AVAILABLE", "yes", "supports building footprint/height/canyon acquisition; canyon axis still requires B8.6g3 derivation")
        return ("NOT_AVAILABLE_REQUIRES_MANUAL_DATA", "no", "requires building footprint/height/canyon source")
    if category == "tree_building_interaction":
        if text_has_any(text, ["tree", "canopy", "gvi", "ndvi"]) and underlying:
            return ("AVAILABLE", "yes", "supports true vector tree/building interaction if canopy geometry is complete")
        if text_has_any(text, ["tree", "canopy", "gvi", "ndvi"]):
            return ("PARTIAL_COMPACT_OR_PROXY_SOURCE_FOUND", "yes", "compact/proxy tree fields can guide B8.6g3 but do not replace true canopy geometry")
        if "building" in text and underlying:
            return ("PARTIAL_BUILDING_ONLY_SOURCE_FOUND", "yes", "building geometry alone is not a tree/building interaction source")
        return ("NOT_AVAILABLE_REQUIRES_MANUAL_DATA", "no", "requires tree canopy plus building geometry")
    if category == "water_park_road_hardscape_edge":
        if text_has_any(text, ["water", "park", "road", "hardscape", "impervious"]) and (vector or "cell_id" in text):
            return ("PARTIAL_OR_AVAILABLE", "yes", "supports edge-context review depending on AOI completeness and geometry quality")
        return ("NOT_AVAILABLE_REQUIRES_MANUAL_DATA", "no", "requires water/park/road/hardscape edge vectors or compact adjacency tables")
    return ("NOT_AVAILABLE_REQUIRES_MANUAL_DATA", "no", "unrecognized category")


def review_rows_for_category(sources: pd.DataFrame, category: str) -> pd.DataFrame:
    """Build source review rows for one category."""
    matched = sources.loc[sources.apply(lambda row: category_matches(row, category), axis=1)].copy()
    rows: list[dict[str, Any]] = []
    for _, row in matched.iterrows():
        support_level, can_support, caveat = support_decision(row, category)
        rows.append(
            {
                "source_category": category,
                "source_found": "yes",
                "path": row.get("path", ""),
                "extension": row.get("extension", ""),
                "CRS": row.get("crs", ""),
                "geometry_type": row.get("geometry_type", ""),
                "row_count": row.get("row_count", ""),
                "useful_columns": row.get("useful_columns", ""),
                "read_status": row.get("read_status", ""),
                "safety_status": row.get("safety_status", ""),
                "feature_family_supported": CATEGORY_CONFIG[category]["feature_family_supported"],
                "support_level": support_level,
                "can_support_B86G3": can_support,
                "caveat": caveat,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    if not rows:
        rows.append(
            {
                "source_category": category,
                "source_found": "no",
                "path": "",
                "extension": "",
                "CRS": "",
                "geometry_type": "",
                "row_count": "",
                "useful_columns": "",
                "read_status": "NOT_AVAILABLE",
                "safety_status": "SAFE_NO_SOURCE_FOUND",
                "feature_family_supported": CATEGORY_CONFIG[category]["feature_family_supported"],
                "support_level": "NOT_AVAILABLE_REQUIRES_MANUAL_DATA",
                "can_support_B86G3": "no",
                "caveat": "no compact/vector source discovered under configured safe roots",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def gap_register(review_by_category: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Summarize category-level true-vector source gaps."""
    rows = []
    for category, review in review_by_category.items():
        support = review["support_level"].astype(str)
        yes_count = int(review["can_support_B86G3"].astype(str).eq("yes").sum())
        source_count = int(review["source_found"].astype(str).eq("yes").sum())
        if source_count == 0:
            status = "NOT_AVAILABLE_REQUIRES_MANUAL_DATA"
            action = "manual data acquisition or external vector/network source review"
        elif support.str.startswith("AVAILABLE").any():
            status = "AVAILABLE_FOR_B86G3_REVIEW"
            action = "use in B8.6g3 source acquisition after schema/coverage QA"
        elif yes_count > 0:
            status = "PARTIAL_SOURCE_REQUIRES_QA"
            action = "review geometry completeness and derive only source-backed compact features"
        else:
            status = "NOT_AVAILABLE_REQUIRES_MANUAL_DATA"
            action = "manual data acquisition or OSM/walkway-source acquisition lane"
        if category == "connected_shade_corridor" and status != "AVAILABLE_FOR_B86G3_REVIEW":
            action = "do not infer corridor continuity; acquire/QA pedestrian covered-walkway or shade-network source"
        rows.append(
            {
                "source_category": category,
                "feature_family_supported": CATEGORY_CONFIG[category]["feature_family_supported"],
                "source_candidate_count": source_count,
                "can_support_B86G3_count": yes_count,
                "source_status": status,
                "recommended_action": action,
                "blocking_for_n300_design_freeze": "no" if status != "NOT_AVAILABLE_REQUIRES_MANUAL_DATA" else "review_required",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> SourceAvailabilityResult:
    """Run B8.7 true-vector source availability review."""
    config = load_config(config_path)
    source_rows = [inspect_source(path, config) for path in discover_candidate_paths(config)]
    sources = pd.DataFrame(source_rows)
    if sources.empty:
        sources = pd.DataFrame(
            columns=[
                "path",
                "extension",
                "file_size_bytes",
                "row_count",
                "column_count",
                "geometry_type",
                "crs",
                "useful_columns",
                "likely_role",
                "read_status",
                "safety_status",
                "claim_boundary",
            ]
        )
    review_by_category = {category: review_rows_for_category(sources, category) for category in CATEGORY_CONFIG}
    inventory = pd.concat(review_by_category.values(), ignore_index=True)
    gaps = gap_register(review_by_category)
    write_csv(inventory, output_path(config, "true_vector_source_inventory_path"))
    write_csv(gaps, output_path(config, "true_vector_source_gap_register_path"))
    for category, review in review_by_category.items():
        output_key = CATEGORY_CONFIG[category]["output_key"]
        if output_key:
            write_csv(review, output_path(config, output_key))
    status = "B87_TRUE_VECTOR_SOURCE_REVIEW_PASS" if not gaps.empty else "B87_TRUE_VECTOR_SOURCE_REVIEW_EMPTY"
    status_map = dict(zip(gaps["source_category"], gaps["source_status"]))
    return SourceAvailabilityResult(
        status=status,
        reviewed_sources=len(inventory),
        connected_shade_status=str(status_map.get("connected_shade_corridor", "NOT_AVAILABLE_REQUIRES_MANUAL_DATA")),
        pedestrian_network_status=str(status_map.get("pedestrian_network", "NOT_AVAILABLE_REQUIRES_MANUAL_DATA")),
        overhead_status=str(status_map.get("overhead_geometry", "NOT_AVAILABLE_REQUIRES_MANUAL_DATA")),
        building_status=str(status_map.get("building_canyon", "NOT_AVAILABLE_REQUIRES_MANUAL_DATA")),
        tree_building_status=str(status_map.get("tree_building_interaction", "NOT_AVAILABLE_REQUIRES_MANUAL_DATA")),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Review compact/vector source availability for B8.7/B8.6g3. "
            "No raster files, QGIS, SOLWEIG, AOI/B9, WBGT, hazard/risk, "
            "manifest, or execution outputs are read or created."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
