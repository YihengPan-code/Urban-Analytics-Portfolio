"""Inventory B8.7b.2 cross-worktree asset discovery inputs and helpers.

Inputs:
    configs/v12/systemb_b87b2_cross_worktree_asset_discovery.yaml and the
    compact B8.7b.1, B8.7b, and B8.6g3 CSV inputs declared there.
Outputs:
    outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/
    b87b2_input_inventory.csv.
Saved metrics:
    Required input existence, row and column counts, 150-candidate count,
    configured search roots, and guardrail status. This module reads compact
    text/tabular metadata only. It never opens raster contents, never uses
    rasterio/GDAL, never runs QGIS/SOLWEIG, never copies/moves/symlinks assets,
    and never creates a run-ready manifest, runner, AOI/B9 output, local WBGT,
    hazard/risk score, or System A/B coupling.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "v12" / "systemb_b87b2_cross_worktree_asset_discovery.yaml"

CLAIM_BOUNDARY = (
    "B8.7b.2 metadata-only cross-worktree local asset discovery and remap "
    "planning; no raster read/write/copy/open, no rasterio/GDAL, no "
    "QGIS/SOLWEIG, no run-ready N300 manifest, no QGIS/local runner, no local "
    "execution package, no AOI/B9 output, no local WBGT, no hazard/risk score, "
    "no Tmrt-to-WBGT conversion, and no System A/B coupling."
)

FORBIDDEN_RASTER_SUFFIXES = {".tif", ".tiff", ".vrt", ".asc", ".img", ".nc", ".grib"}
TEXT_SCAN_SUFFIXES = {".csv", ".md", ".yaml", ".yml", ".py", ".json", ".txt"}

REQUIRED_INPUT_KEYS = [
    "b87b1_expected_paths_path",
    "b87b1_readiness_path",
    "b87b_new_candidate_sample_index_path",
    "b86g3_n300_v4_design_path",
]

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "b87b1_expected_paths_path": ["cell_id", "cell_tile_folder_candidate"],
    "b87b1_readiness_path": ["cell_id", "readiness_status"],
    "b87b_new_candidate_sample_index_path": ["cell_id", "primary_role", "spatial_bin", "typology"],
    "b86g3_n300_v4_design_path": ["cell_id", "primary_role", "spatial_bin", "typology"],
}

GUARDRAIL_KEYS = [
    "metadata_only",
    "no_raster_io",
    "no_qgis_solweig",
    "no_copy_move_symlink",
    "no_run_ready_manifest",
    "no_qgis_runner",
    "no_aoi_prediction",
    "no_b9",
]


@dataclass(frozen=True)
class InputInventoryResult:
    """B8.7b.2 input inventory result."""

    status: str
    inputs_checked: int
    missing_required_inputs: int
    schema_errors: int
    candidate_count: int
    search_root_count: int


def clean(value: Any) -> str:
    """Return a compact single-line string."""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def parse_scalar(value: str) -> Any:
    """Parse the small YAML scalar subset used by this config."""
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
    """Resolve a path relative to the OpenHeat B8 project subdirectory."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def rel_path(path: str | Path) -> str:
    """Return a project-relative POSIX path when possible."""
    resolved = repo_path(path)
    try:
        return resolved.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def load_config(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Load the explicit B8.7b.2 YAML config without external dependencies."""
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
    """Return a config item as a list of strings."""
    value = config.get(key, [])
    if isinstance(value, list):
        return [clean(item) for item in value]
    if value in {None, ""}:
        return []
    return [part.strip() for part in clean(value).split("|") if part.strip()]


def output_dir(config: dict[str, Any]) -> Path:
    """Create and return the compact B8.7b.2 output directory."""
    out_dir = repo_path(clean(config["output_dir"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def out_path(config: dict[str, Any], filename: str) -> Path:
    """Return a B8.7b.2 output path by filename."""
    return output_dir(config) / filename


def yes_no(value: bool) -> str:
    """Format a boolean as yes/no."""
    return "yes" if value else "no"


def bool_text(value: bool) -> str:
    """Format a boolean as lowercase true/false."""
    return "true" if value else "false"


def path_exists_metadata(path: str | Path) -> tuple[str, str, str, str, str]:
    """Check path existence/type/size metadata without reading contents."""
    if not clean(path):
        return "no", "no", "no", "no", ""
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


def git_output(args: list[str]) -> str:
    """Return stdout for a lightweight Git command."""
    completed = subprocess.run(args, cwd=PROJECT_ROOT, check=False, capture_output=True, text=True)
    return completed.stdout.strip()


def effective_search_roots(config: dict[str, Any]) -> list[str]:
    """Return current B8 worktree plus configured roots, de-duplicated by text."""
    roots = [clean(config.get("current_b8_worktree_root"))] + config_list(config, "search_roots")
    seen: set[str] = set()
    unique: list[str] = []
    for root in roots:
        key = root.rstrip("/\\").lower()
        if root and key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def source_roots(config: dict[str, Any]) -> list[str]:
    """Compatibility alias for the ordered B8.7b.2 search roots."""
    roots = [
        clean(config.get("current_b8_worktree_root")),
        clean(config.get("main_worktree_root")),
        clean(config.get("local_root")),
        *config_list(config, "search_roots"),
    ]
    seen: set[str] = set()
    unique: list[str] = []
    for root in roots:
        normalized = root.replace("\\", "/").rstrip("/")
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            unique.append(normalized)
    return unique


def root_role(config: dict[str, Any], path: str | Path) -> str:
    """Classify a search path as current B8, main worktree, or local root."""
    text = str(Path(path)).replace("\\", "/").rstrip("/").lower()
    current = clean(config.get("current_b8_worktree_root")).replace("\\", "/").rstrip("/").lower()
    main = clean(config.get("main_worktree_root")).replace("\\", "/").rstrip("/").lower()
    local = clean(config.get("local_root")).replace("\\", "/").rstrip("/").lower()
    if text == current or text.startswith(current + "/"):
        return "current_b8_worktree"
    if text == main or text.startswith(main + "/"):
        return "main_worktree"
    if text == local or text.startswith(local + "/"):
        return "local_root"
    return "other"


def csv_shape(path: str | Path) -> tuple[str, str, list[str], str]:
    """Return row count, column count, columns, and read status for a compact CSV."""
    try:
        rows = read_csv_rows(path)
    except Exception as exc:  # pragma: no cover - defensive diagnostics
        return "", "", [], f"READ_ERROR:{exc}"
    columns = list(rows[0].keys()) if rows else read_csv_header(path)
    return clean(len(rows)), clean(len(columns)), columns, "READ_OK"


def input_row(config: dict[str, Any], key: str) -> dict[str, Any]:
    """Build one input inventory row."""
    raw_path = clean(config.get(key, ""))
    exists, _, _, _, size = path_exists_metadata(raw_path)
    row_count = ""
    column_count = ""
    required_columns_present = "not_applicable"
    status = "PASS"
    notes = "compact metadata/text input"
    if exists != "yes":
        status = "FAIL"
        notes = "required input missing"
    elif repo_path(raw_path).suffix.lower() == ".csv":
        row_count, column_count, columns, read_status = csv_shape(raw_path)
        missing = [column for column in REQUIRED_COLUMNS.get(key, []) if column not in columns]
        required_columns_present = "yes" if not missing else "no"
        if missing:
            status = "FAIL"
            notes = f"missing columns: {'|'.join(missing)}"
        if read_status != "READ_OK":
            status = "FAIL"
            notes = read_status
    return {
        "input_key": key,
        "path": raw_path,
        "exists_by_metadata_check": exists,
        "size_bytes": size,
        "row_count": row_count,
        "column_count": column_count,
        "required": "yes",
        "required_columns_present": required_columns_present,
        "status": status,
        "read_scope": "compact_text_table_only",
        "notes": notes,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def run(config_path: Path = DEFAULT_CONFIG) -> InputInventoryResult:
    """Run the B8.7b.2 input inventory."""
    config = load_config(config_path)
    rows = [input_row(config, key) for key in REQUIRED_INPUT_KEYS]

    candidate_count = 0
    if rows[2]["status"] == "PASS":
        candidate_count = len(read_csv_rows(clean(config["b87b_new_candidate_sample_index_path"])))
    expected = int(config.get("expected_new_candidate_count", 150))
    rows.append(
        {
            "input_key": "expected_new_candidate_count_check",
            "path": clean(config["b87b_new_candidate_sample_index_path"]),
            "exists_by_metadata_check": "yes" if candidate_count == expected else "no",
            "size_bytes": "",
            "row_count": candidate_count,
            "column_count": "",
            "required": "yes",
            "required_columns_present": "not_applicable",
            "status": "PASS" if candidate_count == expected else "FAIL",
            "read_scope": "compact_csv_count_check",
            "notes": f"expected={expected}",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    )
    for key in GUARDRAIL_KEYS:
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
    for root in effective_search_roots(config):
        rows.append(
            {
                "input_key": "search_root_configured",
                "path": root,
                "exists_by_metadata_check": path_exists_metadata(root)[0],
                "size_bytes": "",
                "row_count": "",
                "column_count": "",
                "required": "yes",
                "required_columns_present": "not_applicable",
                "status": "PASS",
                "read_scope": "path_metadata_only",
                "notes": f"root_role={root_role(config, root)}",
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
    write_csv_rows(out_path(config, "b87b2_input_inventory.csv"), rows, fieldnames)
    missing_required = sum(1 for row in rows if row["required"] == "yes" and row["exists_by_metadata_check"] == "no")
    schema_errors = sum(1 for row in rows if row["required_columns_present"] == "no" or row["status"] == "FAIL")
    status = "PASS" if missing_required == 0 and schema_errors == 0 else "FAIL"
    return InputInventoryResult(
        status=status,
        inputs_checked=len(rows),
        missing_required_inputs=missing_required,
        schema_errors=schema_errors,
        candidate_count=candidate_count,
        search_root_count=len(effective_search_roots(config)),
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Inventory B8.7b.2 compact inputs and guardrails. Writes metadata "
            "CSV only; no raster IO, QGIS/SOLWEIG, manifest, runner, copy, move, or symlink."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
