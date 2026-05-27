"""Aggregate B8.5-F3c N24 / 480-run raster-content QA.

Inputs:
    configs/v12/systemb_b85_f3c_n24_full_execution.yaml
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_n24_manifest.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_postrun_validation.csv
    480 local Tmrt_average.tif rasters declared by the F3c manifest, only
    after human execution and postrun validation have succeeded.

Outputs:
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_raster_inventory.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_raster_stats.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_alignment_qa.csv
    outputs/v12_surrogate/b8_5_f3c_n24/b85_f3c_sanity_checks.csv
    outputs/v12_surrogate/b8_5_f3c_n24/B8_5_F3C_STATUS.md

Saved metrics:
    Per-raster inventory, CRS/shape/transform/nodata/dtype metadata, valid
    pixel counts, nodata fractions, Tmrt percentiles, threshold exceedance
    percentages, per-cell and cross-cell alignment checks, and compact sanity
    checks.

This script does not run QGIS, run SOLWEIG, copy/open svfs.zip, create/copy/move
rasters, write raster/image/large-array outputs, create AOI-wide predictions,
compute local WBGT, create hazard_score/risk_score outputs, create System A/B
coupling outputs, perform Tmrt-to-WBGT conversion, stage, or commit. Before
human execution it writes compact NOT_RUN_YET placeholders and opens no rasters.
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
    NO,
    NOT_RUN_YET,
    N24_EXECUTED_PARTIAL,
    N24_EXECUTED_PASS,
    PASS,
    READY_FOR_HUMAN_N24,
    ROOT,
    WARN,
    YES,
    all_lane_paths,
    changed_forbidden_paths,
    clean,
    git_status_short,
    markdown_table,
    path_outside_git_and_under_local,
    read_config,
    read_csv_rows,
    rel,
    repo_path,
    write_cn_doc,
    write_csv_rows,
    write_status_report,
)


DEFAULT_CONFIG = ROOT / "configs/v12/systemb_b85_f3c_n24_full_execution.yaml"


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
    unique_cell_count: int
    pre_execution_ready_count: int
    postrun_status: str
    raster_qa_status: str
    stability_summary_status: str
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


def add_check(rows: list[dict[str, Any]], name: str, status: str, value: Any, details: str) -> None:
    """Append one compact QA check row."""
    rows.append({"check_name": name, "status": status, "value": clean(value), "details": details})


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


def postrun_ready_for_content_qa(config: dict[str, Any], rows: Sequence[dict[str, str]]) -> bool:
    """Return whether postrun validation permits raster content reads."""
    if len(rows) != int(config["expected_run_count"]):
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


def compact_postrun_status(config: dict[str, Any]) -> str:
    """Return compact postrun status from the postrun validation CSV."""
    path = repo_path(config["outputs"]["postrun_validation"])
    if not path.exists():
        return NOT_RUN_YET
    rows = read_csv_rows(path)
    if postrun_ready_for_content_qa(config, rows):
        return f"{len(rows)}/{config['expected_run_count']}_EXECUTED_OUTPUTS_VALID"
    if rows and all(clean(row.get("validation_status")) == NOT_RUN_YET for row in rows):
        return NOT_RUN_YET
    return "PARTIAL_OR_BLOCKED"


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
    thresholds = [float(value) for value in config["thresholds_c"]]
    inventory = placeholder_inventory_rows(manifest_rows)
    stats = placeholder_stats_rows(manifest_rows, thresholds)
    alignment = [
        {
            "check_name": "postrun_validation_required_before_raster_content_read",
            "status": NOT_RUN_YET,
            "value": reason,
            "details": "Raster QA does not open local rasters until postrun validation shows 480/480 success/skipped and output files exist.",
        }
    ]
    sanity = [
        {
            "check_name": "no_raster_content_opened_before_manual_execution",
            "status": PASS,
            "value": "0 rasters opened",
            "details": "This placeholder run wrote compact CSV/Markdown summaries only.",
        },
        {
            "check_name": "no_qgis_or_solweig_execution",
            "status": PASS,
            "value": "no",
            "details": "Codex/Python did not run QGIS or SOLWEIG.",
        },
        {
            "check_name": "not_b9_not_n150_not_full_aoi",
            "status": PASS,
            "value": "N24 / 480 only",
            "details": "This lane does not authorize B9, N150, or full AOI execution.",
        },
    ]
    write_csv_rows(repo_path(outputs["raster_inventory"]), inventory, RASTER_INVENTORY_FIELDS)
    write_csv_rows(repo_path(outputs["raster_stats"]), stats, raster_stats_fields(thresholds))
    write_csv_rows(repo_path(outputs["alignment_qa"]), alignment, CHECK_FIELDS)
    write_csv_rows(repo_path(outputs["sanity_checks"]), sanity, CHECK_FIELDS)
    ready_count = precheck_ready_count(config)
    manifest_count = len(manifest_rows)
    unique_cell_count = len({row["cell_id"] for row in manifest_rows})
    decision = READY_FOR_HUMAN_N24 if ready_count == int(config["expected_run_count"]) else BLOCKED_PRECHECK
    write_cn_doc(
        repo_path(outputs["canonical_note_cn"]),
        config,
        decision,
        ready_count,
        compact_postrun_status(config),
        NOT_RUN_YET,
        NOT_RUN_YET,
    )
    write_status_report(
        repo_path(outputs["status"]),
        config,
        decision,
        manifest_count,
        unique_cell_count,
        ready_count,
        compact_postrun_status(config),
        NOT_RUN_YET,
        NOT_RUN_YET,
        reason,
    )
    return RasterQaResult(
        decision_status=decision,
        manifest_run_count=manifest_count,
        unique_cell_count=unique_cell_count,
        pre_execution_ready_count=ready_count,
        postrun_status=compact_postrun_status(config),
        raster_qa_status=NOT_RUN_YET,
        stability_summary_status=NOT_RUN_YET,
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
                "sanity_status": FAIL,
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
            "sanity_status": WARN if notes else PASS,
            "sanity_notes": "none" if not notes else "; ".join(notes),
        }
    )
    for threshold in thresholds:
        pct = 100.0 * float(np.mean(values >= float(threshold)))
        base[f"pct_ge_{int(threshold)}"] = format_float(pct)
    return base


def metadata_values(payloads: Sequence[RasterPayload], key: str) -> set[str]:
    """Return distinct metadata values for opened rasters."""
    return {clean(payload.metadata.get(key)) for payload in payloads if payload.opened}


def alignment_rows(config: dict[str, Any], payloads: Sequence[RasterPayload]) -> list[dict[str, Any]]:
    """Build per-cell and cross-cell alignment QA rows."""
    rows: list[dict[str, Any]] = []
    opened = [payload for payload in payloads if payload.opened]
    add_check(rows, "all_480_rasters_opened", PASS if len(opened) == int(config["expected_run_count"]) else FAIL, f"{len(opened)}/{config['expected_run_count']}", "All expected local Tmrt rasters must open for content QA.")
    for cell_id in sorted({payload.run["cell_id"] for payload in payloads}):
        group = [payload for payload in opened if payload.run["cell_id"] == cell_id]
        add_check(rows, f"{cell_id}:opened_raster_count", PASS if len(group) == 20 else FAIL, f"{len(group)}/20", "Each N24 cell must have 20 rasters.")
        for label in ("crs", "shape", "transform", "nodata", "dtype"):
            values = metadata_values(group, label)
            add_check(
                rows,
                f"{cell_id}:same_{label}",
                PASS if len(values) == 1 else FAIL,
                "; ".join(sorted(values)),
                f"Rasters within each cell must share {label}.",
            )
    for label in ("crs", "dtype"):
        values = metadata_values(opened, label)
        add_check(
            rows,
            f"all_cells_same_{label}",
            PASS if len(values) == 1 else FAIL,
            "; ".join(sorted(values)),
            f"Across cells, {label} should match.",
        )
    transform_values = metadata_values(opened, "transform")
    add_check(
        rows,
        "all_cells_transform_may_differ",
        PASS,
        f"{len(transform_values)} distinct transforms",
        "Across cells, transform may differ; within-cell transform identity is checked separately.",
    )
    local_paths_ok = all(path_outside_git_and_under_local(config, Path(payload.run["expected_tmrt_path"])) for payload in payloads)
    add_check(rows, "output_path_outside_git_worktree", PASS if local_paths_ok else FAIL, config["local_solweig_output_root"], "Expected output paths must remain local-only and outside Git.")
    add_check(rows, "no_raster_output_written_by_qa", PASS, NO, "QA writes no raster/image/array outputs.")
    return rows


def sanity_rows(
    config: dict[str, Any],
    payloads: Sequence[RasterPayload],
    stats: Sequence[dict[str, Any]],
    alignment: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build F3c raster sanity checks."""
    rows: list[dict[str, Any]] = []
    add_check(rows, "expected_run_count", PASS if len(payloads) == int(config["expected_run_count"]) else FAIL, f"{len(payloads)}/{config['expected_run_count']}", "F3c manifest must remain exactly 480 rows.")
    add_check(rows, "expected_cell_count", PASS if len({payload.run["cell_id"] for payload in payloads}) == int(config["expected_cell_count"]) else FAIL, len({payload.run["cell_id"] for payload in payloads}), "F3c manifest must remain exactly 24 cells.")
    add_check(rows, "no_qgis_or_solweig_execution_by_codex", PASS, NO, "Codex/Python did not run QGIS/SOLWEIG.")
    add_check(rows, "no_raster_image_or_array_output_written", PASS, NO, "No raster, image, or large-array outputs are written.")
    add_check(rows, "not_b9_not_wbgt_not_risk", PASS, "stability evidence only", "No B9, local WBGT, hazard_score, risk_score, or System A/B coupling output is created.")
    forbidden = changed_forbidden_paths(git_status_short())
    add_check(rows, "no_forbidden_repo_files_changed", PASS if not forbidden else FAIL, "none" if not forbidden else "; ".join(forbidden), "Forbidden rasters, svfs.zip, raw archives, and large forecast CSVs must remain untouched.")
    add_check(rows, "alignment_checks_pass", PASS if all(row.get("status") == PASS for row in alignment) else FAIL, "PASS" if all(row.get("status") == PASS for row in alignment) else "FAIL", "All alignment checks must pass.")
    for row in stats:
        run_id = row.get("run_id", "")
        add_check(rows, f"{run_id}:valid_pixel_count_gt_0", PASS if int(clean(row.get("valid_pixel_count")) or "0") > 0 else FAIL, row.get("valid_pixel_count", ""), "Raster must contain at least one valid Tmrt pixel.")
        add_check(rows, f"{run_id}:nodata_fraction_lt_0_5", PASS if float(clean(row.get("nodata_fraction")) or "1") < 0.5 else FAIL, row.get("nodata_fraction", ""), "Nodata fraction should remain below 0.5.")
        status = clean(row.get("sanity_status"))
        add_check(rows, f"{run_id}:per_raster_sanity_status", PASS if status == PASS else WARN if status == WARN else FAIL, status, clean(row.get("sanity_notes")))
    return rows


