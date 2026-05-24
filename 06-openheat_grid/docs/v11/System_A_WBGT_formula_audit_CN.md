# System A WBGT 公式敏感性审计说明

**日期:** 2026-05-24  
**阶段:** v1.1-beta-formula companion audit  
**对应正式结果:** v1.1-beta-formal frozen-snapshot closeout  
**审计性质:** 公式敏感性筛查，不是公式替换，不 retroactively recalibrate v1.1-beta-formal。

## 0. 结论摘要

本审计检查 System A 当前 v09 WBGT proxy 公式及一组简单 globe 系数敏感性变体，目的是解释 v1.1-beta-formal 中 M0/raw proxy 的系统性低估和 fixed_31/fixed_33 阈值穿越失败。

核心结论如下。

1. `existing_v09_proxy` 可以被 `stull_simple_globe_k0p0045` 精确重建。`reconstructed_from_v09_components`、`stull_simple_globe_k0p0045` 与 `existing_v09_proxy` 在 bias、MAE、RMSE、R2、分布和阈值分类上完全一致。
2. `stull_simple_globe_k0p0065` 是本组简单 globe 系数中 MAE 最低的变体，但相对 `existing_v09_proxy` 只把 MAE 从 1.273195°C 降到 1.253325°C，改善约 0.01987°C，约等于 0.020°C。该改善太小，不能作为公式替换依据。
3. 所有 raw formula variants 的预测值最大值都低于 31°C 和 33°C。因此 fixed_31 / fixed_33 raw confusion matrix 中 predicted positives 全为 0。
4. 对每个公式做 mean-bias correction 后，fixed_31 / fixed_33 仍然没有 predicted positives。也就是说，简单地补偿平均偏差仍不足以恢复固定阈值穿越。
5. 要恢复固定阈值穿越，需要的 additive shift 很大。即使最高尾部的 `stull_simple_globe_k0p0065`，让 max 触及 31°C 仍需 +1.565716°C，让 max 触及 33°C 需 +3.565716°C；若要匹配 observed event count，则 31°C 需约 +3.061915°C，33°C 需约 +4.042956°C。
6. 当前问题不是简单调大 globe coefficient 就能解决的微调问题，而是 high-tail compression / structural under-prediction：高温尾部被压得过低，导致 raw score distribution 无法接近 31°C / 33°C 固定阈值。
7. v1.1-beta-formal 不应被重写。公式问题应进入独立的 formula-v2 future cycle，并在单独验证后再讨论是否替换公式。

## 1. 范围边界

本文件是 System A WBGT formula companion sensitivity audit。它只解释公式敏感性，不修改、替换或重新解释 v1.1-beta-formal 的 frozen-snapshot formal calibration outputs。

本审计没有做以下工作：

- 没有修改 `outputs/v11_beta_formal/` 下的正式输出。
- 没有声称找到 validated replacement formula。
- 没有启动 Liljegren/PyWBGT 实现。
- 没有启动 ML、surrogate、v1.2、SOLWEIG 或 hazard map 工作。
- 没有把 station-level WBGT 审计升级为 100m local WBGT prediction。

允许的表述：

- calibrated hourly WBGT temporal baseline
- simulation-informed local radiative modifier
- WBGT-gated local radiative hazard score
- first-order local heat hazard prioritisation
- future risk overlay after exposure and vulnerability are explicit

不允许的表述：

- validated local WBGT prediction
- real-time heat risk forecast
- SOLWEIG Tmrt equals WBGT
- ML surrogate calibrates observed local WBGT
- hazard map equals risk map
- feature importance proves real-world causal heat-risk drivers

## 2. 输入与输出

公式审计输入：

```text
data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_v091.csv
```

目标列：

```text
official_wbgt_c
```

行数说明：

```text
脚本加载 snapshot 时显示 40,419 rows。
公式误差、confusion matrix、threshold sweep 等指标使用 official_wbgt_c 与公式分数同时非空的 analytic rows，因此 n=40,389。
差异 30 rows 来自 target/formula validity filtering，不代表 formal snapshot 被修改，也不代表 archive row loss。
```

主要输出：

