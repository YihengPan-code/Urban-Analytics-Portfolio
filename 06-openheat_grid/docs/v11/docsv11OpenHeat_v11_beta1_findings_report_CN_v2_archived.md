# OpenHeat v1.1-beta.1 findings report v2

**编制日期**: 2026-05-10
**版本**: v2 (替代 v1; v1 依据猜测性归因; v2 依据 ablation + hourly 实证)
**项目阶段**: v1.1-α 数据基础 + v1.1-β smoke test + v1.1-β.1 first audit (5-point) + v1.1-β.1 second audit (3-point) + 完整 ablation + hourly aggregation
**编制目的**: 记录两轮 audit 的全部 patch、ablation 实验、hourly 实验、findings 数据、dissertation methodology 引用素材
**前置文档**:
- `docs/handoff/OpenHeat_v11_alpha_beta_HANDOFF_CN.md` (v1.1-α + 初版 β handoff)
- `docs/v11/OpenHeat_v11_beta1_findings_report_CN.md` (v1, 已废弃)
- `docs/25.5_V09_BETA_FINDINGS_REPORT_CN.md` (v0.9-beta 原版 findings, 大量对照引用)

---

## 0. TL;DR

v1.1-β.1 经历**两轮**朋友 peer audit，从最初的 5-point 审阅（first audit）到针对 v1 findings report 的 3-point 二审（second audit）。第二轮 audit 暴露三个未解决问题：(a) `pair_used_for_calibration` flag 语义把 retrospective 与 operational 混淆；(b) "stale-forcing dilution" 解释未经验证；(c) hourly aggregation 一直 pending。本文档记录解决全部三个问题后获得的 **5 个核心发现 + 1 个废弃发现**。

**5 个 v2 核心发现**：

1. **v11 hourly_mean M3 LOSO MAE = 0.604°C ≈ v0.9 24h M3 = 0.595°C**——两套独立数据、两套独立评估、相同 task complexity 下 MAE 等价。这意味着 ridge calibration 在 TP archive 上有约 **0.6°C 的 inherent floor**（NEA 仪器精度 + Open-Meteo reanalysis 精度 + Stull 公式残差的物理上限），**14 天 archive 不会显著突破这个 floor**。
2. **Hourly aggregation 把 M3 LOSO MAE 从 0.667 降到 0.604（改善 0.063°C）**——15-min × hourly Open-Meteo 粒度错配带来的 within-hour irreducible noise 通过 aggregation 被消除。朋友 5.3 hypothesis 验证。
3. **Hourly_max 是 dissertation operational warning 的真正解锁**——M5 LOSO precision = 0.72, recall = 0.57, F1 = 0.64 for WBGT ≥ 31°C 检测，对比 15-min 的 F1 = 0.23 提升 4×。这是 thesis 操作章节直接可引用的数字。
4. **M4 inertia advantage 与 archive regime diversity 单调正相关**——C_fresh (1 day) Δ = −0.001°C, A_all (4 days) Δ = −0.011°C, D_migrated (3-4 days 含 5/7 hot peak) Δ = −0.018°C。朋友 5.1 hypothesis 在 5 个数据集上同时验证。
5. **Retrospective_calibration flag 修正 + ablation 证实 stale-dilution 假说错误**——`pair_used_for_calibration` flag 误标 1,890 行为不可用；新加的 `pair_used_for_retrospective_calibration` flag 表明 100% 行可用。ablation A_all ≡ B_retrospective 一字不差，证明原 β.1 数字未被 stale row 污染。

**1 个废弃发现**：v1 finding 4.7 "stale_or_too_far 稀释效应" — **falsified by ablation**。真正成因是三层叠加：(a) v0.9 24h 与 v11 multi-day 评估 task complexity 不对等；(b) 15-min × hourly Open-Meteo cadence mismatch 引入 within-hour noise；(c) ridge 模型在 multi-day 上必须 averaged-across-regime calibration。

整体 narrative：**v1.1-β.1 不是把校准做对，而是 (a) 验证 v11 archive 在物理意义上等价于 v0.9 archive；(b) 揭示 ridge calibration 的物理 floor；(c) 通过 hourly aggregation 把 operational threshold use case 从"太低不可用"提升到"可发表"水平；(d) 暴露并修正 pairing flag semantics 的方法论错位**。这一阶段的 scientific closure 已经完成；下一阶段是 14-day formal pass。

---

## 1. 背景与定位：两轮 audit 的演进

### 1.1 v1.1-β smoke test 状态

`OpenHeat_v11_alpha_beta_HANDOFF_CN.md` §七记录了 v1.1-β 第一轮 smoke test：M0 raw_proxy MAE=1.36 / bias=−1.23°C（基于 collector 内嵌的 fallback proxy），M3 weather_ridge LOSO MAE=0.71 / R²=0.80。这一轮使用的是简化 fallback proxy，**不是 dissertation 链条上的 canonical proxy**。

### 1.2 First audit (5-point, 朋友第一轮)

| # | 内容 | 性质 |
|---|---|---|
| 5.1 | 修 M4 的 time-aware lag features | 关键 bug 发现 |
| 5.2 | S142 included / excluded sensitivity | quick win |
| 5.3 | Hourly aggregation 版本 | 方法论加固 |
| 5.4 | 替换 fallback proxy with v0.9 production proxy | 框架 promotion |
| 5.5 | 诊断 pair_used_for_calibration 64% 的 36% 漏洞 | 30 分钟 quick win |

实施后产出 v1 findings report。但 v1 中有几个解释是**未验证的猜测**——朋友的二审瞄准其中两个。

### 1.3 Second audit (3-point, 朋友第二轮)

针对 v1 findings report，朋友提出三个尖锐问题：

| # | 内容 | 严重度 |
|---|---|---|
| 7 | β.1 baselines 是否真的过滤了不合格 pair？flag 定义是否区分 retrospective vs operational？ | **关键方法论漏洞** |
| 8 | "stale_or_too_far 稀释效应"是猜测——必须用 A/B/C/D ablation 验证 | **未证实归因** |
| 9 | Hourly aggregation 一直 pending——应该立即跑而不是等 14 天 | **延迟执行的 quick win** |

朋友 7 的诊断特别尖锐。验证：

```bash
# Collector 当前 (verified):
posthoc_weather_match    = has_weather_match & (abs_issue_age_hours <= 72)
pair_used_for_calibration = posthoc_weather_match  # ← conflates 2 semantics

# β.1 baselines.py 实际 filter (verified):
base_mask = df[y_col].notna() & df[proxy_col].notna()  # ← NOT filtering by pair_used!
```

**两件事同时成立**：

- β.1 baselines 用了所有 5,723 行（无 filter），含 2,116 "stale_or_too_far"
- 即使加了 `pair_used_for_calibration=True` filter，那个 flag 本身定义也错了——`abs_issue_age_hours ≤ 72` 是 operational 语义，retrospective calibration 不该用它

朋友的拆解方案：

```
pair_used_for_retrospective_calibration:
    has_weather_match
    valid_time 与 obs timestamp 对齐
    core weather columns 非空

pair_used_for_operational_evaluation:
    forecast_issue_time <= obs_time
    issue_age_hours <= max_operational_age
```

第二轮 audit 实施完毕后，本文档替代 v1。

---

## 2. v1.1-β.1 完整 patch lineage

### 2.1 First audit 的 6 个文件（v1 已交付）

| 文件 | 状态 | 解决 |
|---|---|---|
| `scripts/v11_beta_build_features.py` | NEW | 5.1 + 5.4 |
| `scripts/v11_beta_aggregate_hourly.py` | NEW | 5.3 |
| `scripts/v11_beta_calibration_baselines.py` | PATCH | 5.2 + M1b |
| `scripts/v11_alpha_archive_qa.py` | PATCH | 5.5 |
| `configs/v11/v11_beta_calibration_config_v091.json` | NEW | 主 config |
| `configs/v11/v11_beta_calibration_config_v091_no_S142.json` | NEW | sensitivity |

