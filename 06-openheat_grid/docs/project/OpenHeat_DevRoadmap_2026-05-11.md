# OpenHeat Development Roadmap: Next-Step Optimizations & Features

**Author**: Yiheng Pan
**Date**: 2026-05-11
**Type**: Forward-looking development plan (actionable items, not framework discussion)
**Source**: Distilled from 2026-05-11 extended discussion (see `OpenHeat_ThinkingJournal_2026-05-11.md` for thinking process)
**Status**: Pre-EDSML sprint plan, ~14 weeks until ICL EDSML enrollment (~9/1)

---

## 0. 关于这份文档

### 0.1 这是什么

这是一份**待办与决策**清单, 记录这次对话决定要做的 OpenHeat 升级。每个项目包含:
- 做什么 (what)
- 为什么 (why)
- 怎么做 (how)
- 时间估计 (when)
- 优先级 (priority)
- 依赖 (depends on)
- Status 跟踪

跟 thinking journal 区别:
- **Journal** = 思考过程, 怎么想到要做这些
- **Roadmap** (这份) = 决策结果, 接下来 14 周做什么

### 0.2 总体 sprint 框架

```text
Pre-EDSML 14-week sprint (5/11 → 9/1):
  Phase 1 (5/11 → 6/1, ~3 周): 当前 v11-β.1 完成 + 工程基础
  Phase 2 (6/1 → 6/22, ~3 周): Calibration ladder 扩展 (M8/M9/Lasso) 
  Phase 3 (6/22 → 7/13, ~3 周): SOLWEIG batch + Approach 2 modifier 升级
  Phase 4 (7/13 → 8/10, ~4 周): System A+B coupling + Hazard quantification 升级 + Risk framework
  Phase 5 (8/10 → 9/1, ~3 周): Write up + synthesis v2 + EDSML 准备

Post-EDSML (Year 1):
  扩展 modifier 至 mobile validation
  Risk framework 升级到 epidemiology
  Thesis chapter draft
```

---

## 1. Phase 1: 完成当前阶段 (5/11 → 6/1)

### 1.1 14-day formal pass on calibration ladder

**Status**: Scheduled, 数据在 collect
**Priority**: P0 (critical, 基础)
**Owner**: Local Windows runner

**做什么**:
- ~5/25 archive 满 14 天后, run `scripts\v11_beta_freeze_snapshot.bat 14d_formal`
- 重跑 M0-M7 全 ladder LOSO calibration
- 重跑 H1-H11 hypothesis tests
- 重跑 bootstrap M4-M3 advantage CI
- 重跑 threshold scan (4 operating points)
- 重跑 H10 keystone bit-identity check

**为什么**: v11-β.1 v2.2 FINAL 期待的 formal verification. 24h pilot → 14d production confirm M4 effect size + H10 unidentifiability.

**输出**: `OpenHeat_v11_beta_formal_findings_report_CN.md` (~30-40 KB)

**预期结果**:
- M3 LOSO MAE: ~0.605°C → 14d 后可能 0.58-0.62°C 范围
- M4 LOSO MAE: ~0.593°C → bootstrap CI 更窄
- M5/M6/M7 bit-identity 仍 hold
- F1@31 hourly_max: ~0.632 → 可能稳定或微调

**Risk**: 如果 M4-M3 advantage CI 包含 0, 需要 framing 调整 (从 "small but detectable" 到 "indistinguishable")

---

### 1.2 GitHub Actions cron migration

**Status**: Workflow YAML 草稿已写 (v11-β.1 doc 提到), 未部署
**Priority**: P0 (critical, 6/1 截止)
**Owner**: GitHub Actions

**做什么**:
- 6/1 前完成 `.github/workflows/v11_archive_collector.yml` 部署
- 测试 cron 在 GHA 触发 + Open-Meteo + NEA API 都可达
- 验证 commit-back 机制 (cron-bot user)
- 监控 first 3-day run 看 latency 跟 success rate

**为什么**: 6/1 后本地 Windows runner 不能挂 24/7. GHA 是 free + reliable 替代.

**关键 design choice**: 
- **Public repo**: 完全免费 + 15min cadence 可行 → ★ 推荐
- Private repo: hourly cadence 才完全免费

**前提条件**: 
- Repo 切换到 public (建议同时做)
- API keys (如有) 用 GitHub Secrets 管理

**输出**: 
- Working cron, archive 自动累积到 30+ days by EDSML 入学

---

### 1.3 Thinking journal + Synthesis v1 → v2 计划

**Status**: Journal 已写 (today), v1 仍 valid, v2 待写
**Priority**: P1 (high)
**Owner**: 写作

