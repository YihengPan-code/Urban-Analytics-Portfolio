"""Close out B8.7a manual source-review cells and write N300 v4 design.

Inputs:
    B8.7a v3 patched N300 design, B8.7a patch log, B8.7a manual input,
    B8.6g/B8.7 source evidence, current N150 compact cell source, and
    candidate universe declared in the B8.6g3 config.
Outputs:
    b86g3_manual_source_review_closeout.csv,
    b86g3_n300_design_v4_source_reviewed.csv, and
    b86g3_n300_v4_diff_vs_b87a.csv.
Saved metrics:
    TP_0103/TP_0104/TP_0464 source-review closeout, kept/replaced manual facts,
    execution-precheck blocker flags, surrogate/AOI/B9 blocker flags, v4 row
    count, N150 overlap count, duplicate cell count, and metadata-only diff
    status. This script creates no raster, QGIS/SOLWEIG, N300 manifest,
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
class CellCloseoutResult:
    """B8.6g3 cell closeout result."""

    status: str
    source_review_cells_closed: int
    v4_rows: int
    n150_overlap_count: int
    duplicate_count: int


MANUAL_FACTS = {
    "TP_0103": {
        "status": "KEEP_WITH_RIVER_EDGE_CAVEAT",
        "fact": "Mixed river channel with both banks; river surface approximately one quarter; not pure water.",
        "caveat": "Keep as river-edge mixed-bank candidate; compact water proxy may overstate water surface and should not be treated as pure-water truth.",
        "next": "Carry caveat into B8.7b precheck; no replacement required.",
    },
    "TP_0104": {
        "status": "KEEP_WITH_RIVER_EDGE_CAVEAT",
        "fact": "Mixed river channel with both banks; river surface approximately one quarter; not pure water.",
        "caveat": "Keep as river-edge mixed-bank candidate; compact water proxy may overstate water surface and should not be treated as pure-water truth.",
        "next": "Carry caveat into B8.7b precheck; no replacement required.",
    },
    "TP_0464": {
        "status": "KEEP_WITH_UTILITY_WOODLAND_CAVEAT",
        "fact": "Approximately 37 percent waterworks and 63 percent woodland; not pure water.",
        "caveat": "Keep with utility-site and pedestrian-relevance caveat; useful as woodland/utility edge context, not as a pure pedestrian exposure cell.",
        "next": "Carry utility/woodland caveat into B8.7b precheck; no replacement required.",
    },
    "TP_0159": {
        "status": "KEEP_CURRENT_SPORT_HALL_TEMPORAL_UPDATE",
        "fact": "Construction site in 2022 but Toa Payoh Sport Hall in 2026; keep as current public/sports facility.",
        "caveat": "Record temporal land-use mismatch between older compact water proxy/source layers and current public sports-facility use.",
        "next": "Keep in v4 metadata; no replacement required.",
    },
    "TP_0519": {
        "status": "KEEP_WOODLAND_GREEN_CONTROL",
        "fact": "Woodland; keep as vegetation/canopy/green-control candidate.",
        "caveat": "Keep as green-control/woodland candidate; not a water-surface exclusion.",
        "next": "Keep in v4 metadata; no replacement required.",
    },
    "TP_0830": {
        "status": "MANUAL_EXCLUDED_REPLACED_WATER_SURFACE",
        "fact": "Basically river/water surface and excluded/replaced in B8.7a.",
        "caveat": "Already removed from v3/v4 candidate design.",
        "next": "No action; confirm replacement remains non-overlap and non-duplicate.",
    },
    "TP_0858": {
        "status": "MANUAL_EXCLUDED_REPLACED_WATER_SURFACE",
        "fact": "Basically river/water surface and excluded/replaced in B8.7a.",
        "caveat": "Already removed from v3/v4 candidate design.",
        "next": "No action; confirm replacement remains non-overlap and non-duplicate.",
    },
    "TP_0943": {
        "status": "MANUAL_EXCLUDED_REPLACED_WATER_SURFACE",
        "fact": "Basically river/water surface and excluded/replaced in B8.7a.",
        "caveat": "Already removed from v3/v4 candidate design.",
        "next": "No action; confirm replacement remains non-overlap and non-duplicate.",
    },
}


def one_row(frame: pd.DataFrame, cell_id: str) -> pd.Series | None:
    """Return the first row for a cell ID if available."""
    if frame.empty or "cell_id" not in frame.columns:
        return None
    match = frame.loc[frame["cell_id"].astype(str).eq(cell_id)]
    return None if match.empty else match.iloc[0]


def source_evidence(cell_id: str, design: pd.DataFrame, manual: pd.DataFrame, patch_log: pd.DataFrame, universe: pd.DataFrame) -> str:
    """Build compact source-evidence text for a manual closeout row."""
    parts: list[str] = []
    design_row = one_row(design, cell_id)
    manual_row = one_row(manual, cell_id)
    patch_row = one_row(patch_log, cell_id)
    universe_row = one_row(universe, cell_id)
    if design_row is not None:
        parts.append(
            "v3_design="
            + "|".join(
                [
                    f"status:{design_row.get('design_status', '')}",
                    f"role:{design_row.get('primary_role', '')}",
                    f"spatial:{design_row.get('spatial_bin', '')}",
                    f"typology:{design_row.get('typology', '')}",
                ]
            )
        )
    if manual_row is not None:
        parts.append(
            "manual_input="
            + "|".join(
                [
                    f"decision:{manual_row.get('manual_decision', '')}",
                    f"reason:{manual_row.get('manual_reason', '')}",
                    f"notes:{manual_row.get('manual_notes', '')}",
                ]
            )
        )
    if patch_row is not None:
        parts.append(
            "patch_log="
            + "|".join(
                [
                    f"action:{patch_row.get('patch_action', '')}",
                    f"replacement:{patch_row.get('replacement_cell_id', '')}",
                    f"decision:{patch_row.get('manual_decision', '')}",
                ]
            )
        )
    if universe_row is not None:
        fields = [
            "typology_label",
            "water_fraction",
            "dynamic_world_water_fraction",
            "tree_canopy_fraction",
            "road_fraction",
            "overhead_fraction_total",
            "pedestrian_shelter_fraction",
            "sport_facility_count",
            "land_use_raw",
            "water_distance_m",
            "park_distance_m",
        ]
        parts.append(
            "candidate_universe="
            + "|".join(f"{field}:{universe_row.get(field, '')}" for field in fields if field in universe_row.index)
        )
    return " ; ".join(parts) if parts else "no local compact source evidence found"


def closeout_row(cell_id: str, design: pd.DataFrame, manual: pd.DataFrame, patch_log: pd.DataFrame, universe: pd.DataFrame) -> dict[str, Any]:
    """Build one manual source-review closeout row."""
    fact = MANUAL_FACTS[cell_id]
    in_design = one_row(design, cell_id) is not None
    replaced = fact["status"] == "MANUAL_EXCLUDED_REPLACED_WATER_SURFACE"
    recommended = "KEEP_WITH_CAVEAT"
    if replaced:
        recommended = "REPLACE_REQUIRED"
    execution_blocker = "no"
    surrogate_blocker = "no"
    if cell_id in {"TP_0103", "TP_0104", "TP_0464"}:
        recommended = "KEEP_WITH_CAVEAT" if in_design else "STILL_BLOCKED_NEEDS_MANUAL_QA"
        execution_blocker = "no" if in_design else "yes"
        surrogate_blocker = "no" if in_design else "yes"
    return {
        "source_review_cell": cell_id,
        "manual_fact": fact["fact"],
        "source_evidence": source_evidence(cell_id, design, manual, patch_log, universe),
        "recommended_closeout": recommended,
        "source_closeout_status": fact["status"],
        "execution_precheck_blocker": execution_blocker,
        "surrogate_feature_blocker": surrogate_blocker,
        "caveat_text": fact["caveat"],
        "recommended_next_action": fact["next"],
        "claim_boundary": CLAIM_BOUNDARY,
    }


def build_closeout(config: dict[str, Any]) -> pd.DataFrame:
    """Build source-review closeout rows from manual facts and local evidence."""
    design = read_csv(config["b87a_v3_design_path"])
    manual = read_csv(config["b87a_manual_input_path"])
    patch_log = read_csv(config["b87a_patch_log_path"])
    universe = read_csv(config["candidate_universe_path"])
    cells = (
        config_list(config, "source_review_cells")
        + config_list(config, "kept_manual_cells")
        + config_list(config, "replaced_water_cells")
    )
    return pd.DataFrame([closeout_row(cell_id, design, manual, patch_log, universe) for cell_id in cells])


def v4_status_for_cell(cell_id: str, closeout: pd.DataFrame) -> tuple[str, str, str, str, str, str]:
    """Return v4 source-review metadata fields for one design cell."""
    row = closeout.loc[closeout["source_review_cell"].astype(str).eq(cell_id)]
    if row.empty:
        return ("NOT_REVIEW_REQUIRED", "", "no", "no", "no", "no")
    item = row.iloc[0]
    return (
        str(item["source_closeout_status"]),
        str(item["caveat_text"]),
        str(item["execution_precheck_blocker"]),
        str(item["surrogate_feature_blocker"]),
        "no",
        "no",
    )


def build_v4(config: dict[str, Any], closeout: pd.DataFrame) -> pd.DataFrame:
    """Create source-reviewed N300 v4 design without row replacement unless needed."""
    design = read_csv(config["b87a_v3_design_path"]).copy()
    statuses = [v4_status_for_cell(str(cell_id), closeout) for cell_id in design["cell_id"].astype(str)]
    design["source_closeout_status"] = [item[0] for item in statuses]
    design["source_closeout_caveat"] = [item[1] for item in statuses]
    design["execution_precheck_blocker"] = [item[2] for item in statuses]
    design["surrogate_feature_blocker"] = [item[3] for item in statuses]
    design["true_vector_required_before_execution"] = [item[4] for item in statuses]
    design["true_vector_required_before_aoi_b9"] = [item[5] for item in statuses]
    design["b86g3_design_status"] = design["source_closeout_status"].map(
        lambda value: "B86G3_SOURCE_REVIEWED_KEEP" if str(value) != "NOT_REVIEW_REQUIRED" else "B86G3_UNCHANGED_FROM_B87A"
    )
    return design


def diff_vs_b87a(config: dict[str, Any], v4: pd.DataFrame) -> pd.DataFrame:
    """Return compact v4-vs-B8.7a diff table."""
    old = read_csv(config["b87a_v3_design_path"])
    old_ids = set(old["cell_id"].astype(str))
    new_ids = set(v4["cell_id"].astype(str))
    rows: list[dict[str, Any]] = []
    for cell_id in sorted(old_ids - new_ids):
        rows.append({"cell_id": cell_id, "change_type": "removed_from_b87a", "paired_cell_id": "", "diff_note": "unexpected row removal", "claim_boundary": CLAIM_BOUNDARY})
    for cell_id in sorted(new_ids - old_ids):
        rows.append({"cell_id": cell_id, "change_type": "added_to_v4", "paired_cell_id": "", "diff_note": "unexpected row addition", "claim_boundary": CLAIM_BOUNDARY})
    metadata_cells = v4.loc[v4["source_closeout_status"].astype(str).ne("NOT_REVIEW_REQUIRED"), "cell_id"].astype(str).tolist()
    rows.append(
        {
            "cell_id": "ALL" if not metadata_cells else "|".join(metadata_cells),
            "change_type": "metadata_only_source_review_closeout",
            "paired_cell_id": "",
            "diff_note": "B8.6g3 did not replace rows; it added source-review metadata and caveats to B8.7a v3.",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    )
    return pd.DataFrame(rows)


def run(config_path: Path = DEFAULT_CONFIG) -> CellCloseoutResult:
    """Run manual source-review closeout and write N300 v4 design."""
    config = load_config(config_path)
    closeout = build_closeout(config)
    write_csv(closeout, output_path(config, "manual_source_review_closeout_path"))
    v4 = build_v4(config, closeout)
    write_csv(v4, output_path(config, "n300_design_v4_source_reviewed_path"))
    write_csv(diff_vs_b87a(config, v4), output_path(config, "n300_v4_diff_vs_b87a_path"))
    n150_overlap = len(set(v4["cell_id"].astype(str)).intersection(current_n150_cells(config)))
    duplicate_count = int(v4["cell_id"].astype(str).duplicated().sum())
    source_review_cells = set(config_list(config, "source_review_cells"))
    closed = int(
        closeout.loc[closeout["source_review_cell"].astype(str).isin(source_review_cells), "recommended_closeout"]
        .astype(str)
        .eq("KEEP_WITH_CAVEAT")
        .sum()
    )
    expected = int(config.get("expected_n300_count", 150))
    blocked = int(closeout["execution_precheck_blocker"].astype(str).eq("yes").sum())
    status = "B86G3_CELL_SOURCE_CLOSEOUT_PASS" if len(v4) == expected and n150_overlap == 0 and duplicate_count == 0 and blocked == 0 else "B86G3_BLOCKED_SOURCE_REVIEW"
    return CellCloseoutResult(
        status=status,
        source_review_cells_closed=closed,
        v4_rows=len(v4),
        n150_overlap_count=n150_overlap,
        duplicate_count=duplicate_count,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Close B8.7a manual source-review cells and write B8.6g3 v4 "
            "source-reviewed design. No row replacement unless required; no "
            "raster/QGIS/SOLWEIG/manifest/AOI/B9/WBGT/hazard/risk output."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
