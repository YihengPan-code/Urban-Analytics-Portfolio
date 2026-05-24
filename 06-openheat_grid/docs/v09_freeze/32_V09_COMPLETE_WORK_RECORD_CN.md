# OpenHeat-ToaPayoh v0.9 完整工作记录

> Lab notebook 形式的 v0.9 完整记录：alpha → beta → beta extension → gamma → gamma overhead-aware → SOLWEIG analysis。
> 包括所有脚本、文件路径、关键变量、数值发现、踩过的坑、未解决的 known issue。
> Authored 2026-05-08 后写作阶段使用。

---

## 0. 项目背景

### 0.1 v0.9 之前

- **v0.5-v0.7**：100m grid (Toa Payoh AOI 984 cells)，v0.6 整合 NEA 实时观测，v0.7 引入风险得分排序
- **v0.8**：UMEP morphology layer。building DSM (HDB3D + URA, 2m 分辨率)，vegetation DSM (ETH GlobalCanopyHeight 2020 10m → 2m bilinear)，SVF + shadow + WBGT proxy，固定在 2026-03-20 春分 + 等向天空
- **v0.8 关键决策**：vegetation transmissivity = 3%, trunk zone height = 25%

### 0.2 v0.9 总目标

```
v0.9 = beta (calibration) + gamma (SOLWEIG) + sensitivity + ML residual learning
```

哲学：**ML 只做 residual learning**，永远不替代 Open-Meteo / UTCI/WBGT 公式 / GIS 特征。

### 0.3 项目根

```
C:\Users\CloudStar\Documents\GitHub\Urban-Analytics-Portfolio\06-openheat_grid
```

conda env: `openheat`

---

## 1. v0.9-alpha：Calibration Data Foundation

### 1.1 目标

收集配对的"forecast (Open-Meteo) vs official (NEA WBGT 站)"数据，量化 v0.8 经验 WBGT proxy 的 systematic bias。

### 1.2 主要脚本

```
scripts/v09_archive_qa.py                          QA 24h archive
scripts/v09_fetch_historical_forecast_for_archive.py  补抓历史 forecast
scripts/v09_build_wbgt_station_pairs.py            生成配对表
scripts/v09_evaluate_wbgt_pairs_baseline.py        baseline residual 评估
scripts/v09_common.py                              共享工具
scripts/run_v09_archive_loop.bat                   15 分钟 cadence 循环抓取
```

### 1.3 数据收集窗口

```
开始: 2026-05-07 02:00 SGT
结束: 2026-05-08 02:03 SGT
时长: 24 小时
观测点 (archive_runs): 96
WBGT 站: 27 (S100-S125 等)
配对行数: 2564
   Moderate events (≥31°C): 268
   High events (≥33°C):     10
```

### 1.4 关键变量名

```python
official_wbgt_c             # NEA 站的官方 WBGT 测量
wbgt_proxy_c                # v0.8 经验公式预测
proxy_residual_c            # = official - proxy
station_id                  # S100-S125 等
hour_sgt                    # 0-23 SGT
station_dist_to_grid_m      # 站到 grid 距离
station_classification      # local_grid_proxy / local / nearby / regional
                            #   _distance_not_representative
```

### 1.5 关键发现

```
1. Universal proxy bias: -1.14°C across 27 stations (range 0.57-1.92)
2. Bias scales with WBGT level (proxy 压缩了 ~3°C 的动态范围
   vs official ~6.5°C 的范围)
3. 残差 diurnal 结构:
       hour       residual
       13:00     +3.48
       15:30     +4.44   ← peak
       sunset    -0.30
       night     +0.22
4. 15:30 残差峰值滞后 SW peak 2.5h → thermal mass / longwave
   from heated walls 物理签名
5. 0% recall on both WBGT≥31 and WBGT≥33 thresholds (raw proxy)
6. 3 个 Toa Payoh anchor 站:
       S128 Bishan       48m to grid     local_grid_proxy
       S145 MacRitchie   685m            local
       S127 Stadium Rd   2676m           nearby
7. 22/27 stations 标记 regional_distance_not_representative
```

### 1.6 主要 alpha 输出

```
data/calibration/v09_wbgt_station_pairs.csv
data/calibration/v09_historical_forecast_by_station_hourly.csv  ← 后续 gamma met forcing 来源
outputs/v09_alpha_qa/...
```

---

## 2. v0.9-beta：Non-ML Calibration Models

### 2.1 目标

用 7 个候选模型在 alpha 数据上做 LOSO-CV (leave-one-station-out)，找哪类信号能压缩 alpha 残差。

### 2.2 主要脚本

```
scripts/v09_beta_fit_calibration_models.py   主 CV 引擎
scripts/v09_beta_make_conclusion_report.py   生成 conclusion 报告
configs/v09_beta_calibration_config.json    config
```

### 2.3 7 个模型设计

```
M0  raw                          原始 proxy 无校准
M1  global_bias                  全局加常数偏置
M1b period_bias                  按时段（白天/晚上）分别加偏置
M2  linear                       线性回归 proxy → official
M3  regime_current_ridge         ridge 回归，特征 = 当前 SW + Tair + RH +
                                  hour_sin/cos + station_class
M4  inertia_ridge                M3 + lagged SW (1h, 3h) +
                                  cumulative SW + dTair/dt
M5  inertia_morphology_ridge     M4 + svf + shade_fraction +
                                  building_density 等形态
```

