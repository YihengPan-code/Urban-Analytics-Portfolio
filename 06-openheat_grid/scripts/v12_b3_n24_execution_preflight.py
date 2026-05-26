"""Sprint B3 N24 SOLWEIG execution preflight.

Inputs:
  - B2.2 frozen selected-cell CSV.
  - v12 N24 SOLWEIG run matrix and scenario manifests.
  - Local DSM/vector/forcing inputs declared in the execution config.

Outputs:
  - outputs/v12_solweig_n24_execution/b3_b2_2_sync_check.csv
  - outputs/v12_solweig_n24_execution/b3_b2_2_sync_check.md
  - outputs/v12_solweig_n24_execution/b3_input_preflight.csv
  - outputs/v12_solweig_n24_execution/b3_input_preflight.md

Saved metrics:
  - frozen-cell count and replacement presence/absence checks.
  - run matrix row and uniqueness checks.
  - per-cell scenario/hour completeness checks.
  - non-QGIS input existence, geometry/centroid resolvability, git staging and
    raw-output tracking checks.

Run:
  C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\\v12_b3_n24_execution_preflight.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs/v12/v12_solweig_n24_execution_config.example.json"
EXPECTED_CELLS = [
    "TP_0059",
    "TP_0326",
    "TP_0366",
    "TP_0542",
    "TP_0565",
    "TP_0627",
    "TP_0835",
    "TP_0986",
    "TP_0088",
    "TP_0575",
    "TP_0433",
    "TP_0857",
    "TP_0301",
    "TP_0773",
    "TP_0492",
    "TP_0037",
    "TP_0141",
    "TP_0409",
    "TP_0098",
    "TP_0960",
    "TP_0115",
    "TP_0254",
    "TP_0676",
    "TP_0154",
]
REPLACEMENT_IN = ["TP_0141", "TP_0301", "TP_0773", "TP_0676", "TP_0575"]
REPLACED_OUT = ["TP_0058", "TP_0828", "TP_0802", "TP_0675", "TP_0916"]


@dataclass
class Check:
    section: str
    check_name: str
    status: str
    expected: str
    observed: str
    detail: str = ""


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add_check(
    rows: list[Check],
    section: str,
    name: str,
    ok: bool,
    expected: Any,
    observed: Any,
    detail: str = "",
) -> None:
    rows.append(
        Check(
            section=section,
            check_name=name,
            status="PASS" if ok else "FAIL",
            expected=str(expected),
            observed=str(observed),
            detail=detail,
        )
    )


def run_git(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def write_checks(rows: list[Check], csv_path: Path, md_path: Path, title: str) -> bool:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([r.__dict__ for r in rows])
    df.to_csv(csv_path, index=False)
    failed = df[df["status"] != "PASS"].copy()
    lines = [f"# {title}", ""]
    lines.append(f"- checks: `{len(df)}`")
    lines.append(f"- failed: `{len(failed)}`")
    lines.append("")
    if failed.empty:
        lines.append("Status: **PASS**")
    else:
        lines.append("Status: **BLOCKED**")
        lines.append("")
        lines.append("## Failed checks")
        lines.append("")
        lines.append(failed.to_markdown(index=False))
    lines.append("")
    lines.append("## All checks")
    lines.append("")
    lines.append(df.to_markdown(index=False))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return failed.empty


def sync_checks(selected: pd.DataFrame, run_matrix: pd.DataFrame) -> list[Check]:
    rows: list[Check] = []
    selected_cells = selected["cell_id"].astype(str).tolist()
    rm = run_matrix.copy()
    rm["cell_id"] = rm["cell_id"].astype(str)
    rm["scenario"] = rm["scenario"].astype(str)
    rm["hour"] = rm["hour"].astype(int)

    add_check(rows, "b2_2_sync", "selected_cell_count", len(selected_cells) == 24, 24, len(selected_cells))
    add_check(rows, "b2_2_sync", "selected_cells_match_expected_order", selected_cells == EXPECTED_CELLS, "expected frozen N24 order", "|".join(selected_cells))
    add_check(rows, "b2_2_sync", "run_matrix_rows", len(rm) == 240, 240, len(rm))
    add_check(rows, "b2_2_sync", "unique_run_id", rm["run_id"].nunique() == 240, 240, rm["run_id"].nunique())
    present = sorted(set(REPLACEMENT_IN) & set(selected_cells))
    absent_bad = sorted(set(REPLACED_OUT) & set(selected_cells))
    add_check(rows, "b2_2_sync", "replacement_in_cells_present", set(present) == set(REPLACEMENT_IN), ",".join(REPLACEMENT_IN), ",".join(present))
    add_check(rows, "b2_2_sync", "replaced_out_cells_absent", not absent_bad, "none present", ",".join(absent_bad) if absent_bad else "none")

    expected_scenarios = {"base", "overhead_as_canopy"}
    expected_hours = {10, 12, 13, 15, 16}
    for cell_id in selected_cells:
        sub = rm[rm["cell_id"] == cell_id]
        scenarios = set(sub["scenario"])
        hours = set(sub["hour"])
        add_check(rows, "b2_2_sync", f"{cell_id}_has_base_and_overhead", scenarios == expected_scenarios, sorted(expected_scenarios), sorted(scenarios))
        add_check(rows, "b2_2_sync", f"{cell_id}_has_required_hours", hours == expected_hours, sorted(expected_hours), sorted(hours))
        expected_pairs = {(s, h) for s in expected_scenarios for h in expected_hours}
        observed_pairs = set(zip(sub["scenario"], sub["hour"]))
        add_check(rows, "b2_2_sync", f"{cell_id}_has_10_scenario_hour_runs", observed_pairs == expected_pairs, 10, len(observed_pairs))
    return rows


def geometry_checks(cfg: dict[str, Any], selected_cells: list[str]) -> list[Check]:
    rows: list[Check] = []
    grid_path = repo_path(cfg["grid_feature_path"])
    if not grid_path.exists():
        add_check(rows, "geometry", "grid_feature_file_exists", False, grid_path, "missing")
        return rows
    grid = pd.read_csv(grid_path)
    required_cols = {"cell_id", "centroid_x_svy21", "centroid_y_svy21"}
    add_check(rows, "geometry", "grid_has_centroid_columns", required_cols.issubset(grid.columns), sorted(required_cols), sorted(set(grid.columns) & required_cols))
    if not required_cols.issubset(grid.columns):
        return rows
    grid["cell_id"] = grid["cell_id"].astype(str)
    found = sorted(set(selected_cells) & set(grid["cell_id"]))
    add_check(rows, "geometry", "selected_cells_resolved_in_grid", len(found) == len(selected_cells), len(selected_cells), len(found), ",".join(sorted(set(selected_cells) - set(found))))
    sub = grid[grid["cell_id"].isin(selected_cells)].copy()
    finite = sub[["centroid_x_svy21", "centroid_y_svy21"]].notna().all(axis=1)
    add_check(rows, "geometry", "selected_cell_centroids_non_null", bool(finite.all()), len(selected_cells), int(finite.sum()))
    return rows


def input_checks(cfg: dict[str, Any], selected_cells: list[str]) -> list[Check]:
    rows: list[Check] = []
    for key in [
        "selected_cells_path",
        "run_matrix_path",
        "base_manifest_path",
        "overhead_manifest_path",
        "building_dsm_path",
        "vegetation_dsm_path",
        "overhead_vector_path",
    ]:
        path = repo_path(cfg[key])
        add_check(rows, "inputs", f"{key}_exists", path.exists(), path, "exists" if path.exists() else "missing")
    for hour in cfg["hours"]:
        forcing = repo_path(cfg["forcing_paths_by_hour"][str(hour)])
        add_check(rows, "inputs", f"forcing_h{hour:02d}_exists", forcing.exists(), forcing, "exists" if forcing.exists() else "missing")

    rows.extend(geometry_checks(cfg, selected_cells))

    raw_root = repo_path(cfg["raw_output_root"])
    code, tracked = run_git(["ls-files", str(raw_root.relative_to(PROJECT_ROOT)).replace("\\", "/")])
    add_check(rows, "git_safety", "raw_output_root_not_tracked", tracked == "", "no tracked files", tracked or "none")
    code, staged = run_git(["diff", "--cached", "--name-only"])
    add_check(rows, "git_safety", "no_staged_changes_before_execution", staged == "", "no staged files", staged or "none")
    code, ignored = run_git(["check-ignore", "-q", str(raw_root.relative_to(PROJECT_ROOT)).replace("\\", "/")])
    add_check(rows, "git_safety", "raw_output_root_ignored_or_untracked", code == 0 or tracked == "", "ignored or no tracked files", "ignored" if code == 0 else "not ignored but currently untracked")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run B3 N24 preflight and B2.2 sync checks.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Execution config JSON.")
    args = parser.parse_args()

    cfg = read_json(repo_path(args.config))
    out_dir = repo_path(cfg["summary_output_dir"])
    selected = load_csv(repo_path(cfg["selected_cells_path"]))
    run_matrix = load_csv(repo_path(cfg["run_matrix_path"]))

    sync = sync_checks(selected, run_matrix)
    sync_ok = write_checks(
        sync,
        out_dir / "b3_b2_2_sync_check.csv",
        out_dir / "b3_b2_2_sync_check.md",
        "Sprint B3 B2.2 Synchronization Check",
    )
    if not sync_ok:
        raise SystemExit("BLOCKED: B2.2 sync check failed. See outputs/v12_solweig_n24_execution/b3_b2_2_sync_check.md")

    selected_cells = selected["cell_id"].astype(str).tolist()
    preflight = input_checks(cfg, selected_cells)
    preflight_ok = write_checks(
        preflight,
        out_dir / "b3_input_preflight.csv",
        out_dir / "b3_input_preflight.md",
        "Sprint B3 Input Preflight",
    )
    if not preflight_ok:
        raise SystemExit("BLOCKED: input preflight failed. See outputs/v12_solweig_n24_execution/b3_input_preflight.md")
    print("[OK] B3 B2.2 sync and input preflight passed")


if __name__ == "__main__":
    main()
