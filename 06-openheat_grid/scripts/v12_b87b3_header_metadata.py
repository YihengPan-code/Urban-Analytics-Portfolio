"""Inspect allowed raster headers without reading raster pixels.

Inputs:
    b87b3_canonical_source_set.csv.
Outputs:
    b87b3_header_metadata.csv.
Saved metrics:
    CRS, bounds, transform, width, height, resolution, dtype, nodata, and band
    count for raster sources with user_decision=use when header-only inspection
    is available. If rasterio/header access is unavailable, rows are marked
    HEADER_NOT_CHECKED. The script never calls dataset.read(), never opens
    svfs.zip, and never writes rasters.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from v12_b87b3_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    clean,
    load_config,
    metadata_for_path,
    out_path,
    read_csv_rows,
    repo_path,
    write_csv_rows,
)


def header_not_checked(reason: str) -> dict[str, Any]:
    """Return a HEADER_NOT_CHECKED metadata payload."""
    return {
        "header_status": "HEADER_NOT_CHECKED",
        "metadata_method": "metadata_only_no_pixel_read",
        "crs": "",
        "bounds": "",
        "transform": "",
        "width": "",
        "height": "",
        "resolution_x": "",
        "resolution_y": "",
        "dtype": "",
        "nodata": "",
        "band_count": "",
        "header_error": reason,
    }


def inspect_header(path: str) -> dict[str, Any]:
    """Inspect raster header only; never read band data."""
    if not clean(path):
        return header_not_checked("missing source path")
    meta = metadata_for_path(path)
    if meta["exists_by_metadata"] != "yes":
        return header_not_checked("source path missing by metadata")
    try:
        import rasterio  # type: ignore
    except Exception as exc:
        return header_not_checked("rasterio unavailable: " + clean(exc))
    try:
        with rasterio.open(repo_path(path)) as dataset:  # header-only metadata access; no dataset.read().
            bounds = dataset.bounds
            return {
                "header_status": "HEADER_OK",
                "metadata_method": "rasterio_open_header_only_no_read",
                "crs": clean(dataset.crs),
                "bounds": f"{bounds.left},{bounds.bottom},{bounds.right},{bounds.top}",
                "transform": clean(dataset.transform),
                "width": dataset.width,
                "height": dataset.height,
                "resolution_x": dataset.res[0] if dataset.res else "",
                "resolution_y": dataset.res[1] if dataset.res else "",
                "dtype": "|".join(clean(dtype) for dtype in dataset.dtypes),
                "nodata": "|".join(clean(value) for value in dataset.nodatavals),
                "band_count": dataset.count,
                "header_error": "",
            }
    except Exception as exc:
        return header_not_checked(clean(exc))


def run(config_path: Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    """Run header-only metadata inspection."""
    config = load_config(config_path)
    rows: list[dict[str, Any]] = []
    for source in read_csv_rows(out_path(config, "b87b3_canonical_source_set.csv")):
        if clean(source.get("user_decision")) != "use":
            continue
        source_kind = clean(source.get("source_kind"))
        path = clean(source.get("canonical_path"))
        if source_kind == "grid_geometry":
            continue
        header = inspect_header(path) if config.get("header_only_allowed") is True else header_not_checked("header_only_allowed=false")
        rows.append(
            {
                "source_kind": source_kind,
                "scenario": clean(source.get("scenario")),
                "source_path": path,
                "user_decision": clean(source.get("user_decision")),
                "lock_status": clean(source.get("lock_status")),
                **header,
                "no_pixel_read": "true",
                "no_raster_write": "true",
                "claim_boundary": CLAIM_BOUNDARY,
            }
        )
    write_csv_rows(
        out_path(config, "b87b3_header_metadata.csv"),
        rows,
        [
            "source_kind",
            "scenario",
            "source_path",
            "user_decision",
            "lock_status",
            "header_status",
            "metadata_method",
            "crs",
            "bounds",
            "transform",
            "width",
            "height",
            "resolution_x",
            "resolution_y",
            "dtype",
            "nodata",
            "band_count",
            "header_error",
            "no_pixel_read",
            "no_raster_write",
            "claim_boundary",
        ],
    )
    return rows


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Inspect allowed raster headers only and write b87b3_header_metadata.csv; "
            "never reads raster pixels or writes rasters."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(f"header_metadata_rows={len(run(args.config))}")


if __name__ == "__main__":
    main()