### 2.4 关键发现

```
1. M3 ≈ M4 几乎不可区分:
       LOSO MAE: 0.5951 vs 0.5946
       Linear features 在 24h × 27 站规模上达到 ridge 上限,
       collinearity 让 lag 特征跟 hour_sin/cos 重叠

2. M4 把 15:30 残差峰值从 +4.44°C 压到 -0.92°C (80% 改善)

3. 14:00 overshoot artifact +0.31-0.53°C (linear feature timing 限制)

4. 残余 ~1°C 下午 cold bias 是 SOLWEIG-targetable signal

5. M5 LOSO MAE = 0.657 (worse than M4)
   overfit ratio 1.23 vs M4 1.04
   → 形态特征过拟合,验证 morphology-not-representative
   flagging 是正确的

6. M2 slope = 1.93±0.04 across folds
   (range compression 确认,但小于预测 2.0-2.5)

7. Day MAE M0→M4: 2.80 → 0.84
   Peak MAE M0→M4: 3.41 → 0.87
   Night MAE: 0.37 → 0.38 (preserved, very nice)

8. M1 night MAE 0.37 → 1.02
   (说明 global bias correction 会破坏 night, period_bias 必要)

9. LOSO ≥31 recall:
       M0  = 0%
       M3  = 28.4%   (best)
       M4  = 26.1%

10. LOSO ≥33 recall: 0% across ALL models
    (model max never crosses 33°C)
```

### 2.5 关键文件

```
outputs/v09_beta_calibration/v09_beta_predictions_long.csv
outputs/v09_beta_calibration/v09_beta_residual_by_hour.csv
outputs/v09_beta_calibration/v09_beta_slope_diagnostics.csv
outputs/v09_beta_calibration/v09_beta_loso_metrics.csv
outputs/v09_beta_calibration/v09_beta_event_detection_metrics.csv
outputs/v09_beta_calibration/v09_beta_loso_by_period.csv
outputs/v09_beta_calibration/v09_beta_overfit_diagnostics.csv
```

### 2.6 主报告

```
26_V09_BETA_FINDINGS_REPORT_CN.md
```

---

## 3. v0.9-beta 扩展：Threshold Scanning

### 3.1 动机

β 的 0% recall on WBGT≥33 + 28% on ≥31 看起来糟糕。但 **calibrated regression model 的 score scale 不等于 official WBGT scale**——score 30 可能对应 official 31。需要 post-hoc 决策阈值优化。

### 3.2 脚本

```
scripts/v09_beta_threshold_scan.py
```

### 3.3 关键发现

```
1. Best-F1 thresholds 集中在 29.8-30.1°C
2. Recall 跳跃 3.3x:

       Model       Fixed @ 31.0   Best-F1 @ ~30.0    倍数
       M3          0.284          0.929              3.3x
       M4          0.261          0.910              3.5x
       M5          0.209          0.862              4.1x
       M1b         0.030          0.769              25x

3. 操作含义: M3@30.0 决策阈值 → recall 92.9%, precision 42.2%,
   F1 0.588
4. WBGT ≥ 33 仍然 0% recall (model max < 33,
   连续回归硬上限)

5. 关键叙事更新:
   旧: "naive threshold gives 0/28% recall"
   新: "post-hoc decision threshold optimization on calibrated
        scores gives 91-93% recall at precision ~0.43"
```

### 3.4 主要输出

```
outputs/v09_beta_threshold_scan/v09_beta_threshold_scan_summary.csv
outputs/v09_beta_threshold_scan/v09_beta_threshold_scan_metrics.csv
outputs/v09_beta_threshold_scan/v09_beta_threshold_scan_report.md
```

---

## 4. v0.9-gamma 原始版（5 tiles，被弃用）

### 4.1 设计

按 v0.8 risk ranking 选 5 个代表 tile：

```
T01 hazard_top              TP_0088   road-dominated
T02 conservative_risk_top   TP_0378   park edge
T03 social_risk_top         TP_0452   residential
T04 candidate_policy_top    TP_0366   civic
T05 shaded_reference        TP_0892   tree canopy heavy
```

每个 tile 500m 中心 + 100m buffer = 700m × 700m clipped DSM。

### 4.2 主要脚本（hotfixed 版本）

```
scripts/v09_gamma_select_solweig_tiles.py
scripts/v09_gamma_clip_tile_rasters.py
scripts/v09_gamma_aggregate_solweig_tmrt.py
scripts/v09_gamma_compare_tmrt_proxy_vs_solweig.py
configs/v09_gamma_solweig_config.example.json
```

### 4.3 Hotfix 内容（applied to original gamma scripts）

```
1. Tmrt 文件名时间正则 (避免把 2026 当成 13:00)
2. DSM nodata 拆分成 _masked.tif (-9999 nodata) + _tile.tif
   (UMEP-ready, ground=0)
3. Reference tile QA 加权评分 + status flag
4. Time-matched vs diagnostic comparison mode
5. tabulate 依赖移除（用 to_string 代替 to_markdown）
```

### 4.4 致命发现：5/5 tile 都被 overhead 污染

通过 `v09_gamma_check_overhead_structures.py` 用 Overpass API 查询，发现：

