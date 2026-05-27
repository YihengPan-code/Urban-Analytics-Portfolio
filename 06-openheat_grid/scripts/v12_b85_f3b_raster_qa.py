"""Aggregate B8.5-F3b one-cell full-slice raster-content QA.

Inputs:
    configs/v12/systemb_b85_f3b_onecell_fullslice.yaml
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_onecell_manifest.csv
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_postrun_validation.csv
    Twenty local Tmrt_average.tif rasters declared by the F3b manifest, only
    after human execution and postrun validation have succeeded.

Outputs:
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_raster_inventory.csv
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_raster_stats.csv
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_hourly_profile.csv
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_pairwise_delta_by_hour.csv
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_forcing_day_contrast_by_hour.csv
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_alignment_qa.csv
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_sanity_checks.csv
    outputs/v12_surrogate/b8_5_f3b_onecell/b85_f3b_onecell_report.md
    outputs/v12_surrogate/b8_5_f3b_onecell/B8_5_F3B_STATUS.md

Saved metrics:
    Raster inventory, per-raster valid/nodata and Tmrt percentile stats,
    threshold exceedance percentages, alignment checks, hourly profiles,
    base-vs-overhead_as_canopy deltas by hour, FD02-vs-FD01 contrasts by hour,
    one-cell summary tables, F3a hour-13 consistency anchors, sanity checks,
    and final one-cell slice raster QA decision status.

This script does not run QGIS, run SOLWEIG, copy/open svfs.zip, create/copy/move
rasters, write raster/image/large-array outputs, create AOI-wide predictions,
compute local WBGT, create hazard_score/risk_score outputs, create System A/B
coupling outputs, stage, or commit. Before human execution it writes compact
NOT_RUN_YET placeholders and does not open raster contents.
"""

from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from v12_b85_f3b_prepare_onecell_fullslice import (
    BLOCKED_POSTRUN,
    BLOCKED_PRECHECK,
    FAIL,
    FAILED,
    NO,
    NOT_RUN_YET,
    ONECELL_SLICE_EXECUTED_PARTIAL,
    ONECELL_SLICE_EXECUTED_PASS,
    PASS,
    READY_FOR_HUMAN_ONECELL_SLICE,
    ROOT,
    WARN,
    YES,
    all_lane_paths,
    changed_forbidden_paths,
    clean,
    expected_run_count,
    git_root,
    git_status_short,
    is_relative_to,
    markdown_table,
    onecell,
    path_outside_git_and_under_local,
    read_config,
    read_csv_rows,
    rel,
    repo_path,
    row_key,
    write_csv_rows,
    write_status_report,
    write_text,
)


DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_f3b_onecell_fullslice.yaml"


@dataclass(frozen=True)
class RasterPayload:
    """Raster metadata, array content, and valid mask for one run."""

    run: dict[str, str]
    metadata: dict[str, Any]
    array: Any
    valid_mask: Any
    opened: bool
    backend: str
    error: str


@dataclass(frozen=True)
class RasterQaResult:
    """Compact result for CLI reporting."""

    decision_status: str
    manifest_run_count: int
    pre_execution_ready_count: int
    postrun_status: str
    raster_qa_status: str
    raster_count_opened: int
    alignment_status: str
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


def parent_hour(path: Path) -> int | None:
    """Parse an h13-style parent folder hour when present."""
    match = re.search(r"^h(\d{1,2})$", path.parent.name)
    return int(match.group(1)) if match else None


def add_check(rows: list[dict[str, Any]], name: str, status: str, value: Any, details: str) -> None:
    """Append one compact QA check row."""
    rows.append({"check_name": name, "status": status, "value": clean(value), "details": details})


def postrun_ready_for_content_qa(config: dict[str, Any], rows: Sequence[dict[str, str]]) -> bool:
    """Return whether postrun validation permits raster content reads."""
    if len(rows) != expected_run_count(config):
        return False
    for row in rows:
        if clean(row.get("phase")) != "EXECUTED":
            return False
        if clean(row.get("validation_status")).upper() != PASS:
            return False
        if clean(row.get("file_exists")).lower() != YES:
            return False
        try:
            if int(clean(row.get("file_size_bytes")) or "0") <= 0:
                return False
        except ValueError:
            return False
    return True


def precheck_ready_count(config: dict[str, Any]) -> int:
    """Return the F3b pre-execution ready count when the file exists."""
    path = repo_path(config["outputs"]["pre_execution_asset_check"])
    if not path.exists():
        return 0
    rows = read_csv_rows(path)
    return sum(
        1
        for row in rows
        if clean(row.get("run_ready")).lower() == YES and clean(row.get("pre_execution_status")).upper() == PASS
    )


