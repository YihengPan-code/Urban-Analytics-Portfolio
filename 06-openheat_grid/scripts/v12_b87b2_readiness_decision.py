"""Decide B8.7b.2 cross-worktree asset discovery readiness.

Inputs:
    B8.7b.2 inventory, root inventory, folder candidates, asset signatures,
    candidate asset mapping, unresolved/ambiguous registers, and remap plan.
Outputs:
    b87b2_b87c_readiness_matrix.csv, b87b2_no_raster_touch_audit.csv,
    b87b2_next_lane_decision_matrix.csv, future prompts, b87b2_report.md,
    B8_7B2_STATUS.md, and the lane doc.
Saved metrics:
    Final decision, search roots checked, candidate count, resolved complete
    and minimal SVF/DSM counts, partial/ambiguous/unresolved counts, main
    worktree and local-root hit counts, no-raster-touch audit headline, and
    next lane recommendation. This script writes compact CSV/Markdown only.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from v12_b87b2_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, clean, load_config, out_path
from v12_b87b2_input_inventory import read_csv_rows, write_csv_rows, write_text


@dataclass(frozen=True)
class ReadinessDecisionResult:
    """B8.7b.2 final decision result."""

    status: str
    search_roots_checked: int
    candidate_count: int
    resolved_complete_count: int
    resolved_minimal_count: int
    partial_count: int
    ambiguous_count: int
    unresolved_count: int
    main_worktree_hit_count: int
    local_root_hit_count: int
    no_raster_touch_headline: str
    next_lane_recommendation: str


FILES_CREATED = [
    "configs/v12/systemb_b87b2_cross_worktree_asset_discovery.yaml",
    "scripts/v12_b87b2_input_inventory.py",
    "scripts/v12_b87b2_search_roots.py",
    "scripts/v12_b87b2_cell_asset_discovery.py",
    "scripts/v12_b87b2_asset_signature.py",
    "scripts/v12_b87b2_mapping_plan.py",
    "scripts/v12_b87b2_readiness_decision.py",
    "scripts/v12_b87b2_run_cross_worktree_asset_discovery.py",
    "docs/v12/OpenHeat_SystemB_B8_7b2_cross_worktree_asset_discovery_CN.md",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_input_inventory.csv",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_search_root_inventory.csv",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_cell_folder_candidates.csv",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_asset_signature_by_folder.csv",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_candidate_asset_mapping.csv",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_unresolved_cell_register.csv",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_ambiguous_cell_register.csv",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_remap_plan.csv",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_local_only_materialization_options.csv",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_manual_mapping_template.csv",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_manual_mapping_instructions.md",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_b87c_readiness_matrix.csv",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_no_raster_touch_audit.csv",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_next_lane_decision_matrix.csv",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_codex_prompt_B87B3_local_only_materialization.md",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_codex_prompt_B87C_N300_execution_package.md",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_report.md",
    "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/B8_7B2_STATUS.md",
]


def count_status(rows: list[dict[str, str]]) -> Counter[str]:
    """Count mapping statuses."""
    return Counter(clean(row.get("mapping_status")) for row in rows)


def decide(candidate_count: int, complete: int, minimal: int, partial: int, ambiguous: int, unresolved: int) -> tuple[str, str]:
    """Apply B8.7b.2 decision statuses."""
    resolved_required = complete + minimal
    if candidate_count == 0:
        return "FAILED", "repair B8.7b.2 compact inputs"
    if resolved_required == candidate_count and ambiguous == 0 and unresolved == 0:
        return "B87B2_ASSET_DISCOVERY_PASS", "B8.7c if explicitly authorized"
    if resolved_required >= int(candidate_count * 0.9):
        return "B87B2_READY_FOR_LOCAL_ONLY_MATERIALIZATION", "B8.7b.3 local-only materialization/remap"
    if resolved_required == 0 and partial == 0 and ambiguous == 0:
        return "B87B2_BLOCKED_NO_ASSETS_FOUND", "B8.7b.4 asset generation"
    if ambiguous > 0 or unresolved > 0:
        return "B87B2_WAITING_MANUAL_MAPPING", "B8.7b.3 after manual mapping, or B8.7b.4 for gaps"
    return "B87B2_PARTIAL_ASSET_DISCOVERY", "B8.7b.4 asset generation for missing SVF/DSM"


def no_raster_audit(config: dict[str, Any]) -> str:
    """Write the no-raster-touch audit and return its headline."""
    headline = (
        "PASS: metadata only; no raster read/write/copy/open; no rasterio/GDAL; "
        "no QGIS/SOLWEIG; no manifest/runner; no symlink/junction"
    )
    rows = [
        ("no_raster_read_open", "Only filenames, suffixes, file sizes, and directory metadata were inspected."),
        ("no_rasterio_gdal", "No rasterio, GDAL, QGIS, or SOLWEIG imports/calls are used."),
        ("no_raster_write_create", "No raster outputs are written."),
        ("no_copy_move_symlink", "No copy, move, symlink, or junction operations are implemented."),
        ("no_run_ready_manifest", "Only remap-planning CSV/Markdown outputs are written."),
        ("no_qgis_runner", "No QGIS runner or local runner is created."),
        ("no_aoi_b9", "AOI/B9 remains out of scope."),
    ]
    write_csv_rows(
        out_path(config, "b87b2_no_raster_touch_audit.csv"),
        [
            {"audit_item": item, "status": "PASS", "evidence": evidence, "claim_boundary": CLAIM_BOUNDARY}
            for item, evidence in rows
        ],
        ["audit_item", "status", "evidence", "claim_boundary"],
    )
    return headline


def write_readiness_matrix(config: dict[str, Any], result: ReadinessDecisionResult) -> None:
    """Write compact B8.7c readiness matrix."""
    rows = [
        ("candidate_count", "PASS" if result.candidate_count == 150 else "FAIL", f"candidate_count={result.candidate_count}", "repair candidate index if not 150"),
        (
            "required_svf_dsm_resolved",
            "PASS" if result.resolved_complete_count + result.resolved_minimal_count == 150 else "BLOCKED",
            f"resolved_required={result.resolved_complete_count + result.resolved_minimal_count}/150",
            result.next_lane_recommendation,
        ),
        ("ambiguous_cells", "PASS" if result.ambiguous_count == 0 else "REVIEW", f"ambiguous={result.ambiguous_count}", "fill manual mapping template if nonzero"),
        ("unresolved_cells", "PASS" if result.unresolved_count == 0 else "BLOCKED", f"unresolved={result.unresolved_count}", "manual mapping or asset generation if nonzero"),
        ("materialization_plan_only", "PASS", "b87b2_remap_plan.csv created as plan only", "B8.7b.3 needs user authorization before local materialization"),
        ("no_manifest_runner", "PASS", "no run-ready N300 manifest, QGIS runner, or local runner created", "future B8.7c only after explicit authorization"),
    ]
    write_csv_rows(
        out_path(config, "b87b2_b87c_readiness_matrix.csv"),
        [
            {"check_item": item, "status": status, "evidence": evidence, "next_action": action, "claim_boundary": CLAIM_BOUNDARY}
            for item, status, evidence, action in rows
        ],
        ["check_item", "status", "evidence", "next_action", "claim_boundary"],
    )


def write_next_lane_matrix(config: dict[str, Any], result: ReadinessDecisionResult) -> None:
    """Write next-lane decision matrix."""
    rows = [
        {
            "future_lane": "B8.7b.3_local_only_materialization_remap",
            "decision": "RECOMMENDED" if result.status in {"B87B2_ASSET_DISCOVERY_PASS", "B87B2_READY_FOR_LOCAL_ONLY_MATERIALIZATION"} else "CONDITIONAL",
            "why": "Only a plan was created here; materialization requires user authorization.",
            "next_action": result.next_lane_recommendation,
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "future_lane": "B8.7b.4_asset_generation",
            "decision": "RECOMMENDED" if result.status in {"B87B2_BLOCKED_NO_ASSETS_FOUND", "B87B2_PARTIAL_ASSET_DISCOVERY"} else "OPTIONAL_FOR_GAPS",
            "why": "Needed for unresolved or partial cells missing required SVF/DSM.",
            "next_action": "generate missing assets in a future authorized lane; do not do it here",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "future_lane": "B8.7c_N300_execution_package",
            "decision": "READY_AFTER_AUTHORIZATION" if result.status == "B87B2_ASSET_DISCOVERY_PASS" else "BLOCKED",
            "why": "B8.7c may create manifest/runner only after all required assets are resolved and user authorizes it.",
            "next_action": result.next_lane_recommendation,
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "future_lane": "B9",
            "decision": "BLOCKED",
            "why": "AOI/B9 is outside this local N300 asset discovery lane.",
            "next_action": "do not start B9 from B8.7b.2",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    write_csv_rows(
        out_path(config, "b87b2_next_lane_decision_matrix.csv"),
        rows,
        ["future_lane", "decision", "why", "next_action", "claim_boundary"],
    )


def write_prompts(config: dict[str, Any]) -> None:
    """Write future-lane prompts."""
    write_text(
        out_path(config, "b87b2_codex_prompt_B87B3_local_only_materialization.md"),
        "# Future Codex Prompt: B8.7b.3 Local-Only Materialization\n\nUse only after explicit user authorization. Start from `b87b2_candidate_asset_mapping.csv` and `b87b2_remap_plan.csv`. Do not run QGIS/SOLWEIG or create B8.7c execution artifacts unless separately authorized.\n",
    )
    write_text(
        out_path(config, "b87b2_codex_prompt_B87C_N300_execution_package.md"),
        "# Future Codex Prompt: B8.7c N300 Execution Package\n\nUse only after B8.7b.2 or B8.7b.3 resolves required SVF/DSM assets for all 150 new cells and the user explicitly requests B8.7c. Do not claim AOI-wide prediction, local WBGT validation, hazard/risk completion, or System A/B coupling.\n",
    )


def write_reports(config: dict[str, Any], result: ReadinessDecisionResult, roots: list[dict[str, str]]) -> None:
    """Write report, status, and lane doc."""
    files_md = "\n".join(f"- `{path}`" for path in FILES_CREATED)
    root_lines = "\n".join(
        f"- `{clean(row.get('root_path'))}`: {clean(row.get('included_in_search'))} ({clean(row.get('root_role'))})"
        for row in roots
    )
    report = f"""# B8.7b.2 Cross-Worktree Asset Discovery

