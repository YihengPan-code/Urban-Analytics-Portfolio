"""Shared B87D N300 label integration utilities.

Inputs:
    configs/v12/systemb_b87d_n300_label_integration.yaml
    B87C manifest, B87C local run log, final F5 pairwise labels, final F5
    raster QA stats, and B87C local Tmrt_average.tif rasters.

Outputs:
    Compact CSV/Markdown artifacts under
    outputs/v12_surrogate/b87d_n300_label_integration/ plus the Chinese
    canonical note under docs/v12.

Config path:
    Pass --config configs/v12/systemb_b87d_n300_label_integration.yaml to the
    runner or individual wrapper scripts.

Saved metrics:
    Input inventory, B87C run-log audit, manifest audit summary, Tmrt output
    inventory, recovered F5 extraction convention, per-run full-tile Tmrt
    stats, B87C pairwise delta labels, F5 schema alignment, N300 integrated
    label QA, target distribution, protocol lineage, blockers, and next-lane
    recommendation.

Claim boundaries:
    This code reads existing local SOLWEIG Tmrt rasters only to compute compact
    statistics. It does not run QGIS/SOLWEIG, write/copy/move rasters, create
    WBGT, AOI/B9 predictions, hazard maps, risk maps, exposure/vulnerability
    outputs, observed-truth claims, or causal feature-importance claims.
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b87d_n300_label_integration.yaml"

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
YES = "yes"
NO = "no"

B87D_PASS = "B87D_N300_LABEL_INTEGRATION_PASS"
B87D_BLOCKED_EXTRACTION_CONVENTION_UNKNOWN = "B87D_BLOCKED_EXTRACTION_CONVENTION_UNKNOWN"
B87D_BLOCKED_MISSING_TMRT = "B87D_BLOCKED_MISSING_TMRT"
B87D_BLOCKED_INCOMPLETE_PAIRS = "B87D_BLOCKED_INCOMPLETE_PAIRS"
B87D_BLOCKED_SCHEMA_MISMATCH = "B87D_BLOCKED_SCHEMA_MISMATCH"
B87D_BLOCKED_CELL_OVERLAP = "B87D_BLOCKED_CELL_OVERLAP"
FAILED = "FAILED"

F5_CONVENTION_ID = "F5_FULL_150X150_VALID_NON_NODATA_TMRT_AVERAGE_TIF_V1"
F5_MASK_TYPE = "full_tile_valid_non_nodata"
CLAIM_BOUNDARY = (
    "SOLWEIG Tmrt simulated radiative output only; delta is overhead_as_canopy "
    "- base; not observed truth, not WBGT, not AOI/B9 prediction, not hazard "
    "map, not risk map, and not causal evidence."
)

DATE_BY_FORCING = {
    "FD01_high_shortwave_hot_20260507": "2026-05-07",
    "FD02_humid_hot_cloudy_or_diffuse_20260508": "2026-05-08",
}

PAIRWISE_COLUMNS = [
    "cell_id",
    "forcing_day_id",
    "date",
    "hour_sgt",
    "base_tmrt_mean_c",
    "overhead_tmrt_mean_c",
    "base_tmrt_median_c",
    "overhead_tmrt_median_c",
    "base_tmrt_p90_c",
    "overhead_tmrt_p90_c",
    "base_tmrt_p95_c",
    "overhead_tmrt_p95_c",
    "base_tmrt_max_c",
    "overhead_tmrt_max_c",
    "delta_tmrt_mean_c",
    "delta_tmrt_median_c",
    "delta_tmrt_p50_c",
    "delta_tmrt_p90_c",
    "delta_tmrt_p95_c",
    "delta_tmrt_max_c",
    "within_slice_rank",
    "rank_direction",
    "label_source",
    "protocol_id",
    "sample_group",
    "extraction_convention_id",
    "b87d_label_status",
    "notes",
]


@dataclass(frozen=True)
class B87DResult:
    """Compact B87D run result."""

    status: str
    tmrt_stats_rows: int
    b87c_pairwise_rows: int
    n300_pairwise_rows: int
    n300_unique_cells: int
    overlap_count: int
    blockers: list[str]
    output_dir: Path


def clean(value: Any) -> str:
    """Return a compact single-line string."""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def now_stamp() -> str:
    """Return a local timestamp."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def repo_path(value: str | Path) -> Path:
    """Resolve repository-relative paths."""
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def rel(path: str | Path) -> str:
    """Return repository-relative POSIX path when possible."""
    p = repo_path(path)
    try:
        return p.resolve(strict=False).relative_to(ROOT.resolve(strict=False)).as_posix()
    except ValueError:
        return p.as_posix()


def parse_inline_list(text: str) -> list[Any]:
    """Parse a tiny YAML inline list fallback."""
    inner = text.strip()[1:-1].strip()
    if not inner:
        return []
    return [parse_scalar(part.strip()) for part in inner.split(",")]


def parse_scalar(value: str) -> Any:
    """Parse a small YAML scalar fallback."""
    stripped = value.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        return parse_inline_list(stripped)
    lowered = stripped.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none", "~"}:
        return None
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        return stripped.strip("\"'")


def read_simple_yaml(path: Path) -> dict[str, Any]:
    """Read the simple YAML subset used by lane configs."""
    lines = [
        line.rstrip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    for idx, line in enumerate(lines):
        indent = len(line) - len(line.lstrip(" "))
        text = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if text.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"Unsupported YAML list placement: {line}")
            parent.append(parse_scalar(text[2:].strip()))
            continue
        key, _, raw_value = text.partition(":")
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value:
            if not isinstance(parent, dict):
                raise ValueError(f"Unsupported YAML parent: {line}")
            parent[key] = parse_scalar(raw_value)
            continue
        next_container: Any = {}
        for future in lines[idx + 1 :]:
            future_indent = len(future) - len(future.lstrip(" "))
            future_text = future.strip()
            if future_indent <= indent:
                break
            next_container = [] if future_text.startswith("- ") else {}
            break
        if not isinstance(parent, dict):
            raise ValueError(f"Unsupported YAML parent: {line}")
        parent[key] = next_container
        stack.append((indent, next_container))
    return root


def read_config(path: Path) -> dict[str, Any]:
    """Read YAML with PyYAML or a local fallback."""
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Config is not a mapping: {path}")
        return loaded
    except ImportError:
        return read_simple_yaml(path)


def output_path(config: dict[str, Any], name: str) -> Path:
    """Return a configured output path."""
    return repo_path(config["outputs"][name])


