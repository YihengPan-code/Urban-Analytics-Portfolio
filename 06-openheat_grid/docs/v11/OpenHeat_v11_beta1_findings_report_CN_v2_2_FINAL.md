# OpenHeat v1.1-beta.1 findings report v2.2 FINAL

**编制日期**: 2026-05-11  
**版本**: v2.2 FINAL（替代 v2.1；第四轮 audit Plan A 完成；H10 已证实；已完成 final cleanup）  
**项目阶段**: v1.1-α + β smoke + 1st/2nd/3rd/4th audit + ablation + hourly aggregation + M7 + bootstrap CI + threshold operating-point scan  
**编制目的**: 作为 v1.1-beta.1 formal beta 前的 canonical audit report，记录四轮 audit、patch lineage、实验结果、dissertation methodology 可引用素材，以及 14-day formal pass 的 falsifiable hypotheses。

**前置文档**:

- `docs/handoff/OpenHeat_v11_alpha_beta_HANDOFF_CN.md`
- `docs/v11/OpenHeat_v11_beta1_findings_report_CN_v1_archived.md`（v1，废弃）
- `docs/v11/OpenHeat_v11_beta1_findings_report_CN_v2_archived.md`（v2，superseded）
- `docs/v11/OpenHeat_v11_beta1_findings_report_CN_v2_1_archived.md`（v2.1，superseded by v2.2）
- `docs/25.5_V09_BETA_FINDINGS_REPORT_CN.md`（v0.9-beta 对照）

---

## 0. TL;DR

v1.1-β.1 经历四轮 peer audit。v2.2 FINAL 采纳第四轮 audit 后的所有方法论修正，并完成最后 7 点 cleanup：

1. `STATIC_FIRST_COLS` 统一表述为 **17 个候选 static columns，当前输入中实际匹配并 forward 15 个**。
2. `no_S142` bootstrap fold count 已核实：**26 unique stations，S142 rows = 0**；station-grouped bootstrap 实际有效 folds = 25（1 个 station 在 LOSO + retrospective filter 后 M3/M4 预测被 NaN-dropped）。如果旧表出现 `n_folds=27`，应视作 script `fold`-column convention artifact，本 FINAL no_S142 行统一为 25（详 §7.2 †）。
3. `M4 + hourly_max + fixed_31` 改为 **physics-first / recall-oriented operational primary**；`M7` 保留为 **compact precision-oriented alternative**。
4. 修正 TP/FP trade-off：M4 相比 M3 多抓 **15 TP**；M4 相比 M7 多抓 **3 TP**，但增加 **11 FP**。
5. 全文删除“independent dataset framings”这类过强表述，统一为 **evaluation framings / dataset framings derived from the same v1.1 archive**。
6. “morphology contribution = 0” 全部加限定：**under the current NEA station network and station-level ridge/imputer pipeline**。
7. row-count attrition 改为明确 caution：`6,372 → 5,724` 来自 target/proxy non-null analytic-set requirement；formal pass 必须补 row-attrition diagnostic。

**v2.2 FINAL 的 6 个核心发现**：

1. **H10 confirmed（audit-proof keystone）**：hourly aggregator PATCH 3 主动 forward static morphology / overhead / grid columns 后，M5/M6/M7 在 `hourly_mean` 与 `hourly_max` 上仍 bit-identical 到 6 位小数。M5/M6/M7 等价不再依赖 aggregator drop，而是当前 station-network sparsity + imputer/scaler pipeline 的 signal-level consequence。
2. **M4 inertia advantage 有统计方向性，但 practical small**：5,000-iter fold-level block bootstrap 显示 6/8 evaluation framings 的 95% CI 排除 0；最大 D_migrated Δ=-0.0179°C，仍低于 0.03°C practical-meaningful threshold。
3. **hourly-max 是 operational target**：fixed_31 下，M4 F1=0.632，M7 F1=0.639；best-F1 上限约 0.72–0.73。15-min fixed_31 F1 仅约 0.10–0.23，precision_70 不可达。
4. **v0.9 production proxy 的 structural under-prediction 在 v11 multi-day framings 中复现**：v0.9 M0 bias=-1.140°C，v11 A_all=-1.125°C，hourly_mean=-1.042°C。该结论限定为同一 v1.1 archive 的多种 evaluation framings，不声称 source-independent archives。
5. **stale-dilution hypothesis fully falsified**：A_all 与 B_retrospective 在 M3/M4 等指标上 bit-equal；collector 原 `pair_used_for_calibration` 混淆 retrospective calibration 与 operational issue freshness。
6. **M5/M6 morphology/overhead calibration structurally unidentifiable**：当前 27 个 NEA WBGT stations 里只有 S128 有 Toa Payoh grid morphology，station-level ridge calibration 无法识别 100m morphology/overhead contribution。这不是“urban morphology 物理上没有影响”，而是当前 station network 不能验证。