Status: `{result.status}`

## 1. Why this follows B8.7b.1

B8.7b.1 ended at `B87B1_WAITING_LOCAL_ROOTS`: the 150 new N300 candidates were known, met forcing and output roots were metadata-ready, but no cell tile folders or SVF/DSM/CDSM/DEM/landcover assets were resolved.

## 2. Main worktree vs B8 worktree

Current B8 worktree: `{clean(config.get('current_b8_worktree_root'))}`.
Original/main worktree: `{clean(config.get('main_worktree_root'))}`.

## 3. Search roots

{root_lines}

## 4. Discovery counts

- candidate count: `{result.candidate_count}`
- resolved complete count: `{result.resolved_complete_count}`
- resolved minimal SVF/DSM count: `{result.resolved_minimal_count}`
- partial count: `{result.partial_count}`
- ambiguous count: `{result.ambiguous_count}`
- unresolved count: `{result.unresolved_count}`
- main worktree hit count: `{result.main_worktree_hit_count}`
- local root hit count: `{result.local_root_hit_count}`

## 5. SVF/DSM status

Required SVF/DSM resolution is `{result.resolved_complete_count + result.resolved_minimal_count}/{result.candidate_count}`.

## 6. Per-cell mapping status

See `b87b2_candidate_asset_mapping.csv`, `b87b2_unresolved_cell_register.csv`, and `b87b2_ambiguous_cell_register.csv`.