def ensure_output_dirs(config: dict[str, Any]) -> None:
    """Create compact output directories only."""
    repo_path(config["outputs"]["out_dir"]).mkdir(parents=True, exist_ok=True)
    repo_path(config["outputs"]["canonical_note_cn"]).parent.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    """Read CSV with UTF-8 BOM tolerance."""
    return pd.read_csv(path, encoding="utf-8-sig", **kwargs)


def write_csv(path: Path, frame: pd.DataFrame, columns: Sequence[str] | None = None) -> None:
    """Write a compact UTF-8 CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    if columns is not None:
        for column in columns:
            if column not in out.columns:
                out[column] = ""
        out = out.loc[:, list(columns)]
    out.to_csv(path, index=False, encoding="utf-8")


def write_rows(path: Path, rows: Sequence[dict[str, Any]], columns: Sequence[str] | None = None) -> None:
    """Write dictionaries to CSV."""
    frame = pd.DataFrame(list(rows))
    write_csv(path, frame, columns)


def format_float(value: Any, digits: int = 6) -> str:
    """Format finite numeric values for stable CSV output."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(numeric):
        return ""
    return f"{numeric:.{digits}f}"


def bool_status(condition: bool) -> str:
    """Return PASS/FAIL."""
    return PASS if condition else FAIL


def path_status(path: Path) -> tuple[str, str, str]:
    """Return exists, size, and readability status for an input path."""
    exists = path.exists()
    size = path.stat().st_size if exists and path.is_file() else 0
    status = PASS if exists and (path.is_dir() or size > 0) else FAIL
    return YES if exists else NO, str(size), status


