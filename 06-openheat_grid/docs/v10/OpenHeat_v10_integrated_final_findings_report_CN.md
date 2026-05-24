# OpenHeat-ToaPayoh v10 Integrated Final Findings Report

> Version: v10 integrated report  
> Scope: v0.9 audit freeze → v10 augmented DSM → v10 UMEP rerun → overhead sensitivity → future ML positioning  
> Status: integrated findings draft after v10-delta overhead sensitivity  
> Language: Chinese  
> Intended use: dissertation / portfolio / project handoff / next-stage planning

---

## 0. Executive summary

OpenHeat v10 的核心贡献不是单纯生成一个新的 heat-hazard 排名，而是完成了一条完整的 **data-integrity audit → morphology correction → ranking rerun → sensitivity interpretation** 工作流。

v0.9 阶段已经证明：旧 HDB3D + URA building DSM 存在严重 building-footprint completeness gap，导致旧 v08/v09 hazard ranking 中部分 top cells 可能是 source-data artifacts。v10 之后，项目依次完成：

1. **v10-alpha / alpha.3**：构建 OSM-first augmented building DSM，经过 manual QA、conflict merge、missing-building digitisation 和 height/geometry correction；
2. **v10-beta**：重算 building-only morphology，识别旧 hazard ranking 中的 DSM-gap false-positive candidates；
3. **v10-gamma**：用 reviewed height-QA DSM 重跑 UMEP SVF / shadow，生成 reviewed-DSM hazard ranking，并与 v08 排名比较；
4. **v10-gamma robustness**：修正 TP_0315 分类歧义，透明化 false-positive candidate 定义，并加入 FP vs non-FP baseline；
5. **v10-delta**：构建 overhead infrastructure layer，量化高架/连廊/车站遮罩对 ranking 的 sensitivity。

v10 的最终结论可以概括为：

> **OpenHeat 的热风险排序不仅受气象和植被影响，也强烈依赖城市三维形态数据的完整性。旧 v08/v09 ranking 中一部分 hotspots 是 building DSM coverage gap 造成的；v10 reviewed DSM 修正后，又暴露出 overhead infrastructure mis-attribution 这一新层级问题。因此，最终解释必须同时呈现 reviewed-DSM base hazard、overhead sensitivity 和 confident/caveated hotspot subset，而不能只给出单一 ranking。**

---

## 1. Why v0.9 was frozen

v0.9 已经完成了 calibration、threshold scan、selected-tile SOLWEIG 和 building DSM audit。但 building completeness audit 发现，HDB3D + URA DSM 在关键 SOLWEIG tile buffer 中相对 OSM-mapped building area 的 completeness 极低，且高 hazard tile 往往 completeness 更低。尤其 T06 在旧 DSM 中 building area 为 0，但在 OSM 中有大量建筑 footprint。

因此 v0.9 被冻结为：

```text
current-HDB3D+URA DSM experiment
```

而不是 final physical heat-hazard model。

v0.9 的保留价值是：

```text
1. calibration pipeline 可用；
2. SOLWEIG selected-tile workflow 可用；
3. v0.9 audit 揭示了 upstream morphology data integrity 是核心不确定性；
4. v10 的必要性由 v0.9 audit 直接导出。
```

v0.9 的降级或撤回点：

```text
1. T01–T05 26.2°C Tmrt contrast 只能作为 current-DSM directional finding；
2. T01–T06 overhead finding 因 T06 building DSM absence 被撤出主结果；
3. 旧 hazard_rank_v08 只能作为 current-DSM baseline，不再当作最终排序。
```

---

## 2. v10 workflow overview

v10 的完整流程如下：

```text
v10-alpha
    HDB3D + URA + OSM source standardisation
    conservative deduplication
    height imputation
    augmented DSM rasterization
    completeness audit

v10-alpha.1
    nodata=0 修复
    OSM height/levels promotion
    rasterization cleanup

v10-alpha.2
    manual QA target generation

v10-alpha.3
    manual QA application
    v10_bldg_000690 移入 overhead candidates
    Top conflict candidates merge
    manual missing buildings append
    reviewed DSM generation

v10-beta
    building-only morphology recomputation
    old-vs-new morphology shift audit
    DSM-gap false-positive candidate identification

v10-beta.1
    v10_bldg_000001 / v10_bldg_000002 height / geometry correction
    height-QA DSM generation

v10-gamma
    reviewed height-QA DSM + vegetation DSM
    UMEP SVF / shadow rerun
    forecast / hazard reranking
    v08-v10 comparison

v10-gamma robustness
    transition-class audit
    false-positive candidate definition check
    FP vs non-FP old-top20 baseline
    dense-cell sanity check

v10-delta
    overhead infrastructure canonical layer
    per-cell overhead metrics
    overhead-shade sensitivity grid
    base-vs-overhead ranking comparison
    opacity sensitivity sweep
```

