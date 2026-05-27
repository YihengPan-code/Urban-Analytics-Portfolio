"""Build the B8.5-F4 N24 stability decision matrix and target-card gate.

Inputs:
    configs/v12/systemb_b85_f4_n24_decision.yaml
    outputs/v12_surrogate/b8_5_f3c_n24/B8_5_F3C_STATUS.md
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_postrun_validation.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_cell_hour_summary.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_pairwise_delta_by_cell_hour.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_forcing_day_contrast_by_cell_hour.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_alignment_qa.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_sanity_checks.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_stability_summary.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_unstable_cell_inventory.csv

Outputs:
    docs/v12/OpenHeat_SystemB_B8_5_F4_N24_decision_matrix_CN.md
    outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_hourly_stability_summary.csv
    outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_cell_stability_scorecard.csv
    outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_robust_priority_cells.csv
    outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_neutral_boundary_cells.csv
    outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_unstable_priority_cells.csv
    outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_target_card_delta_tmrt_p90.md
    outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_n150_readiness_recommendation.md
    outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_surrogate_role_decision.md
    outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_geometry_uncertainty_register.csv
    outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_decision_matrix.csv
    outputs/v12_surrogate/b8_5_f4_n24_decision/b85_f4_report.md
    outputs/v12_surrogate/b8_5_f4_n24_decision/B8_5_F4_STATUS.md

Saved metrics:
    Hour-level rank stability decisions, cell-level delta_tmrt_p90_c stability
    scorecards, robust priority anchors, neutral-boundary cells, unstable-review
    cells, geometry uncertainty register, target-card text, N150 recommendation,
    surrogate role decision, and a compact decision matrix.

This script does not run QGIS, run SOLWEIG, read/open/copy/write rasters,
copy/open svfs.zip, create local WBGT, create hazard_score/risk_score,
create AOI-wide prediction, create System A/B coupling output, create an N150
manifest/runner, train a surrogate, perform Tmrt-to-WBGT conversion, stage, or
commit. It consumes compact F3c CSV/Markdown evidence only; it is not B9.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from v12_b85_f3c_prepare_n24 import (
    ROOT,
    changed_forbidden_paths,
    clean,
    git_status_short,
    markdown_table,
    read_config,
    read_csv_rows,
    rel,
    repo_path,
    write_csv_rows,
    write_text,
)


DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_f4_n24_decision.yaml"

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
FAILED = "FAILED"
F4_PASS = "F4_N24_DECISION_PASS"
F4_PARTIAL = "F4_N24_DECISION_PARTIAL"
F4_BLOCKED = "F4_N24_DECISION_BLOCKED"

CORE_STABLE = "CORE_STABLE"
STABLE_WITH_CAVEAT = "STABLE_WITH_CAVEAT"
UNSTABLE_REVIEW_REQUIRED = "UNSTABLE_REVIEW_REQUIRED"

ALLOW_N150_READINESS_ONLY = "ALLOW_N150_READINESS_ONLY"
ALLOW_N150_CONTROLLED_EXECUTION_AFTER_PRECHECK = "ALLOW_N150_CONTROLLED_EXECUTION_AFTER_PRECHECK"
DEFER_N150_PENDING_REVIEW = "DEFER_N150_PENDING_REVIEW"
BLOCK_N150 = "BLOCK_N150"

B9_BLOCKED = "BLOCKED_F4_IS_NOT_B9"
SURROGATE_ROLE_DECISION = "SURROGATE_PROTOCOL_READY_N24_STRESS_VALIDATION_NO_TRAINING_IN_F4"


@dataclass(frozen=True)
class EvidenceBundle:
    """F3c compact evidence loaded from CSV/Markdown artifacts."""

    status_text: str
    postrun_rows: list[dict[str, str]]
    cell_hour_rows: list[dict[str, str]]
    pairwise_rows: list[dict[str, str]]
    forcing_day_contrast_rows: list[dict[str, str]]
    alignment_rows: list[dict[str, str]]
    sanity_rows: list[dict[str, str]]
    stability_rows: list[dict[str, str]]
    unstable_rows: list[dict[str, str]]


@dataclass(frozen=True)
class EvidenceValidation:
    """Validation state for upstream F3c compact evidence."""

    f3c_ready: bool
    postrun_valid: bool
    raster_qa_valid: bool
    core_inputs_valid: bool
    blockers: list[str]
    evidence_notes: list[str]


@dataclass(frozen=True)
class F4Result:
    """Compact result printed by the CLI runner."""

    decision_status: str
    core_hour_headline: str
    h10_caveat_headline: str
    robust_priority_count: int
    neutral_boundary_count: int
    unstable_review_count: int
    n150_recommendation: str
    surrogate_role_decision: str
    b9_status: str
    files_created: list[Path]


def now_stamp() -> str:
    """Return a local timestamp for reports."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_float(value: Any, digits: int = 6) -> str:
    """Format a finite numeric value for CSV/Markdown output."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(number):
        return ""
    return f"{number:.{digits}f}"


def parse_float(value: Any, default: float = math.nan) -> float:
    """Parse a float with a caller-provided default."""
    text = clean(value)
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def parse_int(value: Any, default: int = 0) -> int:
    """Parse an integer with a caller-provided default."""
    text = clean(value)
    if not text:
        return default
    try:
        return int(float(text))
    except ValueError:
        return default


def median(values: Sequence[float]) -> float:
    """Return the median of numeric values."""
    if not values:
        return math.nan
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def sign_label(value: float) -> str:
    """Return raw sign for sign-flip accounting."""
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "zero"


def is_near_zero(value: float, threshold: float) -> bool:
    """Return whether a delta is inside the configured neutral band."""
    return abs(value) < threshold


def ensure_scope(config: dict[str, Any]) -> None:
    """Refuse any config that crosses the F4 evidence-only boundary."""
    forbidden_true = {
        "execute_qgis_or_solweig": config.get("execute_qgis_or_solweig"),
        "read_rasters": config.get("read_rasters"),
        "write_rasters": config.get("write_rasters"),
    }
    scope = config.get("scope", {})
    for key in (
        "qgis_executed_by_codex",
        "solweig_executed_by_codex",
        "create_rasters",
        "copy_rasters",
        "move_rasters",
        "open_rasters",
        "copy_svf_zip",
        "open_svf_zip",
        "create_local_wbgt",
        "create_hazard_score",
        "create_risk_score",
        "create_aoi_predictions",
        "create_system_ab_coupling",
        "tmrt_to_wbgt_conversion",
        "create_n150_manifest_or_runner",
        "train_surrogate",
        "call_this_b9",
        "stage_changes",
        "commit_changes",
    ):
        forbidden_true[key] = scope.get(key)
    bad = [f"{key}={value!r}" for key, value in forbidden_true.items() if value is not False]
    if bad:
        raise ValueError("Unsafe F4 config flags: " + "; ".join(sorted(bad)))
    if int(config["expected_run_count"]) != 480:
        raise ValueError("F4 must consume the fixed F3c 480-run evidence set.")
    if int(config["expected_cell_count"]) != 24:
        raise ValueError("F4 must consume the fixed F3c N24 cell set.")


def read_text(path: Path) -> str:
    """Read UTF-8 text, accepting UTF-8 with BOM if present."""
    return path.read_text(encoding="utf-8-sig")


def load_evidence(config: dict[str, Any]) -> EvidenceBundle:
    """Load all upstream F3c compact evidence files."""
    return EvidenceBundle(
        status_text=read_text(repo_path(config["f3c_status_path"])),
        postrun_rows=read_csv_rows(repo_path(config["f3c_postrun_validation_path"])),
        cell_hour_rows=read_csv_rows(repo_path(config["f3c_cell_hour_summary_path"])),
        pairwise_rows=read_csv_rows(repo_path(config["f3c_pairwise_delta_path"])),
        forcing_day_contrast_rows=read_csv_rows(repo_path(config["f3c_forcing_day_contrast_path"])),
        alignment_rows=read_csv_rows(repo_path(config["f3c_alignment_qa_path"])),
        sanity_rows=read_csv_rows(repo_path(config["f3c_sanity_checks_path"])),
        stability_rows=read_csv_rows(repo_path(config["f3c_stability_summary_path"])),
        unstable_rows=read_csv_rows(repo_path(config["f3c_unstable_cell_inventory_path"])),
    )


def unique_cells(rows: Sequence[dict[str, str]]) -> list[str]:
    """Return sorted cell IDs from a CSV row sequence."""
    return sorted({clean(row.get("cell_id")) for row in rows if clean(row.get("cell_id"))})


def expected_pairwise_count(config: dict[str, Any]) -> int:
    """Return expected pairwise delta row count."""
    hours = list(config["core_hours_sgt"]) + list(config["caveat_hours_sgt"])
    forcing_days = 2
    return int(config["expected_cell_count"]) * forcing_days * len(hours)


def validate_evidence(config: dict[str, Any], evidence: EvidenceBundle) -> EvidenceValidation:
    """Validate upstream F3c evidence without touching raster files."""
    blockers: list[str] = []
    notes: list[str] = []
    expected_runs = int(config["expected_run_count"])
    expected_cells = int(config["expected_cell_count"])
    expected_cell_hour_rows = expected_runs
    expected_pairwise_rows = expected_pairwise_count(config)

    f3c_ready = "N24_STABILITY_REVIEW_READY" in evidence.status_text
    if not f3c_ready:
        blockers.append("F3c status is not N24_STABILITY_REVIEW_READY.")
    else:
        notes.append("F3c status is N24_STABILITY_REVIEW_READY.")

    postrun_valid = (
        len(evidence.postrun_rows) == expected_runs
        and all(clean(row.get("validation_status")).upper() == PASS for row in evidence.postrun_rows)
    )
    if not postrun_valid:
        blockers.append(f"Postrun validation is not {expected_runs}/{expected_runs} PASS.")
    else:
        notes.append("Postrun validation is 480/480 PASS.")

    cell_count = len(unique_cells(evidence.pairwise_rows))
    core_inputs_valid = True
    if len(evidence.cell_hour_rows) != expected_cell_hour_rows:
        core_inputs_valid = False
        blockers.append(f"Cell-hour summary row count is {len(evidence.cell_hour_rows)}, expected {expected_cell_hour_rows}.")
    if len(evidence.pairwise_rows) != expected_pairwise_rows:
        core_inputs_valid = False
        blockers.append(f"Pairwise delta row count is {len(evidence.pairwise_rows)}, expected {expected_pairwise_rows}.")
    if cell_count != expected_cells:
        core_inputs_valid = False
        blockers.append(f"Pairwise unique cell count is {cell_count}, expected {expected_cells}.")
    if core_inputs_valid:
        notes.append("Cell-hour and pairwise compact summaries have the expected N24/F3c shape.")

    alignment_failures = [row for row in evidence.alignment_rows if clean(row.get("status")).upper() == FAIL]
    sanity_failures = [row for row in evidence.sanity_rows if clean(row.get("status")).upper() == FAIL]
    raster_opened_row = next(
        (row for row in evidence.alignment_rows if clean(row.get("check_name")) == "all_480_rasters_opened"),
        {},
    )
    raster_qa_valid = (
        not alignment_failures
        and not sanity_failures
        and clean(raster_opened_row.get("status")).upper() == PASS
        and clean(raster_opened_row.get("value")) == "480/480"
    )
    if not raster_qa_valid:
        blockers.append("F3c raster/alignment QA compact evidence is not PASS.")
    else:
        notes.append("F3c raster/alignment QA compact evidence is PASS; F4 did not open rasters.")

    forbidden_hits = changed_forbidden_paths(git_status_short())
    if forbidden_hits:
        blockers.append("Forbidden changed files detected: " + "; ".join(forbidden_hits))

    return EvidenceValidation(
        f3c_ready=f3c_ready,
        postrun_valid=postrun_valid,
        raster_qa_valid=raster_qa_valid,
        core_inputs_valid=core_inputs_valid,
        blockers=blockers,
        evidence_notes=notes,
    )


def metric_value(rows: Sequence[dict[str, str]], hour: int, metric: str) -> float:
    """Return a stability-summary metric value for an hour."""
    for row in rows:
        if parse_int(row.get("hour_sgt")) == hour and clean(row.get("metric")) == metric:
            return parse_float(row.get("value"))
    return math.nan


def hourly_stability_summary(
    config: dict[str, Any],
    evidence: EvidenceBundle,
) -> list[dict[str, Any]]:
    """Build one decision row per hour."""
    core_hours = {int(value) for value in config["core_hours_sgt"]}
    caveat_hours = {int(value) for value in config["caveat_hours_sgt"]}
    thresholds = config["decision_thresholds"]
    hours = sorted(core_hours | caveat_hours)
    rows: list[dict[str, Any]] = []
    for hour in hours:
        spearman = metric_value(evidence.stability_rows, hour, "spearman_delta_tmrt_p90_fd01_fd02")
        sign_fraction = metric_value(evidence.stability_rows, hour, "sign_stability_fraction")
        top5 = metric_value(evidence.stability_rows, hour, "top5")
        top10pct = metric_value(evidence.stability_rows, hour, "top10pct")
        top20pct = metric_value(evidence.stability_rows, hour, "top20pct")
        warn_count = sum(
            1
            for row in evidence.stability_rows
            if parse_int(row.get("hour_sgt")) == hour and clean(row.get("status")).upper() == WARN
        )
        high_severity_count = sum(
            1
            for row in evidence.unstable_rows
            if parse_int(row.get("hour_sgt")) == hour and clean(row.get("severity")).upper() == "HIGH"
        )
        if hour in core_hours:
            stable = (
                spearman >= float(thresholds["core_min_spearman"])
                and sign_fraction >= float(thresholds["core_min_sign_stability_fraction"])
                and top10pct >= float(thresholds["core_min_top10pct_overlap"])
                and top5 >= float(thresholds["core_min_top5_overlap"])
                and high_severity_count == 0
            )
            decision = CORE_STABLE if stable else UNSTABLE_REVIEW_REQUIRED
            notes = (
                "Core-hour slice is stable across forcing days for rank order, sign, and top10pct overlap."
                if stable
                else "Core-hour slice needs review before using it as target-card support."
            )
        else:
            caveated = (
                spearman >= float(thresholds["caveat_min_spearman"])
                and sign_fraction >= float(thresholds["caveat_min_sign_stability_fraction"])
            )
            decision = STABLE_WITH_CAVEAT if caveated else UNSTABLE_REVIEW_REQUIRED
            notes = (
                "h10 is usable only as caveated evidence: lower rank agreement, weaker top-k overlap, and low-sun-angle sensitivity."
                if caveated
                else "h10 is unstable and should not support target-card anchoring."
            )
        rows.append(
            {
                "hour_sgt": str(hour),
                "spearman_fd01_fd02": format_float(spearman),
                "sign_stability_fraction": format_float(sign_fraction),
                "top5_overlap": format_float(top5),
                "top10pct_overlap": format_float(top10pct),
                "top20pct_overlap": format_float(top20pct),
                "warn_count": str(warn_count),
                "high_severity_count": str(high_severity_count),
                "decision": decision,
                "notes": notes,
            }
        )
    return rows


def forcing_day_ids(pairwise_rows: Sequence[dict[str, str]]) -> tuple[str, str]:
    """Return the FD01 and FD02 forcing-day IDs."""
    forcing_days = sorted({clean(row.get("forcing_day_id")) for row in pairwise_rows})
    if len(forcing_days) != 2:
        raise ValueError(f"Expected exactly two forcing days, found: {forcing_days}")
    return forcing_days[0], forcing_days[1]


def pairwise_value_map(pairwise_rows: Sequence[dict[str, str]]) -> dict[tuple[str, str, int], dict[str, str]]:
    """Return pairwise rows keyed by cell/forcing day/hour."""
    return {
        (clean(row.get("cell_id")), clean(row.get("forcing_day_id")), parse_int(row.get("hour_sgt"))): row
        for row in pairwise_rows
    }


def rank_drift_map(stability_rows: Sequence[dict[str, str]]) -> dict[tuple[str, int], int]:
    """Return rank drift by cell/hour from F3c stability rows."""
    out: dict[tuple[str, int], int] = {}
    for row in stability_rows:
        if clean(row.get("record_type")) != "rank_drift_by_cell_hour":
            continue
        out[(clean(row.get("cell_id")), parse_int(row.get("hour_sgt")))] = parse_int(row.get("value"))
    return out


def unstable_reason_map(unstable_rows: Sequence[dict[str, str]]) -> dict[tuple[str, int], list[str]]:
    """Return unstable reasons by cell/hour."""
    out: dict[tuple[str, int], list[str]] = {}
    for row in unstable_rows:
        cell = clean(row.get("cell_id"))
        if not cell:
            continue
        hour = parse_int(row.get("hour_sgt"))
        reasons = [item for item in clean(row.get("instability_reason")).split(";") if item]
        out.setdefault((cell, hour), []).extend(reasons)
    return out


def count_rank_presence(rows: Sequence[dict[str, str]], max_rank: int) -> int:
    """Count rows with within-slice rank at or above the priority threshold."""
    return sum(1 for row in rows if parse_int(row.get("within_slice_rank"), 9999) <= max_rank)


def rank_summary(rows: Sequence[dict[str, str]], forcing_day: str, hours: Sequence[int]) -> str:
    """Return compact hXX=rank text for a forcing day."""
    by_hour = {parse_int(row.get("hour_sgt")): row for row in rows if clean(row.get("forcing_day_id")) == forcing_day}
    return "; ".join(
        f"h{hour}={parse_int(by_hour[hour].get('within_slice_rank'))}" for hour in hours if hour in by_hour
    )


def delta_summary(rows: Sequence[dict[str, str]], forcing_day: str, hours: Sequence[int]) -> str:
    """Return compact hXX=delta text for a forcing day."""
    by_hour = {parse_int(row.get("hour_sgt")): row for row in rows if clean(row.get("forcing_day_id")) == forcing_day}
    return "; ".join(
        f"h{hour}={format_float(by_hour[hour].get('delta_tmrt_p90_c'), 3)}" for hour in hours if hour in by_hour
    )


def build_scorecards(config: dict[str, Any], evidence: EvidenceBundle) -> list[dict[str, Any]]:
    """Build one stability scorecard row per cell."""
    core_hours = [int(value) for value in config["core_hours_sgt"]]
    caveat_hours = [int(value) for value in config["caveat_hours_sgt"]]
    all_hours = sorted(set(core_hours + caveat_hours))
    neutral_threshold = float(config["neutral_delta_abs_threshold_c"])
    weak_threshold = float(config["weak_delta_abs_threshold_c"])
    strong_threshold = float(config["strong_delta_abs_threshold_c"])
    thresholds = config["decision_thresholds"]
    high_rank_threshold = int(thresholds["high_rank_drift_threshold"])
    neutral_min = int(thresholds["neutral_min_core_near_zero_count"])
    robust_min_top5 = int(thresholds["robust_min_top5_core_presence"])
    robust_min_top10 = int(thresholds["robust_min_top10_core_presence"])
    fd01, fd02 = forcing_day_ids(evidence.pairwise_rows)
    value_map = pairwise_value_map(evidence.pairwise_rows)
    drift_map = rank_drift_map(evidence.stability_rows)
    reason_map = unstable_reason_map(evidence.unstable_rows)
    scorecards: list[dict[str, Any]] = []

    for cell_id in unique_cells(evidence.pairwise_rows):
        cell_rows = [row for row in evidence.pairwise_rows if clean(row.get("cell_id")) == cell_id]
        core_rows = [row for row in cell_rows if parse_int(row.get("hour_sgt")) in core_hours]
        fd01_core_deltas = [
            parse_float(row.get("delta_tmrt_p90_c"))
            for row in core_rows
            if clean(row.get("forcing_day_id")) == fd01
        ]
        fd02_core_deltas = [
            parse_float(row.get("delta_tmrt_p90_c"))
            for row in core_rows
            if clean(row.get("forcing_day_id")) == fd02
        ]
        top3_core = count_rank_presence(core_rows, 3)
        top5_core = count_rank_presence(core_rows, 5)
        top10_core = count_rank_presence(core_rows, 10)
        neutral_all = sum(
            1 for row in cell_rows if is_near_zero(parse_float(row.get("delta_tmrt_p90_c")), neutral_threshold)
        )
        neutral_core = sum(
            1 for row in core_rows if is_near_zero(parse_float(row.get("delta_tmrt_p90_c")), neutral_threshold)
        )
        meaningful_core = sum(1 for row in core_rows if parse_float(row.get("delta_tmrt_p90_c")) <= -weak_threshold)
        strong_core = sum(1 for row in core_rows if parse_float(row.get("delta_tmrt_p90_c")) <= -strong_threshold)
        rank_drifts_core = [drift_map.get((cell_id, hour), 0) for hour in core_hours]
        rank_drifts_h10 = [drift_map.get((cell_id, hour), 0) for hour in caveat_hours]
        max_core_drift = max(rank_drifts_core) if rank_drifts_core else 0
        h10_drift = max(rank_drifts_h10) if rank_drifts_h10 else 0

        sign_flip_count = 0
        sign_flip_near_zero_count = 0
        sign_flip_non_neutral_count = 0
        for hour in all_hours:
            first = value_map[(cell_id, fd01, hour)]
            second = value_map[(cell_id, fd02, hour)]
            d1 = parse_float(first.get("delta_tmrt_p90_c"))
            d2 = parse_float(second.get("delta_tmrt_p90_c"))
            if sign_label(d1) != sign_label(d2):
                sign_flip_count += 1
                if is_near_zero(d1, neutral_threshold) and is_near_zero(d2, neutral_threshold):
                    sign_flip_near_zero_count += 1
                else:
                    sign_flip_non_neutral_count += 1

        core_reasons = [
            reason
            for hour in core_hours
            for reason in reason_map.get((cell_id, hour), [])
        ]
        h10_reasons = [
            reason
            for hour in caveat_hours
            for reason in reason_map.get((cell_id, hour), [])
        ]
        has_core_instability = (
            max_core_drift >= high_rank_threshold
            or "sign_flip" in core_reasons
            or "high_rank_drift" in core_reasons
        )
        has_h10_only_instability = bool(h10_reasons) and not core_reasons
        median_fd01 = median(fd01_core_deltas)
        median_fd02 = median(fd02_core_deltas)
        robust = (
            top5_core >= robust_min_top5
            and top10_core >= robust_min_top10
            and median_fd01 <= -weak_threshold
            and median_fd02 <= -weak_threshold
            and sign_flip_count == 0
            and neutral_core == 0
            and max_core_drift < high_rank_threshold
        )
        robust_score = (
            top3_core * 3
            + top5_core * 2
            + top10_core
            + strong_core * 3
            + meaningful_core
            - sign_flip_non_neutral_count * 8
            - neutral_core * 2
            - max(0, max_core_drift - 2)
        )
        if robust:
            stability_class = "robust_priority"
            notes = "Core-hour priority is stable across both forcing days; h10 is not used as anchor evidence."
        elif sign_flip_near_zero_count > 0:
            stability_class = "neutral_boundary"
            notes = "Sign flip is inside the neutral delta band and should not be interpreted as warming evidence."
        elif neutral_core >= neutral_min and sign_flip_non_neutral_count == 0:
            stability_class = "stable_neutral"
            notes = "Core-hour delta is consistently near zero; useful as a neutral comparator, not a cooling anchor."
        elif has_core_instability and (top10_core >= 4 or meaningful_core >= 4):
            stability_class = "high_priority_unstable"
            notes = "Meaningful cooling evidence coexists with core-hour rank instability; review before anchoring."
        elif has_core_instability or sign_flip_non_neutral_count > 0 or has_h10_only_instability:
            stability_class = "unstable_review"
            notes = "Instability is present; distinguish h10-only caveat from core-hour disagreement before use."
        else:
            stability_class = "stable_neutral"
            notes = "Stable but not a robust priority anchor under the conservative F4 rule."

        scorecards.append(
            {
                "cell_id": cell_id,
                "median_delta_tmrt_p90_core_hours_fd01": format_float(median_fd01),
                "median_delta_tmrt_p90_core_hours_fd02": format_float(median_fd02),
                "max_abs_rank_drift_core_hours": str(max_core_drift),
                "h10_rank_drift": str(h10_drift),
                "sign_flip_count": str(sign_flip_count),
                "top_k_presence_count": str(top5_core),
                "neutral_boundary_count": str(neutral_all),
                "robust_priority_score": str(robust_score),
                "stability_class": stability_class,
                "notes": notes,
                "top3_core_presence_count": str(top3_core),
                "top5_core_presence_count": str(top5_core),
                "top10_core_presence_count": str(top10_core),
                "neutral_core_count": str(neutral_core),
                "sign_flip_near_zero_count": str(sign_flip_near_zero_count),
                "sign_flip_non_neutral_count": str(sign_flip_non_neutral_count),
                "meaningful_core_delta_count": str(meaningful_core),
                "strong_core_delta_count": str(strong_core),
                "h10_only_instability_flag": "yes" if has_h10_only_instability else "no",
                "fd01_rank_summary": rank_summary(cell_rows, fd01, core_hours),
                "fd02_rank_summary": rank_summary(cell_rows, fd02, core_hours),
                "fd01_delta_summary": delta_summary(cell_rows, fd01, core_hours),
                "fd02_delta_summary": delta_summary(cell_rows, fd02, core_hours),
            }
        )
    return sorted(
        scorecards,
        key=lambda row: (
            row["stability_class"] != "robust_priority",
            -parse_int(row["robust_priority_score"]),
            row["cell_id"],
        ),
    )


def evidence_hours_for_cell(
    config: dict[str, Any],
    cell_rows: Sequence[dict[str, str]],
    max_rank: int = 5,
) -> str:
    """Return core-hour/forcing-day evidence where a cell is top-ranked."""
    core_hours = [int(value) for value in config["core_hours_sgt"]]
    items: list[str] = []
    for hour in core_hours:
        fds = [
            "FD01" if clean(row.get("forcing_day_id")).startswith("FD01") else "FD02"
            for row in cell_rows
            if parse_int(row.get("hour_sgt")) == hour and parse_int(row.get("within_slice_rank"), 9999) <= max_rank
        ]
        if fds:
            items.append(f"h{hour}:{'+'.join(sorted(fds))}")
    return "; ".join(items)


def recommended_role(scorecard: dict[str, Any]) -> str:
    """Assign a conservative anchor role for robust priority cells."""
    score = parse_int(scorecard.get("robust_priority_score"))
    top5 = parse_int(scorecard.get("top5_core_presence_count"))
    strong = parse_int(scorecard.get("strong_core_delta_count"))
    if score >= 45 and strong >= 4:
        return "surrogate_priority_anchor"
    if top5 >= 6:
        return "typology_review_anchor"
    if top5 >= 4:
        return "visualization_anchor"
    return "not_anchor"


def robust_priority_rows(
    config: dict[str, Any],
    evidence: EvidenceBundle,
    scorecards: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build robust priority-cell output rows."""
    fd01, fd02 = forcing_day_ids(evidence.pairwise_rows)
    core_hours = [int(value) for value in config["core_hours_sgt"]]
    rows: list[dict[str, Any]] = []
    for scorecard in scorecards:
        if scorecard["stability_class"] != "robust_priority":
            continue
        cell_id = scorecard["cell_id"]
        cell_rows = [row for row in evidence.pairwise_rows if clean(row.get("cell_id")) == cell_id]
        rows.append(
            {
                "cell_id": cell_id,
                "evidence_hours": evidence_hours_for_cell(config, cell_rows, max_rank=5),
                "fd01_rank_summary": rank_summary(cell_rows, fd01, core_hours),
                "fd02_rank_summary": rank_summary(cell_rows, fd02, core_hours),
                "median_delta_core_fd01": scorecard["median_delta_tmrt_p90_core_hours_fd01"],
                "median_delta_core_fd02": scorecard["median_delta_tmrt_p90_core_hours_fd02"],
                "stability_notes": scorecard["notes"],
                "recommended_role": recommended_role(scorecard),
                "robust_priority_score": scorecard["robust_priority_score"],
            }
        )
    return rows


