"""Sprint B5 System B target freeze and modifier reference definition.

Inputs:
    - outputs/v12_systemb_n24_target_robustness/sprint_b4_n24_target_robustness_report.md
    - outputs/v12_systemb_n24_target_robustness/n24_target_decision_matrix.csv
    - outputs/v12_systemb_n24_target_robustness/n24_target_rank_correlation.csv
    - outputs/v12_systemb_n24_target_robustness/n24_target_topk_overlap.csv
    - outputs/v12_systemb_n24_target_robustness/n24_hour_stability_rank_correlation.csv
    - outputs/v12_systemb_n24_target_robustness/n24_base_vs_overhead_sensitivity_summary.csv
    - outputs/v12_systemb_n24_target_robustness/n24_threshold_area_audit.csv
    - outputs/v12_systemb_n24_target_robustness/n24_tail_heterogeneity_diagnostics.csv
    - outputs/v12_solweig_n24_execution/n24_focus_tmrt_summary.csv
    - outputs/v12_solweig_n24_execution/n24_base_vs_overhead_delta.csv
    - outputs/v12_solweig_n24_execution/n24_modifier_targets_provisional.csv
    - outputs/v12_solweig_n24_execution/sprint_b3_n24_solweig_execution_report.md
    - selected docs/v12 System B notes and optional earlier decision matrix.

Outputs:
    - outputs/v12_systemb_target_freeze/b5_b4_decision_validation.csv
    - outputs/v12_systemb_target_freeze/b5_b4_decision_validation.md
    - outputs/v12_systemb_target_freeze/systemb_target_family_freeze.csv
    - outputs/v12_systemb_target_freeze/systemb_modifier_reference_rules.csv
    - outputs/v12_systemb_target_freeze/systemb_modifier_reference_rules.md
    - outputs/v12_systemb_target_freeze/systemb_target_output_schema.csv
    - outputs/v12_systemb_target_freeze/systemb_surrogate_label_contract.csv
    - outputs/v12_systemb_target_freeze/systemb_downstream_claim_boundary_matrix.csv
    - outputs/v12_systemb_target_freeze/n24_modifier_targets_b5_method_check.csv
    - outputs/v12_systemb_target_freeze/n24_reference_values_b5.csv
    - outputs/v12_systemb_target_freeze/n24_modifier_method_comparison.csv
    - configs/v12/systemb_target_freeze_config.example.yaml
    - configs/v12/systemb_modifier_reference_definition.example.yaml
    - docs/v12/OpenHeat_SystemB_target_freeze_modifier_reference_CN.md
    - docs/v12/OpenHeat_modifier_target_spec_CN.md
    - outputs/v12_systemb_target_freeze/sprint_b5_target_freeze_report.md

Saved metrics:
    - B4 decision carry-forward validation checks.
    - Frozen System B target family, reference-domain rules, future target
      schema, surrogate label contract, and downstream claim boundary matrix.
    - N24-internal B5 method-check reference medians, deltas, canonical
      0-1 rank modifier, and row-level comparison to legacy provisional
      modifier columns when available.

Boundary:
    This script reads existing CSV/Markdown summaries only. It does not read
    .tif/.tiff files or raw rasters, does not modify data/solweig raw outputs,
    and does not run QGIS, qgis_process, or SOLWEIG. It does not compute local
    WBGT, hazard_score, risk_score, surrogate/emulator models, final maps, or
    System A/B coupling.

Run:
    C:\\Users\\CloudStar\\anaconda3\\Scripts\\conda.exe run -n openheat --no-capture-output python -X faulthandler -u scripts\\v12_b5_freeze_systemb_target_spec.py
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path("outputs/v12_systemb_target_freeze")
B4_DIR = Path("outputs/v12_systemb_n24_target_robustness")
B3_DIR = Path("outputs/v12_solweig_n24_execution")
DOCS_DIR = Path("docs/v12")
CONFIG_DIR = Path("configs/v12")

B4_REPORT = B4_DIR / "sprint_b4_n24_target_robustness_report.md"
B4_DECISION = B4_DIR / "n24_target_decision_matrix.csv"
B4_INPUTS = [
    B4_DIR / "n24_target_rank_correlation.csv",
    B4_DIR / "n24_target_topk_overlap.csv",
    B4_DIR / "n24_hour_stability_rank_correlation.csv",
    B4_DIR / "n24_base_vs_overhead_sensitivity_summary.csv",
    B4_DIR / "n24_threshold_area_audit.csv",
    B4_DIR / "n24_tail_heterogeneity_diagnostics.csv",
]
B3_REPORT = B3_DIR / "sprint_b3_n24_solweig_execution_report.md"
FOCUS_SUMMARY = B3_DIR / "n24_focus_tmrt_summary.csv"
DELTA_SUMMARY = B3_DIR / "n24_base_vs_overhead_delta.csv"
PROVISIONAL_MODIFIER = B3_DIR / "n24_modifier_targets_provisional.csv"
OPTIONAL_B1_DECISION = Path("outputs/v12_systemb_target_robustness/systemb_target_decision_matrix.csv")
DOC_INPUTS = [
    DOCS_DIR / "OpenHeat_SystemB_N24_target_robustness_reaudit_CN.md",
    DOCS_DIR / "OpenHeat_SystemB_product_taxonomy_CN.md",
    DOCS_DIR / "OpenHeat_SystemB_N24_companion_metric_plan_CN.md",
    DOCS_DIR / "OpenHeat_SystemB_target_robustness_protocol_CN.md",
    DOCS_DIR / "OpenHeat_SystemB_architecture_discussion_record_CN.md",
]

EXPECTED_HOURS = [10, 12, 13, 15, 16]
EXPECTED_SCENARIOS = ["base", "overhead_as_canopy"]
THRESHOLD_METRICS = [
    "pct_pixels_tmrt_ge_40",
    "pct_pixels_tmrt_ge_45",
    "pct_pixels_tmrt_ge_50",
    "pct_pixels_tmrt_ge_55",
]
COMPANION_STATUSES = {
    "tmrt_p75_c": ["companion", "required", "sensitivity"],
    "tmrt_p95_c": ["companion", "required", "sensitivity"],
    "tmrt_mean_c": ["companion", "background", "sensitivity"],
    "tmrt_max_c": ["companion", "sensitivity"],
}
FORBIDDEN_OUTPUT_FIELDS = [
    "local_wbgt_c",
    "wbgt_cell_c",
    "delta_wbgt_cell",
    "hazard_score",
    "risk_score",
    "exposure_score",
    "vulnerability_score",
    "official_warning_probability",
]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Freeze the System B target family and modifier reference contract "
            "from existing B3/B4 CSV and Markdown summaries. Writes validation "
            "CSV/MD, target-family tables, reference rules, schema/claim "
            "contracts, N24-internal method-check tables, example YAML configs, "
            "and Chinese documentation. Does not read raw rasters, run QGIS or "
            "SOLWEIG, compute local WBGT/hazard/risk, train surrogates, make "
            "maps, or perform System A/B coupling."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT, help="Repository root.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="B5 output directory.")
    return parser.parse_args()


def repo_path(root: Path, path: Path) -> Path:
    """Return an absolute path for a repository-relative path."""
    return path if path.is_absolute() else root / path


def read_text(path: Path) -> str:
    """Read text with tolerant UTF-8 handling."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig", errors="replace")


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def rel(path: Path, root: Path) -> str:
    """Return a stable repo-relative path for reports."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def status_pass(text: str) -> bool:
    """Detect a PASS status in a Markdown report."""
    lowered = text.lower()
    return bool(
        re.search(r"##\s*status\s*\n+\s*pass\b", lowered)
        or re.search(r"status\s*:\s*\**pass\**", lowered)
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
    rows.append(
        {
            "section": section,
            "check": check,
            "status": "PASS" if ok else ("WARN" if warn else "FAIL"),
            "observed": observed,
            "expected": expected,
            "note": note,
        }
    )


def compact_markdown_table(rows: list[dict[str, Any]]) -> str:
    """Build a compact Markdown table without optional dependencies."""
    headers = ["section", "check", "status", "observed", "expected", "note"]
    lines = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        values = [str(row.get(header, "")).replace("\n", " ") for header in headers]
        lines.append("|" + "|".join(values) + "|")
    return "\n".join(lines)


def load_csv_if_present(path: Path) -> pd.DataFrame:
    """Load a CSV if it exists, otherwise return an empty DataFrame."""
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def validate_b4(root: Path, output_dir: Path) -> tuple[str, pd.DataFrame, dict[str, Any]]:
    """Validate B4 inputs and write validation CSV/Markdown."""
    rows: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}

    b4_report_path = repo_path(root, B4_REPORT)
    b4_decision_path = repo_path(root, B4_DECISION)
    focus_path = repo_path(root, FOCUS_SUMMARY)
    delta_path = repo_path(root, DELTA_SUMMARY)
    provisional_path = repo_path(root, PROVISIONAL_MODIFIER)
    b3_report_path = repo_path(root, B3_REPORT)

    report_text = read_text(b4_report_path) if b4_report_path.exists() else ""
    add_check(rows, "B4 report", "report exists", b4_report_path.exists(), rel(b4_report_path, root), "present")
    add_check(rows, "B4 report", "status is PASS", status_pass(report_text), "PASS" if status_pass(report_text) else "not PASS", "PASS")

    decision = load_csv_if_present(b4_decision_path)
    add_check(rows, "B4 decision", "decision matrix exists", not decision.empty, rel(b4_decision_path, root), "present")
    add_check(rows, "B3 report", "B3 report exists", b3_report_path.exists(), rel(b3_report_path, root), "present")

    focus = load_csv_if_present(focus_path)
    delta = load_csv_if_present(delta_path)
    provisional = load_csv_if_present(provisional_path)
    metadata["focus_rows"] = len(focus)
    metadata["delta_rows"] = len(delta)
    metadata["provisional_rows"] = len(provisional)
    metadata["unique_cells"] = int(focus["cell_id"].nunique()) if "cell_id" in focus.columns else 0
    metadata["hours"] = sorted(focus["hour"].dropna().astype(int).unique().tolist()) if "hour" in focus.columns else []
    metadata["scenarios"] = sorted(focus["scenario"].dropna().unique().tolist()) if "scenario" in focus.columns else []
    add_check(rows, "B3 focus", "focus summary exists", not focus.empty, f"{len(focus)} rows", "240 rows")
    add_check(rows, "B3 delta", "base-vs-overhead delta exists", not delta.empty, f"{len(delta)} rows", "120 rows")
    add_check(rows, "B3 modifier", "provisional modifier exists", not provisional.empty, f"{len(provisional)} rows", "present")

    if not decision.empty and {"metric", "recommended_status"}.issubset(decision.columns):
        status_by_metric = dict(zip(decision["metric"], decision["recommended_status"]))
        p90_status = str(status_by_metric.get("tmrt_p90_c", ""))
        add_check(
            rows,
            "B4 decision",
            "tmrt_p90_c is N24-supported primary candidate",
            p90_status == "n24_supported_primary_candidate" or "primary" in p90_status.lower(),
            p90_status,
            "n24_supported_primary_candidate or equivalent",
        )
        for metric, keywords in COMPANION_STATUSES.items():
            observed = str(status_by_metric.get(metric, ""))
            add_check(
                rows,
                "B4 decision",
                f"{metric} has companion/sensitivity status",
                any(keyword in observed.lower() for keyword in keywords),
                observed,
                "companion / sensitivity status",
            )
        for metric in THRESHOLD_METRICS:
            observed = str(status_by_metric.get(metric, ""))
            add_check(
                rows,
                "B4 decision",
                f"{metric} exists as threshold-area metric",
                metric in status_by_metric and ("companion" in observed.lower() or "sensitivity" in observed.lower() or "optional" in observed.lower()),
                observed,
                "optional companion / sensitivity",
            )
        for metric in ["delta_tmrt_p90_c", "m_rad_pct_provisional"]:
            observed = str(status_by_metric.get(metric, ""))
            add_check(
                rows,
                "B4 decision",
                f"{metric} caveated as derived/provisional",
                "derived" in observed.lower() or "provisional" in observed.lower(),
                observed,
                "derived / provisional caveat",
            )
    else:
        add_check(rows, "B4 decision", "decision matrix has required columns", False, list(decision.columns), "metric, recommended_status")

    for metric in THRESHOLD_METRICS:
        add_check(rows, "B3 focus", f"{metric} present in focus summary", metric in focus.columns, metric in focus.columns, "column present")

    no_final_mrad = "no final aoi-wide" in report_text.lower() and ("m_rad" in report_text.lower() or "canonical target" in report_text.lower())
    no_risk_claim = "forbidden" in report_text.lower() and "risk" in report_text.lower()
    add_check(rows, "Claim boundary", "B4 did not claim final AOI-wide M_rad", no_final_mrad, no_final_mrad, "explicit no-final-AOI-wide caveat")
    add_check(rows, "Claim boundary", "B4 did not claim risk", no_risk_claim, no_risk_claim, "risk forbidden/caveated")

    for input_path in B4_INPUTS + DOC_INPUTS + [OPTIONAL_B1_DECISION]:
        full_path = repo_path(root, input_path)
        optional = input_path in [DOCS_DIR / "OpenHeat_SystemB_architecture_discussion_record_CN.md", OPTIONAL_B1_DECISION]
        exists = full_path.exists()
        if exists and full_path.suffix.lower() == ".md":
            _ = read_text(full_path)
        elif exists and full_path.suffix.lower() == ".csv":
            _ = pd.read_csv(full_path, nrows=5)
        add_check(
            rows,
            "Input inventory",
            rel(full_path, root),
            exists or optional,
            "present" if exists else "missing optional" if optional else "missing",
            "present" if not optional else "present if available",
            warn=optional and not exists,
        )

    validation = pd.DataFrame(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    validation.to_csv(output_dir / "b5_b4_decision_validation.csv", index=False)
    failed = validation["status"].eq("FAIL").any()
    status = "BLOCKED" if failed else "PASS"
    validation_md = (
        "# Sprint B5 B4 Decision Validation\n\n"
        f"## Status\n{status}\n\n"
        "This validation checks that the B4 N24 decision can be carried forward "
        "without upgrading claims beyond the N24-internal evidence base.\n\n"
        f"{compact_markdown_table(rows)}\n"
    )
    write_text(output_dir / "b5_b4_decision_validation.md", validation_md)
    return status, validation, metadata


def target_family_table(provisional_present: bool) -> pd.DataFrame:
    """Return the frozen target family table."""
    rows = [
        {
            "target_field": "tmrt_p90_c",
            "target_role": "primary_physical_target",
            "freeze_status": "n24_supported_primary_candidate",
            "meaning": "mixed-cell upper-tail radiant exposure",
            "downstream_allowed": "N150 label; surrogate label candidate; modifier derivation",
            "downstream_forbidden": "local WBGT; observed truth; risk; hazard_score by itself",
            "caveat": "N24-supported, not final AOI-wide canonical until N150/full-domain validation",
        },
        {
            "target_field": "delta_tmrt_p90_c",
            "target_role": "primary_modifier_physical_delta",
            "freeze_status": "method_frozen_for_next_scale",
            "meaning": "p90 relative to same-hour same-scenario reference median",
            "downstream_allowed": "surrogate regression label candidate; M_rad derivation",
            "downstream_forbidden": "Celsius ratio; local WBGT; hazard_score by itself; risk",
            "caveat": "reference-domain dependent",
        },
        {
            "target_field": "m_rad_pct01",
            "target_role": "canonical_normalized_modifier_candidate",
            "freeze_status": "method_frozen_for_next_scale",
            "meaning": "0-1 percentile rank of delta_tmrt_p90_c within same-hour same-scenario reference domain",
            "downstream_allowed": "future WBGT-conditioned radiative priority input",
            "downstream_forbidden": "standalone hazard_score; standalone risk; observed truth; official warning",
            "caveat": "not final AOI-wide map until reference domain is full AOI / N150-derived prediction",
        },
        {
            "target_field": "tmrt_p75_c",
            "target_role": "required_companion",
            "freeze_status": "retained_required_companion",
            "meaning": "shoulder / stable upper-distribution companion",
            "downstream_allowed": "validation companion; robustness evidence",
            "downstream_forbidden": "standalone canonical target unless spec is revised",
            "caveat": "companion to p90, not replacement in B5",
        },
        {
            "target_field": "tmrt_p95_c",
            "target_role": "required_companion",
            "freeze_status": "retained_required_companion",
            "meaning": "higher-tail companion",
            "downstream_allowed": "validation companion; tail sensitivity",
            "downstream_forbidden": "standalone canonical target unless spec is revised",
            "caveat": "more tail-sensitive than p90",
        },
        {
            "target_field": "tmrt_mean_c",
            "target_role": "background_companion",
            "freeze_status": "retained_background_companion",
            "meaning": "cell-average radiant exposure",
            "downstream_allowed": "background diagnostics; validation companion",
            "downstream_forbidden": "sole upper-tail target",
            "caveat": "may hide mixed-cell exposed pockets",
        },
        {
            "target_field": "tmrt_max_c",
            "target_role": "sensitivity_only",
            "freeze_status": "retained_sensitivity_only",
            "meaning": "pixel-level extreme / outlier sensitivity",
            "downstream_allowed": "outlier and edge-case sensitivity",
            "downstream_forbidden": "primary target; observed truth; risk",
            "caveat": "too sensitive for canonical target use",
        },
    ]
    for metric in THRESHOLD_METRICS:
        threshold = metric.rsplit("_", 1)[-1]
        rows.append(
            {
                "target_field": metric,
                "target_role": "optional_threshold_area_companion",
                "freeze_status": "retained_optional_companion",
                "meaning": f"percentage of focus-cell pixels above {threshold} C radiant threshold",
                "downstream_allowed": "threshold-area diagnostics; validation companion",
                "downstream_forbidden": "policy threshold; official warning; risk by itself",
                "caveat": "thresholds are analytical companions, not policy thresholds yet",
            }
        )
    if provisional_present:
        rows.append(
            {
                "target_field": "m_rad_pct_provisional_legacy",
                "target_role": "legacy_n24_internal_modifier",
                "freeze_status": "not_canonical",
                "meaning": "prior N24 provisional percentile rank, preserved only for traceability",
                "downstream_allowed": "legacy comparison and B4 traceability",
                "downstream_forbidden": "canonical B5 modifier; final AOI-wide modifier",
                "caveat": "use m_rad_pct01 for B5-forward method checks",
            }
        )
    return pd.DataFrame(rows)


def reference_rules_table() -> pd.DataFrame:
    """Return canonical reference-domain rules."""
    return pd.DataFrame(
        [
            {
                "reference_domain_version": "n24_internal_b3",
                "eligible_cells": "completed N24 cells only",
                "intended_use": "B4/B5 evidence and traceability only",
                "canonical_for_final_aoi_mrad": False,
                "rule": "same-hour same-scenario median reference",
                "caveat": "not final AOI-wide M_rad",
            },
            {
                "reference_domain_version": "n150_training_future",
                "eligible_cells": "future N150 executed SOLWEIG sample",
                "intended_use": "surrogate training / validation",
                "canonical_for_final_aoi_mrad": False,
                "rule": "same-hour same-scenario median reference",
                "caveat": "future sample must be frozen before label generation",
            },
            {
                "reference_domain_version": "full_aoi_prediction_future",
                "eligible_cells": "all eligible predicted cells after accepted surrogate inference",
                "intended_use": "final AOI-wide modifier ranking",
                "canonical_for_final_aoi_mrad": True,
                "rule": "same-hour same-scenario median reference",
                "caveat": "requires accepted surrogate and full-domain prediction contract",
            },
            {
                "reference_domain_version": "sensitivity_reference_optional",
                "eligible_cells": "future shaded-reference or typology-specific subset",
                "intended_use": "optional sensitivity analysis",
                "canonical_for_final_aoi_mrad": False,
                "rule": "explicitly labelled alternative reference",
                "caveat": "not canonical in B5",
            },
        ]
    )


def write_reference_rules_md(path: Path) -> None:
    """Write the reference-domain rules Markdown note."""
    text = """# System B Modifier Reference Rules

