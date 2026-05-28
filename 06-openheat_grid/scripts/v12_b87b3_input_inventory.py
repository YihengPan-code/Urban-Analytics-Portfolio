"""Inventory B8.7b.3 compact inputs and provide shared helpers.

Inputs:
    configs/v12/systemb_b87b3_full_raster_source_preplan.yaml plus the manual
    source CSV and prior B8.7b/B8.7b.1/B8.7b.2 compact text/table artifacts
    declared or expected by this lane.
Outputs:
    outputs/v12_surrogate/b8_7b3_full_raster_source_preplan/
    b87b3_input_inventory.csv.
Saved metrics:
    Path existence, row/column counts for compact CSV inputs, optional prior
    report/status availability, and guardrail flags. This script does not run
    QGIS/SOLWEIG, read raster pixels, write/copy/move/symlink rasters, open
    svfs.zip, create per-cell assets, or create a run-ready manifest/runner.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "v12" / "systemb_b87b3_full_raster_source_preplan.yaml"

CLAIM_BOUNDARY = (
    "B8.7b.3 metadata/header-only source lock and preplan; no raster pixel read; "
    "no raster write/copy/move/symlink; no svfs.zip open; no QGIS/SOLWEIG; no "
    "run-ready manifest/runner; no AOI/B9/WBGT/risk/hazard/exposure/"
    "vulnerability/System A-B coupling."
)

REQUIRED_CONFIG_KEYS = [
    "manual_source_csv_path",
    "b87b_new_candidate_sample_index_path",
    "b86g3_n300_v4_design_path",
    "b87b1_expected_paths_path",
    "b87b1_readiness_path",
]

REQUIRED_COLUMNS = {
    "manual_source_csv_path": ["source_kind", "scenario", "absolute_path", "user_decision", "version_status", "notes"],
    "b87b_new_candidate_sample_index_path": ["cell_id", "sample_group", "primary_role", "spatial_bin", "typology"],
    "b86g3_n300_v4_design_path": ["cell_id", "primary_role", "spatial_bin", "typology", "source_closeout_status"],
    "b87b1_expected_paths_path": ["cell_id"],
    "b87b1_readiness_path": ["cell_id"],
}

GUARDRAIL_KEYS = [
    "metadata_only",
    "header_only_allowed",
    "no_pixel_read",
    "no_raster_write",
    "no_copy_move_symlink",
    "no_qgis_solweig",
    "no_run_ready_manifest",
    "no_qgis_runner",
    "no_aoi_prediction",
    "no_b9",
]


@dataclass(frozen=True)
class InventoryResult:
    """Compact result from the input inventory step."""

    status: str
    rows_written: int
    missing_required_inputs: int
    guardrail_failures: int


def clean(value: Any) -> str:
    """Return a compact one-line string."""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def parse_scalar(value: str) -> Any:
    """Parse the tiny YAML scalar subset used by the lane config."""
    stripped = value.strip()
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
    """Resolve project-relative paths under the current worktree."""
    candidate = Path(clean(path))
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def output_dir(config: dict[str, Any]) -> Path:
    """Return the B8.7b.3 output directory, creating it if needed."""
    path = repo_path(config["output_dir"])
    path.mkdir(parents=True, exist_ok=True)
    return path


def out_path(config: dict[str, Any], filename: str) -> Path:
    """Return a path inside the B8.7b.3 output directory."""
    return output_dir(config) / filename


def yes_no(value: bool) -> str:
    """Format a boolean as yes/no."""
    return "yes" if value else "no"


def load_config(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Load the small YAML config without external dependencies."""
    resolved = repo_path(config_path)
    config: dict[str, Any] = {}
    current_list: str | None = None
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
                current_list = None
            else:
                config[key] = []
                current_list = key
            continue
        if current_list and stripped.startswith("- "):
            config[current_list].append(parse_scalar(stripped[2:]))
    return config


def config_list(config: dict[str, Any], key: str) -> list[str]:
    """Return a config field as a list of strings."""
    value = config.get(key, [])
    if isinstance(value, list):
        return [clean(item) for item in value]
    if value in {None, ""}:
        return []
    return [clean(value)]


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    """Read a UTF-8 or UTF-8-sig CSV file."""
    with repo_path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def read_csv_header(path: str | Path) -> list[str]:
    """Read only the CSV header."""
    with repo_path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        return next(csv.reader(handle), [])


def write_csv_rows(path: str | Path, rows: Iterable[dict[str, Any]], fieldnames: Sequence[str]) -> None:
    """Write a UTF-8 CSV with stable column order."""
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


def metadata_for_path(path: str | Path) -> dict[str, Any]:
    """Return filesystem metadata without opening file contents."""
    resolved = repo_path(path)
    row: dict[str, Any] = {
        "exists_by_metadata": "no",
        "is_file": "no",
        "is_dir": "no",
        "size_bytes": "",
        "metadata_error": "",
    }
    try:
        exists = resolved.exists()
        row["exists_by_metadata"] = yes_no(exists)
        row["is_file"] = yes_no(resolved.is_file()) if exists else "no"
        row["is_dir"] = yes_no(resolved.is_dir()) if exists else "no"
        if exists and resolved.is_file():
            row["size_bytes"] = resolved.stat().st_size
    except OSError as exc:
        row["metadata_error"] = clean(exc)
    return row