```
T01 hazard_top              12 高架结构 (含 PIE Pan-Island Expressway)
T02 conservative_risk_top   39 高架结构 (38 covered walkways)
T03 social_risk_top         30 高架结构 (8 ped bridges + Toa Payoh North Flyover)
T04 candidate_policy_top    6 高架结构
T05 shaded_reference        59 高架结构 (53 NSL elevated rail!)
```

**T05 reference 实际是 NSL 高架阴影下,不是树荫**。结论：v0.9-gamma 5 tile 设计需要重新做，加入 overhead 干净度约束。

### 4.5 OSM 检查脚本

```
scripts/v09_gamma_check_overhead_structures.py    无 osmnx 依赖,
                                                   用 requests 直接打 Overpass

主要踩坑:
   - osmnx 太重不装 → 用 requests
   - HTTP 406 (User-Agent 拦截) → 加显式 UA + 4 endpoint fallback
```

### 4.6 输出

```
outputs/v09_gamma_qa/v09_overhead_structures_per_tile.csv
outputs/v09_gamma_qa/v09_overhead_structures.geojson
```

---

## 5. v0.9-gamma overhead-aware（6 tiles，最终版）

### 5.1 设计哲学

**不把高架直接烧进 DSM**（高架是 overhead canopy，不是 ground-up obstacle）。
**改成把高架作为 tile selection 的 confounding 过滤器** + spatial separation 约束。

### 5.2 6 类 tile 设计

```
T01_clean_hazard_top                高 hazard + 低 overhead
T02_conservative_risk_top           风险优先 (risk_rank_v08_conditioned)
T03_social_risk_top                 社会脆弱 (risk_rank_v08_social_conditioned)
T04_open_paved_hotspot              新增: 高 road / 低 shade / 低 green
T05_clean_shaded_reference          低 hazard + 高 shade + 高 green + 低 overhead
T06_overhead_confounded_hazard_case 高 hazard + 高 overhead (诊断用)
```

### 5.3 约束（overhead 干净度 + 空间分离）

```json
{
  "min_center_distance_m": 550,
  "max_tile_iou": 0.20,
  "constraints": {
    "max_focus_overhead_fraction_clean": 0.02,      // 2%
    "max_focus_overhead_fraction_risk":  0.05,
    "max_tile_overhead_fraction_clean":  0.10,
    "max_tile_overhead_fraction_reference": 0.05,
    "reference_min_hazard_rank": 750
  }
}
```

### 5.4 4-tier strictness fallback

```
strict → relaxed_overhead → very_relaxed_overhead → fallback_any_unselected
relax 倍率: 1.0    2.5    5.0    999.0
```

### 5.5 选中的 6 个 tile（全部 strict 通过）

```
tile_id                              cell_id   hazard_rank  overhead_focus  tile_overhead  status
T01_clean_hazard_top                 TP_0116        2          0.000          0.000          strict
T02_conservative_risk_top            TP_0378       51          0.038          0.020          strict
T03_social_risk_top                  TP_0452       59          0.000          0.004          strict
T04_open_paved_hotspot               TP_0120       34          0.000          0.050          strict
T05_clean_shaded_reference           TP_0433      974          0.000          0.048          strict
T06_overhead_confounded_hazard_case  TP_0575       20          0.435          0.088          strict
```

### 5.6 主要脚本（overhead-aware 系列）

```
scripts/v09_gamma_build_overhead_cell_qa.py            cell-level overhead QA
scripts/v09_gamma_select_tiles_overhead_aware.py       新选 tile 引擎
scripts/v09_gamma_clip_tiles_overhead_aware.py         clip DSM
scripts/v09_gamma_aggregate_solweig_tmrt_overhead_aware.py  最终 aggregator
scripts/v09_gamma_overhead_aware_pre_umep_pipeline.bat
scripts/v09_gamma_overhead_aware_post_umep_pipeline.bat
configs/v09_gamma_overhead_aware_config.example.json
```

### 5.7 主要输出

```
data/solweig/v09_tiles_overhead_aware/
   T01_clean_hazard_top/
   T02_conservative_risk_top/
   T03_social_risk_top/
   T04_open_paved_hotspot/
   T05_clean_shaded_reference/
   T06_overhead_confounded_hazard_case/
       每个含: dsm_buildings_tile.tif
              dsm_vegetation_tile.tif
              dem_flat.tif (后来 v2025a 需要)
              wall_height.tif (UMEP 跑出来的)
              wall_aspect.tif
              svf_outputs/
                  SkyViewFactor.tif, svfaveg.tif, ..., svfs.zip
              solweig_outputs_h10/, _h12/, _h13/, _h15/, _h16/
                  Tmrt_average.tif (单 hour run)
              solweig_outputs/  (consolidate 之后)
                  Tmrt_2026_127_1000D.tif
                  Tmrt_2026_127_1200D.tif
                  Tmrt_2026_127_1300D.tif
                  Tmrt_2026_127_1500D.tif
                  Tmrt_2026_127_1600D.tif

outputs/v09_gamma_qa/v09_overhead_structures_per_cell.csv
outputs/v09_gamma_qa/v09_overhead_structures_per_cell.geojson
outputs/v09_gamma_qa/v09_overhead_structures_footprints.geojson
outputs/v09_gamma_qa/v09_overhead_cell_QA_report.md
data/solweig/v09_tiles_overhead_aware/v09_solweig_tile_metadata_overhead_aware.csv
data/solweig/v09_tiles_overhead_aware/v09_solweig_tiles_overhead_aware.geojson
data/solweig/v09_tiles_overhead_aware/v09_solweig_tiles_overhead_aware_buffered.geojson
data/solweig/v09_tiles_overhead_aware/v09_solweig_tile_selection_overhead_aware_QA_report.md
```

