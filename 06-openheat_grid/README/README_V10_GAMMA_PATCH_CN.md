# OpenHeat v10-gamma UMEP morphology patch

解压到项目根目录后，按顺序运行：

```bat
scripts\v10_gamma_pre_umep_pipeline.bat
```

然后在 QGIS/UMEP 手工运行 SVF + shadow，输出到：

```text
data/rasters/v10/umep_svf_with_veg/
data/rasters/v10/umep_shadow_with_veg/
```

然后运行：

```bat
scripts\v10_gamma_post_umep_morphology_pipeline.bat
scripts\v10_gamma_run_forecast_and_compare.bat
```

主要输出：

```text
data/grid/v10/toa_payoh_grid_v10_features_umep_with_veg.csv
outputs/v10_gamma_forecast_live/v10_gamma_hotspot_ranking_with_grid_features.csv
outputs/v10_gamma_comparison/v10_vs_v08_forecast_ranking_comparison.md
```

详细说明见：

```text
docs/v10/V10_GAMMA_UMEP_MORPHOLOGY_GUIDE_CN.md
```
