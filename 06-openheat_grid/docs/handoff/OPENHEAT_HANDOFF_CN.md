# OpenHeat-ToaPayoh 项目交接文档

> 用途：在新的 ChatGPT 对话窗口、项目评审、代码交接或 dissertation/portfolio 写作时，让新的 AI/协作者快速理解 OpenHeat-ToaPayoh 的版本历史、当前状态、关键结论、文件结构和下一步开发路线。
>
> 当前状态：v0.9 已完成 audit freeze；v1.0 即将进入 augmented building DSM pilot。
>
> 项目根目录：`C:\Users\CloudStar\Documents\GitHub\Urban-Analytics-Portfolio\06-openheat_grid`
>
> Conda 环境：`openheat`

---

## 0. 一句话总结

OpenHeat-ToaPayoh 是一个基于开放数据的城市热压力预测与风险优先级系统。项目从 v0.6 的 live weather / WBGT workflow，推进到 v0.7 的真实 Toa Payoh 100m grid，再到 v0.8 的 UMEP building+canopy SVF/shade，最后在 v0.9 建立 official WBGT calibration、SOLWEIG selected-tile Tmrt 实验和 building DSM completeness audit。

当前最重要的转折点是：

> v0.9 发现 HDB3D + URA building DSM 相对 OSM-mapped building area 只有约 25.8% completeness，并且高 hazard tiles 往往是 DSM coverage gap regions。因此 v0.7–v0.9 的 heat-hazard ranking 不能再被视为最终真实热风险排序，而应冻结为 current-DSM audit prototype。v1.0 的核心任务是构建 multi-source augmented building DSM，然后重跑 morphology 和 hazard ranking。

---

## 1. 当前版本状态

### v0.6–v0.6.4

目标：建立 live weather + NEA WBGT observation + forecast workflow。

完成内容：

- 接入 Open-Meteo live forecast。
- 接入 NEA / data.gov.sg official WBGT、temperature、humidity、wind observations。
- 修复 v1/v2 WBGT API schema。
- 建立 long-format archive。
- 初步 hotspot forecast workflow。

关键结论：

- live forecast pipeline 可运行。
- official WBGT 应用于 calibration / validation，而不是重新计算成另一个 WBGT。
- archive 必须是 long format，不能混入旧 wide format。

---

### v0.7-alpha / beta

目标：从 sample grid 转向真实 Toa Payoh 100m grid。

完成内容：

- 真实 100m grid features。
- URA / NParks / road / park / land-use features。
- GEE 导出的 GHSL height、Dynamic World tree/grass/water/built-up、Sentinel-2 NDVI。
- 修复 `impervious_fraction` 过高问题。
- 生成 beta final grid：`data/grid/toa_payoh_grid_v07_features_beta_final.csv`。

关键结论：

- v0.7-beta 结果中 top hotspots 倾向于低绿量、低 shade、高 road_fraction、高 SVF 的 open/paved/road-dominated cells。
- `impervious_fraction` 修复后 ranking 不变，说明它主要是 diagnostic feature，而非主 rank driver。

---

### v0.7.1

目标：加入 vulnerability / outdoor exposure，把 heat hazard 转成 risk-priority scenarios。

完成内容：

- Subzone elderly / children proportions。
- Bus stop / MRT exit / sports facility outdoor exposure proxy。
- Hawker / eldercare / preschool vulnerability nodes。
- `vulnerability_score_v071`。
- `outdoor_exposure_score_v071`。
- hazard-conditioned risk ranking。

关键结论：

- 纯 hazard ranking 和 risk ranking 应分开解释。
- `risk_rank_v071_conditioned` 不是“最热排名”，而是在较高 heat hazard cells 中考虑 vulnerability / exposure 的干预优先级。

---

### v0.8-alpha / beta

目标：用 UMEP-derived morphology 替代经验 `svf` / `shade_fraction` proxy。

完成内容：

- HDB3D + URA merged building layer。
- ETH Global Canopy Height 2020 10m → 2m vegetation DSM。
- 2m building DSM。
- UMEP SVF + shadow building-only。
- UMEP SVF + shadow building+vegetation。
- 用 `svf_umep_mean_open_with_veg` 和 `shade_fraction_umep_10_16_open_with_veg` 替换 v0.7 proxy。
- v0.8 risk scenarios：hazard-only, conservative-conditioned, social-conditioned, candidate-policy。