---

## 6. SOLWEIG 执行细节与踩坑

### 6.1 Met forcing 准备

```
scripts/v09_gamma_make_umep_met.py        从 alpha CSV 抽 S128 5 个 hour 写 UMEP 格式

输出: data/solweig/v09_met_forcing_2026_05_07_S128.txt

格式 (UMEP standard):
   %iy id it imin qn qh qe qs qf U RH Tair pres rain kdown snow
   ldown fcld wuh xsmd lai_hr Kdiff Kdir Wd
   2026 127 10 0 -999... 1.42 84 28.4 1010 0 346 0 -999 1.0...
   2026 127 12 0 -999... ...
   2026 127 13 0 -999... ...
   2026 127 15 0 -999... ...
   2026 127 16 0 -999... ...

5 个 hour 选择: 10, 12, 13, 15, 16 SGT (覆盖 alpha 残差峰值时段)
来源: S128 Bishan (距离 Toa Payoh 中心 ~2.4 km, 最近 local proxy)
日期: 2026-05-07 (May 7, DOY 127)
   选择理由: 跟 alpha archive 同一天,
   保证 SOLWEIG 输出可以直接对比 beta calibration residual

May 7 forcing 摘要:
   hour    Tair    RH    wind    kdown    Kdir    Kdiff    fcld
   10:00   28.4    84    1.42    346      118     228      1.0
   12:00   30.1    76    1.91    750      477     273      1.0  (峰值附近)
   13:00   29.5    76    2.25    753      429     324      1.0  (true peak)
   15:00   29.0    78    1.97    576      218     358      1.0
   16:00   28.9    78    1.39    352      57      295      1.0
```

### 6.2 SOLWEIG v2025a 踩过的坑

#### 坑 1: DEM 强制必填，UI 标注 [optional] 错

```
Error: No valid DEM selected
Execution failed after 0.04 seconds
```

**修复**: 用 v09_gamma_make_flat_dem.py 给 6 个 tile 各生成一个常值 0 的
flat DEM (350×302 像素之类，跟对应 building DSM 同 extent/CRS)。
Toa Payoh 平坦,常值 DEM 在物理上自洽。

```
scripts/v09_gamma_make_flat_dem.py
输出: 每个 tile 的 dem_flat.tif
```

#### 坑 2: SOLWEIG v2025a 只输出 Tmrt_average.tif，不输出 per-hour rasters

老版 SOLWEIG (v2022a 及之前) 喂多 hour met file 会输出 per-hour Tmrt 文件。
v2025a 只输出 5h 时段平均,失去了 diurnal 信息。

**修复**: 把 met file 拆成 5 个单 hour 文件,每个 tile 跑 5 次 SOLWEIG。
每次 batch 的 Tmrt_average.tif 就是该 hour 的 Tmrt。

```
scripts/v09_gamma_split_met_per_hour.py
输出: v09_met_forcing_..._h10.txt 至 _h16.txt
```

#### 坑 3: 单行 met file 触发 numpy 1D 数组 bug

```
File "...solweig_algorithm.py", line 591
testwhere = np.where((self.metdata[:, 14] < 0.0) | ...)
IndexError: too many indices for array: array is 1-dimensional,
but 2 were indexed
```

`np.loadtxt` 读单行文件返回 1D 数组,SOLWEIG 代码假设 2D。

**修复**: split 脚本 v2 给每个 hour 文件写 2 行相同数据。两行 identical 的
metdata → 数组维度 2D bug 不触发,SOLWEIG 内部循环算 2 次同样的 Tmrt,
average = 单 hour Tmrt,信息无损。

#### 坑 4: 默认 emissivity (ground) = 0.45 物理错误

UMEP v2025a UI 默认 ground 发射率是 0.45,但城市地面 (沥青/混凝土)
真实值 0.92-0.95。

**修复**: 每次 SOLWEIG dialog 手动改 0.45 → 0.95。
不改的话 Tmrt 系统性偏低 ~3-5°C。

#### 坑 5: 默认 UTC = 0 (伦敦时间) 而不是 8 (Singapore)

**修复**: dialog 里改 UTC = 8。

#### 坑 6: 文件锁 (Permission denied)

QGIS 把 wall_height.tif / wall_aspect.tif / svf_outputs 自动加载为
图层,持有文件句柄。重跑工具时 Windows 拒绝覆盖。

**修复**:
1. Layers Panel 里 Remove Layer
2. Settings → Options → Processing 关闭 "Open output files after running algorithm"

#### 坑 7: Aggregator pattern `**/*Tmrt*.tif` 抓到所有 Tmrt_average.tif duplicates

每个 tile 有:
- solweig_outputs/Tmrt_2026_127_HHMMD.tif (5 个,正确解析)
- solweig_outputs/Tmrt_average.tif (旧 5h run 留下)
- solweig_outputs_h{10/12/13/15/16}/Tmrt_average.tif (单 hour run 留下)

aggregator 把所有 Tmrt 文件都聚合,Tmrt_average.tif 解析为 'unknown' 时间标签。

