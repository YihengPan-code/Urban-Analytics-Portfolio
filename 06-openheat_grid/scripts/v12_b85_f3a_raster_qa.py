"""Aggregate and sanity-check B8.5-F3a micro-batch Tmrt rasters.

Inputs:
    configs/v12/systemb_b85_f3a_raster_qa.yaml
    outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_microbatch_manifest.csv
    outputs/v12_surrogate/b8_5_f3a_microbatch/b85_f3a_postrun_validation.csv
    Four local Tmrt_average.tif rasters declared by the manifest.

Outputs:
    outputs/v12_surrogate/b8_5_f3a_raster_qa/b85_f3a_raster_inventory.csv
    outputs/v12_surrogate/b8_5_f3a_raster_qa/b85_f3a_raster_stats.csv
    outputs/v12_surrogate/b8_5_f3a_raster_qa/b85_f3a_pairwise_delta_summary.csv
    outputs/v12_surrogate/b8_5_f3a_raster_qa/b85_f3a_forcing_day_contrast_summary.csv
    outputs/v12_surrogate/b8_5_f3a_raster_qa/b85_f3a_alignment_qa.csv
    outputs/v12_surrogate/b8_5_f3a_raster_qa/b85_f3a_sanity_checks.csv
    outputs/v12_surrogate/b8_5_f3a_raster_qa/b85_f3a_raster_qa_report.md
    outputs/v12_surrogate/b8_5_f3a_raster_qa/B8_5_F3A_QA_STATUS.md
    docs/v12/OpenHeat_SystemB_B8_5_F3a_raster_QA_CN.md

Saved metrics:
    Raster inventory, per-raster valid/nodata counts and Tmrt percentiles,
    threshold exceedance percentages, base-vs-overhead_as_canopy pixel deltas,
    FD02-vs-FD01 forcing-day contrasts, alignment checks, sanity checks,
    final micro-batch raster QA decision status, and next recommended action.

This script reads raster content for compact QA only. It does not run QGIS,
run SOLWEIG, copy/open svfs.zip, create/copy/move rasters, write raster/image
outputs, create AOI-wide predictions, compute local WBGT, create hazard_score
or risk_score outputs, create System A/B coupling outputs, stage, or commit.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_f3a_raster_qa.yaml"

YES = "yes"
NO = "no"
PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
MICRO_BATCH_RASTER_QA_PASS = "MICRO_BATCH_RASTER_QA_PASS"
MICRO_BATCH_RASTER_QA_PARTIAL = "MICRO_BATCH_RASTER_QA_PARTIAL"
MICRO_BATCH_RASTER_QA_BLOCKED = "MICRO_BATCH_RASTER_QA_BLOCKED"
FAILED = "FAILED"


@dataclass(frozen=True)
class RasterPayload:
    """Raster metadata, array content, and valid-pixel mask for one run."""

    run: dict[str, str]
    metadata: dict[str, Any]
    array: np.ndarray | None
    valid_mask: np.ndarray | None
    opened: bool
    backend: str
    error: str


@dataclass(frozen=True)
class RasterQaResult:
    """Compact return object for the runner."""

    decision_status: str
    raster_count_opened: int
    alignment_status: str
    per_run_p90_range: str
    pairwise_delta_headline: str
    forcing_day_contrast_headline: str
    next_recommended_action: str
    files_created: list[Path]


def now_stamp() -> str:
    """Return a local timestamp for reports."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clean(value: Any) -> str:
    """Return a compact single-line string."""
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def path_text(path: Path | str) -> str:
    """Return a stable slash-separated path string."""
    return Path(path).as_posix()


def repo_path(path: Path | str) -> Path:
    """Resolve repo-relative paths against the OpenHeat project subdirectory."""
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def parse_scalar(value: str) -> Any:
    """Parse the small YAML scalar subset used by project configs."""
    stripped = value.strip()
    if stripped == "[]":
        return []
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
    """Read the simple nested YAML shape used by OpenHeat configs."""
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
            item_text = text[2:].strip()
            if ":" in item_text:
                key, _, raw_value = item_text.partition(":")
                item: dict[str, Any] = {key.strip(): parse_scalar(raw_value.strip())}
                parent.append(item)
                stack.append((indent, item))
            else:
                parent.append(parse_scalar(item_text))
            continue

        key, _, raw_value = text.partition(":")
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value:
            if not isinstance(parent, dict):
                raise ValueError(f"Unsupported YAML mapping placement: {line}")
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
            raise ValueError(f"Unsupported YAML parent for key: {line}")
        parent[key] = next_container
        stack.append((indent, next_container))
    return root


def read_config(path: Path) -> dict[str, Any]:
    """Load the explicit raster QA YAML config."""
    return read_simple_yaml(path)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV as dictionaries."""
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def write_csv_rows(path: Path, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str]) -> None:
    """Write dictionaries as UTF-8 CSV with stable field order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def format_float(value: Any, digits: int = 6) -> str:
    """Format a finite float for compact CSV/Markdown output."""
    try:
        x = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(x):
        return ""
    return f"{x:.{digits}f}"


def percent(values: np.ndarray, mask: np.ndarray) -> str:
    """Return percentage of true values over a valid-pixel denominator."""
    if values.size == 0:
        return ""
    return format_float(float(np.count_nonzero(mask)) * 100.0 / float(values.size))


def markdown_table(rows: Sequence[dict[str, Any]], columns: Sequence[str], max_rows: int | None = None) -> str:
    """Render a small Markdown table without external dependencies."""
    selected = list(rows[:max_rows]) if max_rows is not None else list(rows)
    if not selected:
        return "_No rows._"
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in selected:
        vals = [clean(row.get(col, "")).replace("|", "/") for col in columns]
        body.append("| " + " | ".join(vals) + " |")
    return "\n".join([header, sep, *body])


def ensure_scope_flags(config: dict[str, Any]) -> None:
    """Guard against accidental expansion beyond read-only raster QA."""
    required = {
        "qa_read_raster_content": True,
        "write_raster_outputs": False,
        "execute_qgis_or_solweig": False,
        "commit_safe_outputs_only": True,
    }
    bad = [f"{key}={config.get(key)!r}" for key, expected in required.items() if config.get(key) != expected]
    if bad:
        raise ValueError("Unsafe raster QA config flags: " + "; ".join(bad))


def is_relative_to(path: Path, parent: Path) -> bool:
    """Return whether path is below parent after non-strict resolution."""
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def git_root() -> Path:
    """Return the git worktree root for the current OpenHeat checkout."""
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    text = completed.stdout.strip()
    return Path(text) if text else ROOT


