# OpenHeat-ToaPayoh v10-gamma Final Findings Report

> Version: v10-gamma  
> Theme: reviewed-DSM UMEP morphology rerun and v08/v10 hazard-ranking comparison  
> Status: final findings draft for v10-gamma, before selected-tile SOLWEIG rerun and overhead-DSM sensitivity  
> Language: Chinese  

---

## 1. Executive summary

v10-gamma 成功完成了 OpenHeat v1.0 的第一个核心目标：用 **reviewed height-QA building DSM** 重新计算 UMEP SVF / shadow morphology，并将其合并回 forecast grid，生成第一次基于 corrected building morphology 的 heat-hazard ranking comparison。

v10-gamma 的关键结论是：

1. **v10 reviewed DSM 显著改变了基础城市形态。**  相较 v08/current DSM，v10 的平均 SVF 明显降低，平均 shade fraction 略升，平均 building density 大幅上升。
2. **全局 ranking 大体稳定，但 top hazard set 被实质性修正。** v08 与 v10 的 hazard-rank Spearman correlation 为 0.9705，但 top20 overlap 只有 10/20。
3. **v0.9 audit 的核心判断得到支持。** 旧 v08 top20 中有 12 个 DSM-gap false-positive candidates，其中 9 个在 v10 中离开 top20。
4. **少数旧 false-positive candidates 在 v10 中仍保持高 hazard。** 这说明它们可能不是纯粹假热点，而是在 corrected morphology 下仍具有高热暴露条件。
5. **v10-gamma 是 data-integrity-corrected hazard ranking 的第一版，但还不是最终 operational heat-risk model。** 它仍未显式建模 overhead infrastructure，也还没有重跑 selected-tile SOLWEIG / Tmrt。

最重要的叙事变化是：

> v10-gamma 不只是“重新跑了一遍模型”，而是把 v0.9 发现的 building-DSM data-gap 问题转化成了可量化的 ranking correction evidence。

---

## 2. Scope and method

### 2.1 v10-gamma 的目标

v10-gamma 的目标不是重新训练 ML，也不是直接运行 SOLWEIG/Tmrt，而是复刻 v08 的 UMEP morphology 层级，只替换 building DSM：

```text
v08 baseline:
    old HDB3D + URA building DSM
    + v08 vegetation DSM
    → UMEP SVF / shadow
    → forecast / hazard ranking

v10-gamma:
    reviewed height-QA augmented building DSM
    + same v08 vegetation DSM
    → UMEP SVF / shadow
    → forecast / hazard ranking
```

这样可以尽量保证 v08-v10 comparison 的公平性：主要变化来自 building DSM，而不是 vegetation transmissivity、日期、太阳条件、sky scheme 或 forecast engine。

### 2.2 主要输入

v10-gamma 使用以下关键输入：

```text
data/rasters/v10/dsm_buildings_2m_augmented_reviewed_heightqa.tif
    reviewed + manual-QA + height-QA building DSM

data/rasters/v08/dsm_vegetation_2m_toapayoh.tif
    v08 vegetation DSM, unchanged

data/grid/toa_payoh_grid_v08_features_umep_with_veg.csv
    base forecast grid

data/grid/v10/toa_payoh_grid_v10_umep_morphology_with_veg.csv
    v10 UMEP morphology output aggregated to grid
```

### 2.3 主要输出

核心输出包括：

```text
data/grid/v10/toa_payoh_grid_v10_features_umep_with_veg.csv
outputs/v10_gamma_forecast_live/v10_gamma_hotspot_ranking_with_grid_features.csv
outputs/v10_gamma_comparison/v10_vs_v08_forecast_ranking_comparison.md
outputs/v10_gamma_comparison/v10_vs_v08_rank_comparison.csv
```

其中 comparison 使用 `hazard_score` 排名，因此反映 **physical heat-hazard ranking**，不是 risk-priority ranking。

---

## 3. UMEP morphology QA

### 3.1 Shadow time parsing

v10-gamma 成功识别了完整 shadow hours：

```text
800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900
```

这说明 shadow rasters 文件命名和后处理时间解析都正常。后续 `shade_fraction_10_16` 和 `shade_fraction_13_15` 具有可用基础。

### 3.2 v10 UMEP morphology summary

UMEP zonal morphology 输出覆盖 986 个 grid cells。核心变量摘要如下：

```text
svf_umep_mean_open_v10 mean                  = 0.380031
shade_fraction_umep_10_16_open_v10 mean     = 0.465755
shade_fraction_umep_13_15_open_v10 mean     = 0.424577
building_pixel_fraction_v10 mean            = 0.202752
open_pixel_fraction_v10 mean                = 0.797248
```