---

## 3. v10-alpha / alpha.3: reviewed augmented building DSM

### 3.1 Objective

v10-alpha 的目标是构建 reviewed augmented building DSM，解决 v0.9 发现的 building footprint gap。最初的 v10-alpha 使用 HDB3D + URA + OSM。随后 alpha.3 加入 manual QA：

```text
- v10_bldg_000690 从 building DSM 移至 overhead candidates；
- Top 20 conflict candidates 合并回 canonical；
- 68 个 manual missing buildings 追加进 canonical；
- 后续又补充少量 satellite-observed missing buildings；
- v10_bldg_000001 / v10_bldg_000002 在 beta.1 做 height / geometry correction。
```

### 3.2 Key alpha.3 outputs

主要输出文件：

```text
data/features_3d/v10/height_imputed/canonical_buildings_v10_height_reviewed.geojson
data/features_3d/v10/manual_qa/overhead_candidates_v10.geojson
data/rasters/v10/dsm_buildings_2m_augmented_reviewed.tif
```

后续 height-QA 版本：

```text
data/features_3d/v10/height_imputed/canonical_buildings_v10_height_reviewed_heightqa.geojson
data/rasters/v10/dsm_buildings_2m_augmented_reviewed_heightqa.tif
```

### 3.3 Evidence

alpha.3 report 显示：

```text
Reviewed canonical buildings: 5313
Overhead candidates: 1
Applied decisions: 89
Manual missing buildings appended: 68
Conflict candidates merged: 20
```

reviewed DSM raster:

```text
Buildings rasterized: 5313
Building pixels >0.5m: 664,000
Building area: 2,656,000 m²
nodata: None
```

completeness summary:

```text
All cells:
    Old vs OSM completeness:       0.388
    Reviewed vs OSM completeness:  1.104

Six v0.9 SOLWEIG tile buffers:
    Old vs OSM completeness:       0.263
    Reviewed vs OSM completeness:  1.069
```

Critical tile recovery:

```text
T01: 0.085 → 0.981
T02: 0.134 → 1.145
T03: 0.664 → 1.139
T04: 0.397 → 1.135
T05: 0.169 → 1.037
T06: 0.000 → 0.999
```

### 3.4 Interpretation

v10-alpha / alpha.3 的意义是：

> **旧 building DSM 的 source-data gap 是真实、严重、且可修复的。**

v10-alpha 并不是要证明 OSM 是 ground truth，而是证明 HDB3D + URA 作为 building DSM foundation 不足；OSM-first augmentation + manual QA 能把 building footprint coverage 拉回到可用水平。

---

## 4. v10-beta: building-only morphology shift audit

### 4.1 Objective

v10-beta 不生成最终 hazard ranking。它只重算 building-only morphology：

```text
building_area_m2
building_density
open_pixel_fraction
mean / max / p50 / p90 building height
```

目的是检验：

> 旧 top hazard cells 是否因旧 DSM building_density = 0 被误判为开阔高热区域。

### 4.2 Evidence

v10-beta 结果：

```text
Rows: 986
Possible old DSM-gap false-positive candidates: 34
```

全 AOI building morphology shift：

```text
old_building_density mean: 0.0746
v10_building_density mean: 0.2148
delta mean: +0.1402

old_open_pixel_fraction mean: 0.9254
v10_open_pixel_fraction mean: 0.7852
```

典型旧 top hazard cells：

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

### 4.3 Interpretation

v10-beta 坐实了 v0.9 audit 的核心怀疑：

> 旧 v08/v09 ranking 中一部分 high-hazard cells 是 DSM coverage gap false-positive candidates。

但 v10-beta 仍不是最终 hazard ranking，因为 SVF / shadow 还没有用 reviewed DSM 重跑。

---

## 5. v10-gamma: reviewed DSM UMEP morphology rerun

### 5.1 Objective

v10-gamma 使用 reviewed height-QA building DSM + 原 vegetation DSM 重跑 UMEP SVF / shadow，并保持 v08 baseline 参数一致：

```text
building DSM: dsm_buildings_2m_augmented_reviewed_heightqa.tif
vegetation DSM: dsm_vegetation_2m_toapayoh.tif
date / transmissivity / trunk zone: consistent with v08 baseline
```

目标：

> 在公平控制下，只替换 building DSM，观察 SVF/shade/ranking 如何变化。

### 5.2 Morphology results

