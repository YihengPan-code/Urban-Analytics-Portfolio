from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import box


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pick_id_column(gdf: gpd.GeoDataFrame) -> str:
    for col in ["cell_id", "grid_id", "id"]:
        if col in gdf.columns:
            return col
    raise KeyError("Could not find cell id column among cell_id/grid_id/id")


def square_around_centroid(geom, size_m: float):
    c = geom.centroid
    h = size_m / 2.0
    return box(c.x - h, c.y - h, c.x + h, c.y + h)


def safe_name(cell_id: str, typology: str) -> str:
    typ = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in typology)
    return f"{cell_id}_{typ}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Create v12 SOLWEIG typology tile folders and metadata.")
    ap.add_argument("--config", default="configs/v12/v12_solweig_typology_config.example.json")
    args = ap.parse_args()

    cfg = read_json(Path(args.config))
    crs = cfg.get("crs", "EPSG:3414")
    paths = cfg["paths"]
    tile_root = Path(paths["v12_tile_root"])
    tile_root.mkdir(parents=True, exist_ok=True)

    grid = gpd.read_file(paths["grid_geojson"]).to_crs(crs)
    id_col = pick_id_column(grid)
    grid[id_col] = grid[id_col].astype(str)

    cells = cfg["core8_cells"]
    rows = []
    tile_geoms = []
    buffered_geoms = []
    focus_geoms = []

    for idx, cell in enumerate(cells, start=1):
        cell_id = cell["cell_id"]
        match = grid[grid[id_col].eq(cell_id)]
        if match.empty:
            raise ValueError(f"Cell not found in grid: {cell_id}")

        focus = match.iloc[[0]].copy()
        typology = cell["typology_label"]
        tile_id = f"V12C{idx:02d}_{safe_name(cell_id, typology)}"
        tile_dir = tile_root / tile_id
        tile_dir.mkdir(parents=True, exist_ok=True)

        tile_geom = square_around_centroid(focus.geometry.iloc[0], float(cfg.get("tile_size_m", 500)))
        buffered_geom = square_around_centroid(focus.geometry.iloc[0], float(cfg.get("tile_size_m", 500)) + 2 * float(cfg.get("buffer_m", 100)))

        focus_out = focus.copy()
        focus_out["tile_id"] = tile_id
        focus_out["typology_label"] = typology
        focus_out["pilot_tier"] = cell.get("pilot_tier", "core")
        focus_out.to_file(tile_dir / "focus_cell.geojson", driver="GeoJSON")

        tile_gdf = gpd.GeoDataFrame([{
            "tile_id": tile_id,
            "cell_id": cell_id,
            "typology_label": typology,
            "tile_dir": tile_dir.as_posix(),
            "geometry": tile_geom,
        }], crs=crs)
        tile_gdf.to_file(tile_dir / "tile_boundary.geojson", driver="GeoJSON")

        buf_gdf = tile_gdf.copy()
        buf_gdf["geometry"] = [buffered_geom]
        buf_gdf.to_file(tile_dir / "tile_boundary_buffered.geojson", driver="GeoJSON")

        for sub in ["svf_base", "svf_overhead", "solweig_base", "solweig_overhead_as_canopy"]:
            (tile_dir / sub).mkdir(parents=True, exist_ok=True)

        rows.append({
            "tile_id": tile_id,
            "cell_id": cell_id,
            "typology_label": typology,
            "typology_label_cn": cell.get("typology_label_cn", ""),
            "pilot_tier": cell.get("pilot_tier", "core"),
            "tile_dir": tile_dir.as_posix(),
            "focus_cell_geojson": (tile_dir / "focus_cell.geojson").as_posix(),
            "tile_boundary_geojson": (tile_dir / "tile_boundary.geojson").as_posix(),
            "tile_boundary_buffered_geojson": (tile_dir / "tile_boundary_buffered.geojson").as_posix(),
        })
        tile_geoms.append(tile_gdf.iloc[0])
        buffered_geoms.append(buf_gdf.iloc[0])
        focus_geoms.append(focus_out.iloc[0])

    meta = pd.DataFrame(rows)
    meta_path = tile_root / "v12_typology_tile_metadata.csv"
    meta.to_csv(meta_path, index=False)

    gpd.GeoDataFrame(tile_geoms, crs=crs).to_file(tile_root / "v12_typology_tiles.geojson", driver="GeoJSON")
    gpd.GeoDataFrame(buffered_geoms, crs=crs).to_file(tile_root / "v12_typology_tiles_buffered.geojson", driver="GeoJSON")
    print(f"[OK] wrote {meta_path}")
    print(f"[OK] tile count: {len(meta)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
