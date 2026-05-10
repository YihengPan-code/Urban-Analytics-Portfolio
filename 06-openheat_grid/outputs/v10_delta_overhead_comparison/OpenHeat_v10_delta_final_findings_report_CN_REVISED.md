# OpenHeat-ToaPayoh v10-delta Final Findings Report — Revised

> Version: v10-delta revised  
> Theme: overhead infrastructure QA and ground-level shade sensitivity on top of v10-gamma reviewed-DSM hazard ranking  
> Status: revised findings report after result review and narrative calibration  
> Language: Chinese  
> Companion documents: `OpenHeat_v10_gamma_final_findings_report_CN_REVISED.md`, `v10_delta_overhead_comparison/`, `outputs/v10_overhead_qa/`

---

## 1. Executive summary

v10-delta 在 v10-gamma 的 reviewed building DSM + UMEP morphology 基础上，进一步处理了 OpenHeat 项目的第二类系统性 open-data uncertainty：**overhead infrastructure mis-attribution**。这里的 overhead infrastructure 包括高架道路、高架轨道、viaduct、人行天桥、covered walkway 和车站遮罩等。

v10-delta 的核心定位是：

> **overhead-infrastructure QA and shade-sensitivity layer**，不是最终 overhead-aware physical model。

它通过构建独立的 overhead layer，计算每个 100 m grid cell 的 overhead exposure，并用一个 open-pixel-scope 的 algebraic shade sensitivity 检验：

> 如果 overhead 被视为 ground-level shading source，v10-gamma 的 hazard ranking 会如何变化？

v10-delta 的主要结论如下：

1. **Overhead layer 构建成功。** 去重后得到 952 个 canonical overhead features，总覆盖面积 672,186 m²；其中 789 个 features 是 multi-source canonical，说明大多数 overhead objects 在不同 OSM representation 中被重复捕捉。
2. **Overhead sensitivity 对 top hazard set 的影响显著。** v10 base 与 overhead-shade sensitivity 的 Spearman rank correlation 为 0.9327，Top20 overlap 为 8/20。这个结果说明 global hazard geography 仍相对稳定，但 top intervention set 对 overhead handling 高度敏感。
3. **v10-gamma rank-1 hotspot TP_0088 是最典型的 overhead-confounded case。** 它在 v10-gamma 中为 rank 1，但在 overhead-shade sensitivity 中跌至 rank 224，并被分类为 `transport_deck_or_viaduct`。
4. **v10-gamma 进入 top20 的 cells 中有一批受到 overhead 强烈影响。** v10-gamma 进入 top20 的 10 个 cells 中，有 7 个在 v10-delta sensitivity 中离开 top20，多数为 `transport_deck_or_viaduct` 或 `mixed_pedestrian_and_transport_overhead`。
5. **v10-gamma 的 stubborn false-positive candidates 被进一步分流。** TP_0564 和 TP_0315 在 overhead sensitivity 下下降，属于 overhead-driven suspicious cells；TP_0565 和 TP_0986 在 opacity sweep 中 overhead effect 为 0，并在多层 correction 后仍保持 high hazard，可作为目前最可信的 pedestrian-relevant heat hotspot anchor cells。
6. **Opacity prior 不是全局结论的关键瓶颈，但 saturation 是重要 limitation。** 五组 opacity scenario 的 mean shade_new 只相差约 0.008，说明整体结论对 opacity prior 较稳；但多个 high-overhead cells 被 algebraic formula 推到 shade=1.0，说明该方法不能替代 overhead-aware SOLWEIG。
7. **v10-delta 应作为 sensitivity / QA evidence，而不是 final physical hazard model。** 它证明 overhead infrastructure 会显著改变 top-set interpretation，但没有模拟桥面热储存、桥下通风、长波辐射、交通热排放或真实 Tmrt。

最重要的 revised narrative 是：

> v10-gamma 是 reviewed building DSM 后的 corrected base hazard ranking；v10-delta 是对该 base ranking 的 overhead-infrastructure sensitivity audit。二者应联合呈现：v10-gamma 给出 reviewed-DSM baseline，v10-delta 标记和检验其中的 overhead-confounded hotspots，并提取更稳健的 confident hotspot subset。