关键结论：

- v0.7 proxy vs v0.8 UMEP+vegetation Spearman ≈ 0.5239，top20 overlap 4/20，说明 morphology layer 是高敏感组件。
- v0.8 top hotspots 具有高 SVF、低 shade、低 tree/NDVI/GVI、较高 road fraction 的物理合理特征。
- v0.8 UMEP+vegetation 应作为 current primary morphology layer，但随后 v0.9 audit 发现 building DSM completeness 不足，v0.8 当前排名也需冻结为 current-DSM baseline。

---

### v0.9-alpha

目标：建立 official WBGT calibration foundation。

输入：

- `data/archive/nea_realtime_observations.csv`
- `data/calibration/v09_historical_forecast_by_station_hourly.csv`
- `data/calibration/v09_wbgt_station_pairs.csv`

完成内容：

- 24h NEA archive QA。
- 27 official WBGT stations。
- 2564 paired WBGT station observations。
- Historical forecast / weather forcing pairing。
- raw physics WBGT proxy residual analysis。

关键结果：

- Raw physics WBGT proxy 平均低估 official WBGT 约 1.14°C。
- Raw proxy 完全漏报 WBGT≥31 和 WBGT≥33。
- S128 Bishan 是 Toa Payoh 附近重点 station，出现 High WBGT。

---

### v0.9-beta

目标：非 ML calibration baseline。

完成内容：

- M0 raw proxy。
- M1 global bias。
- M1b period bias。
- M2 linear proxy。
- M3 regime-current ridge。
- M4 thermal-inertia ridge。
- M5 inertia + morphology ridge。
- LOSO-CV。
- day/night/peak metrics。
- threshold scan extension。

关键结果：

- M3/M4 将 LOSO overall MAE 从约 1.32°C 降到约 0.60°C。
- M4/M3 明显改善 daytime 和 peak-window MAE。
- WBGT≥31 recall 从 0 提高到约 26–28% fixed threshold。
- Threshold scan 显示 M3/M4 calibrated score 使用约 30°C decision threshold 可显著提高 WBGT≥31 detection recall。
- WBGT≥33 仍然无法可靠识别。
- M5 加 morphology 反而变差，后续解释为 station representativeness + building DSM completeness issue。

---

### v0.9-gamma

目标：SOLWEIG selected-tile Tmrt physical experiment。

完成内容：

- Overhead-aware tile selection。
- 6 tiles：clean hazard, conservative risk, social risk, open paved hotspot, clean shaded reference, overhead-confounded diagnostic。
- UMEP/SOLWEIG 5 time points：10, 12, 13, 15, 16 SGT。
- S128 May 7 forcing。
- SOLWEIG Tmrt vs empirical globe-term proxy comparison。

关键原始结果：

- T01 clean hazard vs T05 shaded reference 13:00 focus-cell Tmrt contrast = 26.2°C under current DSM。
- T01 SOLWEIG-minus-empirical-proxy delta 在 13:00 和 15:00 都很高，支持 afternoon radiant-load persistence hypothesis。
- T06 overhead comparison 后来被撤下，因为 T06 也是 building DSM source-data gap。

---

### v0.9 DSM gap audit

这是当前项目最重要的发现。

完成内容：

- 用 OSM building footprint 对比 HDB3D + URA-derived building DSM。
- 6 个 SOLWEIG tile buffer aggregate completeness = 25.8% relative to OSM-mapped building area。
- T01 completeness 7.8%。
- T06 completeness 0%。
- T06 DSM source region 确认没有 building pixels，不是 clipping bug。
- 高 hazard tiles 往往 completeness 更低。

核心解释：

> v0.7–v0.9 的 hazard ranking 可能系统性偏向 DSM coverage gap regions。模型把 source-data gap 当成真实 open space，从而产生 false high-hazard signals。

因此 v0.9 被 freeze，v1.0 进入 augmented DSM development。

---

## 2. 当前必须遵守的解释边界

### 可以说

- OpenHeat v0.9 建立了 calibration + SOLWEIG + audit workflow。
- v0.9 证明 raw WBGT proxy 需要校准。
- v0.9 证明 current DSM 下 SOLWEIG 能揭示强烈 radiant heterogeneity。
- v0.9 building DSM audit 揭示了 upstream morphology data integrity 是主要不确定性来源。
- v1.0 需要 augmented multi-source building DSM。

