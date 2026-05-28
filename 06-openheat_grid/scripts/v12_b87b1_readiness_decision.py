"""Decide B8.7b.1 local asset-remap readiness and write reports.

Inputs:
    B8.7b.1 input inventory, prior local-root inventory, manual-root template,
    asset pattern registry, per-cell expected paths, and per-asset metadata
    audit CSVs.
Outputs:
    b87b1_cell_asset_readiness_resolved.csv, missing/root/blocker/checklist
    registers, no-raster-touch audit, next-lane matrix, future prompts,
    b87b1_report.md, B8_7B1_STATUS.md, and the UTF-8 Chinese doc.
Saved metrics:
    Final decision status, manual-root presence, root resolution count, 150-cell
    path readiness counts, per-asset ready counts, missing/ambiguous headlines,
    no-raster/no-runner/no-manifest boundaries, AOI/B9 blocked status, and
    recommended next lane. This script writes compact CSV/Markdown only.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from v12_b87b1_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, clean, git_output, load_config, out_path
from v12_b87b1_input_inventory import read_csv_rows, rel_path, write_csv_rows, write_text


@dataclass(frozen=True)
class ReadinessDecisionResult:
    """B8.7b.1 final decision result."""

    status: str
    manual_local_roots_found: bool
    roots_resolved_count: int
    new_candidate_count: int
    cell_tile_folder_resolved_count: int
    svf_ready_count: int
    dsm_ready_count: int
    cdsm_ready_count: int
    dem_ready_count: int
    landcover_ready_count: int
    met_forcing_ready_count: int
    output_root_ready_count: int
    missing_ambiguous_headline: str
    no_raster_touch_headline: str
    recommended_next_lane: str


FILES_CREATED = [
    "configs/v12/systemb_b87b1_local_asset_remap.yaml",
    "scripts/v12_b87b1_input_inventory.py",
    "scripts/v12_b87b1_local_root_inventory.py",
    "scripts/v12_b87b1_manual_root_template.py",
    "scripts/v12_b87b1_asset_path_patterns.py",
    "scripts/v12_b87b1_cell_asset_resolver.py",
    "scripts/v12_b87b1_asset_metadata_audit.py",
    "scripts/v12_b87b1_readiness_decision.py",
    "scripts/v12_b87b1_run_local_asset_remap.py",
    "docs/v12/OpenHeat_SystemB_B8_7b1_local_asset_remap_CN.md",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_input_inventory.csv",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_prior_local_root_inventory.csv",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_manual_local_root_template.csv",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_manual_local_root_instructions.md",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_asset_pattern_registry.csv",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_cell_asset_expected_paths.csv",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_cell_asset_metadata_audit.csv",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_cell_asset_readiness_resolved.csv",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_missing_asset_register.csv",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_local_root_gap_register.csv",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_b87c_prerequisite_checklist.csv",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_b87c_blocker_register.csv",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_no_raster_touch_audit.csv",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_next_lane_decision_matrix.csv",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_codex_prompt_B87C_N300_execution_package.md",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_codex_prompt_B87B2_local_asset_fix.md",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_report.md",
    "outputs/v12_surrogate/b8_7b1_local_asset_remap/B8_7B1_STATUS.md",
]


def group_audit_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    """Group audit rows by cell and asset kind."""
    grouped: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        grouped[clean(row.get("cell_id"))][clean(row.get("asset_kind"))] = row
    return grouped


def is_ready(row: dict[str, str] | None) -> bool:
    """Return true when an audit row is metadata-ready."""
    return bool(row) and clean(row.get("blocker_level")) == "none" and clean(row.get("exists_by_metadata_check")) == "yes"


def cell_status(rows: dict[str, dict[str, str]]) -> tuple[str, str, str]:
    """Return per-cell readiness status, blocker summary, and next action."""
    blockers = [clean(row.get("blocker_level")) for row in rows.values() if clean(row.get("blocker_level")) != "none"]
    blocker_counts = Counter(blockers)
    if not blockers:
        return "READY_METADATA_ONLY", "none", "B8.7c prepackage only after explicit authorization"
    summary = "; ".join(f"{key}={value}" for key, value in sorted(blocker_counts.items()))
    if blocker_counts.get("ambiguous_multiple_matches"):
        return "AMBIGUOUS_NEEDS_REVIEW", summary, "review duplicate/ambiguous asset filenames by metadata only"
    if blockers and set(blockers) == {"waiting_local_roots"}:
        return "WAITING_LOCAL_ROOTS", summary, "fill manual local-root CSV or expose local roots to the Codex environment"
    if blocker_counts.get("missing_asset", 0) >= 4:
        return "BLOCKED_BY_MISSING_ASSETS", summary, "repair or remap missing local cell assets before B8.7c"
    if blocker_counts.get("missing_asset"):
        return "PARTIAL_MISSING_ASSETS", summary, "repair missing local assets and rerun B8.7b.1"
    return "WAITING_LOCAL_ROOTS", summary, "resolve local root/path uncertainty"


def make_readiness_rows(expected: list[dict[str, str]], audit_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Create one resolved readiness row per candidate cell."""
    grouped = group_audit_rows(audit_rows)
    rows: list[dict[str, Any]] = []
    for cell in expected:
        cell_id = clean(cell.get("cell_id"))
        assets = grouped.get(cell_id, {})
        status, blocker_summary, next_action = cell_status(assets)
        output_ready = is_ready(assets.get("output_root"))
        rows.append(
            {
                "cell_id": cell_id,
                "svf_ready": "yes" if is_ready(assets.get("svf")) else "no",
                "dsm_ready": "yes" if is_ready(assets.get("dsm")) else "no",
                "cdsm_ready": "yes" if is_ready(assets.get("cdsm")) else "no",
                "dem_ready": "yes" if is_ready(assets.get("dem")) else "no",
                "landcover_ready": "yes" if is_ready(assets.get("landcover")) else "no",
                "met_forcing_ready": "yes" if is_ready(assets.get("met_forcing")) else "no",
                "qgis_manual_check_ready": "yes" if is_ready(assets.get("qgis_manual_check")) else "no",
                "output_root_status": "ROOT_SELECTED_METADATA_ONLY" if output_ready else "WAITING_LOCAL_ROOTS",
                "cell_tile_folder_ready": "yes" if is_ready(assets.get("cell_tile_folder")) else "no",
                "all_required_assets_ready": "yes" if status == "READY_METADATA_ONLY" else "no",
                "readiness_status": status,
                "blocker_summary": blocker_summary,
                "next_action": next_action,
                "metadata_only": "true",
                "not_run_ready": "true",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return rows


def write_missing_register(config: dict[str, Any], audit_rows: list[dict[str, str]]) -> tuple[int, int, int]:
    """Write missing/ambiguous asset register and return counts."""
    blockers = [row for row in audit_rows if clean(row.get("blocker_level")) not in {"", "none"}]
    write_csv_rows(
        out_path(config, "b87b1_missing_asset_register.csv"),
        blockers,
        [
            "cell_id",
            "asset_kind",
            "candidate_path_or_pattern",
            "exists_by_metadata_check",
            "candidate_count",
            "matched_file_count",
            "matched_file_names_preview",
            "total_size_bytes",
            "suffixes_seen",
            "blocker_level",
            "metadata_only",
            "not_run_ready",
            "claim_boundary",
        ],
    )
    counts = Counter(clean(row.get("blocker_level")) for row in blockers)
    return counts["waiting_local_roots"], counts["missing_asset"], counts["ambiguous_multiple_matches"]


def write_root_gap_register(config: dict[str, Any], roots: list[dict[str, str]]) -> int:
    """Write local-root gap register and return required gap count."""
    gaps = [
        {
            "root_key": clean(row.get("root_key")),
            "candidate_path": clean(row.get("candidate_path")),
            "source": clean(row.get("source")),
            "required": clean(row.get("required")),
            "exists_by_metadata_check": clean(row.get("exists_by_metadata_check")),
            "is_dir": clean(row.get("is_dir")),
            "user_status": clean(row.get("user_status")),
            "blocker_type": "manual_root_needed" if clean(row.get("required")) == "yes" else "optional_root_unresolved",
            "next_action": "fill manual local-root CSV with user_status=use or repair local root",
            "claim_boundary": CLAIM_BOUNDARY,
        }
        for row in roots
        if clean(row.get("required")) == "yes" and clean(row.get("exists_by_metadata_check")) != "yes"
    ]
    write_csv_rows(
        out_path(config, "b87b1_local_root_gap_register.csv"),
        gaps,
        [
            "root_key",
            "candidate_path",
            "source",
            "required",
            "exists_by_metadata_check",
            "is_dir",
            "user_status",
            "blocker_type",
            "next_action",
            "claim_boundary",
        ],
    )
    return len(gaps)


def count_yes(rows: list[dict[str, str]], field: str) -> int:
    """Count yes values in a readiness field."""
    return sum(1 for row in rows if clean(row.get(field)) == "yes")


def decide_final_status(
    new_count: int,
    ready_cells: int,
    root_gap_count: int,
    waiting_rows: int,
    missing_rows: int,
    ambiguous_rows: int,
    cell_folder_ready: int,
) -> str:
    """Apply B8.7b.1 decision statuses."""
    if new_count == 0:
        return "FAILED"
    if ready_cells == new_count and root_gap_count == 0 and ambiguous_rows == 0:
        return "B87B1_LOCAL_ASSET_REMAP_PASS"
    if root_gap_count > 0 or (waiting_rows > 0 and cell_folder_ready == 0):
        return "B87B1_WAITING_LOCAL_ROOTS"
    if missing_rows > new_count * 3:
        return "B87B1_BLOCKED_BY_MISSING_ASSETS"
    if missing_rows > 0 or ambiguous_rows > 0:
        return "B87B1_PARTIAL_MISSING_ASSETS"
    if ready_cells >= int(new_count * 0.9):
        return "B87B1_READY_FOR_B87C_PREPACKAGE"
    return "B87B1_DIAGNOSTIC_ONLY"


def checklist_row(item: str, status: str, evidence: str, blocker_type: str, next_action: str) -> dict[str, str]:
    """Create one B8.7c prerequisite checklist row."""
    return {
        "check_item": item,
        "status": status,
        "evidence": evidence,
        "blocker_type": blocker_type,
        "next_action": next_action,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def write_checklist(
    config: dict[str, Any],
    new_count: int,
    ready: list[dict[str, str]],
    root_gap_count: int,
    waiting_rows: int,
    missing_rows: int,
    ambiguous_rows: int,
) -> None:
    """Write the non-executable B8.7c prerequisite checklist."""
    cell_count = len(ready)
    svf = count_yes(ready, "svf_ready")
    dsm = count_yes(ready, "dsm_ready")
    cdsm = count_yes(ready, "cdsm_ready")
    dem = count_yes(ready, "dem_ready")
    landcover = count_yes(ready, "landcover_ready")
    met = count_yes(ready, "met_forcing_ready")
    qgis = count_yes(ready, "qgis_manual_check_ready")
    output = sum(1 for row in ready if clean(row.get("output_root_status")) == "ROOT_SELECTED_METADATA_ONLY")
    tile = count_yes(ready, "cell_tile_folder_ready")
    rows = [
        checklist_row("N300 v4 design valid", "PASS", "B8.7b validation already passed; v4 candidate count=150", "none", "none"),
        checklist_row("150 new candidates", "PASS" if new_count == 150 else "BLOCKED", f"new_candidate_count={new_count}", "design_count", "repair input design/count"),
        checklist_row("3000 run preview", "PASS", "B8.7b preview rows=3000 and not_run_ready=true", "none", "future B8.7c may convert only after explicit authorization"),
        checklist_row("local asset root selected", "PASS" if root_gap_count == 0 else "WAITING_LOCAL_ROOTS", f"required_root_gaps={root_gap_count}", "local_root_gap", "fill manual local roots or expose roots"),
        checklist_row("cell_tile_folder resolved for all 150", "PASS" if tile == 150 else "WAITING_LOCAL_ROOTS", f"resolved={tile}/{cell_count}", "cell_tile_folder", "resolve per-cell tile folders"),
        checklist_row("SVF metadata exists for all 150", "PASS" if svf == 150 else "BLOCKED", f"ready={svf}/{cell_count}", "missing_asset", "repair/remap SVF files"),
        checklist_row("DSM metadata exists for all 150", "PASS" if dsm == 150 else "BLOCKED", f"ready={dsm}/{cell_count}", "missing_asset", "repair/remap DSM files"),
        checklist_row("CDSM metadata exists for all 150", "PASS" if cdsm == 150 else "BLOCKED", f"ready={cdsm}/{cell_count}", "missing_asset", "repair/remap CDSM files"),
        checklist_row("DEM metadata exists for all 150", "PASS" if dem == 150 else "BLOCKED", f"ready={dem}/{cell_count}", "missing_asset", "repair/remap DEM files"),
        checklist_row("landcover metadata exists for all 150", "PASS" if landcover == 150 else "BLOCKED", f"ready={landcover}/{cell_count}", "missing_asset", "repair/remap landcover files"),
        checklist_row("met forcing root exists", "PASS" if met == 150 else "WAITING_LOCAL_ROOTS", f"ready={met}/{cell_count}", "local_root_gap", "select verified met forcing root"),
        checklist_row("qgis manual check exists", "PASS" if qgis == 150 else "WAITING_LOCAL_ROOTS", f"ready={qgis}/{cell_count}", "manual_check_gap", "verify QGIS manual check file/folder"),
        checklist_row("output root selected", "PASS" if output == 150 else "WAITING_LOCAL_ROOTS", f"ready={output}/{cell_count}", "output_root_gap", "select local-only output root; do not create here"),
        checklist_row("no raster touched", "PASS", "metadata-only audit; no raster read/write/copy/open", "none", "none"),
        checklist_row("no run-ready manifest", "PASS", "B8.7b.1 writes expected paths/checklists only", "none", "B8.7c only after explicit authorization"),
        checklist_row("no runner", "PASS", "no QGIS runner and no local runner created", "none", "B8.7c only after explicit authorization"),
        checklist_row("AOI/B9 blocked", "PASS", "AOI_PREFLIGHT_BLOCKED and B9_BLOCKED remain", "aoi_b9_boundary", "B8.6g4 external-vector acquisition before AOI/B9"),
    ]
    if waiting_rows or missing_rows or ambiguous_rows:
        rows.append(
            checklist_row(
                "missing or ambiguous asset review",
                "WARN",
                f"waiting={waiting_rows}; missing={missing_rows}; ambiguous={ambiguous_rows}",
                "asset_review",
                "use B8.7b.2 local asset fix before B8.7c",
            )
        )
    write_csv_rows(
        out_path(config, "b87b1_b87c_prerequisite_checklist.csv"),
        rows,
        ["check_item", "status", "evidence", "blocker_type", "next_action", "claim_boundary"],
    )


def write_blockers(config: dict[str, Any], decision: str, root_gap_count: int, waiting: int, missing: int, ambiguous: int) -> None:
    """Write B8.7c blocker register."""
    rows = [
        {
            "blocker_id": "local_asset_roots",
            "status": "PASS" if root_gap_count == 0 else "WAITING_LOCAL_ROOTS",
            "blocker_level": "none" if root_gap_count == 0 else "b87c_blocker",
            "evidence": f"required_root_gaps={root_gap_count}",
            "next_action": "fill manual local-root CSV if gaps remain",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "blocker_id": "cell_asset_metadata",
            "status": "PASS" if waiting == 0 and missing == 0 and ambiguous == 0 else decision,
            "blocker_level": "none" if waiting == 0 and missing == 0 and ambiguous == 0 else "b87c_blocker",
            "evidence": f"waiting={waiting}; missing={missing}; ambiguous={ambiguous}",
            "next_action": "repair/remap assets before any B8.7c manifest",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "blocker_id": "run_ready_manifest",
            "status": "BLOCKED_BY_LANE_BOUNDARY",
            "blocker_level": "intentional_boundary",
            "evidence": "B8.7b.1 must not create a run-ready N300 manifest",
            "next_action": "future B8.7c only after explicit authorization",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "blocker_id": "runner",
            "status": "BLOCKED_BY_LANE_BOUNDARY",
            "blocker_level": "intentional_boundary",
            "evidence": "B8.7b.1 must not create QGIS/local runners",
            "next_action": "future B8.7c only after explicit authorization",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "blocker_id": "aoi_b9",
            "status": "AOI_PREFLIGHT_BLOCKED_B9_BLOCKED",
            "blocker_level": "outside_lane_blocker",
            "evidence": "external vector gaps remain; this lane is N300 asset readiness only",
            "next_action": "B8.6g4 external-vector acquisition before AOI/B9",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    write_csv_rows(
        out_path(config, "b87b1_b87c_blocker_register.csv"),
        rows,
        ["blocker_id", "status", "blocker_level", "evidence", "next_action", "claim_boundary"],
    )


def write_no_raster_touch(config: dict[str, Any]) -> str:
    """Write the no-raster-touch audit."""
    rows = [
        ("no_raster_read_open", "PASS", "Scripts use path metadata and glob filenames only; no rasterio/GDAL calls."),
        ("no_raster_write_create", "PASS", "No raster suffix outputs are created by this lane."),
        ("no_raster_copy_move", "PASS", "No copy/move logic is implemented for local assets."),
        ("no_svfs_zip_open", "PASS", "svfs.zip is referenced only as a forbidden boundary."),
        ("no_qgis_solweig", "PASS", "No QGIS/SOLWEIG command or runner is executed."),
        ("no_run_ready_manifest", "PASS", "Only expected-path/checklist CSVs are written."),
        ("no_qgis_runner", "PASS", "No scripts/qgis file is created."),
        ("no_local_runner", "PASS", "No local runner or execution package is created."),
    ]
    write_csv_rows(
        out_path(config, "b87b1_no_raster_touch_audit.csv"),
        [
            {"audit_item": item, "status": status, "evidence": evidence, "claim_boundary": CLAIM_BOUNDARY}
            for item, status, evidence in rows
        ],
        ["audit_item", "status", "evidence", "claim_boundary"],
    )
    return "PASS: no raster read/write/copy/open; no QGIS/SOLWEIG; no manifest/runner"


def write_next_lane(config: dict[str, Any], decision: str, recommended_next_lane: str) -> None:
    """Write next lane decision matrix."""
    rows = [
        {
            "future_lane": "B8.7c_N300_execution_package",
            "decision": "BLOCKED_UNTIL_EXPLICIT_AUTHORIZATION" if "PASS" in decision or "READY" in decision else "BLOCKED_BY_B87B1",
            "why": "May create real manifest/local runner only in a future lane after explicit authorization and local-only output rules.",
            "next_action": recommended_next_lane,
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "future_lane": "B8.7b.2_local_asset_fix",
            "decision": "RECOMMENDED" if decision not in {"B87B1_LOCAL_ASSET_REMAP_PASS", "B87B1_READY_FOR_B87C_PREPACKAGE"} else "OPTIONAL",
            "why": "Fill manual local roots or repair missing/ambiguous assets if B8.7b.1 is waiting or blocked.",
            "next_action": "Use b87b1_codex_prompt_B87B2_local_asset_fix.md",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "future_lane": "B9",
            "decision": "BLOCKED",
            "why": "AOI/B9 true-vector gaps remain; B8.7b.1 is not AOI-wide prediction.",
            "next_action": "B8.6g4 external-vector acquisition before AOI/B9",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    write_csv_rows(
        out_path(config, "b87b1_next_lane_decision_matrix.csv"),
        rows,
        ["future_lane", "decision", "why", "next_action", "claim_boundary"],
    )


def write_prompts(config: dict[str, Any]) -> None:
    """Write future lane prompts."""
    b87c = """# Future Codex Prompt: B8.7c N300 Execution Package

Future lane only. Start only after explicit user authorization to create a real B8.7c N300 execution package.

Start from B8.7b.1 outputs:

- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_cell_asset_readiness_resolved.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_cell_asset_expected_paths.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_b87c_prerequisite_checklist.csv`
- `outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_b87c_blocker_register.csv`

Allowed only after authorization:

- create a real N300 execution manifest;
- create a local-only QGIS/local runner;
- create smoke, pilot, production chunk, and full-new-N150 gates;
- keep local-only SOLWEIG outputs and run logs outside Git.

Required boundaries:

- Do not commit rasters, `svfs.zip`, local logs, or raw SOLWEIG outputs.
- Keep all local-only outputs outside the Git worktree.
- Include smoke/pilot/production chunk gates, resume checks, failure isolation, and postrun QA before label merge.
- Do not create AOI-wide prediction, B9 output, local WBGT, hazard_score, risk_score, exposure/vulnerability score, observed-truth claim, causal feature-importance claim, Tmrt-to-WBGT conversion, or System A/B coupling.
"""
    b87b2 = """# Future Codex Prompt: B8.7b.2 Local Asset Fix

Use this only if B8.7b.1 is `WAITING_LOCAL_ROOTS`, `PARTIAL_MISSING_ASSETS`, or `BLOCKED_BY_MISSING_ASSETS`.

Goal:

- fill or repair `manual_inputs/b87b1_manual_local_roots.csv`;
- verify local roots by metadata only;
- repair missing or ambiguous per-cell asset mappings;
- rerun the B8.7b.1 metadata-only readiness suite.

Still forbidden:

- no QGIS execution;
- no SOLWEIG execution;
- no run-ready N300 manifest;
- no QGIS runner;
- no local runner;
- no local execution package;
- no raster read/write/copy/open;
- no AOI-wide prediction, B9, local WBGT, hazard/risk/exposure/vulnerability score, observed-truth claim, causal feature-importance claim, Tmrt-to-WBGT conversion, or System A/B coupling.
"""
    write_text(out_path(config, "b87b1_codex_prompt_B87C_N300_execution_package.md"), b87c)
    write_text(out_path(config, "b87b1_codex_prompt_B87B2_local_asset_fix.md"), b87b2)


def write_reports(
    config: dict[str, Any],
    result: ReadinessDecisionResult,
    root_gap_count: int,
    waiting_rows: int,
    missing_rows: int,
    ambiguous_rows: int,
    ready_cells: int,
) -> None:
    """Write English report, status, and Chinese documentation."""
    files_md = "\n".join(f"- `{path}`" for path in FILES_CREATED)
    manual_status = "yes" if result.manual_local_roots_found else "no"
    report = f"""# B8.7b.1 Local Asset Remap Readiness

Status: `{result.status}`

## 1. Why B8.7b.1 follows B8.7b

B8.7b ended at `B87B_PRECHECK_NEEDS_LOCAL_ASSET_REMAP`: the N300 v4 design and run preview were coherent, but the 150 new candidates had no resolved local cell-asset mapping. B8.7b.1 therefore resolves or classifies only the local asset/path gap.

## 2. What B8.7b already passed

B8.7b passed the 150 new-candidate count, 150 existing labelled N150 count, 300 unique-cell index, and 3000-row preview. The preview remains non-executable and not run-ready.

## 3. Local root discovery

Manual local roots found: `{manual_status}`. Roots resolved by metadata: `{result.roots_resolved_count}`. Required root gaps: `{root_gap_count}`.

## 4. Manual local root template status

`b87b1_manual_local_root_template.csv` and `b87b1_manual_local_root_instructions.md` were written. If roots cannot be inspected from this environment, fill the manual CSV at `{clean(config.get('manual_local_root_input_path'))}` and rerun.

## 5. Asset pattern registry

`b87b1_asset_pattern_registry.csv` declares cell tile folder, SVF, DSM, CDSM, DEM, landcover, met forcing, QGIS manual check, and output-root patterns. It creates no files.

## 6. Cell asset metadata audit

Audited `{result.new_candidate_count}` new candidates by metadata only. Cell tile folder resolved count: `{result.cell_tile_folder_resolved_count}`.

## 7. Resolved readiness for all 150 new candidates

Ready cells: `{ready_cells}/{result.new_candidate_count}`. SVF/DSM/CDSM/DEM/landcover ready counts: `{result.svf_ready_count}/{result.dsm_ready_count}/{result.cdsm_ready_count}/{result.dem_ready_count}/{result.landcover_ready_count}`.

## 8. Missing / ambiguous asset register

{result.missing_ambiguous_headline}

## 9. B8.7c prerequisite checklist

`b87b1_b87c_prerequisite_checklist.csv` keeps B8.7c manifest/runner creation blocked unless local asset mapping is resolved and the user explicitly authorizes the future lane.

## 10. Readiness decision

Final decision: `{result.status}`. Recommended next lane: `{result.recommended_next_lane}`.

## 11. What user must do if WAITING_LOCAL_ROOTS

Fill the manual local-root CSV with verified `use`, `missing`, `unknown`, or `not_applicable` statuses. Do not copy assets into Git; only provide compact metadata/path mappings, then rerun this lane.

## 12. Claim boundaries

Not B9; not AOI-wide prediction; not local WBGT; not risk/hazard score; not observed truth; not causal feature importance; no raster read/write/copy/open; no QGIS/SOLWEIG execution; no run-ready N300 manifest; no QGIS runner; no local runner; no Tmrt-to-WBGT conversion; no System A/B coupling.

## Files created

{files_md}
"""
    write_text(out_path(config, "b87b1_report.md"), report)

    status = f"""# B8.7b.1 Status

Status: {result.status}
Branch: codex/b87b1-local-asset-remap-readiness
Scope: local asset readiness and path remap only; no QGIS/SOLWEIG and no run-ready manifest.

## Key results

- manual local roots found: `{manual_status}`
- roots resolved count: `{result.roots_resolved_count}`
- new candidate count: `{result.new_candidate_count}`
- cell_tile_folder resolved count: `{result.cell_tile_folder_resolved_count}`
- SVF/DSM/CDSM/DEM/landcover ready counts: `{result.svf_ready_count}/{result.dsm_ready_count}/{result.cdsm_ready_count}/{result.dem_ready_count}/{result.landcover_ready_count}`
- met forcing readiness: `{result.met_forcing_ready_count}/{result.new_candidate_count}`
- output root status: `{result.output_root_ready_count}/{result.new_candidate_count}`
- missing / ambiguous asset headline: `{result.missing_ambiguous_headline}`
- no-raster-touch audit headline: `{result.no_raster_touch_headline}`
- AOI/B9 status: `AOI_PREFLIGHT_BLOCKED / B9_BLOCKED`
- recommended next lane: `{result.recommended_next_lane}`

## Commands

- `python scripts/v12_b87b1_run_local_asset_remap.py --config configs/v12/systemb_b87b1_local_asset_remap.yaml`

## Files created / modified

{files_md}

## Caveats

B8.7b.1 is metadata-only. It creates no local runner, QGIS runner, run-ready N300 manifest, local execution package, AOI-wide prediction, B9 output, local WBGT, hazard/risk score, exposure/vulnerability score, Tmrt-to-WBGT conversion, observed-truth claim, causal feature-importance claim, or System A/B coupling.
"""
    write_text(out_path(config, "B8_7B1_STATUS.md"), status)

    cn = f"""# OpenHeat System B B8.7b.1 本地资产重映射就绪性说明

## 结论

- 状态：`{result.status}`
- 手动本地根目录输入：`{manual_status}`
- 已解析根目录数量：`{result.roots_resolved_count}`
- 新候选单元数量：`{result.new_candidate_count}`
- cell tile folder 解析数量：`{result.cell_tile_folder_resolved_count}`
- SVF/DSM/CDSM/DEM/landcover 就绪数量：`{result.svf_ready_count}/{result.dsm_ready_count}/{result.cdsm_ready_count}/{result.dem_ready_count}/{result.landcover_ready_count}`
- met forcing 就绪：`{result.met_forcing_ready_count}/{result.new_candidate_count}`
- output root 就绪：`{result.output_root_ready_count}/{result.new_candidate_count}`
- AOI / B9：`AOI_PREFLIGHT_BLOCKED / B9_BLOCKED`

## 1. 为什么 B8.7b.1 接在 B8.7b 后面

B8.7b 已经确认 N300 v4 设计、300 个唯一单元索引和 3000 行预览计划成立，但 150 个新候选单元没有本地 cell asset 映射。因此 B8.7b.1 只处理本地根目录和资产路径重映射就绪性，不创建真正执行包。

## 2. B8.7b 已经通过的内容

B8.7b 已通过：150 个新候选、150 个既有 N150 标签单元、300 个唯一 cell、3000 个预览运行、forcing 设计来自 B8.5-F5。`b87b_run_plan_preview.csv` 仍然是 preview，不是 execution manifest。

## 3. 本地根目录发现

手动本地根目录输入为 `{manual_status}`；元数据可解析根目录数量为 `{result.roots_resolved_count}`；必需根目录缺口为 `{root_gap_count}`。所有检查只使用 `Path.exists`、`Path.is_dir`、`Path.is_file`、文件大小和文件名 glob 元数据。

## 4. 手动本地根目录模板状态

已写出 `b87b1_manual_local_root_template.csv` 和 `b87b1_manual_local_root_instructions.md`。如果当前 Codex 环境无法看到本地根目录，请在 `{clean(config.get('manual_local_root_input_path'))}` 填写手动 CSV 后重新运行。

## 5. 资产路径模式登记

`b87b1_asset_pattern_registry.csv` 只登记候选模式：cell tile folder、SVF、DSM、CDSM、DEM、landcover、met forcing、QGIS manual check 和 output root。它不创建文件、不创建目录、不复制资产。

## 6. Cell 资产元数据审计

已对 `{result.new_candidate_count}` 个新候选单元做元数据审计。cell tile folder 解析数量为 `{result.cell_tile_folder_resolved_count}`。

## 7. 150 个新候选的解析就绪性

ready cells 为 `{ready_cells}/{result.new_candidate_count}`。SVF/DSM/CDSM/DEM/landcover 就绪数量为 `{result.svf_ready_count}/{result.dsm_ready_count}/{result.cdsm_ready_count}/{result.dem_ready_count}/{result.landcover_ready_count}`。

## 8. 缺失 / 歧义资产登记

{result.missing_ambiguous_headline}

## 9. B8.7c 前置清单

`b87b1_b87c_prerequisite_checklist.csv` 明确保留 B8.7c manifest / runner gate。只有本地资产映射解决，并且用户明确授权未来 B8.7c lane 后，才可以创建真正 manifest 或 runner。

## 10. 就绪性决策

最终决策为 `{result.status}`。建议下一 lane：`{result.recommended_next_lane}`。

## 11. 如果状态是 WAITING_LOCAL_ROOTS，用户需要做什么

请只填写手动本地根目录 CSV，使用 `use`、`missing`、`unknown` 或 `not_applicable` 标记。不要把 raster、`svfs.zip`、本地 run log 或 SOLWEIG 输出复制进 Git。填写后重新运行 B8.7b.1。

## 12. 声明边界

- 不是 B9。
- 不是 AOI-wide prediction。
- 不是 local WBGT。
- 不是 risk / hazard score。
- 不是 observed truth。
- 不是 causal feature importance。
- 没有 raster read/write/copy/open。
- 没有 QGIS / SOLWEIG execution。
- 没有 run-ready N300 manifest。
- 没有 QGIS runner。
- 没有 local runner。
- 没有 Tmrt-to-WBGT conversion。
- 没有 System A/B coupling。
"""
    write_text(config["cn_doc_path"], cn)


def run(config_path: Path = DEFAULT_CONFIG) -> ReadinessDecisionResult:
    """Run final B8.7b.1 readiness decision."""
    config = load_config(config_path)
    expected = read_csv_rows(out_path(config, "b87b1_cell_asset_expected_paths.csv"))
    audit_rows = read_csv_rows(out_path(config, "b87b1_cell_asset_metadata_audit.csv"))
    roots = read_csv_rows(out_path(config, "b87b1_prior_local_root_inventory.csv"))

    ready_rows = make_readiness_rows(expected, audit_rows)
    write_csv_rows(
        out_path(config, "b87b1_cell_asset_readiness_resolved.csv"),
        ready_rows,
        [
            "cell_id",
            "svf_ready",
            "dsm_ready",
            "cdsm_ready",
            "dem_ready",
            "landcover_ready",
            "met_forcing_ready",
            "qgis_manual_check_ready",
            "output_root_status",
            "cell_tile_folder_ready",
            "all_required_assets_ready",
            "readiness_status",
            "blocker_summary",
            "next_action",
            "metadata_only",
            "not_run_ready",
            "claim_boundary",
        ],
    )

    waiting, missing, ambiguous = write_missing_register(config, audit_rows)
    root_gap_count = write_root_gap_register(config, roots)
    no_raster_headline = write_no_raster_touch(config)
    new_count = len(expected)
    ready_cells = count_yes(ready_rows, "all_required_assets_ready")
    cell_folder_ready = count_yes(ready_rows, "cell_tile_folder_ready")
    decision = decide_final_status(new_count, ready_cells, root_gap_count, waiting, missing, ambiguous, cell_folder_ready)
    recommended_next_lane = (
        "B8.7c_N300_execution_package_after_explicit_authorization"
        if decision in {"B87B1_LOCAL_ASSET_REMAP_PASS", "B87B1_READY_FOR_B87C_PREPACKAGE"}
        else "B8.7b.2_local_asset_fix"
    )

    write_checklist(config, new_count, ready_rows, root_gap_count, waiting, missing, ambiguous)
    write_blockers(config, decision, root_gap_count, waiting, missing, ambiguous)
    write_next_lane(config, decision, recommended_next_lane)
    write_prompts(config)

    manual_found = any(clean(row.get("source")) == "manual_input" for row in roots)
    roots_resolved = len(
        {
            clean(row.get("root_key"))
            for row in roots
            if clean(row.get("selected_for_resolution")) == "yes" and clean(row.get("root_key"))
        }
    )
    headline = f"waiting={waiting}; missing={missing}; ambiguous={ambiguous}"
    result = ReadinessDecisionResult(
        status=decision,
        manual_local_roots_found=manual_found,
        roots_resolved_count=roots_resolved,
        new_candidate_count=new_count,
        cell_tile_folder_resolved_count=cell_folder_ready,
        svf_ready_count=count_yes(ready_rows, "svf_ready"),
        dsm_ready_count=count_yes(ready_rows, "dsm_ready"),
        cdsm_ready_count=count_yes(ready_rows, "cdsm_ready"),
        dem_ready_count=count_yes(ready_rows, "dem_ready"),
        landcover_ready_count=count_yes(ready_rows, "landcover_ready"),
        met_forcing_ready_count=count_yes(ready_rows, "met_forcing_ready"),
        output_root_ready_count=sum(1 for row in ready_rows if clean(row.get("output_root_status")) == "ROOT_SELECTED_METADATA_ONLY"),
        missing_ambiguous_headline=headline,
        no_raster_touch_headline=no_raster_headline,
        recommended_next_lane=recommended_next_lane,
    )
    write_reports(config, result, root_gap_count, waiting, missing, ambiguous, ready_cells)
    return result


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Create B8.7b.1 final local-asset readiness decision and reports. "
            "No QGIS/SOLWEIG, raster IO, manifest, or runner is created."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