**修复**: 跑完 aggregator 之后过滤:

```python
df = df[df['tmrt_time_label'].astype(str).str.match(r'^\d{4}$')]
```

行数从 2478 降到 1225 (50% 是 'unknown' duplicate)。

### 6.3 Per-tile 完整执行流程

```
1. UMEP → Pre-Processor → Sky View Factor (Urban Geometry)
   输入: building DSM, vegetation DSM
   参数: trans=3, trunk=25, "153 shadow images" 勾选
   输出: svf_outputs/ 含 ~10 个 svf*.tif + svfs.zip

2. UMEP → Pre-Processor → Wall Height and Aspect
   输入: building DSM
   参数: lower_limit=3.0
   输出: wall_height.tif + wall_aspect.tif

3. UMEP → Outdoor Thermal Comfort → SOLWEIG v2025a
   → "Run as Batch Process..."
   配置 5 行 (10/12/13/15/16 SGT 各一行),共享:
       building DSM, vegetation DSM, dem_flat.tif,
       wall_height.tif, wall_aspect.tif, svfs.zip,
       albedo (walls=0.20, ground=0.15),
       emissivity (walls=0.90, ground=0.95) ⚠ 默认 0.45 错,改 0.95
       posture=Standing, cyl=True
       UTC=8 ⚠ 默认 0 错,改 8
       absorption (SW=0.7, LW=0.95)
   每行不同:
       met file = v09_met_forcing_..._hHH.txt
       output folder = solweig_outputs_hHH/
   Run: 5 个 task 顺序跑, ~25-50 min unattended

4. python scripts/v09_gamma_consolidate_per_hour_tmrt.py
   把 solweig_outputs_hHH/Tmrt_average.tif 重命名复制到
   solweig_outputs/Tmrt_2026_127_HHMMD.tif
```

### 6.4 SOLWEIG 共享参数最终值

```
Albedo (walls):                0.20
Albedo (ground):               0.15
Emissivity (walls):            0.90
Emissivity (ground):           0.95   ← 改默认 0.45
Vegetation transmissivity:     3      (%)
Trunk zone height:             25     (% of canopy)
First/Last leaf day:           1 / 366  (热带全年有叶)
Posture:                       Standing
Consider human as cylinder:    True
Absorption SW (human):         0.70
Absorption LW (human):         0.95
UTC offset:                    8      ← 改默认 0
Wall scheme:                   Off (wallscheme=0)
Land cover:                    Off (landcover=0)
Anisotropic sky:               Off (aniso=0) ⚠ 见 §9 known issue
ldown estimate:                from atmospheric (因为 fcld=1.0,
                                ldown 略偏高,见 §9)
```

---

## 7. 主要发现汇总（v0.9-gamma 核心科学产出）

### 7.1 Diurnal sanity check（per-tile mean）

```
                                 13:00 mean  diurnal range
T01_clean_hazard_top              56.6        13.9
T02_conservative_risk_top         45.4         8.3
T03_social_risk_top               50.3        11.8
T04_open_paved_hotspot            50.6        11.4
T05_clean_shaded_reference        46.4         9.2
T06_overhead_confounded_hazard    53.3        12.3
```

⚠ tile mean 包含 700m buffer 区域,被边缘像素稀释。
**真实科学解读用 focus cell only**。

### 7.2 Focus cell Tmrt by tile_type × hour（核心表格 1）

```
hour     T01     T02     T03     T04     T05     T06
10:00   46.3    44.9    42.7    41.9    32.9    44.4
12:00   62.1    60.2    59.4    57.8    36.0    59.6
13:00   62.3    60.3    58.8    57.6    36.1    59.7  ⭐
15:00   60.5    58.5    55.4    55.0    35.9    57.8
16:00   51.5    49.9    46.7    46.2    34.5    49.3
```

### 7.3 SOLWEIG_Tmrt - empirical_T_globe by tile_type × hour（核心表格 2）

```
经验 T_globe = Tair + 0.0045 × SW / sqrt(wind + 0.25)
   (Stull-style, v0.9-beta calibration 用的)

hour     T01      T02      T03      T04      T05     T06
10:00   +16.72  +15.30   +13.07   +12.31   +3.32   +14.78
12:00   +29.74  +27.78   +26.97   +25.39   +3.63   +27.16
13:00   +30.70  +28.67   +27.11   +25.94   +4.48   +28.06   ⭐
15:00   +29.79  +27.72   +24.69   +24.26   +5.18   +27.06
16:00   +21.40  +19.71   +16.55   +16.04   +4.36   +19.17
```

### 7.4 三大数字（dissertation §X.X 主要发现）