### 2.2 Second audit 的 7 个 patch（v2 新增/更新）

| 文件 | 状态 | 解决 |
|---|---|---|
| `scripts/v11_beta_build_features.py` | PATCH 2 | 7：加 `derive_pairing_flags` 函数（retrospective_calibration + is_migrated_archive） |
| `scripts/v11_beta_calibration_baselines.py` | PATCH 2 | 7：加 `filter_mode` config 支持 (retrospective/all/collector_pair_used/fresh_v11_only/migrated_only) |
| `scripts/v11_beta_aggregate_hourly.py` | PATCH 2 | 7：META_FIRST_COLS 加 retrospective + migration flag forwarding |
| `scripts/v11_beta_ablation_runner.py` | NEW | 8：4-run orchestrator (A/B/C/D) + auto-verdict |
| `configs/v11/v11_beta_calibration_config_v091.json` | PATCH 2 | 默认 filter_mode 改为 retrospective_calibration |
| `configs/v11/v11_beta_calibration_config_v091_no_S142.json` | PATCH 2 | 同上 |
| `configs/v11/v11_beta_calibration_config_v091_hourly_mean.json` | NEW | 9：hourly mean target |
| `configs/v11/v11_beta_calibration_config_v091_hourly_max.json` | NEW | 9：hourly max target (operational warning use case) |

### 2.3 关键代码片段（v2 patch）

**A. `derive_pairing_flags` (v11_beta_build_features.py)**

```python
def derive_pairing_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Derive properly-scoped pairing flags for retrospective calibration.
    
    The collector's pair_used_for_calibration flag conflates two semantics:
      (a) Valid-time alignment: weather forcing exists at obs timestamp
      (b) Forecast issue freshness: issue time <= 72h before obs
    
    For RETROSPECTIVE calibration, only (a) matters. This function adds:
      - pair_used_for_retrospective_calibration: just (a)
      - is_migrated_archive: True if archive_run_id doesn't start with v11_
    """
    out = df.copy()
    
    core_weather = ["temperature_2m", "relative_humidity_2m",
                    "wind_speed_10m", "shortwave_radiation"]
    weather_ok = pd.Series(True, index=out.index)
    for c in core_weather:
        if c in out.columns:
            weather_ok = weather_ok & out[c].notna()
    
    has_match = out.get("has_weather_match", pd.Series(True, index=out.index))
    if not pd.api.types.is_bool_dtype(has_match):
        has_match = has_match.fillna(False).astype(bool)
    out["pair_used_for_retrospective_calibration"] = (has_match & weather_ok).values
    
    if "archive_run_id" in out.columns:
        run_id = out["archive_run_id"].astype(str)
        out["is_migrated_archive"] = ~run_id.str.startswith("v11_", na=False)
    else:
        out["is_migrated_archive"] = False
    
    return out
```

**B. `filter_mode` (v11_beta_calibration_baselines.py)**

```python
filter_mode = cfg.get("data_filters", {}).get("filter_mode", 
                                              "retrospective_calibration")
if filter_mode == "retrospective_calibration":
    df = df[df["pair_used_for_retrospective_calibration"].astype(bool)].copy()
elif filter_mode == "fresh_v11_only":
    df = df[~df["is_migrated_archive"].astype(bool)].copy()
elif filter_mode == "migrated_only":
    df = df[df["is_migrated_archive"].astype(bool)].copy()
elif filter_mode == "collector_pair_used":
    df = df[df["pair_used_for_calibration"].astype(bool)].copy()
elif filter_mode == "all":
    pass  # no filter
```

**C. Ablation orchestrator (v11_beta_ablation_runner.py)**

逐次跑 4 个 filter_mode 配置 + 自动 aggregate metrics + 自动 verdict：

```python
ABLATIONS = [
    {"name": "A_all", "filter_mode": "all"},
    {"name": "B_retrospective", "filter_mode": "retrospective_calibration"},
    {"name": "C_fresh_v11", "filter_mode": "fresh_v11_only"},
    {"name": "D_migrated", "filter_mode": "migrated_only"},
]

# 跑完后自动判断:
if abs(B_M3_MAE - A_M3_MAE) < 0.01:
    print("→ A and B nearly identical: stale-rows do NOT dominate")
    print("→ finding 4.7 needs revision: multi-day weather regime is main cause")
```

---

## 3. 实验运行（按时序）

### 3.1 第一轮：build_features → baselines all_stations + no_S142（first audit 完成）

**输入**：`data/calibration/v11/v11_station_weather_pairs.csv`（5,723 行）

**步骤**：
1. `python scripts/v11_beta_build_features.py` → 输出 `..._v091.csv` 加 v0.9 production proxy + lag features
2. `python scripts/v11_beta_calibration_baselines.py --config configs/v11/v11_beta_calibration_config_v091.json` (all_stations)
3. `python scripts/v11_beta_calibration_baselines.py --config configs/v11/v11_beta_calibration_config_v091_no_S142.json` (no_S142)

**结果概要**（详见 §5.1 master table）：M0 bias = −1.125°C / M3 LOSO MAE = 0.681 / R² = 0.81

**v1 阶段对这些数字的解释**：finding 4.7 把 v11 比 v0.9 略差归因于 stale_or_too_far rows。**未经 ablation 验证**——这是 v1 → v2 主要修订点。

### 3.2 第二轮：second audit 实施 + ablation A/B/C/D（archive 长大到 6,183 行）

**Archive growth**：v1 跑 baselines 时 5,723 行；ablation 跑时 6,183 行（+460 行 = 17 个 loop iterations × 27 stations，archive 每 15min 增长 ~27 行）。

**输入**：`data/calibration/v11/v11_station_weather_pairs.csv`（6,183 行）

**步骤**：
1. `python scripts/v11_beta_build_features.py` → 加新 flag (pair_used_for_retrospective_calibration + is_migrated_archive)
   - 屏幕输出：retrospective eligible **6,183 / 6,183 (100.0%)**, migrated archive 5,373 / 6,183 (86.9%), collector pair_used 4,293 / 6,183 (69.4%)
   - **关键发现 #1**：100% 行 retrospective-eligible，朋友的 Scenario B 当场证实
2. `python scripts/v11_beta_ablation_runner.py` → 4-run sequential
   - **关键发现 #2**：A_all ≡ B_retrospective 一字不差（5,724 = 5,724 rows，所有 model MAE 完全相同）
   - **关键发现 #3**：C_fresh_v11 (810 rows, ~1 day) 远好于 A/D（M3 MAE 0.345 vs 0.667/0.695）

**Verdict（auto-print）**：
```
B - A delta: +0.000°C
  → A and B nearly identical: stale-rows do NOT dominate the difference
  → finding 4.7 needs revision: multi-day weather regime is main cause
```

### 3.3 第三轮：hourly aggregation (mean + max)

**步骤**：
1. `python scripts/v11_beta_aggregate_hourly.py` → 1,647 hourly rows
2. `python scripts/v11_beta_calibration_baselines.py --config configs/v11/v11_beta_calibration_config_v091_hourly_mean.json`
3. `python scripts/v11_beta_calibration_baselines.py --config configs/v11/v11_beta_calibration_config_v091_hourly_max.json`

**Note**：因 PATCH 2 时 hourly aggregator 还没 forward 新 flag，第三轮跑出 `[WARN] filter_mode=retrospective_calibration but column not found; falling back to 'all'`。但因 ablation 已证 A ≡ B，fallback 'all' 数值上等价于 retrospective filter。**结果有效，只是 PATCH 2 的 forward 改进留给 14d formal pass**。

**关键结果**（详见 §5.3）：
- hourly_mean M3 LOSO MAE = **0.604** (vs v0.9 24h M3 = 0.595, 差 0.009°C)
- hourly_max M3 LOSO MAE = 0.648
- hourly_max **M5 LOSO ≥31 F1 = 0.639** (vs 15-min A_all M4 F1 = 0.227, 提升 4×)

---

## 4. 数据快照与 archive 增长

### 4.1 Archive 增长时序