**当前状态判断**：

```text
v1.1-beta.1 v2.2 FINAL = formal beta 前最终 hardening / audit report
可以进入 docs/v11/ 作为 canonical beta1 audit trail
不是 14-day formal beta 结论
不是 ML 启动信号
```

---

## 1. 背景与四轮 audit 演进

### 1.1 v1.1-β smoke test

初版 β smoke test 使用 collector fallback proxy，M0 MAE≈1.36、bias≈−1.23°C，M3 LOSO MAE≈0.71、R²≈0.80。该阶段证明 pipeline 可运行，但不是 dissertation-ready calibration。

### 1.2 First audit：5-point patch

| # | 内容 | 性质 |
|---|---|---|
| 5.1 | M4 time-aware lag features | 关键 bug |
| 5.2 | S142 sensitivity | quick win |
| 5.3 | hourly aggregation | 方法论加固 |
| 5.4 | fallback proxy → v0.9 production proxy | framework promotion |
| 5.5 | pairing diagnostic | quick win |

### 1.3 Second audit：3-point patch

| # | 内容 | 结论 |
|---|---|---|
| 7 | retrospective vs operational flag semantics | 拆分 pairing flags |
| 8 | stale-dilution 未证实 | A/B/C/D ablation 后 falsified |
| 9 | hourly aggregation pending | 立即完成 hourly mean/max |

### 1.4 Third audit：5-point patch

| # | 问题 | v2.1 解决 |
|---|---|---|
| 4.1 | “inherent floor” 过强 | 改为 practical calibration floor hypothesis |
| 4.2 | “independent archives” 夸大 | 改为 migrated + fresh segments / evaluation framings |
| 4.3 | M5 morphology winner misleading | 新增 M7 compact weather baseline |
| 4.4 | hourly aggregator 状态矛盾 | 重跑 hourly aggregator |
| 4.5 | row count 缺解释 | 加 analytic-set attrition 说明 |

### 1.5 Fourth audit：Plan A + H10

| # | 内容 | v2.2 FINAL 解决 |
|---|---|---|
| 4.1 | terminology 残留 | 删除 ERA5-derived / independent datasets 等过强措辞 |
| 4.2 | dataset vs framing | 全文统一为 evaluation framings |
| 4.3 | M4-M3 缺 CI | 5,000-iter fold-level block bootstrap |
| 4.4 | hourly_max F1=0.639 操作点不清 | 4 operating points scan |
| H10 | aggregator forward morph columns 后 M5/M6/M7 是否仍等价 | confirmed |

---

## 2. v1.1-β.1 patch lineage

### 2.1 First audit patches

| 文件 | 状态 | 解决 |
|---|---|---|
| `scripts/v11_beta_build_features.py` | NEW | v0.9 proxy + time-aware features |
| `scripts/v11_beta_aggregate_hourly.py` | NEW | hourly mean/max/p90 target |
| `scripts/v11_beta_calibration_baselines.py` | PATCH | S142 exclusion + M1b |
| `scripts/v11_alpha_archive_qa.py` | PATCH | pairing diagnostic |
| `configs/v11/v11_beta_calibration_config_v091.json` | NEW | 主 config |
| `configs/v11/v11_beta_calibration_config_v091_no_S142.json` | NEW | no_S142 sensitivity |

### 2.2 Second audit patches

| 文件 | 状态 | 解决 |
|---|---|---|
| `scripts/v11_beta_build_features.py` | PATCH 2 | `derive_pairing_flags` |
| `scripts/v11_beta_calibration_baselines.py` | PATCH 2 | `filter_mode` 5-mode |
| `scripts/v11_beta_aggregate_hourly.py` | PATCH 2 | metadata flag forwarding |
| `scripts/v11_beta_ablation_runner.py` | NEW | A/B/C/D ablation |
| `configs/v11/...v091*.json` | PATCH 2 | default retrospective filter |
| `configs/v11/...hourly_mean/max.json` | NEW | hourly target configs |

### 2.3 Third audit patches

| 文件 | 状态 | 解决 |
|---|---|---|
| `scripts/v11_beta_calibration_baselines.py` | PATCH 3 | add M7_compact_weather_ridge |
| `configs/v11/...v091*.json` | PATCH 3 | add compact_weather feature group |

### 2.4 Fourth audit patches

| 文件 | 状态 | 解决 |
|---|---|---|
| `scripts/v11_beta_aggregate_hourly.py` | PATCH 3 | forward static morph/overhead/grid columns |
| `scripts/v11_beta_freeze_snapshot.bat` | NEW | formal pass snapshot freeze helper |
| `scripts/v11_beta_bootstrap_advantage.py` | NEW | fold-level block bootstrap |
| `scripts/v11_beta_threshold_scan.py` | NEW | four operating-point threshold scan |

---