## Status
PASS - reference rule frozen for next-scale use.

## Canonical calculation

For each `reference_domain_version`, `hour_sgt`, and `scenario`:

```text
tmrt_ref_p90_c(hour, scenario, reference_domain_version)
= median(tmrt_p90_c across eligible cells in that reference domain, same hour, same scenario)

delta_tmrt_p90_c(cell, hour, scenario)
= tmrt_p90_c(cell, hour, scenario) - tmrt_ref_p90_c(hour, scenario, reference_domain_version)

m_rad_pct01(cell, hour, scenario)
= (rank_average(delta_tmrt_p90_c) - 1) / (n_reference_cells - 1)
```

## Rules

- The lowest reference-domain delta gets `0`.
- The highest reference-domain delta gets `1`.
- Ties use average rank.
- If `n_reference_cells = 1`, set `m_rad_pct01 = 0.5` and flag `insufficient_reference_domain`.
- Compute within the same hour and same scenario only.
- Never compare h10 against h13.
- Never compare `base` against `overhead_as_canopy` directly for rank unless scenario comparison is explicitly intended.
- Celsius ratios are forbidden: use difference plus rank, not division by mean Tmrt.

## Reference-domain versions

- `n24_internal_b3`: completed N24 cells only; B4/B5 evidence and traceability only; not final AOI-wide M_rad.
- `n150_training_future`: future N150 executed SOLWEIG sample; intended for surrogate training and validation.
- `full_aoi_prediction_future`: all eligible predicted cells after accepted surrogate inference; intended for final AOI-wide modifier ranking.
- `sensitivity_reference_optional`: shaded-reference or typology-specific references may be explored later, but are not canonical in B5.
"""
    write_text(path, text)


def schema_table() -> pd.DataFrame:
    """Return the future target output schema contract."""
    fields = [
        ("cell_id", "string", "required", "cell identifier"),
        ("hour_sgt", "integer", "required", "Singapore local hour"),
        ("scenario", "string", "required", "SOLWEIG scenario"),
        ("reference_domain_version", "string", "required", "reference domain used for modifier normalization"),
        ("target_version", "string", "required", "target contract version"),
        ("tmrt_mean_c", "float", "required_companion", "cell-average radiant exposure"),
        ("tmrt_p50_c", "float", "optional_companion", "median radiant exposure"),
        ("tmrt_p75_c", "float", "required_companion", "upper shoulder radiant exposure"),
        ("tmrt_p90_c", "float", "primary_target", "mixed-cell upper-tail radiant exposure"),
        ("tmrt_p95_c", "float", "required_companion", "higher-tail radiant exposure"),
        ("tmrt_max_c", "float", "sensitivity_only", "pixel-level extreme"),
        ("pct_pixels_tmrt_ge_40", "float", "optional_threshold_area_companion", "percent pixels at or above 40 C Tmrt"),
        ("pct_pixels_tmrt_ge_45", "float", "optional_threshold_area_companion", "percent pixels at or above 45 C Tmrt"),
        ("pct_pixels_tmrt_ge_50", "float", "optional_threshold_area_companion", "percent pixels at or above 50 C Tmrt"),
        ("pct_pixels_tmrt_ge_55", "float", "optional_threshold_area_companion", "percent pixels at or above 55 C Tmrt"),
        ("tmrt_ref_p90_c", "float", "reference", "same-hour same-scenario reference median p90"),
        ("delta_tmrt_p90_c", "float", "primary_modifier_delta", "p90 minus reference p90"),
        ("m_rad_pct01", "float", "normalized_modifier", "0-1 average-rank normalized delta"),
        ("target_quality_flag", "string", "required", "OK or explicit quality caveat"),
        ("source", "string", "required", "solweig_observed / surrogate_predicted / provisional_n24"),
        ("raw_solweig_available", "boolean", "required", "whether raw SOLWEIG output is locally available"),
        ("notes", "string", "optional", "free-text caveat"),
    ]
    rows = [{"field": field, "type": dtype, "requirement": req, "description": desc} for field, dtype, req, desc in fields]
    rows.extend(
        {
            "field": field,
            "type": "forbidden",
            "requirement": "forbidden_in_systemb_target_output",
            "description": "reserved for future/non-System-B contracts; not produced by B5 target outputs",
        }
        for field in FORBIDDEN_OUTPUT_FIELDS
    )
    return pd.DataFrame(rows)


def surrogate_contract_table() -> pd.DataFrame:
    """Return surrogate label contract rows."""
    return pd.DataFrame(
        [
            {
                "contract_item": "primary_supervised_label_candidate",
                "fields": "delta_tmrt_p90_c",
                "allowed_use": "surrogate regression label candidate",
                "forbidden_use": "local WBGT, hazard_score, risk_score, observed truth",
                "notes": "Preferred physical delta because it is reference-relative and in Celsius difference units.",
            },
            {
                "contract_item": "secondary_supervised_label_candidate",
                "fields": "tmrt_p90_c",
                "allowed_use": "secondary surrogate regression label candidate",
                "forbidden_use": "standalone modifier without reference-domain normalization",
                "notes": "May support direct p90 prediction before delta and rank derivation.",
            },
            {
                "contract_item": "companion_validation_labels",
                "fields": "tmrt_p75_c; tmrt_p95_c; tmrt_mean_c; tmrt_max_c; pct_pixels_tmrt_ge_40; pct_pixels_tmrt_ge_45; pct_pixels_tmrt_ge_50; pct_pixels_tmrt_ge_55",
                "allowed_use": "robustness and validation diagnostics",
                "forbidden_use": "automatic replacement of primary target without revised spec",
                "notes": "Keep p90 from becoming a single-metric blind spot.",
            },
            {
                "contract_item": "post_prediction_modifier",
                "fields": "m_rad_pct01",
                "allowed_use": "computed after prediction from delta/p90 values within the chosen reference domain",
                "forbidden_use": "rank-only sole regression label unless explicitly justified",
                "notes": "B5 freezes the rank method, not a final AOI map.",
            },
        ]
    )


def claim_boundary_table(target_family: pd.DataFrame) -> pd.DataFrame:
    """Return downstream claim boundary matrix."""
    rows = []
    for row in target_family.to_dict("records"):
        rows.append(
            {
                "target_field": row["target_field"],
                "allowed_downstream_use": row["downstream_allowed"],
                "forbidden_downstream_use": row["downstream_forbidden"],
                "required_caveat": row["caveat"],
            }
        )
    for field in FORBIDDEN_OUTPUT_FIELDS:
        rows.append(
            {
                "target_field": field,
                "allowed_downstream_use": "none in System B target contract",
                "forbidden_downstream_use": "must not appear in System B target freeze outputs",
                "required_caveat": "belongs to future WBGT/hazard/risk/official-warning contracts, not B5",
            }
        )
    return pd.DataFrame(rows)


def compute_b5_method_check(root: Path, output_dir: Path) -> dict[str, Any]:
    """Compute the N24-internal B5 reference/delta/rank method check."""
    focus = pd.read_csv(repo_path(root, FOCUS_SUMMARY))
    provisional = load_csv_if_present(repo_path(root, PROVISIONAL_MODIFIER))
    focus = focus.copy()
    if "hour" in focus.columns:
        focus["hour_sgt"] = focus["hour"].astype(int)
    required = {"cell_id", "scenario", "hour_sgt", "tmrt_p90_c"}
    missing = sorted(required.difference(focus.columns))
    if missing:
        raise ValueError(f"Focus summary missing required columns for B5 method check: {missing}")

    group_cols = ["hour_sgt", "scenario"]
    refs = (
        focus.groupby(group_cols, dropna=False)
        .agg(tmrt_ref_p90_c=("tmrt_p90_c", "median"), n_reference_cells=("cell_id", "nunique"))
        .reset_index()
    )
    refs["reference_domain_version"] = "n24_internal_b3"
    refs["reference_rule"] = "same_hour_same_scenario_reference_domain_median"
    refs["reference_caveat"] = "N24-internal method check only; not final AOI-wide M_rad"
    method = focus.merge(refs[group_cols + ["tmrt_ref_p90_c", "n_reference_cells", "reference_domain_version"]], on=group_cols, how="left")
    method["delta_tmrt_p90_c"] = method["tmrt_p90_c"] - method["tmrt_ref_p90_c"]
    ranks = method.groupby(group_cols)["delta_tmrt_p90_c"].rank(method="average", ascending=True)
    denom = method["n_reference_cells"] - 1
    method["m_rad_pct01"] = (ranks - 1) / denom
    one_cell = method["n_reference_cells"].eq(1)
    method.loc[one_cell, "m_rad_pct01"] = 0.5
    method["target_quality_flag"] = "ok"
    method.loc[one_cell, "target_quality_flag"] = "insufficient_reference_domain"
    method["target_version"] = "systemb_target_family_v0_1_b5"
    method["source"] = "provisional_n24"
    method["raw_solweig_available"] = True
    method["notes"] = "N24-internal B5 method check only; not final AOI-wide modifier"

    keep_cols = [
        "cell_id",
        "hour_sgt",
        "scenario",
        "reference_domain_version",
        "target_version",
        "tmrt_mean_c",
        "tmrt_p50_c",
        "tmrt_p75_c",
        "tmrt_p90_c",
        "tmrt_p95_c",
        "tmrt_max_c",
        *THRESHOLD_METRICS,
        "tmrt_ref_p90_c",
        "delta_tmrt_p90_c",
        "m_rad_pct01",
        "target_quality_flag",
        "source",
        "raw_solweig_available",
        "notes",
    ]
    keep_cols = [col for col in keep_cols if col in method.columns]

    comparison = method[["cell_id", "hour_sgt", "scenario", "delta_tmrt_p90_c", "m_rad_pct01"]].copy()
    legacy_col = None
    if not provisional.empty:
        prov = provisional.copy()
        if "hour" in prov.columns:
            prov["hour_sgt"] = prov["hour"].astype(int)
        rename_cols = {}
        if "m_rad_pct" in prov.columns:
            rename_cols["m_rad_pct"] = "m_rad_pct_provisional_legacy"
            legacy_col = "m_rad_pct_provisional_legacy"
        elif "m_rad_pct_provisional" in prov.columns:
            rename_cols["m_rad_pct_provisional"] = "m_rad_pct_provisional_legacy"
            legacy_col = "m_rad_pct_provisional_legacy"
        if "delta_tmrt_p90_c" in prov.columns:
            rename_cols["delta_tmrt_p90_c"] = "delta_tmrt_p90_c_provisional_legacy"
        prov = prov.rename(columns=rename_cols)
        merge_cols = ["cell_id", "hour_sgt", "scenario"]
        prov_cols = merge_cols + [col for col in ["delta_tmrt_p90_c_provisional_legacy", "m_rad_pct_provisional_legacy", "reference_definition"] if col in prov.columns]
        comparison = comparison.merge(prov[prov_cols], on=merge_cols, how="left")
        if legacy_col and legacy_col in comparison.columns:
            comparison["m_rad_pct01_minus_legacy"] = comparison["m_rad_pct01"] - comparison[legacy_col]
            method = method.merge(comparison[merge_cols + [legacy_col, "m_rad_pct01_minus_legacy"]], on=merge_cols, how="left")
        if "delta_tmrt_p90_c_provisional_legacy" in comparison.columns:
            comparison["delta_tmrt_p90_c_minus_legacy"] = comparison["delta_tmrt_p90_c"] - comparison["delta_tmrt_p90_c_provisional_legacy"]

    method_cols = keep_cols + [col for col in ["m_rad_pct_provisional_legacy", "m_rad_pct01_minus_legacy"] if col in method.columns]
    method[method_cols].to_csv(output_dir / "n24_modifier_targets_b5_method_check.csv", index=False)
    refs.to_csv(output_dir / "n24_reference_values_b5.csv", index=False)
    comparison.to_csv(output_dir / "n24_modifier_method_comparison.csv", index=False)

    diff_summary = "no legacy provisional modifier available"
    if "m_rad_pct01_minus_legacy" in comparison.columns:
        max_abs = float(comparison["m_rad_pct01_minus_legacy"].abs().max())
        changed = int((comparison["m_rad_pct01_minus_legacy"].abs() > 1e-12).sum())
        diff_summary = f"{changed} rows differ from legacy m_rad_pct; max abs difference {max_abs:.6f}"
    return {
        "method_rows": len(method),
        "reference_rows": len(refs),
        "comparison_rows": len(comparison),
        "legacy_difference_summary": diff_summary,
    }


def write_configs(root: Path) -> None:
    """Write example YAML configs for B5 target freeze and reference definition."""
    CONFIG_DIR_ABS = repo_path(root, CONFIG_DIR)
    CONFIG_DIR_ABS.mkdir(parents=True, exist_ok=True)
    common = """target_version: systemb_target_family_v0_1_b5