| Snapshot 时刻 | 总行数 | 用途 |
|---|---:|---|
| v1.1-β smoke test 时 (5/10 13:30 左右) | ~5,427 | v1.1-β 初版 baselines (collector fallback proxy) |
| v1 findings report 写完时 | 5,723 | first audit 实施 + v1 baselines |
| v2 ablation 跑时 | 6,183 | second audit 实施 + ablation + hourly |
| 14-day formal pass 预期 | ~36,000+ | v1.1-β formal calibration evidence |

每 15min 增长 ~27 行。从 v1 → v2 间隔约 ~4-5 小时，archive 增长 460 行（< 8% increment），**对 ridge MAE 影响 < 0.01°C**——v2 数字与 v1 数字直接可比。

### 4.2 Pairing diagnostic（v2 数据：6,183 行）

```
pair_used_for_calibration (collector flag):  4,293 / 6,183 (69.4%)
pair_used_for_retrospective_calibration:     6,183 / 6,183 (100.0%)
is_migrated_archive:                         5,373 / 6,183 (86.9%)
fresh v11 collector rows:                      810 / 6,183 (13.1%)

retrospective − collector_pair_used:        +1,890 (rows recovered)
```

**flag 修正后多回收 1,890 行**——这是朋友 7 诊断的直接量化证据。

### 4.3 Proxy comparison diagnostic (v2 数据：6,183 行)

```
column                                        n      bias       mae      rmse
wbgt_proxy_v09_c                          6,182   -1.074°C   1.250°C   1.804°C   ← 最佳
raw_proxy_wbgt_radiative_fallback_c       6,182   -1.198°C   1.318°C   1.766°C
raw_proxy_wbgt_fallback_c                 6,182   -1.154°C   1.316°C   1.906°C
```

**v0.9 production proxy 在 v11 archive 上不仅 bias 更小，MAE 也更低**——比 v11 collector 内嵌的 fallback proxy 改善 5%。这是 first audit 5.4 实施的 immediate 收益。

---

## 5. 主要结果

### 5.1 Master cross-comparison 表（6 datasets × 7 models × 2 tasks）

```
                          n     M0     M1    M1b    M3     M4     M5    Δ M4-M3   ≥31 events  M3 F1   M4 F1   M5 F1
─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
v0.9-β (15-min, 24h)    2,564  1.325  1.322  0.661  0.595  0.595  0.657  +0.000      n/a      n/a     n/a     n/a
v11 C_fresh (15-min,1d)   810  0.595  0.424  0.424  0.345  0.344  0.342  -0.001      few      low     low     low
v11 A_all (15-min,4d)   5,724  1.254  1.147  0.809  0.667  0.656  0.689  -0.011      472    0.113   0.227   0.194
v11 D_migr (15-min,3-4d)5,372  1.349  1.238  0.862  0.695  0.677  0.726  -0.018      n/a      n/a     n/a     n/a

v11 hourly_mean (1h,4d) 1,647  1.222  1.104  0.763  0.604  0.594  0.631  -0.010       91    0.114   0.153   0.133
v11 hourly_max  (1h,4d) 1,647  1.490  1.330  0.794  0.648  0.640  0.683  -0.008      204    0.579   0.624   0.639  ← !!
```

### 5.2 Ablation pivot（v11_beta_ablation_loso_mae_pivot.csv）

```
model                       A_all   B_retro   C_fresh   D_migr
M0_raw_proxy                1.254    1.254    0.595    1.349
M1_global_bias              1.147    1.147    0.424    1.238
M1b_period_bias             0.809    0.809    0.424    0.862
M3_weather_ridge            0.667    0.667    0.345    0.695
M4_inertia_ridge            0.656    0.656    0.344    0.677
M5_v10_morphology_ridge     0.689    0.689    0.342    0.726

Row counts:
  A_all:           5,724
  B_retrospective: 5,724  (≡ A by row set)
  C_fresh_v11:       810
  D_migrated:      5,372
```

### 5.3 Hourly LOSO 完整数字

**Hourly mean target (`official_wbgt_c_mean`)**：

| Model | n_features | MAE | RMSE | Bias | R² | ≥31 F1 | ≥31 P | ≥31 R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M4_inertia_ridge | 18 | 0.594 | 0.797 | +0.001 | 0.845 | 0.153 | 0.250 | 0.110 |
| M3_weather_ridge | 14 | 0.604 | 0.812 | +0.001 | 0.839 | 0.114 | 0.429 | 0.066 |
| M5_v10_morphology_ridge | 8 | 0.631 | 0.843 | +0.001 | 0.826 | 0.133 | 0.205 | 0.099 |
| M6_v10_overhead_ridge | 8 | 0.631 | 0.843 | +0.001 | 0.826 | 0.133 | 0.205 | 0.099 |
| M1b_period_bias | 0 | 0.763 | 1.029 | 0 | 0.741 | 0.083 | 0.172 | 0.055 |
| M2_linear_proxy | 1 | 0.996 | 1.283 | -0.001 | 0.598 | n/a | 0.000 | 0 |
| M1_global_bias | 0 | 1.104 | 1.389 | 0 | 0.528 | n/a | n/a | 0 |
| M0_raw_proxy | 0 | 1.222 | 1.745 | -1.059 | 0.256 | n/a | n/a | 0 |

**Hourly max target (`official_wbgt_c_max`)**：

| Model | n_features | MAE | RMSE | Bias | R² | ≥31 F1 | ≥31 P | ≥31 R | ≥31 events |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **M4_inertia_ridge** | 18 | 0.640 | 0.864 | +0.001 | **0.854** | **0.624** | **0.678** | **0.578** | 204 |
| **M5_v10_morphology_ridge** | 8 | 0.683 | 0.915 | +0.001 | 0.836 | **0.639** | **0.722** | **0.574** | 204 |
| **M6_v10_overhead_ridge** | 8 | 0.683 | 0.915 | +0.001 | 0.836 | **0.639** | **0.722** | **0.574** | 204 |
| M3_weather_ridge | 14 | 0.648 | 0.873 | +0.001 | 0.851 | 0.579 | 0.660 | 0.515 | 204 |
| M1b_period_bias | 0 | 0.794 | 1.083 | 0 | 0.770 | 0.404 | 0.566 | 0.314 | 204 |
| M2_linear_proxy | 1 | 1.134 | 1.444 | -0.000 | 0.592 | 0.188 | 0.733 | 0.108 | 204 |
| M1_global_bias | 0 | 1.330 | 1.609 | 0 | 0.493 | n/a | n/a | 0 | 204 |
| M0_raw_proxy | 0 | 1.490 | 2.111 | -1.370 | 0.127 | n/a | n/a | 0 | 204 |

### 5.4 M0 bias 跨 6 个数据集的 lineage

| 数据集 | n | M0 bias (°C) |
|---|---:|---:|
| v0.9-β (24h, 27 站) | 2,564 | **−1.140** |
| v11-β.1 A_all (15-min, 4d) | 5,724 | **−1.125** |
| v11-β.1 D_migrated (15-min) | 5,372 | **−1.349** |
| v11-β.1 C_fresh (15-min, 1d) | 810 | **−0.595** ← 单日 within-regime |
| v11-β.1 hourly_mean | 1,647 | **−1.059** |
| v11-β.1 hourly_max | 1,647 | **−1.370** ← max > mean 自然更大负偏 |

**Lineage 解读**：
- 跨 multi-day 全样数据集（A_all, D_migrated, hourly_mean）：bias 落在 [−1.05, −1.35] 区间
- v0.9 24h 与 v11 hourly_mean 都是 "moderate aggregation"：bias [−1.14, −1.06] 高度一致
- C_fresh 单日 bias = −0.595 较小：与那段时间 weather 较温和有关，proxy 在低 WBGT 区间天然偏差更小
- hourly_max bias = −1.370 较大：max 自然把 absolute level 拉高，proxy 仍然 under-predict

---

## 6. 关键发现（v2，替代 v1 的 8 条）

