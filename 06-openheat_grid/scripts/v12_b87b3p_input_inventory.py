"""Inventory B8.7b.3p protocol parity inputs and shared helpers.

Inputs:
    configs/v12/systemb_b87b3p_solweig_protocol_parity.yaml plus compact CSV,
    Markdown, JSON/YAML, and script evidence declared in that config.
Outputs:
    outputs/v12_surrogate/b8_7b3p_solweig_protocol_parity/
    b87b3p_input_inventory.csv.
Saved metrics:
    Path existence, file size, CSV row/column counts, configured guardrail
    status, and compact source-lock metadata availability. This script does
    not run QGIS/SOLWEIG, read raster pixels, open svfs.zip, write/copy/move
    rasters, create a run-ready manifest, create a runner, stage, or commit.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "v12" / "systemb_b87b3p_solweig_protocol_parity.yaml"

CLAIM_BOUNDARY = (
    "B8.7b.3p protocol/source parity audit only; no QGIS/SOLWEIG; no raster "
    "pixel read; no raster write/copy/move; no svfs.zip open; no run-ready "
    "manifest/runner; no AOI/B9/WBGT/risk/hazard/exposure/vulnerability/"
    "System A-B coupling."
)

FORBIDDEN_SCOPE_TRUE_KEYS = {
    "qgis_executed_by_codex",
    "solweig_executed_by_codex",
    "create_rasters",
    "copy_rasters",
    "move_rasters",
    "write_rasters",
    "read_raster_pixels",
    "open_svf_zip",
    "create_run_ready_manifest",
    "create_runner",
    "create_local_runner",
    "create_aoi_outputs",
    "create_b9_outputs",
    "create_wbgt_outputs",
    "create_risk_outputs",
    "stage_changes",
    "commit_changes",
}

CSV_EXTENSIONS = {".csv"}
TEXT_EXTENSIONS = {".md", ".txt", ".py", ".yaml", ".yml", ".json"}
RASTER_EXTENSIONS = {".tif", ".tiff", ".vrt", ".asc", ".img", ".nc", ".grib"}


@dataclass(frozen=True)
class InventoryResult:
    """Compact result from the input inventory step."""

    status: str
    rows_written: int
    missing_inputs: int
    guardrail_failures: int


def clean(value: Any) -> str:
    """Return a compact single-line string."""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def parse_inline_list(text: str) -> list[Any]:
    """Parse a small YAML inline list."""
    inner = text.strip()[1:-1].strip()
    if not inner:
        return []
    return [parse_scalar(part.strip()) for part in inner.split(",")]


def parse_scalar(value: str) -> Any:
    """Parse the small YAML scalar subset used by OpenHeat configs."""
    stripped = value.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        return parse_inline_list(stripped)
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
        pass
    try:
        return float(stripped)
    except ValueError:
        return stripped.strip("\"'")


def read_simple_yaml(path: Path) -> dict[str, Any]:
    """Read the simple nested YAML shape used by local configs."""
    lines = [
        line.rstrip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    for idx, line in enumerate(lines):
        indent = len(line) - len(line.lstrip(" "))
        text = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if text.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"Unsupported YAML list placement: {line}")
            parent.append(parse_scalar(text[2:].strip()))
            continue
        key, _, raw_value = text.partition(":")
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value:
            if not isinstance(parent, dict):
                raise ValueError(f"Unsupported YAML mapping placement: {line}")
            parent[key] = parse_scalar(raw_value)
            continue
        next_container: Any = {}
        for future in lines[idx + 1 :]:
            future_indent = len(future) - len(future.lstrip(" "))
            future_text = future.strip()
            if future_indent <= indent:
                break
            next_container = [] if future_text.startswith("- ") else {}
            break
        if not isinstance(parent, dict):
            raise ValueError(f"Unsupported YAML parent for key: {line}")
        parent[key] = next_container
        stack.append((indent, next_container))
    return root


def load_config(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Load the B8.7b.3p config."""
    return read_simple_yaml(repo_path(config_path))


def repo_path(value: str | Path) -> Path:
    """Resolve repository-relative paths against this OpenHeat subdirectory."""
    path = Path(clean(value))
    return path if path.is_absolute() else PROJECT_ROOT / path


def rel(path: str | Path) -> str:
    """Return a repository-relative POSIX path when possible."""
    resolved = repo_path(path)
    try:
        return resolved.resolve(strict=False).relative_to(PROJECT_ROOT.resolve(strict=False)).as_posix()
    except ValueError:
        return resolved.as_posix()


def output_dir(config: dict[str, Any]) -> Path:
    """Return and create the B8.7b.3p output directory."""
    outputs = config.get("outputs", {})
    out_dir = outputs.get("output_dir", "outputs/v12_surrogate/b8_7b3p_solweig_protocol_parity")
    resolved = repo_path(out_dir)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def out_path(config: dict[str, Any], filename: str) -> Path:
    """Return a path inside the B8.7b.3p output directory."""
    return output_dir(config) / filename