v10-gamma UMEP morphology QA 显示：

```text
Rows: 986
Parsed shadow hours: 800–1900
svf_umep_mean_open_v10 mean: 0.380
shade_fraction_umep_10_16_open_v10 mean: 0.466
building_pixel_fraction_v10 mean: 0.203
```

grid merge 后，v08 vs v10 morphology：

```text
SVF:
    v08 mean = 0.491
    v10 mean = 0.380
    delta = -0.110

Shade fraction:
    v08 mean = 0.423
    v10 mean = 0.466
    delta = +0.043

Building density:
    v08 mean = 0.066
    v10 mean = 0.215
```

### 5.3 Ranking results

v08 vs v10 hazard ranking comparison：

```text
Spearman rank correlation: 0.9705
Top20 overlap: 10 / 20
```

Interpretation:

```text
Global hazard geography remains broadly stable,
but high-priority top set changes substantially.
```

旧 top20 中：

```text
co-derived DSM-gap candidates: 12
leaving v10 top20: 9
```

但 robustness audit 之后，这句话需要更谨慎：

> v10-gamma 不独立证明每一个 diagnosed candidate 都是 false positive；更准确地说，被诊断为 old DSM-gap candidates 的 cells 在 reviewed-DSM morphology correction 后发生了不成比例的排名下降。

### 5.4 Robustness audit

v10-gamma robustness audit 解决了几个关键问题：

#### TP_0315 classification

TP_0315：

```text
v08 rank = 22
v10 rank = 14
transition_class = entering_v10_top_fp_candidate
```

它不是 old-top20 retained false-positive，而是：

```text
v08 top20 外进入 v10 top20，同时携带 broader v10-beta candidate flag。
```

#### Candidate definition transparency

两类 candidate：

```text
co_derived_fp_candidate:
    使用 v10 coverage gain / density gain，因此是 co-derived diagnostic。

independent_old_DSM_gap_candidate:
    old rank ≤ 50 + old-vs-OSM completeness ≤ 0.1，
    更独立但仍是 OSM-reference diagnostic。
```

#### FP vs non-FP baseline

co-derived candidate old-top20 leaving rate：

```text
candidate old-top20 cells:
    9 / 12 left top20 = 75.0%

non-candidate old-top20 cells:
    1 / 8 left top20 = 12.5%

Fisher exact p ≈ 0.0198
```

independent definition:

```text
candidate leave rate = 10 / 15 = 66.7%
noncandidate leave rate = 0 / 5 = 0%
Fisher p ≈ 0.0325
```

### 5.5 Interpretation

v10-gamma 的正确结论：

> reviewed building DSM correction 不会完全重写全域 hazard geography，但会显著改变 high-priority intervention set。old DSM-gap candidates 比 non-candidates 更容易在 reviewed-DSM ranking 中离开 top20。

---

## 6. v10-delta: overhead infrastructure sensitivity

### 6.1 Why v10-delta was needed

v10-gamma 修复了 building DSM gap，但也暴露了新的问题：

```text
高架道路 / 轨道
人行天桥
covered walkway
station canopy
```

这些是 overhead infrastructure，不应并入 ground-up building DSM，也不能继续当成普通开阔地。

### 6.2 Overhead layer

v10-delta 构建独立 overhead layer：

```text
Features after dedup: 952
Total footprint area: 672,186.3 m²
Input candidates: 1769
Dropped duplicates: 817
Multi-source canonical: 789
```

类型分布：

```text
covered_walkway       538
elevated_rail         166
elevated_road         127
pedestrian_bridge      83
viaduct                38
```

### 6.3 Sensitivity method

v10-delta 不重跑 UMEP/SOLWEIG，而是做 ground-level overhead shade sensitivity：

```text
shade_fraction_overhead_sens =
1 - (1 - shade_base_open) × (1 - overhead_proxy_open)
```

其中 `overhead_proxy_open` 使用 open-pixel scope，而不是 whole-cell scope。

### 6.4 Ranking impact

v10 base vs overhead-sensitivity ranking：

```text
Spearman: 0.9327
Top20 overlap: 8 / 20
```

Leaving v10 base top20：

```text
TP_0088, TP_0089, TP_0315, TP_0344, TP_0373, TP_0460,
TP_0564, TP_0572, TP_0575, TP_0888, TP_0916, TP_0973
```

这些 leaving cells 主要是：

```text
transport_deck_or_viaduct
mixed_pedestrian_and_transport_overhead
major_confounding
```

### 6.5 TP_0088 case

TP_0088 是 v10-gamma rank 1，但 v10-delta 后：