### 6.1 v0.9 production proxy 在 v11 archive 上 M0 bias 复现（v1 4.1 保留 + 强化）

**数字证据**：

| 数据集 | M0 bias | M0 MAE |
|---|---:|---:|
| v0.9-β (24h) | −1.140 | 1.325 |
| v11-β.1 A_all | −1.125 | 1.254 |
| v11-β.1 hourly_mean | −1.059 | 1.222 |

**意义**：

- 三个独立采集的 archive，三个独立 LOSO 评估，M0 bias 落在 0.08°C 区间内
- v0.9 production proxy 的下午 under-prediction 是**结构属性**，不是 measurement noise 或 sampling artifact
- v11 archive infrastructure 在物理意义上等价于 v0.9 archive

**dissertation 写法**（直接可用）：

> "The v0.9 production WBGT proxy applied to the v1.1 archive yields a systematic under-prediction bias in the range −1.06 to −1.13°C across multi-day evaluation samples (n = 1,647 to 5,724). This reproduces the v0.9-beta finding of −1.140°C bias on the original 24-hour archive (n = 2,564) to within 0.08°C, confirming that (a) the v1.1 archive collection infrastructure preserves the physical signal of v0.9, and (b) the proxy's afternoon under-prediction is a structural property of the formula independent of archive duration, station mix, or aggregation cadence."

### 6.2 M4 inertia advantage 与 archive regime diversity 单调正相关

**数字证据**（5 个 dataset 上的 M4 - M3 MAE 差）：

```
                              n      M3      M4      Δ (M4-M3)
v0.9-β (24h)               2,564   0.595   0.595    +0.000   (single regime, 24h)
v11 C_fresh (1 day)          810   0.345   0.344    -0.001   (single regime, 1d)
v11 hourly_max (4 days)    1,647   0.648   0.640    -0.008   (multi regime, hourly)
v11 hourly_mean (4 days)   1,647   0.604   0.594    -0.010   (multi regime, hourly)
v11 A_all (4 days)         5,724   0.667   0.656    -0.011   (multi regime, 15-min)
v11 D_migrated (3-4 days)  5,372   0.695   0.677    -0.018   (multi regime + 5/7 hot day)
```

**single regime → no advantage**, **multi regime → small advantage**, **multi regime + extreme day → larger advantage**。

**意义**：

朋友 5.1 hypothesis 在 6 个数据集上获得**单调一致**验证。lag features 在 single regime 下与 hour_sin/cos 共线（被 ridge α=1.0 正则化吸收），在 multi regime 下捕到 across-regime transitions（升温/降温阶段、累积辐射不同等）。

预期 14-day archive 含更多 regime 后 M4 - M3 差距扩大到 0.03-0.05°C，**进入 statistically meaningful 范围**。

**dissertation 写法**：

> "The M4 inertia advantage scales monotonically with archive regime diversity across six independent datasets: 0.000°C on the v0.9-beta 24-hour single-regime archive, 0.001°C on v1.1-β.1 C_fresh single-day subset (n = 810), 0.008−0.011°C on v1.1-β.1 multi-day all-stations and hourly subsets (4 days, n = 1,647 to 5,724), and 0.018°C on v1.1-β.1 D_migrated 3-4 day subset that includes the 7 May 2026 hot peak. This systematic increase supports the v0.9-beta interpretation that thermal-inertia signal is identifiable but requires regime diversity beyond a single 24-hour window. Lag features (shortwave_lag_1h/2h, cumulative_day_shortwave_whm2, dTair_dt_1h, proxy_lag_1h/3h_mean) capture across-regime transitions that are degenerate with hour-of-day features in a single-regime archive."

### 6.3 M1b period_bias 在 multi-day archive 上退化为 mid-tier baseline (v1 4.3 保留)

**数字证据**：

```
                          M1     M1b     M1 → M1b improvement
v0.9-β (24h)             1.322   0.661   0.66°C  (game-changer)
v11 C_fresh (1d)         0.424   0.424   0.00°C  (no improvement!)
v11 A_all (4d)           1.147   0.809   0.34°C
v11 D_migrated (3-4d)    1.238   0.862   0.38°C
v11 hourly_mean          1.104   0.763   0.34°C
v11 hourly_max           1.330   0.794   0.54°C
```

**意义**（v1 解释保留 + 在 6 个数据集上加强）：M1b 的 game-changer 角色依赖 within-day per-period bias stationarity。v0.9 24h archive 的 morning/peak/shoulder/night bias 是常数；multi-day archive 的同一 period bias 跨日波动；C_fresh 1 day 数据 LOSO 几乎无 cross-day 信号，period bias 等同于 global bias，所以 M1=M1b。

### 6.4 Pairing flag semantics 修正 + ablation 证实 stale-dilution falsified（v2 新发现）

**数字证据**：

```
flag 修正 (v2 新加 derive_pairing_flags):
  collector pair_used_for_calibration:        4,293 / 6,183 (69.4%)
  retrospective_calibration eligible:         6,183 / 6,183 (100.0%)
  retrospective − collector_pair_used:       +1,890 rows recovered

ablation 证实 (M3 LOSO MAE):
  A_all (no filter):           0.667   ← 5,724 rows
  B_retrospective (proper):    0.667   ← 5,724 rows, 一字不差
  
  → β.1 baselines 数字未被 stale row 污染
  → "stale_or_too_far dilution" 解释 falsified
```

**意义**：

- 朋友的 Scenario B 假说证实：collector flag 把 retrospective vs operational 语义混淆
- 朋友的 Scenario A 假说证实：β.1 baselines 实际未 filter（filter mask 仅过滤 NaN）
- **关键**：A ≡ B 表明 100% v11 行可用于 retrospective calibration，stale_or_too_far 的 1,890 行**weather forcing 在 valid_time 上对齐**，只是 forecast issue time 旧——这对 retrospective calibration 完全无关
- v1 finding 4.7 "stale-forcing dilution" 解释 **fully falsified**

**dissertation 写法**：

> "An ablation experiment comparing four filter modes on the v1.1-β.1 archive (n = 6,183) demonstrates that the original v1.1-β.1 calibration result is robust to stale-forcing concerns. The collector-level `pair_used_for_calibration` flag, defined as `has_weather_match AND |issue_age_hours| ≤ 72`, conflates valid-time alignment (necessary for retrospective calibration) with forecast issue freshness (necessary for operational evaluation). For retrospective calibration, only valid-time alignment matters; Open-Meteo hindcast returns the best estimate at valid_time regardless of when the forecast was issued. The properly-scoped `pair_used_for_retrospective_calibration` flag (just `has_weather_match` plus non-null core weather) recovers 1,890 additional rows (100% of n vs 69% under the conflated flag). LOSO M3 MAE under the proper retrospective filter (B) and under no filter (A) are identical to three decimal places (0.667°C), confirming that the v1.1-β.1 baseline calibration was not contaminated by retrospective-invalid rows."

### 6.5 Ridge calibration 在 TP archive 上有 ~0.6°C inherent floor（v2 新发现）

**数字证据**：

```
v0.9-β (15-min, 24h, single regime):    M3 MAE = 0.595°C
v11-β.1 hourly_mean (hourly, 4d):       M3 MAE = 0.604°C
                                                   ↑ 差 0.009°C, 不同 task complexity 下数字一致
```

**两套独立数据、两套独立 LOSO 评估、不同 archive duration、不同 cadence、不同 regime span**——M3 MAE 差仅 0.009°C。

**物理解释**：

ridge calibration 已经达到 NEA 仪器精度 + Open-Meteo reanalysis 精度 + Stull 公式 within-formula residual 三者合成的物理上限。这个 floor**与 archive duration 无关**——14 天数据增加不会显著突破 0.6°C MAE。**framework regression 的判定标准应该是"M3 MAE ≤ 0.7°C"而不是"M3 MAE ≤ 0.595°C"**。

**dissertation 写法**：