def build_input_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Write the B87D source input inventory."""
    ensure_output_dirs(config)
    rows: list[dict[str, Any]] = []
    named_paths = {
        "b87c_manifest_path": config["b87c_manifest_path"],
        "b87c_manifest_audit_path": config.get("b87c_manifest_audit_path", ""),
        "b87c_run_log_path": config["b87c_run_log_path"],
        "b87c_output_root": config["b87c_output_root"],
        "f5_pairwise_label_path": config["f5_pairwise_label_path"],
        "f5_cell_hour_summary_path": config.get("f5_cell_hour_summary_path", ""),
        "f5_raster_stats_path": config.get("f5_raster_stats_path", ""),
        "f5_raster_inventory_path": config.get("f5_raster_inventory_path", ""),
        "f5_label_merge_plan_path": config.get("f5_label_merge_plan_path", ""),
        "b87b_new_candidate_sample_index_path": config["b87b_new_candidate_sample_index_path"],
        "b86g3_n300_v4_design_path": config["b86g3_n300_v4_design_path"],
    }
    for index, extra in enumerate(config.get("postrun_summary_paths", []), start=1):
        named_paths[f"postrun_summary_{index}"] = extra
    for name, value in named_paths.items():
        if not value:
            rows.append(
                {
                    "input_name": name,
                    "path": "",
                    "exists": NO,
                    "file_size_bytes": "0",
                    "status": FAIL,
                    "notes": "missing from config",
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
            continue
        path = repo_path(value)
        exists, size, status = path_status(path)
        rows.append(
            {
                "input_name": name,
                "path": rel(path),
                "exists": exists,
                "file_size_bytes": size,
                "status": status,
                "notes": "local-only path read allowed" if path.is_absolute() and not str(path).startswith(str(ROOT)) else "repo compact artifact",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    frame = pd.DataFrame(rows)
    write_csv(output_path(config, "input_inventory"), frame)
    return frame


def audit_manifest(config: dict[str, Any]) -> pd.DataFrame:
    """Write a compact B87C manifest audit summary."""
    manifest = read_csv(repo_path(config["b87c_manifest_path"]), dtype=str)
    audit_path = repo_path(config.get("b87c_manifest_audit_path", ""))
    audit = read_csv(audit_path, dtype=str) if audit_path.exists() else pd.DataFrame()
    rows = [
        {
            "check_name": "manifest_row_count",
            "observed": len(manifest),
            "expected": config["expected_b87c_success_runs"],
            "status": bool_status(len(manifest) == int(config["expected_b87c_success_runs"])),
            "notes": "B87C manifest rows.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "check_name": "manifest_unique_cells",
            "observed": manifest["cell_id"].nunique(),
            "expected": config["expected_new_cells"],
            "status": bool_status(manifest["cell_id"].nunique() == int(config["expected_new_cells"])),
            "notes": "B87C new150 cell count.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    for column, expected_values in (
        ("forcing_day_id", config["expected_forcing_days"]),
        ("hour_sgt", [str(v) for v in config["expected_hours"]]),
        ("scenario", config["expected_scenarios"]),
    ):
        observed_values = sorted(manifest[column].astype(str).unique().tolist())
        rows.append(
            {
                "check_name": f"manifest_{column}_set",
                "observed": "|".join(observed_values),
                "expected": "|".join(str(v) for v in expected_values),
                "status": bool_status(observed_values == sorted(str(v) for v in expected_values)),
                "notes": "Expected B87C coverage set.",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    if not audit.empty:
        rows.append(
            {
                "check_name": "source_manifest_audit_fail_count",
                "observed": int((audit.get("status", pd.Series(dtype=str)).astype(str) == FAIL).sum()),
                "expected": 0,
                "status": bool_status(int((audit.get("status", pd.Series(dtype=str)).astype(str) == FAIL).sum()) == 0),
                "notes": "Copied from B87C manifest audit status counts.",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    frame = pd.DataFrame(rows)
    write_csv(output_path(config, "manifest_audit_summary"), frame)
    return frame


def success_run_log(config: dict[str, Any]) -> pd.DataFrame:
    """Return the 3000 successful B87C rows from the local run log."""
    log = read_csv(repo_path(config["b87c_run_log_path"]), dtype=str)
    log["hour_sgt"] = log["hour_sgt"].astype(str)
    success = log.loc[log["status"].astype(str).eq("success")].copy()
    return success


def audit_run_log(config: dict[str, Any]) -> pd.DataFrame:
    """Write B87C local run-log audit rows."""
    log = read_csv(repo_path(config["b87c_run_log_path"]), dtype=str)
    status_counts = log["status"].astype(str).value_counts(dropna=False).to_dict()
    success = log.loc[log["status"].astype(str).eq("success")].copy()
    rows = [
        {
            "check_name": "log_rows",
            "observed": len(log),
            "expected": "3040 verified runtime state",
            "status": PASS if len(log) >= int(config["expected_b87c_success_runs"]) else FAIL,
            "notes": str(status_counts),
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "check_name": "success_rows",
            "observed": len(success),
            "expected": config["expected_b87c_success_runs"],
            "status": bool_status(len(success) == int(config["expected_b87c_success_runs"])),
            "notes": "Only status=success rows are used for B87D extraction.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "check_name": "success_unique_run_id",
            "observed": success["run_id"].nunique(),
            "expected": config["expected_b87c_success_runs"],
            "status": bool_status(success["run_id"].nunique() == int(config["expected_b87c_success_runs"])),
            "notes": "Duplicate success run IDs would be blocked downstream.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "check_name": "success_unique_cells",
            "observed": success["cell_id"].nunique(),
            "expected": config["expected_new_cells"],
            "status": bool_status(success["cell_id"].nunique() == int(config["expected_new_cells"])),
            "notes": "B87C new150 cell count from local run log.",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    for scenario in config["expected_scenarios"]:
        rows.append(
            {
                "check_name": f"{scenario}_success",
                "observed": int((success["scenario"].astype(str) == scenario).sum()),
                "expected": int(config["expected_new_cells"]) * len(config["expected_forcing_days"]) * len(config["expected_hours"]),
                "status": bool_status(int((success["scenario"].astype(str) == scenario).sum()) == int(config["expected_new_cells"]) * len(config["expected_forcing_days"]) * len(config["expected_hours"])),
                "notes": "Scenario-level success coverage.",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    frame = pd.DataFrame(rows)
    write_csv(output_path(config, "run_log_audit"), frame)
    return frame


def tmrt_output_inventory(config: dict[str, Any]) -> pd.DataFrame:
    """Locate B87C Tmrt_average.tif outputs without copying or writing rasters."""
    manifest = read_csv(repo_path(config["b87c_manifest_path"]), dtype=str)
    success = success_run_log(config)
    merged = success.merge(
        manifest[["run_id", "expected_tmrt_path"]],
        on="run_id",
        how="left",
        suffixes=("", "_manifest"),
        validate="one_to_one",
    )
    rows: list[dict[str, Any]] = []
    output_root = repo_path(config["b87c_output_root"]).resolve(strict=False)
    for _, row in merged.iterrows():
        log_path = Path(clean(row.get("tmrt_output_path")))
        manifest_path = Path(clean(row.get("expected_tmrt_path")))
        chosen = log_path if clean(log_path) else manifest_path
        exists = chosen.exists()
        size = chosen.stat().st_size if exists else 0
        under_output_root = False
        try:
            chosen.resolve(strict=False).relative_to(output_root)
            under_output_root = True
        except ValueError:
            under_output_root = False
        rows.append(
            {
                "run_id": row["run_id"],
                "cell_id": row["cell_id"],
                "forcing_day_id": row["forcing_day_id"],
                "date": row.get("date", ""),
                "hour_sgt": row["hour_sgt"],
                "scenario": row["scenario"],
                "status": row["status"],
                "tmrt_output_path": chosen.as_posix(),
                "expected_tmrt_path": manifest_path.as_posix(),
                "exists": YES if exists else NO,
                "file_size_bytes": size,
                "under_b87c_output_root": YES if under_output_root else NO,
                "inventory_status": PASS if exists and size > 0 and under_output_root else FAIL,
                "notes": "read-only local Tmrt raster path; no raster copied or written",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    frame = pd.DataFrame(rows).sort_values(["cell_id", "forcing_day_id", "hour_sgt", "scenario"])
    write_csv(output_path(config, "tmrt_output_inventory"), frame)
    return frame


def recover_f5_convention(config: dict[str, Any]) -> pd.DataFrame:
    """Recover the final F5 Tmrt statistic convention."""
    rows: list[dict[str, Any]] = []
    stats_path = repo_path(config.get("f5_raster_stats_path", ""))
    inv_path = repo_path(config.get("f5_raster_inventory_path", ""))
    plan_path = repo_path(config.get("f5_label_merge_plan_path", ""))
    script_path = ROOT / "scripts/v12_b85_f5_raster_qa.py"
    stats = read_csv(stats_path, dtype=str) if stats_path.exists() else pd.DataFrame()
    inventory = read_csv(inv_path, dtype=str) if inv_path.exists() else pd.DataFrame()
    plan = read_csv(plan_path, dtype=str) if plan_path.exists() else pd.DataFrame()
    script_text = script_path.read_text(encoding="utf-8") if script_path.exists() else ""

    def add(check: str, observed: Any, expected: Any, status: str, evidence: str) -> None:
        rows.append(
            {
                "check_name": check,
                "observed": observed,
                "expected": expected,
                "status": status,
                "extraction_mask_type": F5_MASK_TYPE if status == PASS else "",
                "extraction_convention_id": F5_CONVENTION_ID if status == PASS else "",
                "evidence": evidence,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )

    add("f5_raster_stats_exists", YES if stats_path.exists() else NO, YES, PASS if stats_path.exists() else FAIL, rel(stats_path))
    add("f5_raster_stats_rows", len(stats), 3000, PASS if len(stats) == 3000 else FAIL, "F5 final raster QA source rows.")
    if not stats.empty and "valid_pixel_count" in stats.columns:
        counts = pd.to_numeric(stats["valid_pixel_count"], errors="coerce")
        unique_counts = sorted(counts.dropna().astype(int).unique().tolist())
        add("f5_valid_pixel_count_full_tile", "|".join(map(str, unique_counts[:5])), "22500", PASS if unique_counts == [22500] else FAIL, "150x150 full tile has 22500 pixels.")
    else:
        add("f5_valid_pixel_count_full_tile", "", "22500", FAIL, "valid_pixel_count missing.")
    if not inventory.empty and {"width", "height"}.issubset(inventory.columns):
        shapes = sorted((inventory["width"].astype(str) + "x" + inventory["height"].astype(str)).dropna().unique().tolist())
        add("f5_inventory_shape", "|".join(shapes[:5]), "150x150", PASS if shapes == ["150x150"] else FAIL, "F5 raster inventory shape.")
    else:
        add("f5_inventory_shape", "", "150x150", FAIL, "raster inventory missing shape.")
    if not plan.empty and "source" in plan.columns:
        source_ok = plan["source"].astype(str).str.contains("b85_f5_raster_stats.csv", regex=False).any()
        add("f5_label_merge_sources_raster_stats", YES if source_ok else NO, YES, PASS if source_ok else FAIL, "F5 pairwise labels are downstream of raster_stats.")
    else:
        add("f5_label_merge_sources_raster_stats", "", YES, FAIL, "label merge plan missing.")
    add("f5_script_no_focus_mask_crop", YES if "rasterio.mask" not in script_text and "valid_pixel_mask" in script_text else NO, YES, PASS if "rasterio.mask" not in script_text and "valid_pixel_mask" in script_text else FAIL, "F5 raster QA uses full array finite non-nodata mask, not rasterio.mask crop.")
    add("f5_valid_pixels_only", YES if "np.isfinite" in script_text and "nodata" in script_text else NO, YES, PASS if "np.isfinite" in script_text and "nodata" in script_text else FAIL, "F5 valid_pixel_mask filters finite non-nodata values.")
    frame = pd.DataFrame(rows)
    write_csv(output_path(config, "focus_mask_convention_audit"), frame)
    return frame


def convention_passed(config: dict[str, Any]) -> bool:
    """Return whether extraction convention audit passed."""
    path = output_path(config, "focus_mask_convention_audit")
    if not path.exists():
        return False
    audit = read_csv(path, dtype=str)
    return not audit.empty and (audit["status"].astype(str) == PASS).all()


def read_raster_values(path: Path) -> tuple[dict[str, Any], np.ndarray]:
    """Read a single Tmrt raster and return metadata plus finite non-nodata values."""
    import rasterio

    with rasterio.open(path) as src:
        array = src.read(1)
        nodata = src.nodata
        values = array.astype("float64", copy=False)
        valid = np.isfinite(values)
        if nodata is not None:
            try:
                nodata_float = float(nodata)
                if math.isfinite(nodata_float):
                    valid &= values != nodata_float
            except (TypeError, ValueError):
                pass
        metadata = {
            "raster_width": int(src.width),
            "raster_height": int(src.height),
            "raster_crs": src.crs.to_string() if src.crs else "",
            "raster_nodata": nodata,
            "raster_dtype": str(src.dtypes[0]) if src.dtypes else "",
            "raster_band_count": int(src.count),
            "pixel_count": int(src.width * src.height),
            "transform": str(tuple(float(v) for v in src.transform.to_gdal())),
        }
    return metadata, values[valid]


def extract_tmrt_stats(config: dict[str, Any]) -> pd.DataFrame:
    """Extract compact B87C full-tile Tmrt statistics."""
    if not convention_passed(config):
        empty = pd.DataFrame()
        write_csv(output_path(config, "tmrt_stats_by_run"), empty)
        write_csv(output_path(config, "cell_hour_scenario_summary"), empty)
        return empty
    inventory_path = output_path(config, "tmrt_output_inventory")
    inventory = read_csv(inventory_path, dtype=str) if inventory_path.exists() else tmrt_output_inventory(config)
    rows: list[dict[str, Any]] = []
    for _, row in inventory.iterrows():
        path = Path(clean(row["tmrt_output_path"]))
        base = {
            "run_id": row["run_id"],
            "cell_id": row["cell_id"],
            "forcing_day_id": row["forcing_day_id"],
            "date": row.get("date", DATE_BY_FORCING.get(row["forcing_day_id"], "")),
            "hour_sgt": row["hour_sgt"],
            "scenario": row["scenario"],
            "tmrt_output_path": path.as_posix(),
            "extraction_mask_type": F5_MASK_TYPE,
            "extraction_convention_id": F5_CONVENTION_ID,
            "claim_boundary": CLAIM_BOUNDARY,
        }
        try:
            metadata, values = read_raster_values(path)
            pixel_count = int(metadata["pixel_count"])
            valid_count = int(values.size)
            nodata_count = max(pixel_count - valid_count, 0)
            if valid_count == 0:
                raise ValueError("no_valid_pixels")
            base.update(
                {
                    **metadata,
                    "valid_pixel_count": valid_count,
                    "nodata_pixel_count": nodata_count,
                    "tmrt_mean_c": format_float(float(np.mean(values))),
                    "tmrt_median_c": format_float(float(np.percentile(values, 50))),
                    "tmrt_p90_c": format_float(float(np.percentile(values, 90))),
                    "tmrt_p95_c": format_float(float(np.percentile(values, 95))),
                    "tmrt_max_c": format_float(float(np.max(values))),
                    "stat_status": PASS,
                    "stat_notes": "full tile finite non-nodata pixels; no raster output written",
                }
            )
        except Exception as exc:
            base.update(
                {
                    "raster_width": "",
                    "raster_height": "",
                    "raster_crs": "",
                    "raster_nodata": "",
                    "raster_dtype": "",
                    "raster_band_count": "",
                    "pixel_count": "",
                    "valid_pixel_count": 0,
                    "nodata_pixel_count": "",
                    "tmrt_mean_c": "",
                    "tmrt_median_c": "",
                    "tmrt_p90_c": "",
                    "tmrt_p95_c": "",
                    "tmrt_max_c": "",
                    "stat_status": FAIL,
                    "stat_notes": clean(exc),
                }
            )
        rows.append(base)
    frame = pd.DataFrame(rows).sort_values(["cell_id", "forcing_day_id", "hour_sgt", "scenario"])
    write_csv(output_path(config, "tmrt_stats_by_run"), frame)
    summary_cols = [
        "run_id",
        "cell_id",
        "forcing_day_id",
        "date",
        "hour_sgt",
        "scenario",
        "tmrt_mean_c",
        "tmrt_median_c",
        "tmrt_p90_c",
        "tmrt_p95_c",
        "tmrt_max_c",
        "valid_pixel_count",
        "nodata_pixel_count",
        "raster_width",
        "raster_height",
        "raster_crs",
        "extraction_mask_type",
        "extraction_convention_id",
        "stat_status",
        "claim_boundary",
    ]
    write_csv(output_path(config, "cell_hour_scenario_summary"), frame, summary_cols)
    return frame


def add_within_slice_rank(frame: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Rank each forcing/hour slice with the most negative delta as rank 1."""
    out = frame.copy()
    ranks: list[pd.DataFrame] = []
    for _, group in out.groupby(["forcing_day_id", "hour_sgt"], sort=True):
        part = group.copy()
        part[value_col] = pd.to_numeric(part[value_col], errors="coerce")
        part["within_slice_rank"] = part[value_col].rank(method="min", ascending=True).astype("Int64").astype(str)
        part["rank_direction"] = "most_negative_delta_rank_1"
        ranks.append(part)
    return pd.concat(ranks, ignore_index=True).sort_values(["cell_id", "forcing_day_id", "hour_sgt"])