def alignment_status(alignment: Sequence[dict[str, Any]]) -> str:
    """Return compact alignment status."""
    if alignment and any(row.get("status") == NOT_RUN_YET for row in alignment):
        return NOT_RUN_YET
    return PASS if alignment and all(row.get("status") == PASS for row in alignment) else FAIL


def decide_status(payloads: Sequence[RasterPayload], stats: Sequence[dict[str, Any]], alignment: Sequence[dict[str, Any]], sanity: Sequence[dict[str, Any]]) -> str:
    """Return the final N24 raster QA decision status."""
    if any(not payload.opened for payload in payloads):
        return N24_EXECUTED_PARTIAL
    if any(row.get("status") == FAIL for row in alignment):
        return N24_EXECUTED_PARTIAL
    if any(row.get("status") == FAIL for row in sanity):
        return N24_EXECUTED_PARTIAL
    if any(row.get("sanity_status") not in {PASS, WARN} for row in stats):
        return N24_EXECUTED_PARTIAL
    return N24_EXECUTED_PASS


def run(config_path: Path) -> RasterQaResult:
    """Run F3c raster QA or NOT_RUN_YET placeholder mode."""
    config = read_config(repo_path(config_path))
    outputs = config["outputs"]
    manifest_rows = read_csv_rows(repo_path(outputs["manifest"]))
    postrun_rows = read_csv_rows(repo_path(outputs["postrun_validation"]))
    reason = "Postrun validation has not confirmed 480/480 successful or skipped-existing human runs."
    if not postrun_ready_for_content_qa(config, postrun_rows):
        return placeholder_outputs(config, reason)

    thresholds = [float(value) for value in config["thresholds_c"]]
    plausible_min = float(config["plausible_tmrt_min_c"])
    plausible_max = float(config["plausible_tmrt_max_c"])
    payloads = [read_raster_payload(row) for row in manifest_rows]
    inventory = [inventory_row(payload) for payload in payloads]
    stats = [raster_stats_row(payload, thresholds, plausible_min, plausible_max) for payload in payloads]
    alignment = alignment_rows(config, payloads)
    sanity = sanity_rows(config, payloads, stats, alignment)
    decision = decide_status(payloads, stats, alignment, sanity)
    raster_qa_status = PASS if decision == N24_EXECUTED_PASS else N24_EXECUTED_PARTIAL
    ready_count = precheck_ready_count(config)
    unique_cell_count = len({row["cell_id"] for row in manifest_rows})
    postrun_status = f"{len(postrun_rows)}/{config['expected_run_count']}_EXECUTED_OUTPUTS_VALID"
    notes = "Raster QA passed; first-pass stability summary still required." if decision == N24_EXECUTED_PASS else "Inspect raster QA before any wider execution."

    write_csv_rows(repo_path(outputs["raster_inventory"]), inventory, RASTER_INVENTORY_FIELDS)
    write_csv_rows(repo_path(outputs["raster_stats"]), stats, raster_stats_fields(thresholds))
    write_csv_rows(repo_path(outputs["alignment_qa"]), alignment, CHECK_FIELDS)
    write_csv_rows(repo_path(outputs["sanity_checks"]), sanity, CHECK_FIELDS)
    write_cn_doc(
        repo_path(outputs["canonical_note_cn"]),
        config,
        decision,
        ready_count,
        postrun_status,
        raster_qa_status,
        "PENDING_STABILITY_SUMMARY" if decision == N24_EXECUTED_PASS else NOT_RUN_YET,
    )
    write_status_report(
        repo_path(outputs["status"]),
        config,
        decision,
        len(manifest_rows),
        unique_cell_count,
        ready_count,
        postrun_status,
        raster_qa_status,
        "PENDING_STABILITY_SUMMARY" if decision == N24_EXECUTED_PASS else NOT_RUN_YET,
        notes,
    )
    return RasterQaResult(
        decision_status=decision,
        manifest_run_count=len(manifest_rows),
        unique_cell_count=unique_cell_count,
        pre_execution_ready_count=ready_count,
        postrun_status=postrun_status,
        raster_qa_status=raster_qa_status,
        stability_summary_status="PENDING_STABILITY_SUMMARY" if decision == N24_EXECUTED_PASS else NOT_RUN_YET,
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


CHECK_FIELDS = ["check_name", "status", "value", "details"]


def main() -> int:
    """Parse CLI args and run F3c raster QA."""
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate B8.5-F3c N24 raster QA. Before human execution it writes "
            "NOT_RUN_YET placeholders and opens no rasters; after postrun "
            "validation it reads only the 480 expected local Tmrt_average.tif "
            "rasters and writes compact CSV summaries."
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
    print(f"Raster count opened: {result.raster_count_opened}")
    print(f"Alignment status: {result.alignment_status}")
    print("QGIS/SOLWEIG executed by Codex: no")
    print("Raster outputs written: no")
    print("Files created:")
    for path in result.files_created:
        print(f"- {rel(path)}")
    return 0 if result.decision_status in {READY_FOR_HUMAN_N24, N24_EXECUTED_PASS} else 2


if __name__ == "__main__":
    raise SystemExit(main())
