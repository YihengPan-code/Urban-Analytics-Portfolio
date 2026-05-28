"""Create non-executable B8.7b pre-manifest and run-plan previews.

Inputs:
    configs/v12/systemb_b87b_n300_execution_precheck.yaml, B8.6g3 N300 v4
    design, and B8.5-F5 forcing metadata.
Outputs:
    b87b_pre_manifest_schema_preview.csv, b87b_run_plan_preview.csv,
    b87b_batch_grouping_plan.csv, b87b_resume_failure_strategy.csv,
    b87b_local_execution_boundary_checklist.csv, and
    b87b_qgis_console_safety_notes.md.
Saved metrics:
    Future manifest schema columns, 3000 non-executable preview rows, batch
    group recommendations, resume/failure-handling strategy, and local-only
    execution boundary checks. No run-ready manifest, QGIS runner, local runner,
    QGIS/SOLWEIG execution, raster IO, AOI/B9 output, WBGT, hazard/risk score,
    or System A/B coupling is created.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from v12_b87b_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, clean
from v12_b87b_input_inventory import config_list, load_config, out_path, path_exists_metadata
from v12_b87b_input_inventory import read_csv_rows, write_csv_rows, write_text


@dataclass(frozen=True)
class RunPlanPreviewResult:
    """B8.7b run-plan preview result."""

    status: str
    preview_run_rows: int
    batch_plan_rows: int
    headline: str


SCHEMA_COLUMNS = [
    ("run_id", "string", "yes", "Future unique run key; preview only in B8.7b."),
    ("cell_id", "string", "yes", "TP_#### cell ID."),
    ("forcing_day_id", "string", "yes", "F5 forcing day key."),
    ("date", "date", "yes", "YYYY-MM-DD in Singapore local time."),
    ("hour_sgt", "integer", "yes", "10|12|13|15|16 unless future reviewed design differs."),
    ("scenario", "string", "yes", "base|overhead_as_canopy."),
    ("expected_output_dir", "string", "yes", "Future local-only path placeholder; not executable in B8.7b."),
    ("expected_tmrt_path", "string", "yes", "Future local-only Tmrt path placeholder; no raster created/read."),
    ("asset_status", "string", "yes", "Asset readiness status from future local remap."),
    ("run_status", "string", "yes", "planned|blocked|success|failed in future B8.7c only."),
    ("notes", "string", "no", "Free-text notes."),
    ("precheck_only_not_execution_manifest", "boolean", "yes", "Must be true for B8.7b preview rows."),
    ("not_run_ready", "boolean", "yes", "Must be true for B8.7b preview rows."),
    ("no_qgis_solweig_execution", "boolean", "yes", "Must be true for B8.7b preview rows."),
]


def forcing_combos(config: dict[str, Any]) -> list[dict[str, str]]:
    """Return forcing-day/hour/scenario combinations from F5 metadata."""
    manifest_exists, _ = path_exists_metadata(config.get("f5_manifest_path", ""))
    if manifest_exists == "yes":
        rows = read_csv_rows(config["f5_manifest_path"])
        combos = {
            (
                clean(row.get("forcing_day_id")),
                clean(row.get("date")),
                clean(row.get("hour_sgt")),
                clean(row.get("scenario")),
            )
            for row in rows
            if clean(row.get("forcing_day_id")) and clean(row.get("hour_sgt")) and clean(row.get("scenario"))
        }
    else:
        pairwise = read_csv_rows(config["f5_pairwise_label_path"])
        days = sorted({clean(row.get("forcing_day_id")) for row in pairwise if clean(row.get("forcing_day_id"))})
        hours = sorted({clean(row.get("hour_sgt")) for row in pairwise if clean(row.get("hour_sgt"))}, key=lambda x: int(x))
        combos = {(day, "", hour, scenario) for day in days for hour in hours for scenario in config_list(config, "expected_scenarios")}
    return [
        {"forcing_day_id": day, "date": date, "hour_sgt": hour, "scenario": scenario}
        for day, date, hour, scenario in sorted(combos, key=lambda item: (item[0], int(item[2]), item[3]))
    ]


def run(config_path: Path = DEFAULT_CONFIG) -> RunPlanPreviewResult:
    """Create non-executable run-plan preview outputs."""
    config = load_config(config_path)
    design = read_csv_rows(config["b86g3_n300_v4_design_path"])
    combos = forcing_combos(config)

    schema_rows = [
        {
            "column_name": name,
            "dtype": dtype,
            "required": required,
            "description": description,
            "precheck_only_not_execution_manifest": "true",
            "not_run_ready": "true",
            "no_qgis_solweig_execution": "true",
            "claim_boundary": CLAIM_BOUNDARY,
        }
        for name, dtype, required, description in SCHEMA_COLUMNS
    ]
    write_csv_rows(
        out_path(config, "b87b_pre_manifest_schema_preview.csv"),
        schema_rows,
        [
            "column_name",
            "dtype",
            "required",
            "description",
            "precheck_only_not_execution_manifest",
            "not_run_ready",
            "no_qgis_solweig_execution",
            "claim_boundary",
        ],
    )

    preview_rows: list[dict[str, Any]] = []
    for item in design:
        cell_id = clean(item.get("cell_id"))
        for combo in combos:
            hour = clean(combo["hour_sgt"])
            scenario = clean(combo["scenario"])
            forcing_day = clean(combo["forcing_day_id"])
            output_group = f"LOCAL_ONLY_PLACEHOLDER/b87c_n300/{forcing_day}/{cell_id}/{scenario}/h{hour}"
            preview_rows.append(
                {
                    "run_id": f"PREVIEW_ONLY_B87C_{forcing_day}_{cell_id}_{scenario}_h{hour}",
                    "cell_id": cell_id,
                    "forcing_day_id": forcing_day,
                    "date": clean(combo["date"]),
                    "hour_sgt": hour,
                    "scenario": scenario,
                    "expected_output_dir": output_group,
                    "expected_tmrt_path": f"{output_group}/Tmrt_average.tif",
                    "asset_status": "UNKNOWN_LOCAL_AUDIT_REQUIRED",
                    "run_status": "NOT_RUN_READY_PRECHECK_ONLY",
                    "notes": "Schema/row planning preview only; not an executable manifest.",
                    "precheck_only_not_execution_manifest": "true",
                    "not_run_ready": "true",
                    "no_qgis_solweig_execution": "true",
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
    write_csv_rows(
        out_path(config, "b87b_run_plan_preview.csv"),
        preview_rows,
        [
            "run_id",
            "cell_id",
            "forcing_day_id",
            "date",
            "hour_sgt",
            "scenario",
            "expected_output_dir",
            "expected_tmrt_path",
            "asset_status",
            "run_status",
            "notes",
            "precheck_only_not_execution_manifest",
            "not_run_ready",
            "no_qgis_solweig_execution",
            "claim_boundary",
        ],
    )

    batch_rows = [
        {
            "batch_id": "smoke_batch",
            "recommended_cell_count": "1-3",
            "expected_run_count_range": f"{len(combos)}-{len(combos) * 3}",
            "chunk_size_recommendation": "smallest end-to-end smoke only",
            "role_spatial_typology_distribution": "include at least one caveat or edge-case cell if authorized",
            "resume_strategy": "future B8.7c runner should log each row and skip prior success only with output present",
            "failure_isolation_strategy": "stop immediately on schema/path/QGIS initialization failure",
            "status": "PREVIEW_ONLY_NOT_AUTHORIZED_FOR_EXECUTION",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "batch_id": "pilot_batch",
            "recommended_cell_count": "10-20",
            "expected_run_count_range": f"{len(combos) * 10}-{len(combos) * 20}",
            "chunk_size_recommendation": "pilot after smoke passes",
            "role_spatial_typology_distribution": "cover primary roles and spatial bins",
            "resume_strategy": "resume by run_id and expected output metadata only",
            "failure_isolation_strategy": "isolate failures by cell/forcing_day/hour/scenario",
            "status": "PREVIEW_ONLY_NOT_AUTHORIZED_FOR_EXECUTION",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "batch_id": "production_chunk",
            "recommended_cell_count": "25-50",
            "expected_run_count_range": f"{len(combos) * 25}-{len(combos) * 50}",
            "chunk_size_recommendation": "repeatable production chunks",
            "role_spatial_typology_distribution": "preserve balanced candidate ordering where possible",
            "resume_strategy": "append-only local log with flush per row",
            "failure_isolation_strategy": "continue only after failure threshold and blocker class are reviewed",
            "status": "PREVIEW_ONLY_NOT_AUTHORIZED_FOR_EXECUTION",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "batch_id": "full_new_n150",
            "recommended_cell_count": "150",
            "expected_run_count_range": str(len(preview_rows)),
            "chunk_size_recommendation": "full new candidate set after smoke/pilot/chunks pass",
            "role_spatial_typology_distribution": "all B8.6g3 v4 candidate roles",
            "resume_strategy": "full resume audit before postrun QA",
            "failure_isolation_strategy": "do not promote labels until postrun QA passes",
            "status": "PREVIEW_ONLY_NOT_AUTHORIZED_FOR_EXECUTION",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    write_csv_rows(
        out_path(config, "b87b_batch_grouping_plan.csv"),
        batch_rows,
        [
            "batch_id",
            "recommended_cell_count",
            "expected_run_count_range",
            "chunk_size_recommendation",
            "role_spatial_typology_distribution",
            "resume_strategy",
            "failure_isolation_strategy",
            "status",
            "claim_boundary",
        ],
    )

    strategy_rows = [
        ("run_log_schema", "Future B8.7c should reuse F5 started_at/completed_at/duration/status/error fields.", "PREVIEW_ONLY"),
        ("resume", "Skip a row only when prior success log and expected output metadata both agree.", "PREVIEW_ONLY"),
        ("failure_threshold", "Stop on repeated setup failures; isolate per cell/day/hour/scenario failures.", "PREVIEW_ONLY"),
        ("postrun_gate", "Postrun validation and raster QA belong to a future postrun lane, not B8.7b.", "PREVIEW_ONLY"),
        ("claim_boundary", "Do not convert Tmrt to WBGT or create hazard/risk/AOI/B9 outputs.", "PASS"),
    ]
    write_csv_rows(
        out_path(config, "b87b_resume_failure_strategy.csv"),
        [
            {
                "strategy_item": item,
                "recommendation": recommendation,
                "status": status,
                "claim_boundary": CLAIM_BOUNDARY,
            }
            for item, recommendation, status in strategy_rows
        ],
        ["strategy_item", "recommendation", "status", "claim_boundary"],
    )

    boundary_rows = [
        ("no_run_ready_manifest", "PASS", "B8.7b writes schema/preview only, with not_run_ready=true."),
        ("no_qgis_runner", "PASS", "No scripts/qgis or local runner file is created."),
        ("no_qgis_solweig_execution", "PASS", "No QGIS/SOLWEIG command or processing.run call is executed."),
        ("local_only_future_execution", "WARN", "Future B8.7c needs explicit user authorization before local execution package."),
        ("no_raster_io", "PASS", "B8.7b uses compact CSV/MD and Path.exists/stat metadata only."),
        ("no_aoi_b9", "PASS", "AOI_PREFLIGHT_BLOCKED and B9_BLOCKED remain in decision outputs."),
    ]
    write_csv_rows(
        out_path(config, "b87b_local_execution_boundary_checklist.csv"),
        [
            {
                "check_item": item,
                "status": status,
                "evidence": evidence,
                "action_required": "carry into B8.7c prompt" if status == "WARN" else "none",
                "claim_boundary": CLAIM_BOUNDARY,
            }
            for item, status, evidence in boundary_rows
        ],
        ["check_item", "status", "evidence", "action_required", "claim_boundary"],
    )

    safety_notes = """# B8.7b QGIS Console Safety Notes

These notes are for a future B8.7c execution package only. B8.7b does not create a runner and does not authorize QGIS or SOLWEIG execution.

- Read any future local runner with `encoding="utf-8-sig"` to avoid BOM-related console failures.
- Inject an explicit `__file__` for the future local-only runner path.
- Set `sys.argv` to the future local-only runner path before execution.
- Set `cwd` to the future runner parent directory.
- Keep any future real execution outside the Git worktree and under a local-only output root.
- Keep repo-side runners dry-run or absent unless a future lane explicitly authorizes otherwise.
- Do not copy, open, or commit rasters or `svfs.zip`.
"""
    write_text(out_path(config, "b87b_qgis_console_safety_notes.md"), safety_notes)

    status = "PASS" if len(preview_rows) == int(config["planned_additional_solweig_run_count"]) else "WARN"
    headline = f"{len(preview_rows)} non-executable preview rows; no manifest/runner created."
    return RunPlanPreviewResult(status=status, preview_run_rows=len(preview_rows), batch_plan_rows=len(batch_rows), headline=headline)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Create B8.7b pre-manifest schema and run-plan previews only. "
            "The row-level preview is explicitly not run-ready."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
