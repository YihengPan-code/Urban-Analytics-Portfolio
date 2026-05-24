#!/usr/bin/env python3
"""Guard OpenHeat Git commits against heavy/raw archive and raster artifacts.

This script is intentionally conservative. It is designed for the v1.1 GitHub
Actions archive workflow and for pre-public-repo checks.

Examples
--------
Scan changed files plus common dangerous paths::

    python scripts/v11_archive_commit_guard.py --repo-root . --max-mb 25

Scan only staged files before committing::

    python scripts/v11_archive_commit_guard.py --repo-root . --staged-only --max-mb 25

The script exits with non-zero status if a forbidden path or oversized file is
found.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

FORBIDDEN_PATTERNS: tuple[str, ...] = (
    "*.tif",
    "*.tiff",
    "svfs.zip",
    "data/solweig/**",
    "data/rasters/**",
    "data/archive/**",
    "data/raw/buildings_v10/**",
    "outputs/*forecast_live/*hourly_grid_heatstress_forecast*.csv",
    "*.zip",
)

ALLOWED_ZIP_EXCEPTIONS: tuple[str, ...] = (
    "outputs/v11_archive_ops/**",
)

@dataclass(frozen=True)
class GuardFinding:
    path: str
    reason: str
    size_mb: float | None = None
    pattern: str | None = None


def run_git(repo_root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout


def parse_status_paths(status_output: str) -> list[str]:
    paths: list[str] = []
    for line in status_output.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        if status.strip() == "D":
            continue
        # Porcelain format: XY path, or XY old -> new
        raw = line[3:] if len(line) > 3 else line
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        paths.append(raw.strip().strip('"'))
    return paths


def git_candidate_paths(repo_root: Path, staged_only: bool, include_tracked: bool) -> set[str]:
    if staged_only:
        out = run_git(repo_root, ["diff", "--cached", "--name-status"])
        paths = set()
        for line in out.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if parts[0] == "D":
                continue
            if len(parts) >= 2:
                paths.add(parts[-1].strip().strip('"'))
        return paths
    out = run_git(repo_root, ["status", "--porcelain"])
    paths = set(parse_status_paths(out))
    if include_tracked:
        tracked = run_git(repo_root, ["ls-files"])
        for p in tracked.splitlines():
            if p.strip():
                paths.add(p.strip())
    return paths


def matches_any(path: str, patterns: tuple[str, ...]) -> str | None:
    normalized = path.replace("\\", "/")
    for pattern in patterns:
        if fnmatch.fnmatch(normalized, pattern):
            return pattern
    return None


def is_allowed_zip_exception(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return matches_any(normalized, ALLOWED_ZIP_EXCEPTIONS) is not None


def inspect_paths(repo_root: Path, paths: set[str], max_mb: float) -> list[GuardFinding]:
    findings: list[GuardFinding] = []
    for rel in sorted(paths):
        normalized_rel = rel.replace("\\", "/")
        if not rel or normalized_rel.startswith(".git/") or normalized_rel.startswith("../"):
            continue
        full = repo_root / rel
        if not full.exists():
            continue
        pattern = matches_any(rel, FORBIDDEN_PATTERNS)
        if pattern and not (rel.lower().endswith(".zip") and is_allowed_zip_exception(rel)):
            findings.append(GuardFinding(path=rel, reason="forbidden_path_pattern", pattern=pattern))
            continue
        if full.is_file():
            size_mb = full.stat().st_size / (1024 * 1024)
            if size_mb > max_mb:
                findings.append(GuardFinding(path=rel, reason="file_too_large", size_mb=round(size_mb, 3)))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--max-mb", type=float, default=25.0)
    parser.add_argument("--staged-only", action="store_true")
    parser.add_argument("--include-tracked", action="store_true", help="Also scan all files already tracked in HEAD.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    paths = git_candidate_paths(repo_root, staged_only=args.staged_only, include_tracked=args.include_tracked)
    findings = inspect_paths(repo_root, paths, max_mb=args.max_mb)

    payload = {
        "repo_root": str(repo_root),
        "staged_only": args.staged_only,
        "max_mb": args.max_mb,
        "n_paths_checked": len(paths),
        "n_findings": len(findings),
        "findings": [asdict(f) for f in findings],
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if findings:
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
