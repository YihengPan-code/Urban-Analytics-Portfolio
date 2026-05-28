"""Inventory B8.7b N300 execution-precheck inputs and shared helpers.

Inputs:
    configs/v12/systemb_b87b_n300_execution_precheck.yaml and compact CSV,
    Markdown, and YAML inputs declared there.
Outputs:
    outputs/v12_surrogate/b8_7b_n300_execution_precheck/b87b_input_inventory.csv.
Saved metrics:
    Required input existence, file sizes, row/column counts, schema presence
    where expected, local run-log metadata, and guardrail flags. This script
    reads compact text/tabular artifacts only. It does not read raster contents,
    open svfs.zip, run QGIS or SOLWEIG, create a run-ready manifest, create a
    QGIS/local runner, create AOI/B9 outputs, compute local WBGT, hazard_score,
    risk_score, exposure/vulnerability score, observed-truth evidence, causal
    feature importance, Tmrt-to-WBGT conversion, or System A/B coupling.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "v12" / "systemb_b87b_n300_execution_precheck.yaml"
OUTPUT_DIR_KEY = "output_dir"

CLAIM_BOUNDARY = (
    "B8.7b N300 execution precheck only; not B9, not AOI-wide prediction, "
    "not local WBGT, not hazard_score or risk_score, not exposure/vulnerability "
    "score, not observed truth, not causal feature importance, no raster "
    "read/write/copy, no QGIS/SOLWEIG execution, no run-ready N300 manifest, "
    "no QGIS/local runner, no Tmrt-to-WBGT conversion, and no System A/B coupling."
)

FORBIDDEN_EXTENSIONS = {".tif", ".tiff", ".vrt", ".asc", ".img", ".nc", ".grib"}
FORBIDDEN_COMMIT_TOKENS = {
    ".tif",
    ".tiff",
    ".vrt",
    ".asc",
    ".img",
    ".nc",
    ".grib",
    "svfs.zip",
    "data/solweig/",
    "data/rasters/",
    "data/archive/",
    "data/raw/buildings_v10/",
    "hourly_grid_heatstress_forecast",
}

REQUIRED_INPUT_KEYS = [
    "b86g3_n300_v4_design_path",
    "b86g3_execution_precheck_matrix_path",
    "b86g3_closeout_path",
    "b86g3_aoi_b9_blocker_path",
    "b86g3_true_vector_source_readiness_path",
    "b86g_n300_feature_dataset_path",
    "b86g_feature_schema_path",
    "n150_feature_matrix_path",
    "n150_selected_cells_path",
    "f5_pairwise_label_path",
]

OPTIONAL_INPUT_KEYS = [
    "f5_manifest_path",
    "f5_pre_execution_asset_check_path",
    "f5_postrun_validation_path",
    "f5_expected_run_log_schema_path",
    "f5_status_path",
    "f2b_asset_remap_table_path",
    "f2b_root_candidate_inventory_path",
    "f2b_run_readiness_after_remap_path",
    "f2d_asset_status_path",
    "f2d_root_inventory_path",
    "b87a_patched_design_path",
    "b87a_diff_path",
    "b87a_freeze_readiness_path",
    "b87_design_freeze_candidates_path",
]

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "b86g3_n300_v4_design_path": [
        "cell_id",
        "primary_role",
        "spatial_bin",
        "typology",
        "source_closeout_status",
        "source_closeout_caveat",
        "execution_precheck_blocker",
        "claim_boundary",
    ],
    "b86g3_execution_precheck_matrix_path": ["readiness_item", "status", "evidence"],
    "b86g3_closeout_path": [
        "source_review_cell",
        "source_closeout_status",
        "execution_precheck_blocker",
        "caveat_text",
    ],
    "b86g3_aoi_b9_blocker_path": ["blocker_item", "status", "evidence"],
    "b86g3_true_vector_source_readiness_path": ["source_category", "status", "validity_verdict"],
    "b86g_n300_feature_dataset_path": ["cell_id", "feature_version"],
    "b86g_feature_schema_path": ["feature_name", "feature_family", "source_type"],
    "n150_feature_matrix_path": ["cell_id"],
    "n150_selected_cells_path": ["cell_id", "selection_status", "typology_label"],
    "f5_pairwise_label_path": ["cell_id", "forcing_day_id", "hour_sgt"],
    "f5_manifest_path": ["run_id", "cell_id", "forcing_day_id", "hour_sgt", "scenario"],
    "f5_pre_execution_asset_check_path": ["run_id", "cell_id", "run_ready", "pre_execution_status"],
    "f5_postrun_validation_path": ["run_id", "cell_id", "file_size_bytes", "validation_status"],
    "f2b_asset_remap_table_path": ["asset_type", "logical_name", "selected_path_exists"],
    "f2d_asset_status_path": ["asset_type", "logical_name", "exists", "asset_ready"],
}


@dataclass(frozen=True)
class InputInventoryResult:
    """B8.7b input inventory result."""

    status: str
    inputs_checked: int
    missing_required_inputs: int
    schema_errors: int
    local_run_logs_found: int


def clean(value: Any) -> str:
    """Return a compact single-line string."""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def parse_scalar(value: str) -> Any:
    """Parse the tiny YAML scalar subset used in the B8.7b config."""
    stripped = value.strip()
    if stripped == "":
        return ""
    lowered = stripped.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none", "~"}:
        return None
    try:
        return int(stripped)
    except ValueError:
        return stripped.strip("\"'")


def load_config(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Load the explicit B8.7b YAML config without external dependencies."""
    resolved = repo_path(config_path)
    config: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in resolved.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                config[key] = parse_scalar(value)
                current_key = None
            else:
                config[key] = []
                current_key = key
            continue
        if current_key and stripped.startswith("- "):
            config[current_key].append(parse_scalar(stripped[2:]))
    if not config:
        raise ValueError(f"Config did not parse as a mapping: {resolved}")
    return config


