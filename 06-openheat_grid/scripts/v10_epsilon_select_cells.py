from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import box


def read_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", str(text)).strip("_")


def optional_csv(path: str | None) -> pd.DataFrame | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return pd.read_csv(p)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v10/v10_epsilon_solweig_config.example.json")
    args = ap.parse_args()
    cfg = read_json(Path(args.config))
    crs = cfg.get("crs", "EPSG:3414")
    tile_size = float(cfg.get("tile_size_m", 500))
    buffer_m = float(cfg.get("buffer_m", 100))
    paths = cfg["paths"]

    tile_root = Path(paths["tile_root"])
    out_root = Path(paths["output_root"])
    tile_root.mkdir(parents=True, exist_ok=True)
    out_root.mkdir(parents=True, exist_ok=True)

    grid = gpd.read_file(paths["grid_geojson"]).to_crs(crs)
    if "cell_id" not in grid.columns:
        raise KeyError("grid_geojson must contain a cell_id column")

    gamma = optional_csv(paths.get("v10_gamma_hotspot_csv"))
    delta = optional_csv(paths.get("v10_delta_rank_comparison_csv"))

    rows = []
    tile_features = []
    tile_buffer_features = []
    for i, item in enumerate(cfg["selected_cells"], start=1):
        cid = item["cell_id"]
        role = item.get("role", "selected_cell")
        reason = item.get("selection_reason", "")
        hit = grid[grid["cell_id"].astype(str) == str(cid)]
        if hit.empty:
            raise ValueError(f"Selected cell not found in grid: {cid}")
        geom = hit.geometry.iloc[0]
        c = geom.centroid
        half = tile_size / 2.0
        tile_geom = box(c.x - half, c.y - half, c.x + half, c.y + half)
        tile_buffer_geom = tile_geom.buffer(buffer_m, cap_style=3, join_style=2)
        tile_id = f"E{i:02d}_{safe(role)}_{safe(cid)}"
        tile_dir = tile_root / tile_id
        base_dir = tile_dir / "solweig_base"
        oh_dir = tile_dir / "solweig_overhead"
        base_dir.mkdir(parents=True, exist_ok=True)
        oh_dir.mkdir(parents=True, exist_ok=True)

        row = {
            "tile_id": tile_id,
            "cell_id": cid,
            "role": role,
            "selection_reason": reason,
            "tile_dir": str(tile_dir),
            "solweig_base_dir": str(base_dir),
            "solweig_overhead_dir": str(oh_dir),
            "centroid_x": c.x,
            "centroid_y": c.y,
            "tile_size_m": tile_size,
            "buffer_m": buffer_m,
        }
        # attach selected useful ranking fields if available
        for df in [gamma, delta]:
            if df is not None and "cell_id" in df.columns:
                eh = df[df["cell_id"].astype(str) == str(cid)]
                if not eh.empty:
                    for col, val in eh.iloc[0].items():
                        if col != "geometry" and col not in row:
                            row[col] = val
        rows.append(row)
        tile_features.append({**row, "geometry": tile_geom})
        tile_buffer_features.append({**row, "geometry": tile_buffer_geom})

        # per-tile files
        gpd.GeoDataFrame([{**row}], geometry=[geom], crs=crs).to_file(tile_dir / "focus_cell.geojson", driver="GeoJSON")
        gpd.GeoDataFrame([{**row}], geometry=[tile_geom], crs=crs).to_file(tile_dir / "tile_boundary.geojson", driver="GeoJSON")
        gpd.GeoDataFrame([{**row}], geometry=[tile_buffer_geom], crs=crs).to_file(tile_dir / "tile_boundary_buffered.geojson", driver="GeoJSON")
        (tile_dir / "README_SOLWEIG_STEPS.txt").write_text(
            f"OpenHeat v10-epsilon SOLWEIG tile\n\nCell: {cid}\nRole: {role}\nReason: {reason}\n\n"
            "After `v10_epsilon_prepare_rasters.py`, run two SOLWEIG scenarios in QGIS/UMEP:\n\n"
            "Scenario A: solweig_base\n"
            "  Building DSM: dsm_buildings_tile.tif\n"
            "  Vegetation DSM: dsm_vegetation_tile_base.tif\n\n"
            "Scenario B: solweig_overhead\n"
            "  Building DSM: dsm_buildings_tile.tif\n"
            "  Vegetation DSM: dsm_vegetation_tile_overhead.tif\n\n"
            "Save Tmrt rasters into the corresponding solweig_* folder. Filenames must include HHMM, e.g. Tmrt_20260320_1300.tif.\n",
            encoding="utf-8",
        )

    meta = pd.DataFrame(rows)
    meta.to_csv(tile_root / "v10_epsilon_tile_metadata.csv", index=False)
    gpd.GeoDataFrame(tile_features, geometry="geometry", crs=crs).to_file(tile_root / "v10_epsilon_tiles.geojson", driver="GeoJSON")
    gpd.GeoDataFrame(tile_buffer_features, geometry="geometry", crs=crs).to_file(tile_root / "v10_epsilon_tiles_buffered.geojson", driver="GeoJSON")

    report = out_root / "v10_epsilon_tile_selection_report.md"
    report.write_text(
        "# v10-epsilon selected-cell tile selection report\n\n"
        f"Selected cells: **{len(meta)}**\n\n"
        f"Tile size: **{tile_size:.0f} m**; buffer: **{buffer_m:.0f} m**\n\n"
        + meta[["tile_id", "cell_id", "role", "selection_reason"]].to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )
    print(f"[OK] metadata: {tile_root / 'v10_epsilon_tile_metadata.csv'}")
    print(f"[OK] report: {report}")


if __name__ == "__main__":
    main()