def write_csv_rows(path: str | Path, rows: Iterable[dict[str, Any]], fieldnames: Sequence[str]) -> None:
    """Write UTF-8 CSV rows with stable columns."""
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


def read_text(path: str | Path) -> str:
    """Read a UTF-8 or UTF-8-sig text file."""
    return repo_path(path).read_text(encoding="utf-8-sig")


def read_json(path: str | Path) -> dict[str, Any]:
    """Read a JSON config/evidence file."""
    return json.loads(read_text(path))


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    """Read a UTF-8 or UTF-8-sig CSV file."""
    with repo_path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def read_csv_header(path: str | Path) -> list[str]:
    """Read only the CSV header."""
    with repo_path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        return next(csv.reader(handle), [])


def csv_profile(path: str | Path) -> dict[str, Any]:
    """Return row count, column count, and header without raster access."""
    resolved = repo_path(path)
    try:
        with resolved.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
            row_count = sum(1 for _ in reader)
        return {
            "read_status": "READABLE_CSV",
            "row_count": row_count,
            "column_count": len(header),
            "columns": "|".join(header),
            "read_error": "",
        }
    except Exception as exc:
        return {
            "read_status": "READ_ERROR",
            "row_count": "",
            "column_count": "",
            "columns": "",
            "read_error": clean(exc),
        }


def unique_values(rows: list[dict[str, str]], column: str) -> list[str]:
    """Return sorted unique nonblank values from a column."""
    return sorted({clean(row.get(column, "")) for row in rows if clean(row.get(column, ""))})


def as_list(value: Any) -> list[Any]:
    """Normalize a scalar/list config value to a list."""
    if isinstance(value, list):
        return value
    if value in {None, ""}:
        return []
    return [value]


def nested_get(data: dict[str, Any], path: Sequence[str], default: Any = "") -> Any:
    """Get a nested dict value."""
    current: Any = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def yes_no(value: bool) -> str:
    """Format a boolean as yes/no."""
    return "yes" if value else "no"


def metadata_for_path(path: str | Path) -> dict[str, Any]:
    """Return filesystem metadata without opening file contents."""
    resolved = repo_path(path)
    row: dict[str, Any] = {
        "exists": "no",
        "is_file": "no",
        "is_dir": "no",
        "size_bytes": "",
        "metadata_error": "",
    }
    try:
        exists = resolved.exists()
        row["exists"] = yes_no(exists)
        row["is_file"] = yes_no(resolved.is_file()) if exists else "no"
        row["is_dir"] = yes_no(resolved.is_dir()) if exists else "no"
        if exists and resolved.is_file():
            row["size_bytes"] = resolved.stat().st_size
    except OSError as exc:
        row["metadata_error"] = clean(exc)
    return row


def git_output(args: list[str]) -> str:
    """Run a read-only git command and return compact stdout/stderr."""
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=PROJECT_ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
    except OSError as exc:
        return f"GIT_ERROR:{clean(exc)}"
    output = completed.stdout.strip() or completed.stderr.strip()
    return clean(output)