```text
rank 1 → rank 224
overhead_fraction_total = 0.732
overhead_interpretation = transport_deck_or_viaduct
```

这说明：

> TP_0088 不能作为 ordinary pedestrian hotspot anchor。它更像是 overhead / transport-deck confounded cell。

### 6.6 Stable anchor hotspots

v10-delta 最重要的 positive finding 是：

```text
TP_0565
TP_0986
```

它们在 building DSM correction 和 overhead sensitivity 后仍保持 high hazard，且 overhead exposure = 0，在 opacity sweep 中 shade 不变。

因此它们可以作为：

```text
confident pedestrian-relevant heat hotspot candidates
```

---

## 7. Integrated interpretation: three-map philosophy

v10 最终不应该只输出一张 map，而应输出三类互补图层。

### Map 1 — v10-gamma base hazard map

含义：

```text
reviewed building DSM + vegetation DSM 的 base physical hazard
```

用途：

```text
展示 corrected building morphology 后的 heat-hazard geography。
```

### Map 2 — v10-delta overhead sensitivity map

含义：

```text
如果 overhead 被视为 ground-level shade，ranking 如何变化。
```

用途：

```text
识别 overhead-confounded hotspots。
```

### Map 3 — hotspot interpretation map

分类建议：

```text
confident_hotspot:
    v10-gamma high
    v10-delta high
    overhead_fraction low

overhead_confounded_hotspot:
    v10-gamma high
    v10-delta drops strongly
    overhead_fraction high

building_DSM_gap_corrected_false_positive:
    v08 high
    v10-gamma drops
    old completeness low

dense_built_edge_case:
    fully / near-fully built, no open-pixel SVF

transport_deck_caveat:
    bridge deck / viaduct / elevated rail dominated cell
```

---

## 8. Final v10 findings

### Finding 1 — v0.9 building DSM gap was real and material

HDB3D + URA DSM was insufficient as a complete building morphology base. v10-alpha / alpha.3 corrected this through OSM-first augmentation, manual QA and reviewed DSM generation.

### Finding 2 — old top hazards included DSM-gap false-positive candidates

v10-beta identified 34 possible old DSM-gap false-positive candidates. Many old top20 cells had old building density = 0 but v10 building density between 0.17 and 0.43.

### Finding 3 — reviewed DSM correction changes the top hazard set

v10-gamma showed global rank stability but top20 restructuring:

```text
Spearman = 0.9705
Top20 overlap = 10 / 20
```

### Finding 4 — diagnosed DSM-gap candidates were disproportionately corrected downward

Among old top20 cells:

```text
co-derived DSM-gap candidates left top20: 9/12
non-candidates left top20: 1/8
```

### Finding 5 — overhead infrastructure is the next major confounder

v10-delta showed overhead sensitivity:

```text
v10 base vs overhead sensitivity:
Spearman = 0.9327
Top20 overlap = 8 / 20
```

Several v10-gamma top cells were transport-deck / viaduct dominated.

### Finding 6 — TP_0565 and TP_0986 are strongest current confident hotspot anchors

They remain high after:

```text
building DSM correction
UMEP rerun
overhead sensitivity
opacity sweep
```

### Finding 7 — v10 remains a corrected research model, not an operational warning system

Remaining limitations include:

```text
no full overhead-aware SOLWEIG
no transport-deck heat modelling
no pedestrian accessibility model
no ML residual calibration on extended archive
no uncertainty quantification
```

---

## 9. Limitations

### 9.1 OSM is not ground truth

Completeness is relative to OSM-mapped footprints. OSM can omit buildings or include roof/canopy-like structures.

### 9.2 Height realism remains approximate

Although v10-beta.1 corrected major visible anomalies, many building heights still use default or inferred values.

### 9.3 Overhead sensitivity is algebraic

v10-delta does not model time-varying shadows, overhead height, longwave radiation, wind, bridge deck heat or transport heat.

### 9.4 Fully built cells remain edge cases

Cells like TP_0945 have no open-pixel SVF and may drop to zero hazard. These need special interpretation.

### 9.5 Pedestrian exposure not directly observed

Hazard ranking estimates potential heat stress, not measured pedestrian counts or real-time activity exposure.

### 9.6 Archive-based calibration and ML remain future work

v0.9 calibration established the need for WBGT proxy calibration, but v10 morphology changes have not yet been integrated into a new ML residual model.

---

## 10. Future work and ML positioning

### 10.1 v10-epsilon selected SOLWEIG

Optional lightweight validation:

```text
TP_0565 — confident hot anchor
TP_0986 — confident hot anchor
TP_0088 — overhead-confounded rank-1 collapse case
TP_0916 / TP_0973 — saturated overhead case
T05 / TP_0433 — shaded reference
```