```text
outputs/v11_formula_audit/formula_bias_mae_rmse_table.csv
outputs/v11_formula_audit/formula_distribution_summary.csv
outputs/v11_formula_audit/formula_event_confusion_matrix.csv
outputs/v11_formula_audit/formula_threshold_operating_points.csv
outputs/v11_formula_audit/formula_bias_corrected_confusion_matrix.csv
outputs/v11_formula_audit/formula_required_shift_summary.csv
outputs/v11_formula_audit/formula_flip_summary_vs_v09.csv
outputs/v11_formula_audit/System_A_WBGT_formula_audit_report.md
```

本中文说明文件：

```text
docs/v11/System_A_WBGT_formula_audit_CN.md
```

### 2.1 公式定义与输入列

输入列来自 `configs/v11/v11_formula_audit_config.example.json`：

| 用途 | column |
| --- | --- |
| observed target | `official_wbgt_c` |
| existing proxy | `wbgt_proxy_v09_c` |
| air temperature | `temperature_2m` |
| relative humidity | `relative_humidity_2m` |
| wind speed | `wind_speed_10m` |
| shortwave radiation | `shortwave_radiation` |
| Stull wet-bulb column | `wetbulb_stull_c_v09` |
| v09 globe proxy column | `globe_temp_proxy_v09_c` |

本审计中的公式定义如下：

```text
existing_v09_proxy
    = wbgt_proxy_v09_c

reconstructed_from_v09_components
    = 0.7 * wetbulb_stull_c_v09
    + 0.2 * globe_temp_proxy_v09_c
    + 0.1 * temperature_2m

stull_simple_globe_k*
    wind_term = sqrt(max(wind_speed_10m, min_wind_for_sqrt) + wind_offset)
    globe_temp_simple = temperature_2m + k * shortwave_radiation / wind_term
    WBGT_simple = 0.7 * wetbulb_stull_c_v09
                + 0.2 * globe_temp_simple
                + 0.1 * temperature_2m

no_radiation_sensitivity_tg_eq_tair
    = 0.7 * wetbulb_stull_c_v09
    + 0.3 * temperature_2m
```

配置中 `wind_offset=0.25`，`min_wind_for_sqrt=0.0`，`k` 扫描值为 `0.0025, 0.0035, 0.0045, 0.0055, 0.0065`。若 `wetbulb_stull_c_v09` 不存在，脚本会用 Stull wet-bulb approximation 从 `temperature_2m` 与 `relative_humidity_2m` 重新计算；本次 snapshot 中使用现有 v09 wet-bulb column。

## 3. 与 v1.1-beta-formal 的关系

v1.1-beta-formal 的核心定位仍然成立：System A 提供 calibrated hourly WBGT temporal severity baseline，用于后续 WBGT-gated local radiative hazard scoring。formal pass 已经把 raw proxy 的 under-prediction 作为 M0 baseline 问题处理，并用 M3/M4/M7 等 calibrated baselines 提供正式比较。

本公式审计只回答一个较窄问题：

```text
如果只调整 v09 proxy 的简单 globe coefficient，是否足以解释并修复 fixed threshold crossing failure?
```

答案是否定的。`k0.0065` 对 MAE 有微弱改善，但不能恢复 raw formula 在 31°C / 33°C 的 fixed-threshold positives。formal calibration 不应因此被重写；若要替换 WBGT 公式，应作为 formula-v2 单独立项、单独验证。

## 4. 公式指标

| formula | bias_pred_minus_obs | MAE | RMSE | R2 | 解释 |
| --- | ---: | ---: | ---: | ---: | --- |
| `stull_simple_globe_k0p0065` | -0.821547 | 1.253325 | 1.726936 | 0.346560 | 本组内 MAE 最低，但改善很小 |
| `stull_simple_globe_k0p0055` | -0.839113 | 1.263170 | 1.743590 | 0.333897 | 比 v09 略好 |
| `existing_v09_proxy` | -0.856679 | 1.273195 | 1.760567 | 0.320862 | 当前 v09 proxy |
| `reconstructed_from_v09_components` | -0.856679 | 1.273195 | 1.760567 | 0.320862 | 精确重建 v09 proxy |
| `stull_simple_globe_k0p0045` | -0.856679 | 1.273195 | 1.760567 | 0.320862 | 精确等价于 v09 proxy |
| `stull_simple_globe_k0p0035` | -0.874245 | 1.283368 | 1.777860 | 0.307455 | 更低估 |
| `stull_simple_globe_k0p0025` | -0.891810 | 1.293698 | 1.795459 | 0.293676 | 更低估 |
| `no_radiation_sensitivity_tg_eq_tair` | -0.935725 | 1.320454 | 1.840738 | 0.257601 | 无辐射敏感性 baseline，不是户外替代公式 |

