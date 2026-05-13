#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json
from pathlib import Path
from typing import List, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask


def read_json(p):
    with open(p, 'r', encoding='utf-8') as f: return json.load(f)

def ensure_parent(p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)


def read_gdf(path, crs):
    gdf=gpd.read_file(path)
    if gdf.crs is None: gdf=gdf.set_crs(crs)
    else: gdf=gdf.to_crs(crs)
    gdf=gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    return gdf


def raster_building_area_by_polygons(raster_path: Path, polys: gpd.GeoDataFrame, id_col: str, threshold: float=0.5) -> pd.DataFrame:
    rows=[]
    with rasterio.open(raster_path) as src:
        pix_area=abs(src.transform.a*src.transform.e)
        for _, row in polys.iterrows():
            geom=row.geometry
            try:
                out, _ = mask(src, [geom], crop=True, filled=False)
                arr = out[0]
                data = arr.compressed() if hasattr(arr, 'compressed') else arr.ravel()
                area=float((data > threshold).sum() * pix_area)
            except Exception:
                area=0.0
            rows.append({id_col: row[id_col], 'dsm_area_m2': area})
    return pd.DataFrame(rows)


def vector_area_by_polygons(ref: gpd.GeoDataFrame, polys: gpd.GeoDataFrame, id_col: str, area_name: str) -> pd.DataFrame:
    if ref.empty:
        return pd.DataFrame({id_col: polys[id_col], area_name: 0.0})
    # spatial index candidate then exact intersection, less memory than full overlay for 986 cells.
    sidx = ref.sindex
    rows=[]
    for _, prow in polys.iterrows():
        geom = prow.geometry
        cand_idx = list(sidx.query(geom, predicate='intersects'))
        total=0.0
        if cand_idx:
            cand = ref.iloc[cand_idx]
            for g in cand.geometry:
                try:
                    inter = geom.intersection(g)
                    if not inter.is_empty:
                        total += inter.area
                except Exception:
                    pass
        rows.append({id_col: prow[id_col], area_name: float(total)})
    return pd.DataFrame(rows)


def make_summary(df: pd.DataFrame, label: str) -> str:
    lines=[]
    lines.append(f'## {label}')
    lines.append(f'Rows: **{len(df)}**')
    old=df['old_dsm_area_m2'].sum()
    new=df['new_dsm_area_m2'].sum()
    osm=df['osm_area_m2'].sum()
    lines.append(f'Old DSM area sum: **{old:.1f} m²**')
    lines.append(f'Reviewed DSM area sum: **{new:.1f} m²**')
    lines.append(f'OSM area sum: **{osm:.1f} m²**')
    lines.append(f'Old vs OSM completeness: **{(old/osm if osm else np.nan):.3f}**')
    lines.append(f'Reviewed vs OSM completeness: **{(new/osm if osm else np.nan):.3f}**')
    lines.append('')
    cols=['old_vs_osm_completeness','reviewed_vs_osm_completeness','coverage_gain_vs_osm','reviewed_minus_old_dsm_area_m2']
    lines.append('Completeness distribution:')
    lines.append('```text')
    lines.append(df[cols].describe().to_string())
    lines.append('```')
    return '\n'.join(lines)


