"""Refresh the Sprint B7 N150 new-run-only SOLWEIG execution report.

Inputs:
  - configs/v12/v12_solweig_n150_execution_config.example.json
  - outputs/v12_solweig_n150_execution/b7_input_preflight.csv, if present.
  - outputs/v12_solweig_n150_execution/n150_new_solweig_run_log.csv, if present.
  - B7 aggregation, merge, validation, and QGIS algorithm-resolution outputs, if present.

Outputs:
  - outputs/v12_solweig_n150_execution/sprint_b7_n150_solweig_execution_report.md

Saved metrics:
  - preflight status, run-log status counts, completed-new count, catastrophic-stop flag.
  - new aggregation row counts, merged row counts, and B5 modifier target row counts.
  - QGIS/UMEP algorithm-resolution availability and git/raw-output safety note.

Run:
  C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\\v12_b7_n150_refresh_execution_report.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs/v12/v12_solweig_n150_execution_config.example.json"


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def count_rows(path: Path) -> int | None:
    if not path.exists():
        return None
    return int(len(pd.read_csv(path)))


def preflight_status(out_dir: Path) -> str:
    path = out_dir / "b7_input_preflight.csv"
    if not path.exists():
        return "MISSING"
    df = pd.read_csv(path)
    return "PASS" if not df.empty and df["status"].eq("PASS").all() else "BLOCKED"


def parse_algorithm_report(path: Path) -> str:
    if not path.exists():
        return "pending QGIS Console run"
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    selected = [line for line in text if "selected_algorithm_id" in line]
    return selected[0].strip("- ").strip() if selected else "algorithm report present"


def run_counts(log_path: Path) -> dict[str, int]:
    if not log_path.exists():
        return {
            "attempted": 0,
            "success": 0,
            "skipped_completed": 0,
            "failed_preprocess": 0,
            "failed_solweig": 0,
            "blocked": 0,
            "rows": 0,
        }
    log = pd.read_csv(log_path)
    status = log["status"].astype(str) if "status" in log.columns else pd.Series(dtype=str)
    success = int(status.eq("success").sum())
    skipped = int(status.eq("skipped_completed").sum())
    failed_pre = int(status.eq("failed_preprocess").sum())
    failed_sol = int(status.eq("failed_solweig").sum())
    blocked = int(status.isin(["blocked_environment", "blocked_algorithm_missing"]).sum())
    return {
        "attempted": success + failed_pre + failed_sol,
        "success": success,
        "skipped_completed": skipped,
        "failed_preprocess": failed_pre,
        "failed_solweig": failed_sol,
        "blocked": blocked,
        "rows": int(len(log)),
    }


def resolve_status(cfg: dict[str, Any], out_dir: Path, counts: dict[str, int]) -> str:
    preflight = preflight_status(out_dir)
    if preflight == "BLOCKED":
        return "BLOCKED"
    if preflight == "MISSING":
        return "PREPARED"
    log_exists = (out_dir / "n150_new_solweig_run_log.csv").exists()
    if not log_exists:
        return "READY_FOR_QGIS_CONSOLE_RUN"
    expected = int(cfg.get("expected_new_runs", 1260))
    completed_new = counts["success"] + counts["skipped_completed"]
    if counts["blocked"] > 0:
        return "BLOCKED"
    if completed_new == 0 and (counts["failed_preprocess"] + counts["failed_solweig"]) > 0:
        return "FAILED"
    if completed_new < expected or counts["failed_preprocess"] or counts["failed_solweig"]:
        return "PARTIAL"
    merge_validation = out_dir / "n150_merge_validation.csv"
    if not merge_validation.exists():
        return "PARTIAL"
    validation = pd.read_csv(merge_validation)
    return "PASS" if validation["status"].eq("PASS").all() else "PARTIAL"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh the Sprint B7 N150 SOLWEIG execution report from available preflight, QGIS, aggregation, and merge outputs.",
        epilog="Writes a Markdown status report. Does not run QGIS, SOLWEIG, local WBGT, hazard_score, risk_score, surrogate models, or System A/B coupling.",
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="B7 execution config JSON.")
    args = parser.parse_args()
    cfg = read_json(repo_path(args.config))
    out_dir = repo_path(cfg["summary_output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "n150_new_solweig_run_log.csv"
    counts = run_counts(log_path)
    status = resolve_status(cfg, out_dir, counts)
    expected = int(cfg.get("expected_new_runs", 1260))
    completed_new = counts["success"] + counts["skipped_completed"]
    catastrophic_stop = (out_dir / "n150_runtime_stop_report.md").exists()

    new_summary_rows = count_rows(out_dir / "n150_new_focus_tmrt_summary.csv")
    new_delta_rows = count_rows(out_dir / "n150_new_base_vs_overhead_delta.csv")
    merged_summary_rows = count_rows(out_dir / "n150_focus_tmrt_summary_merged.csv")
    merged_delta_rows = count_rows(out_dir / "n150_base_vs_overhead_delta_merged.csv")
    modifier_rows = count_rows(out_dir / "n150_modifier_targets_b5.csv")
    preflight = preflight_status(out_dir)
    algorithm = parse_algorithm_report(out_dir / "qgis_algorithm_resolution.md")
    preprocess_algorithm = parse_algorithm_report(out_dir / "qgis_preprocess_algorithm_resolution.md")

    lines = [
        "# Sprint B7 - N150 New-run-only SOLWEIG Execution",
        "",
        "## Status",
        status,
        "",
        "## Scope",
        "- N150 new-run-only SOLWEIG execution",
        "- N24 completed outputs reused",
        "- no N24 rerun",
        "- local raw rasters allowed but local-only",
        "- no local WBGT",
        "- no hazard_score",
        "- no risk_score",
        "- no surrogate",
        "- no System A/B coupling",
        "",
        "## B6/B6.1/B6.2 input",
        "- N150 = 24 retained N24 + 126 new.",
        "- no replacements after quick map QA.",
        "- selected cells unchanged.",
        "- new-run-only matrix rows = 1260.",
        f"- B7 input preflight status: `{preflight}`.",
        "",
        "## Execution environment",
        "- QGIS Desktop Python Console.",
        "- qgis_process not used.",
        f"- UMEP/SOLWEIG algorithm resolution: `{algorithm}`.",
        f"- UMEP preprocess algorithm resolution: `{preprocess_algorithm}`.",
        "",
        "## Run summary",
        f"- expected new runs = {expected}",
        f"- attempted = {counts['attempted']}",
        f"- success = {counts['success']}",
        f"- skipped_completed = {counts['skipped_completed']}",
        f"- failed_preprocess = {counts['failed_preprocess']}",
        f"- failed_solweig = {counts['failed_solweig']}",
        f"- blocked = {counts['blocked']}",
        f"- completed_new = {completed_new}",
        f"- catastrophic stop = {'yes' if catastrophic_stop else 'no'}",
        "",
        "## Aggregation summary",
        f"- new focus summary rows expected = 1260; observed = `{new_summary_rows if new_summary_rows is not None else 'missing'}`",
        f"- new delta rows expected = 630; observed = `{new_delta_rows if new_delta_rows is not None else 'missing'}`",
        f"- merged focus rows expected = 1500; observed = `{merged_summary_rows if merged_summary_rows is not None else 'missing'}`",
        f"- merged delta rows expected = 750; observed = `{merged_delta_rows if merged_delta_rows is not None else 'missing'}`",
        f"- B5 modifier target rows expected = 1500; observed = `{modifier_rows if modifier_rows is not None else 'missing'}`",
        "",
        "## Git safety",
        "- raw outputs under data/solweig/v12_n150_tiles are local-only",
        "- never stage/commit .tif, .tiff, svfs.zip, data/solweig, data/rasters",
        "",
        "## What this proves",
        "- N150 label execution/merge ready for B8 surrogate protocol if PASS",
        "",
        "## What this does not prove",
        "- no local WBGT",
        "- no risk",
        "- no final AOI-wide map",
        "- no surrogate validation",
        "- no observed truth",
        "",
        "## Next recommended action",
    ]
    if status == "PASS":
        lines.append("B8 - surrogate / emulator protocol and model comparison using N150 labels.")
    elif status == "PARTIAL":
        lines.append("Rerun failed new-run-only subset using resume.")
    elif status == "BLOCKED":
        lines.append("Fix QGIS/UMEP/preprocess environment.")
    elif status == "READY_FOR_QGIS_CONSOLE_RUN":
        lines.append("Run the B7 QGIS Desktop Python Console script, then aggregate, merge, and refresh this report.")
    else:
        lines.append("Inspect the B7 preflight/run log and resolve the failed step.")
    (out_dir / "sprint_b7_n150_solweig_execution_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] wrote {out_dir / 'sprint_b7_n150_solweig_execution_report.md'} status={status}")


if __name__ == "__main__":
    main()
