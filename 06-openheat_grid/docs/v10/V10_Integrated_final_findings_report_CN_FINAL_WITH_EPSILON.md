# OpenHeat-ToaPayoh v10 Integrated Final Findings Report — FINAL WITH EPSILON

> **Version:** v10-final integrated report  
> **Scope:** v0.9 audit freeze → v10 augmented DSM → reviewed-DSM UMEP rerun → overhead sensitivity → selected-cell SOLWEIG validation → v11 archive / ML handoff  
> **Status:** final integrated findings report for v10 sprint  
> **Language:** Chinese  
> **Intended use:** dissertation results chapter / portfolio case study / project handoff / v11 planning  
> **Companion reports:**  
> - `OpenHeat_v10_gamma_final_findings_report_CN_REVISED.md`  
> - `OpenHeat_v10_delta_final_findings_report_CN_REVISED_v2.md`  
> - `OpenHeat_v10_epsilon_SOLWEIG_final_findings_report_CN.md`  
> - `v10_gamma_robustness_audit_report.md`  
> - `v10_base_vs_overhead_sensitivity_comparison.md`  
> - `v10_epsilon_base_vs_overhead_tmrt_comparison.csv`

---

## 0. Executive summary

OpenHeat v10 的核心成果不是“又生成一个 heat-hazard ranking”，而是完成了一条完整的 **audit → correct → validate** 方法链：

```text
v0.9 audit:
    发现 HDB3D + URA building DSM completeness gap
    不再把旧 hazard ranking 视为 ground truth

v10-alpha / alpha.3:
    构建 OSM-first + manual QA reviewed building DSM
    合并真实 conflict buildings，补充 missing buildings，移除 station canopy / overhead candidate

v10-beta / beta.1:
    重算 building-only morphology
    修正高度/几何异常
    识别旧 ranking 中 DSM-gap false-positive candidates

v10-gamma:
    用 reviewed height-QA DSM 重跑 UMEP SVF / shadow
    生成 reviewed-DSM base hazard ranking
    与 v08 ranking 做 controlled comparison

v10-gamma robustness:
    修正 TP_0315 分类歧义
    透明化 false-positive candidate 定义
    增加 FP vs non-FP baseline
    确认 dense built-up edge case 不是系统性问题

v10-delta:
    构建独立 overhead infrastructure layer
    做 overhead-shade sensitivity
    识别 overhead-confounded hotspots

v10-epsilon:
    用 selected-cell SOLWEIG 物理验证 v10-delta 的方向
    确认 TP_0565 / TP_0986 是目前最可信的 pedestrian heat hotspot anchors
```

v10 最终结论可以概括为：

> **OpenHeat v10 证明，基于开放数据的 fine-scale urban heat-hazard ranking 必须同时处理两类系统性数据问题：building DSM incompleteness 和 overhead infrastructure mis-attribution。** 只修 building DSM 不够；只看 overhead sensitivity 也不够。v10 的贡献在于把这两层问题依次审计、修正、量化，并用 SOLWEIG selected-cell 物理建模验证关键解释。

最终不建议把 OpenHeat v10 呈现为单一 hazard score，而应呈现为三张互补地图：

```text
Map A: v10-gamma reviewed-DSM base hazard map
Map B: v10-delta overhead-sensitivity map
Map C: confident / caveated hotspot interpretation map
```

其中，最稳的 confident pedestrian-relevant hotspot anchors 是：

```text
TP_0565
TP_0986
```

它们经过 building DSM correction、overhead sensitivity、selected-cell SOLWEIG validation 后仍保持 high Tmrt。v10-epsilon 中，TP_0565 和 TP_0986 在 13:00 的 SOLWEIG mean ground Tmrt 分别约为 **60.06°C** 和 **60.67°C**，而 shaded reference TP_0433 约为 **36.09°C**。这说明 corrected geometry 下，confident hotspot 与 natural canopy reference 之间仍存在约 **24°C** 的 Tmrt contrast。

同时，v10-gamma rank-1 cell TP_0088 在 v10-delta 中被识别为 transport-deck / viaduct-confounded，并在 v10-epsilon overhead-as-canopy SOLWEIG 中显示 13:00 Tmrt 从 **61.74°C** 降到 **44.98°C**，支持其从 ordinary pedestrian hotspot 解读中降级。

---

## 1. Why v10 was necessary