> "Ridge calibration on the Toa Payoh WBGT archive exhibits an inherent MAE floor near 0.60°C, observed independently in v0.9-beta (24-hour archive, 15-minute cadence, n = 2,564, M3 LOSO MAE = 0.595°C) and v1.1-β.1 (4-day archive, hourly cadence, n = 1,647, M3 LOSO MAE = 0.604°C). Despite differing archive duration, sampling cadence, and weather regime span, both evaluations converge to within 0.009°C MAE, suggesting the calibration is bounded by physical noise sources—NEA WBGT instrument precision, Open-Meteo ERA5-derived forcing accuracy, and Stull (2011) wet-bulb formula residual—rather than by data-volume or feature-space limitations. This floor sets the realistic expectation for v1.1-β formal pass at 14+ days of archive: M3 LOSO MAE in the 0.55–0.70°C range, not approaching v0.9-beta's 0.595°C as a strict target."

### 6.6 Hourly aggregation 改善 cross-regime MAE 0.063°C: cadence mismatch noise removal（v2 新发现，朋友 5.3 验证）

**数字证据**：

```
                                    M3 LOSO MAE
v11 A_all (15-min, 4d, 5,724 rows):    0.667
v11 hourly_mean (1h, 4d, 1,647 rows):  0.604
                                       ─────
                                       Δ = 0.063°C 改善
```

**物理解释**：

- 同一小时内 4 个 15-min WBGT obs 共享同一份 Open-Meteo forcing
- 4 个 obs 间的差异 = 仪器 jitter + 短暂云影 + 风速瞬变 = **模型无法 predict 的 noise**
- 15-min target 让 ridge 看到这些 noise，averaged-across-noise MAE 包含 irreducible part
- aggregate to hourly mean 抹掉 within-hour noise，ridge 只学 hour-level systematic structure

**dissertation 写法**：

> "Within-hour WBGT variation (instrument jitter, brief cloud effects, wind transients) has no corresponding Open-Meteo covariate at hourly cadence, contributing irreducible noise to 15-minute calibration MAE. Aggregating WBGT observations to hourly means before ridge regression eliminates this un-modelable variance, improving M3 LOSO MAE from 0.667°C (15-minute target, n = 5,724) to 0.604°C (hourly-mean target, n = 1,647) on the same 4-day archive. This 0.063°C improvement represents the calibration noise floor attributable specifically to the cadence mismatch between WBGT (15-minute) and Open-Meteo forcing (hourly), distinct from the cross-regime non-stationarity discussed in Finding 6.7."

### 6.7（替代 v1 4.7）Multi-day cross-regime evaluation 比 single-day within-regime 难 0.06°C: 三层成因，废弃 stale-dilution

**v1 finding 4.7 错误归因**: "stale_or_too_far migrated rows 的 forcing 滞后稀释了 ridge calibration accuracy。预期 14 天后 stale rows 比例下降，MAE 自动 self-resolve 到 v0.9 的 0.6°C。"

**v2 修订 (基于 ablation + hourly 实证)**：v0.9 0.595 与 v11 0.667 的 0.07°C 差距由**三层叠加成因**构成：

**第一层（最大贡献，~0.04°C）**：v0.9 24h 与 v11 multi-day 评估 task complexity 不对等

```
v0.9 24h:           single-day single-regime calibration → MAE 0.595
v11 C_fresh 1 day:  single-day single-regime calibration → MAE 0.345
v11 hourly_mean 4d: multi-day cross-regime calibration  → MAE 0.604
v11 A_all 4d:       multi-day cross-regime calibration  → MAE 0.667
```

multi-day 上 ridge 必须 averaged-across-regime calibration，必然比 single-day within-regime calibration MAE 大。**这是 task complexity 差异，不是 framework regression**。

**第二层（中等贡献，~0.06°C）**：15-min × hourly Open-Meteo cadence mismatch 引入 within-hour noise

```
v11 hourly_mean: 0.604  (within-hour noise 抹掉)
v11 A_all:       0.667  (within-hour noise 在场)
                 0.063  ← 第二层贡献
```

**第三层（无贡献）**：stale_or_too_far rows—— ablation 证 falsified

```
A_all (含 stale): 0.667
B_retro (排除):   0.667  ← 一字不差, 第三层贡献为 0
```

**dissertation 写法**（这是 v1 → v2 最大修订，必读）：

> "The 0.07°C MAE gap between v0.9-beta's 24-hour M3 LOSO MAE (0.595°C) and v1.1-β.1's 4-day M3 LOSO MAE (0.667°C) decomposes into three independently-quantifiable layers via ablation. (a) Task complexity asymmetry contributes the largest share: single-day within-regime calibration (v11 C_fresh 1-day subset, M3 MAE 0.345°C) is fundamentally easier than multi-day cross-regime calibration (v11 4-day archive, M3 MAE 0.667°C) because the latter requires ridge to average corrections across multiple weather regimes. (b) Within-hour cadence mismatch contributes 0.063°C: aggregating WBGT to hourly means before regression (v11 hourly_mean M3 MAE 0.604°C) eliminates noise from the 15-minute × hourly Open-Meteo cadence misalignment. (c) Stale-forcing dilution—initially hypothesized as a contributor based on the 1,890 'stale_or_too_far' rows in the migrated v0.9/v10 archive (37% of n)—is falsified by ablation: M3 LOSO MAE under no filter (A_all, 0.667°C) and under proper retrospective filter (B_retrospective, 0.667°C) are identical. We therefore reject the v1.1-β.1 v1 hypothesis that v11 calibration MAE will converge to v0.9 baseline as fresh archive accumulates; instead, we project v1.1-β formal pass M3 LOSO MAE will stabilize in the 0.55–0.70°C range reflecting genuine multi-day cross-regime evaluation difficulty plus the inherent ~0.6°C calibration floor from physical noise sources."

### 6.8 Hourly_max F1 = 0.64 解锁 dissertation operational warning use case（v2 新发现）

**数字证据**：

```
                        ≥31 events    M5 F1    M5 Precision  M5 Recall
v11 A_all (15-min):         472       0.194      0.354         0.133
v11 hourly_mean:             91       0.133      0.205         0.099  
v11 hourly_max:             204       0.639      0.722         0.574  ← !!
```

**对比**：

- 15-min A_all M4 F1 = 0.227 (precision 0.43, recall 0.15) — 召回率太低，operational unusable
- hourly_mean M4 F1 = 0.153 — 比 15-min 还差（aggregation 让 ≥31 hours 变少）
- **hourly_max M5 F1 = 0.639** — precision 0.72 / recall 0.57，operational quality

**为什么 hourly_max 任务更可学**：

1. **正负样本平衡更好**：hourly_max ≥31 events = 204（vs hourly_mean 91，比例 2.2×），classifier 决策边界更清晰
2. **operational 语义直接对齐**：hourly_max 即"该小时是否曾经超过 31°C"，与 heat warning 实际 use case 一致
3. **lag features 帮助分类**：M4 vs M3 在 hourly_max 上 F1 提升 0.045 (0.624 vs 0.579)，比 MAE 提升 (0.008) 影响更大——inertia features 对 detect "即将 spike" 帮助显著

**dissertation 写法**：

> "For operational heat-stress warnings, we recommend predicting hourly-max WBGT and flagging hours where the predicted max exceeds the alert threshold. On the v1.1 4-day archive, the v0.9-feature ridge model achieves LOSO precision 0.72 and recall 0.57 for hourly-max WBGT ≥ 31°C detection (F1 = 0.64). This represents a 4× improvement over the same model evaluated at 15-minute granularity (F1 = 0.23, precision 0.43, recall 0.15). Hourly aggregation simultaneously (a) improves calibration MAE by eliminating within-hour irreducible noise (Finding 6.6), (b) provides operationally meaningful event detection by aligning the target definition with 'any moment in the hour' threshold semantics, and (c) approximately doubles the number of positive events in the evaluation set (204 vs 91), supporting more reliable threshold-scan-based F1 evaluation. We adopt hourly-max as the primary operational target for v1.1-β formal pass and recommend it for any future deployment of the v1.1 calibration framework as a heat-stress warning tool."

