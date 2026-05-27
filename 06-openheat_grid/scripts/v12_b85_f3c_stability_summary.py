"""Build B8.5-F3c first-pass N24 multi-forcing stability summaries.

Inputs:
    configs/v12/systemb_b85_f3c_n24_full_execution.yaml
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_n24_manifest.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_raster_stats.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_alignment_qa.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_sanity_checks.csv

Outputs:
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_cell_hour_summary.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_pairwise_delta_by_cell_hour.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_forcing_day_contrast_by_cell_hour.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_stability_summary.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_unstable_cell_inventory.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_n24_report.md
    outputs/v12_surrogate/b8_5_f3c_n24/B8_5_F3C_STATUS.md

Saved metrics:
    Per cell/forcing/hour/scenario Tmrt stats, overhead-base delta_tmrt_p90_c,
    within-slice ranks, FD02-FD01 contrasts, rank drift, Spearman correlation
    by hour, top-k overlaps, sign stability, unstable-cell inventory, and a
    compact Markdown report.

This script does not run QGIS, run SOLWEIG, open raster contents, write
rasters/images/arrays, compute local WBGT, create hazard_score/risk_score
outputs, create System A/B coupling outputs, perform Tmrt-to-WBGT conversion,
stage, or commit. It summarizes stability evidence only; it is not B9.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from v12_b85_f3c_prepare_n24 import (
    BLOCKED_PRECHECK,
    FAILED,
    FAIL,
    NOT_RUN_YET,
    N24_EXECUTED_PARTIAL,
    N24_STABILITY_REVIEW_READY,
    PASS,
    READY_FOR_HUMAN_N24,
    ROOT,
    WARN,
    YES,
    all_lane_paths,
    clean,
    markdown_table,
    read_config,
    read_csv_rows,
    rel,
    repo_path,
    write_cn_doc,
    write_csv_rows,
    write_status_report,
    write_text,
)


DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_f3c_n24_full_execution.yaml"


@dataclass(frozen=True)
class StabilityResult:
    """Compact result for CLI reporting."""

    decision_status: str
    manifest_run_count: int
    unique_cell_count: int
    pre_execution_ready_count: int
    postrun_status: str
    raster_qa_status: str
    stability_summary_status: str
    files_created: list[Path]


def format_float(value: Any, digits: int = 6) -> str:
    """Format a finite float for compact CSV output."""
    try:
        x = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(x):
        return ""
    return f"{x:.{digits}f}"


def precheck_ready_count(config: dict[str, Any]) -> int:
    """Return the F3c pre-execution ready count when the file exists."""
    path = repo_path(config["outputs"]["pre_execution_asset_check"])
    if not path.exists():
        return 0
    rows = read_csv_rows(path)
    return sum(
        1
        for row in rows
        if clean(row.get("run_ready")).lower() == YES and clean(row.get("pre_execution_status")).upper() == PASS
    )


def postrun_status(config: dict[str, Any]) -> str:
    """Return compact postrun status from validation output."""
    path = repo_path(config["outputs"]["postrun_validation"])
    if not path.exists():
        return NOT_RUN_YET
    rows = read_csv_rows(path)
    if rows and all(clean(row.get("validation_status")).upper() == PASS for row in rows):
        return f"{len(rows)}/{config['expected_run_count']}_EXECUTED_OUTPUTS_VALID"
    if rows and all(clean(row.get("validation_status")) == NOT_RUN_YET for row in rows):
        return NOT_RUN_YET
    return "PARTIAL_OR_BLOCKED"


def raster_qa_ready(config: dict[str, Any], stats: Sequence[dict[str, str]]) -> bool:
    """Return whether raster stats are ready for stability summaries."""
    if len(stats) != int(config["expected_run_count"]):
        return False
    for row in stats:
        if clean(row.get("sanity_status")) not in {PASS, WARN}:
            return False
        if not clean(row.get("p90_c")):
            return False
    alignment = read_csv_rows(repo_path(config["outputs"]["alignment_qa"]))
    sanity = read_csv_rows(repo_path(config["outputs"]["sanity_checks"]))
    if any(clean(row.get("status")) == FAIL for row in alignment):
        return False
    if any(clean(row.get("status")) == FAIL for row in sanity):
        return False
    if any(clean(row.get("status")) == NOT_RUN_YET for row in alignment):
        return False
    return True


def raster_qa_status(config: dict[str, Any]) -> str:
    """Return compact raster QA status."""
    stats_path = repo_path(config["outputs"]["raster_stats"])
    if not stats_path.exists():
        return NOT_RUN_YET
    stats = read_csv_rows(stats_path)
    if raster_qa_ready(config, stats):
        return PASS
    if stats and all(clean(row.get("sanity_status")) == NOT_RUN_YET for row in stats):
        return NOT_RUN_YET
    return N24_EXECUTED_PARTIAL


def write_empty_outputs(config: dict[str, Any], reason: str) -> StabilityResult:
    """Write NOT_RUN_YET stability placeholders."""
    outputs = config["outputs"]
    manifest_rows = read_csv_rows(repo_path(outputs["manifest"]))
    ready_count = precheck_ready_count(config)
    unique_cell_count = len({row["cell_id"] for row in manifest_rows})
    placeholder = [
        {
            "record_type": NOT_RUN_YET,
            "status": NOT_RUN_YET,
            "value": reason,
            "details": "Stability summary waits for postrun validation and raster QA.",
        }
    ]
    unstable = [
        {
            "cell_id": "",
            "hour_sgt": "",
            "instability_reason": NOT_RUN_YET,
            "severity": NOT_RUN_YET,
            "details": reason,
        }
    ]
    write_csv_rows(repo_path(outputs["cell_hour_summary"]), [], CELL_HOUR_FIELDS)
    write_csv_rows(repo_path(outputs["pairwise_delta_by_cell_hour"]), [], PAIRWISE_FIELDS)
    write_csv_rows(repo_path(outputs["forcing_day_contrast_by_cell_hour"]), [], CONTRAST_FIELDS)
    write_csv_rows(repo_path(outputs["stability_summary"]), placeholder, STABILITY_FIELDS)
    write_csv_rows(repo_path(outputs["unstable_cell_inventory"]), unstable, UNSTABLE_FIELDS)
    write_report(
        repo_path(outputs["n24_report"]),
        config,
        READY_FOR_HUMAN_N24 if ready_count == int(config["expected_run_count"]) else BLOCKED_PRECHECK,
        NOT_RUN_YET,
        [],
        [],
        [],
        placeholder,
        unstable,
        reason,
    )
    decision = READY_FOR_HUMAN_N24 if ready_count == int(config["expected_run_count"]) else BLOCKED_PRECHECK
    write_cn_doc(
        repo_path(outputs["canonical_note_cn"]),
        config,
        decision,
        ready_count,
        postrun_status(config),
        raster_qa_status(config),
        NOT_RUN_YET,
    )
    write_status_report(
        repo_path(outputs["status"]),
        config,
        decision,
        len(manifest_rows),
        unique_cell_count,
        ready_count,
        postrun_status(config),
        raster_qa_status(config),
        NOT_RUN_YET,
        reason,
    )
    return StabilityResult(
        decision_status=decision,
        manifest_run_count=len(manifest_rows),
        unique_cell_count=unique_cell_count,
        pre_execution_ready_count=ready_count,
        postrun_status=postrun_status(config),
        raster_qa_status=raster_qa_status(config),
        stability_summary_status=NOT_RUN_YET,
        files_created=all_lane_paths(config),
    )


def float_value(row: dict[str, str], field: str) -> float:
    """Return a required float field."""
    return float(clean(row.get(field)))


def cell_hour_rows(stats: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
    """Return per-cell, per-hour, per-scenario Tmrt summary rows."""
    out: list[dict[str, Any]] = []
    for row in stats:
        out.append(
            {
                "cell_id": row["cell_id"],
                "forcing_day_id": row["forcing_day_id"],
                "date": row["date"],
                "hour_sgt": row["hour_sgt"],
                "scenario": row["scenario"],
                "tmrt_mean_c": row["mean_c"],
                "tmrt_p50_c": row["p50_c"],
                "tmrt_p90_c": row["p90_c"],
                "tmrt_p95_c": row["p95_c"],
                "tmrt_max_c": row["max_c"],
                "valid_pixel_count": row["valid_pixel_count"],
                "nodata_fraction": row["nodata_fraction"],
                "sanity_status": row["sanity_status"],
            }
        )
    return out


def rank_values(rows: Sequence[dict[str, Any]], value_field: str, rank_field: str) -> list[dict[str, Any]]:
    """Rank rows ascending by value, with the most negative delta as rank 1."""
    sorted_rows = sorted(rows, key=lambda row: (float(row[value_field]), row["cell_id"]))
    ranked: list[dict[str, Any]] = []
    last_value: float | None = None
    current_rank = 0
    for index, row in enumerate(sorted_rows, start=1):
        value = float(row[value_field])
        if last_value is None or value != last_value:
            current_rank = index
            last_value = value
        new_row = dict(row)
        new_row[rank_field] = str(current_rank)
        new_row["rank_direction"] = "most_negative_delta_rank_1"
        ranked.append(new_row)
    return ranked


def pairwise_delta_rows(config: dict[str, Any], stats: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
    """Compute overhead minus base deltas by cell, forcing day, and hour."""
    by_key = {
        (row["cell_id"], row["forcing_day_id"], int(row["hour_sgt"]), row["scenario"]): row
        for row in stats
    }
    out: list[dict[str, Any]] = []
    for cell_id in sorted({row["cell_id"] for row in stats}):
        for forcing_day in config["forcing_days"]:
            for hour in config["hours_sgt"]:
                base = by_key[(cell_id, forcing_day, int(hour), "base")]
                overhead = by_key[(cell_id, forcing_day, int(hour), "overhead_as_canopy")]
                row = {
                    "cell_id": cell_id,
                    "forcing_day_id": forcing_day,
                    "hour_sgt": str(hour),
                    "base_tmrt_p90_c": base["p90_c"],
                    "overhead_tmrt_p90_c": overhead["p90_c"],
                    "delta_tmrt_mean_c": format_float(float_value(overhead, "mean_c") - float_value(base, "mean_c")),
                    "delta_tmrt_p50_c": format_float(float_value(overhead, "p50_c") - float_value(base, "p50_c")),
                    "delta_tmrt_p90_c": format_float(float_value(overhead, "p90_c") - float_value(base, "p90_c")),
                    "delta_tmrt_p95_c": format_float(float_value(overhead, "p95_c") - float_value(base, "p95_c")),
                    "delta_tmrt_max_c": format_float(float_value(overhead, "max_c") - float_value(base, "max_c")),
                    "within_slice_rank": "",
                    "rank_direction": "",
                    "notes": "overhead_as_canopy - base; Tmrt stability evidence only, not WBGT.",
                }
                out.append(row)
    ranked: list[dict[str, Any]] = []
    for forcing_day in config["forcing_days"]:
        for hour in config["hours_sgt"]:
            group = [row for row in out if row["forcing_day_id"] == forcing_day and int(row["hour_sgt"]) == int(hour)]
            ranked.extend(rank_values(group, "delta_tmrt_p90_c", "within_slice_rank"))
    return sorted(ranked, key=lambda row: (row["cell_id"], row["forcing_day_id"], int(row["hour_sgt"])))


def forcing_day_contrast_rows(config: dict[str, Any], stats: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
    """Compute FD02 minus FD01 contrasts by cell, hour, and scenario."""
    fd01, fd02 = config["forcing_days"]
    by_key = {
        (row["cell_id"], row["forcing_day_id"], int(row["hour_sgt"]), row["scenario"]): row
        for row in stats
    }
    out: list[dict[str, Any]] = []
    for cell_id in sorted({row["cell_id"] for row in stats}):
        for hour in config["hours_sgt"]:
            for scenario in config["scenarios"]:
                first = by_key[(cell_id, fd01, int(hour), scenario)]
                second = by_key[(cell_id, fd02, int(hour), scenario)]
                out.append(
                    {
                        "cell_id": cell_id,
                        "hour_sgt": str(hour),
                        "scenario": scenario,
                        "fd01_forcing_day_id": fd01,
                        "fd02_forcing_day_id": fd02,
                        "contrast_direction": "FD02_minus_FD01",
                        "mean_difference_c": format_float(float_value(second, "mean_c") - float_value(first, "mean_c")),
                        "p50_difference_c": format_float(float_value(second, "p50_c") - float_value(first, "p50_c")),
                        "p90_difference_c": format_float(float_value(second, "p90_c") - float_value(first, "p90_c")),
                        "p95_difference_c": format_float(float_value(second, "p95_c") - float_value(first, "p95_c")),
                        "max_difference_c": format_float(float_value(second, "max_c") - float_value(first, "max_c")),
                        "notes": "FD02 - FD01 Tmrt contrast; not WBGT.",
                    }
                )
    return out


def ranks_by_cell(pairwise: Sequence[dict[str, Any]], forcing_day: str, hour: int) -> dict[str, int]:
    """Return cell ranks for one forcing day/hour."""
    return {
        row["cell_id"]: int(row["within_slice_rank"])
        for row in pairwise
        if row["forcing_day_id"] == forcing_day and int(row["hour_sgt"]) == hour
    }


def deltas_by_cell(pairwise: Sequence[dict[str, Any]], forcing_day: str, hour: int) -> dict[str, float]:
    """Return delta values for one forcing day/hour."""
    return {
        row["cell_id"]: float(row["delta_tmrt_p90_c"])
        for row in pairwise
        if row["forcing_day_id"] == forcing_day and int(row["hour_sgt"]) == hour
    }


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Return Pearson correlation or None for degenerate input."""
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    denom_x = math.sqrt(sum(x * x for x in dx))
    denom_y = math.sqrt(sum(y * y for y in dy))
    if denom_x == 0 or denom_y == 0:
        return None
    return sum(x * y for x, y in zip(dx, dy)) / (denom_x * denom_y)


