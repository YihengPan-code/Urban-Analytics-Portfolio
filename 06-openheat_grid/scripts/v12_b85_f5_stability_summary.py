"""Build B8.5-F5 N150 multi-forcing stability summaries.

Inputs:
    configs/v12/systemb_b85_f5_n150_multiforcing.yaml
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_pairwise_delta_by_cell_hour.csv
    B8.5-F4 robust/neutral/unstable anchor context CSV files.

Outputs:
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_forcing_day_contrast_by_cell_hour.csv
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_stability_summary.csv
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_report.md
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/B8_5_F5_STATUS.md

Saved metrics:
    FD02-vs-FD01 delta_tmrt_p90_c contrast by cell/hour, Spearman correlation
    by hour, top-5/top-10-percent/top-20-percent overlap by hour, sign
    stability by hour, h10 caveat flag, and N24 F4 anchor role comparisons.

This script does not run QGIS, run SOLWEIG, open raster contents, compute local
WBGT, create hazard_score/risk_score, create AOI-wide prediction, create
System A/B coupling, perform Tmrt-to-WBGT conversion, stage, or commit. It is
not B9 and does not create risk.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from v12_b85_f5_prepare_n150_multiforcing import (
    CONTRAST_FIELDS,
    FAILED,
    NOT_RUN_YET,
    N150_MULTIFORCING_EXECUTED_PASS,
    N150_MULTIFORCING_STABILITY_REVIEW_READY,
    PASS,
    READY_FOR_HUMAN_N150_MULTIFORCING,
    ROOT,
    STABILITY_FIELDS,
    WARN,
    YES,
    all_lane_paths,
    clean,
    execution_risk_register_rows,
    load_anchor_roles,
    read_config,
    read_csv_rows,
    rel,
    repo_path,
    write_cn_doc,
    write_csv_rows,
    write_report,
    write_status,
)


DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_f5_n150_multiforcing.yaml"


@dataclass(frozen=True)
class StabilityResult:
    """Compact result for CLI reporting."""

    decision_status: str
    manifest_run_count: int
    unique_cell_count: int
    pre_execution_ready_count: int
    postrun_status: str
    raster_qa_status: str
    label_merge_status: str
    stability_status: str
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
    """Return pre-execution ready count."""
    rows = read_csv_rows(repo_path(config["outputs"]["pre_execution_asset_check"]))
    return sum(1 for row in rows if clean(row.get("run_ready")).lower() == YES and clean(row.get("pre_execution_status")).upper() == PASS)


def postrun_status(config: dict[str, Any]) -> str:
    """Return compact postrun status."""
    rows = read_csv_rows(repo_path(config["outputs"]["postrun_validation"]))
    if rows and all(clean(row.get("validation_status")).upper() == PASS for row in rows):
        return f"{len(rows)}/{config['expected_run_count']}_EXECUTED_OUTPUTS_VALID"
    if rows and all(clean(row.get("validation_status")) == NOT_RUN_YET for row in rows):
        return NOT_RUN_YET
    return "PARTIAL_OR_BLOCKED"


def raster_qa_status(config: dict[str, Any]) -> str:
    """Return compact raster QA status."""
    stats = read_csv_rows(repo_path(config["outputs"]["raster_stats"]))
    if stats and len(stats) == int(config["expected_run_count"]) and all(clean(row.get("sanity_status")) in {PASS, WARN} for row in stats) and clean(stats[0].get("p90_c")):
        return PASS
    if stats and all(clean(row.get("sanity_status")) == NOT_RUN_YET for row in stats):
        return NOT_RUN_YET
    return "PARTIAL_OR_BLOCKED"


def pairwise_ready(config: dict[str, Any], pairwise: Sequence[dict[str, str]]) -> bool:
    """Return whether pairwise labels are ready for stability summaries."""
    expected_rows = int(config["expected_cell_count"]) * len(config["forcing_days"]) * len(config["hours_sgt"])
    if len(pairwise) != expected_rows:
        return False
    return all(clean(row.get("delta_tmrt_p90_c")) and clean(row.get("within_slice_rank")) for row in pairwise)


def write_not_run_outputs(config: dict[str, Any], reason: str) -> StabilityResult:
    """Write NOT_RUN_YET stability placeholders."""
    outputs = config["outputs"]
    manifest_rows = read_csv_rows(repo_path(outputs["manifest"]))
    ready_count = precheck_ready_count(config)
    decision = READY_FOR_HUMAN_N150_MULTIFORCING
    contrast_placeholder: list[dict[str, Any]] = []
    stability = [
        {
            "record_type": NOT_RUN_YET,
            "cell_id": "",
            "hour_sgt": "",
            "metric": NOT_RUN_YET,
            "value": "",
            "status": NOT_RUN_YET,
            "details": reason,
        }
    ]
    write_csv_rows(repo_path(outputs["forcing_day_contrast_by_cell_hour"]), contrast_placeholder, CONTRAST_FIELDS)
    write_csv_rows(repo_path(outputs["stability_summary"]), stability, STABILITY_FIELDS)
    risk_rows = execution_risk_register_rows(config)
    write_cn_doc(repo_path(outputs["canonical_note_cn"]), config, decision, ready_count, postrun_status(config), raster_qa_status(config), NOT_RUN_YET, NOT_RUN_YET)
    write_report(repo_path(outputs["report"]), config, decision, ready_count, postrun_status(config), raster_qa_status(config), NOT_RUN_YET, NOT_RUN_YET, risk_rows)
    write_status(repo_path(outputs["status"]), config, decision, len(manifest_rows), len({row["cell_id"] for row in manifest_rows}), ready_count, postrun_status(config), raster_qa_status(config), NOT_RUN_YET, NOT_RUN_YET, reason)
    return StabilityResult(decision, len(manifest_rows), len({row["cell_id"] for row in manifest_rows}), ready_count, postrun_status(config), raster_qa_status(config), NOT_RUN_YET, NOT_RUN_YET, all_lane_paths(config))


def ranks_by_cell(pairwise: Sequence[dict[str, Any]], forcing_day: str, hour: int) -> dict[str, int]:
    """Return cell ranks for one forcing day/hour."""
    return {row["cell_id"]: int(row["within_slice_rank"]) for row in pairwise if row["forcing_day_id"] == forcing_day and int(row["hour_sgt"]) == hour}


def deltas_by_cell(pairwise: Sequence[dict[str, Any]], forcing_day: str, hour: int) -> dict[str, float]:
    """Return delta values for one forcing day/hour."""
    return {row["cell_id"]: float(row["delta_tmrt_p90_c"]) for row in pairwise if row["forcing_day_id"] == forcing_day and int(row["hour_sgt"]) == hour}


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


def rank_for_spearman(values: dict[str, float]) -> dict[str, float]:
    """Return deterministic ascending ranks with average ranks for ties."""
    items = sorted(values.items(), key=lambda item: (item[1], item[0]))
    ranks: dict[str, float] = {}
    idx = 0
    while idx < len(items):
        value = items[idx][1]
        end = idx
        while end < len(items) and items[end][1] == value:
            end += 1
        average_rank = (idx + 1 + end) / 2.0
        for j in range(idx, end):
            ranks[items[j][0]] = average_rank
        idx = end
    return ranks


def spearman_from_deltas(fd01: dict[str, float], fd02: dict[str, float]) -> float | None:
    """Compute Spearman correlation from two cell-delta maps."""
    cells = sorted(set(fd01) & set(fd02))
    if len(cells) < 2:
        return None
    r1 = rank_for_spearman({cell: fd01[cell] for cell in cells})
    r2 = rank_for_spearman({cell: fd02[cell] for cell in cells})
    return pearson([r1[cell] for cell in cells], [r2[cell] for cell in cells])


def sign_label(value: float) -> str:
    """Return a compact sign label with a tiny neutral band."""
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


def contrast_rows(config: dict[str, Any], pairwise: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute FD02 minus FD01 delta contrasts by cell and hour."""
    fd01, fd02 = config["forcing_days"]
    out: list[dict[str, Any]] = []
    for hour in config["hours_sgt"]:
        r1 = ranks_by_cell(pairwise, fd01, int(hour))
        r2 = ranks_by_cell(pairwise, fd02, int(hour))
        d1 = deltas_by_cell(pairwise, fd01, int(hour))
        d2 = deltas_by_cell(pairwise, fd02, int(hour))
        for cell_id in sorted(set(d1) & set(d2)):
            out.append(
                {
                    "cell_id": cell_id,
                    "hour_sgt": str(hour),
                    "fd01_forcing_day_id": fd01,
                    "fd02_forcing_day_id": fd02,
                    "contrast_direction": "FD02_minus_FD01",
                    "delta_tmrt_p90_fd01_c": format_float(d1[cell_id]),
                    "delta_tmrt_p90_fd02_c": format_float(d2[cell_id]),
                    "fd02_minus_fd01_delta_tmrt_p90_c": format_float(d2[cell_id] - d1[cell_id]),
                    "sign_stable": YES if sign_label(d1[cell_id]) == sign_label(d2[cell_id]) else "no",
                    "rank_fd01": str(r1[cell_id]),
                    "rank_fd02": str(r2[cell_id]),
                    "rank_drift": str(abs(r2[cell_id] - r1[cell_id])),
                    "notes": "FD02 - FD01 for delta_tmrt_p90_c; SOLWEIG Tmrt label only.",
                }
            )
    return out