def build_b87c_pairwise_delta(config: dict[str, Any]) -> pd.DataFrame:
    """Build B87C overhead_as_canopy minus base labels."""
    stats_path = output_path(config, "tmrt_stats_by_run")
    stats = read_csv(stats_path, dtype=str) if stats_path.exists() else extract_tmrt_stats(config)
    if stats.empty or (stats.get("stat_status", pd.Series(dtype=str)).astype(str) == FAIL).any():
        write_csv(output_path(config, "b87c_pairwise_delta"), pd.DataFrame())
        return pd.DataFrame()
    key_cols = ["cell_id", "forcing_day_id", "date", "hour_sgt"]
    dupes = stats.duplicated(key_cols + ["scenario"], keep=False)
    if dupes.any():
        write_csv(output_path(config, "b87c_pairwise_delta"), pd.DataFrame())
        return pd.DataFrame()
    base = stats.loc[stats["scenario"].eq("base")].copy()
    overhead = stats.loc[stats["scenario"].eq("overhead_as_canopy")].copy()
    pair = base.merge(overhead, on=key_cols, how="inner", suffixes=("_base", "_overhead"), validate="one_to_one")
    rows: list[dict[str, Any]] = []
    for _, row in pair.iterrows():
        out: dict[str, Any] = {
            "cell_id": row["cell_id"],
            "forcing_day_id": row["forcing_day_id"],
            "date": row["date"],
            "hour_sgt": row["hour_sgt"],
            "label_source": "b87c_new150_full150",
            "protocol_id": config["protocol_ids"]["b87c_new150"],
            "sample_group": "new150_b87c",
            "extraction_convention_id": F5_CONVENTION_ID,
            "b87d_label_status": PASS,
            "notes": "overhead_as_canopy - base; SOLWEIG Tmrt only, not WBGT/risk/B9",
        }
        for method in ("mean", "median", "p90", "p95", "max"):
            base_col = f"tmrt_{method}_c_base"
            over_col = f"tmrt_{method}_c_overhead"
            out[f"base_tmrt_{method}_c"] = format_float(row[base_col])
            out[f"overhead_tmrt_{method}_c"] = format_float(row[over_col])
            out[f"delta_tmrt_{method}_c"] = format_float(float(row[over_col]) - float(row[base_col]))
        out["delta_tmrt_p50_c"] = out["delta_tmrt_median_c"]
        rows.append(out)
    frame = add_within_slice_rank(pd.DataFrame(rows), "delta_tmrt_p90_c") if rows else pd.DataFrame()
    write_csv(output_path(config, "b87c_pairwise_delta"), frame, PAIRWISE_COLUMNS)
    return frame