def placeholder_inventory_rows(manifest_rows: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
    """Build raster inventory placeholders without touching local rasters."""
    return [
        {
            "run_id": row["run_id"],
            "cell_id": row["cell_id"],
            "forcing_day_id": row["forcing_day_id"],
            "date": row["date"],
            "hour_sgt": row["hour_sgt"],
            "scenario": row["scenario"],
            "raster_path": row["expected_tmrt_path"],
            "exists": "",
            "file_size_bytes": "",
            "crs": "",
            "width": "",
            "height": "",
            "shape": "",
            "pixel_count": "",
            "transform": "",
            "nodata": "",
            "dtype": "",
            "band_count": "",
            "opened_for_qa": NO,
            "copied_or_written": NO,
            "raster_backend": "",
            "open_error": NOT_RUN_YET,
        }
        for row in manifest_rows
    ]


def placeholder_stats_rows(manifest_rows: Sequence[dict[str, str]], thresholds: Sequence[float]) -> list[dict[str, Any]]:
    """Build raster stats placeholders without touching local rasters."""
    rows: list[dict[str, Any]] = []
    for row in manifest_rows:
        out = {
            "run_id": row["run_id"],
            "cell_id": row["cell_id"],
            "forcing_day_id": row["forcing_day_id"],
            "date": row["date"],
            "hour_sgt": row["hour_sgt"],
            "scenario": row["scenario"],
            "raster_path": row["expected_tmrt_path"],
            "valid_pixel_count": "",
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
            "sanity_status": NOT_RUN_YET,
            "sanity_notes": "Raster content QA waits for postrun validation.",
        }
        for threshold in thresholds:
            out[f"pct_ge_{int(threshold)}"] = ""
        rows.append(out)
    return rows


def placeholder_outputs(config: dict[str, Any], reason: str) -> RasterQaResult:
    """Write compact NOT_RUN_YET QA placeholders and status."""
    outputs = config["outputs"]
    manifest_rows = read_csv_rows(repo_path(outputs["manifest"]))
    thresholds = [float(value) for value in onecell(config)["thresholds_c"]]
    inventory = placeholder_inventory_rows(manifest_rows)
    stats = placeholder_stats_rows(manifest_rows, thresholds)
    alignment = [
        {
            "check_name": "postrun_validation_required_before_raster_content_read",
            "status": NOT_RUN_YET,
            "value": reason,
            "details": "Raster QA does not open local rasters until postrun validation shows 20/20 success and output files exist.",
        }
    ]
    sanity = [
        {
            "check_name": "no_raster_content_opened_before_manual_execution",
            "status": PASS,
            "value": "0 rasters opened",
            "details": "This placeholder run wrote CSV/Markdown summaries only.",
        },
        {
            "check_name": "no_qgis_or_solweig_execution",
            "status": PASS,
            "value": "no",
            "details": "Codex/Python did not run QGIS or SOLWEIG.",
        },
    ]
    write_csv_rows(repo_path(outputs["raster_inventory"]), inventory, RASTER_INVENTORY_FIELDS)
    write_csv_rows(repo_path(outputs["raster_stats"]), stats, raster_stats_fields(thresholds))
    write_csv_rows(repo_path(outputs["hourly_profile"]), [], HOURLY_PROFILE_FIELDS)
    write_csv_rows(repo_path(outputs["pairwise_delta_by_hour"]), [], PAIRWISE_FIELDS)
    write_csv_rows(repo_path(outputs["forcing_day_contrast_by_hour"]), [], FORCING_CONTRAST_FIELDS)
    write_csv_rows(repo_path(outputs["alignment_qa"]), alignment, CHECK_FIELDS)
    write_csv_rows(repo_path(outputs["sanity_checks"]), sanity, CHECK_FIELDS)
    write_report(
        repo_path(outputs["onecell_report"]),
        config,
        READY_FOR_HUMAN_ONECELL_SLICE,
        NOT_RUN_YET,
        inventory,
        stats,
        [],
        [],
        [],
        alignment,
        sanity,
        [],
        [],
        "Full 480 remains blocked; run the 20-run human-controlled slice first.",
    )
    ready_count = precheck_ready_count(config)
    write_status_report(
        repo_path(outputs["status"]),
        config,
        READY_FOR_HUMAN_ONECELL_SLICE if ready_count == expected_run_count(config) else BLOCKED_PRECHECK,
        len(manifest_rows),
        ready_count,
        NOT_RUN_YET,
        NOT_RUN_YET,
        reason,
    )
    return RasterQaResult(
        decision_status=READY_FOR_HUMAN_ONECELL_SLICE if ready_count == expected_run_count(config) else BLOCKED_PRECHECK,
        manifest_run_count=len(manifest_rows),
        pre_execution_ready_count=ready_count,
        postrun_status=NOT_RUN_YET,
        raster_qa_status=NOT_RUN_YET,
        raster_count_opened=0,
        alignment_status=NOT_RUN_YET,
        files_created=all_lane_paths(config),
    )


def read_with_rasterio(path: Path) -> tuple[dict[str, Any], Any, str]:
    """Read one raster with rasterio when available."""
    import numpy as np
    import rasterio

    with rasterio.open(path) as src:
        array = src.read(1)
        transform = tuple(float(v) for v in src.transform.to_gdal())
        metadata = {
            "crs": src.crs.to_string() if src.crs else "",
            "width": int(src.width),
            "height": int(src.height),
            "shape": f"{int(src.height)}x{int(src.width)}",
            "pixel_count": int(src.width * src.height),
            "transform": str(transform),
            "nodata": src.nodata,
            "dtype": str(src.dtypes[0]) if src.dtypes else "",
            "band_count": int(src.count),
        }
    return metadata, np.asarray(array), "rasterio"


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


def read_with_gdal(path: Path) -> tuple[dict[str, Any], Any, str]:
    """Read one raster with GDAL Python bindings when rasterio is unavailable."""
    import numpy as np
    from osgeo import gdal

    dataset = gdal.Open(path.as_posix(), gdal.GA_ReadOnly)
    if dataset is None:
        raise RuntimeError(f"GDAL could not open raster: {path.as_posix()}")
    try:
        band = dataset.GetRasterBand(1)
        if band is None:
            raise RuntimeError(f"Raster has no band 1: {path.as_posix()}")
        array = band.ReadAsArray()
        transform = tuple(float(v) for v in dataset.GetGeoTransform())
        metadata = {
            "crs": crs_from_wkt(dataset.GetProjectionRef()),
            "width": int(dataset.RasterXSize),
            "height": int(dataset.RasterYSize),
            "shape": f"{int(dataset.RasterYSize)}x{int(dataset.RasterXSize)}",
            "pixel_count": int(dataset.RasterXSize * dataset.RasterYSize),
            "transform": str(transform),
            "nodata": band.GetNoDataValue(),
            "dtype": str(gdal.GetDataTypeName(band.DataType)),
            "band_count": int(dataset.RasterCount),
        }
    finally:
        dataset = None
    return metadata, np.asarray(array), "gdal"


def valid_pixel_mask(array: Any, nodata: Any) -> Any:
    """Return finite non-nodata pixels."""
    import numpy as np

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


def read_raster_payload(run: dict[str, str]) -> RasterPayload:
    """Read one manifest-declared raster after postrun validation passes."""
    path = Path(run["expected_tmrt_path"])
    exists = path.exists()
    metadata: dict[str, Any] = {
        "exists": YES if exists else NO,
        "file_size_bytes": str(path.stat().st_size) if exists else "0",
        "parent_folder_hour_sgt": parent_hour(path),
    }
    if not exists:
        return RasterPayload(run, metadata, None, None, False, "", "raster_missing")
    errors: list[str] = []
    for reader in (read_with_rasterio, read_with_gdal):
        try:
            raster_metadata, array, backend = reader(path)
            metadata.update(raster_metadata)
            return RasterPayload(run, metadata, array, valid_pixel_mask(array, metadata.get("nodata")), True, backend, "")
        except ModuleNotFoundError as exc:
            errors.append(f"{reader.__name__}: missing {exc.name}")
        except Exception as exc:
            errors.append(f"{reader.__name__}: {exc}")
    return RasterPayload(run, metadata, None, None, False, "", "; ".join(errors))


def valid_values(payload: RasterPayload) -> Any:
    """Return valid float values for one raster."""
    import numpy as np

    if payload.array is None or payload.valid_mask is None:
        return np.asarray([], dtype="float64")
    return payload.array.astype("float64", copy=False)[payload.valid_mask]


def percentile(values: Any, q: float) -> float:
    """Return a percentile as float."""
    import numpy as np

    return float(np.percentile(values, q))


def inventory_row(payload: RasterPayload) -> dict[str, Any]:
    """Build one raster inventory row."""
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
        "shape": metadata.get("shape", ""),
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


def raster_stats_row(payload: RasterPayload, thresholds: Sequence[float], plausible_min: float, plausible_max: float) -> dict[str, Any]:
    """Build per-raster content stats."""
    import numpy as np

    run = payload.run
    base: dict[str, Any] = {
        "run_id": run.get("run_id", ""),
        "cell_id": run.get("cell_id", ""),
        "forcing_day_id": run.get("forcing_day_id", ""),
        "date": run.get("date", ""),
        "hour_sgt": run.get("hour_sgt", ""),
        "scenario": run.get("scenario", ""),
        "raster_path": run.get("expected_tmrt_path", ""),
    }
    for threshold in thresholds:
        base[f"pct_ge_{int(threshold)}"] = ""
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
                "sanity_status": BLOCKED_POSTRUN,
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
                "sanity_status": FAIL,
                "sanity_notes": "no_valid_pixels",
            }
        )
        return base
    min_c = float(np.min(values))
    max_c = float(np.max(values))
    p50 = percentile(values, 50)
    p90 = percentile(values, 90)
    p95 = percentile(values, 95)
    nodata_fraction = float(nodata_count) / float(pixel_count) if pixel_count else math.nan
    notes: list[str] = []
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
        base[f"pct_ge_{int(threshold)}"] = format_float(float(np.count_nonzero(values >= threshold)) * 100.0 / float(valid_count))
    return base