def infer_read_status(path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    """Return compact content-read metadata for safe text/table files."""
    if metadata["exists"] != "yes" or metadata["is_file"] != "yes":
        return {"read_status": "MISSING", "row_count": "", "column_count": "", "columns": "", "read_error": ""}
    suffix = path.suffix.lower()
    if suffix in CSV_EXTENSIONS:
        return csv_profile(path)
    if suffix in RASTER_EXTENSIONS or path.name.lower() == "svfs.zip":
        return {
            "read_status": "METADATA_ONLY_FORBIDDEN_TO_OPEN",
            "row_count": "",
            "column_count": "",
            "columns": "",
            "read_error": "",
        }
    if suffix in TEXT_EXTENSIONS:
        try:
            text = read_text(path)
            return {
                "read_status": "READABLE_TEXT",
                "row_count": len(text.splitlines()),
                "column_count": "",
                "columns": "",
                "read_error": "",
            }
        except Exception as exc:
            return {"read_status": "READ_ERROR", "row_count": "", "column_count": "", "columns": "", "read_error": clean(exc)}
    return {"read_status": "METADATA_ONLY", "row_count": "", "column_count": "", "columns": "", "read_error": ""}


def configured_path_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build inventory rows from configured evidence paths."""
    rows: list[dict[str, Any]] = []
    for group_name in ["inputs", "canonical_sources"]:
        group = config.get(group_name, {})
        if not isinstance(group, dict):
            continue
        for key, value in group.items():
            if isinstance(value, (dict, list)):
                continue
            value_text = clean(value)
            looks_like_path = (
                "/" in value_text
                or "\\" in value_text
                or Path(value_text).suffix.lower() in CSV_EXTENSIONS | TEXT_EXTENSIONS | RASTER_EXTENSIONS
            )
            if not looks_like_path:
                rows.append(
                    {
                        "input_group": group_name,
                        "input_key": key,
                        "configured_value": value_text,
                        "resolved_path": "",
                        "path_kind": "scalar_metadata",
                        "exists": "",
                        "is_file": "",
                        "is_dir": "",
                        "size_bytes": "",
                        "read_status": "NOT_A_PATH",
                        "row_count": "",
                        "column_count": "",
                        "columns": "",
                        "guardrail_status": "PASS",
                        "notes": "Configured scalar value.",
                        "claim_boundary": CLAIM_BOUNDARY,
                    }
                )
                continue
            resolved = repo_path(value_text)
            metadata = metadata_for_path(resolved)
            read_status = infer_read_status(resolved, metadata)
            rows.append(
                {
                    "input_group": group_name,
                    "input_key": key,
                    "configured_value": value_text,
                    "resolved_path": resolved.as_posix(),
                    "path_kind": "absolute" if resolved.is_absolute() else "relative",
                    **metadata,
                    **read_status,
                    "guardrail_status": "PASS",
                    "notes": "Configured compact evidence path; rasters/svfs.zip metadata-only if present.",
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
    return rows


def search_root_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build metadata-only inventory rows for configured search roots."""
    rows: list[dict[str, Any]] = []
    for root in as_list(config.get("search_roots", [])):
        resolved = repo_path(root)
        metadata = metadata_for_path(resolved)
        rows.append(
            {
                "input_group": "search_roots",
                "input_key": clean(root),
                "configured_value": clean(root),
                "resolved_path": resolved.as_posix(),
                "path_kind": "search_root",
                **metadata,
                "read_status": "METADATA_ONLY",
                "row_count": "",
                "column_count": "",
                "columns": "",
                "read_error": "",
                "guardrail_status": "PASS",
                "notes": "Search root inventory only; missing roots are nonfatal.",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return rows


def guardrail_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Build rows for explicit scope guardrails."""
    scope = config.get("scope", {})
    rows: list[dict[str, Any]] = []
    if not isinstance(scope, dict):
        return rows
    for key, value in sorted(scope.items()):
        failure = key in FORBIDDEN_SCOPE_TRUE_KEYS and bool(value)
        rows.append(
            {
                "input_group": "scope",
                "input_key": key,
                "configured_value": clean(value),
                "resolved_path": "",
                "path_kind": "guardrail",
                "exists": "",
                "is_file": "",
                "is_dir": "",
                "size_bytes": "",
                "metadata_error": "",
                "read_status": "CONFIG_GUARDRAIL",
                "row_count": "",
                "column_count": "",
                "columns": "",
                "read_error": "",
                "guardrail_status": "FAIL" if failure else "PASS",
                "notes": "Forbidden guardrail must be false." if failure else "Scope guardrail accepted.",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    return rows


FIELDNAMES = [
    "input_group",
    "input_key",
    "configured_value",
    "resolved_path",
    "path_kind",
    "exists",
    "is_file",
    "is_dir",
    "size_bytes",
    "metadata_error",
    "read_status",
    "row_count",
    "column_count",
    "columns",
    "read_error",
    "guardrail_status",
    "notes",
    "claim_boundary",
]


def run(config_path: str | Path = DEFAULT_CONFIG) -> InventoryResult:
    """Run the B8.7b.3p input inventory."""
    config = load_config(config_path)
    rows = configured_path_rows(config) + search_root_rows(config) + guardrail_rows(config)
    missing_inputs = sum(1 for row in rows if row["input_group"] == "inputs" and row.get("exists") == "no")
    guardrail_failures = sum(1 for row in rows if row.get("guardrail_status") == "FAIL")
    status = "PASS" if missing_inputs == 0 and guardrail_failures == 0 else "WARN_INPUT_REVIEW"
    write_csv_rows(out_path(config, "b87b3p_input_inventory.csv"), rows, FIELDNAMES)
    return InventoryResult(status=status, rows_written=len(rows), missing_inputs=missing_inputs, guardrail_failures=guardrail_failures)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Inventory B8.7b.3p protocol parity inputs. Writes compact CSV "
            "metadata only; does not run QGIS/SOLWEIG, read raster pixels, "
            "open svfs.zip, create manifests/runners, stage, or commit."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    result = run(args.config)
    print(f"input_inventory_status={result.status}")
    print(f"rows_written={result.rows_written}")
    print(f"missing_inputs={result.missing_inputs}")
    print(f"guardrail_failures={result.guardrail_failures}")


if __name__ == "__main__":
    main()