def compute_completeness(units: gpd.GeoDataFrame, id_col: str, old_dsm: Path, new_dsm: Path, osm: gpd.GeoDataFrame, threshold: float) -> pd.DataFrame:
    old_area=raster_building_area_by_polygons(old_dsm, units, id_col, threshold).rename(columns={'dsm_area_m2':'old_dsm_area_m2'})
    new_area=raster_building_area_by_polygons(new_dsm, units, id_col, threshold).rename(columns={'dsm_area_m2':'new_dsm_area_m2'})
    osm_area=vector_area_by_polygons(osm, units, id_col, 'osm_area_m2')
    out=units[[id_col]].merge(old_area,on=id_col).merge(new_area,on=id_col).merge(osm_area,on=id_col)
    denom=out['osm_area_m2'].replace({0: np.nan})
    out['old_vs_osm_completeness']=out['old_dsm_area_m2']/denom
    out['reviewed_vs_osm_completeness']=out['new_dsm_area_m2']/denom
    out['coverage_gain_vs_osm']=out['reviewed_vs_osm_completeness']-out['old_vs_osm_completeness']
    out['reviewed_minus_old_dsm_area_m2']=out['new_dsm_area_m2']-out['old_dsm_area_m2']
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config', default='configs/v10/v10_alpha3_manual_qa_config.example.json')
    args=ap.parse_args()
    cfg=read_json(args.config)
    crs=cfg.get('crs','EPSG:3414')
    inp=cfg['inputs']; out=cfg['outputs']
    threshold=float(cfg.get('raster',{}).get('height_threshold_m',0.5))

    grid=read_gdf(inp['base_grid_geojson'], crs)
    if 'cell_id' not in grid.columns:
        raise KeyError('base grid must contain cell_id')
    osm=read_gdf(inp['osm_reference_buildings_geojson'], crs)
    old_dsm=Path(inp['old_building_dsm'])
    new_dsm=Path(out['reviewed_dsm'])

    cell_df=compute_completeness(grid[['cell_id','geometry']], 'cell_id', old_dsm, new_dsm, osm, threshold)
    cell_path=Path(out['reviewed_completeness_per_cell_csv']); ensure_parent(cell_path); cell_df.to_csv(cell_path,index=False)

    tile_path=Path(inp.get('v09_tiles_buffered_geojson',''))
    tile_df=None
    if tile_path.exists():
        tiles=read_gdf(tile_path, crs)
        # Support several tile id fields.
        if 'tile_id' not in tiles.columns:
            tiles['tile_id']=[f'T{i+1:02d}' for i in range(len(tiles))]
        tile_df=compute_completeness(tiles[['tile_id','geometry']], 'tile_id', old_dsm, new_dsm, osm, threshold)
        extra=[c for c in ['tile_type','cell_id','focus_cell_id'] if c in tiles.columns]
        if extra:
            tile_df=tiles[['tile_id']+extra].merge(tile_df,on='tile_id',how='right')
        tile_out=Path(out['reviewed_completeness_per_tile_csv']); ensure_parent(tile_out); tile_df.to_csv(tile_out,index=False)

    report=Path(out['reviewed_completeness_report_md']); ensure_parent(report)
    lines=[]
    lines.append('# v1.0-alpha.3 reviewed DSM completeness gain report')
    lines.append('')
    lines.append('## Interpretation note')
    lines.append('- Completeness is calculated relative to OSM-mapped building footprint area, not absolute real-world completeness.')
    lines.append('- Ratios can exceed 1.0 because OSM is a reference layer, not ground truth.')
    lines.append('- Reviewed completeness may be slightly lower than alpha.1 if manual QA moved roof/canopy/transport shelter objects out of the ground-up building DSM; this is desirable if those objects belong in a future overhead DSM.')
    lines.append('')
    lines.append(make_summary(cell_df, 'Per-cell completeness'))
    if tile_df is not None:
        lines.append('')
        lines.append(make_summary(tile_df, 'Per-tile completeness'))
        lines.append('')
        lines.append('## Critical tile recovery')
        show_cols=[c for c in ['tile_id','tile_type','cell_id','old_dsm_area_m2','new_dsm_area_m2','osm_area_m2','old_vs_osm_completeness','reviewed_vs_osm_completeness','coverage_gain_vs_osm'] if c in tile_df.columns]
        lines.append('```text')
        lines.append(tile_df[show_cols].to_string(index=False))
        lines.append('```')
    report.write_text('\n'.join(lines), encoding='utf-8')
    print('[OK] cell completeness:', cell_path)
    if tile_df is not None: print('[OK] tile completeness:', Path(out['reviewed_completeness_per_tile_csv']))
    print('[OK] report:', report)

if __name__=='__main__':
    main()
