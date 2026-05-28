"""Inventory source artifacts for the OpenHeat 2026-05-28 development log.

Inputs:
  - A JSON-compatible YAML config passed with ``--config``. The config declares
    source roots, expected artifacts, scan directories, search patterns, and
    output CSV paths.

Outputs:
  - ``openheat_devlog_input_inventory.csv`` with expected-artifact existence,
    selected source root, size, and modified time.
  - ``openheat_devlog_file_inventory.csv`` with compact text-file inventory and
    search-pattern match counts.
  - ``openheat_devlog_missing_or_unreadable_artifacts.csv`` with expected
    artifacts that were not found or could not be read.

Saved metrics:
  - artifact_found, source_root_id, byte_size, modified_utc,
    matched_terms, match_count, readable, and missing_reason.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TEXT_SUFFIXES = {
    ".csv",
    ".json",
    ".md",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class SourceRoot:
    """Named repository/worktree root."""

    root_id: str
    path: Path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Build compact expected-artifact and text-file inventories for "
            "the OpenHeat 2026-05-28 devlog."
        )
    )
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help=(
            "Path to JSON-compatible YAML config. Inputs, outputs, and saved "
            "metrics are declared in the module docstring."
        ),
    )
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    """Load a JSON-compatible YAML config."""

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_path(path_value: str, base_dir: Path) -> Path:
    """Resolve a config path relative to the current worktree."""

    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def source_roots(config: dict[str, Any], base_dir: Path) -> list[SourceRoot]:
    """Return configured source roots."""

    roots: list[SourceRoot] = []
    for item in config["source_roots"]:
        roots.append(
            SourceRoot(
                root_id=str(item["id"]),
                path=resolve_path(str(item["path"]), base_dir),
            )
        )
    return roots


def utc_mtime(path: Path) -> str:
    """Return ISO UTC modified time."""

    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return modified.isoformat()


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    """Write rows to CSV with stable field order."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def find_artifact(relative_path: str, roots: list[SourceRoot]) -> tuple[SourceRoot | None, Path | None]:
    """Find the first existing artifact across configured roots."""

    rel = Path(relative_path)
    for root in roots:
        candidate = root.path / rel
        if candidate.exists():
            return root, candidate
    return None, None


def build_input_inventory(
    config: dict[str, Any],
    roots: list[SourceRoot],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build expected-artifact and missing-artifact inventories."""

    rows: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for artifact in config["expected_artifacts"]:
        artifact_id = artifact["id"]
        rel_path = artifact["path"]
        group = artifact.get("group", "")
        root, found = find_artifact(rel_path, roots)
        if found is None or root is None:
            row = {
                "artifact_id": artifact_id,
                "group": group,
                "relative_path": rel_path,
                "found": "no",
                "source_root_id": "",
                "source_path": "",
                "byte_size": "",
                "modified_utc": "",
                "readable": "no",
                "missing_reason": "not_found_in_configured_roots",
            }
            rows.append(row)
            missing.append(row)
            continue
        try:
            stat = found.stat()
            row = {
                "artifact_id": artifact_id,
                "group": group,
                "relative_path": rel_path,
                "found": "yes",
                "source_root_id": root.root_id,
                "source_path": str(found),
                "byte_size": stat.st_size,
                "modified_utc": utc_mtime(found),
                "readable": "yes" if found.is_file() else "directory",
                "missing_reason": "",
            }
        except OSError as exc:
            row = {
                "artifact_id": artifact_id,
                "group": group,
                "relative_path": rel_path,
                "found": "yes",
                "source_root_id": root.root_id,
                "source_path": str(found),
                "byte_size": "",
                "modified_utc": "",
                "readable": "no",
                "missing_reason": f"stat_failed:{exc.__class__.__name__}",
            }
            missing.append(row)
        rows.append(row)
    return rows, missing


def text_match_metrics(path: Path, patterns: list[str], max_bytes: int) -> tuple[str, int, str]:
    """Return matched search terms, count, and readability flag for a text file."""

    try:
        if path.stat().st_size > max_bytes:
            return "", 0, "skipped_size_limit"
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return "", 0, "no"
    lowered = text.lower()
    matched = [term for term in patterns if term.lower() in lowered]
    return ";".join(matched), len(matched), "yes"


def iter_scan_files(config: dict[str, Any], roots: list[SourceRoot]) -> Iterable[tuple[SourceRoot, Path]]:
    """Yield configured text-like files from scan directories."""

    scan_dirs = [Path(item) for item in config.get("inventory_scan_dirs", [])]
    for root in roots:
        for scan_dir in scan_dirs:
            base = root.path / scan_dir
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                    yield root, path


def build_file_inventory(config: dict[str, Any], roots: list[SourceRoot]) -> list[dict[str, Any]]:
    """Build a compact file inventory with search-term hits."""

    rows: list[dict[str, Any]] = []
    patterns = list(config.get("search_patterns", []))
    max_bytes = int(config.get("max_search_bytes", 5_000_000))
    seen: set[tuple[str, str]] = set()
    for root, path in iter_scan_files(config, roots):
        rel_path = path.relative_to(root.path).as_posix()
        key = (root.root_id, rel_path)
        if key in seen:
            continue
        seen.add(key)
        matched_terms, match_count, readable = text_match_metrics(path, patterns, max_bytes)
        rows.append(
            {
                "source_root_id": root.root_id,
                "relative_path": rel_path,
                "source_path": str(path),
                "suffix": path.suffix.lower(),
                "byte_size": path.stat().st_size,
                "modified_utc": utc_mtime(path),
                "readable": readable,
                "matched_terms": matched_terms,
                "match_count": match_count,
            }
        )
    return sorted(rows, key=lambda item: (item["source_root_id"], item["relative_path"]))


def main() -> None:
    """CLI entrypoint."""

    args = parse_args()
    base_dir = Path.cwd()
    config = load_config(args.config)
    roots = source_roots(config, base_dir)
    outputs = config["outputs"]

    input_rows, missing_rows = build_input_inventory(config, roots)
    file_rows = build_file_inventory(config, roots)

    write_csv(
        resolve_path(outputs["input_inventory_csv"], base_dir),
        input_rows,
        [
            "artifact_id",
            "group",
            "relative_path",
            "found",
            "source_root_id",
            "source_path",
            "byte_size",
            "modified_utc",
            "readable",
            "missing_reason",
        ],
    )
    write_csv(
        resolve_path(outputs["file_inventory_csv"], base_dir),
        file_rows,
        [
            "source_root_id",
            "relative_path",
            "source_path",
            "suffix",
            "byte_size",
            "modified_utc",
            "readable",
            "matched_terms",
            "match_count",
        ],
    )
    write_csv(
        resolve_path(outputs["missing_artifacts_csv"], base_dir),
        missing_rows,
        [
            "artifact_id",
            "group",
            "relative_path",
            "found",
            "source_root_id",
            "source_path",
            "byte_size",
            "modified_utc",
            "readable",
            "missing_reason",
        ],
    )
    print(
        "inventory_complete "
        f"expected={len(input_rows)} files={len(file_rows)} missing={len(missing_rows)}"
    )


if __name__ == "__main__":
    main()
