"""Sprint B4 N24 System B target robustness re-audit.

Inputs:
    - outputs/v12_solweig_n24_execution/sprint_b3_n24_solweig_execution_report.md
    - outputs/v12_solweig_n24_execution/b3_3_execution_completion_validation.md
    - outputs/v12_solweig_n24_execution/n24_solweig_run_log.csv
    - outputs/v12_solweig_n24_execution/n24_focus_tmrt_summary.csv
    - outputs/v12_solweig_n24_execution/n24_base_vs_overhead_delta.csv
    - outputs/v12_solweig_n24_execution/n24_modifier_targets_provisional.csv
    - outputs/v12_systemb_n24_sample_design/*.csv and B2.2 freeze report
    - outputs/v12_systemb_target_robustness/systemb_target_decision_matrix.csv
    - outputs/v12_systemb_target_robustness/systemb_target_robustness_report.md
    - selected docs/v12 System B protocol, companion metric, and taxonomy notes.

Outputs:
    - outputs/v12_systemb_n24_target_robustness/b4_input_validation.csv
    - outputs/v12_systemb_n24_target_robustness/b4_input_validation.md
    - outputs/v12_systemb_n24_target_robustness/n24_metric_availability_matrix.csv
    - outputs/v12_systemb_n24_target_robustness/n24_target_descriptive_stats.csv
    - outputs/v12_systemb_n24_target_robustness/n24_target_rank_correlation.csv
    - outputs/v12_systemb_n24_target_robustness/n24_target_topk_overlap.csv
    - outputs/v12_systemb_n24_target_robustness/n24_hour_stability_rank_correlation.csv
    - outputs/v12_systemb_n24_target_robustness/n24_hour_stability_topk_overlap.csv
    - outputs/v12_systemb_n24_target_robustness/n24_consistent_top_cells.csv
    - outputs/v12_systemb_n24_target_robustness/n24_tail_heterogeneity_diagnostics.csv
    - outputs/v12_systemb_n24_target_robustness/n24_base_vs_overhead_sensitivity_summary.csv
    - outputs/v12_systemb_n24_target_robustness/n24_overhead_cooling_by_cell.csv
    - outputs/v12_systemb_n24_target_robustness/n24_overhead_rank_shift.csv
    - outputs/v12_systemb_n24_target_robustness/n24_threshold_area_audit.csv
    - outputs/v12_systemb_n24_target_robustness/n24_replacement_cell_sanity.csv
    - outputs/v12_systemb_n24_target_robustness/n24_legacy_anchor_sanity.csv
    - outputs/v12_systemb_n24_target_robustness/n24_target_decision_matrix.csv
    - outputs/v12_systemb_n24_target_robustness/sprint_b4_n24_target_robustness_report.md
    - docs/v12/OpenHeat_SystemB_N24_target_robustness_reaudit_CN.md

Saved metrics:
    - Input validation status and B3/B2.2 coverage checks.
    - Metric availability, descriptive statistics, Spearman rank correlations,
      top-k overlap, cross-hour rank stability, consistent top cells, within-cell
      tail diagnostics, base-vs-overhead sensitivity, threshold-area companion
      audit, replacement/legacy sanity checks, and N24 target decision statuses.

Boundary:
    This script reads existing CSV/Markdown summaries only. It does not read
    .tif/.tiff files, raw rasters, or data/solweig raw outputs. It does not run
    SOLWEIG, QGIS, or qgis_process. It does not create local WBGT, hazard_score,
    risk_score, a surrogate/emulator, final maps, or System A/B coupling.

Run:
    C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\\v12_b4_n24_target_robustness_reaudit.py
"""

from __future__ import annotations

import argparse
import itertools
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path("outputs/v12_systemb_n24_target_robustness")
DOC_PATH = Path("docs/v12/OpenHeat_SystemB_N24_target_robustness_reaudit_CN.md")

B3_DIR = Path("outputs/v12_solweig_n24_execution")
B2_DIR = Path("outputs/v12_systemb_n24_sample_design")
B1_DIR = Path("outputs/v12_systemb_target_robustness")

B3_REPORT = B3_DIR / "sprint_b3_n24_solweig_execution_report.md"
B3_VALIDATION_MD = B3_DIR / "b3_3_execution_completion_validation.md"
RUN_LOG = B3_DIR / "n24_solweig_run_log.csv"
FOCUS_SUMMARY = B3_DIR / "n24_focus_tmrt_summary.csv"
DELTA_SUMMARY = B3_DIR / "n24_base_vs_overhead_delta.csv"
PROVISIONAL_MODIFIER = B3_DIR / "n24_modifier_targets_provisional.csv"
SELECTED_CELLS = B2_DIR / "n24_selected_cells_b2_2_human_qa_freeze.csv"
ROLE_COVERAGE = B2_DIR / "n24_diagnostic_role_coverage.csv"
TYPOLOGY_COVERAGE = B2_DIR / "n24_typology_coverage_matrix.csv"
B2_FREEZE_REPORT = B2_DIR / "sprint_b2_2_n24_human_qa_freeze_report.md"
B1_DECISION = B1_DIR / "systemb_target_decision_matrix.csv"
B1_REPORT = B1_DIR / "systemb_target_robustness_report.md"
PROTOCOL_DOCS = [
    Path("docs/v12/OpenHeat_SystemB_target_robustness_protocol_CN.md"),
    Path("docs/v12/OpenHeat_SystemB_N24_companion_metric_plan_CN.md"),
    Path("docs/v12/OpenHeat_SystemB_product_taxonomy_CN.md"),
]

EXPECTED_CELLS = 24
EXPECTED_ROWS = 240
EXPECTED_DELTA_ROWS = 120
EXPECTED_SCENARIOS = ["base", "overhead_as_canopy"]
EXPECTED_HOURS = [10, 12, 13, 15, 16]
REPLACEMENT_IN = ["TP_0141", "TP_0301", "TP_0773", "TP_0676", "TP_0575"]
REPLACED_OUT = ["TP_0058", "TP_0828", "TP_0802", "TP_0675", "TP_0916"]
LEGACY_ANCHORS = ["TP_0565", "TP_0986", "TP_0088", "TP_0433", "TP_0575"]
LEGACY_EXPECTATIONS = {
    "TP_0565": "hot anchor",
    "TP_0986": "hot anchor",
    "TP_0088": "shaded reference",
    "TP_0433": "overhead diagnostic",
    "TP_0575": "TP_0916 replacement overhead diagnostic",
}

TARGET_METRICS = [
    "tmrt_mean_c",
    "tmrt_p50_c",
    "tmrt_p75_c",
    "tmrt_p90_c",
    "tmrt_p95_c",
    "tmrt_max_c",
    "pct_pixels_tmrt_ge_40",
    "pct_pixels_tmrt_ge_45",
    "pct_pixels_tmrt_ge_50",
    "pct_pixels_tmrt_ge_55",
]
HOUR_STABILITY_METRICS = [
    "tmrt_mean_c",
    "tmrt_p75_c",
    "tmrt_p90_c",
    "tmrt_p95_c",
    "tmrt_max_c",
    "pct_pixels_tmrt_ge_50",
    "pct_pixels_tmrt_ge_55",
]
DECISION_METRICS = [
    "tmrt_mean_c",
    "tmrt_p75_c",
    "tmrt_p90_c",
    "tmrt_p95_c",
    "tmrt_max_c",
    "pct_pixels_tmrt_ge_40",
    "pct_pixels_tmrt_ge_45",
    "pct_pixels_tmrt_ge_50",
    "pct_pixels_tmrt_ge_55",
    "delta_tmrt_p90_c",
    "m_rad_pct_provisional",
]
DELTA_ALIASES = {
    "delta_tmrt_mean_c": ["delta_tmrt_mean_c"],
    "delta_tmrt_p75_c": ["delta_tmrt_p75_c"],
    "delta_tmrt_p90_c": ["delta_tmrt_p90_c"],
    "delta_tmrt_p95_c": ["delta_tmrt_p95_c"],
    "delta_tmrt_max_c": ["delta_tmrt_max_c"],
    "delta_pct_pixels_ge_40": ["delta_pct_pixels_ge_40", "delta_pct_pixels_tmrt_ge_40"],
    "delta_pct_pixels_ge_45": ["delta_pct_pixels_ge_45", "delta_pct_pixels_tmrt_ge_45"],
    "delta_pct_pixels_ge_50": ["delta_pct_pixels_ge_50", "delta_pct_pixels_tmrt_ge_50"],
    "delta_pct_pixels_ge_55": ["delta_pct_pixels_ge_55", "delta_pct_pixels_tmrt_ge_55"],
}
RANK_SHIFT_METRICS = [
    "tmrt_mean_c",
    "tmrt_p75_c",
    "tmrt_p90_c",
    "tmrt_p95_c",
    "tmrt_max_c",
    "pct_pixels_tmrt_ge_50",
    "pct_pixels_tmrt_ge_55",
]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Re-audit N24 SOLWEIG-derived System B target robustness using "
            "completed B3 summary CSV/MD outputs only. Writes machine-readable "
            "diagnostics and Markdown reports. Does not read rasters, run QGIS, "
            "run SOLWEIG, compute local WBGT/hazard/risk, train surrogates, or "
            "perform System A/B coupling."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT, help="Repository root.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for B4 target robustness outputs.",
    )
    parser.add_argument(
        "--design-doc",
        type=Path,
        default=DOC_PATH,
        help="Chinese design/findings note path.",
    )
    return parser.parse_args()


def repo_path(root: Path, path: Path) -> Path:
    """Resolve a repository-relative path."""
    return path if path.is_absolute() else root / path