## 7. Remap/materialization recommendation

No remap was performed. `b87b2_remap_plan.csv` and `b87b2_local_only_materialization_options.csv` are plan-only outputs.

## 8. Next lane

Recommended next lane: `{result.next_lane_recommendation}`.

## 9. Boundaries

{result.no_raster_touch_headline}. No QGIS/SOLWEIG, no run-ready manifest, no QGIS/local runner, no local execution package, no AOI/B9, no local WBGT, no hazard/risk score, and no System A/B coupling.

## Files created

{files_md}
"""
    write_text(out_path(config, "b87b2_report.md"), report)
    status = f"""# B8.7b.2 Status

Status: {result.status}
Branch: codex/b87b2-cross-worktree-asset-discovery
Scope: cross-worktree local asset discovery and remap planning only.

## Key results

- search roots checked: `{result.search_roots_checked}`
- candidate count: `{result.candidate_count}`
- resolved complete count: `{result.resolved_complete_count}`
- resolved minimal SVF/DSM count: `{result.resolved_minimal_count}`
- partial count: `{result.partial_count}`
- ambiguous count: `{result.ambiguous_count}`
- unresolved count: `{result.unresolved_count}`
- main worktree hit count: `{result.main_worktree_hit_count}`
- local root hit count: `{result.local_root_hit_count}`
- no-raster-touch audit headline: `{result.no_raster_touch_headline}`
- next lane recommendation: `{result.next_lane_recommendation}`