---

## 2. Scope and interpretation boundary

### 2.1 v10-delta 回答什么问题？

v10-delta 回答的是一个 narrow but important 的问题：

> 在 v10-gamma reviewed-DSM hazard ranking 中，哪些 cells 的高 hazard 可能来自 overhead infrastructure 被误当作普通开阔行人空间？如果将 overhead 视作 ground-level shade source，ranking 是否发生实质性变化？

因此 v10-delta 是：

```text
QA layer
sensitivity layer
ranking interpretation layer
```

不是：

```text
完整 overhead-aware UMEP/SOLWEIG physical model
最终 operational hazard ranking
桥面道路 surface heat model
真实 Tmrt 降温量估计
```

### 2.2 为什么不能把 overhead 直接并入 building DSM？

高架桥 / viaduct / covered walkway / station canopy 是 two-layer urban objects：

```text
上方：桥面、轨道、屋盖或 canopy；
下方：仍可能是可通行的 ground-level pedestrian / road / parking space。
```

普通 building DSM 的假设是：

```text
从地面开始，footprint 范围内是实体障碍物。
```

如果把 overhead 直接烧进 ground-up building DSM，会把桥下可通行空间误当成实心建筑，从而污染 open-pixel mask、SVF、shadow 和 pedestrian heat exposure interpretation。

因此 v10-delta 使用独立 overhead layer，而不修改 reviewed building DSM。

---

## 3. Data inputs and outputs

### 3.1 Main inputs

```text
data/grid/v10/toa_payoh_grid_v10_features_umep_with_veg.csv
    v10-gamma reviewed-DSM UMEP morphology grid

outputs/v09_gamma_qa/v09_overhead_structures.geojson
outputs/v09_gamma_qa/v09_overhead_structures_footprints.geojson
    v0.9-gamma Overpass/OSM overhead candidates

data/features_3d/v10/manual_qa/overhead_candidates_v10.geojson
    v10 manual QA overhead candidate layer, including station canopy / roof-like objects

outputs/v10_gamma_forecast_live/v06_live_hotspot_ranking.csv
    v10-gamma base hazard ranking
```

### 3.2 Main outputs

```text
data/features_3d/v10/overhead/overhead_structures_v10.geojson
    canonical overhead layer after deduplication

outputs/v10_overhead_qa/v10_overhead_per_cell.csv
    per-cell overhead metrics

data/grid/v10/toa_payoh_grid_v10_features_overhead_sensitivity.csv
    v10 grid with shade_fraction_overhead_sens

outputs/v10_delta_overhead_comparison/v10_base_vs_overhead_sensitivity_comparison.md
    base vs overhead sensitivity ranking comparison

outputs/v10_overhead_qa/v10_opacity_sensitivity_sweep_report.md
    opacity prior robustness check
```

---

## 4. Methodological patches and quality controls

### 4.1 IoU-based overhead deduplication

原始 overhead sources 中存在重复 representation：同一个 overhead object 可能同时以 polygon footprint 和 line structure 出现。如果直接 concat 后 overlay 到 grid，会双计或多计 overhead area。

v10-delta 因此使用 IoU-based deduplication：

```text
input candidates:        1769
kept canonical features: 952
dropped as duplicate:    817
multi-source canonical:  789
IoU threshold:           0.5
```

这一步是 v10-delta 可信的前提。没有 dedup，overhead_fraction_total 可能被系统性高估，特别是在高架/连廊密集区域。

### 4.2 Scope alignment: cell-area to open-pixel-area

v10-gamma 的 UMEP `shade_fraction` 是 open-pixel scope，即：

> cell 中非建筑像素里，有多少比例处于 shade。

而 overhead footprint 原始比例是 whole-cell scope，即：

> cell 总面积里，有多少比例被 overhead 覆盖。

二者分母不同，不能直接相乘。v10-delta 因此将 overhead proxy 重新缩放到 open-pixel scope：

```text
overhead_proxy_open = overhead_proxy_cell / open_pixel_fraction_v10
```

并 clip 到 0–1。

核心 sensitivity formula 为：

```text
shade_fraction_overhead_sens =
    1 - (1 - shade_base_open) × (1 - overhead_proxy_open)
```