def git_status_short() -> list[str]:
    """Return short Git status lines under the current OpenHeat subdirectory."""
    completed = subprocess.run(
        ["git", "status", "--short", "--", "."],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return [line.rstrip() for line in completed.stdout.splitlines() if line.strip()]


def changed_forbidden_paths(status_lines: Iterable[str]) -> list[str]:
    """Identify forbidden changed files from Git status output."""
    forbidden_fragments = [
        "data/solweig/",
        "data/rasters/",
        "data/archive/",
        "svfs.zip",
        "hourly_grid_heatstress_forecast",
    ]
    forbidden_suffixes = (".tif", ".tiff", ".zip")
    hits: list[str] = []
    for line in status_lines:
        path = line[3:].replace("\\", "/")
        lower = path.lower()
        if lower.endswith(forbidden_suffixes) or any(fragment in lower for fragment in forbidden_fragments):
            hits.append(path)
    return hits


def parent_hour(path: Path) -> int | None:
    """Parse an h13-style parent folder hour when present."""
    match = re.search(r"^h(\d{1,2})$", path.parent.name)
    return int(match.group(1)) if match else None


def crs_from_wkt(wkt: str) -> str:
    """Return an EPSG label or compact CRS name from GDAL WKT."""
    if not wkt:
        return ""
    try:
        from osgeo import osr

        srs = osr.SpatialReference()
        srs.ImportFromWkt(wkt)
        srs.AutoIdentifyEPSG()
        auth_name = srs.GetAuthorityName(None) or srs.GetAuthorityName("PROJCS")
        auth_code = srs.GetAuthorityCode(None) or srs.GetAuthorityCode("PROJCS")
        if auth_name and auth_code:
            return f"{auth_name}:{auth_code}"
        return clean(srs.GetName())
    except Exception:
        return clean(wkt)[:120]


def read_with_rasterio(path: Path) -> tuple[dict[str, Any], np.ndarray, str]:
    """Read one raster with rasterio when available."""
    import rasterio

    with rasterio.open(path) as src:
        array = src.read(1)
        transform = tuple(float(v) for v in src.transform.to_gdal())
        metadata = {
            "crs": src.crs.to_string() if src.crs else "",
            "width": int(src.width),
            "height": int(src.height),
            "pixel_count": int(src.width * src.height),
            "transform": str(transform),
            "nodata": src.nodata,
            "dtype": str(src.dtypes[0]) if src.dtypes else "",
            "band_count": int(src.count),
        }
    return metadata, np.asarray(array), "rasterio"


def read_with_gdal(path: Path) -> tuple[dict[str, Any], np.ndarray, str]:
    """Read one raster with GDAL Python bindings when rasterio is unavailable."""
    from osgeo import gdal

    dataset = gdal.Open(path.as_posix(), gdal.GA_ReadOnly)
    if dataset is None:
        raise RuntimeError(f"GDAL could not open raster: {path_text(path)}")
    try:
        band = dataset.GetRasterBand(1)
        if band is None:
            raise RuntimeError(f"Raster has no band 1: {path_text(path)}")
        array = band.ReadAsArray()
        if array is None:
            raise RuntimeError(f"GDAL returned no array for band 1: {path_text(path)}")
        transform = tuple(float(v) for v in dataset.GetGeoTransform())
        metadata = {
            "crs": crs_from_wkt(dataset.GetProjectionRef()),
            "width": int(dataset.RasterXSize),
            "height": int(dataset.RasterYSize),
            "pixel_count": int(dataset.RasterXSize * dataset.RasterYSize),
            "transform": str(transform),
            "nodata": band.GetNoDataValue(),
            "dtype": str(gdal.GetDataTypeName(band.DataType)),
            "band_count": int(dataset.RasterCount),
        }
    finally:
        dataset = None
    return metadata, np.asarray(array), "gdal"


def read_raster_payload(run: dict[str, str]) -> RasterPayload:
    """Read one manifest-declared raster, returning metadata and pixel content."""
    raster_path = Path(run["expected_tmrt_path"])
    exists = raster_path.exists()
    metadata: dict[str, Any] = {
        "exists": YES if exists else NO,
        "file_size_bytes": str(raster_path.stat().st_size) if exists else "0",
        "parent_folder_hour_sgt": parent_hour(raster_path),
    }
    if not exists:
        return RasterPayload(run, metadata, None, None, False, "", "raster_missing")

    errors: list[str] = []
    for reader in (read_with_rasterio, read_with_gdal):
        try:
            raster_metadata, array, backend = reader(raster_path)
            metadata.update(raster_metadata)
            valid_mask = valid_pixel_mask(array, metadata.get("nodata"))
            return RasterPayload(run, metadata, array, valid_mask, True, backend, "")
        except ModuleNotFoundError as exc:
            errors.append(f"{reader.__name__}: missing {exc.name}")
        except Exception as exc:
            errors.append(f"{reader.__name__}: {exc}")
    return RasterPayload(run, metadata, None, None, False, "", "; ".join(errors))


def valid_pixel_mask(array: np.ndarray, nodata: Any) -> np.ndarray:
    """Return the finite non-nodata pixel mask for a raster array."""
    values = array.astype("float64", copy=False)
    mask = np.isfinite(values)
    if nodata is not None and clean(nodata) != "":
        try:
            nodata_float = float(nodata)
            if math.isfinite(nodata_float):
                mask &= values != nodata_float
        except (TypeError, ValueError):
            pass
    return mask


def valid_values(payload: RasterPayload) -> np.ndarray:
    """Return valid float values for a raster payload."""
    if payload.array is None or payload.valid_mask is None:
        return np.asarray([], dtype="float64")
    return payload.array.astype("float64", copy=False)[payload.valid_mask]


def percentile(values: np.ndarray, q: float) -> float:
    """Return a percentile as float."""
    return float(np.percentile(values, q))


def inventory_row(payload: RasterPayload) -> dict[str, Any]:
    """Build the raster inventory row for one payload."""
    run = payload.run
    metadata = payload.metadata
    return {
        "run_id": run.get("run_id", ""),
        "cell_id": run.get("cell_id", ""),
        "forcing_day_id": run.get("forcing_day_id", ""),
        "date": run.get("date", ""),
        "hour_sgt": run.get("hour_sgt", ""),
        "scenario": run.get("scenario", ""),
        "raster_path": run.get("expected_tmrt_path", ""),
        "exists": metadata.get("exists", NO),
        "file_size_bytes": metadata.get("file_size_bytes", "0"),
        "crs": metadata.get("crs", ""),
        "width": metadata.get("width", ""),
        "height": metadata.get("height", ""),
        "pixel_count": metadata.get("pixel_count", ""),
        "transform": metadata.get("transform", ""),
        "nodata": metadata.get("nodata", ""),
        "dtype": metadata.get("dtype", ""),
        "band_count": metadata.get("band_count", ""),
        "opened_for_qa": YES if payload.opened else NO,
        "copied_or_written": NO,
        "raster_backend": payload.backend,
        "open_error": payload.error,
    }


def raster_stats_row(
    payload: RasterPayload,
    thresholds: Sequence[float],
    plausible_min: float,
    plausible_max: float,
) -> dict[str, Any]:
    """Build the per-raster content stats row."""
    run = payload.run
    base = {
        "run_id": run.get("run_id", ""),
        "cell_id": run.get("cell_id", ""),
        "forcing_day_id": run.get("forcing_day_id", ""),
        "date": run.get("date", ""),
        "hour_sgt": run.get("hour_sgt", ""),
        "scenario": run.get("scenario", ""),
        "raster_path": run.get("expected_tmrt_path", ""),
    }
    for threshold in thresholds:
        base[f"pct_pixels_ge_{int(threshold)}"] = ""
    if not payload.opened:
        base.update(
            {
                "valid_pixel_count": "0",
                "nodata_pixel_count": "",
                "nodata_fraction": "",
                "min_c": "",
                "p01_c": "",
                "p05_c": "",
                "p25_c": "",
                "mean_c": "",
                "p50_c": "",
                "p75_c": "",
                "p90_c": "",
                "p95_c": "",
                "p99_c": "",
                "max_c": "",
                "std_c": "",
                "sanity_status": BLOCKED,
                "sanity_notes": payload.error,
            }
        )
        return base

    values = valid_values(payload)
    pixel_count = int(payload.metadata.get("pixel_count", 0) or 0)
    valid_count = int(values.size)
    nodata_count = max(pixel_count - valid_count, 0)
    if valid_count == 0:
        base.update(
            {
                "valid_pixel_count": "0",
                "nodata_pixel_count": str(nodata_count),
                "nodata_fraction": format_float(1.0 if pixel_count else math.nan),
                "min_c": "",
                "p01_c": "",
                "p05_c": "",
                "p25_c": "",
                "mean_c": "",
                "p50_c": "",
                "p75_c": "",
                "p90_c": "",
                "p95_c": "",
                "p99_c": "",
                "max_c": "",
                "std_c": "",
                "sanity_status": BLOCKED,
                "sanity_notes": "no_valid_pixels",
            }
        )
        return base

    min_c = float(np.min(values))
    max_c = float(np.max(values))
    p50 = percentile(values, 50)
    p90 = percentile(values, 90)
    p95 = percentile(values, 95)
    notes: list[str] = []
    nodata_fraction = float(nodata_count) / float(pixel_count) if pixel_count else math.nan
    if nodata_fraction >= 0.5:
        notes.append("nodata_fraction_ge_0_5")
    if min_c < plausible_min or max_c > plausible_max:
        notes.append(f"outside_plausible_range_{plausible_min:g}_{plausible_max:g}_c")
    if p90 < p50:
        notes.append("p90_lt_p50")
    if p95 < p90:
        notes.append("p95_lt_p90")
    if int(payload.metadata.get("band_count", 0) or 0) != 1:
        notes.append("band_count_not_1")

    base.update(
        {
            "valid_pixel_count": str(valid_count),
            "nodata_pixel_count": str(nodata_count),
            "nodata_fraction": format_float(nodata_fraction),
            "min_c": format_float(min_c),
            "p01_c": format_float(percentile(values, 1)),
            "p05_c": format_float(percentile(values, 5)),
            "p25_c": format_float(percentile(values, 25)),
            "mean_c": format_float(float(np.mean(values))),
            "p50_c": format_float(p50),
            "p75_c": format_float(percentile(values, 75)),
            "p90_c": format_float(p90),
            "p95_c": format_float(p95),
            "p99_c": format_float(percentile(values, 99)),
            "max_c": format_float(max_c),
            "std_c": format_float(float(np.std(values))),
            "sanity_status": PASS if not notes else WARN,
            "sanity_notes": "none" if not notes else "; ".join(notes),
        }
    )
    for threshold in thresholds:
        base[f"pct_pixels_ge_{int(threshold)}"] = percent(values, values >= threshold)
    return base


def payload_by_key(payloads: Sequence[RasterPayload]) -> dict[tuple[str, str], RasterPayload]:
    """Index raster payloads by forcing day and scenario."""
    return {(p.run.get("forcing_day_id", ""), p.run.get("scenario", "")): p for p in payloads}


def overlap_delta(a: RasterPayload, b: RasterPayload) -> np.ndarray:
    """Return b - a over valid overlapping pixels."""
    if not a.opened or not b.opened or a.array is None or b.array is None:
        return np.asarray([], dtype="float64")
    if a.valid_mask is None or b.valid_mask is None or a.array.shape != b.array.shape:
        return np.asarray([], dtype="float64")
    mask = a.valid_mask & b.valid_mask
    if not np.any(mask):
        return np.asarray([], dtype="float64")
    return b.array.astype("float64", copy=False)[mask] - a.array.astype("float64", copy=False)[mask]


def delta_stats(values: np.ndarray) -> dict[str, str]:
    """Return compact distribution stats for a delta vector."""
    if values.size == 0:
        return {
            "mean_delta_c": "",
            "p50_delta_c": "",
            "p90_delta_c": "",
            "p95_delta_c": "",
            "max_delta_c": "",
            "min_delta_c": "",
        }
    return {
        "mean_delta_c": format_float(float(np.mean(values))),
        "p50_delta_c": format_float(percentile(values, 50)),
        "p90_delta_c": format_float(percentile(values, 90)),
        "p95_delta_c": format_float(percentile(values, 95)),
        "max_delta_c": format_float(float(np.max(values))),
        "min_delta_c": format_float(float(np.min(values))),
    }


def classify_overhead_delta(values: np.ndarray) -> str:
    """Classify overhead_as_canopy - base Tmrt sensitivity direction."""
    if values.size == 0:
        return "overhead_warming_or_suspicious"
    mean_delta = float(np.mean(values))
    p50_delta = percentile(values, 50)
    pct_gt_1 = float(np.count_nonzero(values > 1.0)) * 100.0 / float(values.size)
    pct_lt_minus_1 = float(np.count_nonzero(values < -1.0)) * 100.0 / float(values.size)
    if mean_delta > 1.0 or p50_delta > 1.0 or pct_gt_1 > 25.0:
        return "overhead_warming_or_suspicious"
    if mean_delta <= -1.0 or p50_delta <= -1.0 or pct_lt_minus_1 >= 10.0:
        return "overhead_cooling"
    return "overhead_neutral"


def pairwise_delta_rows(payloads: Sequence[RasterPayload]) -> list[dict[str, Any]]:
    """Compare overhead_as_canopy - base for each forcing day."""
    by_key = payload_by_key(payloads)
    forcing_ids = sorted({p.run.get("forcing_day_id", "") for p in payloads})
    rows: list[dict[str, Any]] = []
    for forcing_day_id in forcing_ids:
        base = by_key.get((forcing_day_id, "base"))
        overhead = by_key.get((forcing_day_id, "overhead_as_canopy"))
        row = {"forcing_day_id": forcing_day_id}
        if base is None or overhead is None:
            row.update(
                {
                    "mean_delta_c": "",
                    "p50_delta_c": "",
                    "p90_delta_c": "",
                    "p95_delta_c": "",
                    "max_delta_c": "",
                    "min_delta_c": "",
                    "pct_pixels_delta_lt_minus_1": "",
                    "pct_pixels_delta_lt_minus_5": "",
                    "pct_pixels_delta_gt_1": "",
                    "valid_overlap_pixels": "0",
                    "delta_direction_status": "overhead_warming_or_suspicious",
                    "notes": "missing_base_or_overhead_payload",
                }
            )
            rows.append(row)
            continue
        values = overlap_delta(base, overhead)
        row.update(delta_stats(values))
        row.update(
            {
                "pct_pixels_delta_lt_minus_1": percent(values, values < -1.0),
                "pct_pixels_delta_lt_minus_5": percent(values, values < -5.0),
                "pct_pixels_delta_gt_1": percent(values, values > 1.0),
                "valid_overlap_pixels": str(int(values.size)),
                "delta_direction_status": classify_overhead_delta(values),
                "notes": "overhead_as_canopy_minus_base; sensitivity_delta_not_exact_overhead_physics",
            }
        )
        rows.append(row)
    return rows


def find_forcing_id(payloads: Sequence[RasterPayload], prefix: str) -> str:
    """Return the first forcing day id matching an FD prefix."""
    matches = sorted({p.run.get("forcing_day_id", "") for p in payloads if p.run.get("forcing_day_id", "").startswith(prefix)})
    return matches[0] if matches else ""


def classify_forcing_contrast(values: np.ndarray) -> str:
    """Classify FD02 - FD01 contrast magnitude."""
    if values.size == 0:
        return "suspicious_large_difference"
    mean_delta = float(np.mean(values))
    p90_delta = percentile(values, 90)
    min_delta = float(np.min(values))
    max_delta = float(np.max(values))
    if abs(mean_delta) < 1.0 and abs(p90_delta) < 1.0:
        return "neutral"
    if abs(mean_delta) > 25.0 or abs(p90_delta) > 30.0 or min_delta < -50.0 or max_delta > 50.0:
        return "suspicious_large_difference"
    return "plausible_forcing_difference"


def forcing_day_contrast_rows(payloads: Sequence[RasterPayload]) -> list[dict[str, Any]]:
    """Compare FD02 - FD01 for base and overhead_as_canopy scenarios."""
    by_key = payload_by_key(payloads)
    fd01 = find_forcing_id(payloads, "FD01")
    fd02 = find_forcing_id(payloads, "FD02")
    rows: list[dict[str, Any]] = []
    for scenario in ("base", "overhead_as_canopy"):
        first = by_key.get((fd01, scenario))
        second = by_key.get((fd02, scenario))
        row = {
            "scenario": scenario,
            "fd01_forcing_day_id": fd01,
            "fd02_forcing_day_id": fd02,
            "contrast_direction": "FD02_minus_FD01",
        }
        if first is None or second is None:
            row.update(
                {
                    "mean_delta_c": "",
                    "p50_delta_c": "",
                    "p90_delta_c": "",
                    "p95_delta_c": "",
                    "max_delta_c": "",
                    "min_delta_c": "",
                    "mean_difference_c": "",
                    "p90_difference_c": "",
                    "valid_overlap_pixels": "0",
                    "qualitative_status": "suspicious_large_difference",
                    "notes": "missing_fd01_or_fd02_payload",
                }
            )
            rows.append(row)
            continue
        values = overlap_delta(first, second)
        stats = delta_stats(values)
        row.update(stats)
        row.update(
            {
                "mean_difference_c": stats["mean_delta_c"],
                "p90_difference_c": stats["p90_delta_c"],
                "valid_overlap_pixels": str(int(values.size)),
                "qualitative_status": classify_forcing_contrast(values),
                "notes": "same_scenario_fd02_minus_fd01_tmrt_difference",
            }
        )
        rows.append(row)
    return rows


def add_check(rows: list[dict[str, Any]], check_name: str, status: str, value: Any, details: str) -> None:
    """Append one QA check row."""
    rows.append(
        {
            "check_name": check_name,
            "status": status,
            "value": clean(value),
            "details": details,
        }
    )


def alignment_rows(payloads: Sequence[RasterPayload], config: dict[str, Any], worktree_root: Path) -> list[dict[str, Any]]:
    """Build alignment QA rows across the four rasters."""
    opened = [p for p in payloads if p.opened]
    shapes = {f"{p.metadata.get('height')}x{p.metadata.get('width')}" for p in opened}
    crs_values = {clean(p.metadata.get("crs")) for p in opened}
    transforms = {clean(p.metadata.get("transform")) for p in opened}
    nodata_dtype = {f"{clean(p.metadata.get('nodata'))}|{clean(p.metadata.get('dtype'))}" for p in opened}
    pixel_counts = {clean(p.metadata.get("pixel_count")) for p in opened}
    local_root = Path(str(config["local_output_root"]))
    raster_paths = [Path(p.run.get("expected_tmrt_path", "")) for p in payloads]
    rows: list[dict[str, Any]] = []
    add_check(rows, "all_4_rasters_have_same_shape", PASS if len(opened) == 4 and len(shapes) == 1 else FAIL, ";".join(sorted(shapes)), "Shape comparison uses height x width.")
    add_check(rows, "all_4_rasters_have_same_crs", PASS if len(opened) == 4 and len(crs_values) == 1 else FAIL, ";".join(sorted(crs_values)), "CRS must match before pixelwise deltas.")
    add_check(rows, "all_4_rasters_have_same_transform", PASS if len(opened) == 4 and len(transforms) == 1 else FAIL, ";".join(sorted(transforms)), "Transform must match before pixelwise deltas.")
    add_check(rows, "all_4_rasters_have_same_nodata_dtype", PASS if len(opened) == 4 and len(nodata_dtype) == 1 else WARN, ";".join(sorted(nodata_dtype)), "Nodata and dtype should be consistent across the micro-batch.")
    add_check(rows, "expected_pixel_count_consistency", PASS if len(opened) == 4 and len(pixel_counts) == 1 else FAIL, ";".join(sorted(pixel_counts)), "Pixel count should be identical for the four local rasters.")
    outside_git = all(not is_relative_to(path, worktree_root) for path in raster_paths)
    under_local_root = all(is_relative_to(path, local_root) for path in raster_paths)
    add_check(rows, "output_path_outside_git_worktree", PASS if outside_git and under_local_root else FAIL, path_text(local_root), "Local SOLWEIG raster paths should remain outside the Git worktree and under local_output_root.")
    add_check(rows, "no_raster_output_written", PASS if config.get("write_raster_outputs") is False else FAIL, config.get("write_raster_outputs"), "QA writes only CSV/Markdown control artifacts.")
    return rows


def sanity_rows(
    payloads: Sequence[RasterPayload],
    stats_rows: Sequence[dict[str, Any]],
    pairwise_rows: Sequence[dict[str, Any]],
    config: dict[str, Any],
    status_lines: Sequence[str],
) -> list[dict[str, Any]]:
    """Build detailed sanity checks for raster content QA."""
    rows: list[dict[str, Any]] = []
    expected_count = int(config["expected_run_count"])
    plausible_min = float(config["plausible_tmrt_min_c"])
    plausible_max = float(config["plausible_tmrt_max_c"])
    opened_count = sum(1 for p in payloads if p.opened)
    add_check(rows, "all_rasters_opened_successfully", PASS if opened_count == expected_count else FAIL, f"{opened_count}/{expected_count}", "All expected Tmrt_average.tif files must open for content QA.")
    add_check(rows, "expected_run_count", PASS if len(payloads) == expected_count else FAIL, f"{len(payloads)}/{expected_count}", "Manifest row count must match expected_run_count.")
    postrun_ready = all(clean(p.run.get("postrun_validation_status")) == PASS for p in payloads)
    add_check(rows, "postrun_validation_passed", PASS if postrun_ready else WARN, str(postrun_ready).lower(), "F3a POST should already show 4/4 output validation.")
    for payload, stats in zip(payloads, stats_rows):
        run_id = payload.run.get("run_id", "")
        valid_count = int(stats.get("valid_pixel_count") or 0)
        nodata_fraction = float(stats.get("nodata_fraction") or 1.0)
        min_c = float(stats.get("min_c") or math.nan)
        max_c = float(stats.get("max_c") or math.nan)
        p50 = float(stats.get("p50_c") or math.nan)
        p90 = float(stats.get("p90_c") or math.nan)
        p95 = float(stats.get("p95_c") or math.nan)
        add_check(rows, f"{run_id}:valid_pixel_count_gt_0", PASS if valid_count > 0 else FAIL, valid_count, "Raster must contain at least one valid Tmrt pixel.")
        add_check(rows, f"{run_id}:nodata_fraction_lt_0_5", PASS if nodata_fraction < 0.5 else WARN, format_float(nodata_fraction), "Nodata fraction should remain below 0.5.")
        plausible = math.isfinite(min_c) and math.isfinite(max_c) and min_c >= plausible_min and max_c <= plausible_max
        add_check(rows, f"{run_id}:min_max_plausible", PASS if plausible else WARN, f"{format_float(min_c)}..{format_float(max_c)}", f"Configured plausible range is {plausible_min:g}-{plausible_max:g} C.")
        add_check(rows, f"{run_id}:p90_ge_p50", PASS if p90 >= p50 else WARN, f"p50={format_float(p50)}, p90={format_float(p90)}", "Percentile ordering sanity check.")
        add_check(rows, f"{run_id}:p95_ge_p90", PASS if p95 >= p90 else WARN, f"p90={format_float(p90)}, p95={format_float(p95)}", "Percentile ordering sanity check.")
        expected_hour = int(config["expected_hour_sgt"])
        add_check(rows, f"{run_id}:parent_folder_hour_matches_expected", PASS if payload.metadata.get("parent_folder_hour_sgt") == expected_hour else WARN, payload.metadata.get("parent_folder_hour_sgt"), "Uses parent-folder hour parsing because Tmrt_average.tif does not encode hour.")

    for row in pairwise_rows:
        forcing_day = row.get("forcing_day_id", "")
        overlap = int(row.get("valid_overlap_pixels") or 0)
        add_check(rows, f"{forcing_day}:overhead_delta_not_nan", PASS if overlap > 0 else FAIL, overlap, "overhead_as_canopy - base delta must have valid overlap pixels.")

    by_key = payload_by_key(payloads)
    forcing_ids = sorted({p.run.get("forcing_day_id", "") for p in payloads})
    for forcing_day_id in forcing_ids:
        base = by_key.get((forcing_day_id, "base"))
        overhead = by_key.get((forcing_day_id, "overhead_as_canopy"))
        distinct = bool(base and overhead and base.run.get("expected_tmrt_path") != overhead.run.get("expected_tmrt_path"))
        add_check(rows, f"{forcing_day_id}:base_and_overhead_paths_distinct", PASS if distinct else FAIL, str(distinct).lower(), "Base and overhead_as_canopy raster paths must not alias.")

    fd01 = find_forcing_id(payloads, "FD01")
    fd02 = find_forcing_id(payloads, "FD02")
    for scenario in ("base", "overhead_as_canopy"):
        first = by_key.get((fd01, scenario))
        second = by_key.get((fd02, scenario))
        distinct = bool(first and second and first.run.get("expected_tmrt_path") != second.run.get("expected_tmrt_path"))
        add_check(rows, f"{scenario}:fd01_and_fd02_paths_distinct", PASS if distinct else FAIL, str(distinct).lower(), "FD01 and FD02 raster paths must not alias within scenario.")

    forbidden = changed_forbidden_paths(status_lines)
    add_check(rows, "no_forbidden_repo_files_changed", PASS if not forbidden else FAIL, ";".join(forbidden), "Forbidden rasters, svfs.zip, raw archives, and large forecast CSVs must remain untouched.")
    add_check(rows, "no_qgis_or_solweig_execution", PASS if config.get("execute_qgis_or_solweig") is False else FAIL, config.get("execute_qgis_or_solweig"), "This lane is read-only raster content QA.")
    add_check(rows, "no_raster_image_or_array_output_written", PASS if config.get("write_raster_outputs") is False else FAIL, config.get("write_raster_outputs"), "No GeoTIFF, PNG, image, or large array output is written.")
    return rows


def merge_postrun_status(manifest_rows: list[dict[str, str]], postrun_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Attach postrun validation status to each manifest row."""
    postrun_by_id = {row.get("run_id", ""): row for row in postrun_rows}
    merged: list[dict[str, str]] = []
    for row in manifest_rows:
        out = dict(row)
        post = postrun_by_id.get(row.get("run_id", ""), {})
        out["postrun_validation_status"] = clean(post.get("validation_status"))
        out["postrun_file_exists"] = clean(post.get("file_exists"))
        out["postrun_file_size_bytes"] = clean(post.get("file_size_bytes"))
        merged.append(out)
    return merged


def validate_manifest_scope(config: dict[str, Any], rows: Sequence[dict[str, str]]) -> list[str]:
    """Return manifest scope warnings/errors for the expected 4-run micro-batch."""
    notes: list[str] = []
    expected_count = int(config["expected_run_count"])
    expected_cell = str(config["expected_cell_id"])
    expected_hour = int(config["expected_hour_sgt"])
    if len(rows) != expected_count:
        notes.append(f"manifest_row_count_{len(rows)}_ne_expected_{expected_count}")
    cells = sorted({row.get("cell_id", "") for row in rows})
    if cells != [expected_cell]:
        notes.append("unexpected_cell_ids=" + ";".join(cells))
    hours = sorted({clean(row.get("hour_sgt")) for row in rows})
    if hours != [str(expected_hour)]:
        notes.append("unexpected_hours=" + ";".join(hours))
    scenarios = sorted({row.get("scenario", "") for row in rows})
    if scenarios != ["base", "overhead_as_canopy"]:
        notes.append("unexpected_scenarios=" + ";".join(scenarios))
    return notes


def alignment_status_from_rows(rows: Sequence[dict[str, Any]]) -> str:
    """Return PASS when all alignment checks pass, else PARTIAL."""
    return PASS if all(row.get("status") == PASS for row in rows) else WARN


def p90_range(stats_rows: Sequence[dict[str, Any]]) -> str:
    """Return min-max p90 range across per-run stats."""
    vals = [float(row["p90_c"]) for row in stats_rows if clean(row.get("p90_c"))]
    if not vals:
        return "not_available"
    return f"{min(vals):.2f}-{max(vals):.2f} C"


def pairwise_headline(rows: Sequence[dict[str, Any]]) -> str:
    """Return compact base-vs-overhead delta headline."""
    parts = []
    for row in rows:
        fd = str(row.get("forcing_day_id", "")).split("_")[0]
        parts.append(f"{fd} mean {row.get('mean_delta_c', '')} C ({row.get('delta_direction_status', '')})")
    return "; ".join(parts) if parts else "not_available"


def forcing_contrast_headline(rows: Sequence[dict[str, Any]]) -> str:
    """Return compact FD02-vs-FD01 contrast headline."""
    parts = []
    for row in rows:
        parts.append(f"{row.get('scenario', '')} mean {row.get('mean_difference_c', '')} C, p90 {row.get('p90_difference_c', '')} C ({row.get('qualitative_status', '')})")
    return "; ".join(parts) if parts else "not_available"


def decide_status(
    payloads: Sequence[RasterPayload],
    stats_rows: Sequence[dict[str, Any]],
    alignment: Sequence[dict[str, Any]],
    pairwise: Sequence[dict[str, Any]],
    forcing_contrast: Sequence[dict[str, Any]],
    sanity: Sequence[dict[str, Any]],
    manifest_notes: Sequence[str],
) -> str:
    """Return final decision status for B8.5-F3a-QA."""
    if manifest_notes:
        return MICRO_BATCH_RASTER_QA_BLOCKED
    if any(not payload.opened for payload in payloads):
        return MICRO_BATCH_RASTER_QA_BLOCKED
    if any(row.get("status") == FAIL for row in alignment):
        return MICRO_BATCH_RASTER_QA_PARTIAL
    if any(row.get("status") == FAIL for row in sanity):
        return MICRO_BATCH_RASTER_QA_PARTIAL
    if any(row.get("sanity_status") != PASS for row in stats_rows):
        return MICRO_BATCH_RASTER_QA_PARTIAL
    if any(row.get("delta_direction_status") == "overhead_warming_or_suspicious" for row in pairwise):
        return MICRO_BATCH_RASTER_QA_PARTIAL
    if any(row.get("qualitative_status") == "suspicious_large_difference" for row in forcing_contrast):
        return MICRO_BATCH_RASTER_QA_PARTIAL
    return MICRO_BATCH_RASTER_QA_PASS


def next_action(decision_status: str) -> str:
    """Return the recommended next lane action."""
    if decision_status == MICRO_BATCH_RASTER_QA_PASS:
        return "F3b one-cell full slice"
    if decision_status == MICRO_BATCH_RASTER_QA_BLOCKED:
        return "fix runner/assets"
    return "inspect raster manually before F3b"


def write_report(
    path: Path,
    decision_status: str,
    inventory: Sequence[dict[str, Any]],
    stats: Sequence[dict[str, Any]],
    pairwise: Sequence[dict[str, Any]],
    forcing_contrast: Sequence[dict[str, Any]],
    alignment: Sequence[dict[str, Any]],
    sanity: Sequence[dict[str, Any]],
    recommendation: str,
) -> None:
    """Write the English Markdown QA report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    opened = sum(1 for row in inventory if row.get("opened_for_qa") == YES)
    lines = [
        "# B8.5-F3a Raster Content QA Report",
        "",
        f"Generated: {now_stamp()}",
        "",
        "## Decision",
        "",
        f"- Status: `{decision_status}`",
        f"- Raster count opened: `{opened}/4`",
        f"- Alignment status: `{alignment_status_from_rows(alignment)}`",
        f"- Per-run p90 range: `{p90_range(stats)}`",
        f"- Base-vs-overhead delta headline: {pairwise_headline(pairwise)}",
        f"- FD02-vs-FD01 contrast headline: {forcing_contrast_headline(forcing_contrast)}",
        f"- Next recommended action: `{recommendation}`",
        "",
        "## Why This Follows F3a POST",
        "",
        "B8.5-F3a POST already showed 4/4 run-log success and 4/4 expected `Tmrt_average.tif` files, but it did not open raster contents. This QA lane is the next compact content sanity check for the same four-run micro-batch only.",
        "",
        "## Read/Write Boundary",
        "",
        "The script read only the four local `Tmrt_average.tif` rasters declared by the F3a manifest. It wrote no raster, image, GeoTIFF, PNG, clipped raster, or large array output. It did not open or copy `svfs.zip`, and it did not run QGIS or SOLWEIG.",
        "",
        "## Raster Inventory Summary",
        "",
        markdown_table(
            inventory,
            ["run_id", "forcing_day_id", "scenario", "exists", "file_size_bytes", "crs", "width", "height", "opened_for_qa"],
        ),
        "",
        "## Per-Run Tmrt Stats",
        "",
        markdown_table(
            stats,
            ["run_id", "scenario", "valid_pixel_count", "nodata_fraction", "mean_c", "p50_c", "p90_c", "p95_c", "max_c", "sanity_status"],
        ),
        "",
        "## Base-vs-Overhead_As_Canopy Delta",
        "",
        "Delta is `overhead_as_canopy - base`. This is an overhead-as-canopy sensitivity check, not exact real-world overhead physics.",
        "",
        markdown_table(
            pairwise,
            ["forcing_day_id", "mean_delta_c", "p50_delta_c", "p90_delta_c", "p95_delta_c", "min_delta_c", "max_delta_c", "delta_direction_status"],
        ),
        "",
        "## FD01-vs-FD02 Contrast",
        "",
        markdown_table(
            forcing_contrast,
            ["scenario", "contrast_direction", "mean_difference_c", "p90_difference_c", "valid_overlap_pixels", "qualitative_status"],
        ),
        "",
        "## Alignment And Nodata Sanity",
        "",
        markdown_table(alignment, ["check_name", "status", "value", "details"]),
        "",
        "## Sanity Checks",
        "",
        markdown_table(sanity, ["check_name", "status", "value", "details"]),
        "",
        "## Claim Boundaries",
        "",
        "- This is not B9.",
        "- This is not local WBGT.",
        "- This is not risk.",
        "- This is not full multi-forcing stability.",
        "- No Tmrt-to-WBGT conversion was performed.",
        "- No raster was committed or written by this QA lane.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_status(
    path: Path,
    decision_status: str,
    result: RasterQaResult,
    files_created: Sequence[Path],
) -> None:
    """Write the lane status Markdown file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# B8.5-F3a Raster QA Status",
        "",
        f"Generated: {now_stamp()}",
        "",
        "## Status",
        "",
        f"`{decision_status}`",
        "",
        "## Branch",
        "",
        "`codex/b85-f3a-raster-qa`",
        "",
        "## Scope",
        "",
        "Content sanity QA for the four local F3a micro-batch `Tmrt_average.tif` rasters only. QGIS/SOLWEIG were not executed; no raster, image, or large array outputs were written.",
        "",
        "## Key Results",
        "",
        f"- Raster count opened: `{result.raster_count_opened}`",
        f"- Alignment status: `{result.alignment_status}`",
        f"- Per-run p90 range: `{result.per_run_p90_range}`",
        f"- Base-vs-overhead delta: {result.pairwise_delta_headline}",
        f"- FD02-vs-FD01 contrast: {result.forcing_day_contrast_headline}",
        f"- Next recommended action: `{result.next_recommended_action}`",
        "- QGIS/SOLWEIG executed: `no`",
        "- Raster outputs written: `no`",
        "",
        "## Files Created / Modified",
        "",
        *[f"- `{path_text(path)}`" for path in files_created],
        "",
        "## Commands To Verify",
        "",
        "- `python -m compileall scripts/v12_b85_f3a_raster_qa.py scripts/v12_b85_run_f3a_raster_qa.py`",
        "- `python scripts/v12_b85_run_f3a_raster_qa.py --config configs/v12/systemb_b85_f3a_raster_qa.yaml`",
        "- Python mojibake check on `docs/v12/OpenHeat_SystemB_B8_5_F3a_raster_QA_CN.md`",
        "- `git status --short -- .`",
        "- forbidden-file check",
        "",
        "## Safe To Commit",
        "",
        "Only compact config, scripts, docs, CSV, and Markdown control artifacts listed above after review.",
        "",
        "## Not Safe To Commit",
        "",
        "Rasters, `.tif`, `.tiff`, `svfs.zip`, `data/solweig/`, `data/rasters/`, raw archives, patch zip packages, and large forecast CSV files.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_cn_doc(
    path: Path,
    decision_status: str,
    inventory: Sequence[dict[str, Any]],
    stats: Sequence[dict[str, Any]],
    pairwise: Sequence[dict[str, Any]],
    forcing_contrast: Sequence[dict[str, Any]],
    alignment: Sequence[dict[str, Any]],
    sanity: Sequence[dict[str, Any]],
    recommendation: str,
) -> None:
    """Write the Chinese UTF-8 raster QA note."""
    path.parent.mkdir(parents=True, exist_ok=True)
    opened = sum(1 for row in inventory if row.get("opened_for_qa") == YES)
    lines = [
        "# OpenHeat System B B8.5-F3a 栅格内容 QA 中文说明",
        "",
        f"生成时间：{now_stamp()}",
        "",
        "## 结论",
        "",
        f"- 决策状态：`{decision_status}`",
        f"- 成功打开栅格：`{opened}/4`",
        f"- 对齐状态：`{alignment_status_from_rows(alignment)}`",
        f"- 每次运行 p90 范围：`{p90_range(stats)}`",
        f"- base-vs-overhead_as_canopy delta 摘要：{pairwise_headline(pairwise)}",
        f"- FD02-vs-FD01 对比摘要：{forcing_contrast_headline(forcing_contrast)}",
        f"- 下一步建议：`{recommendation}`",
        "",
        "## 1. 为什么这是 F3a POST 之后的步骤",
        "",
        "F3a POST 已经确认 4/4 run log success，并确认 4/4 预期 `Tmrt_average.tif` 文件存在；但上一阶段没有打开 raster 内容。本 QA lane 只补上四个本地栅格的紧凑内容检查。",
        "",
        "## 2. 读取了什么，没有写什么",
        "",
        "本脚本只读取 manifest 中声明的四个本地 `Tmrt_average.tif`。它没有运行 QGIS/SOLWEIG，没有复制或打开 `svfs.zip`，没有创建、复制、移动任何 raster，也没有写 GeoTIFF、PNG、裁剪栅格或大型数组输出。",
        "",
        "## 3. Raster inventory 摘要",
        "",
        markdown_table(
            inventory,
            ["run_id", "forcing_day_id", "scenario", "exists", "file_size_bytes", "crs", "width", "height", "opened_for_qa"],
        ),
        "",
        "## 4. 每次运行 Tmrt 统计",
        "",
        markdown_table(
            stats,
            ["run_id", "scenario", "valid_pixel_count", "nodata_fraction", "mean_c", "p50_c", "p90_c", "p95_c", "max_c", "sanity_status"],
        ),
        "",
        "## 5. Base-vs-overhead_as_canopy delta",
        "",
        "这里的 delta 定义为 `overhead_as_canopy - base`。它只是 overhead-as-canopy sensitivity，不代表精确的真实高架/连廊物理效应。",
        "",
        markdown_table(
            pairwise,
            ["forcing_day_id", "mean_delta_c", "p50_delta_c", "p90_delta_c", "p95_delta_c", "min_delta_c", "max_delta_c", "delta_direction_status"],
        ),
        "",
        "## 6. FD01-vs-FD02 forcing-day 对比",
        "",
        markdown_table(
            forcing_contrast,
            ["scenario", "contrast_direction", "mean_difference_c", "p90_difference_c", "valid_overlap_pixels", "qualitative_status"],
        ),
        "",
        "## 7. 对齐、nodata 与 sanity",
        "",
        markdown_table(alignment, ["check_name", "status", "value", "details"]),
        "",
        "## 8. Micro-batch content QA 是否通过",
        "",
        f"当前判定为 `{decision_status}`。若为 PASS，则四个栅格均可打开、统计值在合理范围内、栅格对齐通过，且 base-vs-overhead_as_canopy delta 未显示 warming/suspicious 信号。",
        "",
        "## 9. 下一步建议",
        "",
        f"建议下一步：`{recommendation}`。",
        "",
        "## 10. Claim boundaries",
        "",
        "- 这不是 B9。",
        "- 这不是 local WBGT。",
        "- 这不是 risk。",
        "- 这不是 full multi-forcing stability。",
        "- 没有进行 Tmrt-to-WBGT conversion。",
        "- 没有提交或写出任何 raster。",
        "- 本结果只服务于 4-run micro-batch 内容 QA。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def output_paths(config: dict[str, Any]) -> list[Path]:
    """Return all output paths written by the raster QA run."""
    outputs = config["outputs"]
    created = [
        repo_path("configs/v12/systemb_b85_f3a_raster_qa.yaml"),
        repo_path("scripts/v12_b85_f3a_raster_qa.py"),
        repo_path("scripts/v12_b85_run_f3a_raster_qa.py"),
    ]
    keys = [
        "canonical_note_cn",
        "raster_inventory",
        "raster_stats",
        "pairwise_delta_summary",
        "forcing_day_contrast_summary",
        "alignment_qa",
        "sanity_checks",
        "raster_qa_report",
        "status",
    ]
    created.extend(repo_path(outputs[key]) for key in keys)
    return created


def run(config_path: Path = DEFAULT_CONFIG) -> RasterQaResult:
    """Run B8.5-F3a raster content QA and write compact artifacts."""
    config = read_config(repo_path(config_path))
    ensure_scope_flags(config)
    outputs = config["outputs"]
    repo_path(outputs["out_dir"]).mkdir(parents=True, exist_ok=True)

    manifest_rows = read_csv_rows(repo_path(config["microbatch_manifest_path"]))
    postrun_rows = read_csv_rows(repo_path(config["postrun_validation_path"]))
    merged_rows = merge_postrun_status(manifest_rows, postrun_rows)
    manifest_notes = validate_manifest_scope(config, merged_rows)

    payloads = [read_raster_payload(row) for row in merged_rows]
    thresholds = [float(value) for value in config["thresholds_c"]]
    plausible_min = float(config["plausible_tmrt_min_c"])
    plausible_max = float(config["plausible_tmrt_max_c"])

    inventory = [inventory_row(payload) for payload in payloads]
    stats = [raster_stats_row(payload, thresholds, plausible_min, plausible_max) for payload in payloads]
    pairwise = pairwise_delta_rows(payloads)
    forcing_contrast = forcing_day_contrast_rows(payloads)
    alignment = alignment_rows(payloads, config, git_root())
    status_lines = git_status_short()
    sanity = sanity_rows(payloads, stats, pairwise, config, status_lines)
    if manifest_notes:
        for note in manifest_notes:
            add_check(sanity, "manifest_scope", FAIL, note, "Manifest must remain the four-run F3a micro-batch.")

    decision_status = decide_status(payloads, stats, alignment, pairwise, forcing_contrast, sanity, manifest_notes)
    recommendation = next_action(decision_status)
    files_created = output_paths(config)
    result = RasterQaResult(
        decision_status=decision_status,
        raster_count_opened=sum(1 for p in payloads if p.opened),
        alignment_status=alignment_status_from_rows(alignment),
        per_run_p90_range=p90_range(stats),
        pairwise_delta_headline=pairwise_headline(pairwise),
        forcing_day_contrast_headline=forcing_contrast_headline(forcing_contrast),
        next_recommended_action=recommendation,
        files_created=files_created,
    )

    write_csv_rows(repo_path(outputs["raster_inventory"]), inventory, RASTER_INVENTORY_FIELDS)
    write_csv_rows(repo_path(outputs["raster_stats"]), stats, raster_stats_fields(thresholds))
    write_csv_rows(repo_path(outputs["pairwise_delta_summary"]), pairwise, PAIRWISE_FIELDS)
    write_csv_rows(repo_path(outputs["forcing_day_contrast_summary"]), forcing_contrast, FORCING_CONTRAST_FIELDS)
    write_csv_rows(repo_path(outputs["alignment_qa"]), alignment, CHECK_FIELDS)
    write_csv_rows(repo_path(outputs["sanity_checks"]), sanity, CHECK_FIELDS)
    write_report(repo_path(outputs["raster_qa_report"]), decision_status, inventory, stats, pairwise, forcing_contrast, alignment, sanity, recommendation)
    write_cn_doc(repo_path(outputs["canonical_note_cn"]), decision_status, inventory, stats, pairwise, forcing_contrast, alignment, sanity, recommendation)
    write_status(repo_path(outputs["status"]), decision_status, result, files_created)
    return result


RASTER_INVENTORY_FIELDS = [
    "run_id",
    "cell_id",
    "forcing_day_id",
    "date",
    "hour_sgt",
    "scenario",
    "raster_path",
    "exists",
    "file_size_bytes",
    "crs",
    "width",
    "height",
    "pixel_count",
    "transform",
    "nodata",
    "dtype",
    "band_count",
    "opened_for_qa",
    "copied_or_written",
    "raster_backend",
    "open_error",
]


def raster_stats_fields(thresholds: Sequence[float]) -> list[str]:
    """Return raster stats CSV fieldnames including configured thresholds."""
    fields = [
        "run_id",
        "cell_id",
        "forcing_day_id",
        "date",
        "hour_sgt",
        "scenario",
        "raster_path",
        "valid_pixel_count",
        "nodata_pixel_count",
        "nodata_fraction",
        "min_c",
        "p01_c",
        "p05_c",
        "p25_c",
        "mean_c",
        "p50_c",
        "p75_c",
        "p90_c",
        "p95_c",
        "p99_c",
        "max_c",
        "std_c",
    ]
    fields.extend([f"pct_pixels_ge_{int(threshold)}" for threshold in thresholds])
    fields.extend(["sanity_status", "sanity_notes"])
    return fields


PAIRWISE_FIELDS = [
    "forcing_day_id",
    "mean_delta_c",
    "p50_delta_c",
    "p90_delta_c",
    "p95_delta_c",
    "max_delta_c",
    "min_delta_c",
    "pct_pixels_delta_lt_minus_1",
    "pct_pixels_delta_lt_minus_5",
    "pct_pixels_delta_gt_1",
    "valid_overlap_pixels",
    "delta_direction_status",
    "notes",
]


FORCING_CONTRAST_FIELDS = [
    "scenario",
    "fd01_forcing_day_id",
    "fd02_forcing_day_id",
    "contrast_direction",
    "mean_delta_c",
    "p50_delta_c",
    "p90_delta_c",
    "p95_delta_c",
    "max_delta_c",
    "min_delta_c",
    "mean_difference_c",
    "p90_difference_c",
    "valid_overlap_pixels",
    "qualitative_status",
    "notes",
]


CHECK_FIELDS = ["check_name", "status", "value", "details"]


def main() -> int:
    """Parse CLI args and run the raster QA."""
    parser = argparse.ArgumentParser(
        description=(
            "Read the four B8.5-F3a local Tmrt_average.tif rasters and write "
            "compact content QA CSV/Markdown outputs without running QGIS/SOLWEIG "
            "or writing raster/image outputs."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="B8.5-F3a raster QA YAML config.")
    args = parser.parse_args()
    result = run(repo_path(args.config))
    print(f"Decision status: {result.decision_status}")
    print(f"Raster count opened: {result.raster_count_opened}")
    print(f"Alignment status: {result.alignment_status}")
    print(f"Per-run p90 range: {result.per_run_p90_range}")
    print(f"Base-vs-overhead delta headline: {result.pairwise_delta_headline}")
    print(f"FD02-vs-FD01 contrast headline: {result.forcing_day_contrast_headline}")
    print(f"Next recommended action: {result.next_recommended_action}")
    print("QGIS/SOLWEIG executed: no")
    print("Raster outputs written: no")
    print("Files created:")
    for path in result.files_created:
        print(f"- {path_text(path)}")
    return 0 if result.decision_status != FAILED else 1


if __name__ == "__main__":
    raise SystemExit(main())