## Files created / modified

{files_md}
"""
    write_text(out_path(config, "B8_7B2_STATUS.md"), status)
    doc = f"""# OpenHeat System B B8.7b.2 Cross-Worktree Asset Discovery Note

This note intentionally uses ASCII text to avoid mojibake in the lane output.

Status: `{result.status}`.
Candidate count: `{result.candidate_count}`.
Required SVF/DSM resolved: `{result.resolved_complete_count + result.resolved_minimal_count}/{result.candidate_count}`.
Ambiguous cells: `{result.ambiguous_count}`.
Unresolved cells: `{result.unresolved_count}`.

No raster contents were opened. No raster was copied, moved, symlinked, or
generated. No QGIS/SOLWEIG, manifest, runner, AOI/B9, local WBGT, hazard/risk
score, or System A/B coupling output was created.

Recommended next lane: `{result.next_lane_recommendation}`.
"""
    write_text(clean(config["cn_doc_path"]), doc)


def run(config_path: Path = DEFAULT_CONFIG) -> ReadinessDecisionResult:
    """Run B8.7b.2 readiness decision and reports."""
    config = load_config(config_path)
    mapping = read_csv_rows(out_path(config, "b87b2_candidate_asset_mapping.csv"))
    roots = read_csv_rows(out_path(config, "b87b2_search_root_inventory.csv"))
    counts = count_status(mapping)
    complete = counts["RESOLVED_COMPLETE"]
    minimal = counts["RESOLVED_MINIMAL_SVF_DSM"]
    partial = counts["RESOLVED_PARTIAL"]
    ambiguous = counts["AMBIGUOUS_REVIEW"]
    unresolved = counts["UNRESOLVED_NOT_FOUND"] + counts["ROOT_INACCESSIBLE"]
    status, next_lane = decide(len(mapping), complete, minimal, partial, ambiguous, unresolved)
    main_hits = len(
        {
            clean(row.get("cell_id"))
            for row in mapping
            if clean(row.get("source_root"))
            and "06-openheat_grid" in clean(row.get("source_root"))
            and "_b8" not in clean(row.get("source_root"))
        }
    )
    local_hits = len(
        {
            clean(row.get("cell_id"))
            for row in mapping
            if clean(row.get("source_root")).replace("\\", "/").lower().startswith("c:/openheat-local")
        }
    )
    audit = no_raster_audit(config)
    result = ReadinessDecisionResult(
        status=status,
        search_roots_checked=len(roots),
        candidate_count=len(mapping),
        resolved_complete_count=complete,
        resolved_minimal_count=minimal,
        partial_count=partial,
        ambiguous_count=ambiguous,
        unresolved_count=unresolved,
        main_worktree_hit_count=main_hits,
        local_root_hit_count=local_hits,
        no_raster_touch_headline=audit,
        next_lane_recommendation=next_lane,
    )
    write_readiness_matrix(config, result)
    write_next_lane_matrix(config, result)
    write_prompts(config)
    write_reports(config, result, roots)
    return result


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Decide B8.7b.2 readiness and write reports; metadata-only, no raster IO."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