### 不要说

- v0.9 已经给出了最终真实 heat-hazard ranking。
- T01–T05 26.2°C 是真实精确 vegetation cooling magnitude。
- T01–T06 2.6°C 证明 overhead infrastructure bias。
- HDB3D+URA 是完整建筑地面真值。
- 当前 v0.8/v0.9 risk map 可直接 operational deployment。

---

## 3. 文件结构现状

当前项目仍然使用：

```text
06-openheat_grid/
```

不要另开新项目。v1.0 使用 namespace：

```text
configs/v10/
data/raw/buildings_v10/
data/features_3d/v10/
data/rasters/v10/
data/grid/v10/
outputs/v10_dsm_audit/
outputs/v10_morphology/
outputs/v10_ranking_audit/
outputs/v10_solweig/
docs/v10/
src/openheat_v10/
```

当前 `directory_structure.md` 显示 v10 namespace 已经存在，包括 `configs/v10/`、`data/features_3d/v10/`、`data/grid/v10/`、`data/rasters/v10/`、`outputs/v10_*` 和 `src/openheat_v10/`。这说明已经可以在当前 repo 中继续 v1.0，而不需要另开项目。

---

## 4. 最重要的冻结文件

新对话/新 AI 必须读这些：

```text
docs/v09_freeze/V09_FREEZE_NOTE_CN.md
docs/v09_freeze/V09_REVISED_FINDINGS_CN.md
docs/v09_freeze/32_V09_COMPLETE_WORK_RECORD_CN.md
docs/v09_freeze/33_V09_BUILDING_DSM_GAP_AUDIT_CN.md
docs/v10/V10_PROJECT_STRUCTURE_CN.md
```

如果只能上传 3 个：

```text
docs/v09_freeze/V09_FREEZE_NOTE_CN.md
docs/v09_freeze/V09_REVISED_FINDINGS_CN.md
docs/v09_freeze/33_V09_BUILDING_DSM_GAP_AUDIT_CN.md
```

如果要让 AI 写代码，还要上传：

```text
directory_structure.md
scripts/v09_gamma_check_building_completeness.py
scripts/v09_gamma_check_overhead_structures.py
scripts/v08_merge_buildings_with_height.py
scripts/v08_rasterize_building_dsm.py
```

---

## 5. v1.0 开发目标

v1.0 不是 ML、dashboard 或全岛扩展。

v1.0 的核心是：

> augmented multi-source building DSM + morphology rerun + rank-shift audit。

目标：

1. 解决 HDB3D+URA building DSM completeness gap。
2. 用多源 footprint 重建 canonical building layer。
3. 重新赋 height。
4. 重新 rasterize 2m building DSM。
5. 重新计算 building density / height stats / morphology features。
6. 重新跑 hazard ranking。
7. 比较 v0.9 current-DSM rank 和 v1.0 augmented-DSM rank。
8. 识别 DSM-gap false positives。

---

## 6. v1.0 Phase 1 推荐计划

### Phase 1A：OSM augmented DSM pilot

先不要一次性加 Microsoft / Google / OneMap。

第一步只做：

```text
HDB3D + URA + OSM
```

原因：OSM 已经在 audit 中暴露了大量 gap，是最直接的补充源。

输出：

```text
data/features_3d/v10/source_standardized/osm_standardized.geojson
data/features_3d/v10/canonical/canonical_buildings_v10.geojson
data/features_3d/v10/height_imputed/canonical_buildings_v10_height.geojson
data/rasters/v10/dsm_buildings_2m_augmented.tif
outputs/v10_dsm_audit/v10_completeness_gain_report.md
```

### Phase 1B：rank-shift audit

输出：

```text
outputs/v10_ranking_audit/v10_hazard_rank_shift.csv
outputs/v10_ranking_audit/v10_rank_shift_summary.md
outputs/v10_ranking_audit/v10_old_false_positive_candidates.csv
```

重点问题：

```text
旧 top20 是否大量跌出？
旧 high hazard cells 是否因为 building data gap 被推高？
新 top20 是否在 satellite/OSM 上更合理？
T01/T06 类型 source gap 是否被修复？
```