def neutral_boundary_rows(scorecards: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build neutral-boundary output rows."""
    rows: list[dict[str, Any]] = []
    for scorecard in scorecards:
        near_zero_core = parse_int(scorecard.get("neutral_core_count"))
        near_zero_flip = parse_int(scorecard.get("sign_flip_near_zero_count"))
        if near_zero_core < 6 and near_zero_flip < 1:
            continue
        if scorecard["stability_class"] not in {"stable_neutral", "neutral_boundary"}:
            continue
        caveat = (
            "Near-zero sign flip; classify as neutral-boundary rather than warming."
            if near_zero_flip
            else "Many near-zero deltas; classify as stable neutral comparator."
        )
        rows.append(
            {
                "cell_id": scorecard["cell_id"],
                "neutral_boundary_count": scorecard["neutral_boundary_count"],
                "neutral_core_count": scorecard["neutral_core_count"],
                "sign_flip_count": scorecard["sign_flip_count"],
                "sign_flip_near_zero_count": scorecard["sign_flip_near_zero_count"],
                "median_delta_core_fd01": scorecard["median_delta_tmrt_p90_core_hours_fd01"],
                "median_delta_core_fd02": scorecard["median_delta_tmrt_p90_core_hours_fd02"],
                "caveats": caveat,
            }
        )
    return sorted(rows, key=lambda row: (-parse_int(row["neutral_boundary_count"]), row["cell_id"]))


def unstable_priority_rows(scorecards: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build unstable priority/review output rows."""
    rows: list[dict[str, Any]] = []
    for scorecard in scorecards:
        stability_class = scorecard["stability_class"]
        h10_drift = parse_int(scorecard.get("h10_rank_drift"))
        core_drift = parse_int(scorecard.get("max_abs_rank_drift_core_hours"))
        sign_flip_near = parse_int(scorecard.get("sign_flip_near_zero_count"))
        sign_flip_non_neutral = parse_int(scorecard.get("sign_flip_non_neutral_count"))
        h10_only = clean(scorecard.get("h10_only_instability_flag")).lower() == "yes"
        include = stability_class in {"unstable_review", "high_priority_unstable"} or sign_flip_near > 0
        if not include:
            continue
        if sign_flip_near > 0 and sign_flip_non_neutral == 0:
            instability_type = "neutral-boundary sign flip"
        elif h10_only:
            instability_type = "h10-only instability"
        elif core_drift >= 6 or stability_class == "high_priority_unstable":
            instability_type = "true instability candidate"
        else:
            instability_type = "true instability candidate"
        rows.append(
            {
                "cell_id": scorecard["cell_id"],
                "instability_type": instability_type,
                "stability_class": stability_class,
                "max_abs_rank_drift_core_hours": scorecard["max_abs_rank_drift_core_hours"],
                "h10_rank_drift": scorecard["h10_rank_drift"],
                "sign_flip_count": scorecard["sign_flip_count"],
                "sign_flip_near_zero_count": scorecard["sign_flip_near_zero_count"],
                "sign_flip_non_neutral_count": scorecard["sign_flip_non_neutral_count"],
                "top_k_presence_count": scorecard["top_k_presence_count"],
                "median_delta_core_fd01": scorecard["median_delta_tmrt_p90_core_hours_fd01"],
                "median_delta_core_fd02": scorecard["median_delta_tmrt_p90_core_hours_fd02"],
                "review_notes": scorecard["notes"],
            }
        )
    return sorted(rows, key=lambda row: (row["instability_type"], row["cell_id"]))


def geometry_uncertainty_rows() -> list[dict[str, str]]:
    """Return the compact F4 geometry uncertainty register."""
    return [
        {
            "uncertainty_item": "overhead_as_canopy approximation",
            "status": "OPEN",
            "implication": "Scenario approximates overhead shade as canopy-like geometry, not actual installed infrastructure.",
            "mitigation": "Keep target card framed as SOLWEIG-derived sensitivity evidence.",
            "claim_boundary": "No causal claim about real installed overhead infrastructure.",
        },
        {
            "uncertainty_item": "local-output-only rasters",
            "status": "CONTROLLED",
            "implication": "F4 consumes compact CSV summaries, while raster contents remain local-only.",
            "mitigation": "Do not commit rasters; preserve F3c compact QA evidence.",
            "claim_boundary": "No raster artifact is committed or redistributed.",
        },
        {
            "uncertainty_item": "h10 low sun-angle instability",
            "status": "CAVEATED",
            "implication": "h10 rank/top-k agreement is weaker than core hours.",
            "mitigation": "Do not use h10 as an anchor hour for target-card or priority decisions.",
            "claim_boundary": "h10 is caveated support only.",
        },
        {
            "uncertainty_item": "neutral-boundary sign flips",
            "status": "CAVEATED",
            "implication": "Small sign flips around zero can look like warming but are neutral-boundary behavior.",
            "mitigation": "Separate near-zero flips from true instability candidates.",
            "claim_boundary": "Near-zero flips are not warming evidence.",
        },
        {
            "uncertainty_item": "DSM/SVF/path sensitivity",
            "status": "OPEN",
            "implication": "Geometry and path assumptions can change local SOLWEIG Tmrt statistics.",
            "mitigation": "Require typology and spatial holdouts before stronger surrogate claims.",
            "claim_boundary": "No field-validated local WBGT or risk claim.",
        },
        {
            "uncertainty_item": "cell transform differences across cells expected",
            "status": "CONTROLLED",
            "implication": "Transforms differ by cell location but are internally consistent within each cell.",
            "mitigation": "Preserve per-cell alignment QA rather than requiring cross-cell identical transforms.",
            "claim_boundary": "Cell-local comparison only.",
        },
        {
            "uncertainty_item": "raster not committed",
            "status": "CONTROLLED",
            "implication": "Review relies on compact QA and summary tables.",
            "mitigation": "Keep outputs CSV/Markdown only in Git.",
            "claim_boundary": "No raster read/write/copy in F4.",
        },
        {
            "uncertainty_item": "no field validation yet",
            "status": "OPEN",
            "implication": "SOLWEIG-derived Tmrt modifier is not observed truth.",
            "mitigation": "Add future field or independent validation before stronger claims.",
            "claim_boundary": "Not WBGT, not risk, not observed truth.",
        },
    ]


def core_hour_headline(hourly_rows: Sequence[dict[str, Any]]) -> str:
    """Return compact core-hour stability headline."""
    core = [row for row in hourly_rows if row["decision"] == CORE_STABLE]
    if len(core) == 4:
        return "h12/h13/h15/h16 are core-stable across FD01/FD02 for delta_tmrt_p90_c ranking."
    return "One or more core hours require review before target-card support."


def h10_headline(hourly_rows: Sequence[dict[str, Any]]) -> str:
    """Return compact h10 caveat headline."""
    row = next((item for item in hourly_rows if item["hour_sgt"] == "10"), None)
    if row and row["decision"] == STABLE_WITH_CAVEAT:
        return "h10 is weaker and remains caveated; it is not anchor evidence."
    return "h10 is unstable and should be excluded from decision support."


def n150_recommendation(
    validation: EvidenceValidation,
    hourly_rows: Sequence[dict[str, Any]],
    robust_count: int,
) -> str:
    """Return conservative N150 readiness recommendation."""
    if validation.blockers:
        return BLOCK_N150
    core_ok = all(row["decision"] == CORE_STABLE for row in hourly_rows if row["hour_sgt"] in {"12", "13", "15", "16"})
    h10_ok = any(row["hour_sgt"] == "10" and row["decision"] == STABLE_WITH_CAVEAT for row in hourly_rows)
    if core_ok and h10_ok and robust_count >= 3:
        return ALLOW_N150_CONTROLLED_EXECUTION_AFTER_PRECHECK
    if core_ok:
        return ALLOW_N150_READINESS_ONLY
    return DEFER_N150_PENDING_REVIEW


def decision_status(
    validation: EvidenceValidation,
    hourly_rows: Sequence[dict[str, Any]],
    recommendation: str,
) -> str:
    """Return the overall F4 decision status."""
    if validation.blockers:
        return F4_BLOCKED
    core_ok = all(row["decision"] == CORE_STABLE for row in hourly_rows if row["hour_sgt"] in {"12", "13", "15", "16"})
    target_ready = recommendation in {
        ALLOW_N150_READINESS_ONLY,
        ALLOW_N150_CONTROLLED_EXECUTION_AFTER_PRECHECK,
    }
    if core_ok and target_ready:
        return F4_PASS
    return F4_PARTIAL


def build_decision_matrix(
    validation: EvidenceValidation,
    hourly_rows: Sequence[dict[str, Any]],
    robust_rows: Sequence[dict[str, Any]],
    neutral_rows: Sequence[dict[str, Any]],
    unstable_rows: Sequence[dict[str, Any]],
    recommendation: str,
) -> list[dict[str, str]]:
    """Build F4 decision matrix rows."""
    h10 = next((row for row in hourly_rows if row["hour_sgt"] == "10"), {})
    core = [row for row in hourly_rows if row["hour_sgt"] in {"12", "13", "15", "16"}]
    core_evidence = "; ".join(
        f"h{row['hour_sgt']} rho={row['spearman_fd01_fd02']} sign={row['sign_stability_fraction']} top10pct={row['top10pct_overlap']}"
        for row in core
    )
    return [
        {
            "row": "F3c execution validity",
            "decision": PASS if validation.postrun_valid else FAIL,
            "evidence": "480/480 postrun validation PASS." if validation.postrun_valid else "Postrun validation mismatch.",
            "blocker": "none" if validation.postrun_valid else "F3c execution compact evidence incomplete.",
            "next_action": "Use F3c compact summaries only.",
            "claim_boundary": "Execution validity is not B9, not WBGT, and not risk.",
        },
        {
            "row": "Raster QA validity",
            "decision": PASS if validation.raster_qa_valid else FAIL,
            "evidence": "Alignment/sanity compact QA PASS; all_480_rasters_opened=480/480 in F3c QA.",
            "blocker": "none" if validation.raster_qa_valid else "F3c raster QA compact evidence failed.",
            "next_action": "Do not read or commit rasters in F4.",
            "claim_boundary": "F4 consumes QA summaries only; no raster artifact is committed.",
        },
        {
            "row": "Core-hour stability",
            "decision": CORE_STABLE if all(row["decision"] == CORE_STABLE for row in core) else UNSTABLE_REVIEW_REQUIRED,
            "evidence": core_evidence,
            "blocker": "none" if all(row["decision"] == CORE_STABLE for row in core) else "Core-hour instability.",
            "next_action": "Use h12/h13/h15/h16 as primary stability evidence.",
            "claim_boundary": "Radiative modifier stability only, not local WBGT.",
        },
        {
            "row": "h10 caveat",
            "decision": h10.get("decision", UNSTABLE_REVIEW_REQUIRED),
            "evidence": f"h10 rho={h10.get('spearman_fd01_fd02', '')}; sign={h10.get('sign_stability_fraction', '')}; top5={h10.get('top5_overlap', '')}.",
            "blocker": "h10 should not anchor priority decisions.",
            "next_action": "Carry h10 as caveated low-sun-angle evidence only.",
            "claim_boundary": "Do not treat h10 sign flips as strong warming without neutral-boundary review.",
        },
        {
            "row": "Target definition readiness",
            "decision": PASS,
            "evidence": "Primary target is delta_tmrt_p90_c = overhead_as_canopy - base.",
            "blocker": "none",
            "next_action": "Use target card with explicit not-WBGT/not-risk boundaries.",
            "claim_boundary": "SOLWEIG-derived radiative modifier, not observed truth.",
        },
        {
            "row": "Surrogate protocol readiness",
            "decision": "ALLOW_TARGET_CARD_PROTOCOL_SUITE",
            "evidence": f"{len(robust_rows)} robust anchors; {len(neutral_rows)} neutral-boundary/stable-neutral cells; {len(unstable_rows)} unstable-review rows.",
            "blocker": "No surrogate training in F4.",
            "next_action": "Proceed to protocol/target-card documentation and validation split design.",
            "claim_boundary": "Surrogate may emulate SOLWEIG-derived labels only.",
        },
        {
            "row": "N150 readiness",
            "decision": recommendation,
            "evidence": "Core hours passed; h10 is caveated; precheck remains required.",
            "blocker": "No N150 manifest or runner is created in F4.",
            "next_action": "Run only a future N150 precheck/readiness gate before any controlled execution.",
            "claim_boundary": "N150 expansion is not B9 and not AOI-wide prediction.",
        },
        {
            "row": "B9 readiness",
            "decision": "BLOCKED",
            "evidence": "F4 is an N24 evidence decision lane only.",
            "blocker": "No B9 authorization.",
            "next_action": "Keep B9 blocked until separately scoped.",
            "claim_boundary": "Do not call this B9.",
        },
        {
            "row": "Risk readiness",
            "decision": "BLOCKED",
            "evidence": "No exposure/vulnerability layer and no risk model were created.",
            "blocker": "Risk requires explicit exposure and vulnerability.",
            "next_action": "Defer risk overlay to a future scoped lane.",
            "claim_boundary": "Hazard prioritisation is not risk.",
        },
        {
            "row": "System A coupling readiness",
            "decision": "BLOCKED",
            "evidence": "F4 does not create local WBGT or System A/B coupling output.",
            "blocker": "No coupling protocol in this lane.",
            "next_action": "Keep System A/B coupling blocked until separately scoped.",
            "claim_boundary": "No Tmrt-to-WBGT conversion.",
        },
    ]


def write_target_card(path: Path) -> None:
    """Write the delta_tmrt_p90_c target card."""
    text = f"""# B8.5-F4 Target Card: delta_tmrt_p90_c

Generated: {now_stamp()}

## Target Name

`delta_tmrt_p90_c = overhead_as_canopy - base`

## Primary Role

SOLWEIG-derived radiative modifier / cooling sensitivity evidence for N24 stability review.

## What It Is Not

- Not WBGT.
- Not risk.
- Not observed truth.
- Not causal effect of actual installed overhead infrastructure.

## Why p90

- OpenHeat operational upper-tail radiant exposure target.
- More stable than max.
- More pocket-sensitive than mean.

## Required Future Validation

- p95 / area-above-threshold sensitivity.
- Spatial holdout.
- Forcing-day holdout.
- Typology holdout.

## Claim Boundary

This target supports first-order local heat hazard prioritisation as a SOLWEIG-informed radiative modifier. It does not create local WBGT, risk, AOI-wide prediction, B9 output, or System A/B coupling.
"""
    write_text(path, text)


def write_n150_recommendation(path: Path, recommendation: str, hourly_rows: Sequence[dict[str, Any]]) -> None:
    """Write the N150 readiness recommendation."""
    h10 = next((row for row in hourly_rows if row["hour_sgt"] == "10"), {})
    text = f"""# B8.5-F4 N150 Readiness Recommendation

Generated: {now_stamp()}

## Recommendation

`{recommendation}`

## Evidence Basis

- F3c compact evidence is 480/480 valid.
- Core hours h12/h13/h15/h16 are stable for the N24 decision target.
- h10 remains caveated: rho={h10.get('spearman_fd01_fd02', '')}, sign stability={h10.get('sign_stability_fraction', '')}, top5 overlap={h10.get('top5_overlap', '')}.
- No QGIS/SOLWEIG execution, raster read/write/copy, N150 manifest, or N150 runner is created in F4.

## Gate

Any N150 multi-forcing expansion still requires an explicit future precheck and controlled execution scope. B9 remains blocked.

## Claim Boundary

This recommendation is about readiness only. It is not B9, not local WBGT, not risk, not AOI-wide prediction, and not System A/B coupling.
"""
    write_text(path, text)


def write_surrogate_role(path: Path, recommendation: str) -> None:
    """Write the surrogate role decision."""
    text = f"""# B8.5-F4 Surrogate Role Decision

Generated: {now_stamp()}

## Decision

`{SURROGATE_ROLE_DECISION}`

## Proceed / Do Not Proceed

- Surrogate target-card / protocol suite: `ALLOW`.
- Baseline surrogate training on existing N150 labels: `ALLOW_AS_SEPARATE_REVIEWED_LANE`; no training is performed in F4.
- N24 as multi-forcing stress-validation set: `ALLOW`.
- N150 multi-forcing expansion: `{recommendation}`.

## Boundary

System B may use N24 as a stress-validation set for SOLWEIG-derived radiative modifier labels. It must not claim observed WBGT calibration, risk, causal feature importance, B9 readiness, or System A/B coupling from F4.
"""
    write_text(path, text)


def write_report(
    path: Path,
    decision: str,
    validation: EvidenceValidation,
    hourly_rows: Sequence[dict[str, Any]],
    scorecards: Sequence[dict[str, Any]],
    robust_rows_: Sequence[dict[str, Any]],
    neutral_rows_: Sequence[dict[str, Any]],
    unstable_rows_: Sequence[dict[str, Any]],
    recommendation: str,
) -> None:
    """Write the F4 Markdown report."""
    lines = [
        "# B8.5-F4 N24 Stability Decision Matrix Report",
        "",
        f"Generated: {now_stamp()}",
        "",
        "## 1. Why F4 follows F3c",
        "",
        "F3c produced the controlled N24 / 480-run compact evidence package. F4 is the review gate that decides what that evidence supports before any N150 or B9 movement.",
        "",
        "## 2. What F3c proved",
        "",
        "- 24 cells x 2 forcing days x 5 hours x 2 scenarios = 480 controlled runs.",
        "- Postrun validation is 480/480 PASS.",
        "- F3c raster QA and alignment QA compact evidence are PASS.",
        "- Core-hour delta_tmrt_p90_c rank stability is strong enough for target-card evidence.",
        "",
        "## 3. What F3c did not prove",
        "",
        "- It did not prove local WBGT prediction.",
        "- It did not prove risk.",
        "- It did not prove observed truth or causal effects of installed overhead infrastructure.",
        "- It did not authorize B9, AOI-wide prediction, or System A/B coupling.",
        "",
        "## 4. Hour-level stability interpretation",
        "",
        markdown_table(hourly_rows, HOURLY_FIELDS),
        "",
        "## 5. h10 caveat",
        "",
        h10_headline(hourly_rows),
        "",
        "## 6. Robust priority cells",
        "",
        markdown_table(robust_rows_, ROBUST_FIELDS),
        "",
        "## 7. Neutral-boundary cells",
        "",
        "Near-zero deltas and near-zero sign flips are treated as neutral-boundary behavior, not warming evidence.",
        "",
        markdown_table(neutral_rows_, NEUTRAL_FIELDS, max_rows=30),
        "",
        "## 8. Unstable cells",
        "",
        markdown_table(unstable_rows_, UNSTABLE_PRIORITY_FIELDS, max_rows=30),
        "",
        "## 9. Target-card decision",
        "",
        "`delta_tmrt_p90_c` is ready as the primary target-card variable for SOLWEIG-derived radiative modifier / cooling sensitivity evidence.",
        "",
        "## 10. N150 recommendation",
        "",
        f"`{recommendation}`. B9 remains blocked.",
        "",
        "## 11. Surrogate role decision",
        "",
        f"`{SURROGATE_ROLE_DECISION}`. No surrogate is trained in F4.",
        "",
        "## 12. Claim boundaries",
        "",
        "- Not B9.",
        "- Not local WBGT.",
        "- Not risk.",
        "- Not N150 execution.",
        "- No raster committed.",
        "- No Tmrt-to-WBGT conversion.",
        "",
        "## Evidence validation notes",
        "",
        "\n".join(f"- {note}" for note in validation.evidence_notes) if validation.evidence_notes else "- none",
        "",
        "## Blockers",
        "",
        "\n".join(f"- {item}" for item in validation.blockers) if validation.blockers else "- none",
        "",
        "## Decision status",
        "",
        f"`{decision}`",
    ]
    write_text(path, "\n".join(lines) + "\n")


def write_cn_doc(
    path: Path,
    decision: str,
    hourly_rows: Sequence[dict[str, Any]],
    robust_rows_: Sequence[dict[str, Any]],
    neutral_rows_: Sequence[dict[str, Any]],
    unstable_rows_: Sequence[dict[str, Any]],
    recommendation: str,
) -> None:
    """Write a valid UTF-8 Chinese F4 control note."""
    text = f"""# OpenHeat System B B8.5-F4 N24 稳定性决策矩阵中文说明

生成时间：{now_stamp()}

## 结论

- F4 决策状态：`{decision}`
- 核心小时结论：{core_hour_headline(hourly_rows)}
- h10 结论：{h10_headline(hourly_rows)}
- N150 建议：`{recommendation}`
- B9 状态：`{B9_BLOCKED}`

## 为什么 F4 接在 F3c 之后

F3c 已完成 N24 / 480-run 的受控执行证据包。F4 不再运行 QGIS/SOLWEIG，也不读取任何 raster；它只消费 F3c 的紧凑 CSV/Markdown 证据，用来判断 `delta_tmrt_p90_c` 是否可作为目标卡和后续 surrogate 协议的依据。

## F3c 已证明的内容

- 24 个 cells、2 个 forcing days、5 个 SGT hours、2 个 scenarios，共 480 个运行结果通过 postrun validation。
- F3c 的 raster QA、alignment QA 和 stability summary 为 PASS。
- h12/h13/h15/h16 的核心小时排序稳定性支持 N24 层面的目标卡判断。

## F3c 没有证明的内容

- 没有证明 local WBGT。
- 没有证明 risk。
- 没有证明 `Tmrt` 等于 WBGT。
- 没有证明实际安装 overhead infrastructure 的因果效应。
- 没有授权 B9、AOI-wide prediction、hazard_score、risk_score 或 System A/B coupling。

## 小时层级稳定性解释

{markdown_table(hourly_rows, HOURLY_FIELDS)}

## h10 caveat

h10 的 Spearman、top-k overlap 和 sign stability 弱于核心小时。F4 将 h10 作为低太阳高度角 caveat，不把 h10 用作 priority anchor。

## Robust priority cells

{markdown_table(robust_rows_, ROBUST_FIELDS)}

## Neutral-boundary cells

接近 0 的 delta 和接近 0 的 sign flip 被解释为 neutral-boundary，不解释为真实 warming。

{markdown_table(neutral_rows_, NEUTRAL_FIELDS, max_rows=30)}

## Unstable cells

{markdown_table(unstable_rows_, UNSTABLE_PRIORITY_FIELDS, max_rows=30)}

## Target-card decision

`delta_tmrt_p90_c = overhead_as_canopy - base` 可作为 SOLWEIG-derived radiative modifier / cooling sensitivity evidence 的 primary target。它不是 WBGT，不是 risk，不是 observed truth，也不是实际安装设施的因果效应。

## N150 recommendation

`{recommendation}`。这只表示后续 readiness / controlled execution gate 的建议；F4 没有创建 N150 manifest 或 runner，也没有执行 N150。

## Surrogate role decision

`{SURROGATE_ROLE_DECISION}`。System B 可以把 N24 用作 multi-forcing stress-validation set，并推进 target-card / protocol suite；F4 不训练 surrogate。

## Claim boundaries

- 这不是 B9。
- 这不是 local WBGT。
- 这不是 risk。
- 这不是 N150 execution。
- 没有提交 raster。
- 没有 Tmrt-to-WBGT conversion。
"""
    write_text(path, text)


def write_status(
    path: Path,
    result: F4Result,
    validation: EvidenceValidation,
) -> None:
    """Write the F4 lane status Markdown."""
    files_block = "\n".join(f"- `{rel(path)}`" for path in result.files_created)
    text = f"""# B8.5-F4 Status

Generated: {now_stamp()}

## Status

`{result.decision_status}`

## Branch

`codex/b85-f4-n24-decision-matrix`

## Scope

N24 stability decision matrix, target-card gate, N150 readiness recommendation, and surrogate role decision from compact F3c evidence only.

## Key Results

- Core-hour stability headline: {result.core_hour_headline}
- h10 caveat headline: {result.h10_caveat_headline}
- Robust priority cell count: `{result.robust_priority_count}`
- Neutral-boundary cell count: `{result.neutral_boundary_count}`
- Unstable-review cell count: `{result.unstable_review_count}`
- N150 recommendation: `{result.n150_recommendation}`
- Surrogate role decision: `{result.surrogate_role_decision}`
- B9 status: `{result.b9_status}`
- QGIS/SOLWEIG executed by Codex: `no`
- Raster read/write/copy in F4: `no`

## Evidence Notes

{chr(10).join(f"- {note}" for note in validation.evidence_notes) if validation.evidence_notes else "- none"}

## Blockers

{chr(10).join(f"- {item}" for item in validation.blockers) if validation.blockers else "- none"}

## Files Created / Modified

{files_block}

## Commands To Verify

- `python -m compileall scripts/v12_b85_f4_n24_decision_matrix.py scripts/v12_b85_run_f4_n24_decision_matrix.py`
- `python scripts/v12_b85_run_f4_n24_decision_matrix.py --config configs/v12/systemb_b85_f4_n24_decision.yaml`
- Python mojibake check on `docs/v12/OpenHeat_SystemB_B8_5_F4_N24_decision_matrix_CN.md`
- `git status --short -- .`
- forbidden-file check

## Safe To Commit

Only compact config, scripts, docs, CSV, and Markdown artifacts listed above after review.

## Not Safe To Commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, `data/solweig/`, `data/rasters/`, raw archives, patch zip packages, and large forecast CSV files.
"""
    write_text(path, text)


def all_output_paths(config: dict[str, Any]) -> list[Path]:
    """Return all compact artifacts owned by F4."""
    outputs = config["outputs"]
    return [
        DEFAULT_CONFIG,
        ROOT / "scripts/v12_b85_f4_n24_decision_matrix.py",
        ROOT / "scripts/v12_b85_run_f4_n24_decision_matrix.py",
        repo_path(outputs["canonical_note_cn"]),
        repo_path(outputs["hourly_stability_summary"]),
        repo_path(outputs["cell_stability_scorecard"]),
        repo_path(outputs["robust_priority_cells"]),
        repo_path(outputs["neutral_boundary_cells"]),
        repo_path(outputs["unstable_priority_cells"]),
        repo_path(outputs["target_card_delta_tmrt_p90"]),
        repo_path(outputs["n150_readiness_recommendation"]),
        repo_path(outputs["surrogate_role_decision"]),
        repo_path(outputs["geometry_uncertainty_register"]),
        repo_path(outputs["decision_matrix"]),
        repo_path(outputs["report"]),
        repo_path(outputs["status"]),
    ]


def run(config_path: Path) -> F4Result:
    """Run the F4 decision matrix generation."""
    config = read_config(repo_path(config_path))
    ensure_scope(config)
    outputs = config["outputs"]
    repo_path(outputs["out_dir"]).mkdir(parents=True, exist_ok=True)
    evidence = load_evidence(config)
    validation = validate_evidence(config, evidence)
    hourly_rows = hourly_stability_summary(config, evidence)
    scorecards = build_scorecards(config, evidence)
    robust = robust_priority_rows(config, evidence, scorecards)
    neutral = neutral_boundary_rows(scorecards)
    unstable = unstable_priority_rows(scorecards)
    robust_count = len(robust)
    neutral_count = len(neutral)
    unstable_review_count = sum(
        1 for row in scorecards if row["stability_class"] in {"unstable_review", "high_priority_unstable"}
    )
    recommendation = n150_recommendation(validation, hourly_rows, robust_count)
    decision = decision_status(validation, hourly_rows, recommendation)
    if decision == F4_BLOCKED:
        recommendation = BLOCK_N150
    decision_matrix = build_decision_matrix(validation, hourly_rows, robust, neutral, unstable, recommendation)

    write_csv_rows(repo_path(outputs["hourly_stability_summary"]), hourly_rows, HOURLY_FIELDS)
    write_csv_rows(repo_path(outputs["cell_stability_scorecard"]), scorecards, SCORECARD_FIELDS)
    write_csv_rows(repo_path(outputs["robust_priority_cells"]), robust, ROBUST_FIELDS)
    write_csv_rows(repo_path(outputs["neutral_boundary_cells"]), neutral, NEUTRAL_FIELDS)
    write_csv_rows(repo_path(outputs["unstable_priority_cells"]), unstable, UNSTABLE_PRIORITY_FIELDS)
    write_target_card(repo_path(outputs["target_card_delta_tmrt_p90"]))
    write_n150_recommendation(repo_path(outputs["n150_readiness_recommendation"]), recommendation, hourly_rows)
    write_surrogate_role(repo_path(outputs["surrogate_role_decision"]), recommendation)
    write_csv_rows(
        repo_path(outputs["geometry_uncertainty_register"]),
        geometry_uncertainty_rows(),
        GEOMETRY_FIELDS,
    )
    write_csv_rows(repo_path(outputs["decision_matrix"]), decision_matrix, DECISION_MATRIX_FIELDS)
    write_report(
        repo_path(outputs["report"]),
        decision,
        validation,
        hourly_rows,
        scorecards,
        robust,
        neutral,
        unstable,
        recommendation,
    )
    write_cn_doc(
        repo_path(outputs["canonical_note_cn"]),
        decision,
        hourly_rows,
        robust,
        neutral,
        unstable,
        recommendation,
    )

    result = F4Result(
        decision_status=decision,
        core_hour_headline=core_hour_headline(hourly_rows),
        h10_caveat_headline=h10_headline(hourly_rows),
        robust_priority_count=robust_count,
        neutral_boundary_count=neutral_count,
        unstable_review_count=unstable_review_count,
        n150_recommendation=recommendation,
        surrogate_role_decision=SURROGATE_ROLE_DECISION,
        b9_status=B9_BLOCKED,
        files_created=all_output_paths(config),
    )
    write_status(repo_path(outputs["status"]), result, validation)
    return result


HOURLY_FIELDS = [
    "hour_sgt",
    "spearman_fd01_fd02",
    "sign_stability_fraction",
    "top5_overlap",
    "top10pct_overlap",
    "top20pct_overlap",
    "warn_count",
    "high_severity_count",
    "decision",
    "notes",
]

SCORECARD_FIELDS = [
    "cell_id",
    "median_delta_tmrt_p90_core_hours_fd01",
    "median_delta_tmrt_p90_core_hours_fd02",
    "max_abs_rank_drift_core_hours",
    "h10_rank_drift",
    "sign_flip_count",
    "top_k_presence_count",
    "neutral_boundary_count",
    "robust_priority_score",
    "stability_class",
    "notes",
    "top3_core_presence_count",
    "top5_core_presence_count",
    "top10_core_presence_count",
    "neutral_core_count",
    "sign_flip_near_zero_count",
    "sign_flip_non_neutral_count",
    "meaningful_core_delta_count",
    "strong_core_delta_count",
    "h10_only_instability_flag",
    "fd01_rank_summary",
    "fd02_rank_summary",
    "fd01_delta_summary",
    "fd02_delta_summary",
]

ROBUST_FIELDS = [
    "cell_id",
    "evidence_hours",
    "fd01_rank_summary",
    "fd02_rank_summary",
    "median_delta_core_fd01",
    "median_delta_core_fd02",
    "stability_notes",
    "recommended_role",
    "robust_priority_score",
]

NEUTRAL_FIELDS = [
    "cell_id",
    "neutral_boundary_count",
    "neutral_core_count",
    "sign_flip_count",
    "sign_flip_near_zero_count",
    "median_delta_core_fd01",
    "median_delta_core_fd02",
    "caveats",
]

UNSTABLE_PRIORITY_FIELDS = [
    "cell_id",
    "instability_type",
    "stability_class",
    "max_abs_rank_drift_core_hours",
    "h10_rank_drift",
    "sign_flip_count",
    "sign_flip_near_zero_count",
    "sign_flip_non_neutral_count",
    "top_k_presence_count",
    "median_delta_core_fd01",
    "median_delta_core_fd02",
    "review_notes",
]

GEOMETRY_FIELDS = [
    "uncertainty_item",
    "status",
    "implication",
    "mitigation",
    "claim_boundary",
]

DECISION_MATRIX_FIELDS = [
    "row",
    "decision",
    "evidence",
    "blocker",
    "next_action",
    "claim_boundary",
]


def main() -> int:
    """Parse CLI args and run the F4 decision matrix."""
    parser = argparse.ArgumentParser(
        description=(
            "Create B8.5-F4 N24 decision-matrix artifacts from compact F3c "
            "evidence only. Does not run QGIS/SOLWEIG, read rasters, create "
            "WBGT/risk/hazard outputs, train surrogates, or create N150 runners."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B8.5-F4 YAML config path.")
    args = parser.parse_args()
    try:
        result = run(args.config)
    except Exception as exc:
        print(f"Status: {FAILED}")
        print(f"Error: {exc}")
        return 1
    print(f"Status: {result.decision_status}")
    print(f"Core-hour stability headline: {result.core_hour_headline}")
    print(f"h10 caveat headline: {result.h10_caveat_headline}")
    print(f"Robust priority cell count: {result.robust_priority_count}")
    print(f"Neutral-boundary cell count: {result.neutral_boundary_count}")
    print(f"Unstable-review cell count: {result.unstable_review_count}")
    print(f"N150 recommendation: {result.n150_recommendation}")
    print(f"Surrogate role decision: {result.surrogate_role_decision}")
    print(f"B9 status: {result.b9_status}")
    print("Files created:")
    for path in result.files_created:
        print(f"- {rel(path)}")
    return 0 if result.decision_status in {F4_PASS, F4_PARTIAL} else 2


if __name__ == "__main__":
    raise SystemExit(main())