关键读法：

- `existing_v09_proxy`、`reconstructed_from_v09_components`、`stull_simple_globe_k0p0045` 完全一致，因此 v09 proxy 的 simple-globe coefficient 等价于 `k=0.0045`。
- `k=0.0065` 把 bias 从 -0.856679°C 改到 -0.821547°C，MAE 从 1.273195°C 改到 1.253325°C。改善方向正确，但量级只有约 0.020°C。
- 这个量级远小于 formal pass 中要解决的 high-tail threshold crossing failure。

## 5. Raw 分布与 high-tail compression

| formula | p95 | p99 | max | mean |
| --- | ---: | ---: | ---: | ---: |
| `existing_v09_proxy` | 27.967162 | 28.534765 | 29.235366 | 26.140359 |
| `stull_simple_globe_k0p0045` | 27.967162 | 28.534765 | 29.235366 | 26.140359 |
| `stull_simple_globe_k0p0065` | 28.067507 | 28.678506 | 29.434284 | 26.175540 |
| `no_radiation_sensitivity_tg_eq_tair` | 27.719988 | 28.245859 | 28.827236 | 26.061201 |

所有 raw formula variants 的 `max` 都低于 31°C。最高的是 `stull_simple_globe_k0p0065`，`max=29.434284°C`，距离 31°C 仍差 1.565716°C，距离 33°C 差 3.565716°C。

这说明问题集中在高尾部分布被压缩，而不是均值附近的小幅误差。提高 globe coefficient 会整体略微抬高分布，但没有把高尾部推到 fixed_31 / fixed_33 附近。

## 6. 固定阈值结果

raw formula fixed-threshold confusion matrix 的结论很直接：

```text
event threshold 31°C: observed events = 2,844, predicted positives = 0
event threshold 33°C: observed events = 212, predicted positives = 0
```

上述结果适用于所有 raw formula variants，包括 `existing_v09_proxy`、`stull_simple_globe_k0p0045` 和 `stull_simple_globe_k0p0065`。

因此，`fixed_31` / `fixed_33` raw confusion 是 all-zero predicted positives，不是因为没有 observed WBGT events，而是因为公式输出分布整体没有到达这些固定阈值。

## 7. Threshold sweep 结果

threshold sweep 从 27.0°C 到 34.0°C，步长 0.05°C。它说明如果放弃固定的 31°C / 33°C score threshold，低得多的 score threshold 可以捕捉一部分事件，但这只是敏感性诊断，不是 deployment replacement。

重要 caution：这里的 raw formula threshold sweep 不能直接拿来和 v1.1-beta-formal 的 calibrated M3/M4 threshold scan 作同尺度比较。原因是：

- 本节 sweep 的 score 是 raw formula output，没有经过 LOSO calibration、ridge residual correction、lag/inertia feature correction 或 hourly target calibration。
- formal M3/M4 scan 的 score 是 calibrated model prediction，属于 frozen formal calibration pipeline 的 out-of-fold / formal evaluation artifact。
- 因此，本节只能说明 raw formula scale 与 observed threshold scale 的错位，不能说明 raw formula 在 operational setting 中优于或劣于 M3/M4。

代表性结果：

| formula | event threshold | operating point | score threshold | precision | recall | F1 |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| `existing_v09_proxy` | 31 | best_F1 | 27.55 | 0.342289 | 0.604782 | 0.437158 |
| `stull_simple_globe_k0p0065` | 31 | best_F1 | 27.65 | 0.347286 | 0.609705 | 0.442516 |
| `existing_v09_proxy` | 33 | best_F1 | 28.25 | 0.050829 | 0.216981 | 0.082363 |
| `stull_simple_globe_k0p0065` | 33 | best_F1 | 28.40 | 0.050998 | 0.216981 | 0.082585 |

读法：

- best_F1 thresholds 明显低于 31°C / 33°C，说明 raw score scale 与 observed WBGT threshold scale 不对齐。
- `k0.0065` 相对 v09 只带来非常小的 F1 改善。
- 对 33°C event，best_F1 仍非常低，precision 约 0.05，说明高阈值事件不能靠简单公式 sweep 获得可靠判别。