## 3. 关键代码与语义定义

### 3.1 Retrospective vs operational pairing flags

```python
def derive_pairing_flags(df):
    """Separate retrospective calibration from operational evaluation."""
    out = df.copy()
    weather_ok = out[[
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "shortwave_radiation",
    ]].notna().all(axis=1)
    has_match = out.get("has_weather_match", pd.Series(True, index=out.index))
    out["pair_used_for_retrospective_calibration"] = has_match & weather_ok

    if "archive_run_id" in out.columns:
        out["is_migrated_archive"] = ~out["archive_run_id"].astype(str).str.startswith("v11_", na=False)
    return out
```

**Interpretation**:

```text
pair_used_for_retrospective_calibration:
    valid-time weather exists + core weather non-null
    used for v1.1-beta calibration

pair_used_for_operational_evaluation:
    forecast issue freshness / deployment-time availability
    used for future prospective forecast evaluation
```

### 3.2 M7 compact weather baseline

```python
("M7_compact_weather_ridge", available_features(df, feature_groups.get("compact_weather", [])))
```

`compact_weather` 8 features:

```json
[
  "wbgt_proxy_v09_c",
  "temperature_2m",
  "relative_humidity_2m",
  "wind_speed_10m",
  "shortwave_radiation",
  "shortwave_3h_mean",
  "hour_sin_v09",
  "hour_cos_v09"
]
```

**Purpose**: M7 是 M5/M6 实际 effective feature set 的 honest naming，避免误称 “morphology model winner”。

### 3.3 Static feature forwarding for H10

`STATIC_FIRST_COLS` contains **17 candidate static columns**. In the current v11 input, **15 columns were present and forwarded** by the hourly aggregator.

Candidate columns:

```text
cell_id
morph_svf
morph_building_density
morph_mean_building_height
morph_building_height_p90
morph_road_fraction
morph_gvi_percent
morph_shade_fraction
v10_dsm_max_all_m
shade_fraction_base_v10
shade_fraction_overhead_sens
delta_shade_overhead_sens_minus_base
overhead_fraction_elevated_road
overhead_fraction_elevated_rail
overhead_area_pedestrian_bridge_m2
overhead_area_covered_walkway_m2
n_overhead_features
```

Actual run log:

```text
[aggregate] static morph/overhead/grid first-of-hour: 15 cols
[sanity] static columns constant-per-station ✓ (1 of 27 stations have non-null morph)
```

Interpretation:

```text
17 candidate static columns are configured.
15 were present in the current input and forwarded.
Only 1 of 27 stations has non-null Toa Payoh morphology.
```

---

## 4. Data snapshots and row-count interpretation

### 4.1 Archive growth

| Snapshot | 总行数 | 用途 |
|---|---:|---|
| β smoke | ~5,427 | 初版 β smoke |
| v1 baselines | 5,723 | first audit |
| v2 ablation/hourly | 6,183 | second audit |
| v2.2 fourth audit | 6,372 | Plan A + H10 |
| 14d formal pass | ~36,000+ expected | formal beta |

### 4.2 Pairing diagnostic, v2.2

```text
pair_used_for_calibration (collector):       4,482 / 6,372 (70.3%)
pair_used_for_retrospective_calibration:     6,372 / 6,372 (100.0%)
is_migrated_archive:                         5,373 / 6,372 (84.3%)
fresh v11 collector rows:                      999 / 6,372 (15.7%)

retrospective − collector_pair_used:        +1,890
```

### 4.3 Analytic row-count attrition

```text
retrospective-eligible rows: 6,372
analytic rows used in baselines: 5,724
attrition: 648 rows (10.2%)
```

Interpretation:

```text
The 648-row attrition reflects the analytic-set requirement that both
`official_wbgt_c` and `wbgt_proxy_v09_c` are non-null. This report does not
claim a full target/proxy missingness breakdown. The 14-day formal pass must
include a row-attrition diagnostic table:

- retrospective eligible rows
- official_wbgt_c missing
- wbgt_proxy_v09_c missing
- both target and proxy non-null
- final analytic rows
```

### 4.4 no_S142 check

Manual verification:

```text
station_id.nunique() = 26
S142 rows = 0
station list = S124, S125, S126, S127, S128, S129, S130, S132, S135,
               S137, S139, S140, S141, S143, S144, S145, S146, S147,
               S148, S149, S150, S151, S153, S180, S184, S187
```

Therefore:

```text
no_S142 LOSO fold count should be 26.
Any previous bootstrap table reporting n_folds=27 for no_S142 should be treated
as a reporting / empty-fold accounting issue and corrected to 26.
```

---

## 5. Master results

### 5.1 Cross-comparison table

