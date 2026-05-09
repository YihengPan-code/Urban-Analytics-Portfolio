# OpenHeat v0.9-gamma SOLWEIG selected tiles 指导

## 目标

v0.9-gamma 不是全域 SOLWEIG，而是 selected-tile physical deep dive。它要回答：

> v0.8 的 Tmrt/radiant proxy 是否低估了特定热点 tile 的辐射热负荷？SOLWEIG Tmrt 能不能解释下午 official WBGT tail underprediction？

## 推荐流程

### 1. 选择 tiles

```bat
python scripts\v09_gamma_select_solweig_tiles.py --config configs\v09_gamma_solweig_config.example.json
```

输出：

```text
data/solweig/v09_tiles/v09_solweig_tiles.geojson
data/solweig/v09_tiles/v09_solweig_tiles_buffered.geojson
data/solweig/v09_tiles/v09_solweig_tile_metadata.csv
```

默认选择：

- hazard top cell
- conservative risk top cell
- social-sensitive risk top cell
- candidate policy top cell
- shaded/low-hazard reference cell

### 2. 裁剪 DSM / vegetation DSM

```bat
python scripts\v09_gamma_clip_tile_rasters.py --config configs\v09_gamma_solweig_config.example.json
```

每个 tile 文件夹会得到：

```text
dsm_buildings_tile.tif
dsm_vegetation_tile.tif
tile_boundary.geojson
tile_boundary_buffered.geojson
```

### 3. 你需要在 QGIS/UMEP 手动做

对每个 tile：

1. 打开 QGIS。
2. 使用 `dsm_buildings_tile.tif` 和 `dsm_vegetation_tile.tif`。
3. 跑 SOLWEIG。
4. 保存 Tmrt rasters 到该 tile 的 `solweig_outputs/` 文件夹。

建议时段：10:00, 12:00, 13:00, 15:00, 16:00。

### 4. 聚合 Tmrt

```bat
python scripts\v09_gamma_aggregate_solweig_tmrt.py --config configs\v09_gamma_solweig_config.example.json
```

输出：

```text
outputs/v09_solweig/v09_solweig_tmrt_grid_summary.csv
```

### 5. 对比 Tmrt proxy

```bat
python scripts\v09_gamma_compare_tmrt_proxy_vs_solweig.py
```

输出：

```text
outputs/v09_solweig/v09_solweig_tmrt_comparison_report.md
outputs/v09_solweig/v09_tmrt_proxy_vs_solweig_comparison.csv
```

## 解释边界

- SOLWEIG selected tiles 是物理 deep dive，不代表全 AOI 已经完成 SOLWEIG。
- 若 SOLWEIG Tmrt 明显高于 proxy Tmrt，支持 radiant-load underrepresentation hypothesis。
- 若 SOLWEIG 不解释 residual，则 tail underprediction 可能来自 WBGT globe approximation、local wind、sensor siting 或 weather forcing mismatch。