def config_list(config: dict[str, Any], key: str) -> list[str]:
    """Return a config item as a string list."""
    value = config.get(key, [])
    if isinstance(value, list):
        return [clean(item) for item in value]
    if value in {None, ""}:
        return []
    return [part.strip() for part in clean(value).split("|") if part.strip()]


def repo_path(path: str | Path) -> Path:
    """Resolve a path relative to the OpenHeat project subdirectory."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def rel_path(path: str | Path) -> str:
    """Return a stable project-relative POSIX path when possible."""
    resolved = repo_path(path)
    try:
        return resolved.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def output_dir(config: dict[str, Any]) -> Path:
    """Create and return the B8.7b compact output directory."""
    out_dir = repo_path(clean(config[OUTPUT_DIR_KEY]))
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def out_path(config: dict[str, Any], filename: str) -> Path:
    """Return a B8.7b output path by filename."""
    return output_dir(config) / filename


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV into dictionaries."""
    with repo_path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def read_csv_header(path: str | Path) -> list[str]:
    """Read only a CSV header."""
    with repo_path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        return next(reader, [])


def write_csv_rows(path: str | Path, rows: Iterable[dict[str, Any]], fieldnames: Sequence[str]) -> None:
    """Write a UTF-8 CSV artifact."""
    resolved = repo_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: clean(row.get(field, "")) for field in fieldnames})


def write_text(path: str | Path, text: str) -> None:
    """Write a UTF-8 text artifact."""
    resolved = repo_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(text, encoding="utf-8")


def yes_no(value: bool) -> str:
    """Format a boolean as yes/no."""
    return "yes" if value else "no"


def status_rank(statuses: Iterable[str]) -> str:
    """Return the most severe status from a collection."""
    order = ["FAIL", "BLOCKED", "UNKNOWN_LOCAL_AUDIT_REQUIRED", "WARN", "PASS"]
    status_set = {clean(status) for status in statuses}
    for status in order:
        if status in status_set:
            return status
    return "PASS"


def git_output(args: list[str]) -> str:
    """Return stdout for a lightweight Git command."""
    completed = subprocess.run(args, cwd=PROJECT_ROOT, check=False, capture_output=True, text=True)
    return completed.stdout.strip()


def path_exists_metadata(path: str | Path) -> tuple[str, str]:
    """Check path existence and size metadata without reading file contents."""
    if not clean(path):
        return "unknown", ""
    resolved = repo_path(path)
    try:
        exists = resolved.exists()
        size = resolved.stat().st_size if exists and resolved.is_file() else ""
    except OSError:
        return "unknown", ""
    return yes_no(exists), clean(size)


def csv_shape(path: str | Path) -> tuple[str, str, list[str], str]:
    """Return row count, column count, columns, and read status for a compact CSV."""
    resolved = repo_path(path)
    try:
        rows = read_csv_rows(resolved)
    except Exception as exc:  # pragma: no cover - defensive diagnostics
        return "", "", [], f"READ_ERROR:{exc}"
    columns = list(rows[0].keys()) if rows else read_csv_header(resolved)
    return clean(len(rows)), clean(len(columns)), columns, "READ_OK"