v0.9 后期的 building DSM completeness audit 证明，旧 HDB3D + URA DSM 在 selected SOLWEIG tile buffers 中相对 OSM-mapped building area 的 completeness 很低，且旧 hazard ranking 中的高排名 cell 可能被 DSM coverage gaps 人工推高。旧模型把“数据中没有建筑”错误解释为“真实开阔、高 SVF、低 shade、高热暴露”。

因此，v10 的目标不是增加模型复杂度，而是重建 morphology ground truth：

```text
1. 修复 building footprint completeness；
2. 修正高度与几何异常；
3. 用 reviewed DSM 重跑 SVF / shadow；
4. 审计旧 ranking 中的 DSM-gap false positives；
5. 继续识别 reviewed-DSM 后暴露出来的 overhead infrastructure confounding；
6. 用 SOLWEIG 对关键 cells 做物理验证。
```

这条路线与早期 roadmap 一致：先 freeze v0.9 audit，再做 augmented DSM，再重跑 morphology / ranking，再做 selected-tile SOLWEIG，最后才进入 archive / ML / dashboard 阶段。

---

## 2. v10-alpha / alpha.3 — reviewed augmented building DSM

### 2.1 目标

v10-alpha 的目标是构建一个可复现、有 provenance 的 augmented building DSM：

```text
HDB3D + URA + OSM + manual missing buildings
→ dedup
→ height imputation
→ manual QA
→ height/geometry correction
→ reviewed height-QA DSM
```

### 2.2 主要处理

v10-alpha.3 进行了人工 QA application：

```text
Reviewed canonical buildings: 5313
Overhead candidates: 1
Applied decisions: 89
Manual missing buildings appended: 68
Conflict candidates merged: 20
```

其中 `v10_bldg_000690` 被确认为 station canopy / overhead，而不是 ground-up building，因此从 building DSM 中移出，进入 overhead candidates。此决定避免把 overhead canopy 错当成实心建筑。

### 2.3 reviewed DSM completeness

v10-alpha.3 reviewed DSM 相对 OSM-mapped building footprint area 的 completeness 显著提升：

```text
Per-cell:
    old vs OSM completeness       = 0.388
    reviewed vs OSM completeness  = 1.104

Six critical SOLWEIG tile buffers:
    old vs OSM completeness       = 0.263
    reviewed vs OSM completeness  = 1.069
```

critical tile recovery：

```text
T01 clean hazard:          0.085 → 0.981
T02 conservative risk:     0.134 → 1.145
T03 social risk:           0.664 → 1.139
T04 open paved hotspot:    0.397 → 1.135
T05 shaded reference:      0.169 → 1.037
T06 overhead-confounded:   0.000 → 0.999
```

这些结果证明：v0.9 中发现的 building DSM gap 是真实 source coverage issue，并且可以通过 OSM-first augmentation + manual QA 大幅修复。

---

## 3. v10-beta / beta.1 — building morphology shift audit

### 3.1 basic morphology recomputation

v10-beta 使用 reviewed height-QA DSM 重算 building-only morphology，并与旧 v08/current DSM 比较。结果显示，986 个 grid cells 中：

```text
old_building_density mean = 0.0746
v10_building_density mean = 0.2148
mean delta                 = +0.1402

old_open_pixel_fraction mean = 0.9254
v10_open_pixel_fraction mean = 0.7852
mean delta                   = -0.1402
```

也就是说，v10 reviewed DSM 系统性提高了 building density，并降低了 open-pixel fraction。

### 3.2 old DSM-gap false-positive candidates

v10-beta morphology shift audit 识别出：

```text
Possible old DSM-gap false-positive candidates: 34
```

这些 cells 通常满足：

```text
old hazard rank 高；
old_vs_osm_completeness 为 0 或很低；
v10 coverage gain 高；
v10 building density 明显上升。
```

典型旧 top hazard cells 包括：

```text
TP_0116: old rank 2,  old density 0 → v10 density 0.1756
TP_0564: old rank 7,  old density 0 → v10 density 0.3248
TP_0849: old rank 8,  old density 0 → v10 density 0.2696
TP_0985: old rank 9,  old density 0 → v10 density 0.4248
TP_0986: old rank 10, old density 0 → v10 density 0.4276
TP_0984: old rank 12, old density 0 → v10 density 0.4048
TP_0027: old rank 15, old density 0 → v10 density 0.4104
TP_0820: old rank 19, old density 0 → v10 density 0.4348
```