`svf_umep_mean_open_v10` 有 985 个有效值，shade fraction 有 986 个有效值。1 个 SVF missing 的情况应在 QA 中保留说明，可能与 fully built / no valid open pixels 有关。

### 3.3 v08-v10 morphology change

grid merge QA 显示，v10 morphology 成功替换到 forecast grid 中。与 v08 相比：

```text
SVF mean:
    v08 = 0.490616
    v10 = 0.380031
    delta = -0.110082

shade_fraction mean:
    v08 = 0.422549
    v10 = 0.465755
    delta = +0.043206

building_density mean:
    v08 = 0.065906
    v10 = 0.214805

mean_building_height_m:
    v08 = 17.303592
    v10 = 22.334463
```

这与 v10-alpha/beta 的预期一致：reviewed DSM 补足建筑后，城市环境不再被过度解释为开阔空间，因此平均 SVF 降低、遮阴增加、building density 提高。

### 3.4 QA interpretation

v10-gamma morphology 结果整体健康。它没有出现 SVF 全 0、全 1、shadow 全无或 NaN 大量扩散的问题。

需要记录的 QA caveat 是：

```text
- 1 个 cell 的 open-pixel SVF 缺失；
- per-cell completeness ratio >1 在之前 audit 中已解释为 OSM reference denominator 问题；
- v10-gamma 仍未显式建模 overhead infrastructure。
```

---

## 4. Hazard ranking comparison

### 4.1 Global rank stability

v08 与 v10 的 hazard ranking 在全体 986 个 cells 上仍保持高度相关：

```text
Spearman rank correlation = 0.9705
```

这说明 v10 并没有完全推翻整个 heat-hazard geography。许多大尺度空间模式仍然稳定。

但 top20 overlap 为：

```text
Top20 overlap = 10 / 20
```

这说明最重要的 high-hazard intervention set 发生了实质性重排。

### 4.2 Entering and leaving top20

进入 v10 top20 的 cells：

```text
TP_0120
TP_0171
TP_0315
TP_0344
TP_0373
TP_0572
TP_0766
TP_0888
TP_0916
TP_0973
```

离开 v08 top20 的 cells：

```text
TP_0027
TP_0060
TP_0116
TP_0638
TP_0820
TP_0849
TP_0876
TP_0923
TP_0984
TP_0985
```

这种结果非常符合 v10 的目标：全局排序不是乱掉，而是旧 top set 中一批由 DSM gap 推高的 cells 被 correction 下调。

---

## 5. DSM-gap false-positive correction

### 5.1 Diagnostic summary

comparison report 给出：

```text
old_top20_false_positive_candidates = 12
leaving_top20_false_positive_candidates = 9
```

这表示旧 v08 top20 中有 12 个 cells 曾在 v10-beta 中被识别为 possible old DSM-gap false-positive candidates，其中 9 个在 reviewed DSM + v10 UMEP morphology 后离开了 top20。

这是 v10-gamma 最重要的结果。

### 5.2 Strong evidence cases

典型被修正的 old false-positive candidates 包括：

```text
TP_0116
TP_0849
TP_0985
TP_0984
TP_0638
TP_0027
TP_0923
TP_0876
TP_0820
```

这些 cells 在旧 v08 ranking 中属于 top hazards，但 v10-beta 已经显示它们在旧 DSM 中 building completeness 极低或为 0，而 v10 reviewed DSM 中 building density 大幅增加。

v10-gamma 进一步显示：它们在 corrected UMEP morphology 下不再全部保持 top20 status。

这支持以下结论：

> 旧 v08/v09 hazard ranking 的一部分 top hotspots 是 DSM coverage gap 造成的 artificial open-space signal。

### 5.3 Remaining old false-positive candidates in top hazard set

并不是所有 false-positive candidates 都离开 top20。少数 old DSM-gap candidates 在 v10 中仍保持较高 hazard ranking，例如：

```text
TP_0564
TP_0565
TP_0986
TP_0315
```

这类 cases 不应被简单解释为“修正失败”。更合理的解释是：

```text
这些 cells 过去确实受 DSM gap 影响，
但 corrected morphology 后仍可能具有高 SVF、低 shade、道路/硬化空间暴露等真实热危险因素。
```

因此，它们应作为 QGIS manual validation 的重点对象，而不是自动剔除。

---

## 6. New v10 top hazards