primary_target: tmrt_p90_c
primary_modifier_delta: delta_tmrt_p90_c
normalized_modifier: m_rad_pct01
reference_rule: same_hour_same_scenario_reference_domain_median
percentile_rank_rule: rank_average_minus_1_over_n_minus_1
reference_domain_versions:
  - n24_internal_b3
  - n150_training_future
  - full_aoi_prediction_future
scenarios:
  - base
  - overhead_as_canopy
hours_sgt:
  - 10
  - 12
  - 13
  - 15
  - 16
required_companions:
  - tmrt_p75_c
  - tmrt_p95_c
  - tmrt_mean_c
  - tmrt_max_c
optional_threshold_area_companions:
  - pct_pixels_tmrt_ge_40
  - pct_pixels_tmrt_ge_45
  - pct_pixels_tmrt_ge_50
  - pct_pixels_tmrt_ge_55
forbidden_claims:
  - local_wbgt
  - risk
  - observed_truth
  - official_warning
  - final_aoi_mrad_before_surrogate_or_full_aoi
"""
    write_text(
        CONFIG_DIR_ABS / "systemb_target_freeze_config.example.yaml",
        common
        + """output_contract:
  target_family_table: outputs/v12_systemb_target_freeze/systemb_target_family_freeze.csv
  schema_table: outputs/v12_systemb_target_freeze/systemb_target_output_schema.csv
  surrogate_label_contract: outputs/v12_systemb_target_freeze/systemb_surrogate_label_contract.csv
  claim_boundary_matrix: outputs/v12_systemb_target_freeze/systemb_downstream_claim_boundary_matrix.csv