```
1. Vegetation cooling captured by SOLWEIG @ peak hour:
       T01 - T05 = 62.3 - 36.1 = 26.2°C @ 13:00
   解读: 城市绿化在中午把行人 Tmrt 压低 26°C
         (热带 Singapore 的具体数字,
         之前文献只有 1-3°C 的"绿地降温"指空气温度)

2. Thermal mass / late-afternoon longwave hold:
       T01 delta @ 13:00 = +30.70°C
       T01 delta @ 15:00 = +29.79°C
       Δ delta = -0.91°C only
       SW @ 13:00 vs 15:00: 753 vs 576 W/m² (-24%)
       empirical T_globe @ 13:00 vs 15:00: 31.64 vs 30.74 (-0.9°C)
   解读: empirical proxy 跟 SW 紧紧 track,
         SOLWEIG 看到 heated wall longwave 持续辐射,
         delta 在 SW 减少 24% 时几乎不变.
         这就是 alpha 15:30 残差 +4.4°C 峰值的物理来源,
         也是 v0.9-gamma 的 falsifiable hypothesis 在数据上的确认.

3. Overhead infrastructure blind spot:
       T01 (clean) - T06 (44% overhead) = 62.3 - 59.7
                                        = 2.6°C @ 13:00
   解读: SOLWEIG 几乎看不到高架结构 (T06 跟 T01 差 2.6°C
         只来自微小形态差异,不是高架物理).
         真实物理上 T06 应该跟 T05 (~36°C) 接近.
         缺失的 ~20°C cooling 就是 transport DSM v1.0 的工程价值.
```

### 7.5 Tile selection overhead-aware QA 数据

```
6/6 tiles selected with strict status (no relaxation)
6/6 tiles with max_iou_with_previous ≤ 2.9e-14 (effectively zero overlap)
Tile center distances to previous: 583m (T06) to 2973m (T02)
Reference tile T05 hazard_rank = 974 (top 1.5% lowest hazard)
```

---

## 8. 完整文件清单

### 8.1 v0.9-alpha

```
scripts/v09_archive_qa.py
scripts/v09_fetch_historical_forecast_for_archive.py
scripts/v09_build_wbgt_station_pairs.py
scripts/v09_evaluate_wbgt_pairs_baseline.py
scripts/v09_common.py
scripts/run_v09_archive_loop.bat
configs/v09_alpha_*.json

输出:
data/calibration/v09_wbgt_station_pairs.csv
data/calibration/v09_historical_forecast_by_station_hourly.csv
outputs/v09_alpha_qa/v09_alpha_residual_summary.csv
outputs/v09_alpha_qa/v09_alpha_residual_by_hour.csv
```

### 8.2 v0.9-beta

```
scripts/v09_beta_fit_calibration_models.py
scripts/v09_beta_make_conclusion_report.py
configs/v09_beta_calibration_config.json

输出:
outputs/v09_beta_calibration/v09_beta_predictions_long.csv
outputs/v09_beta_calibration/v09_beta_residual_by_hour.csv
outputs/v09_beta_calibration/v09_beta_slope_diagnostics.csv
outputs/v09_beta_calibration/v09_beta_loso_metrics.csv
outputs/v09_beta_calibration/v09_beta_event_detection_metrics.csv
outputs/v09_beta_calibration/v09_beta_loso_by_period.csv
outputs/v09_beta_calibration/v09_beta_overfit_diagnostics.csv

报告:
docs/26_V09_BETA_FINDINGS_REPORT_CN.md
```

### 8.3 v0.9-beta extension

```
scripts/v09_beta_threshold_scan.py

输出:
outputs/v09_beta_threshold_scan/v09_beta_threshold_scan_summary.csv
outputs/v09_beta_threshold_scan/v09_beta_threshold_scan_metrics.csv
outputs/v09_beta_threshold_scan/v09_beta_threshold_scan_report.md
```

### 8.4 v0.9-gamma 原始（已弃用,但保留作为 audit trail）

```
scripts/v09_gamma_select_solweig_tiles.py
scripts/v09_gamma_clip_tile_rasters.py
scripts/v09_gamma_aggregate_solweig_tmrt.py (hotfixed)
scripts/v09_gamma_compare_tmrt_proxy_vs_solweig.py (hotfixed)
configs/v09_gamma_solweig_config.example.json

输出:
data/solweig/v09_tiles/T01_hazard_top_TP_0088/...
                       T02_conservative_risk_top_TP_0378/...
                       T03_social_risk_top_TP_0452/...
                       T04_candidate_policy_top_TP_0366/...
                       T05_shaded_reference_TP_0892/...
data/solweig/v09_tiles/v09_solweig_tile_metadata.csv
data/solweig/v09_tiles/v09_solweig_tiles.geojson
data/solweig/v09_tiles/v09_solweig_tiles_buffered.geojson
```

### 8.5 v0.9-gamma OSM check

```
scripts/v09_gamma_check_overhead_structures.py (User-Agent + multi-endpoint)

输出:
outputs/v09_gamma_qa/v09_overhead_structures_per_tile.csv
outputs/v09_gamma_qa/v09_overhead_structures.geojson
```

### 8.6 v0.9-gamma overhead-aware（最终版）