def hourly_profile_rows(stats_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return per forcing-day x scenario x hour profile rows."""
    rows: list[dict[str, Any]] = []
    for row in sorted(stats_rows, key=lambda r: (r["forcing_day_id"], r["scenario"], int(r["hour_sgt"]))):
        rows.append(
            {
                "forcing_day_id": row["forcing_day_id"],
                "scenario": row["scenario"],
                "hour_sgt": row["hour_sgt"],
                "mean_c": row.get("mean_c", ""),
                "p50_c": row.get("p50_c", ""),
                "p90_c": row.get("p90_c", ""),
                "p95_c": row.get("p95_c", ""),
                "max_c": row.get("max_c", ""),
                "notes": "one raster per forcing_day/scenario/hour for TP_0037",
            }
        )
    return rows


def payload_by_key(payloads: Sequence[RasterPayload]) -> dict[tuple[str, str, int, str], RasterPayload]:
    """Return payloads keyed by cell, forcing day, hour, scenario."""
    return {row_key(payload.run): payload for payload in payloads}


def delta_values(a: RasterPayload, b: RasterPayload) -> Any:
    """Return b - a over valid overlap pixels."""
    import numpy as np

    if not a.opened or not b.opened or a.array is None or b.array is None:
        return np.asarray([], dtype="float64")
    mask = a.valid_mask & b.valid_mask
    if int(np.count_nonzero(mask)) == 0:
        return np.asarray([], dtype="float64")
    return b.array.astype("float64", copy=False)[mask] - a.array.astype("float64", copy=False)[mask]


def pairwise_delta_rows(config: dict[str, Any], payloads: Sequence[RasterPayload]) -> list[dict[str, Any]]:
    """Build base-vs-overhead_as_canopy delta rows by forcing day and hour."""
    import numpy as np

    section = onecell(config)
    by_key = payload_by_key(payloads)
    rows: list[dict[str, Any]] = []
    cell_id = section["cell_id"]
    for forcing_day in section["forcing_days"]:
        for hour in section["hours_sgt"]:
            base = by_key.get((cell_id, forcing_day, int(hour), "base"))
            overhead = by_key.get((cell_id, forcing_day, int(hour), "overhead_as_canopy"))
            vals = delta_values(base, overhead) if base and overhead else np.asarray([], dtype="float64")
            if vals.size == 0:
                rows.append(
                    {
                        "forcing_day_id": forcing_day,
                        "hour_sgt": str(hour),
                        "mean_delta_c": "",
                        "p50_delta_c": "",
                        "p90_delta_c": "",
                        "p95_delta_c": "",
                        "min_delta_c": "",
                        "max_delta_c": "",
                        "pct_pixels_delta_lt_minus_1": "",
                        "pct_pixels_delta_lt_minus_5": "",
                        "pct_pixels_delta_gt_1": "",
                        "valid_overlap_pixels": "0",
                        "status": "overhead_warming_or_suspicious",
                        "notes": "missing valid overlap pixels",
                    }
                )
                continue
            mean_delta = float(np.mean(vals))
            pct_lt_minus_1 = float(np.count_nonzero(vals < -1.0)) * 100.0 / float(vals.size)
            pct_gt_1 = float(np.count_nonzero(vals > 1.0)) * 100.0 / float(vals.size)
            if mean_delta > 0.5 or pct_gt_1 > 5.0:
                status = "overhead_warming_or_suspicious"
            elif mean_delta <= -1.0 or pct_lt_minus_1 >= 10.0:
                status = "overhead_cooling"
            else:
                status = "overhead_neutral"
            rows.append(
                {
                    "forcing_day_id": forcing_day,
                    "hour_sgt": str(hour),
                    "mean_delta_c": format_float(mean_delta),
                    "p50_delta_c": format_float(percentile(vals, 50)),
                    "p90_delta_c": format_float(percentile(vals, 90)),
                    "p95_delta_c": format_float(percentile(vals, 95)),
                    "min_delta_c": format_float(float(np.min(vals))),
                    "max_delta_c": format_float(float(np.max(vals))),
                    "pct_pixels_delta_lt_minus_1": format_float(pct_lt_minus_1),
                    "pct_pixels_delta_lt_minus_5": format_float(float(np.count_nonzero(vals < -5.0)) * 100.0 / float(vals.size)),
                    "pct_pixels_delta_gt_1": format_float(pct_gt_1),
                    "valid_overlap_pixels": str(int(vals.size)),
                    "status": status,
                    "notes": "delta is overhead_as_canopy - base; not WBGT",
                }
            )
    return rows


def forcing_day_contrast_rows(config: dict[str, Any], payloads: Sequence[RasterPayload]) -> list[dict[str, Any]]:
    """Build FD02 - FD01 contrast rows by scenario and hour."""
    import numpy as np

    section = onecell(config)
    fd01, fd02 = section["forcing_days"]
    by_key = payload_by_key(payloads)
    rows: list[dict[str, Any]] = []
    cell_id = section["cell_id"]
    for scenario in section["scenarios"]:
        for hour in section["hours_sgt"]:
            p1 = by_key.get((cell_id, fd01, int(hour), scenario))
            p2 = by_key.get((cell_id, fd02, int(hour), scenario))
            vals = delta_values(p1, p2) if p1 and p2 else np.asarray([], dtype="float64")
            if vals.size == 0:
                status = "suspicious_large_difference"
                rows.append(
                    {
                        "scenario": scenario,
                        "hour_sgt": str(hour),
                        "fd01_forcing_day_id": fd01,
                        "fd02_forcing_day_id": fd02,
                        "contrast_direction": "FD02_minus_FD01",
                        "mean_difference_c": "",
                        "p50_difference_c": "",
                        "p90_difference_c": "",
                        "p95_difference_c": "",
                        "min_difference_c": "",
                        "max_difference_c": "",
                        "valid_overlap_pixels": "0",
                        "qualitative_status": status,
                        "notes": "missing valid overlap pixels",
                    }
                )
                continue
            mean_diff = float(np.mean(vals))
            p90_diff = percentile(vals, 90)
            p95_diff = percentile(vals, 95)
            if abs(mean_diff) > 15.0 or abs(p90_diff) > 15.0 or abs(p95_diff) > 20.0:
                status = "suspicious_large_difference"
            elif abs(mean_diff) < 1.0 and abs(p90_diff) < 1.0:
                status = "neutral"
            else:
                status = "plausible_forcing_difference"
            rows.append(
                {
                    "scenario": scenario,
                    "hour_sgt": str(hour),
                    "fd01_forcing_day_id": fd01,
                    "fd02_forcing_day_id": fd02,
                    "contrast_direction": "FD02_minus_FD01",
                    "mean_difference_c": format_float(mean_diff),
                    "p50_difference_c": format_float(percentile(vals, 50)),
                    "p90_difference_c": format_float(p90_diff),
                    "p95_difference_c": format_float(p95_diff),
                    "min_difference_c": format_float(float(np.min(vals))),
                    "max_difference_c": format_float(float(np.max(vals))),
                    "valid_overlap_pixels": str(int(vals.size)),
                    "qualitative_status": status,
                    "notes": "Tmrt contrast only; no WBGT conversion",
                }
            )
    return rows


def alignment_rows(config: dict[str, Any], payloads: Sequence[RasterPayload]) -> list[dict[str, Any]]:
    """Build alignment QA rows."""
    rows: list[dict[str, Any]] = []
    opened = [payload for payload in payloads if payload.opened]
    expected = expected_run_count(config)
    add_check(rows, "all_20_rasters_opened", PASS if len(opened) == expected else FAIL, f"{len(opened)}/{expected}", "All expected local Tmrt rasters must open for content QA.")
    if not opened:
        return rows
    for field, label in [
        ("crs", "CRS"),
        ("shape", "shape"),
        ("transform", "transform"),
        ("nodata", "nodata"),
        ("dtype", "dtype"),
    ]:
        values = {clean(payload.metadata.get(field)) for payload in opened}
        add_check(
            rows,
            f"all_rasters_same_{field}",
            PASS if len(values) == 1 and len(opened) == expected else FAIL,
            "; ".join(sorted(values)),
            f"All rasters must have the same {label} before pixelwise deltas.",
        )
    pixel_counts = {clean(payload.metadata.get("pixel_count")) for payload in opened}
    add_check(rows, "expected_pixel_count_consistency", PASS if len(pixel_counts) == 1 else FAIL, "; ".join(sorted(pixel_counts)), "Pixel count should be identical for all 20 rasters.")
    local_paths_ok = all(path_outside_git_and_under_local(config, Path(payload.run["expected_tmrt_path"])) for payload in payloads)
    add_check(rows, "output_path_outside_git_worktree", PASS if local_paths_ok else FAIL, onecell(config)["local_solweig_output_root"], "Expected output paths must remain local-only and outside Git.")
    add_check(rows, "no_raster_output_written_by_qa", PASS, NO, "QA writes only compact CSV/Markdown artifacts.")
    return rows


def temporal_pattern_checks(config: dict[str, Any], hourly_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Warn if FD01 p90 does not peak near 12/13 versus 10/16."""
    rows: list[dict[str, Any]] = []
    fd01 = onecell(config)["forcing_days"][0]
    for scenario in onecell(config)["scenarios"]:
        by_hour: dict[int, float] = {}
        for row in hourly_rows:
            if row.get("forcing_day_id") == fd01 and row.get("scenario") == scenario and clean(row.get("p90_c")):
                by_hour[int(row["hour_sgt"])] = float(row["p90_c"])
        if not by_hour:
            add_check(rows, f"{fd01}:{scenario}:temporal_p90_midday_pattern", WARN, "missing", "No FD01 hourly p90 values available.")
            continue
        midday = max(by_hour.get(12, -math.inf), by_hour.get(13, -math.inf))
        edge = max(by_hour.get(10, -math.inf), by_hour.get(16, -math.inf))
        status = PASS if midday + 0.1 >= edge else WARN
        details = "Expected p90 generally higher near 12/13 than 10/16 for FD01; warning only, not automatic failure."
        add_check(rows, f"{fd01}:{scenario}:temporal_p90_midday_pattern", status, f"midday={midday:.6f}; edge={edge:.6f}", details)
    return rows


def sanity_rows(
    config: dict[str, Any],
    payloads: Sequence[RasterPayload],
    stats: Sequence[dict[str, Any]],
    pairwise: Sequence[dict[str, Any]],
    contrast: Sequence[dict[str, Any]],
    hourly_rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build one-cell sanity checks."""
    rows: list[dict[str, Any]] = []
    add_check(rows, "expected_run_count", PASS if len(payloads) == expected_run_count(config) else FAIL, f"{len(payloads)}/{expected_run_count(config)}", "F3b manifest must remain exactly 20 rows.")
    add_check(rows, "no_qgis_or_solweig_execution_by_codex", PASS, NO, "Codex/Python did not run QGIS/SOLWEIG.")
    add_check(rows, "no_raster_image_or_array_output_written", PASS, NO, "No raster, image, or large-array outputs are written.")
    forbidden = changed_forbidden_paths(git_status_short())
    add_check(rows, "no_forbidden_repo_files_changed", PASS if not forbidden else FAIL, "none" if not forbidden else "; ".join(forbidden), "Forbidden rasters, svfs.zip, raw archives, and large forecast CSVs must remain untouched.")
    for row in stats:
        run_id = row.get("run_id", "")
        add_check(rows, f"{run_id}:valid_pixel_count_gt_0", PASS if int(clean(row.get("valid_pixel_count")) or "0") > 0 else FAIL, row.get("valid_pixel_count", ""), "Raster must contain at least one valid Tmrt pixel.")
        add_check(rows, f"{run_id}:nodata_fraction_lt_0_5", PASS if float(clean(row.get("nodata_fraction")) or "1") < 0.5 else FAIL, row.get("nodata_fraction", ""), "Nodata fraction should remain below 0.5.")
        status = clean(row.get("sanity_status"))
        add_check(rows, f"{run_id}:per_raster_sanity_status", PASS if status == PASS else WARN if status == WARN else FAIL, status, clean(row.get("sanity_notes")))
    for row in pairwise:
        status = row.get("status", "")
        add_check(rows, f"{row.get('forcing_day_id')}:h{row.get('hour_sgt')}:overhead_delta_status", WARN if status == "overhead_warming_or_suspicious" else PASS, status, "overhead_as_canopy - base delta; warning status requires manual review.")
    for row in contrast:
        status = row.get("qualitative_status", "")
        add_check(rows, f"{row.get('scenario')}:h{row.get('hour_sgt')}:forcing_day_contrast_status", WARN if status == "suspicious_large_difference" else PASS, status, "FD02 - FD01 Tmrt contrast by scenario/hour.")
    rows.extend(temporal_pattern_checks(config, hourly_rows))
    return rows


def alignment_status(alignment: Sequence[dict[str, Any]]) -> str:
    """Return compact alignment status."""
    if alignment and any(row.get("status") == NOT_RUN_YET for row in alignment):
        return NOT_RUN_YET
    return PASS if alignment and all(row.get("status") == PASS for row in alignment) else FAIL


def f3a_anchor_rows(config: dict[str, Any], hourly_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare F3b h13 p90 values with F3a hour-13 QA anchors."""
    path = repo_path(config["inputs"]["f3a_raster_stats"])
    if not path.exists():
        return []
    f3a_rows = read_csv_rows(path)
    f3a_by_key = {(row["forcing_day_id"], row["scenario"]): row for row in f3a_rows}
    f3b_by_key = {
        (row["forcing_day_id"], row["scenario"]): row
        for row in hourly_rows
        if clean(row.get("hour_sgt")) == "13"
    }
    out: list[dict[str, Any]] = []
    for key, f3a in sorted(f3a_by_key.items()):
        f3b = f3b_by_key.get(key, {})
        f3a_p90 = clean(f3a.get("p90_c"))
        f3b_p90 = clean(f3b.get("p90_c"))
        diff = ""
        status = "anchor_pending"
        if f3a_p90 and f3b_p90:
            delta = float(f3b_p90) - float(f3a_p90)
            diff = format_float(delta)
            status = "consistent_anchor" if abs(delta) <= 2.0 else "manual_review_anchor_difference"
        out.append(
            {
                "forcing_day_id": key[0],
                "scenario": key[1],
                "f3a_h13_p90_c": f3a_p90,
                "f3b_h13_p90_c": f3b_p90,
                "difference_c": diff,
                "status": status,
            }
        )
    return out


def five_hour_summary_rows(hourly_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return 5-hour mean p90 and max-p90 hour by forcing day/scenario."""
    out: list[dict[str, Any]] = []
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in hourly_rows:
        groups.setdefault((row["forcing_day_id"], row["scenario"]), []).append(row)
    for (forcing_day, scenario), rows in sorted(groups.items()):
        p90_rows = [row for row in rows if clean(row.get("p90_c"))]
        if not p90_rows:
            continue
        p90_vals = [float(row["p90_c"]) for row in p90_rows]
        max_row = max(p90_rows, key=lambda row: float(row["p90_c"]))
        out.append(
            {
                "forcing_day_id": forcing_day,
                "scenario": scenario,
                "five_hour_mean_p90_c": format_float(sum(p90_vals) / len(p90_vals)),
                "hour_of_max_p90": max_row["hour_sgt"],
                "max_p90_c": max_row["p90_c"],
            }
        )
    return out


def five_hour_delta_summary_rows(pairwise: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return 5-hour mean delta p90 by forcing day."""
    groups: dict[str, list[float]] = {}
    for row in pairwise:
        if clean(row.get("p90_delta_c")):
            groups.setdefault(row["forcing_day_id"], []).append(float(row["p90_delta_c"]))
    return [
        {
            "forcing_day_id": forcing_day,
            "five_hour_mean_delta_p90_c": format_float(sum(values) / len(values)),
            "hours_included": str(len(values)),
        }
        for forcing_day, values in sorted(groups.items())
        if values
    ]


def decide_status(
    payloads: Sequence[RasterPayload],
    stats: Sequence[dict[str, Any]],
    alignment: Sequence[dict[str, Any]],
    sanity: Sequence[dict[str, Any]],
    pairwise: Sequence[dict[str, Any]],
    contrast: Sequence[dict[str, Any]],
) -> str:
    """Return the final one-cell raster QA decision status."""
    if any(not payload.opened for payload in payloads):
        return ONECELL_SLICE_EXECUTED_PARTIAL
    if any(row.get("status") == FAIL for row in alignment):
        return ONECELL_SLICE_EXECUTED_PARTIAL
    if any(row.get("status") == FAIL for row in sanity):
        return ONECELL_SLICE_EXECUTED_PARTIAL
    if any(row.get("sanity_status") not in {PASS, WARN} for row in stats):
        return ONECELL_SLICE_EXECUTED_PARTIAL
    if any(row.get("status") == "overhead_warming_or_suspicious" for row in pairwise):
        return ONECELL_SLICE_EXECUTED_PARTIAL
    if any(row.get("qualitative_status") == "suspicious_large_difference" for row in contrast):
        return ONECELL_SLICE_EXECUTED_PARTIAL
    return ONECELL_SLICE_EXECUTED_PASS


def write_report(
    path: Path,
    config: dict[str, Any],
    decision_status: str,
    raster_qa_status: str,
    inventory: Sequence[dict[str, Any]],
    stats: Sequence[dict[str, Any]],
    hourly: Sequence[dict[str, Any]],
    pairwise: Sequence[dict[str, Any]],
    contrast: Sequence[dict[str, Any]],
    alignment: Sequence[dict[str, Any]],
    sanity: Sequence[dict[str, Any]],
    five_hour_summary: Sequence[dict[str, Any]],
    f3a_anchor: Sequence[dict[str, Any]],
    next_action: str,
) -> None:
    """Write the F3b Markdown QA report."""
    opened = sum(1 for row in inventory if row.get("opened_for_qa") == YES)
    delta_summary = five_hour_delta_summary_rows(pairwise)
    lines = [
        "# B8.5-F3b One-Cell Full-Slice Report",
        "",
        f"Generated: {datetime_stamp()}",
        "",
        "## Decision",
        "",
        f"- Status: `{decision_status}`",
        f"- Raster QA status: `{raster_qa_status}`",
        f"- Raster count opened: `{opened}/{onecell(config)['expected_run_count']}`",
        f"- Alignment status: `{alignment_status(alignment)}`",
        f"- Next action: `{next_action}`",
        "",
        "## Read/Write Boundary",
        "",
        "Codex/Python did not run QGIS/SOLWEIG. Raster QA reads local `Tmrt_average.tif` contents only after a successful human-run postrun validator. It writes no raster, image, GeoTIFF, PNG, clipped raster, or large array output. It does not copy/open `svfs.zip`.",
        "",
        "## Raster Inventory",
        "",
        markdown_table(inventory, ["run_id", "forcing_day_id", "hour_sgt", "scenario", "exists", "file_size_bytes", "crs", "shape", "opened_for_qa"], max_rows=25),
        "",
        "## Per-Raster Tmrt Stats",
        "",
        markdown_table(stats, ["run_id", "valid_pixel_count", "nodata_fraction", "mean_c", "p50_c", "p90_c", "p95_c", "max_c", "sanity_status"], max_rows=25),
        "",
        "## Hourly Profile",
        "",
        markdown_table(hourly, ["forcing_day_id", "scenario", "hour_sgt", "mean_c", "p50_c", "p90_c", "p95_c", "max_c"], max_rows=25),
        "",
        "## Base-vs-Overhead Delta By Hour",
        "",
        "Delta is `overhead_as_canopy - base`; this is a Tmrt sensitivity check, not WBGT.",
        "",
        markdown_table(pairwise, ["forcing_day_id", "hour_sgt", "mean_delta_c", "p50_delta_c", "p90_delta_c", "p95_delta_c", "pct_pixels_delta_lt_minus_1", "pct_pixels_delta_gt_1", "status"], max_rows=25),
        "",
        "## Forcing-Day Contrast By Hour",
        "",
        "Contrast is `FD02 - FD01` for the same scenario/hour.",
        "",
        markdown_table(contrast, ["scenario", "hour_sgt", "mean_difference_c", "p50_difference_c", "p90_difference_c", "p95_difference_c", "qualitative_status"], max_rows=25),
        "",
        "## One-Cell Summary",
        "",
        markdown_table(five_hour_summary, ["forcing_day_id", "scenario", "five_hour_mean_p90_c", "hour_of_max_p90", "max_p90_c"]),
        "",
        "## Five-Hour Mean Delta P90",
        "",
        markdown_table(delta_summary, ["forcing_day_id", "five_hour_mean_delta_p90_c", "hours_included"]),
        "",
        "## F3a Hour-13 Anchor",
        "",
        markdown_table(f3a_anchor, ["forcing_day_id", "scenario", "f3a_h13_p90_c", "f3b_h13_p90_c", "difference_c", "status"]),
        "",
        "## Alignment QA",
        "",
        markdown_table(alignment, CHECK_FIELDS),
        "",
        "## Sanity Checks",
        "",
        markdown_table(sanity, CHECK_FIELDS, max_rows=80),
        "",
        "## Claim Boundaries",
        "",
        "- This is not B9.",
        "- This is not local WBGT.",
        "- This is not risk.",
        "- This is not full 480.",
        "- No Tmrt-to-WBGT conversion was performed.",
        "- Full 480 remains blocked until this one-cell full slice passes.",
    ]
    write_text(path, "\n".join(lines) + "\n")


def datetime_stamp() -> str:
    """Return a local timestamp for reports."""
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run(config_path: Path) -> RasterQaResult:
    """Run F3b raster QA or NOT_RUN_YET placeholder mode."""
    config = read_config(repo_path(config_path))
    outputs = config["outputs"]
    manifest_rows = read_csv_rows(repo_path(outputs["manifest"]))
    postrun_rows = read_csv_rows(repo_path(outputs["postrun_validation"]))
    reason = "Postrun validation has not confirmed 20/20 successful human runs."
    if not postrun_ready_for_content_qa(config, postrun_rows):
        return placeholder_outputs(config, reason)

    thresholds = [float(value) for value in onecell(config)["thresholds_c"]]
    plausible_min = float(onecell(config)["plausible_tmrt_min_c"])
    plausible_max = float(onecell(config)["plausible_tmrt_max_c"])
    payloads = [read_raster_payload(row) for row in manifest_rows]
    inventory = [inventory_row(payload) for payload in payloads]
    stats = [raster_stats_row(payload, thresholds, plausible_min, plausible_max) for payload in payloads]
    hourly = hourly_profile_rows(stats)
    pairwise = pairwise_delta_rows(config, payloads)
    contrast = forcing_day_contrast_rows(config, payloads)
    alignment = alignment_rows(config, payloads)
    sanity = sanity_rows(config, payloads, stats, pairwise, contrast, hourly)
    five_hour_summary = five_hour_summary_rows(hourly)
    f3a_anchor = f3a_anchor_rows(config, hourly)
    decision = decide_status(payloads, stats, alignment, sanity, pairwise, contrast)
    raster_qa_status = PASS if decision == ONECELL_SLICE_EXECUTED_PASS else ONECELL_SLICE_EXECUTED_PARTIAL
    next_action = "Full 480 may be reviewed only after claim-boundary review." if decision == ONECELL_SLICE_EXECUTED_PASS else "Inspect one-cell raster QA before any wider execution."

    write_csv_rows(repo_path(outputs["raster_inventory"]), inventory, RASTER_INVENTORY_FIELDS)
    write_csv_rows(repo_path(outputs["raster_stats"]), stats, raster_stats_fields(thresholds))
    write_csv_rows(repo_path(outputs["hourly_profile"]), hourly, HOURLY_PROFILE_FIELDS)
    write_csv_rows(repo_path(outputs["pairwise_delta_by_hour"]), pairwise, PAIRWISE_FIELDS)
    write_csv_rows(repo_path(outputs["forcing_day_contrast_by_hour"]), contrast, FORCING_CONTRAST_FIELDS)
    write_csv_rows(repo_path(outputs["alignment_qa"]), alignment, CHECK_FIELDS)
    write_csv_rows(repo_path(outputs["sanity_checks"]), sanity, CHECK_FIELDS)
    write_report(
        repo_path(outputs["onecell_report"]),
        config,
        decision,
        raster_qa_status,
        inventory,
        stats,
        hourly,
        pairwise,
        contrast,
        alignment,
        sanity,
        five_hour_summary,
        f3a_anchor,
        next_action,
    )
    ready_count = precheck_ready_count(config)
    write_status_report(
        repo_path(outputs["status"]),
        config,
        decision,
        len(manifest_rows),
        ready_count,
        "20/20_EXECUTED_OUTPUTS_VALID",
        raster_qa_status,
        next_action,
    )
    return RasterQaResult(
        decision_status=decision,
        manifest_run_count=len(manifest_rows),
        pre_execution_ready_count=ready_count,
        postrun_status="20/20_EXECUTED_OUTPUTS_VALID",
        raster_qa_status=raster_qa_status,
        raster_count_opened=sum(1 for payload in payloads if payload.opened),
        alignment_status=alignment_status(alignment),
        files_created=all_lane_paths(config),
    )


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
    "shape",
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
    """Return raster stats fieldnames including configured thresholds."""
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
    fields.extend([f"pct_ge_{int(threshold)}" for threshold in thresholds])
    fields.extend(["sanity_status", "sanity_notes"])
    return fields


HOURLY_PROFILE_FIELDS = ["forcing_day_id", "scenario", "hour_sgt", "mean_c", "p50_c", "p90_c", "p95_c", "max_c", "notes"]

PAIRWISE_FIELDS = [
    "forcing_day_id",
    "hour_sgt",
    "mean_delta_c",
    "p50_delta_c",
    "p90_delta_c",
    "p95_delta_c",
    "min_delta_c",
    "max_delta_c",
    "pct_pixels_delta_lt_minus_1",
    "pct_pixels_delta_lt_minus_5",
    "pct_pixels_delta_gt_1",
    "valid_overlap_pixels",
    "status",
    "notes",
]

FORCING_CONTRAST_FIELDS = [
    "scenario",
    "hour_sgt",
    "fd01_forcing_day_id",
    "fd02_forcing_day_id",
    "contrast_direction",
    "mean_difference_c",
    "p50_difference_c",
    "p90_difference_c",
    "p95_difference_c",
    "min_difference_c",
    "max_difference_c",
    "valid_overlap_pixels",
    "qualitative_status",
    "notes",
]

CHECK_FIELDS = ["check_name", "status", "value", "details"]


def main() -> int:
    """Parse CLI args and run F3b raster QA."""
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate B8.5-F3b one-cell full-slice raster QA. Before human "
            "execution it writes NOT_RUN_YET placeholders and opens no rasters; "
            "after postrun validation it reads only the 20 expected local "
            "Tmrt_average.tif rasters and writes compact CSV/Markdown summaries."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="F3b YAML config path.")
    args = parser.parse_args()
    try:
        result = run(args.config)
    except Exception as exc:
        print(f"Status: {FAILED}")
        print(f"Error: {exc}")
        return 1
    print(f"Status: {result.decision_status}")
    print(f"Manifest run count: {result.manifest_run_count}")
    print(f"Pre-execution ready count: {result.pre_execution_ready_count}")
    print(f"Postrun status: {result.postrun_status}")
    print(f"Raster QA status: {result.raster_qa_status}")
    print(f"Raster count opened: {result.raster_count_opened}")
    print(f"Alignment status: {result.alignment_status}")
    print("QGIS/SOLWEIG executed by Codex: no")
    print("Raster outputs written: no")
    print("Files created:")
    for path in result.files_created:
        print(f"- {rel(path)}")
    return 0 if result.decision_status in {READY_FOR_HUMAN_ONECELL_SLICE, ONECELL_SLICE_EXECUTED_PASS} else 2


if __name__ == "__main__":
    raise SystemExit(main())