non_goals:
  - no_solweig_rerun
  - no_qgis
  - no_raw_raster_reads
  - no_local_wbgt
  - no_hazard_score
  - no_risk_score
  - no_surrogate_training
  - no_system_a_b_coupling
""",
    )
    write_text(
        CONFIG_DIR_ABS / "systemb_modifier_reference_definition.example.yaml",
        common
        + """reference_domains:
  n24_internal_b3:
    eligible_cells: completed_n24_cells_only
    intended_use: b4_b5_evidence_and_traceability_only
    final_aoi_mrad: false
  n150_training_future:
    eligible_cells: future_n150_executed_solweig_sample
    intended_use: surrogate_training_and_validation
    final_aoi_mrad: false
  full_aoi_prediction_future:
    eligible_cells: all_eligible_predicted_cells_after_accepted_surrogate_inference
    intended_use: final_aoi_modifier_ranking
    final_aoi_mrad: true
  sensitivity_reference_optional:
    eligible_cells: shaded_reference_or_typology_specific_subset
    intended_use: optional_sensitivity_analysis
    final_aoi_mrad: false
ranking_edge_cases:
  ties: average_rank
  n_reference_cells_eq_1:
    m_rad_pct01: 0.5
    target_quality_flag: insufficient_reference_domain
forbidden_normalization:
  - celsius_ratio
  - division_by_mean_tmrt
  - cross_hour_rank
  - cross_scenario_rank_unless_explicit_scenario_comparison