这支持 v0.9 audit 的核心判断：旧 v08/v09 hazard ranking 中确实存在由 building DSM gap 造成的 artificial open-space signal。

### 3.3 beta.1 height / geometry correction

在进入 v10-gamma 之前，项目又修正了两个高度/几何异常：

```text
v10_bldg_000001:
    原高度约 85m，但 Google Street View / 相邻 71m building 对比显示不合理；
    手动修正为 30m。

v10_bldg_000002:
    原始 block-complex polygon 将两栋高塔 + 低层底座统一赋为 93.7m；
    手动拆分为 tower / podium polygons，并分别赋高。
```

修正后生成：

```text
canonical_buildings_v10_height_reviewed_heightqa.geojson
dsm_buildings_2m_augmented_reviewed_heightqa.tif
```

后续 v10-gamma / delta / epsilon 均基于 height-QA DSM。

---

## 4. v10-gamma — reviewed DSM UMEP morphology rerun and hazard ranking

### 4.1 UMEP morphology rerun

v10-gamma 使用 reviewed height-QA building DSM + v08 vegetation DSM 重跑 UMEP SVF / shadow。shadow hours 被正确解析为：

```text
08:00, 09:00, 10:00, 11:00, 12:00, 13:00, 14:00, 15:00, 16:00, 17:00, 18:00, 19:00
```

v10 UMEP morphology 结果健康，986 cells 覆盖完整。与 v08 比较：

```text
SVF mean:
    v08 = 0.491
    v10 = 0.380
    delta = -0.110

shade_fraction mean:
    v08 = 0.423
    v10 = 0.466
    delta = +0.043

building_density mean:
    v08 = 0.066
    v10 = 0.215
```

方向符合预期：building completeness 修复后，open-pixel SVF 降低，shade fraction 上升，building density 增加。

### 4.2 hazard ranking comparison

v10-gamma 与 v08 hazard ranking 比较：

```text
Spearman rank correlation = 0.9705
Top20 overlap             = 10 / 20
```

这说明：

```text
全局 heat-hazard geography 仍然稳定；
但 high-priority top20 intervention set 发生实质重排。
```

v08 top20 中有 12 个 DSM-gap false-positive candidates，其中 9 个在 v10-gamma 后离开 top20。这个结果支持 building DSM correction 对旧 false hotspots 的修正。

### 4.3 robustness audit

v10-gamma robustness audit 修正了几个关键方法学问题：

1. **TP_0315 分类修正**  
   TP_0315 的 v08 rank = 22、v10 rank = 14，不应被描述为 old-top20 retained false positive，而应分类为 `entering_v10_top_fp_candidate`。

2. **false-positive candidate 定义透明化**  
   v10-beta candidate flag 使用了 v10 reviewed DSM 的 coverage gain / building-density gain，因此应被称为 **co-derived diagnostic signal**，不是完全独立验证目标。

3. **FP vs non-FP baseline**  
   在 old top20 中：

```text
co-derived DSM-gap candidates:
    9 / 12 left top20 = 75.0%

non-candidates:
    1 / 8 left top20 = 12.5%

Fisher exact p ≈ 0.0198
```

独立定义下也有类似结果：old rank ≤ 50 且 old-vs-OSM completeness ≤ 0.1 的 candidates 中，10/15 离开 top20，而 non-candidates 0/5 离开 top20。

4. **dense-cell edge case**  
   TP_0945 是 fully / near-fully built edge case，不应作为 ordinary open-pedestrian hazard cell 解读。

因此，v10-gamma 最稳的表述是：

> v10-gamma 并不是独立证明每一个 diagnosed candidate 都是 false positive；更准确地说，被诊断为 old DSM-gap candidates 的 cells 在 reviewed-DSM morphology correction 后发生了不成比例的排名下降。

---

## 5. v10-delta — overhead infrastructure sensitivity

### 5.1 为什么需要 v10-delta

v10-gamma 修复 building DSM gap 后，又暴露出第二类系统性误差：**overhead infrastructure mis-attribution**。高架道路、高架轨道、人行天桥、covered walkway 和 station canopy 不是普通 building，也不是普通 open space。它们是 two-layer infrastructure：

```text
桥面 / 高架道路：可能很热，但通常不是普通行人暴露面；
桥下 / 连廊下：可能显著遮阴，地面行人 Tmrt 可能较低。
```