### 6.1 Newly entering cells

v10 新进入 top20 的 cells 包括：

```text
TP_0120
TP_0171
TP_0315
TP_0344
TP_0373
TP_0572
TP_0766
TP_0888
TP_0916
TP_0973
```

这些 cells 需要在 QGIS 中进行视觉检查，重点确认：

```text
- 是否具有较高 SVF；
- 是否 shade_fraction 较低；
- 是否为道路/硬化空间/开阔公共空间；
- 是否没有明显 overhead / covered walkway 未建模问题；
- 是否位于 reviewed DSM height/geometry uncertainty 较低区域。
```

### 6.2 Suggested interpretation

如果这些新 cells 在卫星图和 QGIS 中更符合真实高热暴露形态，则 v10 top20 可以解释为：

> reviewed building morphology corrected the old false positives and surfaced a more credible high-hazard set.

如果某些进入 cells 仍受 overhead、transport、height uncertainty 或 vegetation gap 影响，则应标记为 v10-gamma QA candidates，而不是直接进入 final map。

---

## 7. Special QA notes

### 7.1 TP_0945

comparison report 显示 TP_0945 出现极端下降：

```text
old hazard rank = 48
v10 hazard rank = 986
hazard_score_v10 = 0
```

这可能与 reviewed DSM 下该 cell 几乎 fully building-covered、缺乏 valid open pixels 有关。grid merge QA 中也显示 v10 `svf` 有 1 个 missing。

建议将 TP_0945 标记为：

```text
fully-built / no-open-pixel QA case
```

它不是主要错误，但需要在方法里说明：open-pixel hazard model 对全建筑覆盖 cell 可能返回 0 或 missing hazard。

### 7.2 Hazard rank vs risk-priority rank

v10-gamma comparison 使用的是：

```text
hazard_score
```

因此它是 **physical heat-hazard ranking**。

不要把 `v10_gamma_hotspot_ranking_with_grid_features.csv` 中的 `rank` 列直接当成 hazard rank。该 rank 很可能按 `risk_priority_score` 或 pipeline 默认 ranking 输出，和纯 hazard rank 不完全一致。

报告和地图中必须区分：

```text
hazard_rank_v10        = physical heat hazard
risk_rank_v10          = intervention priority / social-risk scenario
```

---

## 8. Revised findings

### Finding 1 — Reviewed DSM materially changes morphology

v10 reviewed height-QA DSM 将平均 building density 从 v08 的 0.0659 提高到 0.2148，同时使平均 open-pixel SVF 从 0.4906 降到 0.3800。该结果说明 v08/current DSM 系统性低估了建筑覆盖，并高估了开阔天空暴露。

### Finding 2 — v10 top hazard set is corrected, not randomised

v08-v10 Spearman correlation 为 0.9705，说明全局空间结构仍稳定；但 top20 overlap 只有 10/20，说明高优先级 hazard set 被实质性修正。

### Finding 3 — Old DSM-gap false positives are mostly corrected downward

旧 v08 top20 中有 12 个 DSM-gap false-positive candidates，其中 9 个离开 v10 top20。这是 v10-gamma 最强证据，支持 v0.9 audit 的核心结论：旧 top hazard set 部分由 building DSM coverage gap 推高。

### Finding 4 — Some formerly suspicious cells remain physically hot

少数旧 false-positive candidates 在 v10 corrected morphology 下仍保持高 hazard。这说明它们可能在 footprint gap 修正后仍具有真实热暴露特征。它们应进入 manual validation，而不是自动剔除。

### Finding 5 — v10-gamma is a corrected hazard layer, but not final operational model

v10-gamma 修正了 building DSM coverage gap，并重跑了 UMEP SVF/shadow，但仍未解决 overhead infrastructure、vegetation transmissivity sensitivity、多日期 solar geometry、selected-tile SOLWEIG/Tmrt validation 等问题。

---

## 9. Limitations

### 9.1 No explicit overhead DSM yet

v10-gamma building DSM 排除了 confirmed canopy / overhead candidates，但还没有把 elevated roads、covered walkways、station canopies、pedestrian bridges 作为独立 overhead shade layer 建模。

这意味着：

```text
- building DSM 更干净；
- 但 overhead shade 仍可能被低估；
- 某些 ground-level heat exposure 可能仍被高估。
```

### 9.2 Vegetation DSM unchanged

v10-gamma 继续使用 v08 vegetation DSM 和 v08 vegetation transmissivity assumptions。这是为了 fair v08-v10 comparison，但并未解决 canopy-height / transmissivity uncertainty。