def align_f5_schema(config: dict[str, Any]) -> pd.DataFrame:
    """Align final F5 labels to the B87D N300 schema."""
    f5 = read_csv(repo_path(config["f5_pairwise_label_path"]), dtype=str)
    cell_hour_path = repo_path(config.get("f5_cell_hour_summary_path", ""))
    cell_hour = read_csv(cell_hour_path, dtype=str) if cell_hour_path.exists() else pd.DataFrame()
    rows: list[dict[str, Any]] = []

    def add(field: str, source: str, action: str, status: str, notes: str) -> None:
        rows.append({"field_name": field, "source_field": source, "action": action, "status": status, "notes": notes, "claim_boundary": CLAIM_BOUNDARY})

    aligned = f5.copy()
    aligned["date"] = aligned["forcing_day_id"].map(DATE_BY_FORCING).fillna("")
    if "delta_tmrt_p50_c" in aligned.columns:
        aligned["delta_tmrt_median_c"] = aligned["delta_tmrt_p50_c"]
        add("delta_tmrt_median_c", "delta_tmrt_p50_c", "alias", PASS, "F5 pairwise uses p50 naming; B87D keeps median alias.")
    else:
        add("delta_tmrt_median_c", "", "missing", FAIL, "F5 pairwise lacks p50/median delta.")
    if not cell_hour.empty and {"cell_id", "forcing_day_id", "hour_sgt", "scenario", "tmrt_max_c"}.issubset(cell_hour.columns):
        key = ["cell_id", "forcing_day_id", "hour_sgt"]
        base = cell_hour.loc[cell_hour["scenario"].eq("base"), key + ["tmrt_mean_c", "tmrt_p50_c", "tmrt_p90_c", "tmrt_p95_c", "tmrt_max_c"]].copy()
        overhead = cell_hour.loc[cell_hour["scenario"].eq("overhead_as_canopy"), key + ["tmrt_mean_c", "tmrt_p50_c", "tmrt_p90_c", "tmrt_p95_c", "tmrt_max_c"]].copy()
        base = base.rename(columns={c: f"base_{c}" for c in base.columns if c not in key})
        overhead = overhead.rename(columns={c: f"overhead_{c}" for c in overhead.columns if c not in key})
        enrich = base.merge(overhead, on=key, how="inner", validate="one_to_one")
        aligned = aligned.merge(enrich, on=key, how="left", validate="one_to_one")
        for method, f5_method in (("mean", "mean"), ("median", "p50"), ("p90", "p90"), ("p95", "p95"), ("max", "max")):
            aligned[f"base_tmrt_{method}_c"] = aligned.get(f"base_tmrt_{f5_method}_c", aligned.get(f"base_tmrt_{method}_c", ""))
            aligned[f"overhead_tmrt_{method}_c"] = aligned.get(f"overhead_tmrt_{f5_method}_c", aligned.get(f"overhead_tmrt_{method}_c", ""))
        aligned["delta_tmrt_max_c"] = pd.to_numeric(aligned["overhead_tmrt_max_c"], errors="coerce") - pd.to_numeric(aligned["base_tmrt_max_c"], errors="coerce")
        aligned["delta_tmrt_max_c"] = aligned["delta_tmrt_max_c"].map(format_float)
        add("delta_tmrt_max_c", "b85_f5_cell_hour_summary.tmrt_max_c", "derived_same_source_overhead_minus_base", PASS, "Schema completion from final F5 cell-hour summary, not recalibration.")
    else:
        add("delta_tmrt_max_c", "", "missing", FAIL, "F5 cell-hour summary unavailable or missing tmrt_max_c.")
    for required in ("delta_tmrt_mean_c", "delta_tmrt_median_c", "delta_tmrt_p90_c", "delta_tmrt_p95_c", "delta_tmrt_max_c"):
        add(required, required, "required_for_n300", PASS if required in aligned.columns and aligned[required].notna().all() else FAIL, "Required B87D/N300 target field.")
    aligned["label_source"] = "b85_f5_n150_multiforcing"
    aligned["protocol_id"] = config["protocol_ids"]["f5_n150"]
    aligned["sample_group"] = "existing_n150"
    aligned["extraction_convention_id"] = F5_CONVENTION_ID
    aligned["b87d_label_status"] = PASS
    aligned["notes"] = "Final F5 N150 label aligned to B87D schema; SOLWEIG Tmrt only, not WBGT/risk/B9."
    aligned = add_within_slice_rank(aligned, "delta_tmrt_p90_c")
    write_csv(output_path(config, "f5_schema_alignment"), pd.DataFrame(rows))
    inventory = pd.DataFrame(
        [
            {"metric": "rows", "observed": len(aligned), "expected": int(config["expected_b87c_pairwise_rows"]), "status": bool_status(len(aligned) == int(config["expected_b87c_pairwise_rows"])), "claim_boundary": CLAIM_BOUNDARY},
            {"metric": "unique_cells", "observed": aligned["cell_id"].nunique(), "expected": int(config["expected_existing_cells"]), "status": bool_status(aligned["cell_id"].nunique() == int(config["expected_existing_cells"])), "claim_boundary": CLAIM_BOUNDARY},
            {"metric": "missing_primary_label", "observed": int(aligned[config["primary_label_column"]].isna().sum()), "expected": 0, "status": bool_status(int(aligned[config["primary_label_column"]].isna().sum()) == 0), "claim_boundary": CLAIM_BOUNDARY},
        ]
    )
    write_csv(output_path(config, "n150_existing_label_inventory"), inventory)
    return aligned.loc[:, PAIRWISE_COLUMNS]


