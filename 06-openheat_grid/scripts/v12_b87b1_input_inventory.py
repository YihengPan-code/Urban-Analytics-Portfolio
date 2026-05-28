"""Inventory B8.7b.1 local asset-remap readiness inputs and shared helpers.

Inputs:
    configs/v12/systemb_b87b1_local_asset_remap.yaml plus compact CSV,
    Markdown, and YAML artifacts declared there.
Outputs:
    outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_input_inventory.csv.
Saved metrics:
    Required input existence, file sizes, row/column counts, expected schema
    presence, manual local-root input metadata, and guardrail flags. This script
    reads compact text/tabular artifacts only. It never opens raster contents,
    never opens svfs.zip, never runs QGIS or SOLWEIG, and never creates a
    run-ready N300 manifest, QGIS runner, local runner, AOI/B9 output, local
    WBGT, hazard/risk score, Tmrt-to-WBGT conversion, or System A/B coupling.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "v12" / "systemb_b87b1_local_asset_remap.yaml"
OUTPUT_DIR_KEY = "output_dir"

CLAIM_BOUNDARY = (
    "B8.7b.1 local asset readiness only; not B9, not AOI-wide prediction, "
    "not local WBGT, not hazard_score or risk_score, not exposure/vulnerability "
    "score, not observed truth, not causal feature importance, no raster "
    "read/write/copy/open, no QGIS/SOLWEIG execution, no run-ready N300 "
    "manifest, no QGIS runner, no local runner, no Tmrt-to-WBGT conversion, "
    "and no System A/B coupling."
)

FORBIDDEN_RASTER_SUFFIXES = {".tif", ".tiff", ".vrt", ".asc", ".img", ".nc", ".grib"}
TEXT_SCAN_SUFFIXES = {".csv", ".md", ".yaml", ".yml", ".py", ".json", ".txt"}

REQUIRED_INPUT_KEYS = [
    "b87b_new_candidate_sample_index_path",
    "b87b_cell_asset_readiness_path",
    "b87b_local_path_remap_audit_path",
    "b87b_run_plan_preview_path",
    "b87b_pre_manifest_schema_preview_path",
    "b86g3_n300_v4_design_path",
    "f5_pairwise_label_path",
]

OPTIONAL_INPUT_KEYS = [
    "f5_status_path",
    "f5_pre_execution_asset_check_path",
    "f5_manifest_path",
    "f2b_root_candidate_inventory_path",
    "f2b_asset_remap_table_path",
    "f2d_root_inventory_path",
    "f2d_asset_status_path",
    "f2c_generated_met_forcing_manifest_path",
    "f2c_next_remap_roots_path",
]

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "b87b_new_candidate_sample_index_path": [
        "cell_id",
        "primary_role",
        "spatial_bin",
        "typology",
        "source_closeout_status",
    ],
    "b87b_cell_asset_readiness_path": [
        "cell_id",
        "svf_asset_status",
        "dsm_asset_status",
        "cdsm_asset_status",
        "dem_asset_status",
        "landcover_asset_status",
        "metforcing_asset_status",
        "qgis_template_status",
    ],
    "b87b_local_path_remap_audit_path": ["asset_key", "local_expected_path", "exists_by_metadata_check"],
    "b87b_run_plan_preview_path": ["run_id", "cell_id", "not_run_ready", "no_qgis_solweig_execution"],
    "b87b_pre_manifest_schema_preview_path": ["column_name", "precheck_only_not_execution_manifest"],
    "b86g3_n300_v4_design_path": ["cell_id", "primary_role", "spatial_bin", "typology", "source_closeout_status"],
    "f5_pairwise_label_path": ["cell_id", "forcing_day_id", "hour_sgt"],
    "f5_pre_execution_asset_check_path": ["cell_id", "met_forcing_ready", "qgis_manual_check_status"],
    "f5_manifest_path": ["cell_id", "expected_output_dir", "expected_tmrt_path", "input_asset_root"],
    "f2b_root_candidate_inventory_path": ["root_alias", "root_kind", "root_path_display"],
    "f2b_asset_remap_table_path": ["asset_type", "logical_name", "selected_path_exists"],
    "f2d_root_inventory_path": ["root_alias", "root_path", "exists", "status"],
    "f2d_asset_status_path": ["asset_type", "cell_id", "resolved_path", "exists", "asset_ready"],
    "f2c_generated_met_forcing_manifest_path": ["forcing_day_id", "local_output_path_display", "file_exists"],
}


@dataclass(frozen=True)
class InputInventoryResult:
    """B8.7b.1 input inventory result."""

    status: str
    inputs_checked: int
    missing_required_inputs: int
    schema_errors: int
    manual_local_root_input_found: bool


def clean(value: Any) -> str:
    """Return a compact single-line string."""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def parse_scalar(value: str) -> Any:
    """Parse the small YAML scalar subset used by the B8.7b.1 config."""
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


def load_config(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Load the explicit B8.7b.1 YAML config without external dependencies."""
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


