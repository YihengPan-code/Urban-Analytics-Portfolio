"""Audit SVF and overhead_as_canopy parity for B8.7b.3p.

Inputs:
    b87b3p_batch_protocol_matrix.csv, B8.7b.3 SVF scenario model, and B8.5
    compact protocol evidence.
Outputs:
    b87b3p_svf_scenario_parity.csv and
    b87b3p_overhead_protocol_parity.csv.
Saved metrics:
    Base/overhead SVF separation, overhead SVF non-reuse, overhead_as_canopy
    max-rule evidence, pure-building/pure-vegetation rejection, and planned
    B87C assertions. No QGIS/SOLWEIG, raster pixel reads, svfs.zip opens,
    manifest/runner creation, staging, or commits.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from v12_b87b3p_batch_discovery import ROLE_FINAL, ROLE_PLANNED, ROLE_SMOKE
from v12_b87b3p_protocol_extractor import run as run_protocol_extractor
from v12_b87b3p_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    clean,
    load_config,
    out_path,
    read_csv_rows,
    write_csv_rows,
)


SVF_FIELDS = [
    "batch_id",
    "role",
    "base_svf_method",
    "overhead_svf_method",
    "svf_artifact_type",
    "base_and_overhead_separate",
    "overhead_reuses_base_svf",
    "overhead_svf_scenario_specific",
    "pure_building_or_pure_vegetation_svf_used",
    "svf_parity_status",
    "notes",
    "claim_boundary",
]

OVERHEAD_FIELDS = [
    "batch_id",
    "role",
    "overhead_layer_path",
    "overhead_as_canopy_rule",
    "rule_matches_max_existing_vegetation_overhead_canopy",
    "protocol_status",
    "required_b87c_assertion",
    "notes",
    "claim_boundary",
]


def ensure_protocol_matrix(config: dict[str, Any], config_path: str | Path) -> list[dict[str, str]]:
    """Read protocol matrix, creating it if missing."""
    path = out_path(config, "b87b3p_batch_protocol_matrix.csv")
    if not path.exists():
        run_protocol_extractor(config_path)
    return read_csv_rows(path)


def batch_values(matrix: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Return protocol values keyed by batch ID."""
    values: dict[str, dict[str, str]] = {}
    for row in matrix:
        batch_id = clean(row.get("batch_id", ""))
        if not batch_id:
            continue
        values.setdefault(batch_id, {"role": clean(row.get("role", ""))})
        values[batch_id][clean(row.get("dimension_name", ""))] = clean(row.get("protocol_value", ""))
    return values


def classify_svf(batch_id: str, values: dict[str, str]) -> dict[str, Any]:
    """Classify SVF parity for one batch."""
    role = clean(values.get("role", ""))
    base_method = clean(values.get("base_svf_source_or_generation_method", ""))
    overhead_method = clean(values.get("overhead_svf_source_or_generation_method", ""))
    artifact = clean(values.get("SVF artifact type", ""))
    joined = f"{base_method} {overhead_method} {artifact}".lower()
    separate = ("svf_base" in joined and "svf_overhead" in joined) or "must not reuse base" in joined or "scenario-specific" in joined
    reuses_base = "reuse base" in joined and "must not reuse base" not in joined
    scenario_specific = "scenario-specific" in joined or "svf_overhead_as_canopy" in joined or "svf_overhead" in joined
    pure_invalid = "pure building" in joined or "pure vegetation" in joined

    if role == ROLE_FINAL:
        status = "PASS_FINAL_SVF_SEPARATE" if separate and not reuses_base and not pure_invalid else "B87B3P_BLOCKED_OVERHEAD_SVF_MISMATCH"
        notes = "F5 final labels reference distinct base and overhead_as_canopy per-tile SVF paths." if status.startswith("PASS") else "Final labels do not prove safe overhead SVF handling."
    elif role == ROLE_PLANNED:
        status = "PASS_PLANNED_ASSERTION_REQUIRED" if scenario_specific and not reuses_base else "B87B3P_BLOCKED_OVERHEAD_SVF_MISMATCH"
        notes = "B87C source lock requires scenario-specific overhead SVF materialization and no base-SVF reuse."
    elif role == "unknown":
        status = "UNKNOWN_REQUIRES_REVIEW"
        notes = "SVF protocol is not established."
    else:
        status = "WARN_NONFINAL_PROTOCOL_DIFFERENCE"
        notes = "Nonfinal smoke/deprecated SVF differences are caveats, not final ML label mixing."
    return {
        "batch_id": batch_id,
        "role": role,
        "base_svf_method": base_method,
        "overhead_svf_method": overhead_method,
        "svf_artifact_type": artifact,
        "base_and_overhead_separate": "yes" if separate else "unknown",
        "overhead_reuses_base_svf": "yes" if reuses_base else "no",
        "overhead_svf_scenario_specific": "yes" if scenario_specific else "unknown",
        "pure_building_or_pure_vegetation_svf_used": "yes" if pure_invalid else "no",
        "svf_parity_status": status,
        "notes": notes,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def classify_overhead(batch_id: str, values: dict[str, str]) -> dict[str, Any]:
    """Classify overhead_as_canopy protocol parity for one batch."""
    role = clean(values.get("role", ""))
    overhead_path = clean(values.get("overhead_layer_path", ""))
    rule = clean(values.get("overhead_as_canopy_rule", ""))
    rule_lower = rule.lower()
    rule_matches = "max" in rule_lower and "vegetation" in rule_lower and ("overhead" in rule_lower or "canopy" in rule_lower)
    if role in {ROLE_FINAL, ROLE_PLANNED}:
        status = "PASS" if rule_matches and overhead_path else "UNKNOWN_REQUIRES_REVIEW"
    elif role == "unknown":
        status = "UNKNOWN_REQUIRES_REVIEW"
    else:
        status = "WARN_NONFINAL_PROTOCOL_DIFFERENCE"
    return {
        "batch_id": batch_id,
        "role": role,
        "overhead_layer_path": overhead_path,
        "overhead_as_canopy_rule": rule,
        "rule_matches_max_existing_vegetation_overhead_canopy": "yes" if rule_matches else "unknown",
        "protocol_status": status,
        "required_b87c_assertion": (
            "Assert overhead CDSM = max(existing vegetation DSM, overhead canopy) and assert overhead SVF path differs from base SVF path."
            if role == ROLE_PLANNED
            else ""
        ),
        "notes": "Final/planned overhead_as_canopy rule is compatible." if status == "PASS" else "Review overhead protocol before reuse.",
        "claim_boundary": CLAIM_BOUNDARY,
    }


def run(config_path: str | Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    """Run SVF and overhead parity audit."""
    config = load_config(config_path)
    matrix = ensure_protocol_matrix(config, config_path)
    values_by_batch = batch_values(matrix)
    svf_rows = [classify_svf(batch_id, values) for batch_id, values in sorted(values_by_batch.items())]
    overhead_rows = [classify_overhead(batch_id, values) for batch_id, values in sorted(values_by_batch.items())]
    write_csv_rows(out_path(config, "b87b3p_svf_scenario_parity.csv"), svf_rows, SVF_FIELDS)
    write_csv_rows(out_path(config, "b87b3p_overhead_protocol_parity.csv"), overhead_rows, OVERHEAD_FIELDS)
    return svf_rows


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Audit B8.7b.3p SVF and overhead_as_canopy parity. Reads compact "
            "evidence only; no QGIS/SOLWEIG or raster/svfs.zip content access."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    rows = run(args.config)
    print(f"svf_parity_rows={len(rows)}")


if __name__ == "__main__":
    main()