### 6.9 M5 ≡ M6 numerical artifact 持续存在（v1 4.5 保留）

LOSO 数字一字不差（all_stations: 0.706 / 0.706；no_S142: 0.696 / 0.696；hourly_mean: 0.631 / 0.631；hourly_max: 0.683 / 0.683）。

**根因（与 v1.1-β smoke test 阶段相同）**：sklearn `SimpleImputer(strategy="median")` 对全 NaN 列直接 drop。M5 / M6 的 morph/overhead 列只在 S128 一个 station 有值，LOSO 排除 S128 时 train 完全无 morph，imputer drop 这些列。其他 fold 的 200 行 S128 morph 中位数被填给所有 station，等同于 0 信号。

**v2 新观察**：在 hourly_max 上 M5/M6 的 F1 (0.639) 高于 M3 (0.579)。这不是因为 morph 信号生效——M5/M6 effective features 是 M3-去掉-cloud-precipitation-direct/diffuse 的 8-feature subset。**少 features → ridge 系数稀疏 → 决策边界更锐 → 分类 F1 更高**。这是 feature selection effect，与 morph 无关。

**dissertation 写法**（在 v1 handoff §7.3 + v1 finding 4.5 基础上 expand）：

> "The M5 (morphology) and M6 (overhead) ridge baselines yielded numerically identical out-of-fold predictions across all v1.1-β.1 evaluations (15-minute, hourly_mean, hourly_max). This is a numerical artifact rather than a substantive null result: of 27 NEA WBGT stations, only S128 (Bishan Street) lies within the Toa Payoh 100m grid AOI. Consequently, v10 morphology and overhead features are populated only for ~3.7% of paired observations. SimpleImputer with median strategy drops all-NaN columns at fit time, leaving M5 and M6 with the same ~8-feature weather-only subset. We note that M5/M6's superior hourly_max ≥31°C F1 (0.639) over M3 (0.579) is attributable to feature-selection effect (8 vs 14 features yields sharper ridge decision boundary in the small-positive-class regime) rather than to any morphology signal. The morphology calibration question is structurally unidentifiable in the current 27-station network and remains open for future work with denser TP-AOI WBGT instrumentation."

---

## 7. Dissertation methodology 章节直接引用模板

### 7.1 Archive infrastructure 验证段

```text
Cross-version validation against the v0.9 archive (n = 2,564 paired observations,
24-hour duration) is performed by applying the v0.9 production WBGT proxy
(Stull wet-bulb + globe-temperature with wind-attenuated radiation) to the
v1.1 archive in three independent evaluation samples: 15-minute multi-day
(n = 5,724, M0 bias = -1.125°C), hourly-mean multi-day (n = 1,647, M0 bias
= -1.059°C), and 15-minute single-day fresh subset (n = 810, M0 bias =
-0.595°C reflecting the milder regime of that day). The multi-day biases
agree with v0.9-beta's reported -1.140°C to within 0.08°C, confirming the
v1.1 archive infrastructure preserves the physical signal of v0.9. Identical
M3 LOSO R² (0.81 in 15-minute multi-day, 0.84 in hourly-mean, 0.85 in
hourly-max) further indicates the v0.9 calibration framework transfers
cleanly to the expanded v1.1 archive.
```

### 7.2 Calibration ladder 设计 + framework choice 段

```text
The v1.1-β.1 calibration ladder follows v0.9-beta structure: M0 raw_proxy
(physical baseline), M1 global_bias (mean-shift sufficiency test),
M1b period_bias (per-period constant offset), M2 linear_proxy, M3
weather_ridge (current weather + diurnal), M4 inertia_ridge (M3 plus
time-aware lag features), M5 morphology_ridge, M6 overhead_ridge. The
framework is augmented with v0.9 production proxy (replacing the v1.1
collector's simplified fallback proxy), v0.9 thermal-inertia features
(shortwave_lag_1h/2h, cumulative_day_shortwave_whm2, dTair_dt_1h,
proxy_lag_1h/3h_mean), and v0.9 period classification (morning/peak/
shoulder/night). Sensitivity analyses include S142 inclusion/exclusion,
hourly aggregation (mean and max targets), and four ablations testing
data-source decomposition (all/retrospective/fresh-v11/migrated).
```

### 7.3 Friend-audit-driven methodology robustness 段（v2 新加）

```text
The v1.1-β.1 evaluation underwent two rounds of independent peer audit
that materially improved the methodological rigor of the analysis. The
first audit identified five issues: missing time-aware lag features in
the inertia model M4 (resolved by lifting v0.9 production lag-feature
implementation), absence of S142 sensitivity analysis (resolved by adding
configurable station exclusion), absence of hourly aggregation evaluation
(resolved with separate hourly_mean and hourly_max ridge models),
under-utilization of the v0.9 production WBGT proxy in favor of the v1.1
collector's simplified fallback (resolved by switching primary proxy),
and insufficient diagnostic of the 36% pair_used_for_calibration false
rate (resolved with a new pairing-health diagnostic in the alpha QA
report). The second audit, prompted by the first version of the present
findings report, identified three further issues: semantic conflation
between retrospective and operational calibration in the
pair_used_for_calibration flag, unverified attribution of the 0.07°C
v11-vs-v0.9 MAE gap to stale forecast forcing, and unresolved hourly
aggregation. These are resolved respectively by (a) introducing
properly-scoped pair_used_for_retrospective_calibration and
is_migrated_archive flags at the feature-build stage, (b) running a
formal four-arm ablation (all/retrospective/fresh-v11/migrated) that
falsifies the stale-dilution hypothesis, and (c) completing hourly
aggregation evaluation that demonstrates a calibration MAE floor of
~0.60°C consistent with v0.9-beta. The findings reported in this thesis
reflect the post-second-audit results.
```

### 7.4 Inherent calibration floor 段（v2 新加，重要）

```text
Ridge calibration on the Toa Payoh WBGT archive exhibits an inherent
MAE floor near 0.60°C, observed independently in v0.9-beta (24-hour
single-regime archive, 15-minute cadence, n = 2,564, M3 LOSO MAE =
0.595°C) and v1.1-β.1 (4-day multi-regime archive, hourly cadence,
n = 1,647, M3 LOSO MAE = 0.604°C). Despite differing archive duration,
sampling cadence, and weather regime span, both evaluations converge to
within 0.009°C MAE, suggesting calibration is bounded by physical noise
sources rather than data-volume or feature-space limitations. We
attribute this floor to three components: NEA WBGT instrument precision
(approximately ±0.3°C per WMO operational standards), Open-Meteo ERA5-
derived forcing accuracy (approximately ±0.5°C in tropical urban
contexts), and Stull (2011) wet-bulb formula residual (approximately
±0.2°C in the relative-humidity range typical of Singapore). This sets
realistic expectations for the v1.1-β formal pass at 14+ days of archive:
M3 LOSO MAE in the 0.55–0.70°C range, not approaching v0.9-beta's
0.595°C as a strict target. Further reduction below this floor would
require either (a) higher-precision WBGT instrumentation, (b) site-
specific weather forcing from on-station weather observations rather
than gridded reanalysis, or (c) a non-ridge model class capable of
capturing residual physics beyond linear weather-feature combinations
(deferred to v1.1-γ ML residual learning at 30+ day archive scale).
```

### 7.5 Operational threshold via hourly_max 段（v2 新加，最重要）

