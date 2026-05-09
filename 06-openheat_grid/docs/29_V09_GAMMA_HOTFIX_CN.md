# OpenHeat v0.9-gamma hotfix

这个 hotfix 修复/增强四类问题：

1. **SOLWEIG Tmrt 时间解析**  
   原先可能把 `Tmrt_2026_3_20_1300D.tif` 里的 `2026` 当成时段。现在优先解析末尾 `HHMM`，输出 `tmrt_time_label` 和 `tmrt_hour_sgt`。

2. **DSM nodata / open-pixel mask**  
   clipping 脚本会输出 `*_masked.tif`（nodata=-9999，用于 QA）和 `*_tile.tif`（UMEP-ready，地面=0）。aggregation 脚本使用 `valid_mask` 和 `building_mask = dsm > 0.5`，不再用 `dsm <= 0` 混合地面与 nodata。

3. **reference tile QA**  
   reference tile 会优先选择低 hazard + 高 shade/NDVI cell。如果 fallback 选不到低 hazard reference，会在 metadata 里写 warning。

4. **Tmrt proxy 比较说明**  
   如果可以按 `cell_id + hour` 匹配 SOLWEIG 与 forecast proxy，则输出 strict time-matched comparison；否则明确标记为 diagnostic comparison。

## 使用方法

把 zip 解压到项目根目录：

```bat
C:\Users\CloudStar\Documents\GitHub\Urban-Analytics-Portfolio\06-openheat_grid
```

重新跑 tile selection：

```bat
python scripts\v09_gamma_select_solweig_tiles.py --config configs\v09_gamma_solweig_config.example.json
```

重新裁剪 tile DSM：

```bat
python scripts\v09_gamma_clip_tile_rasters.py --config configs\v09_gamma_solweig_config.example.json
```

然后在 QGIS/UMEP 里重新或继续跑 SOLWEIG，把 Tmrt rasters 放到每个 tile folder 的 `solweig_outputs` 子目录，文件名建议包含 `HHMM`，如：

```text
Tmrt_2026_5_7_1300D.tif
Tmrt_2026_5_7_1500D.tif
```

聚合 SOLWEIG Tmrt：

```bat
python scripts\v09_gamma_aggregate_solweig_tmrt.py --config configs\v09_gamma_solweig_config.example.json
```

比较 proxy 与 SOLWEIG：

```bat
python scripts\v09_gamma_compare_tmrt_proxy_vs_solweig.py --config configs\v09_gamma_solweig_config.example.json
```

## 检查重点

聚合后检查：

```bat
python -c "import pandas as pd; df=pd.read_csv('outputs/v09_solweig/v09_solweig_tmrt_grid_summary.csv'); print(df[['tile_id','cell_id','tmrt_time_label','tmrt_hour_sgt','tmrt_mean_c','n_pixels']].head(30).to_string())"
```

你应该看到 `tmrt_time_label` 是 `1000/1200/1300/1500/1600` 等，而不是 `2026`。