这个公式是 algebraic sensitivity，不是 physical Tmrt simulation。它用于检验 ranking 是否对 overhead shading 假设敏感。

### 4.3 Opacity prior sweep

由于 overhead type opacity 是先验判断，v10-delta 做了五组 scenario：

```text
low_opacity
default
high_opacity
pedestrian_strong
transport_strong
```

结果显示 mean shade_new 在五组 scenario 中范围约为 0.491–0.499，mean difference 约 0.008。n_cells_with_delta_gt_0p10 在 48–70 之间，说明全局 conclusion 对 opacity prior 较稳。

但多个 high-overhead focus cells 在所有 scenario 下都被推到 shade_new=1.0，这是 saturation limitation，而不是物理确定性。

---

## 5. Overhead layer QA

### 5.1 Source composition

v10-delta 构建得到 952 个 canonical overhead features，总面积 672,186.3 m²。

类型分布为：

```text
covered_walkway       538
elevated_rail         166
elevated_road         127
pedestrian_bridge      83
viaduct                38
```

这说明 Toa Payoh AOI 内 overhead infrastructure 不只是个别高架桥，而是一个多类型、空间分布不均的城市层。

### 5.2 Multi-source confidence

789 / 952 个 canonical overhead features 为 multi-source canonical，说明它们在不同 overhead source representation 中重复出现。这增强了 layer 的可信度。

### 5.3 Type-level interpretation

需要区分两种 overhead：

1. **Pedestrian shelter type**：covered walkway、station canopy、人行天桥等。  
   它们通常与 pedestrian exposure 直接相关，可解释为 adaptation / shade infrastructure。

2. **Transport deck type**：elevated road、elevated rail、viaduct。  
   它们通常不是普通行人停留或活动空间。桥面/轨道本身可能很热，但桥下 ground-level 空间可能被遮阴。因此它们应作为 transport-deck confounding flag，而不是简单的 pedestrian cooling feature。

---

## 6. Cell-level overhead sensitivity results

### 6.1 Overall distribution

v10-delta overhead exposure 是高度偏态分布：

```text
overhead_fraction_total mean ≈ 0.046
median = 0
p75 ≈ 0.025
max = 1.0
```

这意味着超过一半的 cells 基本没有 overhead 暴露，但少数 cells 是 overhead-dominated。

Shade sensitivity 的总体变化为：

```text
base shade mean ≈ 0.466
overhead-sensitivity shade mean ≈ 0.496
mean delta ≈ 0.030
```

平均变化不大，但 top tail 变化极大，多个 overhead-dominated cells 的 shade_new 被推到 1.0。

### 6.2 Top affected cells

Top affected cells 几乎全部为 `transport_deck_or_viaduct` 或 `mixed_pedestrian_and_transport_overhead`，例如：

```text
TP_0945, TP_0831, TP_0916, TP_0803, TP_0888,
TP_0746, TP_0887, TP_0859, TP_0973, TP_0860,
TP_0717, TP_0944, TP_0088, TP_0575
```

这说明 v10-delta 的 ranking signal 主要由 transport / viaduct infrastructure 驱动，而不是由零碎 covered walkway 驱动。

### 6.3 Saturation effect

多个 cells 在 algebraic formula 下被推到：

```text
shade_fraction_overhead_sens = 1.0
```

这不是完整物理模型的结果，而是 sensitivity formula 在 high-overhead/open-pixel-limited cells 中的 saturation。它说明这些 cells 是 overhead-dominated，但不能证明它们真实全天 fully shaded。

---

## 7. Ranking comparison: v10 base vs overhead-shade sensitivity

v10-delta ranking comparison 的核心结果为：

```text
Spearman rank correlation = 0.9327
Top20 overlap = 8 / 20
```

这说明 v10-delta 对全局 ranking 仍保持较高相关，但 top hazard set 发生了大幅重组。

### 7.1 Leaving v10 base top20

离开 base v10 top20 的 12 个 cells 为：

```text
TP_0088, TP_0089, TP_0315, TP_0344, TP_0373, TP_0460,
TP_0564, TP_0572, TP_0575, TP_0888, TP_0916, TP_0973
```