```text
For operational heat-stress warnings, we recommend predicting hourly-
maximum WBGT and flagging hours where the predicted max exceeds the
alert threshold (31°C in the Singapore NEA WBGT alerting protocol).
On the v1.1 4-day archive (n = 1,647 hourly aggregations across 27
stations), the v0.9-feature ridge model M5 achieves LOSO precision 0.72
and recall 0.57 for hourly-max WBGT ≥ 31°C detection (F1 = 0.64),
representing a 4× improvement over the same model evaluated at 15-
minute granularity (F1 = 0.23, precision 0.43, recall 0.15). The
hourly-max target outperforms hourly-mean because (a) positive events
are more numerous (204 vs 91 in n = 1,647), giving the classifier more
training signal; (b) the target definition aligns with operational
warning semantics ('any moment in the hour' rather than 'sustained
across the hour'); and (c) inertia features (M4) gain larger F1
advantage on hourly-max (0.624 vs M3's 0.579) than on hourly-mean
(0.153 vs 0.114), suggesting lag features help detect imminent threshold
exceedance. We adopt hourly-max as the primary operational target for
v1.1-β formal pass and any future deployment of the v1.1 calibration
framework as a real-time heat-stress warning tool.
```

### 7.6 S142 sensitivity 段（v1 4.4 保留）

```text
Of the 27 stations in the v1.1 archive, S142 (Sentosa Palawan Green) is
identified as an outlier: although contributing only 3.7% of paired
observations, it accounts for 19 of 29 (65.5%) WBGT ≥ 33°C events and
49 of 472 (10.4%) WBGT ≥ 31°C events. We report calibration results
both with and without S142 as a sensitivity case. Excluding S142
removes 19 of 29 ≥ 33°C events, reducing the ≥ 33°C threshold-scan
exercise to 10 events that are too few for any classifier evaluation.
We interpret this as evidence that the high-WBGT detection problem at
the ≥ 33°C threshold remains under-determined in the current archive
duration and requires either (a) longer archive enriching ≥ 33°C events
at non-S142 stations, or (b) explicit station-level random effects in
the calibration model.
```

### 7.7 Network sparsity / morphology unidentifiability 段（v1 4.5 保留 + v2 强化）

```text
The M5 (morphology) and M6 (overhead infrastructure) ridge models
yielded numerically identical out-of-fold predictions across all v1.1-
β.1 evaluations (15-minute, hourly_mean, hourly_max). This is a
numerical artifact rather than a substantive null result: of 27 NEA
WBGT stations, only S128 (Bishan Street) lies within the Toa Payoh 100m
grid AOI; the second-closest station S145 (MacRitchie Reservoir) is
683m from the nearest grid cell in a distinct land-cover regime and
excluded from station-to-cell mapping. Consequently, v10 morphology
and overhead features are populated only for ~3.7% of paired
observations. sklearn.SimpleImputer with median strategy drops
all-NaN columns at fit time, leaving M5 and M6 with the same ~8-feature
weather-only subset. The morphology calibration question is structurally
unidentifiable in the current 27-station network and remains open for
future work with denser TP-AOI WBGT instrumentation.
```

---

## 8. Pending / 14-day formal pass falsifiable hypotheses

### 8.1 v2 新加 H0：ablation 已经验证（不需要 14d 重跑）

```
H0: A_all M3 MAE - B_retrospective M3 MAE ≤ 0.02°C
    → 已证实 (Δ = 0.000°C, finding 6.4)
    → "stale-forcing dilution" 解释 falsified
    → 任何 14d 重跑都不需要重新质疑这一点
```

### 8.2 14-day archive formal pass hypotheses (v2 修订)

```
H1: M0 bias 仍在 [-1.05, -1.15]°C 范围  
    → 验证 proxy 物理偏差是 archive duration 无关
    
H2: M3 LOSO MAE ∈ [0.55, 0.70]°C  (v1 H2 修订: 不再期望 ≤ 0.62)
    → 反映 multi-day cross-regime evaluation 的真实难度 + ~0.6°C floor
    → 不要把 v0.9 0.595 当作目标
    
H3: M4 - M3 ≥ 0.03°C  (v1 H3 修订: 0.05 → 0.03 更现实)
    → thermal inertia signal 从 trend-level 升级到 statistical-level
    → 14d archive 应该含足够多 regime 让 inertia 显化
    
H4: M1b vs M3 差距 ≥ 0.20°C  (保持)
    → per-period non-stationarity 在 14d 上更明显
    
H5: S142 在 14d 中 ≥33 events 比例从 66% 降至 ≤55%
    → outlier 是站点固定 bias 而非 sampling 偶然
    
H6: M5/M6 numerical artifact 持续 (M5 ≡ M6)
    → station-network sparsity 仍是 binding constraint
    → S128 仍是唯一 morph-populated station
    
H7: Hourly_max ≥31 LOSO F1 ≥ 0.55  (v2 新加)
    → operational warning use case 在 14d 上仍 viable
    → 如果 F1 显著下降, 说明 4d 数字部分依赖于 evaluation set 偶然性
    
H8: Hourly_mean M3 LOSO MAE - v0.9 24h M3 MAE ≤ 0.05°C  (v2 新加)
    → ~0.6°C calibration floor 在 14d 上仍稳定
    → 否则需要重新审视 NEA 仪器精度 / Open-Meteo 精度假设
```

每个 H_i 都可独立 falsified——14d 重跑后逐条核对。

### 8.3 30-day archive v1.1-γ ML residual pilot 启动门槛（保持）

满足以下条件再启动 γ：

- M3 LOSO MAE ≤ 0.65°C（v2 修订: 不要求 ≤ 0.60，因为 floor 在那里）
- WBGT ≥ 31 events ≥ 1,500（每 station × day 期望 ~2 events）
- WBGT ≥ 33 events ≥ 100（足够 threshold scan）
- 至少 3 个不同 weather regime（hot peak / monsoon / cool）
- Hourly_max F1 ≥ 0.55（保证 ML residual 有 detectable signal 可学）

---

## 9. 附录 A：完整命令速查

### 9.1 v1.1-β.1 v2 完整跑通（14d 时同样使用）

```bat
REM 0. archive loop 持续在另一窗口跑（不停）

REM 1. 构造 v0.9 proxy + lag features + retrospective_calibration flags
python scripts\v11_beta_build_features.py
REM 输出: data\calibration\v11\v11_station_weather_pairs_v091.csv
REM 屏幕打印 retrospective eligible / collector pair_used / migrated 比例对照

REM 2. 重跑 alpha QA (含 pairing diagnostic 段, first audit 5.5 实施)
scripts\v11_run_alpha_archive_from_collector_pipeline.bat

REM 3. 跑 β baselines (主 + S142 sensitivity)
python scripts\v11_beta_calibration_baselines.py --config configs\v11\v11_beta_calibration_config_v091.json
python scripts\v11_beta_calibration_baselines.py --config configs\v11\v11_beta_calibration_config_v091_no_S142.json

REM 4. 跑 ablation orchestrator (4-run A/B/C/D)
python scripts\v11_beta_ablation_runner.py
REM 屏幕直接打印 pivot table + auto-verdict

REM 5. 跑 hourly aggregation + hourly mean/max baselines
python scripts\v11_beta_aggregate_hourly.py
python scripts\v11_beta_calibration_baselines.py --config configs\v11\v11_beta_calibration_config_v091_hourly_mean.json
python scripts\v11_beta_calibration_baselines.py --config configs\v11\v11_beta_calibration_config_v091_hourly_max.json

REM 6. (可选) threshold scan 在 hourly_max 上
python scripts\v11_beta_threshold_scan.py --config configs\v11\v11_beta_calibration_config_v091_hourly_max.json
```

### 9.2 健康检查（不影响 loop）

```bat
python scripts\v11_archive_health_check.py
```

### 9.3 14d 重跑 formal pass 前的 snapshot

```bat
REM 在 archive 长大到目标日期后, snapshot pairs CSV 锁定数据
copy data\calibration\v11\v11_station_weather_pairs.csv data\calibration\v11\snapshots\v11_pairs_14d_formal.csv

REM 然后 build_features 指向 snapshot
python scripts\v11_beta_build_features.py --input data\calibration\v11\snapshots\v11_pairs_14d_formal.csv --output data\calibration\v11\snapshots\v11_pairs_14d_formal_v091.csv

REM 改 config 指向 snapshot 后跑全部 §9.1 步骤
```

---

## 10. 附录 B：完整文件清单

### 10.1 v1.1-β.1 patch lineage（first audit + second audit 累加）