| Evaluation framing | n | M0 | M1 | M1b | M3 | M4 | M5/M6/M7 | Δ M4-M3 | ≥31 events | M3 F1 | M4 F1 | M7 F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v0.9-β 15-min 24h | 2,564 | 1.325 | 1.322 | 0.661 | 0.595 | 0.595 | 0.657 | +0.000 | n/a | n/a | n/a | n/a |
| v11 C_fresh 15-min 1d | 810 | 0.595 | 0.424 | 0.424 | 0.345 | 0.344 | 0.342 | -0.001 | few | low | low | low |
| v11 A_all 15-min 4d | 5,724 | 1.254 | 1.147 | 0.809 | 0.667 | 0.656 | 0.689 | -0.012 | 437 | 0.104 | 0.230 | 0.198 |
| v11 B_retrospective | 5,724 | ≡A | ≡A | ≡A | 0.667 | 0.656 | 0.689 | -0.012 | ≡A | ≡A | ≡A | ≡A |
| v11 no_S142 15-min 4d | 5,512 | 1.280 | 1.170 | 0.828 | 0.653 | 0.641 | 0.675 | -0.012 | 400 | 0.097 | 0.165 | 0.146 |
| v11 D_migrated 15-min | 5,372 | 1.349 | 1.238 | 0.862 | 0.695 | 0.677 | 0.726 | -0.018 | n/a | n/a | n/a | n/a |
| v11 hourly_mean | 1,674 | 1.208 | 1.099 | 0.758 | 0.605 | 0.593 | 0.631 | -0.012 | 91 | 0.114 | 0.153 | 0.133 |
| v11 hourly_max | 1,674 | 1.472 | 1.322 | 0.788 | 0.648 | 0.639 | 0.682 | -0.010 | 204 | 0.583 | 0.632 | 0.639 |

### 5.2 Ablation pivot

| Model | A_all | B_retro | C_fresh | D_migrated |
|---|---:|---:|---:|---:|
| M0_raw_proxy | 1.254 | 1.254 | 0.595 | 1.349 |
| M1_global_bias | 1.147 | 1.147 | 0.424 | 1.238 |
| M1b_period_bias | 0.809 | 0.809 | 0.424 | 0.862 |
| M3_weather_ridge | 0.667 | 0.667 | 0.345 | 0.695 |
| M4_inertia_ridge | 0.656 | 0.656 | 0.344 | 0.677 |
| M5_v10_morphology_ridge | 0.689 | 0.689 | 0.342 | 0.726 |
| M6_v10_overhead_ridge | 0.689 | 0.689 | 0.342 | 0.726 |
| M7_compact_weather_ridge | 0.689 | 0.689 | 0.342 | 0.726 |

### 5.3 Hourly mean target

| Model | n_features | MAE | RMSE | R² | F1@31 | P | R |
|---|---:|---:|---:|---:|---:|---:|---:|
| M4_inertia_ridge | 18 | **0.5932** | 0.7949 | 0.846 | 0.153 | 0.250 | 0.110 |
| M3_weather_ridge | 14 | 0.6050 | 0.8114 | 0.840 | 0.114 | 0.429 | 0.066 |
| M5_v10_morphology_ridge | 15 | 0.6306 | 0.8404 | 0.826 | 0.133 | 0.205 | 0.099 |
| M6_v10_overhead_ridge | 17 | 0.6306 | 0.8404 | 0.826 | 0.133 | 0.205 | 0.099 |
| M7_compact_weather_ridge | 8 | 0.6306 | 0.8404 | 0.826 | 0.133 | 0.205 | 0.099 |
| M1b_period_bias | 0 | 0.7580 | 1.0232 | 0.741 | 0.083 | 0.172 | 0.055 |
| M0_raw_proxy | 0 | 1.2081 | 1.7317 | 0.256 | n/a | n/a | 0 |

### 5.4 Hourly max target

| Model | n_features | MAE | RMSE | R² | F1@31 fixed_31 | P | R | events |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M4_inertia_ridge | 18 | **0.6385** | 0.864 | **0.854** | **0.6316** | 0.682 | 0.588 | 204 |
| M3_weather_ridge | 14 | 0.6484 | 0.873 | 0.851 | 0.5833 | 0.673 | 0.515 | 204 |
| M5_v10_morphology_ridge | 15 | 0.6824 | 0.915 | 0.836 | 0.6393 | 0.722 | 0.574 | 204 |
| M6_v10_overhead_ridge | 17 | 0.6824 | 0.915 | 0.836 | 0.6393 | 0.722 | 0.574 | 204 |
| M7_compact_weather_ridge | 8 | 0.6824 | 0.915 | 0.836 | 0.6393 | 0.722 | 0.574 | 204 |
| M1b_period_bias | 0 | 0.7877 | 1.083 | 0.770 | 0.4038 | 0.566 | 0.314 | 204 |
| M0_raw_proxy | 0 | 1.4720 | 2.111 | 0.127 | n/a | n/a | 0 | 204 |

---

## 6. Threshold operating points

