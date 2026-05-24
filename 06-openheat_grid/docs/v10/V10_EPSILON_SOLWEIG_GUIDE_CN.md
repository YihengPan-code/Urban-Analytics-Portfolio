# OpenHeat v10-epsilon 轻量 selected-cell SOLWEIG 指南

## 1. 版本定位

v10-epsilon 是轻量 SOLWEIG selected-cell physical validation。它不是全 AOI overhead-aware physical model，也不是 operational final ranking。

它用于回答：

1. v10-delta 的 overhead shade sensitivity 是否方向合理？
2. TP_0565 / TP_0986 这类 confident hotspots 是否在 SOLWEIG Tmrt 下仍然高热？
3. TP_0088 / TP_0916 这类 overhead-confounded cells 是否确实应该从 ordinary pedestrian hotspot 解读中降级？

## 2. 默认 selected cells

| cell_id | role | 用途 |
|---|---|---|
| TP_0565 | confident_hot_anchor_1 | 经过 building DSM + overhead sensitivity 后仍高热 |
| TP_0986 | confident_hot_anchor_2 | 第二个稳定高热 anchor |
| TP_0088 | overhead_confounded_rank1_case | v10-gamma rank 1，但 v10-delta 大幅下降 |
| TP_0916 | saturated_overhead_case | v10-delta overhead-shade saturation 案例 |
| TP_0433 | clean_shaded_reference | 低热 / shaded reference |

可在 `configs/v10/v10_epsilon_solweig_config.example.json` 修改。

## 3. Pre-SOLWEIG pipeline

运行：

```bat
scripts\v10_epsilon_pre_solweig_pipeline.bat
```

输出到：

```text
data/solweig/v10_epsilon_tiles/
outputs/v10_epsilon_solweig/
```

每个 tile folder 会有：

```text
dsm_buildings_tile.tif
dsm_vegetation_tile_base.tif
dsm_overhead_canopy_tile.tif
dsm_vegetation_tile_overhead.tif
solweig_base/
solweig_overhead/
README_SOLWEIG_STEPS.txt
```

## 4. QGIS / UMEP 手工 SOLWEIG

对每个 tile 跑两个 scenario。

### Scenario A: base

```text
Building DSM: dsm_buildings_tile.tif
Vegetation DSM: dsm_vegetation_tile_base.tif
Output folder: solweig_base/
```

### Scenario B: overhead sensitivity

```text
Building DSM: dsm_buildings_tile.tif
Vegetation DSM: dsm_vegetation_tile_overhead.tif
Output folder: solweig_overhead/
```

`dsm_vegetation_tile_overhead.tif` 是 `max(vegetation DSM, overhead canopy DSM)`，用于把 overhead infrastructure 近似为 canopy-like shade。

推荐小时：

```text
10:00, 12:00, 13:00, 15:00, 16:00
```

时间紧时只跑：

```text
12:00, 13:00, 15:00
```

Tmrt 输出文件名必须包含 HHMM，例如：

```text
Tmrt_20260320_1300.tif
Tmrt_2026_3_20_1300D.tif
```

## 5. Post-SOLWEIG pipeline

将 Tmrt raster 放入对应 `solweig_base/` 与 `solweig_overhead/` 后运行：

```bat
scripts\v10_epsilon_post_solweig_pipeline.bat
```

输出：

```text
outputs/v10_epsilon_solweig/v10_epsilon_focus_tmrt_summary.csv
outputs/v10_epsilon_solweig/v10_epsilon_base_vs_overhead_tmrt_comparison.csv
outputs/v10_epsilon_solweig/v10_epsilon_solweig_comparison_report.md
```

## 6. 结果解读

### TP_0565 / TP_0986

如果 base 和 overhead scenario Tmrt 基本一致，且 Tmrt 高，说明它们是 confident pedestrian-relevant hotspots。

### TP_0088

如果 overhead scenario Tmrt 明显低于 base，说明 v10-delta 对其降级有物理支持。

如果变化很小，说明 v10-delta algebraic overhead sensitivity 可能过强。

### TP_0916

如果 v10-delta 中 shade=1 saturation，但 SOLWEIG 只显示中等 Tmrt 降低，说明 v10-delta 是 confounding flag，不是精确物理值。

## 7. 限制

- overhead-as-canopy 是近似，不是完整 viaduct / bridge physical model。
- 不模拟桥面热储存、车辆排热、桥下风、长波辐射。
- 不替代 v10-delta 或 v10-gamma，只为 selected-cell physical validation 提供辅助证据。