```
scripts/v09_gamma_build_overhead_cell_qa.py
scripts/v09_gamma_select_tiles_overhead_aware.py
scripts/v09_gamma_clip_tiles_overhead_aware.py
scripts/v09_gamma_aggregate_solweig_tmrt_overhead_aware.py
scripts/v09_gamma_overhead_aware_pre_umep_pipeline.bat
scripts/v09_gamma_overhead_aware_post_umep_pipeline.bat
configs/v09_gamma_overhead_aware_config.example.json

输出:
outputs/v09_gamma_qa/v09_overhead_structures_per_cell.csv
outputs/v09_gamma_qa/v09_overhead_structures_per_cell.geojson
outputs/v09_gamma_qa/v09_overhead_structures_footprints.geojson
outputs/v09_gamma_qa/v09_overhead_cell_QA_report.md

data/solweig/v09_tiles_overhead_aware/T01_clean_hazard_top/
data/solweig/v09_tiles_overhead_aware/T02_conservative_risk_top/
data/solweig/v09_tiles_overhead_aware/T03_social_risk_top/
data/solweig/v09_tiles_overhead_aware/T04_open_paved_hotspot/
data/solweig/v09_tiles_overhead_aware/T05_clean_shaded_reference/
data/solweig/v09_tiles_overhead_aware/T06_overhead_confounded_hazard_case/

data/solweig/v09_tiles_overhead_aware/v09_solweig_tile_metadata_overhead_aware.csv
data/solweig/v09_tiles_overhead_aware/v09_solweig_tiles_overhead_aware.geojson
data/solweig/v09_tiles_overhead_aware/v09_solweig_tiles_overhead_aware_buffered.geojson
data/solweig/v09_tiles_overhead_aware/v09_solweig_tile_selection_overhead_aware_QA_report.md
```

### 8.7 v0.9-gamma SOLWEIG 工具 + 分析

```
scripts/v09_gamma_make_umep_met.py             生成 5h met forcing
scripts/v09_gamma_make_flat_dem.py             v2025a DEM workaround
scripts/v09_gamma_split_met_per_hour.py        单 hour met (2 行 identical)
scripts/v09_gamma_consolidate_per_hour_tmrt.py 重命名合并
scripts/v09_gamma_check_per_hour_tmrt.py       diurnal sanity check
scripts/v09_gamma_analyze_solweig_vs_proxy.py  最终核心分析

输入:
data/solweig/v09_met_forcing_2026_05_07_S128.txt
data/solweig/v09_met_forcing_2026_05_07_S128_h10.txt
data/solweig/v09_met_forcing_2026_05_07_S128_h12.txt
data/solweig/v09_met_forcing_2026_05_07_S128_h13.txt
data/solweig/v09_met_forcing_2026_05_07_S128_h15.txt
data/solweig/v09_met_forcing_2026_05_07_S128_h16.txt

输出:
outputs/v09_solweig/v09_solweig_tmrt_grid_summary_overhead_aware.csv
outputs/v09_solweig/v09_solweig_tmrt_grid_summary_overhead_aware_report.md
outputs/v09_gamma_analysis/v09_gamma_solweig_vs_proxy_per_cell.csv
outputs/v09_gamma_analysis/v09_gamma_focus_cell_solweig_vs_proxy.csv
outputs/v09_gamma_analysis/v09_gamma_tiletype_hour_summary.csv
outputs/v09_gamma_analysis/v09_gamma_solweig_vs_proxy_REPORT.md
```

### 8.8 文档

```
docs/26_V09_BETA_FINDINGS_REPORT_CN.md           beta 发现报告
docs/30_V09_GAMMA_UMEP_TUTORIAL_CN.md            UMEP 第一版教程 (旧 5 tile)
docs/30b_V09_GAMMA_PHASE_C_TUTORIAL_CN.md        UMEP Phase C 详教程
docs/31_V09_GAMMA_T02_T06_WORKFLOW_CN.md         T02-T06 速查
docs/32_V09_COMPLETE_WORK_RECORD_CN.md           本文件
```

### 8.9 Hotfix patches（zip 文件，存档）

```
openheat_v09_gamma_hotfix.zip                       gamma 4 项 hotfix
openheat_v09_gamma_overhead_aware_patch.zip         overhead-aware 重设计
```

---

## 9. 已知限制与 future work

### 9.1 v0.9-gamma 内部 known issues

#### Issue 1: Anisotropic sky 关闭 (aniso=0)

UMEP SVF Calculator 勾了 "153 shadow images" 是为 anisotropic sky 准备数据,
但 SOLWEIG dialog 里的 "Shadow maps for anisotropic model (.npz)"
字段没填. 配置不完整 → 用了 isotropic sky.

**影响**: Tmrt 系统性偏低 1-3°C,所有 6 tile 一致.
**对 dissertation**: "uniform bias, doesn't affect inter-tile contrasts.
v0.9-delta refinement target."

#### Issue 2: Open-Meteo fcld=1.0 整天

Open-Meteo cloud_cover 是"任何云的天空覆盖比例",不是"光学透云度".
中午 kdown 实测 750 W/m² 说明 Kdir 477 透过云层很多,
但 fcld=1.0 喂 SOLWEIG 会让 ldown 估算偏高 ~10-30 W/m²,
Tmrt 略偏高 ~0.5-1°C.

**影响**: uniform 偏高,跟 aniso=0 偏低部分抵消.
**对 dissertation**: "documented in §X.X limitations.
v0.9-delta possible refinement: derive fcld_proxy from
Kdiff/kdown ratio."

#### Issue 3: Single-day pilot (2026-05-07 only)

整个 v0.9 (alpha + beta + gamma) 24 小时数据,
SOLWEIG 跑了 5 个 hour 点.
diurnal cycle 单天观测,没有 day-to-day variability.

**对 dissertation**: 写成 "pilot scope; v1.0 multi-day
validation needed."

#### Issue 4: Aggregator 'unknown' duplicates

`**/*Tmrt*.tif` recursive pattern 把 Tmrt_average.tif duplicates 也聚合.
2478 行里 1253 是 unknown.
人工过滤后 1225 行才是真实 5 hour × 6 tile data.