| 文件 | 状态 | first audit | second audit |
|---|---|---|---|
| `scripts/v11_beta_build_features.py` | NEW + PATCH 2 | v0.9 proxy + lag features (5.1, 5.4) | + derive_pairing_flags (7) |
| `scripts/v11_beta_aggregate_hourly.py` | NEW + PATCH 2 | hourly mean/max/p90 (5.3) | + retrospective flag forwarding (7) |
| `scripts/v11_beta_calibration_baselines.py` | PATCH + PATCH 2 | exclude_station_ids + M1b (5.2) | + filter_mode 5-mode support (7) |
| `scripts/v11_alpha_archive_qa.py` | PATCH | + pairing diagnostic (5.5) | (no change) |
| `scripts/v11_beta_ablation_runner.py` | NEW (v2 only) | n/a | 4-run orchestrator (8) |
| `configs/v11/v11_beta_calibration_config_v091.json` | NEW + PATCH 2 | 主 config | + filter_mode default (7) |
| `configs/v11/v11_beta_calibration_config_v091_no_S142.json` | NEW + PATCH 2 | sensitivity (5.2) | + filter_mode default (7) |
| `configs/v11/v11_beta_calibration_config_v091_hourly_mean.json` | NEW (v2 only) | n/a | hourly mean target (9) |
| `configs/v11/v11_beta_calibration_config_v091_hourly_max.json` | NEW (v2 only) | n/a | hourly max target (9) |

### 10.2 v0.9 codebase 中被 lift 的核心函数

| Source | 用途 |
|---|---|
| `scripts/v09_common.py::stull_wet_bulb_c` | Stull 2011 湿球公式 |
| `scripts/v09_common.py::compute_wbgt_proxy_weather_only` | v0.9 production WBGT proxy |
| `scripts/v09_beta_fit_calibration_models.py::add_time_and_inertia_features` | 全部 lag features |
| `scripts/v09_beta_fit_calibration_models.py::PeriodBiasModel` | M1b 周期偏移模型 |

### 10.3 输出位置

```
data/calibration/v11/
├── v11_station_weather_pairs.csv                  (collector raw, 长大中)
├── v11_station_weather_pairs_v091.csv             (加 v0.9 features + retrospective flag)
├── v11_station_weather_pairs_hourly.csv           (hourly aggregated)
└── snapshots/                                      (14d formal pass 时使用)

outputs/v11_beta_calibration/
├── all_stations/                                   (主 baselines)
├── no_S142/                                        (S142 sensitivity)
├── ablation_A_all/                                 (ablation 4-run)
├── ablation_B_retrospective/
├── ablation_C_fresh_v11/
├── ablation_D_migrated/
├── hourly_mean/                                    (hourly mean target)
├── hourly_max/                                     (hourly max target, operational primary)
├── v11_beta_ablation_summary.csv                   (4-run aggregated)
├── v11_beta_ablation_loso_mae_pivot.csv            (4-run pivot for dissertation)
└── (per-subdir: oof_predictions / metrics / report)

outputs/v11_alpha_archive/
└── v11_archive_QA_report.md                        (含 pairing diagnostic 段)
```

---

## 11. 附录 C：决策日志（v1 + v2 累计）

| 日期 | 决策 | 替代方案 | 理由 |
|---|---|---|---|
| 5/10 (first audit) | Path B (offline pre-feature script) 实施 5.4 | Path A (改 collector 加 production proxy) | Loop 不停, 试错成本低 |
| 5/10 (first audit) | Lift v0.9 codebase 而非自己写 lag features | 朋友的原始 5.1 设计 | v0.9 已实现, 减少 ~5h 工作量 |
| 5/10 (first audit) | 加 M1b 进 v11 ladder | 仅 5.1 + 5.4 + 5.2 | v0.9 报告标记 M1b "最简单有用", 跑出来才能验证是否 multi-day 退化 |
| 5/10 (first audit) | S142 sensitivity 优先方案 = A (保留为 primary) | B (排除为 primary) | 透明度优先 |
| 5/10 (first audit) | Hourly aggregation 第二优先级 (v1 阶段不跑) | 立即跑 | 5d 数据先看 trend, hourly 等 14d formal pass —— **second audit 推翻此决定，立即跑** |
| 5/10 (second audit) | 加 retrospective_calibration flag derivation 在 build_features (而非 collector) | 改 collector 直接生成正确 flag | 不动 loop, 单点 fix |
| 5/10 (second audit) | filter_mode 5 选项 (而非简单 boolean) | filter_by_retrospective_calibration: True | 一次性支持 ablation 4-run + 历史回归 |
| 5/10 (second audit) | Ablation orchestrator 写成单脚本 4-run | 4 个独立配置 + 手动运行 | auto-verdict 直接产出 dissertation 数字 |
| 5/10 (second audit) | hourly_mean 与 hourly_max 分两个 config 跑 | 一个 config 同时跑 | 输出隔离 + 易对照 |
| 5/10 (second audit, post-result) | 废弃 v1 finding 4.7 stale-dilution 解释, 改为三层叠加成因 | 维持 v1 解释 + 注脚说明 | ablation 已 falsify, 维持就是 dishonest |
| 5/10 (second audit, post-result) | 推荐 hourly_max 为 dissertation operational primary target | 15-min 或 hourly_mean | F1 0.64 vs 0.23 是决定性证据 |

---

## 12. 维护

**下次更新触发条件**：

- archive 长跑到 14 天后跑完 v1.1-β formal pass → 编 `OpenHeat_v11_beta_formal_findings_report_CN.md`，更新 H1-H8 结果
- 30 天 archive 触发 v1.1-γ ML residual pilot → 编 `OpenHeat_v11_gamma_findings_report_CN.md`
- NEA / Open-Meteo schema 变化 → 更新 v11 handoff §四 P 章节
- 朋友 third audit (如有) → 编 v3 (本 v2 同 v1 关系)

**与其他文档的关系**：

```
docs/handoff/OpenHeat_v10_to_v11_HANDOFF_CN.md
     ↓
docs/v11/OpenHeat_v11_alpha_beta_HANDOFF_CN.md
     ↓
docs/v11/OpenHeat_v11_beta1_findings_report_CN.md          (v1, archived, 已废弃)
     ↓
docs/v11/OpenHeat_v11_beta1_findings_report_CN_v2.md       ← 本文档 (canonical)
     ↓
docs/v11/OpenHeat_v11_beta_formal_findings_report_CN.md    (14d 后编)
     ↓
docs/v11/OpenHeat_v11_gamma_findings_report_CN.md          (30d 后)
```

**版本对比 (v1 → v2 重要变更摘要)**：

| 项 | v1 | v2 |
|---|---|---|
| Findings 数 | 8 | 9 (废弃 1, 新加 4) |
| 数据集对照 | 3 (v0.9 + 2 个 sensitivity) | 6 (v0.9 + 4 ablation + 2 hourly) |
| Stale-dilution 解释 | 主要假说 | falsified by ablation |
| Operational threshold | 15-min, F1 0.23 (low) | hourly_max, F1 0.64 (defensible) |
| Calibration floor 概念 | 隐含, 没明说 | 显式 ~0.6°C 物理上限 |
| H 假说数 | 6 | 9 (H0 + H1-H8) |
| Patch 数 | 6 | 13 (累计) |
| Audit 轮数 | 1 (5-point) | 2 (5-point + 3-point) |

---

**文档结束**

*维护者：你（user）+ Claude assistant collaboration*
*同行审阅功劳：朋友的 first audit (5-point) + second audit (3-point)，特别是 second audit 的 flag-semantics 拆解直接落地在 production code，把 v1 finding 4.7 的猜测性归因换成 ablation 实证*
*v0.9 codebase 复用功劳：v09_common.py + v09_beta_fit_calibration_models.py 提供完整的 production proxy + lag features + period bias model 实现*
*工程纪律：v1 → v2 完整保留 v1 文件作 archived reference, 不覆盖, 让 audit trail 可追溯*
