# OpenHeat v1.1 alpha/beta development package

这是 v1.1 的第一版开发包。文件名中使用 `v11`，含义是 `v1.1`，避免 Windows 文件名和 Python import 中的小数点歧义。

## 阶段定义

```text
v1.1-alpha / v11-alpha
    archive QA + station-weather paired dataset + CV split plan

v1.1-beta / v11-beta
    calibration baseline replay + threshold scan
```

## 新增文件

```text
configs/v11/v11_alpha_archive_config.example.json
configs/v11/v11_beta_calibration_config.example.json
configs/v11/station_to_cell.example.csv

scripts/v11_lib.py
scripts/v11_alpha_archive_inventory.py
scripts/v11_alpha_build_pairs.py
scripts/v11_alpha_archive_qa.py
scripts/v11_alpha_make_cv_splits.py
scripts/v11_beta_calibration_baselines.py
scripts/v11_beta_threshold_scan.py
scripts/v11_run_alpha_archive_pipeline.bat
scripts/v11_run_beta_calibration_pipeline.bat

docs/v11/V11_ALPHA_ARCHIVE_QA_GUIDE_CN.md
docs/v11/V11_BETA_CALIBRATION_GUIDE_CN.md
```

## 依赖

建议安装：

```bash
pip install pandas numpy scikit-learn tabulate
```

如果你已经在 `openheat` conda 环境里有 pandas/numpy，只需要确认 scikit-learn 和 tabulate：

```bash
pip install scikit-learn tabulate
```

## 运行顺序

```bat
scripts\v11_run_alpha_archive_pipeline.bat
scripts\v11_run_beta_calibration_pipeline.bat
```

## 你需要自己做的事情

1. 确认 archive 文件路径。
   - 默认搜索 `data/archive/**` 和 `outputs/archive/**`。
   - 如果你的 archive 在别处，编辑 `configs/v11/v11_alpha_archive_config.example.json`。

2. 如果列名识别失败，填写 `column_overrides`。
   - `timestamp`
   - `station_id`
   - `official_wbgt_c`
   - weather columns

3. 编辑 station-to-cell mapping：

```text
configs/v11/station_to_cell.example.csv
```

4. 跑完 alpha 后，先读：

```text
outputs/v11_alpha_archive/v11_archive_QA_report.md
```

5. 只有 archive QA 健康，再进入 beta。

## 重要提醒

如果脚本没有找到项目已有的 `raw_proxy_wbgt_c`，会用 temperature/RH 计算一个 fallback proxy。这只适合 smoke test。最终 v1.1-beta 应该尽量接入你 v0.9/v10 已经使用过的 WBGT/proxy forecast 输出。