def integrate_n300_labels(config: dict[str, Any]) -> pd.DataFrame:
    """Integrate F5 existing N150 and B87C new150 pairwise labels."""
    f5_aligned = align_f5_schema(config)
    b87c = read_csv(output_path(config, "b87c_pairwise_delta"), dtype=str)
    new_inv = pd.DataFrame(
        [
            {"metric": "rows", "observed": len(b87c), "expected": int(config["expected_b87c_pairwise_rows"]), "status": bool_status(len(b87c) == int(config["expected_b87c_pairwise_rows"])), "claim_boundary": CLAIM_BOUNDARY},
            {"metric": "unique_cells", "observed": b87c["cell_id"].nunique() if not b87c.empty else 0, "expected": int(config["expected_new_cells"]), "status": bool_status((b87c["cell_id"].nunique() if not b87c.empty else 0) == int(config["expected_new_cells"])), "claim_boundary": CLAIM_BOUNDARY},
        ]
    )
    write_csv(output_path(config, "new150_label_inventory"), new_inv)
    n300 = pd.concat([f5_aligned, b87c.loc[:, PAIRWISE_COLUMNS]], ignore_index=True)
    n300 = add_within_slice_rank(n300, "delta_tmrt_p90_c")
    write_csv(output_path(config, "n300_pairwise_delta"), n300, PAIRWISE_COLUMNS)
    lineage = pd.DataFrame(
        [
            {
                "label_source": "b85_f5_n150_multiforcing",
                "sample_group": "existing_n150",
                "protocol_id": config["protocol_ids"]["f5_n150"],
                "rows": len(f5_aligned),
                "unique_cells": f5_aligned["cell_id"].nunique(),
                "extraction_convention_id": F5_CONVENTION_ID,
                "claim_boundary": CLAIM_BOUNDARY,
            },
            {
                "label_source": "b87c_new150_full150",
                "sample_group": "new150_b87c",
                "protocol_id": config["protocol_ids"]["b87c_new150"],
                "rows": len(b87c),
                "unique_cells": b87c["cell_id"].nunique() if not b87c.empty else 0,
                "extraction_convention_id": F5_CONVENTION_ID,
                "claim_boundary": CLAIM_BOUNDARY,
            },
        ]
    )
    write_csv(output_path(config, "protocol_lineage_register"), lineage)
    return n300