def spearman_from_deltas(fd01: dict[str, float], fd02: dict[str, float]) -> float | None:
    """Compute Spearman correlation from two cell-delta maps."""
    cells = sorted(set(fd01) & set(fd02))
    if len(cells) < 2:
        return None
    fd01_rank_rows = rank_values([{"cell_id": cell, "delta": fd01[cell]} for cell in cells], "delta", "rank")
    fd02_rank_rows = rank_values([{"cell_id": cell, "delta": fd02[cell]} for cell in cells], "delta", "rank")
    r1 = {row["cell_id"]: float(row["rank"]) for row in fd01_rank_rows}
    r2 = {row["cell_id"]: float(row["rank"]) for row in fd02_rank_rows}
    return pearson([r1[cell] for cell in cells], [r2[cell] for cell in cells])


def sign_label(value: float) -> str:
    """Return a compact sign label with a small neutral band."""
    if value > 1e-9:
        return "positive"
    if value < -1e-9:
        return "negative"
    return "zero"


def top_k_count(label: str, n_cells: int) -> int:
    """Return the top-k cell count for a configured label."""
    if label == "top5":
        return min(5, n_cells)
    if label == "top10pct":
        return max(1, math.ceil(n_cells * 0.10))
    if label == "top20pct":
        return max(1, math.ceil(n_cells * 0.20))
    raise ValueError(f"Unknown top-k label: {label}")