### 9.3 No SOLWEIG/Tmrt rerun yet

v10-gamma 只重跑 UMEP SVF / shadow，不是完整 SOLWEIG/Tmrt rerun。因此它可以修正 hazard engine 所需的 morphology features，但还没有重新验证 Tmrt-level physical exposure。

### 9.4 Height imputation uncertainty remains

虽然 v10-beta.1 修正了明显异常的 height/geometry cases，但大量 OSM/manual buildings 仍依赖 default height 或 medium-confidence imputation。未来 SOLWEIG rerun 前仍需 selected-cell height QA。

### 9.5 One missing open-pixel SVF

v10 merge QA 中 `svf` 有 1 个 missing。该 case 应解释为 fully-built / no-open-pixel situation，而不是系统性 UMEP failure。

---

## 10. Recommended next steps

### Step 1 — QGIS validation of ranking changes

优先人工检查三类 cells：

1. old false positives leaving top20:
   ```text
   TP_0116, TP_0849, TP_0985, TP_0984, TP_0638,
   TP_0027, TP_0923, TP_0876, TP_0820
   ```

2. old false positives still high:
   ```text
   TP_0564, TP_0565, TP_0986, TP_0315
   ```

3. entering v10 top20:
   ```text
   TP_0120, TP_0171, TP_0344, TP_0373, TP_0572,
   TP_0766, TP_0888, TP_0916, TP_0973
   ```

### Step 2 — Produce v10-gamma visual maps

建议输出：

```text
v10 hazard map
v08-v10 rank-shift map
old false-positive candidates map
entering/leaving top20 map
SVF delta map
shade delta map
```

### Step 3 — v10-delta selected SOLWEIG rerun

选几个代表性 cells 重跑 SOLWEIG/Tmrt：

```text
1 old false-positive leaving top20
1 old false-positive still top20
1 new v10 hotspot
1 clean shaded reference
1 overhead/transport diagnostic case
```

目标是验证 v10 hazard ranking 的 Tmrt 物理合理性。

### Step 4 — Overhead DSM sensitivity

构建独立 overhead layer，而不是把 overhead 混进 building DSM：

```text
covered walkways
station canopy
pedestrian bridges
elevated rail / viaducts
```

然后做 sensitivity：

```text
building + vegetation only
vs
building + vegetation + overhead shade layer
```

---

## 11. Suggested final wording

可以在 dissertation / portfolio 中这样描述 v10-gamma：

> v10-gamma reran UMEP SVF and shadow using the reviewed height-QA building DSM while keeping the vegetation DSM and UMEP parameters consistent with v08. The reviewed DSM reduced mean open-pixel SVF from 0.491 to 0.380 and increased mean 10–16 shade fraction from 0.423 to 0.466. The resulting v10 hazard ranking remained globally correlated with v08 (Spearman = 0.9705), but the top-20 hazard set changed substantially, with only 10/20 overlap. Of the 12 old top-20 DSM-gap false-positive candidates, 9 left the v10 top-20. This supports the v0.9 audit finding that the old hazard ranking was partly driven by building-DSM coverage gaps. A small subset of old false-positive candidates remained high hazard under v10, suggesting they may be genuinely hot even after morphology correction.

中文版本：

> v10-gamma 使用 reviewed height-QA building DSM 重新计算 UMEP SVF 和 shadow，同时保持 vegetation DSM 和 UMEP 参数与 v08 一致。reviewed DSM 将平均 open-pixel SVF 从 0.491 降至 0.380，并将 10–16 点平均 shade fraction 从 0.423 提高到 0.466。v10 hazard ranking 与 v08 在全体 cell 上仍高度相关（Spearman = 0.9705），但 top20 发生明显重排，重合仅为 10/20。旧 v08 top20 中有 12 个 DSM-gap false-positive candidates，其中 9 个在 v10 中离开 top20。这支持 v0.9 audit 的核心发现：旧 hazard ranking 部分受 building DSM coverage gaps 驱动。少数 old false-positive candidates 在 v10 中仍保持高 hazard，说明它们可能在 corrected morphology 下仍是真实高热区域。

---

## 12. Final status

v10-gamma status:

```text
PASSED as reviewed-DSM UMEP morphology rerun and hazard-ranking comparison.
```

It should be considered:

```text
first data-integrity-corrected hazard ranking layer
```

but not yet:

```text
final operational warning model
complete SOLWEIG/Tmrt validation
overhead-aware pedestrian shade model
```