### Phase 1C：limited SOLWEIG sensitivity

只选 2–3 个 tile，不要全跑：

```text
old T01
old T05
old T06
possibly new clean hazard tile
```

目标：

```text
current DSM vs augmented DSM Tmrt difference
```

---

## 7. 需要新增/准备的 v1.0 scripts

建议脚本顺序：

```text
scripts/v10_download_osm_buildings.py
scripts/v10_standardize_building_sources.py
scripts/v10_deduplicate_building_footprints.py
scripts/v10_assign_building_heights.py
scripts/v10_rasterize_augmented_dsm.py
scripts/v10_building_completeness_audit.py
scripts/v10_recompute_morphology_features.py
scripts/v10_rerun_hazard_ranking.py
scripts/v10_rank_shift_audit.py
```

建议 `src/openheat_v10/` 模块：

```text
src/openheat_v10/buildings.py
src/openheat_v10/dedup.py
src/openheat_v10/height_imputation.py
src/openheat_v10/rasterize.py
src/openheat_v10/qa.py
```

---

## 8. v1.0 建筑源处理原则

### Source priority

建议 priority：

```text
1. HDB3D
2. URA
3. OSM
4. Microsoft Global ML Building Footprints
5. Google Open Buildings
6. OneMap optional
```

但不要简单按 priority 覆盖。需要保留 provenance。

### Canonical schema

每栋 canonical building 应有：

```text
building_id
geometry
canonical_source
source_candidates
height_m
height_source
height_confidence
footprint_confidence
building_type_proxy
land_use_desc
area_m2
qa_flag
```

### Height hierarchy

建议：

```text
1. HDB3D height
2. OSM height tag
3. OSM building:levels × 3m
4. HDB floor proxy if available
5. land-use / building-type default
6. KNN within same land-use / area group
7. fallback by area class
```

不要统一 fallback 5m。小棚 3–5m 可以，普通 unknown building 建议 10–12m。

---

## 9. v1.0 不应马上做的事情

暂缓：

```text
full Singapore expansion
public alert API
full frontend deployment
ML residual learning on current 24h archive
national-scale SOLWEIG
full Microsoft/Google/OneMap integration before OSM pilot
```

原因：geometry ground truth 还未修好。

---

## 10. 新对话启动提示模板

在新 ChatGPT 对话里可以这样开场：

```text
我正在继续 OpenHeat-ToaPayoh 项目。当前项目根目录是 06-openheat_grid。
请先阅读我上传的以下文件：
1. OPENHEAT_HANDOFF_CN.md
2. V09_FREEZE_NOTE_CN.md
3. V09_REVISED_FINDINGS_CN.md
4. 33_V09_BUILDING_DSM_GAP_AUDIT_CN.md
5. directory_structure.md

项目当前状态：v0.9 已经 freeze。v0.9 发现 HDB3D+URA building DSM 相对 OSM-mapped building area completeness 只有 25.8%，并且 hazard ranking 可能系统性偏向 DSM coverage gap regions。因此我现在进入 v1.0，目标是构建 augmented multi-source building DSM，先做 HDB3D+URA+OSM pilot，然后重跑 morphology 和 hazard ranking，做 rank-shift audit。

请不要继续基于旧 v0.8/v0.9 hazard_rank 当最终结果；它只能作为 current-DSM baseline。下一步请帮助我做 v10 augmented DSM pipeline。
```

---

## 11. 当前最推荐下一步

从这里开始：

```text
v10-alpha Step 1:
下载 / 提取 OSM building polygons for Toa Payoh AOI + 200m buffer。

v10-alpha Step 2:
标准化 HDB3D / URA / OSM building sources。

v10-alpha Step 3:
Deduplicate to canonical_buildings_v10.geojson。

v10-alpha Step 4:
Height imputation + rasterize augmented DSM。

v10-alpha Step 5:
Completeness gain audit and rank-shift audit。
```

---

## 12. Bottom line

OpenHeat-ToaPayoh 当前最重要的科学转折是：

> v0.9 不只是一个 heat-stress forecast prototype；它通过 SOLWEIG 和 building DSM audit 暴露了 open-data urban morphology completeness 对 heat-hazard ranking 的系统性影响。

v1.0 的目标就是修复这个 morphology foundation。