v10-delta 不把 overhead 烧进 building DSM，而是构建独立 overhead layer，并做 ground-level overhead-shade sensitivity。

### 5.2 overhead layer QA

v10-delta 构建了：

```text
canonical overhead features: 952
total overhead footprint area: 672,186.3 m²
input candidates: 1769
dedup dropped: 817
multi-source canonical features: 789
```

类型分布：

```text
covered_walkway       538
elevated_rail         166
elevated_road         127
pedestrian_bridge      83
viaduct                38
```

这说明 overhead layer 不是单点人工判断，而是由大量 OSM-derived features + dedup provenance 支撑。

### 5.3 overhead sensitivity ranking

v10 base vs overhead-shade sensitivity：

```text
Spearman rank correlation = 0.9327
Top20 overlap             = 8 / 20
```

这说明 top hazard set 对 overhead handling 高度敏感。

离开 v10-gamma base top20 的 cells 包括：

```text
TP_0088, TP_0089, TP_0315, TP_0344, TP_0373, TP_0460,
TP_0564, TP_0572, TP_0575, TP_0888, TP_0916, TP_0973
```

其中多数为 `major_confounding`，并且以 `transport_deck_or_viaduct` 或 `mixed_pedestrian_and_transport_overhead` 为主。

最典型 case：

```text
TP_0088:
    v10-gamma base hazard rank = 1
    overhead sensitivity rank  = 224
    overhead_fraction_total    = 0.732
    interpretation             = transport_deck_or_viaduct
```

这意味着 TP_0088 不应作为 ordinary pedestrian open-space hotspot 解读。

### 5.4 v10-delta 的限制

v10-delta 是 algebraic shade sensitivity，不是完整 physical model。它没有模拟：

```text
高架桥面热储存；
桥下通风；
长波辐射；
交通排热；
overhead 高度和太阳角的精确投影。
```

因此它应被解释为：

```text
overhead-confounding diagnostic / sensitivity layer
```

而不是最终 overhead-aware physical Tmrt model。

---

## 6. v10-epsilon — selected-cell SOLWEIG physical validation

### 6.1 目标

v10-epsilon 是 v10 sprint 的物理验证收尾。它用 SOLWEIG v2025a 对 5 个 selected cells 做 base vs overhead-as-canopy comparison：

```text
5 selected cells × 2 scenarios × 5 hours = 50 SOLWEIG Tmrt outputs
```

两个 scenarios：

```text
base:
    reviewed height-QA building DSM + vegetation DSM

overhead:
    reviewed height-QA building DSM + max(vegetation DSM, overhead canopy DSM)
```

v10-epsilon 不是 full AOI SOLWEIG，也不是完整 overhead physical model，而是 selected-cell physical validation。

### 6.2 selected cells

```text
TP_0565: confident hot anchor 1
TP_0986: confident hot anchor 2 / perfect null control
TP_0088: v10-gamma rank-1 overhead-confounded case
TP_0916: saturated overhead case
TP_0433: natural canopy / shaded reference
```

由于 SOLWEIG 使用 700m × 700m tile，而 v10-delta overhead metrics 是 100m cell-level 指标，因此 v10-epsilon 采用 scope-aware interpretation：

```text
focus cell overhead-free ≠ tile-context overhead-free
```

例如 TP_0565 的 focus cell overhead = 0，但 700m tile 中有 84 个 overhead features；TP_0986 则是真正的 focus-clean + tile-clean null control。

### 6.3 sanity checks

v10-epsilon 三个 sanity checks 全部通过：

```text
TP_0433 base @ 13:00 = 36.09°C (<40°C)
TP_0986 base vs overhead delta = 0.000°C exactly, all 5 hours
TP_0916 base vs overhead delta mean = -18.39°C, peak = -22.46°C
```

### 6.4 confident hot anchors

TP_0565 / TP_0986 的 base Tmrt 非常接近：

```text
TP_0565 base @ 13:00 = 60.06°C
TP_0986 base @ 13:00 = 60.67°C
```

TP_0565 虽然 tile context 有 84 个 overhead features，但 overhead scenario 后 Tmrt delta 只有约 -0.01°C；TP_0986 则在 5 个小时中 base 与 overhead 完全一致。

这说明：

```text
TP_0565 和 TP_0986 是目前最可信的 pedestrian-relevant heat hotspot anchors。
```

### 6.5 overhead-confounded physical validation