### 6.1 Hourly_max, n=1,674, n_pos=204

| Model | Operating point | Threshold | P | R | F1 | TP | FP | FN |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| M3 | fixed_31 | 31.00 | 0.673 | 0.515 | 0.583 | 105 | 51 | 99 |
| M3 | best_F1 | 30.20 | 0.603 | 0.917 | 0.728 | 187 | 123 | 17 |
| M3 | recall_90 | 30.20 | 0.603 | 0.917 | 0.728 | 187 | 123 | 17 |
| M3 | precision_70 | 31.20 | 0.701 | 0.299 | 0.419 | 61 | 26 | 143 |
| M4 | fixed_31 | 31.00 | 0.682 | 0.588 | 0.632 | 120 | 56 | 84 |
| M4 | best_F1 | 30.70 | 0.683 | 0.770 | 0.724 | 157 | 73 | 47 |
| M4 | recall_90 | 30.00 | 0.549 | 0.936 | 0.692 | 191 | 157 | 13 |
| M4 | precision_70 | 31.20 | 0.703 | 0.382 | 0.495 | 78 | 33 | 126 |
| M5/M6/M7 | fixed_31 | 31.00 | 0.722 | 0.574 | 0.639 | 117 | 45 | 87 |
| M5/M6/M7 | best_F1 | 30.25 | 0.620 | 0.833 | 0.711 | 170 | 104 | 34 |
| M5/M6/M7 | recall_90 | 29.25 | 0.492 | 0.917 | 0.640 | 187 | 193 | 17 |
| M5/M6/M7 | precision_70 | 30.90 | 0.713 | 0.583 | 0.642 | 119 | 48 | 85 |

### 6.2 Interpretation

- `fixed_31` is the prospective, deployment-like operating point.
- `best_F1` is a retrospective upper bound and should not be used as deployment threshold without an independent validation set.
- `recall_90` and `precision_70` are policy trade-off diagnostics.
- The reported v2.1 F1=0.639 for M5/M7 is confirmed to be **fixed_31**, not tuned.

### 6.3 Operational primary and alternative

**Recommended primary**:

```text
M4_inertia_ridge + hourly_max target + fixed_31 threshold
```

This is a **physics-first / recall-oriented operational primary** because it:

```text
- preserves the full weather + inertia feature set;
- has the best hourly_max regression MAE/R²;
- improves fixed_31 recall over M3;
- aligns directly with the NEA 31°C threshold without tuning.
```

**Compact alternative**:

```text
M7_compact_weather_ridge + hourly_max target + fixed_31 threshold
```

This is a **compact precision-oriented alternative** because it has:

```text
- slightly higher fixed_31 precision and F1 than M4;
- lower recall than M4;
- fewer features and a cleaner operational decision boundary.
```

Precise trade-off:

```text
Compared with M3:
    M4 captures 15 additional true positives at fixed_31 (120 vs 105).

Compared with M7:
    M4 captures 3 additional true positives (120 vs 117),
    but incurs 11 additional false positives (56 vs 45).
```

---

## 7. Bootstrap M4-M3 advantage

### 7.1 Method

5,000-iteration fold-level block bootstrap:

```text
unit = LOSO fold
statistic = mean per-fold delta = MAE(M4) - MAE(M3)
negative delta = M4 better
```

Row-level bootstrap is avoided because row-level samples are autocorrelated within station/time folds.

### 7.2 Results

| Evaluation framing | n_folds | n_obs | M3 MAE | M4 MAE | mean Δ | 95% CI | p | excludes 0 |
|---|---:|---:|---:|---:|---:|---|---:|---|
| A_all | 27 | 5,724 | 0.6673 | 0.6555 | -0.0118 | [-0.0218, -0.0022] | 0.019 | ✓ |
| B_retrospective | 27 | 5,724 | 0.6673 | 0.6555 | -0.0118 | [-0.0215, -0.0019] | 0.017 | ✓ |
| C_fresh_v11 | 4 | 810 | 0.3450 | 0.3442 | -0.0010 | [-0.0252, +0.0206] | 0.920 | ✗ |
| D_migrated | 26 | 5,372 | 0.6954 | 0.6774 | -0.0179 | [-0.0287, -0.0070] | 0.002 | ✓ |
| all_stations | 27 | 5,724 | 0.6673 | 0.6555 | -0.0118 | [-0.0217, -0.0024] | 0.014 | ✓ |
| hourly_max | 27 | 1,674 | 0.6484 | 0.6385 | -0.0098 | [-0.0215, -0.0000] | 0.049 | ✓ border |
| hourly_mean | 27 | 1,674 | 0.6050 | 0.5932 | -0.0118 | [-0.0245, +0.0005] | 0.062 | ✗ border |
| no_S142 † | 25 | 5,512 | 0.6526 | 0.6407 | -0.0119 | [-0.0226, -0.0013] | 0.026 | ✓ |