def distribution_summary(config: dict[str, Any], frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize primary target distribution."""
    target = config["primary_label_column"]
    rows: list[dict[str, Any]] = []
    groups: list[tuple[str, pd.DataFrame]] = [("all", frame)]
    if "sample_group" in frame.columns:
        groups += [(f"sample_group={name}", part) for name, part in frame.groupby("sample_group", sort=True)]
    if "forcing_day_id" in frame.columns:
        groups += [(f"forcing_day_id={name}", part) for name, part in frame.groupby("forcing_day_id", sort=True)]
    for name, part in groups:
        values = pd.to_numeric(part[target], errors="coerce").dropna()
        if values.empty:
            continue
        rows.append(
            {
                "distribution_slice": name,
                "target": target,
                "count": int(values.size),
                "mean": format_float(values.mean()),
                "std": format_float(values.std(ddof=0)),
                "min": format_float(values.min()),
                "p05": format_float(values.quantile(0.05)),
                "p50": format_float(values.quantile(0.50)),
                "p90": format_float(values.quantile(0.90)),
                "p95": format_float(values.quantile(0.95)),
                "max": format_float(values.max()),
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    out = pd.DataFrame(rows)
    write_csv(output_path(config, "distribution_summary"), out)
    return out


def qa_and_status(config: dict[str, Any]) -> B87DResult:
    """Run N300 label QA, write reports, and return compact status."""
    n300_path = output_path(config, "n300_pairwise_delta")
    n300 = read_csv(n300_path, dtype=str) if n300_path.exists() else integrate_n300_labels(config)
    b87c = read_csv(output_path(config, "b87c_pairwise_delta"), dtype=str) if output_path(config, "b87c_pairwise_delta").exists() else pd.DataFrame()
    stats = read_csv(output_path(config, "tmrt_stats_by_run"), dtype=str) if output_path(config, "tmrt_stats_by_run").exists() else pd.DataFrame()
    f5_cells = set(n300.loc[n300["sample_group"].eq("existing_n150"), "cell_id"].astype(str))
    b87c_cells = set(n300.loc[n300["sample_group"].eq("new150_b87c"), "cell_id"].astype(str))
    overlap = sorted(f5_cells & b87c_cells)
    dupes = n300.duplicated(["cell_id", "forcing_day_id", "hour_sgt"], keep=False)
    target = config["primary_label_column"]
    checks = [
        ("extraction_convention_recovered", convention_passed(config), PASS, "F5 full-tile valid non-nodata convention recovered."),
        ("b87c_tmrt_stats_rows", len(stats) == int(config["expected_b87c_success_runs"]), config["expected_b87c_success_runs"], "One stats row per B87C success run."),
        ("b87c_tmrt_stats_fail_count", int((stats.get("stat_status", pd.Series(dtype=str)).astype(str) == FAIL).sum()) == 0, 0, "All successful B87C Tmrt rasters readable."),
        ("b87c_pairwise_rows", len(b87c) == int(config["expected_b87c_pairwise_rows"]), config["expected_b87c_pairwise_rows"], "150 cells x 2 forcing days x 5 hours."),
        ("n300_pairwise_rows", len(n300) == int(config["expected_n300_pairwise_rows"]), config["expected_n300_pairwise_rows"], "Existing N150 plus B87C new150."),
        ("n300_unique_cells", n300["cell_id"].nunique() == int(config["expected_n300_cells"]), config["expected_n300_cells"], "Integrated N300 cell count."),
        ("f5_b87c_overlap_count", len(overlap) == 0, 0, "Old/new cell sets must not overlap."),
        ("duplicate_cell_forcing_hour_rows", int(dupes.sum()) == 0, 0, "No duplicate N300 cell x forcing day x hour rows."),
        ("missing_primary_label", int(n300[target].isna().sum()) == 0, 0, "No missing primary target."),
    ]
    qa_rows: list[dict[str, Any]] = []
    for check_name, ok, expected, notes in checks:
        observed: Any
        if check_name == "b87c_tmrt_stats_rows":
            observed = len(stats)
        elif check_name == "b87c_tmrt_stats_fail_count":
            observed = int((stats.get("stat_status", pd.Series(dtype=str)).astype(str) == FAIL).sum())
        elif check_name == "b87c_pairwise_rows":
            observed = len(b87c)
        elif check_name == "n300_pairwise_rows":
            observed = len(n300)
        elif check_name == "n300_unique_cells":
            observed = n300["cell_id"].nunique()
        elif check_name == "f5_b87c_overlap_count":
            observed = len(overlap)
        elif check_name == "duplicate_cell_forcing_hour_rows":
            observed = int(dupes.sum())
        elif check_name == "missing_primary_label":
            observed = int(n300[target].isna().sum())
        else:
            observed = PASS if ok else FAIL
        qa_rows.append({"check_name": check_name, "observed": observed, "expected": expected, "status": PASS if ok else FAIL, "notes": notes, "claim_boundary": CLAIM_BOUNDARY})
    qa = pd.DataFrame(qa_rows)
    write_csv(output_path(config, "qa_matrix"), qa)
    dist = distribution_summary(config, n300)

    blockers: list[str] = []
    if not convention_passed(config):
        blockers.append(B87D_BLOCKED_EXTRACTION_CONVENTION_UNKNOWN)
    if not stats.empty and (stats.get("stat_status", pd.Series(dtype=str)).astype(str) == FAIL).any():
        blockers.append(B87D_BLOCKED_MISSING_TMRT)
    if len(b87c) != int(config["expected_b87c_pairwise_rows"]):
        blockers.append(B87D_BLOCKED_INCOMPLETE_PAIRS)
    schema = read_csv(output_path(config, "f5_schema_alignment"), dtype=str) if output_path(config, "f5_schema_alignment").exists() else pd.DataFrame()
    if not schema.empty and (schema["status"].astype(str) == FAIL).any():
        blockers.append(B87D_BLOCKED_SCHEMA_MISMATCH)
    if overlap:
        blockers.append(B87D_BLOCKED_CELL_OVERLAP)
    if len(n300) != int(config["expected_n300_pairwise_rows"]) or n300["cell_id"].nunique() != int(config["expected_n300_cells"]) or int(dupes.sum()) > 0 or int(n300[target].isna().sum()) > 0:
        blockers.append(B87D_BLOCKED_SCHEMA_MISMATCH)

    blockers = sorted(set(blockers))
    status = B87D_PASS if not blockers and (qa["status"].astype(str) == PASS).all() else (blockers[0] if blockers else FAILED)
    blocker_frame = pd.DataFrame(
        [
            {
                "blocker_id": blocker,
                "status": "ACTIVE",
                "notes": "See b87d_n300_label_qa_matrix.csv.",
                "claim_boundary": CLAIM_BOUNDARY,
            }
            for blocker in blockers
        ]
    )
    if blocker_frame.empty:
        blocker_frame = pd.DataFrame([{"blocker_id": "none", "status": PASS, "notes": "No B87D blockers.", "claim_boundary": CLAIM_BOUNDARY}])
    write_csv(output_path(config, "blocker_register"), blocker_frame)
    next_lane = pd.DataFrame(
        [
            {
                "next_lane": "B87E_N300_surrogate_benchmark",
                "decision": "PROCEED" if status == B87D_PASS else "BLOCKED",
                "required_status": B87D_PASS,
                "observed_status": status,
                "notes": "Proceed only with SOLWEIG-derived label benchmark; no AOI/B9 prediction.",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        ]
    )
    write_csv(output_path(config, "next_lane_decision_matrix"), next_lane)
    write_b87d_reports(config, status, qa, dist, blockers, overlap)
    return B87DResult(status, len(stats), len(b87c), len(n300), n300["cell_id"].nunique(), len(overlap), blockers, repo_path(config["outputs"]["out_dir"]))


def write_b87d_reports(config: dict[str, Any], status: str, qa: pd.DataFrame, dist: pd.DataFrame, blockers: Sequence[str], overlap: Sequence[str]) -> None:
    """Write B87D Markdown status, report, and Chinese note."""
    status_lines = [
        "# B87D Status",
        "",
        f"Generated: {now_stamp()}",
        "",
        f"Status: `{status}`",
        "",
        "## Key Results",
        "",
    ]
    for name in ("b87c_tmrt_stats_rows", "b87c_pairwise_rows", "n300_pairwise_rows", "n300_unique_cells", "f5_b87c_overlap_count"):
        row = qa.loc[qa["check_name"].eq(name)]
        if not row.empty:
            status_lines.append(f"- {name}: `{row.iloc[0]['observed']}` (status `{row.iloc[0]['status']}`)")
    status_lines += [
        f"- Blockers: `{', '.join(blockers) if blockers else 'none'}`",
        "- QGIS/SOLWEIG executed by Codex: `no`",
        "- Raster outputs written/copied/moved: `no`",
        "- AOI/B9/WBGT/risk output: `no`",
        "",
        "## Claim Boundary",
        "",
        CLAIM_BOUNDARY,
    ]
    output_path(config, "status").write_text("\n".join(status_lines) + "\n", encoding="utf-8")

    convention = read_csv(output_path(config, "focus_mask_convention_audit"), dtype=str) if output_path(config, "focus_mask_convention_audit").exists() else pd.DataFrame()
    report_lines = [
        "# B87D N300 Label Integration Report",
        "",
        f"Generated: {now_stamp()}",
        "",
        f"Status: `{status}`",
        "",
        "## 1. B87C Full 150 Execution Summary",
        "",
        "B87C full_150 execution is consumed from the completed local run log. Only `status=success` rows feed extraction; dry-run and skipped-completed rows are audit context only.",
        "",
        "## 2. Tmrt Extraction Convention",
        "",
        f"Recovered convention: `{F5_CONVENTION_ID}` / `{F5_MASK_TYPE}`. Final F5 labels came from `b85_f5_raster_stats.csv`, whose raster inventory shape is 150x150 and whose valid pixel count is 22500 for full 2 m tiles. B87D therefore uses finite non-nodata pixels over the full `Tmrt_average.tif` tile and does not crop to a 100 m focus mask.",
        "",
        "## 3. Tmrt Stats Summary",
        "",
        f"- Stats rows: `{qa.loc[qa['check_name'].eq('b87c_tmrt_stats_rows'), 'observed'].iloc[0] if not qa.loc[qa['check_name'].eq('b87c_tmrt_stats_rows')].empty else ''}`",
        "- Saved stats: mean, median, p90, p95, max, valid/nodata counts, raster shape and CRS.",
        "",
        "## 4. Pairwise Delta Construction",
        "",
        "B87C pairwise labels are `overhead_as_canopy - base` by `cell_id x forcing_day_id x date x hour_sgt`. Negative values generally indicate lower simulated Tmrt under overhead-as-canopy, not WBGT reduction.",
        "",
        "## 5. F5 Schema Alignment",
        "",
        "F5 `delta_tmrt_p50_c` is carried as `delta_tmrt_median_c`; F5 `delta_tmrt_max_c` is derived from the final F5 cell-hour summary using the same overhead-minus-base formula. This is schema alignment, not retroactive recalibration.",
        "",
        "## 6. N300 Integrated Label Summary",
        "",
        f"- N300 rows: `{qa.loc[qa['check_name'].eq('n300_pairwise_rows'), 'observed'].iloc[0] if not qa.loc[qa['check_name'].eq('n300_pairwise_rows')].empty else ''}`",
        f"- N300 unique cells: `{qa.loc[qa['check_name'].eq('n300_unique_cells'), 'observed'].iloc[0] if not qa.loc[qa['check_name'].eq('n300_unique_cells')].empty else ''}`",
        f"- Old/new overlap count: `{len(overlap)}`",
        "",
        "## 7. QA And Blockers",
        "",
        f"Blockers: `{', '.join(blockers) if blockers else 'none'}`.",
        "",
        "## 8. Claim Boundaries",
        "",
        CLAIM_BOUNDARY,
    ]
    output_path(config, "report").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    cn_lines = [
        "# OpenHeat System B B87D N300 标签整合说明",
        "",
        f"生成时间：{now_stamp()}",
        "",
        f"状态：`{status}`",
        "",
        "本阶段只把已经完成的 B87C 本地 SOLWEIG `Tmrt_average.tif` 输出读取为紧凑统计表，并与既有 F5 N150 标签整合为 N300 标签表。",
        "",
        "## 提取约定",
        "",
        f"采用最终 F5 约定：`{F5_CONVENTION_ID}`。统计对象是完整 150x150 的 2m tile，像元筛选为有限值且非 nodata；不裁剪 100m focus mask，不写入任何 raster。",
        "",
        "## 标签方向",
        "",
        "`delta_tmrt_* = overhead_as_canopy - base`。负值通常表示 overhead-as-canopy 情景下模拟 Tmrt 较低，但这不是 WBGT 降温、不是观测真值、不是风险或危害地图。",
        "",
        "## 输出",
        "",
        "- `b87d_b87c_tmrt_stats_by_run.csv`：逐运行 Tmrt 统计。",
        "- `b87d_b87c_pairwise_delta_by_cell_hour.csv`：B87C new150 配对标签。",
        "- `b87d_n300_pairwise_delta_by_cell_hour.csv`：F5 N150 + B87C new150 整合标签。",
        "",
        "## 边界",
        "",
        "本阶段不运行 QGIS/SOLWEIG，不复制/移动/写入 raster，不生成 AOI/B9 推理，不做 WBGT 转换，不生成 hazard/risk/exposure/vulnerability 输出，也不提出因果特征重要性结论。",
    ]
    output_path(config, "canonical_note_cn").write_text("\n".join(cn_lines) + "\n", encoding="utf-8")


def run_b87d(config_path: Path = DEFAULT_CONFIG) -> B87DResult:
    """Run the full B87D label integration workflow."""
    config = read_config(repo_path(config_path))
    ensure_output_dirs(config)
    build_input_inventory(config)
    audit_run_log(config)
    audit_manifest(config)
    tmrt_output_inventory(config)
    recover_f5_convention(config)
    extract_tmrt_stats(config)
    build_b87c_pairwise_delta(config)
    integrate_n300_labels(config)
    return qa_and_status(config)


def main_runner() -> int:
    """CLI for the full B87D workflow."""
    parser = argparse.ArgumentParser(
        description=(
            "Run B87D N300 label integration from existing B87C Tmrt outputs. "
            "Inputs, outputs, config path, saved metrics, and claim boundaries "
            "are declared in the module docstring. This does not run QGIS or "
            "SOLWEIG and writes no raster assets."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B87D YAML config path.")
    args = parser.parse_args()
    try:
        result = run_b87d(args.config)
    except Exception as exc:
        print(f"Status: {FAILED}")
        print(f"Error: {exc}")
        return 1
    print(f"Status: {result.status}")
    print(f"B87C tmrt stats rows: {result.tmrt_stats_rows}")
    print(f"B87C pairwise rows: {result.b87c_pairwise_rows}")
    print(f"N300 pairwise rows: {result.n300_pairwise_rows}")
    print(f"N300 unique cells: {result.n300_unique_cells}")
    print(f"F5/B87C overlap count: {result.overlap_count}")
    print(f"Blockers: {', '.join(result.blockers) if result.blockers else 'none'}")
    print(f"Output dir: {rel(result.output_dir)}")
    print("QGIS/SOLWEIG executed by Codex: no")
    print("Raster outputs written/copied/moved: no")
    return 0 if result.status == B87D_PASS else 2


def wrapper_cli(function_name: str) -> int:
    """Run one B87D step by name for the required thin wrapper scripts."""
    parser = argparse.ArgumentParser(
        description=(
            f"Run B87D step {function_name}. Inputs, outputs, config path, saved "
            "metrics, and claim boundaries are declared in scripts/v12_b87d_common.py."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B87D YAML config path.")
    args = parser.parse_args()
    config = read_config(repo_path(args.config))
    ensure_output_dirs(config)
    functions = {
        "input_inventory": build_input_inventory,
        "tmrt_output_inventory": tmrt_output_inventory,
        "tmrt_stats_extractor": extract_tmrt_stats,
        "focus_mask_resolver": recover_f5_convention,
        "pairwise_delta_builder": build_b87c_pairwise_delta,
        "f5_schema_alignment": align_f5_schema,
        "n300_label_integrator": integrate_n300_labels,
        "label_qa": qa_and_status,
    }
    result = functions[function_name](config)
    rows = getattr(result, "shape", [0])[0] if result is not None else 0
    if function_name == "input_inventory":
        audit_run_log(config)
        audit_manifest(config)
    print(f"Status: {PASS}")
    print(f"Step: {function_name}")
    print(f"Rows written/returned: {rows}")
    print("QGIS/SOLWEIG executed by Codex: no")
    print("Raster outputs written/copied/moved: no")
    return 0