""",
    )


def write_docs(root: Path) -> None:
    """Write the B5 Chinese note and append the B5 addendum to the modifier spec."""
    freeze_doc = repo_path(root, DOCS_DIR / "OpenHeat_SystemB_target_freeze_modifier_reference_CN.md")
    modifier_spec = repo_path(root, DOCS_DIR / "OpenHeat_modifier_target_spec_CN.md")
    freeze_text = """# OpenHeat System B 目标冻结与修饰因子参考域定义（Sprint B5）

## 1. 为什么需要 B5

B5 的任务不是再跑 SOLWEIG，也不是生成地图，而是在 B3 完成 N24 执行、B4 完成目标稳健性复核之后，把 System B 的目标家族、参考域规则、修饰因子归一化方法、输出 schema 和下游声明边界固定下来。这样后续 B6/N150、代理模型和 System A/B 条件化耦合不会各自重新定义目标。

## 2. B4 已经决定了什么

B4 的结论是 PASS。`tmrt_p90_c` 被保留为 N24 支持的 primary candidate：它代表混合 100m cell 内较高尾部的辐射暴露，而不是观测真值。`tmrt_p75_c`、`tmrt_p95_c`、`tmrt_mean_c`、`tmrt_max_c` 和四个 threshold-area 指标继续保留为 companion / sensitivity。B4 中的 delta 和 `m_rad` 仍然是 N24 内部的派生/临时量，不是最终 AOI-wide `M_rad`。