**†** `no_S142` 的 `n_folds = 25` 来自 station-grouped bootstrap：26 unique stations 中 1 个 station 在 LOSO + retrospective filter 后 M3 或 M4 预测被 NaN-dropped（insufficient valid predictions）。`v11_beta_bootstrap_advantage.py` v1 输出的 `n_folds = 27` 反映 `fold` column unique 值计数（含原始 27-station LOSO 索引 convention artifact）；表中其他 framings 仍使用脚本原始输出。manual 重 bootstrap (5,000-iter, station_id groupby, dropna) 得 mean=−0.0119°C、95% CI [−0.0226, −0.0013]、p=0.026 — **统计结论 unchanged**（CI 排除 0，effect size 与原报告一致）。

14-day formal pass 应统一所有 framings 改用 station-grouped fold counting；no_S142 case study 显示 mean delta 与 excludes_0 conclusion robust to 该 convention change。

### 7.3 Interpretation

```text
M4 advantage is statistically detectable in 6/8 evaluation framings,
but all observed effects are below the 0.03°C practical contribution threshold.
```

Therefore:

```text
M4 inertia features are retained.
M4 advantage is real enough to track.
But current effect size is practical-small, not a major model breakthrough.
```

---

## 8. Key findings

### 8.1 Proxy structural under-prediction reproduced

Multi-day framings reproduce the v0.9 structural under-prediction magnitude:

| Evaluation framing | M0 bias |
|---|---:|
| v0.9-beta 24h | -1.140°C |
| v11 A_all 15-min | -1.125°C |
| v11 hourly_mean | -1.042°C |
| v11 no_S142 | -1.150°C |

Careful wording:

```text
This is not evidence from source-independent archives. It is evidence from
migrated + fresh segments and multiple evaluation framings of the v1.1 archive.
```

### 8.2 Hourly aggregation is a method choice

```text
15-min A_all M3 MAE:     0.667°C
hourly_mean M3 MAE:     0.605°C
improvement:            0.062°C
```

Interpretation:

```text
15-min WBGT observations contain within-hour variation that hourly Open-Meteo
forcing cannot explain. Hourly aggregation removes cadence-mismatch noise.
```

### 8.3 Hourly-max is the operational warning target

Fixed_31 F1:

```text
15-min:       0.10–0.23
hourly_mean:  0.11–0.15
hourly_max:   0.58–0.64
```

Therefore:

```text
Operational warning evaluation should use hourly-max WBGT, not 15-min point
WBGT or hourly-mean WBGT alone.
```

### 8.4 M5/M6/M7 equivalence is audit-proof under current station network

H10 result:

```text
hourly aggregator forwards static morph/overhead/grid columns;
M5/M6/M7 still bit-identical.
```

Qualified conclusion:

```text
morphology contribution to the current station-level ridge calibration LOSO
predictions under the current NEA station network and imputer/scaler pipeline = 0.
```

Not allowed conclusion:

```text
urban morphology has no physical effect on pedestrian heat exposure.
```

Correct dissertation statement:

> The current NEA station network makes the Toa Payoh morphology calibration question structurally unidentifiable. This is a station-network limitation, not a physical null result.

### 8.5 S142 remains a high-tail dominance issue

```text
S142 rows:            3.7% of observations
S142 ≥33 events:      65.5% of ≥33 events
S142 excluded rows:   0 in no_S142 sensitivity
no_S142 stations:     26
```

Interpretation:

```text
≥33 threshold modeling remains exploratory until archive duration grows and
non-S142 high events accumulate.
```

### 8.6 Practical calibration floor hypothesis

Current evidence suggests:

```text
M3/M4 LOSO MAE has a practical floor near 0.6°C under the current station network
and Open-Meteo gridded forcing setup.
```

But this remains a hypothesis.

Formal pass should test:

```text
hourly_mean M3/M4 MAE remains in [0.55, 0.70]°C
```

---

## 9. Dissertation-ready wording

### 9.1 Archive / proxy validation

> The v0.9 production WBGT proxy applied to the v1.1 archive yields a systematic under-prediction across multi-day evaluation framings. The 15-minute A_all framing and the hourly-mean framing yield M0 biases of approximately -1.13°C and -1.04°C respectively, reproducing the v0.9-beta single-day bias of -1.14°C to within 0.10°C. These framings are evaluator-independent across CV folds, station sets, and aggregation cadences but not source-independent, because the v1.1 archive incorporates migrated v0.9 and v10 segments alongside fresh v11 collector data. The consistency of bias magnitude supports the interpretation that the proxy's under-prediction is a structural property of the formula rather than a schema or sampling artifact.

### 9.2 Calibration ladder and M7