def rel(path: Path, root: Path) -> str:
    """Return a stable repository-relative path for reports."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def read_text(path: Path) -> str:
    """Read UTF-8 text with a tolerant fallback for legacy console output."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig", errors="replace")


def markdown_status_is_pass(text: str) -> bool:
    """Detect a PASS status in a Markdown report."""
    normalized = text.lower()
    return bool(
        re.search(r"status\s*:\s*\**pass\**", normalized)
        or re.search(r"##\s*status\s+pass\b", normalized)
        or re.search(r"##\s*status\s*\n+\s*pass\b", normalized)
    )


def add_check(
    rows: list[dict[str, Any]],
    section: str,
    check: str,
    ok: bool,
    observed: Any,
    expected: Any,
    note: str = "",
    warn: bool = False,
) -> None:
    """Append a validation row."""
    status = "PASS" if ok else ("WARN" if warn else "FAIL")
    rows.append(
        {
            "section": section,
            "check": check,
            "status": status,
            "observed": observed,
            "expected": expected,
            "note": note,
        }
    )


def write_validation_md(validation: pd.DataFrame, output_dir: Path, blocked: bool) -> None:
    """Write validation Markdown summary."""
    status = "BLOCKED" if blocked else "PASS"
    counts = validation["status"].value_counts().to_dict() if not validation.empty else {}
    lines = [
        "# Sprint B4 Input Validation",
        "",
        f"Status: **{status}**",
        "",
        "This validation read existing CSV/Markdown summaries only. It did not rerun SOLWEIG, QGIS, qgis_process, read rasters, compute local WBGT, compute hazard_score/risk_score, train a surrogate, or perform System A/B coupling.",
        "",
        "## Summary",
        "",
    ]
    for key in ["PASS", "WARN", "FAIL"]:
        lines.append(f"- {key}: `{counts.get(key, 0)}`")
    lines.extend(["", "## Checks", ""])
    if validation.empty:
        lines.append("_No validation rows were produced._")
    else:
        lines.append(validation.to_markdown(index=False))
    (output_dir / "b4_input_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_inputs(root: Path, output_dir: Path) -> tuple[bool, dict[str, pd.DataFrame]]:
    """Validate required B4 inputs and return loaded data frames if safe."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    data: dict[str, pd.DataFrame] = {}

    required_files = [
        B3_REPORT,
        B3_VALIDATION_MD,
        RUN_LOG,
        FOCUS_SUMMARY,
        DELTA_SUMMARY,
        SELECTED_CELLS,
        ROLE_COVERAGE,
        TYPOLOGY_COVERAGE,
        B2_FREEZE_REPORT,
        B1_DECISION,
        B1_REPORT,
        *PROTOCOL_DOCS,
    ]
    for path in required_files:
        full = repo_path(root, path)
        add_check(rows, "files", rel(path, root), full.exists(), full.exists(), True)

    if repo_path(root, PROVISIONAL_MODIFIER).exists():
        add_check(rows, "files", rel(PROVISIONAL_MODIFIER, root), True, True, True)
    else:
        add_check(
            rows,
            "files",
            rel(PROVISIONAL_MODIFIER, root),
            False,
            False,
            "present if available",
            "Optional provisional modifier missing; target interpretation can continue without m_rad_pct.",
            warn=True,
        )

    if not repo_path(root, B3_REPORT).exists() or not repo_path(root, B3_VALIDATION_MD).exists():
        validation = pd.DataFrame(rows)
        validation.to_csv(output_dir / "b4_input_validation.csv", index=False)
        write_validation_md(validation, output_dir, blocked=True)
        return False, data

    b3_report_pass = markdown_status_is_pass(read_text(repo_path(root, B3_REPORT)))
    b3_validation_pass = markdown_status_is_pass(read_text(repo_path(root, B3_VALIDATION_MD)))
    add_check(rows, "b3_report", "status_pass", b3_report_pass, b3_report_pass, True)
    add_check(rows, "b3_validation", "status_pass", b3_validation_pass, b3_validation_pass, True)

    csv_paths = {
        "run_log": RUN_LOG,
        "focus": FOCUS_SUMMARY,
        "delta": DELTA_SUMMARY,
        "selected": SELECTED_CELLS,
    }
    if repo_path(root, PROVISIONAL_MODIFIER).exists():
        csv_paths["modifier"] = PROVISIONAL_MODIFIER
    for key, path in csv_paths.items():
        full = repo_path(root, path)
        if full.exists():
            data[key] = pd.read_csv(full)

    focus = data.get("focus", pd.DataFrame())
    delta = data.get("delta", pd.DataFrame())
    modifier = data.get("modifier", pd.DataFrame())
    selected = data.get("selected", pd.DataFrame())

    add_check(rows, "focus_tmrt_summary", "rows", len(focus) == EXPECTED_ROWS, len(focus), EXPECTED_ROWS)
    add_check(
        rows,
        "base_vs_overhead_delta",
        "rows",
        len(delta) == EXPECTED_DELTA_ROWS,
        len(delta),
        EXPECTED_DELTA_ROWS,
    )
    if "modifier" in data:
        add_check(
            rows,
            "provisional_modifier",
            "rows",
            len(modifier) == EXPECTED_ROWS,
            len(modifier),
            EXPECTED_ROWS,
            "N24-internal only; not final AOI-wide M_rad_pct.",
        )

    if not focus.empty:
        focus["cell_id"] = focus["cell_id"].astype(str)
        scenario_values = sorted(focus["scenario"].dropna().astype(str).unique().tolist())
        hour_values = sorted(pd.to_numeric(focus["hour"], errors="coerce").dropna().astype(int).unique().tolist())
        cell_values = sorted(focus["cell_id"].dropna().unique().tolist())
        add_check(rows, "focus_tmrt_summary", "unique_cells", len(cell_values) == EXPECTED_CELLS, len(cell_values), EXPECTED_CELLS)
        add_check(rows, "focus_tmrt_summary", "scenarios", scenario_values == EXPECTED_SCENARIOS, ", ".join(scenario_values), ", ".join(EXPECTED_SCENARIOS))
        add_check(rows, "focus_tmrt_summary", "hours", hour_values == EXPECTED_HOURS, ", ".join(map(str, hour_values)), ", ".join(map(str, EXPECTED_HOURS)))
        missing_metrics = [m for m in TARGET_METRICS if m not in focus.columns]
        add_check(rows, "focus_tmrt_summary", "required_metric_columns", not missing_metrics, ", ".join(missing_metrics) if missing_metrics else "present", "all required metrics")
        if "valid_pixel_count" in focus.columns:
            valid_complete = focus["valid_pixel_count"].notna().all()
            expected_complete = len(focus)
            observed_complete = int(focus["valid_pixel_count"].notna().sum())
            add_check(rows, "focus_tmrt_summary", "valid_pixel_count_complete", valid_complete, observed_complete, expected_complete)
        else:
            add_check(rows, "focus_tmrt_summary", "valid_pixel_count_complete", True, "column absent", "complete if column exists", warn=True)
        add_check(rows, "focus_tmrt_summary", "replacement_in_cells_present", all(c in cell_values for c in REPLACEMENT_IN), ", ".join([c for c in REPLACEMENT_IN if c in cell_values]), ", ".join(REPLACEMENT_IN))
        add_check(rows, "focus_tmrt_summary", "replaced_out_cells_absent", all(c not in cell_values for c in REPLACED_OUT), ", ".join([c for c in REPLACED_OUT if c in cell_values]) or "none", "none")
    if not delta.empty:
        add_check(rows, "base_vs_overhead_delta", "unique_cells", delta["cell_id"].astype(str).nunique() == EXPECTED_CELLS, delta["cell_id"].astype(str).nunique(), EXPECTED_CELLS)
        add_check(rows, "base_vs_overhead_delta", "hours", sorted(pd.to_numeric(delta["hour"], errors="coerce").dropna().astype(int).unique().tolist()) == EXPECTED_HOURS, ", ".join(map(str, sorted(pd.to_numeric(delta["hour"], errors="coerce").dropna().astype(int).unique().tolist()))), ", ".join(map(str, EXPECTED_HOURS)))
        missing_delta = [canonical for canonical, aliases in DELTA_ALIASES.items() if not any(a in delta.columns for a in aliases)]
        add_check(rows, "base_vs_overhead_delta", "delta_metric_columns", not missing_delta, ", ".join(missing_delta) if missing_delta else "present", "all required delta aliases")
    if not selected.empty:
        selected_cells = selected["cell_id"].astype(str).tolist() if "cell_id" in selected.columns else []
        add_check(rows, "b2_2_selected_cells", "unique_cells", len(set(selected_cells)) == EXPECTED_CELLS, len(set(selected_cells)), EXPECTED_CELLS)
        add_check(rows, "b2_2_selected_cells", "replacement_in_cells_present", all(c in selected_cells for c in REPLACEMENT_IN), ", ".join([c for c in REPLACEMENT_IN if c in selected_cells]), ", ".join(REPLACEMENT_IN))
        add_check(rows, "b2_2_selected_cells", "replaced_out_cells_absent", all(c not in selected_cells for c in REPLACED_OUT), ", ".join([c for c in REPLACED_OUT if c in selected_cells]) or "none", "none")

    validation = pd.DataFrame(rows)
    validation.to_csv(output_dir / "b4_input_validation.csv", index=False)
    blocked = validation["status"].eq("FAIL").any()
    write_validation_md(validation, output_dir, blocked)
    return not blocked, data


def numeric_summary(series: pd.Series) -> dict[str, Any]:
    """Return descriptive statistics for one numeric series."""
    values = pd.to_numeric(series, errors="coerce")
    clean = values.dropna()
    if clean.empty:
        return {
            "n_cells": 0,
            "mean": math.nan,
            "median": math.nan,
            "std": math.nan,
            "min": math.nan,
            "p25": math.nan,
            "p75": math.nan,
            "max": math.nan,
            "missing_count": int(values.isna().sum()),
        }
    return {
        "n_cells": int(clean.count()),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "std": float(clean.std(ddof=1)) if clean.count() > 1 else 0.0,
        "min": float(clean.min()),
        "p25": float(clean.quantile(0.25)),
        "p75": float(clean.quantile(0.75)),
        "max": float(clean.max()),
        "missing_count": int(values.isna().sum()),
    }


def spearman(df: pd.DataFrame, a: str, b: str) -> tuple[float, int]:
    """Compute Spearman rank correlation without scipy."""
    sub = df[[a, b]].apply(pd.to_numeric, errors="coerce").dropna()
    n = len(sub)
    if n < 2 or sub[a].nunique() < 2 or sub[b].nunique() < 2:
        return math.nan, n
    return float(sub[a].corr(sub[b], method="spearman")), n


def top_cells(df: pd.DataFrame, metric: str, top_k: int) -> list[str]:
    """Return top-k cell ids for a metric, ranked descending."""
    sub = df[["cell_id", metric]].copy()
    sub[metric] = pd.to_numeric(sub[metric], errors="coerce")
    sub = sub.dropna().sort_values([metric, "cell_id"], ascending=[False, True])
    return sub.head(top_k)["cell_id"].astype(str).tolist()


def topk_overlap(cells_a: list[str], cells_b: list[str]) -> tuple[int, float]:
    """Return count and Jaccard overlap for two cell lists."""
    set_a = set(cells_a)
    set_b = set(cells_b)
    if not set_a and not set_b:
        return 0, math.nan
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter, float(inter / union) if union else math.nan


def metric_availability_and_stats(focus: pd.DataFrame, output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Write metric availability matrix and descriptive stats."""
    avail_rows: list[dict[str, Any]] = []
    stats_rows: list[dict[str, Any]] = []
    for scenario, hour, metric in itertools.product(EXPECTED_SCENARIOS, EXPECTED_HOURS, TARGET_METRICS):
        subset = focus[(focus["scenario"].eq(scenario)) & (focus["hour"].eq(hour))]
        present = metric in focus.columns
        values = pd.to_numeric(subset[metric], errors="coerce") if present else pd.Series(dtype=float)
        non_missing = int(values.notna().sum()) if present else 0
        missing = int(len(subset) - non_missing)
        avail_rows.append(
            {
                "scenario": scenario,
                "hour": hour,
                "metric": metric,
                "metric_present": present,
                "n_rows": int(len(subset)),
                "n_cells": int(subset["cell_id"].nunique()) if not subset.empty else 0,
                "non_missing_count": non_missing,
                "missing_count": missing,
                "availability_status": "available" if present and non_missing == len(subset) and len(subset) else "missing_or_incomplete",
            }
        )
        summary = numeric_summary(values if present else pd.Series([math.nan] * len(subset)))
        stats_rows.append({"scenario": scenario, "hour": hour, "metric": metric, **summary})
    availability = pd.DataFrame(avail_rows)
    stats = pd.DataFrame(stats_rows)
    availability.to_csv(output_dir / "n24_metric_availability_matrix.csv", index=False)
    stats.to_csv(output_dir / "n24_target_descriptive_stats.csv", index=False)
    return availability, stats


def rank_correlation_audit(focus: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    """Write pairwise metric Spearman rank correlations."""
    rows: list[dict[str, Any]] = []
    available = [m for m in TARGET_METRICS if m in focus.columns]
    for scenario, hour in itertools.product(EXPECTED_SCENARIOS, EXPECTED_HOURS):
        subset = focus[(focus["scenario"].eq(scenario)) & (focus["hour"].eq(hour))]
        for metric_a, metric_b in itertools.combinations(available, 2):
            rho, n = spearman(subset, metric_a, metric_b)
            emphasis = (
                metric_a == "tmrt_p90_c"
                or metric_b == "tmrt_p90_c"
                or {metric_a, metric_b} in [
                    {"tmrt_mean_c", "pct_pixels_tmrt_ge_40"},
                    {"tmrt_mean_c", "pct_pixels_tmrt_ge_45"},
                    {"tmrt_mean_c", "pct_pixels_tmrt_ge_50"},
                    {"tmrt_mean_c", "pct_pixels_tmrt_ge_55"},
                ]
            )
            rows.append(
                {
                    "scenario": scenario,
                    "hour": hour,
                    "metric_a": metric_a,
                    "metric_b": metric_b,
                    "spearman_r": rho,
                    "n_cells": n,
                    "emphasis_pair": emphasis,
                }
            )
    result = pd.DataFrame(rows)
    result.to_csv(output_dir / "n24_target_rank_correlation.csv", index=False)
    return result


def target_topk_overlap(focus: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    """Write pairwise top-k overlap diagnostics."""
    rows: list[dict[str, Any]] = []
    available = [m for m in TARGET_METRICS if m in focus.columns]
    emphasis_pairs = {
        tuple(sorted(pair))
        for pair in [
            ("tmrt_p90_c", "tmrt_p75_c"),
            ("tmrt_p90_c", "tmrt_p95_c"),
            ("tmrt_p90_c", "tmrt_max_c"),
            ("tmrt_p90_c", "pct_pixels_tmrt_ge_50"),
            ("tmrt_p90_c", "pct_pixels_tmrt_ge_55"),
            ("tmrt_p90_c", "tmrt_mean_c"),
        ]
    }
    for scenario, hour in itertools.product(EXPECTED_SCENARIOS, EXPECTED_HOURS):
        subset = focus[(focus["scenario"].eq(scenario)) & (focus["hour"].eq(hour))]
        for metric_a, metric_b in itertools.combinations(available, 2):
            for top_k in [6, 3]:
                cells_a = top_cells(subset, metric_a, top_k)
                cells_b = top_cells(subset, metric_b, top_k)
                count, jaccard = topk_overlap(cells_a, cells_b)
                rows.append(
                    {
                        "scenario": scenario,
                        "hour": hour,
                        "metric_a": metric_a,
                        "metric_b": metric_b,
                        "top_k": top_k,
                        "top_cells_metric_a": ";".join(cells_a),
                        "top_cells_metric_b": ";".join(cells_b),
                        "overlap_count": count,
                        "jaccard_overlap": jaccard,
                        "emphasis_pair": tuple(sorted((metric_a, metric_b))) in emphasis_pairs,
                    }
                )
    result = pd.DataFrame(rows)
    result.to_csv(output_dir / "n24_target_topk_overlap.csv", index=False)
    return result


def hour_stability_audit(focus: pd.DataFrame, output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Write cross-hour rank correlation, top-k overlap, and consistent top cells."""
    rank_rows: list[dict[str, Any]] = []
    topk_rows: list[dict[str, Any]] = []
    consistent_rows: list[dict[str, Any]] = []
    for scenario, metric in itertools.product(EXPECTED_SCENARIOS, HOUR_STABILITY_METRICS):
        scenario_df = focus[focus["scenario"].eq(scenario)]
        if metric not in scenario_df.columns:
            continue
        for hour_a, hour_b in itertools.combinations(EXPECTED_HOURS, 2):
            a = scenario_df[scenario_df["hour"].eq(hour_a)][["cell_id", metric]].rename(columns={metric: "metric_hour_a"})
            b = scenario_df[scenario_df["hour"].eq(hour_b)][["cell_id", metric]].rename(columns={metric: "metric_hour_b"})
            merged = a.merge(b, on="cell_id", how="inner")
            rho, n = spearman(merged, "metric_hour_a", "metric_hour_b")
            rank_rows.append(
                {
                    "scenario": scenario,
                    "metric": metric,
                    "hour_a": hour_a,
                    "hour_b": hour_b,
                    "spearman_r": rho,
                    "n_cells": n,
                }
            )
            for top_k in [6, 3]:
                cells_a = top_cells(scenario_df[scenario_df["hour"].eq(hour_a)], metric, top_k)
                cells_b = top_cells(scenario_df[scenario_df["hour"].eq(hour_b)], metric, top_k)
                count, jaccard = topk_overlap(cells_a, cells_b)
                topk_rows.append(
                    {
                        "scenario": scenario,
                        "metric": metric,
                        "hour_a": hour_a,
                        "hour_b": hour_b,
                        "top_k": top_k,
                        "top_cells_hour_a": ";".join(cells_a),
                        "top_cells_hour_b": ";".join(cells_b),
                        "overlap_count": count,
                        "jaccard_overlap": jaccard,
                    }
                )
        for top_k in [6, 3]:
            appearances: dict[str, list[int]] = {}
            for hour in EXPECTED_HOURS:
                for cell in top_cells(scenario_df[scenario_df["hour"].eq(hour)], metric, top_k):
                    appearances.setdefault(cell, []).append(hour)
            for cell, hours in sorted(appearances.items()):
                if len(hours) >= 3:
                    consistent_rows.append(
                        {
                            "scenario": scenario,
                            "metric": metric,
                            "top_k": top_k,
                            "cell_id": cell,
                            "n_hours_in_top_k": len(hours),
                            "hours_in_top_k": ";".join(map(str, hours)),
                            "consistent_top_cell_rule": "appears in top-k for at least 3 of 5 hours",
                        }
                    )
    rank_df = pd.DataFrame(rank_rows)
    topk_df = pd.DataFrame(topk_rows)
    consistent_df = pd.DataFrame(consistent_rows)
    rank_df.to_csv(output_dir / "n24_hour_stability_rank_correlation.csv", index=False)
    topk_df.to_csv(output_dir / "n24_hour_stability_topk_overlap.csv", index=False)
    consistent_df.to_csv(output_dir / "n24_consistent_top_cells.csv", index=False)
    return rank_df, topk_df, consistent_df


def classify_tail(row: pd.Series) -> str:
    """Classify per-cell tail shape using transparent heuristic rules."""
    p90_mean = float(row.get("mean_p90_minus_mean", math.nan))
    p95_p90 = float(row.get("mean_p95_minus_p90", math.nan))
    max_p95 = float(row.get("mean_max_minus_p95", math.nan))
    pct50 = float(row.get("mean_pct_ge_50", math.nan))
    pct55 = float(row.get("mean_pct_ge_55", math.nan))
    if any(math.isnan(v) for v in [p90_mean, p95_p90, max_p95, pct50, pct55]):
        return "uncertain"
    if pct50 >= 60 and p90_mean <= 4:
        return "uniform_hot"
    if pct50 >= 35 or pct55 >= 10:
        return "threshold_area_hot"
    if p90_mean >= 5 and max_p95 < 4:
        return "mixed_cell_upper_tail"
    if max_p95 >= 4 and pct55 < 5:
        return "max_only_extreme"
    if pct50 < 5 and pct55 < 1 and p90_mean < 4:
        return "mostly_shaded_low_tail"
    return "uncertain"


def tail_heterogeneity_audit(focus: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    """Write within-cell tail heterogeneity diagnostics."""
    df = focus.copy()
    df["p90_minus_mean"] = pd.to_numeric(df["tmrt_p90_c"], errors="coerce") - pd.to_numeric(df["tmrt_mean_c"], errors="coerce")
    df["p95_minus_p90"] = pd.to_numeric(df["tmrt_p95_c"], errors="coerce") - pd.to_numeric(df["tmrt_p90_c"], errors="coerce")
    df["max_minus_p95"] = pd.to_numeric(df["tmrt_max_c"], errors="coerce") - pd.to_numeric(df["tmrt_p95_c"], errors="coerce")
    df["high_tail_area_50"] = pd.to_numeric(df["pct_pixels_tmrt_ge_50"], errors="coerce")
    df["high_tail_area_55"] = pd.to_numeric(df["pct_pixels_tmrt_ge_55"], errors="coerce")
    grouped = (
        df.groupby(["cell_id", "scenario"], as_index=False)
        .agg(
            mean_p90_minus_mean=("p90_minus_mean", "mean"),
            max_p90_minus_mean=("p90_minus_mean", "max"),
            mean_p95_minus_p90=("p95_minus_p90", "mean"),
            mean_max_minus_p95=("max_minus_p95", "mean"),
            mean_pct_ge_50=("high_tail_area_50", "mean"),
            mean_pct_ge_55=("high_tail_area_55", "mean"),
        )
        .sort_values(["scenario", "cell_id"])
    )
    grouped["tail_class"] = grouped.apply(classify_tail, axis=1)
    grouped["tail_class_rule"] = (
        "uniform_hot: pct_ge_50>=60 and p90-mean<=4; threshold_area_hot: pct_ge_50>=35 or pct_ge_55>=10; "
        "mixed_cell_upper_tail: p90-mean>=5 and max-p95<4; max_only_extreme: max-p95>=4 and pct_ge_55<5; "
        "mostly_shaded_low_tail: pct_ge_50<5, pct_ge_55<1, p90-mean<4; otherwise uncertain"
    )
    grouped.to_csv(output_dir / "n24_tail_heterogeneity_diagnostics.csv", index=False)
    return grouped


def normalize_delta_columns(delta: pd.DataFrame) -> pd.DataFrame:
    """Copy supported delta aliases into canonical B4 column names."""
    df = delta.copy()
    for canonical, aliases in DELTA_ALIASES.items():
        if canonical in df.columns:
            continue
        for alias in aliases:
            if alias in df.columns:
                df[canonical] = df[alias]
                break
    return df


def overhead_sensitivity_audit(delta: pd.DataFrame, output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Write base-vs-overhead sensitivity outputs."""
    df = normalize_delta_columns(delta)
    delta_metrics = list(DELTA_ALIASES.keys())
    summary_rows: list[dict[str, Any]] = []
    for metric in delta_metrics:
        if metric not in df.columns:
            continue
        values = pd.to_numeric(df[metric], errors="coerce")
        summary_rows.append(
            {
                "metric": metric,
                "n_rows": int(values.notna().sum()),
                "mean_delta": float(values.mean()),
                "median_delta": float(values.median()),
                "min_delta": float(values.min()),
                "max_delta": float(values.max()),
                "count_hours_cooled": int((values < -0.01).sum()),
                "count_hours_unchanged": int((values.abs() <= 0.01).sum()),
                "count_hours_warmed": int((values > 0.01).sum()),
                "interpretation_note": "overhead_as_canopy minus base; sensitivity scenario, not absolute truth",
            }
        )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(output_dir / "n24_base_vs_overhead_sensitivity_summary.csv", index=False)

    cell_rows: list[dict[str, Any]] = []
    for cell_id, cell_df in df.groupby("cell_id"):
        row: dict[str, Any] = {"cell_id": cell_id}
        for metric in delta_metrics:
            if metric not in cell_df.columns:
                continue
            values = pd.to_numeric(cell_df[metric], errors="coerce")
            row[f"{metric}_mean_delta"] = float(values.mean())
            row[f"{metric}_min_delta"] = float(values.min())
            row[f"{metric}_max_delta"] = float(values.max())
            row[f"{metric}_hours_cooled"] = int((values < -0.01).sum())
            row[f"{metric}_hours_unchanged"] = int((values.abs() <= 0.01).sum())
            row[f"{metric}_hours_warmed"] = int((values > 0.01).sum())
        if "delta_tmrt_p90_c" in cell_df.columns:
            p90_values = pd.to_numeric(cell_df["delta_tmrt_p90_c"], errors="coerce")
            min_idx = p90_values.idxmin()
            row["strongest_cooling_hour_by_p90"] = int(cell_df.loc[min_idx, "hour"]) if pd.notna(min_idx) else ""
            row["strongest_p90_cooling_delta"] = float(p90_values.min())
        mean_abs = abs(row.get("delta_tmrt_mean_c_mean_delta", math.nan))
        p90_abs = abs(row.get("delta_tmrt_p90_c_mean_delta", math.nan))
        row["overhead_affects_mean_more_than_p90"] = bool(mean_abs > p90_abs) if not math.isnan(mean_abs) and not math.isnan(p90_abs) else ""
        ge50_mean = row.get("delta_pct_pixels_ge_50_mean_delta", math.nan)
        ge55_mean = row.get("delta_pct_pixels_ge_55_mean_delta", math.nan)
        row["overhead_reduces_threshold_area_substantially"] = bool(
            (not math.isnan(ge50_mean) and ge50_mean <= -10) or (not math.isnan(ge55_mean) and ge55_mean <= -5)
        )
        row["scenario_boundary"] = "overhead_as_canopy is sensitivity, not absolute truth"
        cell_rows.append(row)
    cooling = pd.DataFrame(cell_rows).sort_values("delta_tmrt_p90_c_mean_delta" if cell_rows else "cell_id")
    cooling.to_csv(output_dir / "n24_overhead_cooling_by_cell.csv", index=False)

    rank_rows: list[dict[str, Any]] = []
    for hour, hour_df in df.groupby("hour"):
        for metric in RANK_SHIFT_METRICS:
            base_col = f"{metric}_base"
            over_col = f"{metric}_overhead_as_canopy"
            if base_col not in hour_df.columns or over_col not in hour_df.columns:
                continue
            ranks = hour_df[["cell_id", base_col, over_col]].copy()
            ranks["base_rank"] = pd.to_numeric(ranks[base_col], errors="coerce").rank(ascending=False, method="min")
            ranks["overhead_rank"] = pd.to_numeric(ranks[over_col], errors="coerce").rank(ascending=False, method="min")
            ranks["rank_delta"] = ranks["overhead_rank"] - ranks["base_rank"]
            for _, row in ranks.iterrows():
                rank_rows.append(
                    {
                        "hour": int(hour),
                        "metric": metric,
                        "cell_id": row["cell_id"],
                        "base_value": row[base_col],
                        "overhead_value": row[over_col],
                        "base_rank": int(row["base_rank"]) if pd.notna(row["base_rank"]) else "",
                        "overhead_rank": int(row["overhead_rank"]) if pd.notna(row["overhead_rank"]) else "",
                        "rank_delta": float(row["rank_delta"]) if pd.notna(row["rank_delta"]) else math.nan,
                        "abs_rank_delta": abs(float(row["rank_delta"])) if pd.notna(row["rank_delta"]) else math.nan,
                    }
                )
    rank_shift = pd.DataFrame(rank_rows)
    if not rank_shift.empty:
        rank_shift = rank_shift.merge(
            rank_shift.groupby(["cell_id", "metric"], as_index=False)
            .agg(cell_metric_mean_abs_rank_delta=("abs_rank_delta", "mean"), cell_metric_max_abs_rank_delta=("abs_rank_delta", "max")),
            on=["cell_id", "metric"],
            how="left",
        ).sort_values(["metric", "hour", "base_rank", "cell_id"])
    rank_shift.to_csv(output_dir / "n24_overhead_rank_shift.csv", index=False)
    return summary, cooling, rank_shift


def threshold_area_audit(
    focus: pd.DataFrame,
    rank_corr: pd.DataFrame,
    topk: pd.DataFrame,
    output_dir: Path,
) -> pd.DataFrame:
    """Write threshold-area metric audit."""
    rows: list[dict[str, Any]] = []
    threshold_metrics = [
        "pct_pixels_tmrt_ge_40",
        "pct_pixels_tmrt_ge_45",
        "pct_pixels_tmrt_ge_50",
        "pct_pixels_tmrt_ge_55",
    ]
    for scenario, hour, metric in itertools.product(EXPECTED_SCENARIOS, EXPECTED_HOURS, threshold_metrics):
        subset = focus[(focus["scenario"].eq(scenario)) & (focus["hour"].eq(hour))]
        stats = numeric_summary(subset[metric])
        corr_row = rank_corr[
            (rank_corr["scenario"].eq(scenario))
            & (rank_corr["hour"].eq(hour))
            & (
                ((rank_corr["metric_a"].eq("tmrt_p90_c")) & (rank_corr["metric_b"].eq(metric)))
                | ((rank_corr["metric_b"].eq("tmrt_p90_c")) & (rank_corr["metric_a"].eq(metric)))
            )
        ]
        top_row = topk[
            (topk["scenario"].eq(scenario))
            & (topk["hour"].eq(hour))
            & (topk["top_k"].eq(6))
            & (
                ((topk["metric_a"].eq("tmrt_p90_c")) & (topk["metric_b"].eq(metric)))
                | ((topk["metric_b"].eq("tmrt_p90_c")) & (topk["metric_a"].eq(metric)))
            )
        ]
        p90_top6 = set(top_cells(subset, "tmrt_p90_c", 6))
        metric_top6 = set(top_cells(subset, metric, 6))
        median_area = pd.to_numeric(subset[metric], errors="coerce").median()
        p90_ranks = pd.to_numeric(subset["tmrt_p90_c"], errors="coerce").rank(ascending=False, method="min")
        area_ranks = pd.to_numeric(subset[metric], errors="coerce").rank(ascending=False, method="min")
        temp = subset[["cell_id", "tmrt_p90_c", metric]].copy()
        temp["p90_rank"] = p90_ranks
        temp["area_rank"] = area_ranks
        high_p90_low_area = temp[(temp["cell_id"].isin(p90_top6)) & (pd.to_numeric(temp[metric], errors="coerce") <= median_area)]["cell_id"].astype(str).tolist()
        moderate_p90_high_area = temp[(temp["p90_rank"].between(7, 12)) & (temp["cell_id"].isin(metric_top6))]["cell_id"].astype(str).tolist()
        rho = float(corr_row["spearman_r"].iloc[0]) if not corr_row.empty and pd.notna(corr_row["spearman_r"].iloc[0]) else math.nan
        jac = float(top_row["jaccard_overlap"].iloc[0]) if not top_row.empty and pd.notna(top_row["jaccard_overlap"].iloc[0]) else math.nan
        if not math.isnan(rho) and not math.isnan(jac) and rho >= 0.85 and jac >= 0.60:
            recommendation = "required_companion"
        elif not math.isnan(rho) and (
            rho >= 0.85 or (rho >= 0.65 and not math.isnan(jac) and jac >= 0.40)
        ):
            recommendation = "optional_companion"
        elif not math.isnan(rho) and rho >= 0.40:
            recommendation = "sensitivity_only"
        else:
            recommendation = "not_useful"
        rows.append(
            {
                "scenario": scenario,
                "hour": hour,
                "threshold_metric": metric,
                **stats,
                "spearman_with_tmrt_p90_c": rho,
                "top6_overlap_with_tmrt_p90_c": int(top_row["overlap_count"].iloc[0]) if not top_row.empty else "",
                "top6_jaccard_with_tmrt_p90_c": jac,
                "high_p90_low_area_cells": ";".join(high_p90_low_area),
                "moderate_p90_high_area_cells": ";".join(moderate_p90_high_area),
                "recommended_companion_status": recommendation,
                "assessment_rule": "required if p90 correlation>=0.85 and top6 Jaccard>=0.60; optional if corr>=0.85 or corr>=0.65 with top6 Jaccard>=0.40; sensitivity if corr>=0.40; otherwise not useful",
            }
        )
    result = pd.DataFrame(rows)
    result.to_csv(output_dir / "n24_threshold_area_audit.csv", index=False)
    return result


def selected_metadata(selected: pd.DataFrame) -> pd.DataFrame:
    """Return compact selected-cell metadata if available."""
    if selected.empty or "cell_id" not in selected.columns:
        return pd.DataFrame(columns=["cell_id"])
    cols = [
        c
        for c in [
            "cell_id",
            "primary_role",
            "secondary_roles",
            "typology_label",
            "replaced_cell_id",
            "replacement_cell_id",
            "human_qa_note",
        ]
        if c in selected.columns
    ]
    meta = selected[cols].copy()
    meta["cell_id"] = meta["cell_id"].astype(str)
    return meta


def sanity_rows_for_cells(
    cells: list[str],
    focus: pd.DataFrame,
    tails: pd.DataFrame,
    cooling: pd.DataFrame,
    selected: pd.DataFrame,
    kind: str,
) -> pd.DataFrame:
    """Build replacement or legacy sanity rows."""
    base13 = focus[(focus["scenario"].eq("base")) & (focus["hour"].eq(13))].copy()
    base13["p90_rank_13_base"] = pd.to_numeric(base13["tmrt_p90_c"], errors="coerce").rank(ascending=False, method="min")
    cols = [
        "cell_id",
        "tmrt_mean_c",
        "tmrt_p75_c",
        "tmrt_p90_c",
        "tmrt_p95_c",
        "tmrt_max_c",
        "pct_pixels_tmrt_ge_50",
        "pct_pixels_tmrt_ge_55",
        "p90_rank_13_base",
    ]
    base13 = base13[cols]
    tail_base = tails[tails["scenario"].eq("base")][["cell_id", "tail_class", "mean_p90_minus_mean", "mean_max_minus_p95", "mean_pct_ge_50", "mean_pct_ge_55"]]
    cool_cols = [c for c in ["cell_id", "delta_tmrt_p90_c_mean_delta", "delta_tmrt_p90_c_min_delta", "delta_tmrt_mean_c_mean_delta", "delta_pct_pixels_ge_50_mean_delta", "delta_pct_pixels_ge_55_mean_delta", "overhead_reduces_threshold_area_substantially"] if c in cooling.columns]
    meta = selected_metadata(selected)
    merged = pd.DataFrame({"cell_id": cells}).merge(base13, on="cell_id", how="left").merge(tail_base, on="cell_id", how="left").merge(cooling[cool_cols], on="cell_id", how="left").merge(meta, on="cell_id", how="left")
    rows: list[dict[str, Any]] = []
    for _, row in merged.iterrows():
        cell_id = str(row["cell_id"])
        p90_rank = row.get("p90_rank_13_base", math.nan)
        tail_class = str(row.get("tail_class", ""))
        cooling_delta = row.get("delta_tmrt_p90_c_mean_delta", math.nan)
        if kind == "replacement":
            informative = "yes" if pd.notna(p90_rank) and (p90_rank <= 6 or tail_class in {"mixed_cell_upper_tail", "threshold_area_hot", "max_only_extreme"} or (pd.notna(cooling_delta) and cooling_delta <= -1.0)) else "limited"
            expected = "replacement sanity"
            caveat = "Replacement-cell sanity only; does not validate cell choice as AOI-wide target truth."
        else:
            expected = LEGACY_EXPECTATIONS.get(cell_id, "continuity anchor")
            if expected == "hot anchor":
                informative = "consistent" if pd.notna(p90_rank) and p90_rank <= 8 else "partial"
            elif "shaded" in expected:
                informative = "consistent" if pd.notna(p90_rank) and p90_rank >= 16 else "partial"
            else:
                informative = "consistent" if pd.notna(cooling_delta) and abs(float(cooling_delta)) >= 0.5 else "partial"
            caveat = "Legacy-anchor sanity only; not observed truth and not final risk interpretation."
        record = row.to_dict()
        record["expected_role"] = expected
        record["informative_for_target_audit"] = informative
        record["consistency_with_expected_role"] = informative if kind == "legacy" else ""
        record["caveat"] = caveat
        rows.append(record)
    return pd.DataFrame(rows)


def replacement_and_legacy_sanity(
    focus: pd.DataFrame,
    tails: pd.DataFrame,
    cooling: pd.DataFrame,
    selected: pd.DataFrame,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Write replacement-cell and legacy-anchor sanity checks."""
    replacement = sanity_rows_for_cells(REPLACEMENT_IN, focus, tails, cooling, selected, "replacement")
    legacy = sanity_rows_for_cells(LEGACY_ANCHORS, focus, tails, cooling, selected, "legacy")
    replacement.to_csv(output_dir / "n24_replacement_cell_sanity.csv", index=False)
    legacy.to_csv(output_dir / "n24_legacy_anchor_sanity.csv", index=False)
    return replacement, legacy


def mean_pair_corr(rank_corr: pd.DataFrame, metric_a: str, metric_b: str) -> float:
    """Return mean pairwise Spearman for a metric pair."""
    rows = rank_corr[
        ((rank_corr["metric_a"].eq(metric_a)) & (rank_corr["metric_b"].eq(metric_b)))
        | ((rank_corr["metric_a"].eq(metric_b)) & (rank_corr["metric_b"].eq(metric_a)))
    ]
    return float(pd.to_numeric(rows["spearman_r"], errors="coerce").mean()) if not rows.empty else math.nan


def mean_pair_topk(topk: pd.DataFrame, metric_a: str, metric_b: str, k: int = 6) -> float:
    """Return mean pairwise top-k Jaccard for a metric pair."""
    rows = topk[
        (topk["top_k"].eq(k))
        & (
            ((topk["metric_a"].eq(metric_a)) & (topk["metric_b"].eq(metric_b)))
            | ((topk["metric_a"].eq(metric_b)) & (topk["metric_b"].eq(metric_a)))
        )
    ]
    return float(pd.to_numeric(rows["jaccard_overlap"], errors="coerce").mean()) if not rows.empty else math.nan


def p90_decision_status(
    rank_corr: pd.DataFrame,
    topk: pd.DataFrame,
    hour_rank: pd.DataFrame,
    hour_topk: pd.DataFrame,
    tails: pd.DataFrame,
    rank_shift: pd.DataFrame,
) -> tuple[str, dict[str, Any]]:
    """Evaluate whether p90 can be strengthened within the N24 sample."""
    p90_hour_r = pd.to_numeric(hour_rank[hour_rank["metric"].eq("tmrt_p90_c")]["spearman_r"], errors="coerce").mean()
    p90_hour_top6 = pd.to_numeric(hour_topk[(hour_topk["metric"].eq("tmrt_p90_c")) & (hour_topk["top_k"].eq(6))]["jaccard_overlap"], errors="coerce").mean()
    p90_p75 = mean_pair_corr(rank_corr, "tmrt_p90_c", "tmrt_p75_c")
    p90_p95 = mean_pair_corr(rank_corr, "tmrt_p90_c", "tmrt_p95_c")
    p90_ge50 = mean_pair_corr(rank_corr, "tmrt_p90_c", "pct_pixels_tmrt_ge_50")
    p90_ge55 = mean_pair_corr(rank_corr, "tmrt_p90_c", "pct_pixels_tmrt_ge_55")
    p90_max = mean_pair_corr(rank_corr, "tmrt_p90_c", "tmrt_max_c")
    p90_top_ge50 = mean_pair_topk(topk, "tmrt_p90_c", "pct_pixels_tmrt_ge_50", 6)
    max_only_share = float(tails["tail_class"].eq("max_only_extreme").mean()) if not tails.empty else math.nan
    p90_rank_shift = rank_shift[rank_shift["metric"].eq("tmrt_p90_c")] if not rank_shift.empty else pd.DataFrame()
    mean_abs_shift = float(pd.to_numeric(p90_rank_shift["abs_rank_delta"], errors="coerce").mean()) if not p90_rank_shift.empty else math.nan
    evidence = {
        "p90_hour_mean_spearman": p90_hour_r,
        "p90_hour_top6_mean_jaccard": p90_hour_top6,
        "p90_vs_p75_mean_spearman": p90_p75,
        "p90_vs_p95_mean_spearman": p90_p95,
        "p90_vs_ge50_mean_spearman": p90_ge50,
        "p90_vs_ge55_mean_spearman": p90_ge55,
        "p90_vs_max_mean_spearman": p90_max,
        "p90_vs_ge50_top6_mean_jaccard": p90_top_ge50,
        "max_only_tail_class_share": max_only_share,
        "p90_overhead_mean_abs_rank_shift": mean_abs_shift,
    }
    stable_hours = p90_hour_r >= 0.85 and p90_hour_top6 >= 0.60
    aligned_companions = p90_p75 >= 0.85 and p90_p95 >= 0.75 and min(p90_ge50, p90_ge55) >= 0.65
    not_max_only = (math.isnan(max_only_share) or max_only_share < 0.25) and (math.isnan(p90_max) or p90_max >= 0.45)
    overhead_interpretable = math.isnan(mean_abs_shift) or mean_abs_shift <= 5.0
    status = "n24_supported_primary_candidate" if stable_hours and aligned_companions and not_max_only and overhead_interpretable else "provisional_primary_candidate"
    return status, evidence


def threshold_recommendation_from_scores(rho: float, jac: float) -> str:
    """Classify a threshold metric from aggregate p90 correlation and top-k overlap."""
    if not math.isnan(rho) and not math.isnan(jac) and rho >= 0.85 and jac >= 0.60:
        return "required_companion"
    if not math.isnan(rho) and (rho >= 0.85 or (rho >= 0.65 and not math.isnan(jac) and jac >= 0.40)):
        return "optional_companion"
    if not math.isnan(rho) and rho >= 0.40:
        return "sensitivity_only"
    return "not_useful"


def overall_threshold_recommendations(rank_corr: pd.DataFrame, topk: pd.DataFrame) -> dict[str, str]:
    """Return aggregate N24 recommendations for threshold-area metrics."""
    metrics = [
        "pct_pixels_tmrt_ge_40",
        "pct_pixels_tmrt_ge_45",
        "pct_pixels_tmrt_ge_50",
        "pct_pixels_tmrt_ge_55",
    ]
    return {
        metric: threshold_recommendation_from_scores(
            mean_pair_corr(rank_corr, metric, "tmrt_p90_c"),
            mean_pair_topk(topk, metric, "tmrt_p90_c"),
        )
        for metric in metrics
    }


def target_decision_matrix(
    rank_corr: pd.DataFrame,
    topk: pd.DataFrame,
    hour_rank: pd.DataFrame,
    hour_topk: pd.DataFrame,
    tails: pd.DataFrame,
    rank_shift: pd.DataFrame,
    threshold_audit_df: pd.DataFrame,
    output_dir: Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Write target decision matrix."""
    p90_status, evidence = p90_decision_status(rank_corr, topk, hour_rank, hour_topk, tails, rank_shift)
    threshold_rec = overall_threshold_recommendations(rank_corr, topk)
    rows: list[dict[str, Any]] = []
    for metric in DECISION_METRICS:
        if metric == "tmrt_p90_c":
            rows.append(
                {
                    "metric": metric,
                    "candidate_role": "primary high-tail SOLWEIG-derived radiative exposure target candidate",
                    "recommended_status": p90_status,
                    "evidence_summary": (
                        f"mean hour Spearman={evidence['p90_hour_mean_spearman']:.3f}; "
                        f"p90-p75 Spearman={evidence['p90_vs_p75_mean_spearman']:.3f}; "
                        f"p90-ge50 Spearman={evidence['p90_vs_ge50_mean_spearman']:.3f}; "
                        f"max-only tail share={evidence['max_only_tail_class_share']:.3f}."
                    ),
                    "advantages": "Captures mixed-cell upper-tail radiant exposure without relying on a single maximum pixel.",
                    "risks": "Still N24 sample evidence only; not observed truth and not final AOI-wide canonical target.",
                    "downstream_allowed_use": "N24-supported System B target family candidate and reference for next target freeze discussion.",
                    "downstream_forbidden_use": "Do not use as local WBGT, hazard_score, risk_score, official warning, observed validation, or final AOI-wide M_rad map.",
                    "caveat": "Can be strengthened only within N24; canonical AOI-wide promotion needs accepted target freeze and downstream protocol.",
                }
            )
        elif metric == "tmrt_mean_c":
            rows.append(
                {
                    "metric": metric,
                    "candidate_role": "background central-tendency companion",
                    "recommended_status": "background_companion",
                    "evidence_summary": f"mean-p90 Spearman={mean_pair_corr(rank_corr, 'tmrt_mean_c', 'tmrt_p90_c'):.3f}; useful for checking whether p90 reflects broad heat or residual hot pockets.",
                    "advantages": "Simple broad radiant exposure summary.",
                    "risks": "Can hide high-tail pockets in mixed cells.",
                    "downstream_allowed_use": "Companion interpretation and plausibility check.",
                    "downstream_forbidden_use": "Do not use alone as final target or risk/hazard score.",
                    "caveat": "Simulation-derived Tmrt central tendency only.",
                }
            )
        elif metric == "tmrt_p75_c":
            rows.append(
                {
                    "metric": metric,
                    "candidate_role": "lower-tail shoulder companion",
                    "recommended_status": "companion_required",
                    "evidence_summary": f"p75-p90 Spearman={mean_pair_corr(rank_corr, 'tmrt_p75_c', 'tmrt_p90_c'):.3f}; top6 Jaccard={mean_pair_topk(topk, 'tmrt_p75_c', 'tmrt_p90_c'):.3f}.",
                    "advantages": "Shows whether p90 signal is supported by the distribution shoulder.",
                    "risks": "Less sensitive to hot pockets than p90.",
                    "downstream_allowed_use": "Required companion for p90 robustness checks.",
                    "downstream_forbidden_use": "Do not treat as observed exposure truth.",
                    "caveat": "N24 diagnostic companion only.",
                }
            )
        elif metric == "tmrt_p95_c":
            corr = mean_pair_corr(rank_corr, "tmrt_p95_c", "tmrt_p90_c")
            status = "companion_required" if corr < 0.98 else "optional_companion"
            rows.append(
                {
                    "metric": metric,
                    "candidate_role": "upper-tail companion",
                    "recommended_status": status,
                    "evidence_summary": f"p95-p90 Spearman={corr:.3f}; captures hotter upper-tail behavior beyond p90.",
                    "advantages": "Tests whether p90 misses stronger tail exposure.",
                    "risks": "More tail-sensitive than p90.",
                    "downstream_allowed_use": "Required high-tail companion where p95 is not identical to p90.",
                    "downstream_forbidden_use": "Do not use as local WBGT or risk.",
                    "caveat": "Simulation-derived upper-tail Tmrt only.",
                }
            )
        elif metric == "tmrt_max_c":
            rows.append(
                {
                    "metric": metric,
                    "candidate_role": "extreme upper-bound sensitivity",
                    "recommended_status": "sensitivity_only",
                    "evidence_summary": f"max-p90 Spearman={mean_pair_corr(rank_corr, 'tmrt_max_c', 'tmrt_p90_c'):.3f}; max-only tail classes remain an explicit outlier check.",
                    "advantages": "Flags extreme pixel behavior.",
                    "risks": "Most sensitive to isolated pixels and edge artifacts.",
                    "downstream_allowed_use": "Sensitivity and QA diagnostic.",
                    "downstream_forbidden_use": "Do not use as primary target.",
                    "caveat": "Maximum is not a robust mixed-cell target.",
                }
            )
        elif metric.startswith("pct_pixels_tmrt_ge_"):
            status = threshold_rec.get(metric, "optional_companion")
            rows.append(
                {
                    "metric": metric,
                    "candidate_role": "threshold-area companion",
                    "recommended_status": status,
                    "evidence_summary": f"aggregate N24 status={status}; p90 Spearman={mean_pair_corr(rank_corr, metric, 'tmrt_p90_c'):.3f}; top6 Jaccard={mean_pair_topk(topk, metric, 'tmrt_p90_c'):.3f}.",
                    "advantages": "Expresses the area share above a Tmrt threshold, useful for mixed-cell interpretation.",
                    "risks": "Threshold choice is policy/interpretation sensitive and still not pedestrian-accessibility masked.",
                    "downstream_allowed_use": "Companion area-based interpretation for N24 target robustness.",
                    "downstream_forbidden_use": "Do not convert directly into WBGT, hazard_score, risk_score, or warning classes.",
                    "caveat": "Simulation-derived threshold area only.",
                }
            )
        elif metric == "delta_tmrt_p90_c":
            rows.append(
                {
                    "metric": metric,
                    "candidate_role": "derived p90 delta companion",
                    "recommended_status": "derived_provisional_companion",
                    "evidence_summary": "Available from base-vs-overhead and provisional target tables; derived from p90/reference choices.",
                    "advantages": "Makes hour/scenario-relative p90 differences explicit.",
                    "risks": "Not independent validation and sensitive to reference definition.",
                    "downstream_allowed_use": "Companion for sensitivity and target-freeze discussion.",
                    "downstream_forbidden_use": "Do not treat as observed validation or final AOI-wide modifier.",
                    "caveat": "Derived/provisional N24 metric only.",
                }
            )
        elif metric == "m_rad_pct_provisional":
            rows.append(
                {
                    "metric": metric,
                    "candidate_role": "derived provisional relative modifier companion",
                    "recommended_status": "derived_provisional_companion",
                    "evidence_summary": "N24-internal percentile-like modifier if provisional table is present.",
                    "advantages": "Compact relative ranking within the N24 batch.",
                    "risks": "Relative rank hides absolute Tmrt differences and is not final AOI-wide M_rad_pct.",
                    "downstream_allowed_use": "N24-internal companion only.",
                    "downstream_forbidden_use": "Do not publish as final AOI-wide M_rad map or use for System A/B coupling yet.",
                    "caveat": "`n24_modifier_targets_provisional.csv` is N24-internal only.",
                }
            )
    result = pd.DataFrame(rows)
    result.to_csv(output_dir / "n24_target_decision_matrix.csv", index=False)
    return result, evidence


def fmt(value: Any, digits: int = 3) -> str:
    """Format a float-ish value for Markdown."""
    try:
        value_f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(value_f):
        return "NA"
    return f"{value_f:.{digits}f}"


def cells_from(df: pd.DataFrame, column: str, n: int = 5, ascending: bool = True) -> str:
    """Return a compact list of cells sorted by a numeric column."""
    if df.empty or column not in df.columns:
        return "NA"
    temp = df[["cell_id", column]].copy()
    temp[column] = pd.to_numeric(temp[column], errors="coerce")
    temp = temp.dropna().sort_values(column, ascending=ascending).head(n)
    return ", ".join(f"{r.cell_id} ({fmt(getattr(r, column), 2)})" for r in temp.itertuples())


def write_main_report(
    output_dir: Path,
    status: str,
    focus: pd.DataFrame,
    delta: pd.DataFrame,
    availability: pd.DataFrame,
    rank_corr: pd.DataFrame,
    topk: pd.DataFrame,
    hour_rank: pd.DataFrame,
    hour_topk: pd.DataFrame,
    consistent: pd.DataFrame,
    tails: pd.DataFrame,
    sensitivity: pd.DataFrame,
    cooling: pd.DataFrame,
    rank_shift: pd.DataFrame,
    threshold_audit_df: pd.DataFrame,
    replacement: pd.DataFrame,
    legacy: pd.DataFrame,
    decision: pd.DataFrame,
    evidence: dict[str, Any],
) -> None:
    """Write the Sprint B4 Markdown report."""
    p90_status = decision.loc[decision["metric"].eq("tmrt_p90_c"), "recommended_status"].iloc[0]
    p90_vs_p75 = mean_pair_corr(rank_corr, "tmrt_p90_c", "tmrt_p75_c")
    p90_vs_p95 = mean_pair_corr(rank_corr, "tmrt_p90_c", "tmrt_p95_c")
    p90_vs_max = mean_pair_corr(rank_corr, "tmrt_p90_c", "tmrt_max_c")
    p90_vs_mean = mean_pair_corr(rank_corr, "tmrt_p90_c", "tmrt_mean_c")
    p90_vs_ge50 = mean_pair_corr(rank_corr, "tmrt_p90_c", "pct_pixels_tmrt_ge_50")
    p90_vs_ge55 = mean_pair_corr(rank_corr, "tmrt_p90_c", "pct_pixels_tmrt_ge_55")
    p90_top6_ge50 = mean_pair_topk(topk, "tmrt_p90_c", "pct_pixels_tmrt_ge_50")
    p90_hour = pd.to_numeric(hour_rank[hour_rank["metric"].eq("tmrt_p90_c")]["spearman_r"], errors="coerce").mean()
    p90_hour_top6 = pd.to_numeric(hour_topk[(hour_topk["metric"].eq("tmrt_p90_c")) & (hour_topk["top_k"].eq(6))]["jaccard_overlap"], errors="coerce").mean()
    tail_counts = tails["tail_class"].value_counts().to_dict() if not tails.empty else {}
    threshold_modes = overall_threshold_recommendations(rank_corr, topk)
    largest_shift = rank_shift.sort_values("abs_rank_delta", ascending=False).head(5) if not rank_shift.empty else pd.DataFrame()
    shift_text = ", ".join(
        f"{r.cell_id} {r.metric} h{int(r.hour)} ({fmt(r.rank_delta, 0)})" for r in largest_shift.itertuples()
    ) or "NA"
    lines = [
        "# Sprint B4 — N24 System B Target Robustness Re-audit",
        "",
        "## Status",
        status,
        "",
        "## Scope",
        "- reads completed N24 SOLWEIG summaries",
        "- no QGIS",
        "- no SOLWEIG rerun",
        "- no raw rasters",
        "- no local WBGT",
        "- no hazard_score",
        "- no risk_score",
        "- no surrogate",
        "- no System A/B coupling",
        "",
        "## Inputs",
        f"B3 status is PASS. Focus summary rows: `{len(focus)}`. Base-vs-overhead delta rows: `{len(delta)}`. Unique cells: `{focus['cell_id'].nunique()}`. Scenarios: `{', '.join(sorted(focus['scenario'].unique()))}`. Hours: `{', '.join(map(str, sorted(focus['hour'].unique())))}`.",
        "",
        "## Target availability",
        "Available target metrics include `tmrt_mean_c`, `tmrt_p50_c`, `tmrt_p75_c`, `tmrt_p90_c`, `tmrt_p95_c`, `tmrt_max_c`, and threshold-area metrics `pct_pixels_tmrt_ge_40/45/50/55`.",
        f"Availability rows marked available: `{int(availability['availability_status'].eq('available').sum())}` / `{len(availability)}`.",
        "",
        "## Rank robustness",
        f"Mean Spearman: p90 vs p75 `{fmt(p90_vs_p75)}`, p90 vs p95 `{fmt(p90_vs_p95)}`, p90 vs max `{fmt(p90_vs_max)}`, p90 vs mean `{fmt(p90_vs_mean)}`, p90 vs pct_ge_50 `{fmt(p90_vs_ge50)}`, p90 vs pct_ge_55 `{fmt(p90_vs_ge55)}`.",
        "p90 is interpreted as a simulation-derived mixed-cell upper-tail radiant exposure target, not observed truth.",
        "",
        "## Top-k overlap",
        f"Mean top6 Jaccard for p90 vs pct_ge_50 is `{fmt(p90_top6_ge50)}`. See `n24_target_topk_overlap.csv` for top6 and top3 cell sets by metric pair.",
        "",
        "## Hour stability",
        f"p90 mean cross-hour Spearman is `{fmt(p90_hour)}` and mean top6 Jaccard is `{fmt(p90_hour_top6)}` across 10/12/13/15/16.",
        f"Consistent p90 top6 cells across at least 3 of 5 hours: `{', '.join(consistent[(consistent['metric'].eq('tmrt_p90_c')) & (consistent['top_k'].eq(6))]['cell_id'].astype(str).unique().tolist())}`.",
        "",
        "## Tail heterogeneity",
        f"Tail classes by cell/scenario: `{tail_counts}`.",
        "The audit separates broad hot cells, mixed cells where p90 reveals residual hot pockets, and max-only extremes where `tmrt_max_c` may be too outlier-sensitive.",
        "",
        "## Overhead sensitivity",
        f"Strongest mean p90 cooling cells: {cells_from(cooling, 'delta_tmrt_p90_c_mean_delta', 5, True)}.",
        f"Strongest threshold-area ge50 reductions: {cells_from(cooling, 'delta_pct_pixels_ge_50_mean_delta', 5, True)}.",
        f"Largest rank shifts: {shift_text}.",
        "The `overhead_as_canopy` scenario is a sensitivity scenario, not absolute truth.",
        "",
        "## Threshold-area companions",
        f"Aggregate threshold recommendations: `{threshold_modes}`.",
        "Threshold-area metrics are useful companions because they express area share above radiant thresholds and can reveal cases where p90 is high but the hot area is small, or p90 is moderate but a broad area exceeds a threshold.",
        "",
        "## Replacement and legacy sanity",
        f"Replacement cells checked: `{', '.join(replacement['cell_id'].astype(str).tolist())}`.",
        f"Legacy / continuity anchors checked: `{', '.join(legacy['cell_id'].astype(str).tolist())}`.",
        "These are sanity checks only; they do not validate observed truth.",
        "",
        "## Target decision",
        f"`tmrt_p90_c` recommended status: `{p90_status}`.",
        "Required/retained companions include p75, p95, mean, max sensitivity, threshold-area metrics, and derived/provisional delta or modifier metrics where explicitly caveated.",
        "No final AOI-wide canonical target is claimed here.",
        "",
        "## Claim boundaries",
        "Allowed:",
        "- N24 SOLWEIG-derived target robustness evidence",
        "- N24-supported radiative target family",
        "- simulation-informed radiative hazard-potential target",
        "",
        "Forbidden:",
        "- local WBGT",
        "- risk",
        "- hazard_score",
        "- official warning",
        "- observed truth",
        "- final AOI-wide M_rad map",
        "- surrogate validation",
        "",
        "## Next recommended action",
        "B5: N24 target freeze / modifier reference definition update.",
        "",
        "## Output files",
        "- `b4_input_validation.csv` / `b4_input_validation.md`",
        "- `n24_metric_availability_matrix.csv`",
        "- `n24_target_descriptive_stats.csv`",
        "- `n24_target_rank_correlation.csv`",
        "- `n24_target_topk_overlap.csv`",
        "- `n24_hour_stability_rank_correlation.csv`",
        "- `n24_hour_stability_topk_overlap.csv`",
        "- `n24_consistent_top_cells.csv`",
        "- `n24_tail_heterogeneity_diagnostics.csv`",
        "- `n24_base_vs_overhead_sensitivity_summary.csv`",
        "- `n24_overhead_cooling_by_cell.csv`",
        "- `n24_overhead_rank_shift.csv`",
        "- `n24_threshold_area_audit.csv`",
        "- `n24_replacement_cell_sanity.csv`",
        "- `n24_legacy_anchor_sanity.csv`",
        "- `n24_target_decision_matrix.csv`",
    ]
    (output_dir / "sprint_b4_n24_target_robustness_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_blocked_report(output_dir: Path, design_doc: Path) -> None:
    """Write blocked reports if input validation fails."""
    lines = [
        "# Sprint B4 — N24 System B Target Robustness Re-audit",
        "",
        "## Status",
        "BLOCKED",
        "",
        "Input validation failed. Target interpretation was not run.",
        "",
        "Boundary confirmation: no QGIS, no SOLWEIG rerun, no qgis_process, no raw rasters, no local WBGT, no hazard_score, no risk_score, no surrogate, and no System A/B coupling.",
    ]
    (output_dir / "sprint_b4_n24_target_robustness_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    design_doc.parent.mkdir(parents=True, exist_ok=True)
    design_doc.write_text(
        "# OpenHeat System B N24 目标稳健性复审说明\n\n状态：BLOCKED。输入校验未通过，因此未进行目标解释。\n",
        encoding="utf-8",
    )


def write_design_doc(
    design_doc: Path,
    decision: pd.DataFrame,
    evidence: dict[str, Any],
    threshold_audit_df: pd.DataFrame,
    tails: pd.DataFrame,
    threshold_recommendations: dict[str, str],
) -> None:
    """Write the Chinese design/findings note."""
    p90_status = decision.loc[decision["metric"].eq("tmrt_p90_c"), "recommended_status"].iloc[0]
    tail_counts = tails["tail_class"].value_counts().to_dict() if not tails.empty else {}
    lines = [
        "# OpenHeat System B N24 目标稳健性复审说明",
        "",
        "## 为什么需要 B4",
        "B4 的目的，是在 B3 已经完成并校验通过的 N24 SOLWEIG 汇总结果之上，重新审计 System B 的辐射暴露目标族是否稳健。它只读取既有 CSV/Markdown 汇总，不重跑 SOLWEIG，不运行 QGIS，不读取原始栅格。",
        "",
        "## N24 相比 Core 8 增加了什么",
        "Core 8 只能说明早期目标选择是否有初步一致性；N24 增加了更多诊断角色、替换单元和连续性锚点，使 p90、p95、max、均值以及阈值面积指标可以在更宽的样本内比较。B4 仍然是样本内证据，不是全 AOI 最终结论。",
        "",
        "## p90 做得好的地方",
        f"`tmrt_p90_c` 的 B4 建议状态为 `{p90_status}`。关键证据包括：跨小时平均 Spearman `{fmt(evidence.get('p90_hour_mean_spearman'))}`，p90 与 p75 平均 Spearman `{fmt(evidence.get('p90_vs_p75_mean_spearman'))}`，p90 与 pct_ge_50 平均 Spearman `{fmt(evidence.get('p90_vs_ge50_mean_spearman'))}`。",
        "这说明 p90 在 N24 内可以作为混合单元上尾辐射暴露的主要候选指标：它比均值更能看到局部热斑，又不像 max 那样完全依赖单个极端像元。",
        "",
        "## 为什么还需要 p95、max 和阈值面积伴随指标",
        "p95 用来检查 p90 以上的更高尾部是否改变解释；max 用作极端像元敏感性和 QA 检查，不适合作为主目标；阈值面积指标说明有多少比例像元超过 40/45/50/55 C 的 Tmrt 门槛。",
        f"B4 的尾部分类计数为 `{tail_counts}`。阈值面积的 N24 汇总建议为 `{threshold_recommendations}`。",
        "",
        "## overhead_as_canopy 敏感性意味着什么",
        "`overhead_as_canopy` 只是结构敏感性场景，用来观察架空/遮蔽结构假设改变时，均值、p90、p95、max 和阈值面积是否同步变化。它不是绝对真实世界，也不是观测验证。",
        "",
        "## 为什么这仍然不是 local WBGT / risk",
        "SOLWEIG/Tmrt 输出是模拟得到的辐射暴露目标，不是 WBGT，不是风险，不是官方预警，也不是地面观测真值。B4 不计算 local WBGT、hazard_score、risk_score，不训练代理模型，也不做 System A/B 耦合。",
        "",
        "## 下一步可以做什么",
        "建议进入 B5：N24 target freeze / modifier reference definition update。只有在目标族被接受之后，才应准备后续 surrogate protocol 或 System A/B coupling contract。",
    ]
    design_doc.parent.mkdir(parents=True, exist_ok=True)
    design_doc.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Run the B4 N24 target robustness re-audit."""
    args = parse_args()
    root = args.repo_root.resolve()
    output_dir = repo_path(root, args.output_dir)
    design_doc = repo_path(root, args.design_doc)
    output_dir.mkdir(parents=True, exist_ok=True)

    ok, data = validate_inputs(root, output_dir)
    if not ok:
        write_blocked_report(output_dir, design_doc)
        print("[BLOCKED] B4 input validation failed; target interpretation was not run.")
        return

    focus = data["focus"].copy()
    focus["cell_id"] = focus["cell_id"].astype(str)
    focus["hour"] = pd.to_numeric(focus["hour"], errors="coerce").astype(int)
    delta = data["delta"].copy()
    selected = data.get("selected", pd.DataFrame()).copy()

    availability, stats = metric_availability_and_stats(focus, output_dir)
    rank_corr = rank_correlation_audit(focus, output_dir)
    topk = target_topk_overlap(focus, output_dir)
    hour_rank, hour_topk, consistent = hour_stability_audit(focus, output_dir)
    tails = tail_heterogeneity_audit(focus, output_dir)
    sensitivity, cooling, rank_shift = overhead_sensitivity_audit(delta, output_dir)
    threshold = threshold_area_audit(focus, rank_corr, topk, output_dir)
    replacement, legacy = replacement_and_legacy_sanity(focus, tails, cooling, selected, output_dir)
    decision, evidence = target_decision_matrix(rank_corr, topk, hour_rank, hour_topk, tails, rank_shift, threshold, output_dir)
    write_main_report(
        output_dir=output_dir,
        status="PASS",
        focus=focus,
        delta=delta,
        availability=availability,
        rank_corr=rank_corr,
        topk=topk,
        hour_rank=hour_rank,
        hour_topk=hour_topk,
        consistent=consistent,
        tails=tails,
        sensitivity=sensitivity,
        cooling=cooling,
        rank_shift=rank_shift,
        threshold_audit_df=threshold,
        replacement=replacement,
        legacy=legacy,
        decision=decision,
        evidence=evidence,
    )
    write_design_doc(design_doc, decision, evidence, threshold, tails, overall_threshold_recommendations(rank_corr, topk))
    print(f"[PASS] wrote B4 outputs to {output_dir}")
    print(f"[PASS] wrote design note to {design_doc}")
    print("[BOUNDARY] no QGIS/SOLWEIG/qgis_process/raster/WBGT/hazard/risk/surrogate/System A-B coupling actions performed")


if __name__ == "__main__":
    main()
