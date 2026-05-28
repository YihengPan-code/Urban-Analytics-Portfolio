"""Assess extraction/materialization feasibility without extracting rasters.

Inputs:
    b87b3_version_lock_decision.csv, b87b3_svf_scenario_model.csv,
    b87b3_overhead_source_inventory.csv, b87b3_header_metadata.csv, and
    b87b3_grid_source_audit.csv.
Outputs:
    b87b3_extraction_feasibility_matrix.csv.
Saved metrics:
    Base and overhead_as_canopy feasibility, DEM/landcover blocker status,
    SVF full-AOI versus per-tile svfs.zip caveat, grid/header status, and next
    action. No extraction, raster sampling, raster writing, QGIS/SOLWEIG, or
    runner/manifest creation is performed.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from v12_b87b3_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, clean, load_config, out_path, read_csv_rows, write_csv_rows


def by_kind(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Index source-lock rows by source kind."""
    return {clean(row.get("source_kind")): row for row in rows}


def row_status(lock_rows: dict[str, dict[str, str]], source_kind: str) -> str:
    """Return lock status by source kind."""
    return clean(lock_rows.get(source_kind, {}).get("lock_status"))


def overhead_support(config: dict[str, Any]) -> str:
    """Return yes/no for overhead source support."""
    rows = read_csv_rows(out_path(config, "b87b3_overhead_source_inventory.csv"))
    return "yes" if any(clean(row.get("supports_overhead_scenario")) == "yes" for row in rows) else "no"


def header_summary(config: dict[str, Any]) -> str:
    """Return compact header metadata summary."""
    rows = read_csv_rows(out_path(config, "b87b3_header_metadata.csv"))
    if not rows:
        return "HEADER_NOT_CHECKED"
    ok = sum(1 for row in rows if clean(row.get("header_status")) == "HEADER_OK")
    return f"HEADER_OK={ok}/{len(rows)}"


def grid_support(config: dict[str, Any]) -> str:
    """Return canonical grid support status."""
    rows = read_csv_rows(out_path(config, "b87b3_grid_source_audit.csv"))
    if not rows:
        return "no"
    return clean(rows[0].get("supports_150_new_n300_cells"))


def run(config_path: Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    """Run feasibility assessment."""
    config = load_config(config_path)
    lock_rows = by_kind(read_csv_rows(out_path(config, "b87b3_version_lock_decision.csv")))
    overhead_ok = overhead_support(config)
    grid_ok = grid_support(config)
    headers = header_summary(config)
    dsm_ok = row_status(lock_rows, "dsm") == "LOCKED"
    cdsm_ok = row_status(lock_rows, "cdsm_base_vegetation") == "LOCKED"
    grid_locked = row_status(lock_rows, "grid_geometry") == "LOCKED" and grid_ok == "yes"
    base_svf_ok = row_status(lock_rows, "svf_base_full") == "LOCKED_FULL_AOI_SOURCE_ONLY"
    base_ready = dsm_ok and cdsm_ok and grid_locked and base_svf_ok
    overhead_ready = base_ready and overhead_ok == "yes"
    rows = [
        {
            "check_item": "base_scenario_pre_materialization",
            "scenario": "base",
            "status": "FEASIBLE_FOR_B87B4_PREMATERIALIZATION" if base_ready else "BLOCKED_MISSING_CRITICAL_SOURCE",
            "evidence": f"dsm={row_status(lock_rows, 'dsm')}; cdsm={row_status(lock_rows, 'cdsm_base_vegetation')}; grid={row_status(lock_rows, 'grid_geometry')}/{grid_ok}; base_svf={row_status(lock_rows, 'svf_base_full')}; {headers}",
            "blocker": "" if base_ready else "DSM/CDSM/grid/base SVF source lock incomplete",
            "next_action": "B8.7b.4 may design local-only per-cell/tile materialization; do not execute B87C directly",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "check_item": "overhead_as_canopy_pre_materialization",
            "scenario": "overhead_as_canopy",
            "status": "FEASIBLE_FOR_B87B4_PREMATERIALIZATION" if overhead_ready else "OVERHEAD_SOURCE_MISSING_OR_BASE_BLOCKED",
            "evidence": f"base_ready={base_ready}; overhead_source={overhead_ok}; overhead_svf=SCENARIO_SPECIFIC_SVF_REQUIRED",
            "blocker": "" if overhead_ready else "overhead vector missing or base source lock incomplete",
            "next_action": "Generate scenario-specific per-cell/tile svfs.zip later from building DSM + max(existing vegetation DSM, overhead canopy)",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "check_item": "dem_convention",
            "scenario": "all",
            "status": "NOT_BLOCKER",
            "evidence": row_status(lock_rows, "dem"),
            "blocker": "",
            "next_action": "Future lane should generate flat DEM tiles locally; no full DEM required here",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "check_item": "landcover_convention",
            "scenario": "all",
            "status": "NOT_BLOCKER",
            "evidence": row_status(lock_rows, "landcover"),
            "blocker": "",
            "next_action": "Keep INPUT_LC=None and USE_LC_BUILD=false unless a future issue changes source-of-truth",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "check_item": "direct_b87c_execution",
            "scenario": "all",
            "status": "BLOCKED",
            "evidence": "B8.7b.3 creates no per-cell assets, no execution package, and no run-ready manifest",
            "blocker": "per-cell local assets do not exist",
            "next_action": "B8.7c only after materialized local per-cell assets exist and user explicitly authorizes execution package",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    write_csv_rows(
        out_path(config, "b87b3_extraction_feasibility_matrix.csv"),
        rows,
        ["check_item", "scenario", "status", "evidence", "blocker", "next_action", "claim_boundary"],
    )
    return rows


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Assess B8.7b.3 extraction/materialization feasibility; writes "
            "b87b3_extraction_feasibility_matrix.csv without extracting rasters."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(f"feasibility_rows={len(run(args.config))}")


if __name__ == "__main__":
    main()