## 3. 现在冻结什么

- 目标家族：主目标为 `tmrt_p90_c`，主物理 delta 为 `delta_tmrt_p90_c`，规范化候选修饰因子为 `m_rad_pct01`。
- 参考规则：同一 `reference_domain_version`、同一小时、同一 scenario 内，用 eligible cells 的 `tmrt_p90_c` 中位数作为 `tmrt_ref_p90_c`。
- 归一化方法：先计算差值，再在同小时同 scenario 参考域内做 average rank，公式为 `(rank_average - 1) / (n_reference_cells - 1)`。
- schema / contract：未来 target 表必须显式写出 target version、reference domain、source、quality flag 和 companion metrics。

## 4. 现在不冻结什么

B5 不冻结最终 AOI-wide `M_rad` map，不产生 N150 输出，不训练 surrogate，不计算 `hazard_score`，不计算 `risk_score`，不计算 local WBGT，也不做 System A/B coupling。

## 5. 为什么 p90 是主目标但不能单独使用

`tmrt_p90_c` 比 mean 更能捕捉部分遮阴 cell 内残留的高辐射口袋，又比 max 更少受单个像元和边缘异常影响。它适合作为 System B 的主物理目标候选。但 p90 仍然是 SOLWEIG 模拟派生的 cell-level 指标，不是观测真值；因此必须同时保留 p75、p95、mean、max 和 threshold-area companions，用来检查肩部、尾部、背景均值、极端像元和热面积占比。