TP_0088：

```text
base @ 13:00      = 61.74°C
overhead @ 13:00  = 44.98°C
delta             = -16.76°C
mean delta         = -14.16°C
```

TP_0916：

```text
base @ 13:00      = 61.15°C
overhead @ 13:00  = 39.00°C
delta             = -22.15°C
mean delta         = -18.39°C
```

这物理支持 v10-delta 的方向判断：overhead-confounded cells 不应被当作 ordinary open-pedestrian hotspots。

### 6.6 corrected hot-vs-shaded contrast

At 13:00：

```text
TP_0565 = 60.06°C
TP_0986 = 60.67°C
TP_0433 = 36.09°C
```

因此 confident hot anchors 比 natural canopy reference 高约：

```text
≈ 24°C Tmrt
```

这非常重要：v0.9 中类似的 Tmrt contrast 因 building DSM gap 被降级解释；v10-epsilon 证明，在 reviewed DSM + overhead validation 后，这种 hot-vs-shaded contrast 仍然真实存在。

### 6.7 v10-epsilon 的限制

v10-epsilon 仍然不是最终 operational model：

```text
只跑 5 cells；
只跑 May 7 一天；
overhead-as-canopy 是 approximation；
没有模型化桥面热储存、交通热、通风或多日气象不确定性；
仅输出 Tmrt，不直接输出 PET / UTCI / WBGT。
```

但它足以作为 selected-cell physical validation。

---

## 7. Final hotspot interpretation framework

OpenHeat v10 的最终成果不应是一张单一排名图，而应是一套 evidence-weighted interpretation。

### 7.1 Confident pedestrian heat hotspots

定义：

```text
v10-gamma high hazard;
v10-delta 不被 overhead 显著降级；
v10-epsilon selected-cell validation 支持高 Tmrt（如被选中）。
```

当前最可信 anchors：

```text
TP_0565
TP_0986
```

它们在 v10-epsilon 中 13:00 mean Tmrt 约 60°C，是 Toa Payoh 当前最有物理证据的 confident pedestrian heat hotspot candidates。

### 7.2 Overhead-confounded hotspots

定义：

```text
v10-gamma 高 hazard；
v10-delta overhead sensitivity 下大幅下降；
v10-epsilon 如被选中则显示 large Tmrt reduction。
```

典型：

```text
TP_0088
TP_0916
TP_0973
TP_0888
TP_0575
```

这些不是“不热”，而是不能作为 ordinary ground-level pedestrian open-space hotspot 简单解释。

### 7.3 Building-DSM-gap corrected false positives

定义：

```text
v08 high hazard；
old DSM completeness low / zero；
v10 reviewed DSM 后 building density 显著上升；
v10-gamma ranking 下降。
```

这些 cells 是 v0.9 audit → v10 correction 的核心证据。

### 7.4 Dense built-up edge cases

典型：

```text
TP_0945
```

在 v10 reviewed DSM 下 fully / near-fully built，open-pixel SVF 缺失或 hazard_score 退化为 0。它应被视为 dense built-up edge case，而不是 ordinary pedestrian hotspot。

### 7.5 Natural canopy reference

典型：

```text
TP_0433
```

在 SOLWEIG 中 13:00 mean Tmrt 约 36°C，作为 natural canopy / shaded reference。

---

## 8. Final map package recommendation

建议 v10-final 输出三张互补地图：

### Map A — v10-gamma reviewed-DSM base hazard

用途：展示 reviewed building DSM + vegetation DSM 后的 base physical hazard。

### Map B — v10-delta overhead sensitivity

用途：展示如果 overhead 被视为 ground-level shade，ranking 如何变化；识别 overhead-confounded cells。

### Map C — confident / caveated hotspot interpretation map

字段建议：

```text
cell_id
v10_gamma_hazard_rank
v10_delta_hazard_rank
hazard_transition_class
overhead_confounding_flag
overhead_interpretation
old_dsm_gap_candidate_flag
solweig_validation_class
final_interpretation_class
final_interpretation_note
```

`final_interpretation_class` 可取：

```text
confident_pedestrian_hotspot
overhead_confounded_hotspot
building_dsm_gap_corrected_false_positive
dense_built_edge_case
natural_canopy_reference
uncertain_needs_review
```

---

## 9. Limitations

### 9.1 v10-gamma limitations