## 8. Mean-bias correction 结果

本审计还做了一个简单诊断：

```text
formula_bias_corrected = formula - bias_pred_minus_obs
```

因为各公式 bias 为负，这等价于给公式加上约 0.82°C 到 0.94°C 的平均偏差校正。

结果：

```text
fixed_31: all formulas tp=0, fp=0, fn=2844
fixed_33: all formulas tp=0, fp=0, fn=212
```

也就是说，即使做 mean-bias correction，fixed_31 / fixed_33 仍没有 predicted positives。平均偏差校正不能修复高尾部压缩。

## 9. Required shift 结果

| formula | max reach 31 | match count 31 | p99 reach 31 | max reach 33 | match count 33 | p99 reach 33 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `existing_v09_proxy` | +1.764634 | +3.168593 | +2.465235 | +3.764634 | +4.207519 | +4.465235 |
| `stull_simple_globe_k0p0045` | +1.764634 | +3.168593 | +2.465235 | +3.764634 | +4.207519 | +4.465235 |
| `stull_simple_globe_k0p0065` | +1.565716 | +3.061915 | +2.321494 | +3.565716 | +4.042956 | +4.321494 |
| `no_radiation_sensitivity_tg_eq_tair` | +2.172764 | +3.416580 | +2.754141 | +4.172764 | +4.565945 | +4.754141 |

这些 required shifts 很大，尤其是 match observed event count 所需的 shift。它们远大于 `k0.0045` 到 `k0.0065` 带来的均值或 MAE 改善。

因此，公式问题应被解释为：

```text
high-tail compression / structural under-prediction
```

而不是：

```text
globe coefficient 稍微调大即可解决
```

### 9.1 Station/day diagnostics note

脚本同时写出 station/day 维度的偏差诊断：

```text
outputs/v11_formula_audit/formula_bias_by_station.csv
outputs/v11_formula_audit/formula_bias_by_day.csv
```

这些表用于检查公式偏差是否集中在特定 station 或日期，而不是只看全局 MAE / bias。当前中文说明不把 station/day diagnostics 解释为因果证据，也不把单站或单日异常升级为 formula replacement 结论。它们的用途是 future formula-v2 triage：如果后续发现某些 station、日期、天气 regime 或观测窗口持续贡献高尾部 under-prediction，应回到这些诊断表定位问题范围。

## 10. 对 v1.1-beta-formal 的影响

本审计不会改变 v1.1-beta-formal 的结论。

formal pass 的合理解释仍是：

- M0 raw proxy 是需要被 calibrated baselines beat 的 production proxy baseline。
- M4 inertia ridge 可作为 physics-first / recall-oriented operational primary baseline。
- M7 compact weather ridge 可作为 compact precision-oriented alternative。
- M5/M6/M7 的形态学和 overhead calibration 在当前 station network 下仍 structurally unidentifiable；这不表示 urban morphology 物理上没有影响。
- System A 的当前可主张成果是 calibrated hourly WBGT temporal baseline，而不是 validated local WBGT prediction。

公式审计补充的是：

- M0 的 structural under-prediction 至少部分来自 raw formula score scale 和 high-tail compression。
- 简单 globe coefficient tuning 不能把 raw formula 重新带回 31°C / 33°C fixed-threshold operating regime。
- 如果未来要替换公式，应作为独立 formula-v2 cycle，而不是修改本次 formal closeout。

### 10.1 Formula-v2 trigger criteria

未来只有在满足清晰 trigger 时，才应启动 formula-v2，而不是在 v1.1-beta-formal 内直接改写公式。建议 trigger criteria 如下：

- raw formula high-tail compression 继续在新的 frozen snapshot 或后续 archive window 中复现，尤其是 raw max / p99 长期低于 31°C fixed threshold。
- mean-bias correction、period bias correction 或简单 globe coefficient tuning 仍无法恢复 fixed_31 / fixed_33 threshold crossing。
- station/day diagnostics 指向稳定的结构性偏差模式，而不是单次数据缺口、schema mismatch、station mapping 或 target missingness artifact。
- 有经过单独验证的 formula candidate，例如独立实现并验证的 Liljegren/PyWBGT route，且输入列、单位、辐射/风速假设和 Singapore outdoor context 已被审计。
- formula-v2 能在 frozen snapshot 上给出 machine-readable metrics、threshold diagnostics、station/day diagnostics、row attrition note，并明确不 retroactively rewrite v1.1-beta-formal。