def output_dir(config: dict[str, Any]) -> Path:
    """Create and return the compact B8.7b.1 output directory."""
    out_dir = repo_path(clean(config[OUTPUT_DIR_KEY]))
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def out_path(config: dict[str, Any], filename: str) -> Path:
    """Return a B8.7b.1 output path by filename."""
    return output_dir(config) / filename


def is_placeholder_path(path: str | Path) -> bool:
    """Return true for placeholder paths that must not be checked as files."""
    text = clean(path)
    return not text or "<" in text or ">" in text or "PLACEHOLDER" in text or "TO_BE_SELECTED" in text


def is_forbidden_raster_path(path: str | Path) -> bool:
    """Return true when the path has a forbidden raster-like suffix."""
    return Path(clean(path)).suffix.lower() in FORBIDDEN_RASTER_SUFFIXES


def path_exists_metadata(path: str | Path) -> tuple[str, str, str, str, str]:
    """Check existence, type, parent, and size metadata without reading contents."""
    if is_placeholder_path(path):
        return "unknown", "unknown", "unknown", "unknown", ""
    resolved = repo_path(path)
    try:
        exists = resolved.exists()
        is_dir = resolved.is_dir() if exists else False
        is_file = resolved.is_file() if exists else False
        parent_exists = resolved.parent.exists()
        size = resolved.stat().st_size if exists and is_file else ""
    except OSError:
        return "unknown", "unknown", "unknown", "unknown", ""
    return yes_no(exists), yes_no(is_dir), yes_no(is_file), yes_no(parent_exists), clean(size)


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


def git_output(args: list[str]) -> str:
    """Return stdout for a lightweight Git command."""
    completed = subprocess.run(args, cwd=PROJECT_ROOT, check=False, capture_output=True, text=True)
    return completed.stdout.strip()


def csv_shape(path: str | Path) -> tuple[str, str, list[str], str]:
    """Return row count, column count, columns, and read status for a compact CSV."""
    resolved = repo_path(path)
    try:
        rows = read_csv_rows(resolved)
    except Exception as exc:  # pragma: no cover - defensive diagnostics
        return "", "", [], f"READ_ERROR:{exc}"
    columns = list(rows[0].keys()) if rows else read_csv_header(resolved)
    return clean(len(rows)), clean(len(columns)), columns, "READ_OK"


def file_inventory_row(config: dict[str, Any], key: str, required: bool) -> dict[str, Any]:
    """Build one input inventory row."""
    raw_path = clean(config.get(key, ""))
    exists, _, _, _, size = path_exists_metadata(raw_path)
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
        elif suffix in {".md", ".yaml", ".yml", ".json", ".txt"}:
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
        "read_scope": "compact_text_table_only",
        "notes": notes,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def run(config_path: Path = DEFAULT_CONFIG) -> InputInventoryResult:
    """Run the B8.7b.1 input inventory."""
    config = load_config(config_path)
    rows: list[dict[str, Any]] = []
    for key in REQUIRED_INPUT_KEYS:
        rows.append(file_inventory_row(config, key, required=True))
    for key in OPTIONAL_INPUT_KEYS:
        if clean(config.get(key)):
            rows.append(file_inventory_row(config, key, required=False))

    manual_path = clean(config.get("manual_local_root_input_path"))
    manual_exists, _, _, _, manual_size = path_exists_metadata(manual_path)
    rows.append(
        {
            "input_key": "manual_local_root_input_path",
            "path": manual_path,
            "exists_by_metadata_check": manual_exists,
            "size_bytes": manual_size,
            "row_count": "",
            "column_count": "",
            "required": "no",
            "required_columns_present": "not_applicable",
            "status": "PASS" if manual_exists == "yes" else "WARN",
            "read_scope": "optional_manual_csv_metadata_only",
            "notes": "missing is allowed; template and instructions will be generated",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    )

    for key in [
        "no_raster_io",
        "metadata_only",
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
    write_csv_rows(out_path(config, "b87b1_input_inventory.csv"), rows, fieldnames)
    missing_required = sum(1 for row in rows if row["required"] == "yes" and row["exists_by_metadata_check"] == "no")
    schema_errors = sum(1 for row in rows if row["required_columns_present"] == "no")
    guard_errors = sum(1 for row in rows if row["read_scope"] == "config_guardrail" and row["status"] != "PASS")
    status = "PASS" if missing_required == 0 and schema_errors == 0 and guard_errors == 0 else "FAIL"
    return InputInventoryResult(
        status=status,
        inputs_checked=len(rows),
        missing_required_inputs=missing_required,
        schema_errors=schema_errors + guard_errors,
        manual_local_root_input_found=manual_exists == "yes",
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Inventory B8.7b.1 compact inputs and guardrails. Writes metadata CSV "
            "only; does not touch rasters, QGIS/SOLWEIG, manifests, or runners."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
