# OpenHeat v10-epsilon SOLWEIG patch

解压到项目根目录后：

```bat
scripts\v10_epsilon_pre_solweig_pipeline.bat
```

然后在 QGIS/UMEP 中对每个 selected tile 跑：

- `solweig_base/`: building DSM + base vegetation DSM
- `solweig_overhead/`: building DSM + overhead-as-canopy vegetation DSM

完成 SOLWEIG Tmrt 输出后：

```bat
scripts\v10_epsilon_post_solweig_pipeline.bat
```

详细说明见：

```text
docs/v10/V10_EPSILON_SOLWEIG_GUIDE_CN.md
```