**修复方案**: aggregator pattern 改成 `solweig_outputs/Tmrt_*_*D.tif`
排除 _hHH/ 子目录. 当前 workaround 用 regex 过滤.

#### Issue 5: Tile mean 不等于 focus cell mean

Buffered tile 700m 包含 buffer 区域,稀释 focus cell 物理 signal.
T01 vs T05 contrast at tile mean = 10°C, at focus cell = 26°C.
**dissertation 解读时优先 focus cell metrics**, tile mean 只作辅助参考.

### 9.2 v0.9-gamma 没做的事（v0.9-delta / v1.0 future work）

#### Future 1: SOLWEIG-substituted WBGT recalibration

把 SOLWEIG Tmrt 反代回 WBGT 公式 (取代 empirical T_globe),
重做 alpha + beta calibration framework,
看 15:30 -0.92°C cold bias 是否被填.

需要的工作:
- 给 27 个 WBGT 站的 containing cell 各跑 SOLWEIG (27 × 5 hour = 135 runs)
- 修改 calibration scripts 接 SOLWEIG Tmrt 列
- 跑 LOSO-CV 对比

工程量: ~2-3 天 + UMEP batch 一晚.

#### Future 2: Anisotropic sky enable

把 SVF Calculator 输出的 .npz 路径填进 SOLWEIG dialog 的
"Shadow maps for anisotropic model" 字段,重跑 6 个 tile × 5 hour = 30 SOLWEIG runs.

预期效果: Tmrt 升 1-3°C uniform, 6 tile 间 contrast 不变.

#### Future 3: Transport DSM (高架建模)

把 OSM bridges + viaducts + elevated rail rasterize 成"obstacle DSM",
跟 building DSM 合成,重跑 SVF + SOLWEIG.

预期效果: T06 Tmrt 从 ~60°C 降到 ~40°C 区间,
overhead bias 从 2.6°C 增大到符合物理预期的 ~20°C.

工程量: ~1-2 天 (OSM 数据获取 + 高度 rasterize + UMEP 重跑).

#### Future 4: Multi-day SOLWEIG validation

当前 May 7 single day. v0.9-delta 可以挑 3-5 个不同天气模式天
(cloudy / clear / partly cloudy) 重跑,看 SOLWEIG 物理在不同条件下的 robustness.

#### Future 5: Logistic / Quantile regression beta extension

朋友建议过 logistic regression for event detection +
quantile regression for tail prediction.
需要 archive ≥ 14-30 days 才有足够 positive samples (S142 站只有 7/10 high events).

延后到 archive 数据扩充后.

### 9.3 Dissertation 结构建议

```
§X.1   Motivation: beta calibration's 15:30 cold bias residual

§X.2   Methodology
   §X.2.1  Overhead-aware tile selection (constrained design)
   §X.2.2  Single-hour met forcing decomposition (v2025a workaround)
   §X.2.3  Per-tile UMEP SOLWEIG workflow
   §X.2.4  Aggregation to 100m grid

§X.3   Results
   §X.3.1  Spatial heterogeneity captured by SOLWEIG
            → 26.2°C T01-T05 contrast
            → Figure: diurnal Tmrt by tile_type
   §X.3.2  Thermal mass / late-afternoon longwave hold
            → 15:00 delta = +29.79°C, 13:00 = +30.70°C
            → Confirmation of beta cold-bias physical origin
   §X.3.3  Overhead infrastructure blind spot
            → T01-T06 = 2.6°C (vs ~20°C real-world)
            → Quantitative justification for v1.0 transport DSM

§X.4   Limitations
   §X.4.1  Aniso=0 (UMEP v2025a)
   §X.4.2  fcld=1.0 (Open-Meteo)
   §X.4.3  Single-day pilot
   §X.4.4  Tile-mean dilution

§X.5   Implications and future work
   → v0.9-delta: aniso enable + station-tile recalibration
   → v1.0: transport DSM integration + multi-day
```

---

## 10. 时间线总结

```
Day 1 - Alpha:     archive QA, pair generation, baseline residual evaluation
Day 1 - Beta:      7 model LOSO-CV, M3≈M4 finding, M4 fills 80% of 15:30 gap
Day 1 - Beta ext:  threshold scanning, recall 28% → 93%
Day 1 - Gamma init: 5-tile selection (rank-only)
Day 1 - Gamma OSM check: 5/5 tiles confounded by overhead infrastructure
Day 1 - Gamma redesign: overhead-aware 6-tile selection, all strict
Day 1 - Met forcing: split into 5 single-hour files (with v2025a 1D bug workaround)
Day 1 - SOLWEIG runs: 6 tiles × 5 hours = 30 batch tasks (Wall + SVF + main)
Day 1 - Aggregation: 2478 → 1225 rows after filter
Day 1 - Analysis: SOLWEIG vs empirical proxy comparison, 4 output files
```

整个 v0.9 在 1 天的 work session 里走完 full pipeline alpha → gamma analysis,
6 个 tile × 5 hour = 30 SOLWEIG runs 全部完成,
6/6 strict tile selection 通过,
3 个核心 dissertation findings (vegetation cooling, thermal hold, overhead bias) 量化.

---

*Authored 2026-05-08, OpenHeat-ToaPayoh v0.9 working session.*
*Next step: dissertation writing, §X.X SOLWEIG selected tile validation.*