这些 cells 几乎都属于 `major_confounding`，并主要被解释为 `transport_deck_or_viaduct` 或 `mixed_pedestrian_and_transport_overhead`。

### 7.2 Entering overhead-sensitivity top20

进入 overhead-sensitivity top20 的 12 个 cells 为：

```text
TP_0030, TP_0060, TP_0116, TP_0136, TP_0144, TP_0366,
TP_0452, TP_0527, TP_0639, TP_0641, TP_0984, TP_0985
```

这些 cells 本身不一定“变热”；它们主要是在 overhead-confounded cells 被下调后相对上升。报告和地图中应避免将其解释为 v10-delta 新发现的绝对高热源，而应解释为 overhead sensitivity 下重新排序后的 high-hazard candidates。

### 7.3 TP_0088: primary overhead-confounded case

TP_0088 是 v10-delta 最关键 individual case：

```text
v10 base rank = 1
v10 overhead-sensitivity rank = 224
overhead_fraction_total = 0.732
overhead_shade_proxy = 0.549
overhead_interpretation = transport_deck_or_viaduct
```

这意味着 v10-gamma 单独将 TP_0088 呈现为 top hotspot 并不安全。更合理的解释是：

> TP_0088 是 transport-deck / viaduct-dominated cell。它可能包含桥面高温和桥下遮阴两种相反效应，不能作为普通 ground-level pedestrian hotspot 解释。

---

## 8. Interaction with v10-gamma findings

### 8.1 v10-gamma entering cells 的命运

v10-gamma 中进入 top20 的 10 个 cells，有 7 个在 v10-delta sensitivity 中离开 top20。它们主要是 overhead-driven cells。

这说明：

> v10-gamma 修复了 building DSM gap 后，新的 top set 中又暴露出 overhead infrastructure mis-attribution。

这是 sequential audit 的自然结果，不是 v10-gamma 失败。

### 8.2 stubborn false-positive candidates 的进一步分类

v10-gamma robustness audit 曾指出几个 old DSM-gap candidates 在 v10-gamma 后仍保持 high hazard。v10-delta 将它们进一步分成两类：

```text
overhead-driven / should be downgraded:
    TP_0564
    TP_0315

stable high-hazard anchors:
    TP_0565
    TP_0986
```

TP_0565 和 TP_0986 在 opacity sweep 中 overhead effect 为 0，在 v10-gamma 和 v10-delta 两层 correction 后仍保持 high hazard，因此是目前最可信的 pedestrian-relevant hotspot candidates。

---

## 9. Revised findings

### Finding 1 — Overhead infrastructure is a major top-set sensitivity factor

v10-delta 显示，在 reviewed building DSM 后，overhead infrastructure 会显著影响 top hazard set。v10 base vs overhead-shade sensitivity 的 top20 overlap 为 8/20，说明 top intervention set 对 overhead handling 高度敏感。

该结论应表述为：

> In terms of top-set ranking sensitivity, overhead-shade assumptions were highly disruptive.

而不是：

> Overhead infrastructure has a larger calibrated physical heat effect than buildings.

因为 v10-delta 是 algebraic sensitivity，不是 calibrated physical model。

### Finding 2 — TP_0088 is overhead-confounded, not a clean pedestrian hotspot

TP_0088 是 v10-gamma rank-1 cell，但在 v10-delta 中跌至 rank 224，并被解释为 transport-deck/viaduct dominated。它应被标记为 overhead-confounded hotspot，而不是普通 pedestrian heat hotspot。

### Finding 3 — v10-gamma introduces a second-layer bias after building correction

v10-gamma 修复 building DSM gap 后，一些新的 high-ranking cells 被识别为 overhead-confounded。这说明 OpenHeat 的 data-integrity correction 是 sequential 的：

```text
v0.9/v10-alpha/beta: building DSM completeness bias
v10-gamma: reviewed building DSM correction
v10-delta: overhead infrastructure bias sensitivity
```

### Finding 4 — TP_0565 and TP_0986 are the most defensible anchor hotspots

TP_0565 和 TP_0986 在 building DSM correction 与 overhead sensitivity 后仍然保持 high hazard，并且 overhead exposure 为 0。它们可以作为 dissertation / portfolio 中最稳的 pedestrian-relevant hotspot examples。