Purpose:

```text
validate whether v10-delta overhead sensitivity is physically reasonable in Tmrt terms.
```

### 10.2 v11 archive and ML

ML should not replace physics formulas or GIS morphology. It should be used for:

```text
physics-based residual learning
uncertainty quantification
event threshold calibration
```

Recommended v11 path:

```text
v11-alpha:
    rebuild paired archive using v10 features

v11-beta:
    rerun physics/calibration baselines

v11-gamma:
    GBM / XGBoost / LightGBM residual learning

v11-delta:
    quantile regression / conformal uncertainty

v11-epsilon:
    event probability for WBGT ≥31 / ≥33
```

The best target is:

```text
residual = official_WBGT - calibrated_physics_proxy
```

This matches the ML planning document: ML should learn the residual around physics and morphology, not replace Open-Meteo, UTCI/WBGT formulas or deterministic GIS features.

---

## 11. Suggested dissertation wording

### Chinese

> OpenHeat v10 完成了一个从 building-DSM 数据完整性审计到 reviewed morphology correction，再到 overhead-infrastructure sensitivity 的逐层修正流程。v10-alpha/alpha.3 通过 OSM-first augmentation 和 manual QA 修复了旧 HDB3D+URA DSM 的 building coverage gap；v10-beta 证明旧 v08/v09 top hazard ranking 中有一批 cells 是 DSM-gap false-positive candidates；v10-gamma 使用 reviewed height-QA DSM 重跑 UMEP SVF/shadow，并显示全局 ranking 仍高度相关但 top20 显著重排；v10-gamma robustness audit 进一步证明 DSM-gap candidates 比 non-candidates 更容易离开 top20；v10-delta 则揭示 reviewed-DSM ranking 后新的 overhead-infrastructure bias。最终，OpenHeat v10 不应被理解为单一 hazard map，而应被理解为一套 data-integrity-corrected heat-risk interpretation framework，包括 base hazard、overhead sensitivity 和 confident/caveated hotspot 分类。

### English

> OpenHeat v10 establishes a sequential data-integrity correction framework for neighbourhood-scale tropical heat-risk modelling. An OSM-first augmented building DSM corrected the building-footprint incompleteness identified in v0.9; reviewed-DSM morphology reruns then quantified how old high-hazard cells were disproportionately affected by the correction. A subsequent overhead-infrastructure sensitivity layer showed that elevated roads, rail viaducts, pedestrian bridges and covered walkways form a second major source of ranking confounding. Rather than presenting a single final hazard map, OpenHeat v10 therefore reports a reviewed-DSM base hazard map, an overhead-shade sensitivity map, and a confident/caveated hotspot interpretation layer.

---

## 12. Final status

```text
v10-alpha:      passed
v10-beta:       passed
v10-gamma:      passed with robustness audit
v10-delta:      passed as overhead sensitivity layer
v10-epsilon:    optional selected-cell SOLWEIG validation
v11:            future ML residual and uncertainty pipeline
```

Final v10 interpretation:

> **OpenHeat v10 is a data-integrity-corrected, overhead-aware sensitivity framework for Toa Payoh pedestrian heat-hazard interpretation. It is not yet an operational real-time warning model, but it is a strong methodological contribution demonstrating how open urban morphology data gaps and overhead infrastructure can systematically reshape heat-risk rankings.**

---

## 13. Key file index

```text
docs/v09_freeze/
    V09_FREEZE_NOTE_CN.md
    V09_REVISED_FINDINGS_CN.md

outputs/v10_dsm_audit/
    v10_alpha3_manual_decisions_report.md
    v10_alpha3_completeness_gain_report.md
    v10_beta1_height_geometry_QA_report.md

outputs/v10_morphology/
    v10_basic_morphology_QA_report.md
    v10_old_vs_new_building_morphology_shift.csv

outputs/v10_ranking_audit/
    v10_beta_morphology_shift_audit_report.md
    v10_old_false_positive_candidates.csv

outputs/v10_gamma_comparison/
    v10_vs_v08_forecast_ranking_comparison.md
    v10_vs_v08_rank_comparison.csv

outputs/v10_gamma_robustness/
    v10_gamma_robustness_audit_report.md
    v10_gamma_top20_transition_classes.csv

outputs/v10_overhead_qa/
    v10_overhead_layer_QA_report.md
    v10_overhead_sensitivity_grid_report.md
    v10_opacity_sensitivity_sweep_report.md

outputs/v10_delta_overhead_comparison/
    v10_base_vs_overhead_sensitivity_comparison.md
```
