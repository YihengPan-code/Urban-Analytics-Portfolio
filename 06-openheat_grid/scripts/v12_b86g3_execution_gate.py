"""Write B8.6g3 execution-precheck and AOI/B9 gate matrices.

Inputs:
    B8.6g3 N300 v4 source-reviewed design, manual closeout, and true-vector
    readiness/gap register.
Outputs:
    b86g3_execution_precheck_readiness_matrix.csv and
    b86g3_aoi_b9_blocker_matrix.csv.
Saved metrics:
    Candidate count, N150 overlap, duplicate count, manual water exclusions,
    source-review cell closeout, true-vector feature gaps, SOLWEIG asset
    readiness caveat, execution-manifest status, and AOI/B9 blocker headline.
    This script creates no raster, QGIS/SOLWEIG, N300 execution manifest,
    AOI-wide prediction, B9, WBGT, hazard/risk, or System A/B output.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86g3_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    config_list,
    current_n150_cells,
    load_config,
    output_path,
    read_csv,
    write_csv,
)


@dataclass(frozen=True)
class ExecutionGateResult:
    """B8.6g3 execution and AOI/B9 gate result."""

    status: str
    execution_precheck_headline: str
    aoi_b9_headline: str


def readiness_lookup(readiness: pd.DataFrame, category: str, column: str) -> str:
    """Read one source-readiness field by source category."""
    row = readiness.loc[readiness["source_category"].astype(str).eq(category)]
    return str(row[column].iloc[0]) if not row.empty and column in row.columns else "not_reviewed"


def source_review_closed(closeout: pd.DataFrame, cell_id: str) -> bool:
    """Return whether a source-review cell is closed as keep-with-caveat."""
    row = closeout.loc[closeout["source_review_cell"].astype(str).eq(cell_id)]
    return not row.empty and str(row["recommended_closeout"].iloc[0]) == "KEEP_WITH_CAVEAT"


def matrix_row(item: str, status: str, evidence: str, blocker_type: str, next_action: str) -> dict[str, Any]:
    """Return one readiness matrix row with claim boundary."""
    return {
        "readiness_item": item,
        "status": status,
        "evidence": evidence,
        "blocker_type": blocker_type,
        "next_action": next_action,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def execution_matrix(config: dict[str, Any]) -> pd.DataFrame:
    """Build execution-precheck readiness matrix."""
    v4 = read_csv(output_path(config, "n300_design_v4_source_reviewed_path"))
    closeout = read_csv(output_path(config, "manual_source_review_closeout_path"))
    readiness = read_csv(output_path(config, "true_vector_source_readiness_path"))
    n150_overlap = len(set(v4["cell_id"].astype(str)).intersection(current_n150_cells(config)))
    duplicate_count = int(v4["cell_id"].astype(str).duplicated().sum())
    expected = int(config.get("expected_n300_count", 150))
    source_cells = config_list(config, "source_review_cells")
    replaced_cells = config_list(config, "replaced_water_cells")
    closed_count = sum(1 for cell_id in source_cells if source_review_closed(closeout, cell_id))
    replaced_status = closeout.loc[closeout["source_review_cell"].astype(str).isin(replaced_cells), "source_closeout_status"].astype(str).tolist()
    rows = [
        matrix_row(
            "candidate_count",
            "PASS" if len(v4) == expected else "FAIL",
            f"v4_rows={len(v4)} expected={expected}",
            "execution_precheck_blocker" if len(v4) != expected else "documentation_caveat",
            "repair candidate design count before B8.7b" if len(v4) != expected else "none",
        ),
        matrix_row(
            "N150_overlap",
            "PASS" if n150_overlap == 0 else "FAIL",
            f"overlap_count={n150_overlap}",
            "execution_precheck_blocker" if n150_overlap else "documentation_caveat",
            "replace overlapping candidates" if n150_overlap else "none",
        ),
        matrix_row(
            "duplicate_cell_id",
            "PASS" if duplicate_count == 0 else "FAIL",
            f"duplicate_count={duplicate_count}",
            "execution_precheck_blocker" if duplicate_count else "documentation_caveat",
            "deduplicate v4 design" if duplicate_count else "none",
        ),
        matrix_row(
            "manual_water_exclusions",
            "PASS" if all(status == "MANUAL_EXCLUDED_REPLACED_WATER_SURFACE" for status in replaced_status) else "WARN",
            "replaced_water_cells=" + "|".join(replaced_cells),
            "documentation_caveat",
            "no action; B8.7a replacements remain outside v4 candidate rows",
        ),
        matrix_row(
            "source_review_cells",
            "PASS" if closed_count == len(source_cells) else "FAIL",
            f"closed={closed_count}/{len(source_cells)}",
            "execution_precheck_blocker" if closed_count != len(source_cells) else "documentation_caveat",
            "close source-review cells before B8.7b" if closed_count != len(source_cells) else "carry caveats into B8.7b",
        ),
    ]
    for cell_id in source_cells:
        row = closeout.loc[closeout["source_review_cell"].astype(str).eq(cell_id)].iloc[0]
        rows.append(
            matrix_row(
                cell_id,
                "PASS" if str(row["recommended_closeout"]) == "KEEP_WITH_CAVEAT" else "FAIL",
                str(row["caveat_text"]),
                "documentation_caveat" if str(row["execution_precheck_blocker"]) == "no" else "execution_precheck_blocker",
                str(row["recommended_next_action"]),
            )
        )
    rows.extend(
        [
            matrix_row(
                "connected_shade_corridor",
                readiness_lookup(readiness, "connected_shade_corridor", "status"),
                readiness_lookup(readiness, "connected_shade_corridor", "validity_verdict"),
                "surrogate_aoi_b9_blocker",
                "Not an N300 execution-precheck blocker; required before AOI/B9 surrogate promotion.",
            ),
            matrix_row(
                "pedestrian_network",
                readiness_lookup(readiness, "pedestrian_network", "status"),
                readiness_lookup(readiness, "pedestrian_network", "validity_verdict"),
                "future_feature_gap",
                "Can proceed to B8.7b precheck, but B8.6g4 should acquire/QA true pedestrian paths.",
            ),
            matrix_row(
                "covered_walkway",
                readiness_lookup(readiness, "covered_walkway", "status"),
                readiness_lookup(readiness, "covered_walkway", "validity_verdict"),
                "documentation_caveat",
                "Use as source-backed covered-walkway evidence; not a connected-corridor metric.",
            ),
            matrix_row(
                "building_canyon",
                readiness_lookup(readiness, "building_canyon", "status"),
                readiness_lookup(readiness, "building_canyon", "validity_verdict"),
                "documentation_caveat",
                "Available for future feature derivation; no observed-truth claim.",
            ),
            matrix_row(
                "tree_building_interaction",
                readiness_lookup(readiness, "tree_building_interaction", "status"),
                readiness_lookup(readiness, "tree_building_interaction", "validity_verdict"),
                "surrogate_aoi_b9_blocker",
                "Needs tree-canopy vector or trusted vector-derived interaction before AOI/B9.",
            ),
            matrix_row(
                "feature_proxy_gap",
                "OPEN",
                "B8.6g proxy features remain useful diagnostically but do not count as true-vector closure.",
                "surrogate_aoi_b9_blocker",
                "B8.6g4 external/vector acquisition remains required before AOI/B9.",
            ),
            matrix_row(
                "SOLWEIG asset readiness unknown",
                "UNKNOWN_NOT_EVALUATED_IN_B86G3",
                "B8.6g3 is a source-review lane and does not inspect or create SOLWEIG assets/manifests.",
                "future_feature_gap",
                "B8.7b may inspect execution-precheck requirements without running SOLWEIG/QGIS.",
            ),
            matrix_row(
                "execution_manifest",
                "NOT_CREATED",
                "No N300 execution manifest, QGIS runner, or local runner was created.",
                "documentation_caveat",
                "Future B8.7b may review manifest requirements only; no actual execution.",
            ),
        ]
    )
    return pd.DataFrame(rows)


def aoi_b9_matrix(config: dict[str, Any]) -> pd.DataFrame:
    """Build AOI/B9 blocker matrix."""
    readiness = read_csv(output_path(config, "true_vector_source_readiness_path"))
    gaps = read_csv(output_path(config, "source_gap_register_path"))
    connected = readiness_lookup(readiness, "connected_shade_corridor", "validity_verdict")
    pedestrian = readiness_lookup(readiness, "pedestrian_network", "validity_verdict")
    building = readiness_lookup(readiness, "building_canyon", "validity_verdict")
    tree = readiness_lookup(readiness, "tree_building_interaction", "validity_verdict")
    open_gaps = int(gaps["gap_status"].astype(str).eq("OPEN").sum()) if "gap_status" in gaps.columns else 0
    rows = [
        {
            "blocker_item": "AOI_PREFLIGHT",
            "status": "AOI_PREFLIGHT_BLOCKED",
            "evidence": "B8.6g3 creates source review only and leaves true-vector feature gaps explicit.",
            "blocker_type": "surrogate_aoi_b9_blocker",
            "next_action": "B8.6g4 external/vector acquisition before any AOI preflight recommendation.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "blocker_item": "B9",
            "status": "B9_BLOCKED",
            "evidence": "No AOI-wide prediction, no production surrogate promotion, no WBGT/hazard/risk output.",
            "blocker_type": "surrogate_aoi_b9_blocker",
            "next_action": "Keep B9 blocked.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "blocker_item": "connected_shade_corridor",
            "status": "BLOCKING_AOI_B9",
            "evidence": connected,
            "blocker_type": "surrogate_aoi_b9_blocker",
            "next_action": "Acquire explicit pedestrian shade-network/connectivity source; do not infer from compact fractions.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "blocker_item": "pedestrian_network",
            "status": "PARTIAL_GAP_FOR_AOI_B9",
            "evidence": pedestrian,
            "blocker_type": "future_feature_gap",
            "next_action": "Acquire/QA footway/path/walkway geometry if used for AOI features.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "blocker_item": "tree_building_interaction",
            "status": "BLOCKING_AOI_B9",
            "evidence": tree,
            "blocker_type": "surrogate_aoi_b9_blocker",
            "next_action": "Acquire tree canopy vector or trusted vector-derived interaction table.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "blocker_item": "building_canyon",
            "status": "NOT_BLOCKING_SOURCE_REVIEW",
            "evidence": building,
            "blocker_type": "documentation_caveat",
            "next_action": "Can be used for future derivation after QA; does not unblock AOI/B9 by itself.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "blocker_item": "open_true_vector_gap_count",
            "status": "OPEN",
            "evidence": f"open_or_partial_source_gaps={open_gaps}",
            "blocker_type": "surrogate_aoi_b9_blocker",
            "next_action": "Resolve source gaps before AOI/B9.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    return pd.DataFrame(rows)


def execution_headline(matrix: pd.DataFrame) -> str:
    """Return B8.7b precheck readiness headline."""
    execution_blockers = matrix.loc[
        matrix["blocker_type"].astype(str).eq("execution_precheck_blocker")
        & matrix["status"].astype(str).isin(["FAIL", "BLOCKED"])
    ]
    return "B87B_EXECUTION_PRECHECK_MAY_PROCEED_DESIGN_READY_NO_EXECUTION" if execution_blockers.empty else "B87B_EXECUTION_PRECHECK_BLOCKED_BY_DESIGN"


def aoi_headline(matrix: pd.DataFrame) -> str:
    """Return AOI/B9 blocker headline."""
    if matrix["status"].astype(str).str.contains("B9_BLOCKED|AOI_PREFLIGHT_BLOCKED|BLOCKING_AOI_B9", regex=True).any():
        return "AOI_PREFLIGHT_BLOCKED / B9_BLOCKED_PENDING_TRUE_VECTOR_SOURCE_GAPS"
    return "AOI_B9_NOT_REVIEWED"


def run(config_path: Path = DEFAULT_CONFIG) -> ExecutionGateResult:
    """Run B8.6g3 execution-precheck and AOI/B9 gate matrices."""
    config = load_config(config_path)
    exec_matrix = execution_matrix(config)
    aoi_matrix = aoi_b9_matrix(config)
    write_csv(exec_matrix, output_path(config, "execution_precheck_readiness_matrix_path"))
    write_csv(aoi_matrix, output_path(config, "aoi_b9_blocker_matrix_path"))
    return ExecutionGateResult(
        status="B86G3_EXECUTION_GATE_PASS",
        execution_precheck_headline=execution_headline(exec_matrix),
        aoi_b9_headline=aoi_headline(aoi_matrix),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Write B8.6g3 execution-precheck and AOI/B9 gate matrices. "
            "No raster/QGIS/SOLWEIG/manifest/AOI/B9/WBGT/hazard/risk output."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