### Finding 5 — Opacity prior is not the main uncertainty; saturation is

五组 opacity scenario 的 aggregate differences 较小，说明全局结论对 opacity prior 较稳。但 high-overhead cells 的 shade_new saturation 到 1.0，说明 algebraic method 不能替代 overhead-aware SOLWEIG。

### Finding 6 — v10-delta defines a confident hotspot subset, not a final physical ranking

v10-delta 最适合用于定义：

```text
confident hotspots:
    high in v10-gamma base
    remain high in v10-delta sensitivity
    low overhead or no major overhead confounding
```

而不是单独替代 v10-gamma 成为 final physical hazard ranking。

---

## 10. Recommended interpretation framework

v10-delta 后，建议将 OpenHeat v10 hazard outputs 分成三层：

### 10.1 v10-gamma base hazard ranking

用途：

```text
reviewed building DSM + vegetation UMEP morphology 下的 corrected base hazard map
```

适合展示：

```text
building DSM correction 后的 baseline heat-hazard geography
```

### 10.2 v10-delta overhead sensitivity ranking

用途：

```text
检验 top hazards 对 overhead-shade assumptions 的敏感性
```

适合展示：

```text
overhead-confounded hotspots
transport-deck / viaduct dominated cells
sensitivity-based rank changes
```

### 10.3 Confident hotspot subset

定义建议：

```text
v10-gamma high hazard
AND remains high after v10-delta
AND overhead_fraction_total < 0.05 or overhead_confounding_flag = clean_or_minor
```

示例 anchor cells：

```text
TP_0565
TP_0986
```

这一层最适合作为 dissertation 中 “defensible pedestrian-relevant hotspots”。

---

## 11. Limitations

### 11.1 Algebraic sensitivity, not physical model

v10-delta 没有重跑 overhead-aware UMEP / SOLWEIG。它只修改 shade_fraction，不修改 SVF、longwave、wind、surface heat storage 或 Tmrt。

因此不能声称：

```text
某 cell 的真实 Tmrt 降低了 X°C。
```

只能声称：

```text
该 cell 对 overhead-shade assumptions 高度敏感。
```

### 11.2 Transport-deck heat is not modelled

Elevated roads / rail viaducts 可能是高温硬化交通表面，但 v10-delta 将它们作为 ground-level shade source 处理。这适合 pedestrian-ground exposure sensitivity，但不适合 surface heat reservoir analysis。

### 11.3 Saturation effect

多个 high-overhead cells 的 shade_new 被推到 1.0。这说明 algebraic formula 是 coarse screening tool，而不是精细 radiative transfer model。

### 11.4 OSM-derived overhead is not ground truth

v10-delta 的 overhead layer 绝大多数来自 OSM。OSM 可能漏掉 station canopy、小型 shelter、bus stop roof 或复杂 transport decks。因此 v10-delta overhead layer 是 lower-bound / open-data layer，而不是完整 authoritative inventory。

### 11.5 Overhead layer not incorporated into SVF

真实 overhead 也会影响 pedestrian-perceived SVF，但 v10-delta 没有重算 SVF。未来的 v10-epsilon 或 v11 应通过 overhead-aware SOLWEIG / UMEP sensitivity 做更完整评估。

---

## 12. Suggested dissertation / portfolio wording

### English summary

> Building on the v10-gamma reviewed-DSM hazard ranking, v10-delta tested the sensitivity of hotspot interpretation to overhead infrastructure, including covered walkways, pedestrian bridges, elevated roads, MRT viaducts and station canopies. A canonical overhead layer with 952 features and 672,186 m² footprint area was assembled with IoU-based deduplication. Using an open-pixel-scope overhead shade sensitivity, the resulting hazard ranking remained globally correlated with v10-gamma (Spearman = 0.9327) but showed substantial top-set reorganisation, with only 8/20 top-20 overlap. The v10-gamma rank-1 cell TP_0088 dropped to rank 224 and was classified as transport-deck/viaduct dominated. This indicates that overhead infrastructure is a major interpretive uncertainty after building-DSM correction. However, v10-delta should be interpreted as a sensitivity layer rather than a final physical overhead-aware model. Cells such as TP_0565 and TP_0986, which remain high hazard after both building-DSM correction and overhead sensitivity, are the most defensible pedestrian-relevant hotspot anchors.