def csv_shape(path: str | Path) -> tuple[str, str, list[str], str]:
    """Return row count, column count, header, and read status for a compact CSV."""
    try:
        rows = read_csv_rows(path)
        header = list(rows[0].keys()) if rows else read_csv_header(path)
    except Exception as exc:
        return "", "", [], f"READ_ERROR:{clean(exc)}"
    return clean(len(rows)), clean(len(header)), header, "READ_OK"


def git_output(args: list[str]) -> str:
    """Run a lightweight Git command from the current worktree."""
    completed = subprocess.run(args, cwd=PROJECT_ROOT, check=False, capture_output=True, text=True)
    return completed.stdout.strip()


def normalized_abs(path: str | Path, base_root: str | Path | None = None) -> str:
    """Resolve a possibly relative source path to a displayable absolute path."""
    text = clean(path)
    if not text:
        return ""
    candidate = Path(text)
    if candidate.is_absolute():
        return candidate.as_posix()
    if base_root:
        return (Path(clean(base_root)) / candidate).as_posix()
    return repo_path(candidate).as_posix()


def path_exists_text(path: str | Path) -> str:
    """Return yes/no for path existence using metadata only."""
    if not clean(path):
        return "not_applicable"
    return metadata_for_path(path)["exists_by_metadata"]


def input_inventory_row(config: dict[str, Any], key: str) -> dict[str, Any]:
    """Build one input inventory row."""
    path = clean(config.get(key, ""))
    meta = metadata_for_path(path)
    row_count = ""
    column_count = ""
    status = "PASS"
    notes = "required compact input"
    if meta["exists_by_metadata"] != "yes":
        status = "FAIL"
        notes = "missing required input"
    elif repo_path(path).suffix.lower() == ".csv":
        row_count, column_count, columns, read_status = csv_shape(path)
        missing = [column for column in REQUIRED_COLUMNS.get(key, []) if column not in columns]
        if read_status != "READ_OK":
            status = "FAIL"
            notes = read_status
        elif missing:
            status = "FAIL"
            notes = "missing columns: " + "|".join(missing)
        else:
            notes = "required columns present"
    return {
        "input_key": key,
        "path": path,
        "exists_by_metadata": meta["exists_by_metadata"],
        "row_count": row_count,
        "column_count": column_count,
        "status": status,
        "notes": notes,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def optional_prior_rows() -> list[tuple[str, str]]:
    """Return optional prior status/report paths that this lane summarizes."""
    return [
        ("b87b1_status", "outputs/v12_surrogate/b8_7b1_local_asset_remap/B8_7B1_STATUS.md"),
        ("b87b1_report", "outputs/v12_surrogate/b8_7b1_local_asset_remap/b87b1_report.md"),
        ("b87b2_discovery_status", "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/B8_7B2_STATUS.md"),
        ("b87b2_discovery_report", "outputs/v12_surrogate/b8_7b2_cross_worktree_asset_discovery/b87b2_report.md"),
    ]


def run(config_path: Path = DEFAULT_CONFIG) -> InventoryResult:
    """Run the B8.7b.3 input inventory."""
    config = load_config(config_path)
    rows = [input_inventory_row(config, key) for key in REQUIRED_CONFIG_KEYS]
    for key, path in optional_prior_rows():
        meta = metadata_for_path(path)
        rows.append(
            {
                "input_key": key,
                "path": path,
                "exists_by_metadata": meta["exists_by_metadata"],
                "row_count": "",
                "column_count": "",
                "status": "PASS" if meta["exists_by_metadata"] == "yes" else "OPTIONAL_MISSING",
                "notes": "prior lane context",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    for key in GUARDRAIL_KEYS:
        rows.append(
            {
                "input_key": "guardrail_" + key,
                "path": "",
                "exists_by_metadata": "not_applicable",
                "row_count": "",
                "column_count": "",
                "status": "PASS" if config.get(key) is True else "FAIL",
                "notes": f"{key}={config.get(key)}",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    write_csv_rows(
        out_path(config, "b87b3_input_inventory.csv"),
        rows,
        ["input_key", "path", "exists_by_metadata", "row_count", "column_count", "status", "notes", "claim_boundary"],
    )
    missing = sum(1 for row in rows if row["input_key"] in REQUIRED_CONFIG_KEYS and row["exists_by_metadata"] != "yes")
    guardrail_failures = sum(1 for row in rows if row["input_key"].startswith("guardrail_") and row["status"] != "PASS")
    status = "PASS" if missing == 0 and guardrail_failures == 0 else "FAIL"
    return InventoryResult(status, len(rows), missing, guardrail_failures)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Inventory B8.7b.3 compact inputs and guardrails; writes "
            "b87b3_input_inventory.csv; no raster pixel IO or raster writes."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
