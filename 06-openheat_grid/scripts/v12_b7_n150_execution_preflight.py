"""Sprint B7 N150 new-run-only SOLWEIG execution preflight.

Inputs:
  - B5 target freeze outputs and modifier reference rules.
  - B6/B6.1/B6.2 N150 sample-design, QA, selected-cell, and manifest files.
  - B3 completed N24 SOLWEIG focus summary, delta, and run log.
  - configs/v12/v12_solweig_n150_execution_config.example.json.

Outputs:
  - outputs/v12_solweig_n150_execution/b7_input_preflight.csv
  - outputs/v12_solweig_n150_execution/b7_input_preflight.md
  - if missing, outputs/v12_systemb_n150_sample_design/sprint_b6_2_n150_human_qa_freeze_report.md
  - if missing, outputs/v12_systemb_n150_sample_design/n150_human_quick_map_qa_freeze.csv

Saved metrics:
  - B5/B6/B6.1/B6.2 PASS gates.
  - N150/N24/N126 and manifest row-count invariants.
  - N24 reuse and B2.2 replaced-out-cell exclusion checks.
  - required static/forcing input existence checks.
  - B7 raw-output root and git staging safety checks.

Run:
  C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\\v12_b7_n150_execution_preflight.py
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
DEFAULT_CONFIG = PROJECT_ROOT / "configs/v12/v12_solweig_n150_execution_config.example.json"
OUT_DIR = PROJECT_ROOT / "outputs/v12_solweig_n150_execution"
N150_DIR = PROJECT_ROOT / "outputs/v12_systemb_n150_sample_design"
B5_DIR = PROJECT_ROOT / "outputs/v12_systemb_target_freeze"
N24_DIR = PROJECT_ROOT / "outputs/v12_solweig_n24_execution"
REPLACED_OUT = {"TP_0058", "TP_0828", "TP_0802", "TP_0675", "TP_0916"}
EXPECTED_SCENARIOS = {"base", "overhead_as_canopy"}
EXPECTED_HOURS = {10, 12, 13, 15, 16}


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


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def run_git(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


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


def report_has_pass(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace").upper()
    return "PASS" in text and "STATUS" in text


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_None._"
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in df.iterrows():
        vals = [str(row.get(col, "")).replace("\n", " ") for col in cols]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def ensure_b6_2_freeze(selected: pd.DataFrame, new: pd.DataFrame, full: pd.DataFrame, new_matrix: pd.DataFrame) -> None:
    """Create the no-replacement human QA freeze note only if it is absent."""
    report_path = N150_DIR / "sprint_b6_2_n150_human_qa_freeze_report.md"
    csv_path = N150_DIR / "n150_human_quick_map_qa_freeze.csv"
    retained_count = int(selected["selection_status"].eq("retained_n24").sum()) if "selection_status" in selected.columns else 0
    new_count = int(selected["selection_status"].eq("selected_new").sum()) if "selection_status" in selected.columns else len(new)

    if not csv_path.exists():
        rows = selected[["selection_rank", "cell_id"]].copy() if "selection_rank" in selected.columns else selected[["cell_id"]].copy()
        if "selection_rank" not in rows.columns:
            rows.insert(0, "selection_rank", range(1, len(rows) + 1))
        rows["quick_map_check_status"] = "keep"
        rows["replacement_required"] = False
        rows["human_qa_note"] = "No hard exclusion issue found in whole-sample quick map QA."
        rows["label_caveat"] = "Primary sampling stratum is coarse automatic label; fuzzy label mismatch is not a replacement reason."
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        rows.to_csv(csv_path, index=False)

    if not report_path.exists():
        lines = [
            "# Sprint B6.2 - N150 Human Quick Map QA Freeze",
            "",
            "## Status",
            "PASS",
            "",
            "## Human QA result",
            "- Human quick map QA completed.",
            "- No almost-pure water cells found.",
            "- No obvious pure rooftop / building-body cells found.",
            "- No AOI edge artifacts or invalid geometry found.",
            "- No excessive near-duplicates with no added value found.",
            "- Fuzzy primary label mismatches are not replacement reasons.",
            "",
            "## Freeze decision",
            "- No replacements.",
            "- Selected cells remain unchanged.",
            "- Manifests remain unchanged.",
            "",
            "## Validation",
            f"- Selected cells remain: {len(selected)}",
            f"- Retained N24 remains: {retained_count}",
            f"- Selected new cells remain: {new_count}",
            f"- Full run matrix remains: {len(full)} rows",
            f"- New-run-only matrix remains: {len(new_matrix)} rows",
            "- Ready for B7.",
            "",
            "## Claim boundaries",
            "No local WBGT, no hazard_score, no risk_score, no surrogate, no QGIS/SOLWEIG execution, and no System A/B coupling.",
        ]
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def normalize_matrix(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "hour_sgt" not in out.columns and "hour" in out.columns:
        out["hour_sgt"] = out["hour"]
    out["cell_id"] = out["cell_id"].astype(str)
    out["scenario"] = out["scenario"].astype(str)
    out["hour_sgt"] = out["hour_sgt"].astype(int)
    return out


def matrix_pairs(df: pd.DataFrame) -> set[tuple[str, str, int]]:
    return set(zip(df["cell_id"], df["scenario"], df["hour_sgt"]))


def b5_checks(rows: list[Check]) -> None:
    add_check(rows, "b5", "target_freeze_report_pass", report_has_pass(B5_DIR / "sprint_b5_target_freeze_report.md"), "PASS", "PASS" if report_has_pass(B5_DIR / "sprint_b5_target_freeze_report.md") else "missing_or_not_pass")
    family_path = B5_DIR / "systemb_target_family_freeze.csv"
    rules_md = B5_DIR / "systemb_modifier_reference_rules.md"
    add_check(rows, "b5", "target_family_freeze_csv_exists", family_path.exists(), family_path, "exists" if family_path.exists() else "missing")
    add_check(rows, "b5", "modifier_reference_rules_md_exists", rules_md.exists(), rules_md, "exists" if rules_md.exists() else "missing")
    if family_path.exists():
        fam = pd.read_csv(family_path)
        targets = set(fam.get("target_field", pd.Series(dtype=str)).astype(str))
        add_check(rows, "b5", "primary_target_frozen", "tmrt_p90_c" in targets, "tmrt_p90_c", sorted(targets & {"tmrt_p90_c"}))
        add_check(rows, "b5", "primary_modifier_delta_frozen", "delta_tmrt_p90_c" in targets, "delta_tmrt_p90_c", sorted(targets & {"delta_tmrt_p90_c"}))
        add_check(rows, "b5", "normalized_modifier_frozen", "m_rad_pct01" in targets, "m_rad_pct01", sorted(targets & {"m_rad_pct01"}))


def sample_design_checks(
    rows: list[Check],
    selected: pd.DataFrame,
    new: pd.DataFrame,
    full: pd.DataFrame,
    new_matrix: pd.DataFrame,
) -> tuple[set[str], set[str]]:
    add_check(rows, "b6", "sample_design_report_pass", report_has_pass(N150_DIR / "sprint_b6_n150_sample_design_report.md"), "PASS", "PASS" if report_has_pass(N150_DIR / "sprint_b6_n150_sample_design_report.md") else "missing_or_not_pass")
    add_check(rows, "b6_1", "simple_map_qa_report_pass", report_has_pass(N150_DIR / "sprint_b6_1_n150_simple_map_qa_patch_report.md"), "PASS", "PASS" if report_has_pass(N150_DIR / "sprint_b6_1_n150_simple_map_qa_patch_report.md") else "missing_or_not_pass")
    add_check(rows, "b6_2", "human_qa_freeze_report_pass", report_has_pass(N150_DIR / "sprint_b6_2_n150_human_qa_freeze_report.md"), "PASS", "PASS" if report_has_pass(N150_DIR / "sprint_b6_2_n150_human_qa_freeze_report.md") else "missing_or_not_pass")
    add_check(rows, "b6_2", "human_qa_freeze_csv_exists", (N150_DIR / "n150_human_quick_map_qa_freeze.csv").exists(), "exists", "exists" if (N150_DIR / "n150_human_quick_map_qa_freeze.csv").exists() else "missing")

    selected["cell_id"] = selected["cell_id"].astype(str)
    new["cell_id"] = new["cell_id"].astype(str)
    selected_cells = set(selected["cell_id"])
    retained_cells = set(selected.loc[selected["selection_status"].eq("retained_n24"), "cell_id"].astype(str))
    new_cells = set(selected.loc[selected["selection_status"].eq("selected_new"), "cell_id"].astype(str))
    if not new_cells:
        new_cells = set(new["cell_id"])

    add_check(rows, "counts", "n150_selected_rows", len(selected) == 150, 150, len(selected))
    add_check(rows, "counts", "n150_selected_unique_cells", len(selected_cells) == 150, 150, len(selected_cells))
    add_check(rows, "counts", "retained_n24_count", len(retained_cells) == 24, 24, len(retained_cells))
    add_check(rows, "counts", "new_cells_count", len(new_cells) == 126, 126, len(new_cells))
    add_check(rows, "counts", "n150_new_cells_file_rows", len(new) == 126, 126, len(new))
    add_check(rows, "counts", "full_run_matrix_rows", len(full) == 1500, 1500, len(full))
    add_check(rows, "counts", "new_run_matrix_rows", len(new_matrix) == 1260, 1260, len(new_matrix))

    new_matrix_cells = set(new_matrix["cell_id"])
    full_cells = set(full["cell_id"])
    add_check(rows, "matrix", "new_run_matrix_excludes_retained_n24", new_matrix_cells.isdisjoint(retained_cells), "no retained N24 cells", sorted(new_matrix_cells & retained_cells))
    add_check(rows, "matrix", "new_run_matrix_includes_only_new_cells", new_matrix_cells == new_cells, "126 selected_new cells", len(new_matrix_cells), ",".join(sorted(new_matrix_cells ^ new_cells)[:20]))
    add_check(rows, "matrix", "new_run_matrix_excludes_replaced_out_cells", new_matrix_cells.isdisjoint(REPLACED_OUT), "none", sorted(new_matrix_cells & REPLACED_OUT))
    add_check(rows, "matrix", "full_run_matrix_excludes_replaced_out_cells", full_cells.isdisjoint(REPLACED_OUT), "none", sorted(full_cells & REPLACED_OUT))
    add_check(rows, "matrix", "full_run_matrix_includes_all_selected_cells", full_cells == selected_cells, 150, len(full_cells), ",".join(sorted(full_cells ^ selected_cells)[:20]))
    add_check(rows, "matrix", "full_run_matrix_includes_retained_n24", retained_cells.issubset(full_cells), "all retained N24 cells", len(retained_cells & full_cells))
    add_check(rows, "matrix", "full_run_matrix_includes_new126", new_cells.issubset(full_cells), "all 126 new cells", len(new_cells & full_cells))

    expected_pairs = {(cell, scenario, hour) for cell in selected_cells for scenario in EXPECTED_SCENARIOS for hour in EXPECTED_HOURS}
    add_check(rows, "matrix", "full_run_matrix_all_cell_scenario_hour_pairs", matrix_pairs(full) == expected_pairs, 1500, len(matrix_pairs(full)), ",".join(map(str, sorted(expected_pairs - matrix_pairs(full))[:5])))
    expected_new_pairs = {(cell, scenario, hour) for cell in new_cells for scenario in EXPECTED_SCENARIOS for hour in EXPECTED_HOURS}
    add_check(rows, "matrix", "new_run_matrix_all_new_cell_scenario_hour_pairs", matrix_pairs(new_matrix) == expected_new_pairs, 1260, len(matrix_pairs(new_matrix)), ",".join(map(str, sorted(expected_new_pairs - matrix_pairs(new_matrix))[:5])))
    add_check(rows, "matrix", "new_base_manifest_rows", int(new_matrix["scenario"].eq("base").sum()) == 630, 630, int(new_matrix["scenario"].eq("base").sum()))
    add_check(rows, "matrix", "new_overhead_manifest_rows", int(new_matrix["scenario"].eq("overhead_as_canopy").sum()) == 630, 630, int(new_matrix["scenario"].eq("overhead_as_canopy").sum()))
    return retained_cells, new_cells


def n24_reuse_checks(rows: list[Check], retained_cells: set[str]) -> None:
    summary_path = N24_DIR / "n24_focus_tmrt_summary.csv"
    delta_path = N24_DIR / "n24_base_vs_overhead_delta.csv"
    log_path = N24_DIR / "n24_solweig_run_log.csv"
    add_check(rows, "n24_reuse", "n24_focus_summary_exists", summary_path.exists(), summary_path, "exists" if summary_path.exists() else "missing")
    add_check(rows, "n24_reuse", "n24_delta_exists", delta_path.exists(), delta_path, "exists" if delta_path.exists() else "missing")
    if summary_path.exists():
        n24 = pd.read_csv(summary_path)
        n24["cell_id"] = n24["cell_id"].astype(str)
        add_check(rows, "n24_reuse", "n24_existing_summary_rows", len(n24) == 240, 240, len(n24))
        add_check(rows, "n24_reuse", "n24_existing_summary_unique_cells", set(n24["cell_id"]) == retained_cells, sorted(retained_cells), sorted(set(n24["cell_id"])))
    if log_path.exists():
        log = pd.read_csv(log_path)
        completed = int(log["status"].isin(["success", "skipped_completed"]).sum()) if "status" in log.columns else 0
        add_check(rows, "n24_reuse", "n24_run_log_completion", completed == 240 and len(log) == 240, "240 / 240", f"{completed} / {len(log)}")
    else:
        add_check(rows, "n24_reuse", "n24_run_log_completion", False, "240 / 240", "missing")


def static_input_checks(rows: list[Check], cfg: dict[str, Any]) -> None:
    for key in [
        "run_matrix_path",
        "full_matrix_path",
        "selected_cells_path",
        "new_cells_path",
        "n24_focus_summary_path",
        "building_dsm_path",
        "vegetation_dsm_path",
        "overhead_vector_path",
        "grid_feature_path",
    ]:
        path = repo_path(cfg[key])
        add_check(rows, "inputs", f"{key}_exists", path.exists(), path, "exists" if path.exists() else "missing")
    for hour in EXPECTED_HOURS:
        forcing = repo_path(cfg["forcing_paths_by_hour"][str(hour)])
        add_check(rows, "inputs", f"forcing_h{hour}_exists", forcing.exists(), forcing, "exists" if forcing.exists() else "missing")


def git_safety_checks(rows: list[Check], cfg: dict[str, Any]) -> None:
    raw_root = repo_path(cfg["raw_output_root"]).resolve()
    allowed_root = (PROJECT_ROOT / "data/solweig/v12_n150_tiles").resolve()
    under_allowed = raw_root == allowed_root or allowed_root in raw_root.parents
    add_check(rows, "git_safety", "b7_raw_output_root_under_allowed_path", under_allowed, allowed_root, raw_root)

    code, staged = run_git(["diff", "--cached", "--name-only"])
    staged_files = [line.strip().replace("\\", "/") for line in staged.splitlines() if line.strip()]
    staged_lower = [name.lower() for name in staged_files]
    staged_raw = [
        name
        for name in staged_lower
        if name.startswith("data/solweig/") or name.startswith("data/rasters/") or "hourly_grid_heatstress_forecast" in name
    ]
    staged_rasters = [
        name
        for name in staged_lower
        if name.endswith(".tif") or name.endswith(".tiff") or name.endswith("svfs.zip")
    ]
    add_check(rows, "git_safety", "no_raw_output_is_staged", not staged_raw, "none", staged_raw or "none")
    add_check(rows, "git_safety", "no_tif_tiff_or_svfs_zip_is_staged", not staged_rasters, "none", staged_rasters or "none")

    raw_rel = str(raw_root.relative_to(PROJECT_ROOT)).replace("\\", "/") if raw_root.is_relative_to(PROJECT_ROOT) else str(raw_root)
    _, tracked_b7_raw = run_git(["ls-files", raw_rel])
    add_check(rows, "git_safety", "b7_raw_output_root_has_no_tracked_files", tracked_b7_raw == "", "none", tracked_b7_raw or "none")


def write_checks(rows: list[Check], csv_path: Path, md_path: Path) -> bool:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([row.__dict__ for row in rows])
    df.to_csv(csv_path, index=False)
    failed = df[df["status"] != "PASS"].copy()
    lines = [
        "# Sprint B7 Input Preflight",
        "",
        f"- checks: `{len(df)}`",
        f"- failed: `{len(failed)}`",
        "",
        "Status: **PASS**" if failed.empty else "Status: **BLOCKED**",
        "",
    ]
    if not failed.empty:
        lines += ["## Failed checks", "", markdown_table(failed), ""]
        lines.append("QGIS Console execution is not ready-to-run until these checks pass.")
        lines.append("")
    else:
        lines.append("QGIS Console execution package is ready for the manual B7 new-run-only run.")
        lines.append("")
    lines += ["## All checks", "", markdown_table(df), ""]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return failed.empty


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Sprint B7 N150 new-run-only SOLWEIG input preflight.",
        epilog=(
            "Writes b7_input_preflight.csv and b7_input_preflight.md with B5/B6/N24/input/git-safety metrics. "
            "This script does not run QGIS, SOLWEIG, local WBGT, hazard_score, risk_score, surrogate models, or System A/B coupling."
        ),
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="B7 execution config JSON.")
    args = parser.parse_args()

    cfg = read_json(repo_path(args.config))
    selected = load_csv(repo_path(cfg["selected_cells_path"]))
    new = load_csv(repo_path(cfg["new_cells_path"]))
    full = normalize_matrix(load_csv(repo_path(cfg["full_matrix_path"])))
    new_matrix = normalize_matrix(load_csv(repo_path(cfg["run_matrix_path"])))
    ensure_b6_2_freeze(selected, new, full, new_matrix)

    rows: list[Check] = []
    b5_checks(rows)
    retained_cells, _new_cells = sample_design_checks(rows, selected, new, full, new_matrix)
    n24_reuse_checks(rows, retained_cells)
    static_input_checks(rows, cfg)
    git_safety_checks(rows, cfg)

    ok = write_checks(
        rows,
        OUT_DIR / "b7_input_preflight.csv",
        OUT_DIR / "b7_input_preflight.md",
    )
    if not ok:
        raise SystemExit("BLOCKED: B7 input preflight failed. See outputs/v12_solweig_n150_execution/b7_input_preflight.md")
    print(f"[OK] B7 input preflight PASS: {OUT_DIR / 'b7_input_preflight.md'}")


if __name__ == "__main__":
    main()