> The v1.1-β.1 calibration ladder follows the v0.9-beta structure: M0 raw proxy, M1 global bias, M1b period bias, M2 linear proxy, M3 weather ridge, M4 inertia ridge, M5 morphology ridge, and M6 overhead ridge. M7_compact_weather_ridge is introduced as an 8-feature compact baseline encoding the effective feature set of M5/M6 under the current station network. After explicitly forwarding morphology and overhead columns through hourly aggregation, M5 and M6 remain numerically identical to M7 across all v1.1-β.1 evaluation framings. M7 is therefore the honest compact baseline; M5 and M6 are retained as null-result audit artifacts demonstrating network sparsity.

### 9.3 Operational warning target

> For operational heat-stress warnings, we recommend evaluating hourly-maximum WBGT. The physics-first primary baseline is M4_inertia_ridge with hourly-max target and fixed 31°C threshold, achieving LOSO precision 0.68, recall 0.59, and F1 0.63 on the current archive. This threshold requires no deployment-time tuning because it matches the NEA WBGT alerting threshold. M7_compact_weather_ridge is retained as a compact precision-oriented alternative with slightly higher precision and F1 but lower recall. The 15-minute evaluation cannot achieve comparable fixed-threshold performance, confirming hourly-max as the appropriate operational target.

### 9.4 Morphology unidentifiability

> M5 and M6 produce numerically identical out-of-fold predictions to M7 across all v1.1-β.1 evaluations after the aggregator explicitly forwards morphology and overhead columns. The mechanism is signal-level: only one of 27 NEA WBGT stations, S128, is mapped into the Toa Payoh 100m grid AOI. Under LOSO cross-validation, morphology columns are either dropped as all-NaN when S128 is held out, or imputed to a constant value and neutralized by StandardScaler when S128 is in training. The morphology calibration question is therefore structurally unidentifiable under the current station network. This does not negate v10's spatial morphology findings; it limits station-level calibration inference in v1.1.

---

## 10. Formal beta hypotheses

**Methodological item carried into formal pass**: bootstrap script (`v11_beta_bootstrap_advantage.py` v1) 当前用 OOF predictions 的 `fold` column 做 groupby; 在 holdout-station framings (如 `no_S142`) 上, 该 convention 偏离 station-grouped ground truth (§7.2 †)。formal-pass v2 应统一改 `station_id` + `dropna` groupby; no_S142 case study 显示 statistical conclusion robust to this change, 但 8 个 framings 全部 re-verify 是 formal-pass methodological 任务。

### Already verified

```text
H0: stale-dilution hypothesis is false.
H10: M5/M6/M7 remain identical after hourly aggregator forwards static morph/overhead columns.
```

### 14-day formal pass hypotheses

| ID | Hypothesis | Current status |
|---|---|---|
| H1 | M0 bias in multi-day framings remains roughly [-1.05, -1.40]°C | pending formal pass |
| H2 | M3 LOSO MAE remains in [0.55, 0.70]°C | pending |
| H3 | M4-M3 is statistically distinguishable from 0 in multi-day framings, but practical-small | pending |
| H4 | M1b vs M3 gap ≥ 0.20°C | pending |
| H5 | S142 share of ≥33 events decreases to ≤55% or is confirmed as station-level outlier | pending |
| H6 | M5/M6/M7 identity persists | pending |
| H7 | hourly_max M7 fixed_31 F1 ≥ 0.55 | pending |
| H8 | hourly_mean M3 MAE differs from v0.9 M3 by ≤0.05°C | pending |
| H9 | M7 hourly_max fixed_31 precision ≥0.65 and recall ≥0.50 | pending |
| H11 | M4 hourly_max recall_90 threshold remains in [29.5, 30.5]°C | pending |

### 30-day v1.1-gamma ML gates

ML residual learning should not start until:

```text
- archive ≥ 30 days;
- WBGT ≥31 events ≥ 1,500;
- WBGT ≥33 events ≥ 100;
- at least 3 weather regimes;
- hourly_max fixed_31 F1 remains ≥0.55;
- M3/M4 baselines are stable under LOSO and blocked-time CV.
```

---

## 11. Command reference

### 11.1 v2.2 full run

```bat
REM archive loop continues in another window

python scripts\v11_beta_build_features.py
scripts\v11_run_alpha_archive_from_collector_pipeline.bat

python scripts\v11_beta_calibration_baselines.py --config configs\v11\v11_beta_calibration_config_v091.json
python scripts\v11_beta_calibration_baselines.py --config configs\v11\v11_beta_calibration_config_v091_no_S142.json

python scripts\v11_beta_ablation_runner.py

python scripts\v11_beta_aggregate_hourly.py
python scripts\v11_beta_calibration_baselines.py --config configs\v11\v11_beta_calibration_config_v091_hourly_mean.json
python scripts\v11_beta_calibration_baselines.py --config configs\v11\v11_beta_calibration_config_v091_hourly_max.json

python scripts\v11_beta_bootstrap_advantage.py

python scripts\v11_beta_threshold_scan.py --config configs\v11\v11_beta_calibration_config_v091_hourly_max.json
python scripts\v11_beta_threshold_scan.py --config configs\v11\v11_beta_calibration_config_v091.json --target-event-c 31
```

