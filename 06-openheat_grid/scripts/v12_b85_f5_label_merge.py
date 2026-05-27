"""Merge B8.5-F5 N150 multi-forcing raster QA stats into compact labels.

Inputs:
    configs/v12/systemb_b85_f5_n150_multiforcing.yaml
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_raster_stats.csv
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_alignment_qa.csv
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_sanity_checks.csv

Outputs:
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_cell_hour_summary.csv
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_pairwise_delta_by_cell_hour.csv
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_label_merge_plan.csv
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/b85_f5_report.md
    outputs/v12_surrogate/b8_5_f5_n150_multiforcing/B8_5_F5_STATUS.md

Saved metrics:
    Per cell/forcing/hour/scenario compact Tmrt stats and overhead_as_canopy
    minus base labels: delta_tmrt_mean_c, delta_tmrt_p50_c, delta_tmrt_p90_c,
    delta_tmrt_p95_c, base_tmrt_p90_c, and overhead_tmrt_p90_c.

If manual execution has not happened yet, this script writes a NOT_RUN_YET
merge plan and empty schemas without failing. It does not mix old N150
single-forcing labels into the new F5 labels except as explicit comparison
metadata.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from v12_b85_f5_prepare_n150_multiforcing import (
    CELL_HOUR_FIELDS,
    FAILED,
    LABEL_MERGE_PLAN_FIELDS,
    NOT_RUN_YET,
    N150_MULTIFORCING_EXECUTED_PASS,
    PAIRWISE_FIELDS,
    PASS,
    READY_FOR_HUMAN_N150_MULTIFORCING,
    ROOT,
    WARN,
    YES,
    all_lane_paths,
    clean,
    execution_risk_register_rows,
    label_merge_plan_rows,
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
class LabelMergeResult:
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
    """Return whether raster stats are ready for label merge."""
    if len(stats) != int(config["expected_run_count"]):
        return False
    if not stats or any(clean(row.get("sanity_status")) not in {PASS, WARN} for row in stats):
        return False
    required = {"mean_c", "p50_c", "p90_c", "p95_c"}
    if any(any(not clean(row.get(field)) for field in required) for row in stats):
        return False
    alignment_path = repo_path(config["outputs"]["alignment_qa"])
    sanity_path = repo_path(config["outputs"]["sanity_checks"])
    if not alignment_path.exists() or not sanity_path.exists():
        return False
    if any(clean(row.get("status")) == "FAIL" for row in read_csv_rows(alignment_path)):
        return False
    if any(clean(row.get("status")) == "FAIL" for row in read_csv_rows(sanity_path)):
        return False
    return True


def raster_qa_status(config: dict[str, Any]) -> str:
    """Return compact raster QA status."""
    path = repo_path(config["outputs"]["raster_stats"])
    if not path.exists():
        return NOT_RUN_YET
    stats = read_csv_rows(path)
    if raster_qa_ready(config, stats):
        return PASS
    if stats and all(clean(row.get("sanity_status")) == NOT_RUN_YET for row in stats):
        return NOT_RUN_YET
    return "PARTIAL_OR_BLOCKED"


def write_not_run_outputs(config: dict[str, Any], reason: str) -> LabelMergeResult:
    """Write NOT_RUN_YET merge plan and empty schemas."""
    outputs = config["outputs"]
    manifest_rows = read_csv_rows(repo_path(outputs["manifest"]))
    ready_count = precheck_ready_count(config)
    decision = READY_FOR_HUMAN_N150_MULTIFORCING
    write_csv_rows(repo_path(outputs["cell_hour_summary"]), [], CELL_HOUR_FIELDS)
    write_csv_rows(repo_path(outputs["pairwise_delta_by_cell_hour"]), [], PAIRWISE_FIELDS)
    plan = label_merge_plan_rows(config, NOT_RUN_YET)
    plan.append({"artifact": "not_run_yet_reason", "status": NOT_RUN_YET, "source": rel(outputs["raster_stats"]), "output": rel(outputs["pairwise_delta_by_cell_hour"]), "expected_rows": "0", "notes": reason})
    write_csv_rows(repo_path(outputs["label_merge_plan"]), plan, LABEL_MERGE_PLAN_FIELDS)
    risk_rows = execution_risk_register_rows(config)
    write_cn_doc(repo_path(outputs["canonical_note_cn"]), config, decision, ready_count, postrun_status(config), raster_qa_status(config), NOT_RUN_YET, NOT_RUN_YET)
    write_report(repo_path(outputs["report"]), config, decision, ready_count, postrun_status(config), raster_qa_status(config), NOT_RUN_YET, NOT_RUN_YET, risk_rows)
    write_status(repo_path(outputs["status"]), config, decision, len(manifest_rows), len({row["cell_id"] for row in manifest_rows}), ready_count, postrun_status(config), raster_qa_status(config), NOT_RUN_YET, NOT_RUN_YET, reason)
    return LabelMergeResult(decision, len(manifest_rows), len({row["cell_id"] for row in manifest_rows}), ready_count, postrun_status(config), raster_qa_status(config), NOT_RUN_YET, NOT_RUN_YET, all_lane_paths(config))


def float_value(row: dict[str, str], field: str) -> float:
    """Return a required float field."""
    return float(clean(row.get(field)))


def cell_hour_rows(stats: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
    """Return per-cell, per-hour, per-scenario Tmrt summary rows."""
    return [
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
        for row in stats
    ]


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
    by_key = {(row["cell_id"], row["forcing_day_id"], int(row["hour_sgt"]), row["scenario"]): row for row in stats}
    out: list[dict[str, Any]] = []
    for cell_id in sorted({row["cell_id"] for row in stats}):
        for forcing_day in config["forcing_days"]:
            for hour in config["hours_sgt"]:
                base = by_key[(cell_id, forcing_day, int(hour), "base")]
                overhead = by_key[(cell_id, forcing_day, int(hour), "overhead_as_canopy")]
                out.append(
                    {
                        "cell_id": cell_id,
                        "forcing_day_id": forcing_day,
                        "hour_sgt": str(hour),
                        "base_tmrt_p90_c": base["p90_c"],
                        "overhead_tmrt_p90_c": overhead["p90_c"],
                        "delta_tmrt_mean_c": format_float(float_value(overhead, "mean_c") - float_value(base, "mean_c")),
                        "delta_tmrt_p50_c": format_float(float_value(overhead, "p50_c") - float_value(base, "p50_c")),
                        "delta_tmrt_p90_c": format_float(float_value(overhead, "p90_c") - float_value(base, "p90_c")),
                        "delta_tmrt_p95_c": format_float(float_value(overhead, "p95_c") - float_value(base, "p95_c")),
                        "within_slice_rank": "",
                        "rank_direction": "",
                        "label_source": "b85_f5_n150_multiforcing_raster_qa",
                        "legacy_single_forcing_comparison_source": "metadata_only_not_merged",
                        "notes": "overhead_as_canopy - base; SOLWEIG Tmrt label only, not WBGT/risk/B9.",
                    }
                )
    ranked: list[dict[str, Any]] = []
    for forcing_day in config["forcing_days"]:
        for hour in config["hours_sgt"]:
            group = [row for row in out if row["forcing_day_id"] == forcing_day and int(row["hour_sgt"]) == int(hour)]
            ranked.extend(rank_values(group, "delta_tmrt_p90_c", "within_slice_rank"))
    return sorted(ranked, key=lambda row: (row["cell_id"], row["forcing_day_id"], int(row["hour_sgt"])))


def run(config_path: Path) -> LabelMergeResult:
    """Run label merge or NOT_RUN_YET placeholder mode."""
    config = read_config(repo_path(config_path))
    outputs = config["outputs"]
    manifest_rows = read_csv_rows(repo_path(outputs["manifest"]))
    stats_path = repo_path(outputs["raster_stats"])
    reason = "Raster QA has not confirmed 3000/3000 content-ready rasters."
    if not stats_path.exists():
        return write_not_run_outputs(config, reason)
    stats = read_csv_rows(stats_path)
    if not raster_qa_ready(config, stats):
        return write_not_run_outputs(config, reason)

    cell_hour = cell_hour_rows(stats)
    pairwise = pairwise_delta_rows(config, stats)
    plan = label_merge_plan_rows(config, PASS)
    write_csv_rows(repo_path(outputs["cell_hour_summary"]), cell_hour, CELL_HOUR_FIELDS)
    write_csv_rows(repo_path(outputs["pairwise_delta_by_cell_hour"]), pairwise, PAIRWISE_FIELDS)
    write_csv_rows(repo_path(outputs["label_merge_plan"]), plan, LABEL_MERGE_PLAN_FIELDS)
    ready_count = precheck_ready_count(config)
    decision = N150_MULTIFORCING_EXECUTED_PASS
    risk_rows = execution_risk_register_rows(config)
    write_cn_doc(repo_path(outputs["canonical_note_cn"]), config, decision, ready_count, postrun_status(config), PASS, PASS, NOT_RUN_YET)
    write_report(repo_path(outputs["report"]), config, decision, ready_count, postrun_status(config), PASS, PASS, NOT_RUN_YET, risk_rows)
    write_status(repo_path(outputs["status"]), config, decision, len(manifest_rows), len({row["cell_id"] for row in manifest_rows}), ready_count, postrun_status(config), PASS, PASS, NOT_RUN_YET, "Label merge created compact F5 pairwise deltas; stability summary still required.")
    return LabelMergeResult(decision, len(manifest_rows), len({row["cell_id"] for row in manifest_rows}), ready_count, postrun_status(config), PASS, PASS, NOT_RUN_YET, all_lane_paths(config))


def main() -> int:
    """Parse CLI args and run F5 label merge."""
    parser = argparse.ArgumentParser(
        description=(
            "Merge B8.5-F5 N150 multi-forcing raster QA stats into compact labels. "
            "Before human execution it writes NOT_RUN_YET schemas and does not fail."
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
    return 0 if result.decision_status in {READY_FOR_HUMAN_N150_MULTIFORCING, N150_MULTIFORCING_EXECUTED_PASS} else 2


if __name__ == "__main__":
    raise SystemExit(main())
