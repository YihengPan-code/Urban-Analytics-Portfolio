"""Review B8.6g3 true-vector source validity by feature family.

Inputs:
    b86g3_source_inventory.csv plus B8.7 and B8.6g source-review/gap inputs.
Outputs:
    b86g3_true_vector_source_readiness.csv, seven per-category source-review
    CSVs, and b86g3_source_gap_register.csv.
Saved metrics:
    Source status, support level, validity verdict, blocker type, source
    confidence, and recommended next action for connected shade corridor,
    pedestrian network, covered walkway, building/canyon geometry,
    tree/building interaction, overhead geometry, and water/park/road edge
    context. This script creates no raster, QGIS/SOLWEIG, N300 manifest,
    AOI-wide prediction, B9, WBGT, hazard/risk, or System A/B output.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86g3_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, load_config, output_path, read_csv, write_csv


@dataclass(frozen=True)
class VectorReviewResult:
    """B8.6g3 vector source review result."""

    status: str
    connected_shade_corridor_verdict: str
    pedestrian_network_verdict: str
    building_canyon_verdict: str
    aoi_b9_blocking_gaps: int


CATEGORIES = {
    "connected_shade_corridor": {
        "feature_family": "connected shade corridor / shade continuity",
        "output_key": "connected_shade_corridor_review_path",
    },
    "pedestrian_network": {
        "feature_family": "pedestrian network / footpath",
        "output_key": "pedestrian_network_review_path",
    },
    "covered_walkway": {
        "feature_family": "covered walkway / sheltered path",
        "output_key": "covered_walkway_review_path",
    },
    "building_canyon": {
        "feature_family": "building footprint / building height / canyon geometry",
        "output_key": "building_canyon_review_path",
    },
    "tree_building_interaction": {
        "feature_family": "tree canopy and building interaction",
        "output_key": "tree_building_interaction_review_path",
    },
    "overhead_geometry": {
        "feature_family": "overhead geometry polygons / structures",
        "output_key": "overhead_geometry_review_path",
    },
    "water_park_road_edge": {
        "feature_family": "water / park / road / hardscape edge context",
        "output_key": "water_park_edge_review_path",
    },
}


def text(row: pd.Series) -> str:
    """Return lower-case searchable source metadata."""
    return " ".join(
        str(row.get(column, ""))
        for column in ["path", "extension", "geometry_type", "useful_columns"]
    ).lower()


def has_geometry(row: pd.Series) -> bool:
    """Return true for vector-like source geometry."""
    return str(row.get("extension", "")).lower() in {".geojson", ".gpkg", ".shp"} or bool(str(row.get("geometry_type", "")).strip())


def has_any(row: pd.Series, terms: list[str]) -> bool:
    """Return true when any term appears in metadata."""
    value = text(row)
    return any(term in value for term in terms)


def row_matches_category(row: pd.Series, category: str) -> bool:
    """Return true when an inventory row is relevant for a review category."""
    value = text(row)
    if category == "connected_shade_corridor":
        return any(term in value for term in ["shade_corridor", "connected_shade", "continuity", "covered_walkway", "footway", "walkway", "pedestrian"])
    if category == "pedestrian_network":
        return any(term in value for term in ["footway", "footpath", "walkway", "pedestrian", "sidewalk", "covered_walkway", "highway"])
    if category == "covered_walkway":
        return any(term in value for term in ["covered_walkway", "covered", "shelter", "sheltered", "pedestrian_bridge"])
    if category == "building_canyon":
        return any(term in value for term in ["hdb3d", "ura_building", "building", "manual_height", "height_m", "canyon", "orientation"])
    if category == "tree_building_interaction":
        return any(term in value for term in ["tree", "canopy", "gvi", "ndvi", "building"])
    if category == "overhead_geometry":
        return any(term in value for term in ["overhead", "viaduct", "elevated", "covered_walkway", "pedestrian_bridge"])
    if category == "water_park_road_edge":
        return any(term in value for term in ["water", "river", "park", "road", "hardscape", "impervious", "edge"])
    return False


def is_true_building_source(row: pd.Series) -> bool:
    """Return true for building footprint/height sources, excluding water-tag noise."""
    value = text(row)
    if not has_geometry(row):
        return False
    if "osm_water_toa_payoh" in value:
        return False
    return any(term in value for term in ["hdb3d_buildings", "ura_buildings", "manual_missing_buildings", "manual_split_buildings", "height_m", "manual_height_m"])


def is_covered_walkway_source(row: pd.Series) -> bool:
    """Return true for covered/sheltered walkway or pedestrian bridge geometry."""
    value = text(row)
    return has_geometry(row) and any(term in value for term in ["covered_walkway", "overhead_structures", "pedestrian_bridge", "covered|"])


def is_footpath_network_source(row: pd.Series) -> bool:
    """Return true for actual pedestrian path or footway network geometry."""
    value = text(row)
    return has_geometry(row) and any(term in value for term in ["footway", "footpath", "sidewalk", "pedestrian_path"])


def support_decision(row: pd.Series, category: str) -> tuple[str, str, str, str]:
    """Return support level, can-support flag, validity verdict, and caveat."""
    if str(row.get("safety_status", "")) != "SAFE_TO_INSPECT":
        return ("NOT_AVAILABLE_GUARDRAIL_SKIPPED", "no", "NOT_VALID_FOR_TRUE_VECTOR_CLOSURE", "source was not inspected by guardrail")
    if category == "connected_shade_corridor":
        if "connectivity" in text(row) and has_geometry(row):
            return (
                "PARTIAL_CONNECTIVITY_GEOMETRY_REQUIRES_QA",
                "no",
                "NOT_CLOSED_NEEDS_EXPLICIT_CONNECTIVITY_TABLE",
                "geometry hint exists, but no reviewed pedestrian shade-network topology is available",
            )
        if is_covered_walkway_source(row) or is_footpath_network_source(row):
            return (
                "PARTIAL_GEOMETRY_NO_CONNECTIVITY",
                "no",
                "NOT_CLOSED_NEEDS_EXPLICIT_CONNECTIVITY_TABLE",
                "covered/pedestrian geometry can inform future acquisition but is not a connected corridor metric",
            )
        return (
            "NOT_AVAILABLE",
            "no",
            "NOT_VALID_FOR_TRUE_VECTOR_CLOSURE",
            "connected corridor cannot be inferred from centroid distance, generic shade fraction, or compact cell fractions",
        )
    if category == "pedestrian_network":
        if is_footpath_network_source(row):
            return ("PARTIAL_TRUE_FOOTPATH_NETWORK_FOUND", "yes", "PARTIAL_REQUIRES_COVERAGE_QA", "footpath/walkway geometry requires AOI completeness QA")
        if is_covered_walkway_source(row):
            return ("PARTIAL_COVERED_WALKWAY_ONLY", "yes", "PARTIAL_NOT_FULL_PEDESTRIAN_NETWORK", "covered walkway/pedestrian bridge source is useful but not a full pedestrian footpath network")
        return ("NOT_AVAILABLE", "no", "NOT_VALID_FOR_TRUE_VECTOR_CLOSURE", "requires footway/path/walkway or equivalent pedestrian network source")
    if category == "covered_walkway":
        if is_covered_walkway_source(row):
            return ("AVAILABLE_TRUE_VECTOR_PARTIAL", "yes", "VALID_FOR_COVERED_WALKWAY_REVIEW", "covered/sheltered overhead geometry exists; coverage and topology still need QA")
        return ("NOT_AVAILABLE", "no", "NOT_VALID_FOR_TRUE_VECTOR_CLOSURE", "requires covered/sheltered tags or equivalent geometry")
    if category == "building_canyon":
        if is_true_building_source(row):
            return ("AVAILABLE_TRUE_VECTOR", "yes", "VALID_FOR_BUILDING_CANYON_REVIEW", "building footprint/height source exists; canyon axis/orientation is a future derivation")
        return ("NOT_AVAILABLE", "no", "NOT_VALID_FOR_TRUE_VECTOR_CLOSURE", "requires building footprint and/or height/orientation source")
    if category == "tree_building_interaction":
        if "tree_building_interaction" in text(row):
            return ("PARTIAL_COMPACT_OR_PROXY_INTERACTION_TABLE", "no", "NOT_CLOSED_NEEDS_TREE_CANOPY_VECTOR", "existing interaction table is proxy/compact and does not close the true-vector source requirement")
        if has_any(row, ["tree", "canopy", "gvi", "ndvi"]):
            return ("PARTIAL_COMPACT_TREE_PROXY_ONLY", "no", "NOT_CLOSED_NEEDS_TREE_CANOPY_VECTOR", "compact/proxy tree evidence cannot close true-vector tree/building interaction")
        if is_true_building_source(row):
            return ("PARTIAL_BUILDING_ONLY", "no", "NOT_CLOSED_NEEDS_TREE_CANOPY_VECTOR", "building geometry exists but tree canopy vector is missing")
        return ("NOT_AVAILABLE", "no", "NOT_VALID_FOR_TRUE_VECTOR_CLOSURE", "requires tree canopy plus building geometry or a trusted vector-derived interaction table")
    if category == "overhead_geometry":
        if has_geometry(row) and has_any(row, ["overhead", "viaduct", "elevated", "covered_walkway", "pedestrian_bridge"]):
            return ("AVAILABLE_TRUE_VECTOR", "yes", "VALID_FOR_OVERHEAD_GEOMETRY_REVIEW", "overhead polygons/lines are available for source-backed review")
        return ("NOT_AVAILABLE", "no", "NOT_VALID_FOR_TRUE_VECTOR_CLOSURE", "requires overhead geometry polygons/structures")
    if category == "water_park_road_edge":
        if has_geometry(row) and has_any(row, ["osm_roads", "osm_water", "water", "road"]):
            return ("AVAILABLE_TRUE_VECTOR_PARTIAL", "yes", "VALID_FOR_EDGE_CONTEXT_REVIEW", "water/road geometry exists; park/hardscape completeness may remain partial")
        if has_any(row, ["park", "water", "road", "hardscape", "impervious", "edge"]):
            return ("PARTIAL_COMPACT_CONTEXT", "yes", "PARTIAL_COMPACT_CONTEXT_ONLY", "compact edge context can guide caveats but is not a full vector edge network")
        return ("NOT_AVAILABLE", "no", "NOT_VALID_FOR_TRUE_VECTOR_CLOSURE", "requires water/park/road/hardscape edge vectors or compact adjacency tables")
    return ("NOT_AVAILABLE", "no", "NOT_VALID_FOR_TRUE_VECTOR_CLOSURE", "unrecognized category")


def review_category(inventory: pd.DataFrame, category: str) -> pd.DataFrame:
    """Build per-source review rows for one true-vector category."""
    matched = inventory.loc[inventory.apply(lambda row: row_matches_category(row, category), axis=1)].copy()
    rows: list[dict[str, Any]] = []
    for _, row in matched.iterrows():
        support, can_support, verdict, caveat = support_decision(row, category)
        rows.append(
            {
                "source_category": category,
                "feature_family": CATEGORIES[category]["feature_family"],
                "path": row.get("path", ""),
                "extension": row.get("extension", ""),
                "row_count": row.get("row_count", ""),
                "column_count": row.get("column_count", ""),
                "geometry_type": row.get("geometry_type", ""),
                "CRS": row.get("CRS", ""),
                "useful_columns": row.get("useful_columns", ""),
                "read_status": row.get("read_status", ""),
                "safety_status": row.get("safety_status", ""),
                "source_confidence": row.get("source_confidence", ""),
                "support_level": support,
                "can_support_true_vector_feature": can_support,
                "validity_verdict": verdict,
                "caveat": caveat,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    if not rows:
        rows.append(
            {
                "source_category": category,
                "feature_family": CATEGORIES[category]["feature_family"],
                "path": "",
                "extension": "",
                "row_count": "",
                "column_count": "",
                "geometry_type": "",
                "CRS": "",
                "useful_columns": "",
                "read_status": "NOT_AVAILABLE",
                "safety_status": "SAFE_NO_SOURCE_FOUND",
                "source_confidence": "not_available",
                "support_level": "NOT_AVAILABLE",
                "can_support_true_vector_feature": "no",
                "validity_verdict": "NOT_VALID_FOR_TRUE_VECTOR_CLOSURE",
                "caveat": "no compact/vector source discovered under safe roots",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows)


def category_status(category: str, review: pd.DataFrame) -> tuple[str, str, str, str, str]:
    """Return status, verdict, blocker type, next action, and evidence."""
    valid = review["validity_verdict"].astype(str)
    yes_count = int(review["can_support_true_vector_feature"].astype(str).eq("yes").sum())
    source_count = int(review["path"].astype(str).str.len().gt(0).sum())
    if category == "connected_shade_corridor":
        return (
            "NOT_AVAILABLE",
            "MISSING_EXPLICIT_SHADE_CONNECTIVITY_SOURCE",
            "surrogate_aoi_b9_blocker",
            "B8.6g4 should acquire a pedestrian shade-network or vector-derived connectivity table; do not infer continuity from centroid or shade fractions",
            f"candidate_sources={source_count}; true_connectivity_sources=0",
        )
    if category == "pedestrian_network":
        if valid.str.contains("PARTIAL_TRUE_FOOTPATH_NETWORK_FOUND").any():
            status = "PARTIAL_REQUIRES_QA"
            verdict = "PARTIAL_PEDESTRIAN_NETWORK_SOURCE"
        elif valid.str.contains("PARTIAL_NOT_FULL_PEDESTRIAN_NETWORK").any():
            status = "PARTIAL_COVERED_WALKWAY_ONLY"
            verdict = "NO_FULL_FOOTPATH_NETWORK_SOURCE"
        else:
            status = "NOT_AVAILABLE"
            verdict = "MISSING_FOOTPATH_NETWORK_SOURCE"
        return (status, verdict, "future_feature_gap", "B8.6g4 should acquire/QA OSM or official pedestrian footpath geometry", f"candidate_sources={source_count}; support_rows={yes_count}")
    if category == "covered_walkway":
        status = "AVAILABLE_FOR_REVIEW" if yes_count > 0 else "NOT_AVAILABLE"
        verdict = "COVERED_WALKWAY_GEOMETRY_AVAILABLE" if yes_count > 0 else "MISSING_COVERED_WALKWAY_SOURCE"
        return (status, verdict, "documentation_caveat" if yes_count > 0 else "future_feature_gap", "Use only as source-backed covered-walkway review; topology remains future work", f"support_rows={yes_count}")
    if category == "building_canyon":
        status = "AVAILABLE_FOR_REVIEW" if yes_count > 0 else "NOT_AVAILABLE"
        verdict = "BUILDING_FOOTPRINT_HEIGHT_SOURCE_AVAILABLE" if yes_count > 0 else "MISSING_BUILDING_CANYON_SOURCE"
        return (status, verdict, "documentation_caveat" if yes_count > 0 else "future_feature_gap", "Use building geometry for future canyon derivation; do not claim observed local WBGT", f"support_rows={yes_count}")
    if category == "tree_building_interaction":
        if valid.str.contains("VALID_FOR_TREE_BUILDING_INTERACTION").any():
            return ("AVAILABLE_FOR_REVIEW", "TREE_AND_BUILDING_VECTOR_SOURCE_AVAILABLE", "documentation_caveat", "QA tree/building interaction derivation before AOI/B9", f"support_rows={yes_count}")
        return ("PARTIAL_NEEDS_TREE_CANOPY_VECTOR", "BUILDING_GEOMETRY_PRESENT_TREE_CANOPY_VECTOR_MISSING", "surrogate_aoi_b9_blocker", "B8.6g4 should acquire tree-canopy polygon/source or a trusted vector-derived interaction table", f"candidate_sources={source_count}; valid_interaction_sources=0")
    if category == "overhead_geometry":
        status = "AVAILABLE_FOR_REVIEW" if yes_count > 0 else "NOT_AVAILABLE"
        verdict = "OVERHEAD_GEOMETRY_SOURCE_AVAILABLE" if yes_count > 0 else "MISSING_OVERHEAD_GEOMETRY_SOURCE"
        return (status, verdict, "documentation_caveat" if yes_count > 0 else "future_feature_gap", "Use source-backed overhead geometry review; do not treat as observed cooling truth", f"support_rows={yes_count}")
    if category == "water_park_road_edge":
        status = "PARTIAL_AVAILABLE_FOR_REVIEW" if yes_count > 0 else "NOT_AVAILABLE"
        verdict = "WATER_ROAD_EDGE_CONTEXT_AVAILABLE_PARK_PARTIAL" if yes_count > 0 else "MISSING_EDGE_CONTEXT_SOURCE"
        return (status, verdict, "documentation_caveat" if yes_count > 0 else "future_feature_gap", "Use for caveats and edge context only; no risk/hazard score", f"support_rows={yes_count}")
    return ("NOT_AVAILABLE", "NOT_REVIEWED", "future_feature_gap", "review category mapping", "no evidence")


def readiness_and_gaps(review_by_category: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build readiness and source-gap summary matrices."""
    rows: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    for category, review in review_by_category.items():
        status, verdict, blocker_type, action, evidence = category_status(category, review)
        rows.append(
            {
                "source_category": category,
                "feature_family": CATEGORIES[category]["feature_family"],
                "status": status,
                "validity_verdict": verdict,
                "evidence": evidence,
                "blocker_type": blocker_type,
                "recommended_next_action": action,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
        gap_status = "OPEN" if blocker_type in {"surrogate_aoi_b9_blocker", "future_feature_gap"} and status not in {"AVAILABLE_FOR_REVIEW", "PARTIAL_AVAILABLE_FOR_REVIEW"} else "CLOSED_OR_DOCUMENTED"
        if category in {"connected_shade_corridor", "tree_building_interaction", "pedestrian_network"}:
            gap_status = "OPEN"
        gaps.append(
            {
                "source_category": category,
                "feature_family": CATEGORIES[category]["feature_family"],
                "gap_status": gap_status,
                "source_status": status,
                "blocker_type": blocker_type,
                "blocking_for_execution_precheck": "no",
                "blocking_for_aoi_b9": "yes" if category in {"connected_shade_corridor", "tree_building_interaction"} else ("partial" if category == "pedestrian_network" else "no"),
                "evidence": evidence,
                "recommended_next_action": action,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(gaps)


def run(config_path: Path = DEFAULT_CONFIG) -> VectorReviewResult:
    """Run B8.6g3 true-vector source review."""
    config = load_config(config_path)
    inventory = read_csv(output_path(config, "source_inventory_path"))
    review_by_category = {category: review_category(inventory, category) for category in CATEGORIES}
    readiness, gaps = readiness_and_gaps(review_by_category)
    write_csv(readiness, output_path(config, "true_vector_source_readiness_path"))
    write_csv(gaps, output_path(config, "source_gap_register_path"))
    for category, review in review_by_category.items():
        write_csv(review, output_path(config, CATEGORIES[category]["output_key"]))
    status_map = dict(zip(readiness["source_category"], readiness["validity_verdict"]))
    aoi_b9_blocking = int(gaps["blocking_for_aoi_b9"].astype(str).isin(["yes", "partial"]).sum())
    return VectorReviewResult(
        status="B86G3_VECTOR_SOURCE_REVIEW_PASS",
        connected_shade_corridor_verdict=str(status_map.get("connected_shade_corridor", "MISSING_EXPLICIT_SHADE_CONNECTIVITY_SOURCE")),
        pedestrian_network_verdict=str(status_map.get("pedestrian_network", "MISSING_FOOTPATH_NETWORK_SOURCE")),
        building_canyon_verdict=str(status_map.get("building_canyon", "MISSING_BUILDING_CANYON_SOURCE")),
        aoi_b9_blocking_gaps=aoi_b9_blocking,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Review B8.6g3 true-vector source validity by feature family. "
            "Creates compact CSV review outputs only; no raster/QGIS/SOLWEIG/"
            "manifest/AOI/B9/WBGT/hazard/risk output."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