def median(values: Sequence[float]) -> float | None:
    """Return the median of numeric values."""
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def stability_rows(config: dict[str, Any], pairwise: Sequence[dict[str, Any]], contrast: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build Spearman, top-k, sign, h10 caveat, and anchor comparison rows."""
    fd01, fd02 = config["forcing_days"]
    n_cells = int(config["expected_cell_count"])
    out: list[dict[str, Any]] = []
    anchor_roles = load_anchor_roles(config)
    included_anchor_cells = sorted(set(anchor_roles) & {row["cell_id"] for row in pairwise})
    out.append({"record_type": "h10_caveat", "cell_id": "", "hour_sgt": "10", "metric": "f4_h10_caveat_retained", "value": "caveated", "status": WARN, "details": "F4 found h10 weaker; h10 is retained for sensitivity review and is not anchor evidence."})
    out.append({"record_type": "anchor_inclusion_summary", "cell_id": "", "hour_sgt": "", "metric": "f4_anchor_cells_included", "value": str(len(included_anchor_cells)), "status": PASS, "details": ";".join(included_anchor_cells)})
    for hour in config["hours_sgt"]:
        hour_int = int(hour)
        r1 = ranks_by_cell(pairwise, fd01, hour_int)
        r2 = ranks_by_cell(pairwise, fd02, hour_int)
        d1 = deltas_by_cell(pairwise, fd01, hour_int)
        d2 = deltas_by_cell(pairwise, fd02, hour_int)
        rho = spearman_from_deltas(d1, d2)
        out.append({"record_type": "spearman_by_hour", "cell_id": "", "hour_sgt": str(hour), "metric": "spearman_delta_tmrt_p90_fd01_fd02", "value": format_float(rho) if rho is not None else "", "status": PASS if rho is not None else WARN, "details": "Spearman correlation between FD01 and FD02 delta_tmrt_p90_c ranks by hour."})
        stable_sign_count = sum(1 for cell_id in sorted(set(d1) & set(d2)) if sign_label(d1[cell_id]) == sign_label(d2[cell_id]))
        out.append({"record_type": "sign_stability_by_hour", "cell_id": "", "hour_sgt": str(hour), "metric": "sign_stability_fraction", "value": format_float(stable_sign_count / n_cells if n_cells else math.nan), "status": PASS if stable_sign_count == n_cells else WARN, "details": f"{stable_sign_count}/{n_cells} cells have stable delta sign."})
        for label in ("top5", "top10pct", "top20pct"):
            k = top_k_count(label, n_cells)
            top1 = {cell for cell, _rank in sorted(r1.items(), key=lambda item: (item[1], item[0]))[:k]}
            top2 = {cell for cell, _rank in sorted(r2.items(), key=lambda item: (item[1], item[0]))[:k]}
            overlap = len(top1 & top2)
            out.append({"record_type": "top_k_overlap_by_hour", "cell_id": "", "hour_sgt": str(hour), "metric": label, "value": format_float(overlap / k if k else math.nan), "status": PASS if overlap == k else WARN, "details": f"overlap={overlap}/{k}; FD01_top={';'.join(sorted(top1))}; FD02_top={';'.join(sorted(top2))}"})
        for role in ("robust_priority_anchor", "neutral_boundary", "unstable_review"):
            cells = sorted(cell for cell, roles in anchor_roles.items() if role in roles and cell in d1 and cell in d2)
            values1 = [d1[cell] for cell in cells]
            values2 = [d2[cell] for cell in cells]
            out.append({"record_type": "f4_anchor_role_comparison", "cell_id": ";".join(cells), "hour_sgt": str(hour), "metric": role, "value": f"n={len(cells)};fd01_median={format_float(median(values1))};fd02_median={format_float(median(values2))}", "status": PASS if cells else WARN, "details": "F4 role cells compared when present in N150 F5 pairwise labels."})
    return out


def run(config_path: Path) -> StabilityResult:
    """Run F5 stability summaries or NOT_RUN_YET placeholder mode."""
    config = read_config(repo_path(config_path))
    outputs = config["outputs"]
    manifest_rows = read_csv_rows(repo_path(outputs["manifest"]))
    pairwise_path = repo_path(outputs["pairwise_delta_by_cell_hour"])
    reason = "Label merge has not produced 1500 pairwise delta rows."
    if not pairwise_path.exists():
        return write_not_run_outputs(config, reason)
    pairwise = read_csv_rows(pairwise_path)
    if not pairwise_ready(config, pairwise):
        return write_not_run_outputs(config, reason)

    contrast = contrast_rows(config, pairwise)
    stability = stability_rows(config, pairwise, contrast)
    write_csv_rows(repo_path(outputs["forcing_day_contrast_by_cell_hour"]), contrast, CONTRAST_FIELDS)
    write_csv_rows(repo_path(outputs["stability_summary"]), stability, STABILITY_FIELDS)
    ready_count = precheck_ready_count(config)
    decision = N150_MULTIFORCING_STABILITY_REVIEW_READY
    risk_rows = execution_risk_register_rows(config)
    write_cn_doc(repo_path(outputs["canonical_note_cn"]), config, decision, ready_count, postrun_status(config), raster_qa_status(config), PASS, PASS)
    write_report(repo_path(outputs["report"]), config, decision, ready_count, postrun_status(config), raster_qa_status(config), PASS, PASS, risk_rows)
    write_status(repo_path(outputs["status"]), config, decision, len(manifest_rows), len({row["cell_id"] for row in manifest_rows}), ready_count, postrun_status(config), raster_qa_status(config), PASS, PASS, "F5 stability summary created; B9 remains blocked pending separate promotion review.")
    return StabilityResult(decision, len(manifest_rows), len({row["cell_id"] for row in manifest_rows}), ready_count, postrun_status(config), raster_qa_status(config), PASS, PASS, all_lane_paths(config))


def main() -> int:
    """Parse CLI args and run F5 stability summaries."""
    parser = argparse.ArgumentParser(
        description=(
            "Build B8.5-F5 N150 forcing-day stability summaries from compact F5 "
            "pairwise labels. Before human execution it writes NOT_RUN_YET placeholders."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="F5 YAML config path.")
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
    print(f"Label merge status: {result.label_merge_status}")
    print(f"Stability status: {result.stability_status}")
    print("QGIS/SOLWEIG executed by Codex: no")
    print("B9 status: blocked")
    print("Files created:")
    for path in result.files_created:
        print(f"- {rel(path)}")
    return 0 if result.decision_status in {READY_FOR_HUMAN_N150_MULTIFORCING, N150_MULTIFORCING_STABILITY_REVIEW_READY} else 2


if __name__ == "__main__":
    raise SystemExit(main())