### Chinese summary

> 在 v10-gamma reviewed-DSM hazard ranking 基础上，v10-delta 测试了 hotspot interpretation 对 overhead infrastructure 的敏感性，包括 covered walkway、人行天桥、高架道路、MRT viaduct 和车站遮罩。通过 IoU-based deduplication 构建了 952 个 canonical overhead features，总覆盖面积 672,186 m²。基于 open-pixel-scope 的 overhead shade sensitivity 后，hazard ranking 与 v10-gamma 全局仍较相关（Spearman = 0.9327），但 top20 发生明显重组，重合仅为 8/20。v10-gamma rank-1 cell TP_0088 在 v10-delta 中跌至 rank 224，并被分类为 transport-deck/viaduct dominated。这说明在 building DSM correction 之后，overhead infrastructure 是 hotspot interpretation 的重要不确定性。但 v10-delta 应解释为 sensitivity layer，而不是最终物理 overhead-aware model。TP_0565 和 TP_0986 这类经过 building-DSM correction 与 overhead sensitivity 后仍保持 high hazard 的 cells，是目前最可信的 pedestrian-relevant hotspot anchors。

---

## 13. Recommended next steps

### Step 1 — QGIS visual validation

建议在 QGIS 中视觉验证以下 cells：

```text
TP_0088   rank-1 drop case, transport-deck dominated
TP_0916   saturated overhead case
TP_0973   saturated overhead case
TP_0945   fully-built / transport interchange edge case
TP_0565   stable high-hazard anchor
TP_0986   stable high-hazard anchor
```

重点确认：

```text
overhead layer 是否确实对应卫星图中的高架/连廊/车站遮罩；
TP_0565 / TP_0986 是否确实没有 major overhead confounding；
TP_0088 是否不能作为普通 ground-level pedestrian hotspot 解释。
```

### Step 2 — Build final integrated v10 findings report

建议将 v10-alpha/beta/gamma/delta 整合为：

```text
OpenHeat_v10_integrated_findings_report_CN.md
```

结构：

```text
1. v0.9 audit problem
2. v10-alpha reviewed building DSM
3. v10-beta morphology shift and DSM-gap candidates
4. v10-gamma reviewed-DSM hazard ranking and robustness audit
5. v10-delta overhead sensitivity
6. confident hotspots vs overhead-confounded hotspots
7. limitations and next work
```

### Step 3 — Optional v10-epsilon overhead-aware SOLWEIG

只有在需要量化 Tmrt 差异时才建议做 v10-epsilon。候选 cells：

```text
TP_0088
TP_0916 / TP_0973
TP_0565
TP_0986
T05 shaded reference
```

目标：

```text
比较 building+vegetation-only SOLWEIG 与 overhead-aware SOLWEIG，检验 algebraic saturation 是否过强。
```

如果时间紧，v10-delta 已足以作为 dissertation 中的 overhead-infrastructure sensitivity finding。

---

## 14. Final status

```text
v10-delta status: PASSED as overhead infrastructure QA and shade-sensitivity layer.
```

它应被视为：

```text
1. v10-gamma reviewed-DSM ranking 的 overhead sensitivity audit；
2. OSM-derived overhead infrastructure influence 的 lower-bound diagnostic；
3. 识别 overhead-confounded hotspots 与 confident pedestrian hotspots 的工具。
```

它不应被视为：

```text
1. final overhead-aware physical hazard model；
2. absolute Tmrt reduction estimate；
3. operational warning model；
4. bridge-deck heat exposure model。
```

最终结论：

> v10-delta 成功揭示了 OpenHeat 在 building DSM correction 之后的第二层主要形态不确定性：overhead infrastructure。它并不替代 v10-gamma，而是让 v10-gamma 的 hotspot interpretation 更稳健。OpenHeat v10 最终应同时呈现 reviewed-DSM base hazard、overhead sensitivity map，以及经两层 correction 后仍稳定的 confident hotspot subset。