```text
v10-gamma 是 reviewed building DSM + vegetation DSM 的 UMEP morphology rerun；
尚未包含 overhead infrastructure；
仍依赖单日/固定日期的 shadow configuration；
ranking 是 model output，不是 observed health outcome。
```

### 9.2 v10-delta limitations

```text
v10-delta 是 algebraic shade sensitivity，不是 full physical overhead model；
会发生 shade saturation；
transport-deck heat 本身未被建模；
SVF 未随 overhead 重新计算；
不处理通风、桥面热储存、交通热排放。
```

### 9.3 v10-epsilon limitations

```text
selected 5 cells；
单日 forcing；
overhead-as-canopy approximation；
没有 full AOI Tmrt map；
没有多日期 uncertainty；
没有 PET / UTCI。
```

### 9.4 General limitation

OpenHeat v10 是一个 open-data heat-risk modelling workflow。它能够识别并修正重要数据偏差，但不能替代实地传感器网络、公共卫生 outcome validation 或 operational warning system。

---

## 10. Recommended next development path

### 10.1 Freeze v10-final

建议创建：

```text
docs/v10_final/
outputs/v10_final/
```

保存：

```text
OpenHeat_v10_integrated_final_findings_report_CN_FINAL_WITH_EPSILON.md
OpenHeat_v10_gamma_final_findings_report_CN_REVISED.md
OpenHeat_v10_delta_final_findings_report_CN_REVISED_v2.md
OpenHeat_v10_epsilon_SOLWEIG_final_findings_report_CN.md
v10_final_hotspot_interpretation_map.geojson
v10_final_hotspot_interpretation_table.csv
```

然后：

```bat
git add docs\v10_final outputs\v10_final
git commit -m "Finalize OpenHeat v10 audit-correct-validate sprint"
git tag v10-final-audit-correct-validate
```

### 10.2 v11-alpha — archive QA

后台 archive 的主要作用是把 OpenHeat 从 spatial hazard modelling system 推进到 calibrated forecast system。下一阶段应先做 archive QA：

```text
有多少天？
有多少 station？
WBGT≥31 / ≥33 event 数量多少？
missingness 如何？
是否足够做 LOSO-CV？
```

输出：

```text
data/calibration/v11_station_weather_pairs.csv
outputs/v11_archive_QA_report.md
outputs/v11_event_count_report.md
```

### 10.3 v11-beta — calibration baselines

先重建 non-ML baseline：

```text
M0 raw WBGT proxy
M1 global bias correction
M2 linear calibration
M3 weather-regime ridge
M4 lagged-radiation / thermal-inertia ridge
M5_v10 morphology-aware ridge
M6_v10 overhead-aware ridge
```

验证方式：

```text
leave-one-station-out CV
blocked temporal CV
peak-window metrics
threshold scan
```

### 10.4 v11-gamma — ML residual learning

ML 最合理的位置不是替代 physics，而是学习 residual：

```text
target = official_WBGT - calibrated_physics_proxy
```

推荐模型：

```text
Ridge / ElasticNet residual
LightGBM / XGBoost residual
Quantile GBM
Conformal prediction wrapper
```

不建议现在上 LSTM / Transformer / GNN，因为 NEA station 数量有限，时间序列强自相关，容易 overfit。

### 10.5 v11-delta — uncertainty and event probability

输出：

```text
WBGT_P10 / P50 / P90
P(WBGT ≥ 31)
P(WBGT ≥ 33)
```

这是向 operational warning system 过渡的关键一步。

---

## 11. Dissertation / portfolio core wording

### 11.1 English summary

> OpenHeat v10 developed an audit-correct-validate workflow for fine-scale urban heat-hazard modelling under open-data constraints. A v0.9 audit showed that incomplete HDB3D+URA building DSMs can create artificial open-space hotspots. v10 corrected this using an OSM-first reviewed building DSM, reran UMEP SVF/shadow, and demonstrated that old DSM-gap candidates were disproportionately corrected downward. A second audit layer then showed that overhead infrastructure produces a separate ranking confounder: v10-delta overhead sensitivity reorganised the top-20 hazard set, and v10-epsilon selected-cell SOLWEIG validation physically confirmed both the stable hot anchors (TP_0565, TP_0986) and overhead-confounded cases (TP_0088, TP_0916). The resulting v10 framework does not claim a single definitive hazard ranking; instead, it provides a corrected base hazard map, an overhead sensitivity map, and an evidence-weighted confident/caveated hotspot interpretation.

