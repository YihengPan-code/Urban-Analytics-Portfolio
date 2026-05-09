# OpenHeat v0.9-beta calibration patch

这个 patch 添加 v0.9-beta WBGT proxy 校准脚本。

## 前置文件

需要已有：

```text
data/calibration/v09_wbgt_station_pairs.csv
```

这是 v0.9-alpha 生成的 paired official WBGT / Open-Meteo forcing / physics proxy 表。

## 安装依赖

```bat
pip install -r requirements_v09_beta.txt
```

## 运行

```bat
python scripts\v09_beta_fit_calibration_models.py --config configs\v09_beta_config.example.json
```

或：

```bat
scripts\v09_beta_run_pipeline.bat
```

## 主要输出

```text
outputs/v09_beta_calibration/v09_beta_calibration_report.md
outputs/v09_beta_calibration/v09_beta_model_metrics.csv
outputs/v09_beta_calibration/v09_beta_event_detection_metrics.csv
outputs/v09_beta_calibration/v09_beta_predictions_long.csv
```
