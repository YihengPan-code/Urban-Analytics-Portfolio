#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json
from pathlib import Path
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from rasterio.enums import MergeAlg


def read_json(p):
    with open(p, 'r', encoding='utf-8') as f: return json.load(f)

def ensure_parent(p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config', default='configs/v10/v10_alpha3_manual_qa_config.example.json')
    args=ap.parse_args()
    cfg=read_json(args.config)
    crs=cfg.get('crs','EPSG:3414')
    reviewed=Path(cfg['outputs']['reviewed_canonical_geojson'])
    template=Path(cfg['inputs']['old_building_dsm'])
    out_dsm=Path(cfg['outputs']['reviewed_dsm'])
    out_report=Path(cfg['outputs']['reviewed_raster_QA_md'])
    threshold=float(cfg.get('raster',{}).get('height_threshold_m',0.5))
    all_touched=bool(cfg.get('raster',{}).get('all_touched', False))

    b=gpd.read_file(reviewed)
    if b.crs is None: b=b.set_crs(crs)
    else: b=b.to_crs(crs)
    b=b[b.geometry.notna() & ~b.geometry.is_empty].copy()
    b['height_m']=pd.to_numeric(b['height_m'], errors='coerce').fillna(0)
    b=b[b['height_m']>0].copy().sort_values('height_m', ascending=True)

    with rasterio.open(template) as src:
        profile=src.profile.copy()
        transform=src.transform
        out_shape=(src.height, src.width)
        out_crs=src.crs

    shapes=((geom, float(h)) for geom,h in zip(b.geometry, b['height_m']))
    arr=rasterize(
        shapes=shapes,
        out_shape=out_shape,
        transform=transform,
        fill=0.0,
        dtype='float32',
        all_touched=all_touched,
        merge_alg=MergeAlg.replace,
    )

    profile.update(driver='GTiff', count=1, dtype='float32', compress='deflate')
    if 'nodata' in profile:
        profile.pop('nodata', None)
    ensure_parent(out_dsm)
    with rasterio.open(out_dsm, 'w', **profile) as dst:
        dst.write(arr.astype('float32'), 1)

    pix_area=abs(transform.a*transform.e)
    n_bldg=int((arr>threshold).sum())
    area=float(n_bldg*pix_area)
    vals=arr[arr>threshold]
    ensure_parent(out_report)
    lines=[]
    lines.append('# v1.0-alpha.3 reviewed DSM rasterization QA')
    lines.append('')
    lines.append(f'Output: `{out_dsm}`')
    lines.append(f'Shape: **{out_shape[0]} × {out_shape[1]}**')
    lines.append(f'Resolution: **{abs(transform.a)} m**')
    lines.append('Raster nodata metadata: **None**')
    lines.append('')
    lines.append('## Flat-terrain convention')
    lines.append('- `0.0` is valid ground / no-building height, not nodata.')
    lines.append('- This file intentionally has no nodata value so UMEP/SVF/SOLWEIG will not mask ground pixels.')
    lines.append('')
    lines.append(f'Buildings rasterized: **{len(b)}**')
    lines.append(f'Building pixels >{threshold}m: **{n_bldg}**')
    lines.append(f'Building area m²: **{area:.1f}**')
    if len(vals):
        lines.append(f'Height min/mean/max: **{vals.min():.2f} / {vals.mean():.2f} / {vals.max():.2f} m**')
    out_report.write_text('\n'.join(lines), encoding='utf-8')
    print('[OK] reviewed DSM:', out_dsm)
    print('[OK] report:', out_report)

if __name__=='__main__':
    main()