### 11.2 中文 summary

> OpenHeat v10 建立了一套面向开放数据约束下 fine-scale urban heat-hazard modelling 的 audit-correct-validate 工作流。v0.9 audit 发现不完整的 HDB3D+URA building DSM 会制造人工开阔地热点；v10 使用 OSM-first reviewed building DSM 进行修正，重跑 UMEP SVF/shadow，并证明旧 DSM-gap candidates 在 reviewed-DSM morphology correction 后发生不成比例的排名下降。随后第二层审计发现 overhead infrastructure 是另一类 ranking confounder：v10-delta overhead sensitivity 显著重组 top20 hazard set，而 v10-epsilon selected-cell SOLWEIG validation 物理确认了 stable hot anchors（TP_0565, TP_0986）和 overhead-confounded cases（TP_0088, TP_0916）。因此，v10 不应只给出单一最终 ranking，而应同时呈现 corrected base hazard map、overhead sensitivity map，以及 evidence-weighted confident/caveated hotspot interpretation。

---

## 12. Final status

```text
v10-final status: COMPLETE
```

OpenHeat v10 应被视为：

```text
- reviewed-DSM corrected building morphology model
- overhead-infrastructure sensitivity model
- selected-cell SOLWEIG physical validation
- dissertation-grade audit-correct-validate workflow
```

但还不是：

```text
- full overhead-aware AOI-wide physical model
- calibrated operational WBGT forecast system
- probabilistic heat-warning model
- dashboard / API product
```

最终判断：

> **v10 sprint 已完成。** 下一条主线应该是 v11：利用后台 archive 做 station-level calibration、physics-informed ML residual learning 和 uncertainty quantification。

---

## Appendix A. Key quantitative evidence

| Module | Key evidence | Interpretation |
|---|---:|---|
| v10-alpha.3 | Six critical tile completeness 0.263 → 1.069 | Building DSM gap repaired |
| v10-beta | 34 old DSM-gap false-positive candidates | old ranking had morphology-data artifacts |
| v10-gamma | Spearman 0.9705, Top20 overlap 10/20 | global geography stable, top set corrected |
| v10-gamma robustness | FP leave rate 9/12 vs non-FP 1/8 | diagnosed DSM-gap candidates disproportionately corrected |
| v10-delta | Spearman 0.9327, Top20 overlap 8/20 | overhead sensitivity strongly affects top set |
| v10-epsilon | TP_0565 / TP_0986 ≈ 60°C at 13:00 | confident hot anchors |
| v10-epsilon | TP_0088 overhead delta -16.76°C at 13:00 | overhead-confounded rank-1 case physically validated |
| v10-epsilon | TP_0916 peak delta -22.46°C | algebraic saturation direction validated |
| v10-epsilon | TP_0433 ≈ 36°C at 13:00 | shaded reference / natural canopy cooling |

---

## Appendix B. Recommended v10-final file inventory

```text
docs/v10_final/
    OpenHeat_v10_integrated_final_findings_report_CN_FINAL_WITH_EPSILON.md
    OpenHeat_v10_gamma_final_findings_report_CN_REVISED.md
    OpenHeat_v10_delta_final_findings_report_CN_REVISED_v2.md
    OpenHeat_v10_epsilon_SOLWEIG_final_findings_report_CN.md

outputs/v10_final/
    v10_gamma_hotspot_ranking_with_grid_features.csv
    v10_base_vs_overhead_sensitivity_rank_comparison.csv
    v10_epsilon_base_vs_overhead_tmrt_comparison.csv
    v10_confident_caveated_hotspot_map.geojson
    v10_final_hotspot_interpretation_table.csv
```

---

## Appendix C. Relationship to the original roadmap

The original roadmap proposed:

```text
Phase 0: Freeze v0.9 audit
Phase 1: Augmented DSM pilot
Phase 2: Morphology rerun and rank audit
Phase 3: SOLWEIG rerun on selected tiles
Phase 4: UMEP automation + aniso/fcld fixes
Phase 5: Calibration/ML with archive
Phase 6: Research dashboard
```

v10 has completed Phases 0–3 and expanded Phase 3 with overhead sensitivity and selected-cell SOLWEIG physical validation. Phase 4 should now be treated as engineering hardening, while Phase 5 becomes the next scientific sprint: v11 archive / calibration / ML residual learning.

---

**End of report.**