## 6. delta 与 m_rad_pct01 的区别

`delta_tmrt_p90_c` 是物理差值：

```text
delta_tmrt_p90_c = tmrt_p90_c - tmrt_ref_p90_c
```

它仍然以摄氏度 Tmrt 差值表达。`m_rad_pct01` 是排序归一化修饰因子：

```text
m_rad_pct01 = (rank_average(delta_tmrt_p90_c) - 1) / (n_reference_cells - 1)
```

它表达的是在同小时、同 scenario、同参考域内的相对位置。禁止使用摄氏度比值，例如把 cell Tmrt 除以平均 Tmrt。

## 7. 为什么 N24 reference 只能内部使用

`n24_internal_b3` 只包含 24 个已完成 N24 cells。它足够用于 B4/B5 的方法检查和可追溯性，但不能代表完整 AOI，也不能产生最终 AOI-wide `M_rad`。最终 AOI-wide modifier 只能在 N150 标签、可接受的 surrogate 和 full-AOI prediction contract 成立后再定义。

## 8. N150 与未来 surrogate 应如何使用

B6 应先设计并冻结 N150 sample/manifest，再按 B5 target family 生成 SOLWEIG 标签。未来 surrogate 的优先 supervised label candidate 是 `delta_tmrt_p90_c`，次级候选是 `tmrt_p90_c`；`m_rad_pct01` 应在预测后按 reference domain 计算，不应默认作为唯一回归标签，除非另有明确论证。

## 9. 声明边界

这些 B5 输出不是 local WBGT，不是 risk，不是 observed truth，不是 official warning，也不是 System A/B coupling。允许的表述是：System B 现在拥有一个 N24 支持、面向下一尺度的辐射目标家族与修饰因子参考域定义。
"""
    write_text(freeze_doc, freeze_text)

    addendum = """\n\n---\n\n# Sprint B5 Addendum - System B Target Freeze / Modifier Reference Definition\n\n**Status:** method frozen for next-scale use; N24 evidence only.  \n**Target version:** `systemb_target_family_v0_1_b5`\n\nB5 updates this earlier modifier target specification after the B4 N24 robustness re-audit. The current canonical naming is:\n\n```text\nprimary_target = tmrt_p90_c\nprimary_modifier_delta = delta_tmrt_p90_c\nnormalized_modifier = m_rad_pct01\nreference_rule = same_hour_same_scenario_reference_domain_median\npercentile_rank_rule = rank_average_minus_1_over_n_minus_1\n```\n\nThe B5 canonical rank rule is explicitly:\n\n```text\nm_rad_pct01 = (rank_average(delta_tmrt_p90_c) - 1) / (n_reference_cells - 1)\n```\n\nIf `n_reference_cells = 1`, set `m_rad_pct01 = 0.5` and flag `insufficient_reference_domain`.\n\nReference-domain versions are now named as:\n\n- `n24_internal_b3`: completed N24 cells only, for B4/B5 traceability, not final AOI-wide M_rad.\n- `n150_training_future`: future N150 executed SOLWEIG sample for training and validation.\n- `full_aoi_prediction_future`: future full-domain predicted cells after accepted surrogate inference.\n- `sensitivity_reference_optional`: optional shaded/typology reference sensitivity, not canonical in B5.\n\nB5 preserves the older N24 provisional percentile modifier only as legacy traceability. Use `m_rad_pct01` for B5-forward method checks. This specification still forbids treating System B target outputs as local WBGT, observed truth, risk, official warning, hazard_score, or completed System A/B coupling.\n"""
    if modifier_spec.exists():
        existing = read_text(modifier_spec)
        if "Sprint B5 Addendum - System B Target Freeze" not in existing:
            write_text(modifier_spec, existing.rstrip() + addendum)
    else:
        write_text(
            modifier_spec,
            "# OpenHeat Modifier Target Specification CN\n\n"
            "本文档定义 System B 的 SOLWEIG/Tmrt 修饰因子目标。"
            + addendum,
        )


