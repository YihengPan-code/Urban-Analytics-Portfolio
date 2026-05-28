"""Create B8.7b no-raster-commit and Git hygiene guards.

Inputs:
    configs/v12/systemb_b87b_n300_execution_precheck.yaml and current Git
    status for the project subdirectory.
Outputs:
    b87b_no_raster_commit_guard.csv.
Saved metrics:
    Guard status for forbidden raster extensions, svfs.zip, raw data roots,
    hourly forecast CSVs, AOI/B9/WBGT/hazard/risk outputs, run-ready execution
    manifests, QGIS runners, local runners, staged files, and changed paths.
    This script does not stage or commit.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from v12_b87b_input_inventory import CLAIM_BOUNDARY, DEFAULT_CONFIG, clean, git_output
from v12_b87b_input_inventory import load_config, out_path, write_csv_rows


@dataclass(frozen=True)
class GitHygieneResult:
    """B8.7b Git hygiene result."""

    status: str
    changed_paths: int
    failed_guards: int
    headline: str


def changed_paths_from_status(status_text: str) -> list[str]:
    """Extract paths from porcelain status text."""
    paths: list[str] = []
    for line in status_text.splitlines():
        if not line.strip():
            continue
        paths.append(line[3:].strip())
    return paths


def any_path(paths: list[str], predicate: Callable[[str], bool]) -> list[str]:
    """Return changed paths matching a predicate."""
    return [path for path in paths if predicate(path.replace("\\", "/").lower())]


def guard_row(guard_item: str, matches: list[str], evidence: str) -> dict[str, Any]:
    """Build one guard row."""
    return {
        "guard_item": guard_item,
        "status": "PASS" if not matches else "FAIL",
        "matched_paths": "|".join(matches),
        "evidence": evidence,
        "action_required": "none" if not matches else "remove forbidden artifact before any review/staging",
        "claim_boundary": CLAIM_BOUNDARY,
    }


def run(config_path: Path = DEFAULT_CONFIG) -> GitHygieneResult:
    """Run B8.7b Git hygiene checks without staging or committing."""
    config = load_config(config_path)
    status_text = git_output(["git", "status", "--porcelain", "--", "."])
    staged_text = git_output(["git", "diff", "--name-only", "--cached", "--", "."])
    paths = changed_paths_from_status(status_text)
    guards = [
        (
            "no .tif/.tiff/.vrt/.asc/.img/.nc/.grib",
            any_path(paths, lambda path: path.endswith((".tif", ".tiff", ".vrt", ".asc", ".img", ".nc", ".grib"))),
            "forbidden raster-like extensions must not be committed",
        ),
        ("no svfs.zip", any_path(paths, lambda path: path.endswith("svfs.zip")), "svfs.zip must remain local-only"),
        ("no data/solweig", any_path(paths, lambda path: path.startswith("data/solweig/")), "raw/local SOLWEIG assets must not be committed"),
        ("no data/rasters", any_path(paths, lambda path: path.startswith("data/rasters/")), "raster roots must not be committed"),
        ("no data/archive", any_path(paths, lambda path: path.startswith("data/archive/")), "raw archive roots must not be committed"),
        (
            "no hourly forecast CSV",
            any_path(paths, lambda path: "hourly_grid_heatstress_forecast" in path),
            "large forecast CSVs must not be committed",
        ),
        ("no AOI prediction", any_path(paths, lambda path: "aoi_prediction" in path or "aoi-wide" in path), "B8.7b is not AOI prediction"),
        ("no B9 output", any_path(paths, lambda path: "/b9" in path or "b9_" in path), "B9 remains blocked"),
        (
            "no WBGT/risk/hazard output",
            any_path(paths, lambda path: "wbgt" in path or "risk_score" in path or "hazard_score" in path),
            "B8.7b must not create local WBGT/risk/hazard outputs",
        ),
        (
            "no execution manifest",
            any_path(
                paths,
                lambda path: "manifest" in path
                and "pre_manifest_schema_preview" not in path
                and "codex_prompt" not in path,
            ),
            "B8.7b may create schema preview only, not a run-ready manifest",
        ),
        (
            "no QGIS runner",
            any_path(paths, lambda path: path.startswith("scripts/qgis/") or "_qgis_runner" in path),
            "B8.7b must not create a QGIS runner",
        ),
        (
            "no local runner scripts",
            any_path(paths, lambda path: "local_runner" in path or path.endswith("_runner.py")),
            "B8.7b must not create local runner scripts",
        ),
        (
            "nothing staged",
            staged_text.splitlines(),
            "user requested no staging/committing",
        ),
    ]
    rows = [guard_row(item, matches, evidence) for item, matches, evidence in guards]
    rows.append(
        {
            "guard_item": "git status --porcelain -- . changed path count",
            "status": "PASS",
            "matched_paths": str(len(paths)),
            "evidence": "metadata snapshot only; changed paths listed in final git status",
            "action_required": "review before any future staging",
            "claim_boundary": CLAIM_BOUNDARY,
        }
    )
    write_csv_rows(
        out_path(config, "b87b_no_raster_commit_guard.csv"),
        rows,
        ["guard_item", "status", "matched_paths", "evidence", "action_required", "claim_boundary"],
    )
    failed = sum(1 for row in rows if row["status"] == "FAIL")
    status = "PASS" if failed == 0 else "BLOCKED"
    headline = f"{failed} failed Git hygiene guards; {len(paths)} changed paths under project subdir."
    return GitHygieneResult(status=status, changed_paths=len(paths), failed_guards=failed, headline=headline)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run B8.7b Git hygiene guards without staging or committing."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