def file_inventory_row(
    config: dict[str, Any],
    key: str,
    required: bool,
    local_audit_only: bool = False,
) -> dict[str, Any]:
    """Build one input inventory row."""
    raw_path = clean(config.get(key, ""))
    exists, size = path_exists_metadata(raw_path)
    row_count = ""
    column_count = ""
    required_columns_present = "not_applicable"
    status = "PASS"
    notes = "compact metadata/text input"
    if required and exists != "yes":
        status = "FAIL"
        notes = "required input missing"
    elif exists == "yes":
        suffix = repo_path(raw_path).suffix.lower()
        if suffix == ".csv":
            row_count, column_count, columns, read_status = csv_shape(raw_path)
            expected_columns = REQUIRED_COLUMNS.get(key, [])
            if expected_columns:
                missing = [column for column in expected_columns if column not in columns]
                required_columns_present = "yes" if not missing else "no"
                if missing:
                    status = "FAIL" if required else "WARN"
                    notes = f"missing columns: {'|'.join(missing)}"
            else:
                required_columns_present = "not_declared"
            if read_status != "READ_OK":
                status = "FAIL" if required else "WARN"
                notes = read_status
        elif suffix in {".md", ".yaml", ".yml", ".json"}:
            try:
                text = repo_path(raw_path).read_text(encoding="utf-8-sig")
                row_count = clean(len(text.splitlines()))
                column_count = "not_applicable"
            except Exception as exc:  # pragma: no cover
                status = "FAIL" if required else "WARN"
                notes = f"READ_ERROR:{exc}"
    return {
        "input_key": key,
        "path": raw_path,
        "exists_by_metadata_check": exists,
        "size_bytes": size,
        "row_count": row_count,
        "column_count": column_count,
        "required": yes_no(required),
        "required_columns_present": required_columns_present,
        "status": status,
        "read_scope": "local_audit_only" if local_audit_only else "compact_text_table_only",
        "notes": notes,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def run(config_path: Path = DEFAULT_CONFIG) -> InputInventoryResult:
    """Run the B8.7b input inventory."""
    config = load_config(config_path)
    rows: list[dict[str, Any]] = []
    for key in REQUIRED_INPUT_KEYS:
        rows.append(file_inventory_row(config, key, required=True))
    for key in OPTIONAL_INPUT_KEYS:
        if clean(config.get(key, "")):
            rows.append(file_inventory_row(config, key, required=False))
    local_found = 0
    for index, log_path in enumerate(config_list(config, "local_run_log_candidates"), start=1):
        exists, size = path_exists_metadata(log_path)
        local_found += 1 if exists == "yes" else 0
        rows.append(
            {
                "input_key": f"local_run_log_candidate_{index}",
                "path": log_path,
                "exists_by_metadata_check": exists,
                "size_bytes": size,
                "row_count": "",
                "column_count": "",
                "required": "no",
                "required_columns_present": "not_applicable",
                "status": "PASS" if exists == "yes" else "WARN",
                "read_scope": "local_audit_only",
                "notes": "metadata check only unless runtime estimator reads compact CSV log",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    for key in [
        "no_raster_io",
        "no_qgis_solweig",
        "no_run_ready_manifest",
        "no_qgis_runner",
        "no_aoi_prediction",
        "no_b9",
    ]:
        rows.append(
            {
                "input_key": f"guardrail_{key}",
                "path": "",
                "exists_by_metadata_check": "not_applicable",
                "size_bytes": "",
                "row_count": "",
                "column_count": "",
                "required": "yes",
                "required_columns_present": "not_applicable",
                "status": "PASS" if config.get(key) is True else "FAIL",
                "read_scope": "config_guardrail",
                "notes": f"{key}={config.get(key)}",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    fieldnames = [
        "input_key",
        "path",
        "exists_by_metadata_check",
        "size_bytes",
        "row_count",
        "column_count",
        "required",
        "required_columns_present",
        "status",
        "read_scope",
        "notes",
        "claim_boundary",
    ]
    write_csv_rows(out_path(config, "b87b_input_inventory.csv"), rows, fieldnames)
    missing_required = sum(1 for row in rows if row["required"] == "yes" and row["exists_by_metadata_check"] == "no")
    schema_errors = sum(1 for row in rows if row["required_columns_present"] == "no")
    status = "PASS" if missing_required == 0 and schema_errors == 0 else "FAIL"
    return InputInventoryResult(
        status=status,
        inputs_checked=len(rows),
        missing_required_inputs=missing_required,
        schema_errors=schema_errors,
        local_run_logs_found=local_found,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Inventory B8.7b N300 execution-precheck compact inputs. Writes "
            "CSV metadata only; no raster/QGIS/SOLWEIG/run-ready manifest/local "
            "runner/AOI/B9/WBGT/hazard/risk output is created."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
