# OpenHeat v0.9 beta extension + gamma SOLWEIG patch

包含：

1. v0.9-beta threshold scan extension
2. v0.9-beta conclusion report generator
3. v0.9-gamma selected-tile SOLWEIG preparation / aggregation scripts
4. v0.9 archive loop script

推荐顺序：

```bat
python scripts\v09_beta_threshold_scan.py --config configs\v09_beta_threshold_config.example.json
python scripts\v09_beta_make_conclusion_report.py
scripts\v09_gamma_run_pre_umep_pipeline.bat
```

然后在 QGIS/UMEP 中运行 SOLWEIG。

完成 UMEP 后：

```bat
scripts\v09_gamma_run_post_umep_pipeline.bat
```

持续采集 archive：

```bat
scripts\run_v09_archive_loop.bat
```