## 11. Run log

公式审计脚本：

```text
scripts/v11_formula_audit_compare.py
```

配置：

```text
configs/v11/v11_formula_audit_config.example.json
```

验证命令：

```text
python -m py_compile scripts/v11_formula_audit_compare.py
python scripts/v11_formula_audit_compare.py --config configs/v11/v11_formula_audit_config.example.json
```

本地环境说明：当前 PowerShell session 中 `python` 不在 PATH；实际验证使用 Codex bundled Python runtime 等价执行：

```text
C:\Users\CloudStar\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m py_compile scripts/v11_formula_audit_compare.py
C:\Users\CloudStar\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts/v11_formula_audit_compare.py --config configs/v11/v11_formula_audit_config.example.json
```

运行日志摘要：

```text
[load] data\calibration\v11\snapshots\v11_pairs_14d_formal_20260524_40419_v091.csv
       40,419 rows x 495 cols
[write] outputs\v11_formula_audit\formula_bias_mae_rmse_table.csv
[write] outputs\v11_formula_audit\formula_distribution_summary.csv
[write] outputs\v11_formula_audit\formula_event_confusion_matrix.csv
[write] outputs\v11_formula_audit\formula_threshold_operating_points.csv
[write] outputs\v11_formula_audit\formula_bias_corrected_confusion_matrix.csv
[write] outputs\v11_formula_audit\formula_required_shift_summary.csv
[write] outputs\v11_formula_audit\formula_flip_summary_vs_v09.csv
[write] outputs\v11_formula_audit\System_A_WBGT_formula_audit_report.md
```

本中文说明创建时没有 push，没有 open PR，没有修改 formal outputs。

### 11.1 References / grounding

本说明基于以下本地材料，不引入新的外部模型实现：

```text
outputs/v11_formula_audit/System_A_WBGT_formula_audit_report.md
outputs/v11_formula_audit/formula_bias_mae_rmse_table.csv
outputs/v11_formula_audit/formula_distribution_summary.csv
outputs/v11_formula_audit/formula_event_confusion_matrix.csv
outputs/v11_formula_audit/formula_threshold_operating_points.csv
outputs/v11_formula_audit/formula_bias_corrected_confusion_matrix.csv
outputs/v11_formula_audit/formula_required_shift_summary.csv
outputs/v11_formula_audit/formula_bias_by_station.csv
outputs/v11_formula_audit/formula_bias_by_day.csv
configs/v11/v11_formula_audit_config.example.json
scripts/v11_formula_audit_compare.py
docs/v11/OpenHeat_v11_beta1_findings_report_CN_v2_2_FINAL.md
```

正式结论边界来自项目 AGENTS.md 与 v1.1-beta-formal findings：本项目当前可主张的是 calibrated hourly WBGT temporal baseline，以及后续 WBGT-gated local radiative hazard scoring 的基础；本审计不提供 validated local WBGT prediction、real-time warning system、formula replacement、ML surrogate 或 hazard/risk map claim。

## 12. Claim boundaries

本审计支持的 claim：

```text
The current v09 WBGT proxy can be exactly reconstructed by the simple-globe k=0.0045 variant in this audit setup.
Within the tested simple-globe variants, k=0.0065 marginally improves MAE by about 0.020°C but does not restore fixed 31°C / 33°C threshold crossings.
The formula audit indicates high-tail compression / structural under-prediction in the raw proxy scale.
This is a screening sensitivity audit and should inform a future formula-v2 cycle.
```

本审计不支持的 claim：

```text
System A has a validated replacement WBGT formula.
The v1.1-beta-formal calibration should be rewritten.
Raw formula tuning solves fixed_31 / fixed_33 classification.
OpenHeat now predicts validated local WBGT at 100m cell scale.
Any ML, SOLWEIG, surrogate, or hazard-map conclusion follows from this audit.
```

## 13. Recommended closeout

将本文件作为 v1.1-beta-evidence / v1.1-beta-formula companion note 保留。v1.1-beta-formal report 不重写；最多在证据索引或 formal appendix 中交叉引用本审计，说明 raw proxy 公式存在 high-tail compression，并把公式替换留给未来 formula-v2。