**做什么**:
- 让 thinking journal 在脑子里 sit 1-2 周
- Phase 1 完成时再 polish synthesis v2 (整合 today's framework discussions)
- v2 加 §0 abstract (4 句 distilled framework) + §3.0 two-task framing + §3.0.5 7-layer + §7.4 hazard→risk path + appendix Q&A

**为什么**: today's discussion surface 了 12+ framework refinements 跟 8 corrections to v1. Doc 必须 update.

**预期输出**: `OpenHeat_ProjectSynthesis_v2.md` (~2,000 行, ~120 KB)

---

## 2. Phase 2: Calibration Ladder 扩展 (6/1 → 6/22)

### 2.1 M8: Water-aware compact ridge

**Status**: Proposed, not implemented
**Priority**: P1 (high, quick win)
**Effort**: 3-5 天

**做什么**:
- 在 M7 (compact 8 features) 基础上加 3 water features:
  ```text
  - water_distance_m (per-station, 距最近水体)
  - water_fraction (Dynamic World water cover at station location)
  - nearest_water_type (canal / pond / river / coast, categorical)
  ```
- 跑 LOSO calibration
- 跟 M7 比较 MAE + bootstrap CI
- Hypothesis test: cross-station water features 是否突破 H10 unidentifiability?

**为什么**:
- 你这一周 raised "water 维度 未考虑" — 这是 lightweight 测试
- Water features 是 cross-station varying (跟 morph 不同, morph 只 S128 有值)
- 数学上有可能 break H10
- 即使 no detectable improvement, 也是 publishable null finding

**怎么做**:
1. 加 water features 到 v11 aggregator (`scripts/v11_beta_aggregate_hourly.py`)
2. 数据来源:
   - water_distance_m: OSM water polygons (`osm_water_v07.gpkg` 已有)
   - water_fraction: Dynamic World GEE export (v0.7-β 已 export)
   - nearest_water_type: from OSM water classification
3. 在 calibration config 加 M8_water_aware_compact_ridge entry
4. 跑 `scripts\v11_beta_run_calibration.bat M8_water_aware_compact_ridge`
5. Output: M8 LOSO MAE, weights, bootstrap CI vs M7

**Dependency**: 14d formal pass 完成

**预期结果**:
- 如果 water-WBGT 关系真 exist: M8 vs M7 detectable improvement (~0.02-0.05°C MAE)
- 如果不显著: M8 ≈ M7 (新 null finding, 仍 publishable)

---

### 2.2 M9: Rich environmental ridge (17 features)

**Status**: Proposed, not implemented
**Priority**: P1 (high)
**Effort**: 1-2 周

**做什么**:
- 在 M4 (18 features: weather + inertia) 基础上加 17 cell-level environmental features
- Total ~35 features
- 跑 LOSO calibration
- 跟 M4 比较 MAE + bootstrap weights CI per feature

**17 features 完整 list**:
```text
Land cover (GEE export, 已有):
  1. lst_landsat (★ Cooling TP PPT 用过)
  2. ndvi_mean
  3. tree_canopy_fraction (Dynamic World)
  4. grass_fraction
  5. water_fraction
  6. built_up_fraction
  7. impervious_fraction
  
Distance (OneMap-derived):
  8. water_distance_m
  9. park_distance_m
  10. coast_distance_m

Morphometric (UMEP):
  11. z0 (roughness length)
  12. d (displacement height)
  13. fai (Frontal Area Index)

Topography:
  14. elevation_m
  15. slope_degrees
  16. aspect

Surface (Landsat-derived):
  17. albedo_landsat
```

**Statistical reality**:
- n=20,000+ (14d), p=35, n/p=570 → 充分 statistical power
- 这是 17 features 真正可 fit 的地方 (vs cell modifier n=5 的 n/p=0.29)
- Bootstrap CI 应能 identify 哪些 features 真有 effect

**为什么**:
- 17 features 在 Path 1 (calibration) 的真正应用
- M9 是 "data-driven discover" model: 看 cross-station varying features 哪些 informative
- 跟 M5/M6 (morph fail H10) 形成 对照: cross-station varying 是 key

**怎么做**:
1. Extend `scripts/v11_beta_aggregate_hourly.py` 加 17 features columns
2. Station → cell mapping 已 v0.7-β-OUT-1 完成, 直接复用
3. Add M9 calibration config
4. Run + bootstrap

**Dependency**: 
- 14d formal pass
- M8 完成 (作 lighter-weight baseline)

**预期结果**:
- M9 LOSO MAE vs M4: 改善 ~0.02-0.05°C (small but detectable)
- Bootstrap weights CI 识别 informative features (e.g. LST > 0, water_distance 等)
- 部分 features (e.g. morph 类) 仍 unidentifiable, 跟 H10 keystone consistent

---

### 2.3 Lasso CV automated feature selection

**Status**: Proposed, not implemented
**Priority**: P1 (high, principled best-subset)
**Effort**: 3-5 天

**做什么**:
- 在 ladder 8 models 之外, 加一个 LassoCV model
- Candidate features: 全部 44 个 (M3 weather + inertia + morph + overhead + 17 cell-level)
- 让 Lasso (L1 penalty) 自动 select sparse subset (zero out 不 informative features)
- Bootstrap stability: 哪些 features 稳定被选

**为什么**: 
- 你 raised "应该试很多种组合找最好的" — Lasso 是 principled 实现方式
- Brute force 100+ combinations 会 multiple-testing problem
- Lasso 单次 fit, 数学上 well-understood, 跨数据 bootstrap 测稳定性
- 跨 verification: Lasso 选出来的 vs ladder hypothesis-testing 结论 是否一致?

**怎么做**:
```python
from sklearn.linear_model import LassoCV
from sklearn.preprocessing import StandardScaler
from sklearn.utils import resample
import numpy as np

# 准备所有 candidate features
X = archive[44_candidate_features].values  # n=20,000, p=44
y = archive['NEA_WBGT'].values

# Standardize (Lasso 对 scale 敏感)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# LassoCV with 27-fold (LOSO-like)
lasso = LassoCV(cv=27, n_alphas=100, random_state=42)
lasso.fit(X_scaled, y)

# Selected features
selected = [
    (feat, weight) 
    for feat, weight in zip(candidate_features, lasso.coef_)
    if abs(weight) > 1e-6
]
print(f"Selected: {len(selected)}/{len(candidate_features)}")

# Bootstrap stability (1000 iter)
selection_count = {feat: 0 for feat in candidate_features}
for _ in range(1000):
    X_b, y_b = resample(X_scaled, y)
    lasso_b = LassoCV(cv=10).fit(X_b, y_b)
    for feat, weight in zip(candidate_features, lasso_b.coef_):
        if abs(weight) > 1e-6:
            selection_count[feat] += 1

# Stability score per feature
stability = {feat: count/1000 for feat, count in selection_count.items()}
```

**输出**:
- M11_lasso_selected model + LOSO MAE
- Feature stability table (哪些 features stability > 0.8 = robust)
- 比较 M11 跟 M9 (M9 keep 所有 17 features vs M11 sparse subset)

**为什么这样设计**:
- 测试 "ladder hypothesis-test 结论 vs Lasso data-driven 结论" 是否 consistent
- 如果 morph features Lasso 全 drop → cross-validates H10 from different angle
- 如果 LST + water_distance Lasso 稳定选中 → 强 evidence 它们真有 effect

**Dependency**: M9 已完成 (作 ridge baseline)

---

### 2.4 Calibration ladder design philosophy 文档

**Status**: Implicit in v2.2 FINAL, not explicit
**Priority**: P2 (medium, doc completeness)
**Effort**: 1-2 天

**做什么**:
- 写一个 short doc 解释 ladder design philosophy
- 内容:
  - Why design spectrum (non-nested) vs cumulative tree
  - Why each M tests a specific hypothesis (H1-H11)
  - Why Lasso added as cross-validation, 不是 replacement
  - Why M5/M6/M7 weather subset 跟 M3/M4 不嵌套 (intentional H10 isolation)

**为什么**: today's conversation surface了 ladder 设计的 implicit choices 之前没 explicit document.

**输出**: 加进 synthesis v2 §3.5.x 或独立 `OpenHeat_calibration_ladder_design.md`

---

## 3. Phase 3: SOLWEIG Batch + Modifier Estimation Upgrade (6/22 → 7/13)

### 3.1 ★ Headless QGIS SOLWEIG batch pipeline

**Status**: v10-ε manual (5 cells), batch automation not implemented
**Priority**: P0 (critical for modifier estimation upgrade)
**Effort**: 3-5 天 (开发 + test)

**做什么**:
- 复用 v10-ε infrastructure, 加 headless QGIS batch wrapper
- 让 SOLWEIG 通过 QGIS Python console 自动跑, no manual GUI

**关键 enabler**:
- UMEP 官方支持 `processing.run("umep:Outdoor Thermal Comfort: SOLWEIG", {...})`
- Headless QGIS = no GUI 启动
- Python script 控制 cell selection + parameter passing + output collection

**新 scripts**:
```text
scripts/v10_zeta_select_cells.py           # Latin hypercube 选 150 cells
scripts/v10_zeta_prepare_rasters.py        # 复用 v10-ε + loop
scripts/v10_zeta_solweig_batch.py          # ★ headless batch runner
scripts/v10_zeta_aggregate_tmrt.py         # 复用 v10-ε + loop
scripts/v10_zeta_modifier_estimate.py      # ridge fit modifier
```

**Batch runner 关键 features**:
- Resume capability (跳过已完成 cells)
- Failure logging (continue on error, don't stop)
- Progress + ETA reporting
- Headless mode (no GUI dependency)

**为什么**: 当前 5 cells SOLWEIG 限制 modifier fitting 在 n=5 (severely underdetermined). 100-150 cells 给 n/p=6-9 OK power.

---

### 3.2 Cell sampling (Latin Hypercube, 150 cells)

**Status**: Proposed
**Priority**: P0
**Effort**: 1 天

**做什么**:
- 从 982 grid cells 中 stratified 选 ~150 cells
- Stratify on 5 features (SVF, building_density, shade_fraction, GVI, overhead_fraction)
- Latin Hypercube design (cover feature space 均匀)
- 加 v10-ε 已跑 5 cells (TP_0565, TP_0986, TP_0088, TP_0916, TP_0433) 保 baseline consistency

**为什么**: 不是 random sampling — 让 Latin Hypercube cover feature space corners (high SVF + low building density 等 rare combinations).

**输出**: `outputs/v10_zeta_selected_cells.csv` (~150 cell_ids)

---

### 3.3 Batch SOLWEIG run

**Status**: Pending
**Priority**: P0
**Effort**: 3-5 天 calendar (CPU 1-2 days parallel, 6-12 days single core)

**做什么**:
- 150 cells × 5 hours (10/12/13/15/16) × 2 scenarios (base + overhead) = 1,500 SOLWEIG runs
- 跑在 i7 desktop, 4-8 cores parallel
- Forcing: typical heatwave day (与 v10-ε 一致, 选 archive ≥31°C event 的 mean forcing)

**实操 details**:
- Tile size: 200m × 200m (100m cell + 50m buffer, 防 building shadow edge effect)
- Per run: ~30-90 秒 CPU
- Total CPU: ~25 hours single core
- Parallel (4 cores): ~6 hours
- Failure rate 预期: 1-3% (DSM corruption / memory issue), 后续 manual rerun

**Output structure**:
```text
data/solweig/v10_zeta_tiles/
  tile_TP_XXXX/
    dsm_buildings_tile.tif
    dsm_vegetation_tile_base.tif
    dsm_vegetation_tile_overhead.tif
    solweig_base_h10/  Tmrt_20260320_1000.tif, ...
    solweig_base_h13/  Tmrt_20260320_1300.tif, ...
    ...
    solweig_overhead_h13/  Tmrt_20260320_1300.tif, ...

outputs/v10_zeta_solweig/
  v10_zeta_focus_tmrt_summary.csv      # 1,500 rows: cell × hour × scenario
  v10_zeta_failed_runs.csv              # 失败列表 manual review
```

---

### 3.4 Aggregate Tmrt → cell-level summary

**Status**: Pending (复用 v10-ε aggregator)
**Priority**: P0
**Effort**: 1-2 天

**做什么**:
- 对每 (cell, hour, scenario), 从 SOLWEIG raster (2m × 2m) extract cell-level stats
- 输出 mean / p10 / p50 / p90 / max / variance per cell

**为什么 p90 而非 mean**:
- p90 代表 cell 内 worst 10% pixel (vulnerable population-relevant)
- mean 把 sub-cell variation 平掉
- v10-ε 用 mean 是 conservative, 但 p90 对 modifier calibration 更 operational

**输出**: `outputs/v10_zeta_focus_tmrt_summary.csv` with columns:
```text
cell_id, hour, scenario, 
tmrt_mean_c, tmrt_p10_c, tmrt_p50_c, tmrt_p90_c, tmrt_max_c, 
tmrt_var, tmrt_valid_pixels
```

---

### 3.5 ★ Modifier estimation v2 (ridge on 100+ cells)

**Status**: Pending
**Priority**: P0 (核心 deliverable)
**Effort**: 1 周

**做什么**:
- 用 150 cells SOLWEIG-derived modifier 作 target
- Ridge fit modifier = f(17 features)
- Bootstrap weights CI (1000 iter)
- 应用到全 986 cells

**Procedure**:
```python
# 1. 加载 SOLWEIG 输出 (peak hour 13:00 base scenario)
solweig_df = pd.read_csv('outputs/v10_zeta_focus_tmrt_summary.csv')
peak_df = solweig_df.query('hour == 13 and scenario == "base"')

# 2. 算 modifier = cell_wbgt - baseline_wbgt
# baseline 来自 System A 14d formal pass typical heatwave 13:00 prediction
baseline_wbgt_13 = system_A.predict(typical_heatwave_forcing_at_13)  # e.g. 31.2°C

peak_df['cell_wbgt'] = tmrt_to_wbgt(peak_df['tmrt_p90_c'], typical_forcing)
peak_df['modifier'] = peak_df['cell_wbgt'] - baseline_wbgt_13

# 3. Merge 跟 cell features
features_df = pd.read_csv('grid_features_v10_full.csv')
merged = peak_df.merge(features_df, on='cell_id')

# 4. Ridge fit
X = merged[17_features].values
y = merged['modifier'].values

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
ridge = RidgeCV(alphas=[0.01, 0.1, 1.0, 10.0]).fit(X_scaled, y)

# 5. Bootstrap (1000 iter)
weights_bootstrap = []
for _ in range(1000):
    X_b, y_b = resample(X_scaled, y)
    ridge_b = RidgeCV().fit(X_b, y_b)
    weights_bootstrap.append(ridge_b.coef_)
weights_ci_lower = np.percentile(weights_bootstrap, 2.5, axis=0)
weights_ci_upper = np.percentile(weights_bootstrap, 97.5, axis=0)

# 6. 应用全 986 cells
all_X = scaler.transform(features_df[17_features].values)
features_df['predicted_modifier'] = ridge.predict(all_X)

# 7. 对已 SOLWEIG-跑过 cells, override prediction with actual modifier
for cell_id in selected_cells:
    actual_mod = merged.loc[merged.cell_id == cell_id, 'modifier'].iloc[0]
    features_df.loc[features_df.cell_id == cell_id, 'predicted_modifier'] = actual_mod

features_df.to_csv('outputs/v11_zeta_cell_modifiers.csv')
```

**预期 output**:
- Cell modifier per 986 cells (with CI from bootstrap)
- Feature importance (which features 真有 effect on modifier)
- Validation: SOLWEIG actual modifier vs ridge predicted modifier (LOO)

---

### 3.6 Multi-hour modifier (test time-invariance assumption)

**Status**: Pending (after 3.5)
**Priority**: P2 (test Approach 2 assumption)
**Effort**: 2-3 天

**做什么**:
- 不只 13:00, 也算 10/12/15/16 modifier
- 看 modifier 是否真 time-invariant (Approach 2 假设)

```python
# 对每 hour 都 fit 一个 modifier model
modifier_by_hour = {}
for hour in [10, 12, 13, 15, 16]:
    hour_df = solweig_df.query(f'hour == {hour} and scenario == "base"')
    modifier_by_hour[hour] = fit_modifier(hour_df, features_df)

# 比较各 hour modifier (per cell)
# 如果 modifier_13 ≈ modifier_15 (relative ordering 保持), Approach 2 valid
# 如果 systematic time variation 大, 需要升级 Approach 4 (hourly UMEP shadow)
```

**为什么**: Approach 2 假设 "modifier time-invariant". 用 multi-hour SOLWEIG 直接 test 这个 assumption. 如果违反, 给 Approach 4 提供 motivation.

---

## 4. Phase 4: System A+B Coupling + Hazard Quantification + Risk Framework (7/13 → 8/10)

### 4.1 ★ Approach 2 coupling: cell × hour WBGT

**Status**: Pending (依赖 Phase 3)
**Priority**: P0 (核心 unification)
**Effort**: 3-5 天

**做什么**:
- 把 System A hourly baseline 跟 cell modifier 加在一起, 输出 cell × hour WBGT 矩阵
- 公式: `cell_wbgt(cell, hour) = system_A_baseline(hour) + cell_modifier(cell)`

**实操**:
```python
# System A 给 typical heatwave day hourly baseline
hourly_baseline_wbgt = {}
for hour in range(24):
    forcing_at_hour = typical_heatwave_forcing[hour]
    hourly_baseline_wbgt[hour] = system_A.predict(forcing_at_hour)

# Modifier (from Phase 3.5)
cell_modifiers = pd.read_csv('outputs/v11_zeta_cell_modifiers.csv')

# Coupling
cell_hour_wbgt = np.zeros((986, 24))
for i, cell_id in enumerate(cell_modifiers['cell_id']):
    for hour in range(24):
        cell_hour_wbgt[i, hour] = (
            hourly_baseline_wbgt[hour] + 
            cell_modifiers.loc[cell_modifiers.cell_id == cell_id, 'predicted_modifier'].iloc[0]
        )

# Save
np.save('outputs/v11_zeta_cell_hour_wbgt.npy', cell_hour_wbgt)
```

**输出**: 986 × 24 matrix of cell-level hourly WBGT under typical heatwave.

**Key milestone**: 这是 OpenHeat **第一次** 输出 cell × hour 的 WBGT. 之前要么 hourly + AOI-only (System A), 要么 cell-level + static (System B).

---

### 4.2 ★ Hazard quantification 升级: rank → WBGT °C

**Status**: Pending
**Priority**: P0 (核心 conceptual shift)
**Effort**: 2-3 天

**做什么**:
- 把 hazard ranking 从 "hand-set features weighted sum (unitless 0-1)" 切换到 "WBGT-based (°C, threshold-driven)"
- 物理基础: WBGT 是 standard heat stress metric, 31°C 是 NEA alert threshold

**新 hazard metrics**:

**Option A: Threshold-based** (你 raised "WBGT > threshold value"):
```python
hazard_binary(cell, hour) = (cell_wbgt(cell, hour) > 31.0)
hazard_score(cell) = fraction of hours per day with WBGT > 31°C
```

**Option B: CDH (Cooling Degree Hours, Cooling TP PPT 用过)**:
```python
CDH28(cell) = sum over 24 hours of max(0, cell_wbgt(cell, hour) - 28)
CDH31(cell) = sum over 24 hours of max(0, cell_wbgt(cell, hour) - 31)
```

**Option C: Multi-threshold cumulative**:
```python
hazard_score(cell) = 
    0.3 * hours_above_28 + 
    0.5 * hours_above_31 + 
    1.0 * hours_above_33
# Weighted by NEA / SG MOM severity scale
```

**推荐**: Option B (CDH31), 因为:
- 直接 leverage Cooling TP 框架 (CDH28 在 PPT 用过)
- 物理可解释 (degree-hours above threshold)
- 跨 cell 比较保留 ordinal + cardinal 两层信息
- 跟 risk framework downstream 自然衔接

**为什么这个升级 critical**:
- 旧 hazard score = hand-set features 加权和, unitless, 无物理基础
- 新 hazard score = WBGT °C-based, 物理意义明确, threshold 跟 NEA alert system 一致
- v10 hand-set weights 的 sensitivity 不再是问题 (因为不再用)
- Cell 间 hazard 比较 = 直接 WBGT 比较, transparent

**输出**:
- `outputs/v11_zeta_cell_hazard_cdh.csv`: per-cell CDH28, CDH31, hours_above_31, etc.
- 新 ranking vs v10 hand-set ranking 的对比 + Spearman correlation

---

### 4.3 Vulnerability layer restructure

**Status**: v0.7.1 has score, 需要 disentangle
**Priority**: P1 (high)
**Effort**: 1 周

**做什么**:
- 把 v0.7.1 mixed score 拆成 3 个 distinct components
- 每个 component 独立 score, 不再混在 single vulnerability_score

**3 个 components**:

**2a. Demographic vulnerability**:
```text
来源: SingStat Census 2020 subzone-level
  - pct_elderly_75plus     ★ 强 heat 易感
  - pct_elderly_65to74
  - pct_children_under5     (Toa Payoh 不是主要 priority)
  - pct_living_alone        (老人孤立)
```

**2b. Physical/environmental vulnerability**:
```text
来源: Cooling TP 数据 + HDB pub data
  - pct_top_floor_residents     ★ 顶层无 AC 高风险
  - ac_penetration_rate         (估算难, 用 SES proxy)
  - hdb_housing_age             (HDB 老旧 = 通风差)
```

**2c. Socioeconomic vulnerability**:
```text
来源: SingStat Census
  - median_household_income
  - pct_rental_housing (低 SES proxy)
```

**Implementation**: 
```python
vulnerability_df = pd.read_csv('vulnerability_v071_data.csv')

# Disentangle
vulnerability_df['vuln_demographic'] = (
    0.5 * vulnerability_df['pct_elderly_75plus'] + 
    0.2 * vulnerability_df['pct_elderly_65to74'] +
    0.3 * vulnerability_df['pct_living_alone']
) / 100

vulnerability_df['vuln_physical'] = (
    0.6 * vulnerability_df['pct_top_floor_residents'] +
    0.4 * (1 - vulnerability_df['ac_penetration_estimated'])
)

vulnerability_df['vuln_socioeconomic'] = (
    0.7 * (1 - vulnerability_df['income_normalized']) +
    0.3 * vulnerability_df['pct_rental_housing']
) / 100
```

**Output**: 3 distinct vulnerability scores per cell + composite (for backward compat).

**为什么**: today's discussion 把 vulnerability 跟 exposure proxy 区分清楚. v0.7.1 mixed score 不再 fit IPCC risk framework.

---

### 4.4 Static exposure layer (rename + extend v0.7.1)

**Status**: v0.7.1 anchored points, 改名 + 扩展
**Priority**: P1
**Effort**: 1 周

**做什么**:
- 把 v0.7.1 "vulnerability score" 里实际是 "exposure proxy" 的部分独立出来
- 加更多 anchored exposure 点

**Exposure features** (per-cell static):
```text
Existing v0.7.1 + new:
  - density_bus_stops
  - density_mrt_exits
  - density_hawker_centres        ★ 老人聚集
  - density_eldercare_facilities  ★★ 高 vuln + 高 exposure
  - density_preschools
  - density_outdoor_markets
  - density_neighborhood_parks
  - density_sports_facilities
  - proximity_to_kopitiam
  - count_residential_units       (HDB 人口密度 proxy)
```

**Implementation**: 复用 v0.7.1 OneMap-based scripts, 扩展到 ~10 categories.

**Output**: `outputs/v11_zeta_cell_exposure_static.csv` per cell

**为什么**: Exposure 跟 Vulnerability 不同 (谁来 vs 这些人怎样). 7-layer framework Layer 4 vs Layer 5.

---

### 4.5 Risk integration (multiplicative)

**Status**: Pending (需要 4.1-4.4 完成)
**Priority**: P0 (核心 deliverable)
**Effort**: 3-5 天

**做什么**:
- 把 Hazard × Exposure × Vulnerability 乘起来, 输出 Risk score per cell
- 对不同 population groups 算 subgroup-specific risk

**公式 (Option A: simple multiplicative)**:
```python
risk(cell) = hazard(cell) * exposure(cell) * vulnerability(cell)

# 归一化到 0-1
risk_normalized = risk / risk.max()
```

**公式 (Option B: CDH-based 推荐)**:
```python
risk_for_elderly(cell) = (
    CDH31(cell)              # cells 累积 degree-hours above 31°C
    × exposure(cell, 'elderly')   # 老人 density proxy
    × vuln_demographic(cell, '75plus')   # 老人占比
)
```

**Output**: 
- `outputs/v11_zeta_cell_risk_general.csv`: general population risk
- `outputs/v11_zeta_cell_risk_elderly.csv`: elderly 75+ risk
- `outputs/v11_zeta_cell_risk_children.csv`: children risk

---

### 4.6 5-Map deliverable

**Status**: Pending (需要 4.1-4.5)
**Priority**: P0 (publishable output)
**Effort**: 1 周 (visualization + write up)

**做什么**:
- 输出 5 张 maps for Toa Payoh
- 都是 100m grid resolution

**Maps**:
1. **Map A: Hazard** — CDH31 per cell (Layer 3)
2. **Map B: Vulnerability (composite)** — 3 components averaged (Layer 5)
3. **Map C: Exposure** — static exposure score (Layer 4)
4. **Map D: Risk (general)** — Hazard × Exposure × Vulnerability (Layer 6)
5. **Map E: Risk for elderly 75+** — subgroup-specific (Layer 6 stratified)

**Tools**: 
- QGIS / GeoPandas + Matplotlib
- Custom colormap (cooler colors for safer, hotter for higher risk)
- Inset showing Cooling TP cited intervention nodes overlay

**为什么**:
- Cooling TP project 期待这种 deliverable
- Workshop paper / conference 可发布
- EDSML 入学讨论用 visual material

---

## 5. Phase 5: Write Up + Synthesis + EDSML 准备 (8/10 → 9/1)

### 5.1 Synthesis v2 doc

**Status**: Pending
**Priority**: P0
**Effort**: 1 周

**做什么**: 整合 today's 所有 framework discussions:
- §0 Abstract (distilled 4 sentences)
- §3.0 Two-task framing + Approach 2 unification
- §3.0.5 7-layer conceptual framework
- §3.6 System A reference frame nuance
- §3.7 SOLWEIG with 7-uncertainty list (含 wind treatment)
- §6.5 Architecture-level open questions
- §7.4 Hazard → risk path (本 doc 的 phase 4 内容)
- §7.5 PhD trajectory possibility (cautious)
- Appendix: M0-M9 calibration ladder full doc + Q&A 累积

**Reference**: 直接用 thinking journal §9 Refinements Catalog + 本 doc 内容 + v1 synthesis 既有结构.

---

### 5.2 Workshop paper draft

**Status**: Pending (依赖 Phase 4 完成)
**Priority**: P1
**Effort**: 2 周

**做什么**: Draft 一篇 workshop-paper-quality writeup:

**Title 候选**:
- "Fine-scale heat risk mapping in Toa Payoh: integrating audit-driven calibration with multi-source vulnerability and exposure data"
- "From hazard to risk: coupling SOLWEIG-based microclimate modeling with population vulnerability in Singapore HDB context"

**结构 (~6-8 页)**:
1. Introduction: heat in tropical city, 7-layer framework, HDB elderly context
2. Methods:
   - System A: 27-station ridge calibration (M3/M4)
   - System B: SOLWEIG batch 150 cells + modifier ridge fit
   - Approach 2 coupling: cell × hour WBGT
   - CDH-based hazard quantification
   - Vulnerability + exposure layers
   - Multiplicative risk integration
3. Results:
   - System A LOSO MAE ~0.6°C
   - Modifier estimation R² + feature importance
   - Cell × hour WBGT spatial-temporal pattern
   - Risk map (Map A-E)
   - Cooling TP intervention node validation
4. Discussion:
   - Limitations: H10 unidentifiable, wind treatment Layer 1, single-day reference
   - Future: mobile validation, ABM exposure, climate projection
5. Conclusion: methodological contribution as case study

**Target venue**: 
- AAG (American Association of Geographers) 2027 Spring conference
- Urban Climate journal short paper
- ICUC (International Conference on Urban Climate) 2027

---

### 5.3 Portfolio polish + EDSML 入学材料

**Status**: Pending
**Priority**: P1
**Effort**: 1 周

**做什么**:
- GitHub repo public-ready (clean README, docs, examples)
- Portfolio website (~3-5 项目展示, OpenHeat + Plymouth diss + Cooling TP)
- EDSML supervisor introduction email drafts (multiple advisors)
- "Pre-thesis position paper" (~3 页) outlining EDSML thesis direction options

**Thesis direction options 候选** (cautious framing):
1. Coupling micro-scale climate model output with personal exposure measurement (OpenHeat + Plymouth diss methodology)
2. Audit-driven open-data calibration with quantified information loss layers
3. From hazard map to risk map: cell-level SOLWEIG + 人口暴露 for HDB intervention prioritization

---

## 6. EDSML Year 1 (Post-Sprint, 9/2 →)

这些是 pre-EDSML 14 周搞不完, 留给 EDSML 第一年的事:

### 6.1 Mobile validation (Plymouth diss methodology adapted)

**做什么**:
- 找 Singapore 本地 collaborator
- 4-6 transects 跨 Toa Payoh
- Kestrel 5400 + GPS + GEMA prompts
- 4-6 周 field + 3-4 周 analysis

**为什么**: 
- 唯一能 ground-truth Layer 1-3 chain 的方法
- 验证 modifier estimate, identify SOLWEIG bias
- 跟你 Plymouth diss methodology 一脉相承

---

### 6.2 SOLWEIG sample 扩展 to 500+ cells

**做什么**: Phase 3 跑 150 cells, EDSML 扩到 500+ 含 4 seasons.

**为什么**: 测试 modifier 是否 generalize 跨 seasons (不只 spring equinox).

---

### 6.3 Approach 4 (hourly UMEP shadow modifier)

**做什么**: 解放 "modifier time-invariant" 假设, 让每小时算独立 shadow + radiation.

**为什么**: 真正解决 Approach 2 first-order approximation 的 limit.

---

### 6.4 Epidemiological risk extension

**做什么**: 接 hospital admission / heat mortality data (如果有 collaborator 可获).

**为什么**: 把 risk 从 hazard-exposure-vulnerability 推到 actual outcome (Layer 7).

---

### 6.5 Behavioral feedback model (ABM)

**做什么**: Agent-based simulation of how people respond to alerts / route choice under heat.

**为什么**: PhD 级 frontier, behavioral coupling 是 climate adaptation active 研究方向.

---

## 7. Decision Log (本对话决定的 design choices)

记录这些 decisions 的 rationale:

| Decision | Rationale | Date |
|---|---|---|
| Hazard 从 hand-set ranking → WBGT-based CDH31 | Layer 3 量化升级, 物理基础, 跟 NEA alert system 一致 | 5/11 |
| Use System A typical-day forecast as baseline | Reference frame consistency with Approach 2 mathematics | 5/11 |
| 17 features 在 Path 1 (calibration) 立即可用, modifier (Path 2+3) 等 SOLWEIG 扩到 100+ | Statistical reality: n/p ratio constraints | 5/11 |
| Path 2 跟 Path 3 是 mechanic siblings, 不是 3 paths | Same feature mapping, different targets (ordinal vs cardinal) | 5/11 |
| SOLWEIG batch via headless QGIS, 150 cells | Manual GUI 不 scalable, headless 是 standard practice | 5/11 |
| Add Lasso CV alongside ladder, not replace | Cross-validate ladder findings without sacrificing audit | 5/11 |
| Modifier 用 p90 而非 mean (within cell) | Worst 10% pixel for vulnerable population safety | 5/11 |
| Vulnerability 拆 3 components (demographic / physical / SES) | 7-layer Layer 5 disentangle, ipcc-aligned | 5/11 |
| Pre-EDSML 14 周 sprint 5 phases | Calendar fit + dependency 排序 | 5/11 |
| PhD trajectory: cautious framing, EDSML Year 1 末 decide | 24h 不该 commit, time is best test | 5/11 |

---

## 8. Risk Register

### Risk 1: 14d formal pass 结果不如预期

**Risk**: M4-M3 advantage CI 包含 0, 或 H10 不再 hold

**Mitigation**:
- Pre-register 接受 negative finding (synthesis v1 已经写明)
- Doc 升级 framing, 不 push artificial positive
- 重点放 H10 keystone (这个 robust)

---

### Risk 2: SOLWEIG batch run 大规模失败

**Risk**: QGIS headless 不稳定, 1,500 runs 中 >10% fail

**Mitigation**:
- 先 test 10 cells (Phase 2 末段)
- Resume capability + 详细 logging
- Manual rerun failed cells (1-3% expected normal)
- Fall back: 减少到 50-80 cells (仍比 5 cells 强 statistical power)

---

### Risk 3: Modifier ridge fit 不 statistically significant

**Risk**: 150 cells, 17 features ridge, weights CI 包含 0 全部

**Mitigation**:
- 先用 Lasso 选 sparse subset (e.g. 5-7 features)
- 报 partial finding ("LST + water_distance 强 effect, 其他 features 不显著")
- 仍 publishable as negative finding 关于 specific features

---

### Risk 4: Pre-EDSML 时间不够

**Risk**: 14 周难以完成所有 5 phases

**Mitigation**:
- Phase 1-3 是 must-have (calibration + SOLWEIG batch + modifier)
- Phase 4 (risk framework) 可以做 Lite 版 (只 Hazard map + 1 vulnerability layer)
- Phase 5 (write up) 留到 EDSML 入学 first 2 months 做

---

### Risk 5: PhD trajectory 24h 内 over-commitment

**Risk**: today's "想明白 PhD" 的 emotional moment 后过度 anchor

**Mitigation**:
- Don't tell people about PhD aspiration prematurely
- Let Pre-EDSML 工作自然 develop, 看 framework 在实施中是否仍 robust
- EDSML Year 1 跟多 advisors discuss before 决定
- "Time is the best authenticity test"

---

## 9. Success Metrics

### Pre-EDSML (9/1 by enrollment)

**Must-have**:
- ✓ 14d formal pass complete, M0-M7 LOSO ladder verified
- ✓ GHA cron migrated, archive continuing
- ✓ M8 (water) implemented + result reported
- ✓ M9 (17 env features) implemented + result reported  
- ✓ SOLWEIG batch infrastructure built + 50+ cells run
- ✓ Modifier estimation v2 with statistical CI
- ✓ At least Map A (Hazard, CDH-based) produced

**Should-have**:
- ✓ Lasso CV cross-validation of ladder findings
- ✓ Full 150 cells SOLWEIG
- ✓ Approach 2 coupling: cell × hour WBGT matrix
- ✓ All 5 maps (Hazard / Vuln / Exposure / Risk / Risk_elderly)
- ✓ Synthesis v2 doc

**Nice-to-have**:
- ✓ Workshop paper draft
- ✓ Multi-hour modifier (time-invariance test)
- ✓ Calibration ladder design philosophy doc

### EDSML Year 1 (~ next 6/1)

- Mobile validation pilot (with SG collaborator)
- SOLWEIG 扩 500+ cells × 4 seasons
- Approach 4 hourly UMEP shadow modifier
- Thesis chapter draft 1
- PhD application decision (apply or not)

---

## 10. Doc Maintenance

### 10.1 这份 doc 的位置

```text
Synthesis v1 (已完成, 框架版本)
  ↓
Thinking Journal 2026-05-11 (思考过程记录)
  ↓
★ Dev Roadmap 2026-05-11 (这份, 待办与决策)
  ↓
Synthesis v2 (pending, integrating today's framework discussions)
  ↓
Future updates: 每 phase 完成时 mark status + 加 actual findings
```

### 10.2 Update cadence

- 每 phase 完成时 update status
- 每 risk 真实 occur 时 add to log
- Decisions 修订时 archive 旧 decision + 新 decision 并存 (audit trail)

---

## 11. End

这份 dev roadmap 把这次对话 (2026-05-11) 累积的所有 framework discussions 转换成 **actionable 工作 items**, 跨 14 周 5 phases. 配合 thinking journal (思考过程) 跟 synthesis v2 (reference doc 整合 framework refinements), 形成完整 doc trio.

**对未来的你**: 这份 doc 是 forward-looking commitment. 6 个月后回看, 看哪些 phases 真做了, 哪些 deferred, 哪些 abandoned, 哪些 emerged. Decisions log 帮你 trace 决策 rationale.

**Document complete.**

*Authored*: 2026-05-11
*Source*: Distilled from extended discussion captured in `OpenHeat_ThinkingJournal_2026-05-11.md`
*Phases*: 5 (Pre-EDSML) + 5 (EDSML Year 1)
*Items*: ~25 distinct deliverables
*Total effort*: ~14 weeks Pre-EDSML + ongoing post-enrollment