def stability_rows(config: dict[str, Any], pairwise: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build rank drift, Spearman, top-k, and sign-stability rows."""
    fd01, fd02 = config["forcing_days"]
    n_cells = int(config["expected_cell_count"])
    out: list[dict[str, Any]] = []
    for hour in config["hours_sgt"]:
        hour_int = int(hour)
        r1 = ranks_by_cell(pairwise, fd01, hour_int)
        r2 = ranks_by_cell(pairwise, fd02, hour_int)
        d1 = deltas_by_cell(pairwise, fd01, hour_int)
        d2 = deltas_by_cell(pairwise, fd02, hour_int)
        rho = spearman_from_deltas(d1, d2)
        out.append(
            {
                "record_type": "spearman_by_hour",
                "cell_id": "",
                "hour_sgt": str(hour),
                "forcing_day_id": "",
                "scenario": "",
                "metric": "spearman_delta_tmrt_p90_fd01_fd02",
                "value": format_float(rho) if rho is not None else "",
                "status": "PASS" if rho is not None else "WARN",
                "details": "Spearman correlation between FD01 and FD02 delta_tmrt_p90_c ranks by hour.",
            }
        )
        stable_sign_count = 0
        for cell_id in sorted(set(r1) & set(r2)):
            drift = abs(r2[cell_id] - r1[cell_id])
            sign_stable = sign_label(d1[cell_id]) == sign_label(d2[cell_id])
            if sign_stable:
                stable_sign_count += 1
            out.append(
                {
                    "record_type": "rank_drift_by_cell_hour",
                    "cell_id": cell_id,
                    "hour_sgt": str(hour),
                    "forcing_day_id": "FD01_vs_FD02",
                    "scenario": "overhead_as_canopy_minus_base",
                    "metric": "rank_drift",
                    "value": str(drift),
                    "status": "PASS" if drift < high_rank_drift_threshold(n_cells) else "WARN",
                    "details": f"FD01_rank={r1[cell_id]}; FD02_rank={r2[cell_id]}; sign_stable={sign_stable}",
                }
            )
        out.append(
            {
                "record_type": "sign_stability_by_hour",
                "cell_id": "",
                "hour_sgt": str(hour),
                "forcing_day_id": "FD01_vs_FD02",
                "scenario": "overhead_as_canopy_minus_base",
                "metric": "sign_stability_fraction",
                "value": format_float(stable_sign_count / n_cells if n_cells else math.nan),
                "status": "PASS" if stable_sign_count == n_cells else "WARN",
                "details": f"{stable_sign_count}/{n_cells} cells have stable delta sign.",
            }
        )
        for label in ("top5", "top10pct", "top20pct"):
            k = top_k_count(label, n_cells)
            top1 = {cell for cell, _rank in sorted(r1.items(), key=lambda item: (item[1], item[0]))[:k]}
            top2 = {cell for cell, _rank in sorted(r2.items(), key=lambda item: (item[1], item[0]))[:k]}
            overlap = len(top1 & top2)
            out.append(
                {
                    "record_type": "top_k_overlap_by_hour",
                    "cell_id": "",
                    "hour_sgt": str(hour),
                    "forcing_day_id": "FD01_vs_FD02",
                    "scenario": "overhead_as_canopy_minus_base",
                    "metric": label,
                    "value": format_float(overlap / k if k else math.nan),
                    "status": "PASS" if overlap == k else "WARN",
                    "details": f"overlap={overlap}/{k}; FD01_top={';'.join(sorted(top1))}; FD02_top={';'.join(sorted(top2))}",
                }
            )
    return out


def high_rank_drift_threshold(n_cells: int) -> int:
    """Return a conservative rank drift warning threshold."""
    return max(5, math.ceil(n_cells * 0.25))


def suspicious_alignment_or_nodata(config: dict[str, Any], cell_id: str) -> list[str]:
    """Return nodata/alignment warning reasons for a cell."""
    reasons: list[str] = []
    stats_path = repo_path(config["outputs"]["raster_stats"])
    if stats_path.exists():
        for row in read_csv_rows(stats_path):
            if row.get("cell_id") == cell_id:
                try:
                    if float(clean(row.get("nodata_fraction")) or "0") >= 0.5:
                        reasons.append("suspicious_nodata")
                        break
                except ValueError:
                    reasons.append("suspicious_nodata_parse")
                    break
    alignment_path = repo_path(config["outputs"]["alignment_qa"])
    if alignment_path.exists():
        for row in read_csv_rows(alignment_path):
            name = clean(row.get("check_name"))
            if name.startswith(f"{cell_id}:") and clean(row.get("status")) == FAIL:
                reasons.append("suspicious_alignment")
                break
    return sorted(set(reasons))


def unstable_inventory_rows(
    config: dict[str, Any],
    pairwise: Sequence[dict[str, Any]],
    stability: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build unstable-cell inventory from rank, sign, top-k, nodata, and alignment signals."""
    fd01, fd02 = config["forcing_days"]
    n_cells = int(config["expected_cell_count"])
    threshold = high_rank_drift_threshold(n_cells)
    out: list[dict[str, Any]] = []
    for hour in config["hours_sgt"]:
        r1 = ranks_by_cell(pairwise, fd01, int(hour))
        r2 = ranks_by_cell(pairwise, fd02, int(hour))
        d1 = deltas_by_cell(pairwise, fd01, int(hour))
        d2 = deltas_by_cell(pairwise, fd02, int(hour))
        top20_k = top_k_count("top20pct", n_cells)
        top1 = {cell for cell, _rank in sorted(r1.items(), key=lambda item: (item[1], item[0]))[:top20_k]}
        top2 = {cell for cell, _rank in sorted(r2.items(), key=lambda item: (item[1], item[0]))[:top20_k]}
        for cell_id in sorted(set(r1) & set(r2)):
            reasons: list[str] = []
            drift = abs(r2[cell_id] - r1[cell_id])
            if drift >= threshold:
                reasons.append("high_rank_drift")
            if sign_label(d1[cell_id]) != sign_label(d2[cell_id]):
                reasons.append("sign_flip")
            if (cell_id in top1) != (cell_id in top2):
                reasons.append("top_k_disagreement")
            reasons.extend(suspicious_alignment_or_nodata(config, cell_id))
            if reasons:
                severity = "HIGH" if "sign_flip" in reasons or "suspicious_alignment" in reasons else "REVIEW"
                out.append(
                    {
                        "cell_id": cell_id,
                        "hour_sgt": str(hour),
                        "instability_reason": ";".join(sorted(set(reasons))),
                        "severity": severity,
                        "details": (
                            f"FD01_rank={r1[cell_id]}; FD02_rank={r2[cell_id]}; "
                            f"rank_drift={drift}; FD01_delta={d1[cell_id]:.6f}; FD02_delta={d2[cell_id]:.6f}"
                        ),
                    }
                )
    if not out:
        out.append(
            {
                "cell_id": "",
                "hour_sgt": "",
                "instability_reason": "none_flagged",
                "severity": "PASS",
                "details": "No high rank drift, sign flip, top-k disagreement, nodata, or alignment instability flagged.",
            }
        )
    return out


def write_report(
    path: Path,
    config: dict[str, Any],
    decision_status: str,
    stability_status: str,
    cell_hour: Sequence[dict[str, Any]],
    pairwise: Sequence[dict[str, Any]],
    contrast: Sequence[dict[str, Any]],
    stability: Sequence[dict[str, Any]],
    unstable: Sequence[dict[str, Any]],
    next_action: str,
) -> None:
    """Write the F3c Markdown report."""
    lines = [
        "# B8.5-F3c N24 / 480-Run Report",
        "",
        f"Generated: {now_stamp()}",
        "",
        "## Decision",
        "",
        f"- Status: `{decision_status}`",
        f"- Stability summary status: `{stability_status}`",
        f"- Manifest run count: `{config['expected_run_count']}`",
        f"- Unique cell count: `{config['expected_cell_count']}`",
        f"- Next action: `{next_action}`",
        "",
        "## Read/Write Boundary",
        "",
        "Codex/Python did not run QGIS/SOLWEIG. No rasters were created, copied, moved, opened, written, or committed by the preparation lane. Raster QA reads local `Tmrt_average.tif` contents only after a successful human-run postrun validator. This report is stability evidence only.",
        "",
        "## Claim Boundaries",
        "",
        "- Not B9.",
        "- Not local WBGT.",
        "- Not risk.",
        "- Not N150.",
        "- Not full AOI.",
        "- No Tmrt-to-WBGT conversion.",
        "- No hazard_score, risk_score, AOI-wide prediction, or System A/B coupling output.",
        "- N150 / B9 remains blocked until N24 execution and stability review pass.",
        "",
        "## Cell-Hour Summary Sample",
        "",
        markdown_table(cell_hour, ["cell_id", "forcing_day_id", "hour_sgt", "scenario", "tmrt_mean_c", "tmrt_p50_c", "tmrt_p90_c", "tmrt_p95_c", "tmrt_max_c"], max_rows=25),
        "",
        "## Base-vs-Overhead Delta Sample",
        "",
        "Delta is `overhead_as_canopy - base`; this is Tmrt stability evidence, not WBGT.",
        "",
        markdown_table(pairwise, ["cell_id", "forcing_day_id", "hour_sgt", "delta_tmrt_p90_c", "within_slice_rank", "rank_direction"], max_rows=25),
        "",
        "## Forcing-Day Contrast Sample",
        "",
        "Contrast is `FD02 - FD01` for the same cell/hour/scenario.",
        "",
        markdown_table(contrast, ["cell_id", "hour_sgt", "scenario", "p90_difference_c", "contrast_direction"], max_rows=25),
        "",
        "## Stability Metrics Sample",
        "",
        markdown_table(stability, ["record_type", "cell_id", "hour_sgt", "metric", "value", "status", "details"], max_rows=40),
        "",
        "## Unstable Cell Inventory Sample",
        "",
        markdown_table(unstable, UNSTABLE_FIELDS, max_rows=40),
    ]
    write_text(path, "\n".join(lines) + "\n")


def now_stamp() -> str:
    """Return a local timestamp for reports."""
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run(config_path: Path) -> StabilityResult:
    """Run F3c stability summaries or NOT_RUN_YET placeholder mode."""
    config = read_config(repo_path(config_path))
    outputs = config["outputs"]
    manifest_rows = read_csv_rows(repo_path(outputs["manifest"]))
    stats_path = repo_path(outputs["raster_stats"])
    reason = "Raster QA has not confirmed 480/480 content-ready rasters."
    if not stats_path.exists():
        return write_empty_outputs(config, reason)
    stats = read_csv_rows(stats_path)
    if not raster_qa_ready(config, stats):
        return write_empty_outputs(config, reason)

    cell_hour = cell_hour_rows(stats)
    pairwise = pairwise_delta_rows(config, stats)
    contrast = forcing_day_contrast_rows(config, stats)
    stability = stability_rows(config, pairwise)
    unstable = unstable_inventory_rows(config, pairwise, stability)
    stability_status = PASS
    decision = N24_STABILITY_REVIEW_READY
    ready_count = precheck_ready_count(config)
    unique_cell_count = len({row["cell_id"] for row in manifest_rows})
    post_status = postrun_status(config)
    raster_status = raster_qa_status(config)
    if raster_status != PASS:
        decision = N24_EXECUTED_PARTIAL
        stability_status = N24_EXECUTED_PARTIAL
    next_action = "Human review of N24 stability evidence; N150 / B9 remains blocked until review passes."

    write_csv_rows(repo_path(outputs["cell_hour_summary"]), cell_hour, CELL_HOUR_FIELDS)
    write_csv_rows(repo_path(outputs["pairwise_delta_by_cell_hour"]), pairwise, PAIRWISE_FIELDS)
    write_csv_rows(repo_path(outputs["forcing_day_contrast_by_cell_hour"]), contrast, CONTRAST_FIELDS)
    write_csv_rows(repo_path(outputs["stability_summary"]), stability, STABILITY_FIELDS)
    write_csv_rows(repo_path(outputs["unstable_cell_inventory"]), unstable, UNSTABLE_FIELDS)
    write_report(
        repo_path(outputs["n24_report"]),
        config,
        decision,
        stability_status,
        cell_hour,
        pairwise,
        contrast,
        stability,
        unstable,
        next_action,
    )
    write_cn_doc(
        repo_path(outputs["canonical_note_cn"]),
        config,
        decision,
        ready_count,
        post_status,
        raster_status,
        stability_status,
    )
    write_status_report(
        repo_path(outputs["status"]),
        config,
        decision,
        len(manifest_rows),
        unique_cell_count,
        ready_count,
        post_status,
        raster_status,
        stability_status,
        next_action,
    )
    return StabilityResult(
        decision_status=decision,
        manifest_run_count=len(manifest_rows),
        unique_cell_count=unique_cell_count,
        pre_execution_ready_count=ready_count,
        postrun_status=post_status,
        raster_qa_status=raster_status,
        stability_summary_status=stability_status,
        files_created=all_lane_paths(config),
    )


CELL_HOUR_FIELDS = [
    "cell_id",
    "forcing_day_id",
    "date",
    "hour_sgt",
    "scenario",
    "tmrt_mean_c",
    "tmrt_p50_c",
    "tmrt_p90_c",
    "tmrt_p95_c",
    "tmrt_max_c",
    "valid_pixel_count",
    "nodata_fraction",
    "sanity_status",
]

PAIRWISE_FIELDS = [
    "cell_id",
    "forcing_day_id",
    "hour_sgt",
    "base_tmrt_p90_c",
    "overhead_tmrt_p90_c",
    "delta_tmrt_mean_c",
    "delta_tmrt_p50_c",
    "delta_tmrt_p90_c",
    "delta_tmrt_p95_c",
    "delta_tmrt_max_c",
    "within_slice_rank",
    "rank_direction",
    "notes",
]

CONTRAST_FIELDS = [
    "cell_id",
    "hour_sgt",
    "scenario",
    "fd01_forcing_day_id",
    "fd02_forcing_day_id",
    "contrast_direction",
    "mean_difference_c",
    "p50_difference_c",
    "p90_difference_c",
    "p95_difference_c",
    "max_difference_c",
    "notes",
]

STABILITY_FIELDS = [
    "record_type",
    "cell_id",
    "hour_sgt",
    "forcing_day_id",
    "scenario",
    "metric",
    "value",
    "status",
    "details",
]

UNSTABLE_FIELDS = ["cell_id", "hour_sgt", "instability_reason", "severity", "details"]


def main() -> int:
    """Parse CLI args and run F3c stability summaries."""
    parser = argparse.ArgumentParser(
        description=(
            "Build B8.5-F3c N24 stability summaries from raster QA CSVs. Before "
            "human execution it writes NOT_RUN_YET placeholders; it does not run "
            "QGIS/SOLWEIG, open rasters, compute WBGT, or promote B9."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="F3c YAML config path.")
    args = parser.parse_args()
    try:
        result = run(args.config)
    except Exception as exc:
        print(f"Status: {FAILED}")
        print(f"Error: {exc}")
        return 1
    print(f"Status: {result.decision_status}")
    print(f"Manifest run count: {result.manifest_run_count}")
    print(f"Unique cell count: {result.unique_cell_count}")
    print(f"Pre-execution ready count: {result.pre_execution_ready_count}")
    print(f"Postrun status: {result.postrun_status}")
    print(f"Raster QA status: {result.raster_qa_status}")
    print(f"Stability summary status: {result.stability_summary_status}")
    print("QGIS/SOLWEIG executed by Codex: no")
    print("Files created:")
    for path in result.files_created:
        print(f"- {rel(path)}")
    return 0 if result.decision_status in {READY_FOR_HUMAN_N24, N24_STABILITY_REVIEW_READY} else 2


if __name__ == "__main__":
    raise SystemExit(main())