def write_report(output_dir: Path, status: str, metadata: dict[str, Any], method_summary: dict[str, Any]) -> None:
    """Write the main B5 report."""
    report = f"""# Sprint B5 — System B Target Freeze / Modifier Reference Definition

## Status
{status}

## Scope
- target freeze / reference definition only
- no QGIS
- no SOLWEIG rerun
- no raw raster reads
- no local WBGT
- no hazard_score
- no risk_score
- no surrogate
- no System A/B coupling

## Inputs
- B3 focus summary rows: `{metadata.get("focus_rows")}`
- B3 base-vs-overhead delta rows: `{metadata.get("delta_rows")}`
- B3 provisional modifier rows: `{metadata.get("provisional_rows")}`
- Unique N24 cells: `{metadata.get("unique_cells")}`
- Scenarios: `{", ".join(metadata.get("scenarios", []))}`
- Hours: `{", ".join(str(hour) for hour in metadata.get("hours", []))}`

## B4 decision carried forward
- `tmrt_p90_c` = N24-supported primary candidate.
- `tmrt_p75_c`, `tmrt_p95_c`, `tmrt_mean_c`, and `tmrt_max_c` remain companions/sensitivities.
- `pct_pixels_tmrt_ge_40/45/50/55` remain optional threshold-area companions.
- Delta and modifier rows are derived/provisional in B4 and are formalized here only as a method contract.

## Frozen target family
The frozen target family is written to `systemb_target_family_freeze.csv`. The primary physical target is `tmrt_p90_c`, the primary physical modifier delta is `delta_tmrt_p90_c`, and the normalized modifier candidate is `m_rad_pct01`.

## Reference definition
`tmrt_ref_p90_c` is the same-hour, same-scenario median `tmrt_p90_c` across eligible cells in a declared `reference_domain_version`. `delta_tmrt_p90_c` is the cell p90 minus that reference. `m_rad_pct01` is `(rank_average - 1) / (n_reference_cells - 1)`. The method forbids Celsius ratios and never ranks across hours or across scenarios unless an explicit scenario comparison is intended.

## N24 method check
- B5 method-check rows: `{method_summary.get("method_rows")}`
- Reference rows: `{method_summary.get("reference_rows")}`
- Comparison rows: `{method_summary.get("comparison_rows")}`
- Legacy comparison: {method_summary.get("legacy_difference_summary")}

If the existing provisional `m_rad_pct` differs, it is preserved as legacy/provisional and not overwritten. B5 recommends `m_rad_pct01` going forward.

## Schema / downstream contract
The output schema is written to `systemb_target_output_schema.csv`. The surrogate label contract is written to `systemb_surrogate_label_contract.csv`. The preferred future supervised label candidate is `delta_tmrt_p90_c`; `tmrt_p90_c` is secondary; companion labels remain required for validation context.

## Claim boundaries
Forbidden claims remain explicit: no local WBGT, no observed truth, no official warning, no hazard_score, no risk_score, no exposure/vulnerability score, no final AOI-wide M_rad before surrogate/full-AOI prediction, and no System A/B coupling.

## Next recommended action
B6 — N150 sample design + manifest using the B5 target family. Do not jump directly to surrogate until N150 labels exist.
"""
    write_text(output_dir / "sprint_b5_target_freeze_report.md", report)


def main() -> None:
    """Run Sprint B5 target freeze generation."""
    args = parse_args()
    root = args.repo_root.resolve()
    output_dir = repo_path(root, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    validation_status, _validation, metadata = validate_b4(root, output_dir)
    if validation_status == "BLOCKED":
        write_report(output_dir, "BLOCKED", metadata, {"legacy_difference_summary": "not run because validation failed"})
        print("B5 status: BLOCKED")
        return

    provisional_present = repo_path(root, PROVISIONAL_MODIFIER).exists()
    target_family = target_family_table(provisional_present=provisional_present)
    reference_rules = reference_rules_table()
    schema = schema_table()
    surrogate_contract = surrogate_contract_table()
    claim_boundaries = claim_boundary_table(target_family)

    target_family.to_csv(output_dir / "systemb_target_family_freeze.csv", index=False)
    reference_rules.to_csv(output_dir / "systemb_modifier_reference_rules.csv", index=False)
    write_reference_rules_md(output_dir / "systemb_modifier_reference_rules.md")
    schema.to_csv(output_dir / "systemb_target_output_schema.csv", index=False)
    surrogate_contract.to_csv(output_dir / "systemb_surrogate_label_contract.csv", index=False)
    claim_boundaries.to_csv(output_dir / "systemb_downstream_claim_boundary_matrix.csv", index=False)

    method_summary = compute_b5_method_check(root, output_dir)
    write_configs(root)
    write_docs(root)
    write_report(output_dir, "PASS", metadata, method_summary)
    print("B5 status: PASS")
    print(f"Target family rows: {len(target_family)}")
    print(f"N24 method-check rows: {method_summary['method_rows']}")
    print(method_summary["legacy_difference_summary"])


if __name__ == "__main__":
    main()