### 11.2 no_S142 validation

```bat
python -c "import pandas as pd; p='outputs/v11_beta_calibration/no_S142/v11_beta_oof_predictions.csv'; d=pd.read_csv(p); print(d['station_id'].nunique()); print(sorted(d['station_id'].astype(str).unique())); print('S142 rows:', (d['station_id'].astype(str)=='S142').sum())"
```

Expected:

```text
26
S142 rows: 0
```

### 11.3 Formal pass snapshot

```bat
scripts\v11_beta_freeze_snapshot.bat 14d_formal
```

All formal pass configs should point to the frozen snapshot. Do not compare all/no_S142/hourly/ablation runs generated from a live-growing archive.

---

## 12. File outputs

```text
data/calibration/v11/
├── v11_station_weather_pairs.csv
├── v11_station_weather_pairs_v091.csv
├── v11_station_weather_pairs_hourly.csv
└── snapshots/

outputs/v11_beta_calibration/
├── all_stations/
├── no_S142/
├── ablation_A_all/
├── ablation_B_retrospective/
├── ablation_C_fresh_v11/
├── ablation_D_migrated/
├── hourly_mean/
├── hourly_max/
├── bootstrap_M4_minus_M3.csv
├── fold_level_M3_M4_delta_by_dataset.csv
└── v11_beta_ablation_*.csv
```

---

## 13. Decision log

| Date | Decision | Alternative | Reason |
|---|---|---|---|
| 5/10 | Lift v0.9 proxy and lag features | Write new formulas | Reuse validated v0.9 implementation |
| 5/10 | Add retrospective pairing flag in build_features | Modify collector immediately | Do not interrupt archive loop |
| 5/10 | Run A/B/C/D ablation | Keep stale-dilution assumption | Stale-dilution needed empirical test |
| 5/10 | Run hourly mean/max immediately | Wait 14 days | Hourly aggregation was a method bug, not just long-run task |
| 5/10 | Add M7 compact weather baseline | Keep M5 as operational winner | Avoid misleading morphology model claim |
| 5/11 | Forward static morph/overhead columns in hourly aggregator | Explain aggregator drop | H10 keystone; removes code-path artifact concern |
| 5/11 | Use fold-level block bootstrap | Row-level bootstrap | LOSO folds are independent evaluation units |
| 5/11 | Adopt M4 as physics-first primary, M7 as compact alternative | Single winner | Different policy priorities: recall/physics vs precision/compactness |
| 5/11 | Require frozen snapshot for formal pass | Use live archive | Avoid archive-growth drift between sensitivity runs |

---

## 14. Maintenance

**Next update triggers**:

```text
- 14-day formal pass complete → OpenHeat_v11_beta_formal_findings_report_CN.md
- 30-day archive ML gate reached → OpenHeat_v11_gamma_findings_report_CN.md
- NEA / Open-Meteo schema changes → update handoff + collector docs
- fifth audit, if any → v2.3 / v3
```

**Document chain**:

```text
docs/handoff/OpenHeat_v10_to_v11_HANDOFF_CN.md
  ↓
docs/v11/OpenHeat_v11_alpha_beta_HANDOFF_CN.md
  ↓
docs/v11/OpenHeat_v11_beta1_findings_report_CN_v1_archived.md
  ↓
docs/v11/OpenHeat_v11_beta1_findings_report_CN_v2_archived.md
  ↓
docs/v11/OpenHeat_v11_beta1_findings_report_CN_v2_1_archived.md
  ↓
docs/v11/OpenHeat_v11_beta1_findings_report_CN.md     ← this v2.2 FINAL, canonical
  ↓
docs/v11/OpenHeat_v11_beta_formal_findings_report_CN.md
  ↓
docs/v11/OpenHeat_v11_gamma_findings_report_CN.md
```

---

## 15. Final status

```text
v1.1-alpha archive infrastructure: passed
v1.1-beta.1 audit trail: passed
v1.1-beta.1 v2.2 FINAL: canonical pre-formal report
v1.1-beta formal science: pending 14-day frozen snapshot
v1.1-gamma ML: pending 30-day archive and gate checks
```

**Final one-line interpretation**:

> v1.1-β.1 v2.2 FINAL confirms that OpenHeat's v11 archive can reproduce v0.9 proxy bias, that stale-dilution was not the cause of ridge degradation, that hourly-max is the appropriate operational target, and that morphology/overhead calibration is structurally unidentifiable under the current NEA station network. The next scientific milestone is the 14-day formal beta pass on a frozen snapshot; ML remains deferred until 30+ days.

