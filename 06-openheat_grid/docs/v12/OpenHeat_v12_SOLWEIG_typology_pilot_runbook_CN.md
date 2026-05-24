# OpenHeat v1.2-beta SOLWEIG typology pilot runbook

**Document date:** 2026-05-24  
**Project:** OpenHeat-ToaPayoh  
**Stage:** v1.2-beta pilot planning  
**Depends on:** v1.2-alpha modifier target spec  
**Status:** draft runbook for review before execution

---

## 0. 当前定位

本 runbook 用于从 v1.2-alpha 的 target/spec 阶段进入 v1.2-beta 的小样本 SOLWEIG typology pilot。

这一步要做的是：

```text
用 8 个 Core cells 做小样本 SOLWEIG 物理 sanity check，
验证 tmrt_p90_c / delta_tmrt_p90_c / m_rad_pct 这个 modifier target 是否可解释。
```

这一步不是：

```text
不是全域 SOLWEIG
不是 50/100/150 cell 扩展
不是 surrogate / ML
不是 hazard map
不是 risk map
不是 local WBGT prediction
```

---

## 1. Target 继续沿用 v1.2-alpha 定义

主 cell-level SOLWEIG summary：

```text
tmrt_p90_c
```

主 delta target：

```text
delta_tmrt_p90_c = tmrt_p90_c - tmrt_ref_p90_c
```

主 radiative modifier：

```text
m_rad_pct = percentile_rank(delta_tmrt_p90_c)
```

secondary modifier：

```text
m_rad_robust01
```

reference：

```text
same-hour same-scenario median cell-level tmrt_p90_c
```

严禁在本阶段引入：

```text
WBGT_cell = WBGT_A + f(delta_tmrt_p90_c)
```

本阶段所有输出均应解释为：

```text
SOLWEIG-derived local radiative modifier / local radiative penalty
```

而不是：

```text
local WBGT
observed truth
risk
```

---

## 2. Core 8 pilot cells

第一轮 Core 8 建议如下。

| cell_id | 类型 | 中文说明 | 关键 caveat |
|---|---|---|---|
| TP_0565 | school_gate_road_edge_hot_anchor | 幼儿园门口/道路边界混合热锚点 | 100m mixed cell；建筑/道路占比高；可能存在未标注小遮阴 |
| TP_0986 | low_rise_residential_null_control | 低层住宅 clean null-control | 非高人流节点；用于 overhead null-control |
| TP_0366 | school_gate_bus_stop_waiting_node | 学校门口+公交候车混合等待节点 | 100m mixed cell；不称 risk |
| TP_0542 | river_edge_shaded_walkway | 河边树荫步道 | 约 15% 河面；作为 pedestrian shaded reference |
| TP_0627 | street_canyon_wall_adjacent_low_svf | 街道峡谷/贴墙/低SVF走廊 | 稳定建成环境；看街谷方向与建筑遮阴 |
| TP_0326 | stable_high_rise_residential_estate | 稳定高层住宅小区 | 高层小区 mixed cell；不是单一点位 |
| TP_0059 | open_paved_hardscape_parking_lot | 开阔硬质铺装/露天停车场 | 行人相关较弱；作为 hardscape physical test |
| TP_0835 | grass_park_green_mixed | 草地/公园绿地 mixed | Chuan Grove Open Field；植被时相可能变化 |

### Core 8 的目标

Core 8 不追求“纯粹 typology”。100m cell 本来就是 mixed cell。  
Core 8 的目标是覆盖主要物理机制：

```text
hardscape / open sun
school-gate road-edge exposure
waiting-node exposure
tree-shaded walkway
street canyon / wall-adjacent low-SVF
high-rise estate
low-rise residential null-control
grass / park-green mixed surface
```

---

## 3. Optional / diagnostic cells

以下 cell 不进入第一轮 Core 8，但可保留为后续 optional diagnostic。

| cell_id | 类型 | 建议用途 |
|---|---|---|
| TP_0208 | unmapped_micro_shelter_school_gate | 街景可见小型遮阴走廊，但 DSM/overhead layer 未表达；作为 unmapped micro-shelter diagnostic |
| TP_0802 | river_edge_station_rail_mixed | 河边步道 + 河面 + 车站/铁轨 mixed optional |
| TP_0088 | legacy_vehicle_overhead_stress_test | 车行高架交汇；v10 legacy mapped-overhead stress-test，不作为 pedestrian Core |
| TP_0916 | rail_depot_overhead_diagnostic | Bishan Depot 铁轨/棚状结构；rail/depot diagnostic，不作为 pedestrian Core |
| TP_0433 | forest_canopy_lower_bound | 河边纯树林；canopy lower-bound，不作为 pedestrian shaded Core |
| TP_0857 | newly_completed_hdb_canyon_conditional | Bishan Ridges 新建 HDB canyon；仅在 DSM/HDB3D 已包含当前建成体量时使用 |

---

## 4. Mapped overhead 与 unmapped micro-shelter

本项目必须区分：

### 4.1 Mapped overhead

指当前 geometry / overhead layer / DSM 中已经表达的大型结构，例如：

```text
高架桥
铁路棚状结构
大型 pedestrian bridge
已有 overhead polygon
```

这类可进入：

```text
mapped-overhead diagnostic
```

但不一定 pedestrian-relevant。

### 4.2 Unmapped micro-shelter

指 Google Street View / 人工观察中可见，但当前 DSM / overhead / OSM / HDB3D 图层没有表达的小尺度遮阴结构，例如：

```text
学校门口遮阳走廊
小型 covered walkway
门廊
候车棚
临时棚架
```

这类结构：

```text
不作为 base scenario confirmed geometry
不作为 canonical overhead_as_canopy 输入
不阻塞 pilot
必须在 QA / report 中作为 uncertainty 记录
```

如果要测试它的影响，必须另开：

```text
manual_micro_shelter_sensitivity
```

并明确标为 exploratory / manual geometry / not scalable。

### 4.3 对 TP_0208 的处理

TP_0208 不作为 mapped overhead Core cell。  
它保留为：

```text
optional unmapped micro-shelter diagnostic
```

---

## 5. 数据时相与影像不确定性

不同数据源时相不一致：

```text
Google Street View
Google Satellite
URA/HDB3D
DSM / vegetation DSM
OSM / OneMap
```

处理原则：

```text
1. 最新且多源一致的结构，可作为当前 evidence。
2. 旧街景可见但新卫星/模型图层不确认的结构，记录为 temporal microshade uncertainty。
3. 若 cell 的 typology 依赖该结构，则降级为 optional 或替换。
4. 若只是局部 caveat，则保留但在 report 中注明。
```

本 pilot 不追求完整捕捉所有 1-10m 小遮阴设施。

---

## 6. 运行规模

Core 8 full matrix：

```text
8 cells × 5 hours × 2 scenarios = 80 SOLWEIG runs
```

Pilot hours：

```text
10, 12, 13, 15, 16 SGT
```

Scenarios：

```text
base
overhead_as_canopy
```

注意：

```text
overhead_as_canopy 对没有 mapped overhead 的 cells 应接近 null/sensitivity check。
不要把 unmapped micro-shelter 加进 canonical overhead_as_canopy。
```

---

## 7. 推荐执行顺序

不要一开始就跑 80 个。建议分 4 波。

### Wave 0 — 单 cell smoke test

```text
TP_0986 × hour 13 × base
```

目的：

```text
确认 SOLWEIG 输入、坐标、forcing、输出路径、raster读取都正常。
```

### Wave 1 — 三个机制 sanity cells

```text
TP_0986  low-rise null-control
TP_0542  shaded river walkway
TP_0059  open hardscape
```

hours：

```text
10, 13, 16
```

scenario：

```text
base
```

目的：

```text
开阔硬质应比树荫步道更热；
low-rise residential 应在合理中间或偏热；
小时变化应合理。
```

### Wave 2 — Core 8 base

```text
Core 8 × 5 hours × base = 40 runs
```

目的：

```text
验证 base Tmrt_p90 ranking 和 typology plausibility。
```

### Wave 3 — Core 8 overhead_as_canopy

```text
Core 8 × 5 hours × overhead_as_canopy = 40 runs
```

目的：

```text
检查 scenario 是否产生合理变化；
对无 mapped overhead 的 cells 不应出现大幅异常变化；
对已有 mapped overhead / mapped canopy sensitivity 的 cells 变化应可解释。
```

Optional diagnostics 只有在 Core 8 base 结果可解释后再跑。

---

## 8. 输入层 checklist

运行前确认以下图层存在且时相可接受：

```text
100m grid cell polygons
DSM / surface model
DEM / terrain model if required
building footprints / HDB3D or building height source
vegetation DSM / canopy layer
land-cover or ground-cover proxy
mapped overhead layer if used
meteorological forcing
SOLWEIG wall/ground settings
```

必须记录：

```text
input_layer_name
source
vintage / approximate date
CRS
resolution
known caveat
```

---

## 9. Forcing 设置

本 runbook 暂不硬编码 forcing。执行前必须选择一个 `forcing_id`。

优先候选：

```text
v10_epsilon_hot_day_forcing
```

理由：

```text
可连接 v10-epsilon selected-cell validation。
```

可选 formal hot-day forcing：

```text
formal_hot_day_2026_05_19
formal_hot_day_2026_05_20
```

如果使用 formal archive hot day，必须记录：

```text
date_sgt
hour_sgt
temperature
humidity
wind
shortwave
cloud / radiation assumptions
source table
```

不要混用不同 forcing 后直接比较 M_rad，除非 reference 按 forcing/scenario 分组。

---

## 10. 输出目录建议

不要把 SOLWEIG rasters 提交 Git。

本地输出建议：

```text
outputs/v12_solweig_typology_pilot/
  run_manifest.csv
  tmrt_cell_summary_long.csv
  modifier_targets_long.csv
  modifier_reference_table.csv
  modifier_normalization_params.csv
  figures/
  qa/
```

原始 SOLWEIG rasters 建议放：

```text
outputs/v12_solweig_typology_pilot/rasters/
```

并加入 `.gitignore`，不要提交。

---

## 11. Cell-level summary schema

每个 `cell × hour × scenario` 汇总输出：

```text
cell_id
typology_label
pilot_tier
date_sgt
hour_sgt
scenario_id
forcing_id
solweig_run_id
tmrt_mean_c
tmrt_p50_c
tmrt_p75_c
tmrt_p90_c
tmrt_p95_c
tmrt_max_c
n_valid_pixels
valid_pixel_fraction
reference_method
reference_domain_id
tmrt_ref_p90_c
delta_tmrt_p90_c
m_rad_pct
m_rad_robust01
qa_status
qa_notes
```

---

## 12. QA checks after runs

### 12.1 Physical plausibility

Expected patterns:

```text
TP_0059 open hardscape should be hotter than TP_0542 shaded river walkway.
TP_0542 should rank low or lower-middle in M_rad.
TP_0986 should behave as clean null-control.
TP_0627 should show canyon/low-SVF behaviour.
TP_0366 / TP_0565 may show mixed road-edge high p90.
TP_0835 should help distinguish grass/park mean vs p90.
```

### 12.2 p90 vs mean

Check:

```text
tmrt_p90_c - tmrt_mean_c
```

Large gaps may indicate exposure pockets inside mixed cells.

### 12.3 Scenario check

For `overhead_as_canopy`:

```text
No mapped overhead / no relevant canopy:
  delta should be near zero or explainable.

Mapped overhead present:
  Tmrt_p90 should decrease or direction should be physically explained.
```

### 12.4 Failure flags

Flag a run if:

```text
n_valid_pixels very low
valid_pixel_fraction too low
Tmrt values physically implausible
open hardscape cooler than shaded walkway without explanation
scenario changes in wrong direction
hourly rank flips are extreme
raster is misaligned with cell
```

---

## 13. Interpretation rules

Allowed wording:

```text
SOLWEIG-derived local radiative modifier
100m mixed-cell Tmrt_p90
delta_tmrt_p90_c local radiative penalty
m_rad_pct relative local radiative ranking
WBGT-gated local radiative hazard score, later stage only
```

Disallowed wording:

```text
local WBGT prediction
validated 100m WBGT
risk map
real-time heat risk forecast
Tmrt converted to WBGT
SOLWEIG output equals observed truth
```

---

## 14. Do-not-commit list

Do not commit:

```text
*.tif
*.tiff
SOLWEIG rasters
raw SOLWEIG output folders
large hourly forcing CSV
raw archive
formula_comparison_by_row.csv.gz
OOF prediction CSVs
```

Can commit later if small:

```text
runbook
run_manifest.csv
tmrt_cell_summary_long.csv
modifier_targets_long.csv
modifier_reference_table.csv
modifier_normalization_params.csv
QA summaries
small figures
```

---

## 15. Exit criteria for v1.2-beta pilot

v1.2-beta pilot can be considered passed if:

```text
1. Wave 0 smoke test runs successfully.
2. Core 8 base runs complete.
3. Core 8 scenario runs complete or scenario limitations are documented.
4. Tmrt summaries are physically plausible.
5. TP_0059 / TP_0542 / TP_0986 sanity checks are directionally plausible.
6. p90 provides additional information beyond mean.
7. mapped overhead and unmapped micro-shelter are clearly separated.
8. no local-WBGT or risk-map claims are introduced.
```

Only after this should the project consider:

```text
v1.2-beta-scale 50-cell expansion
```

not surrogate training yet.

---

## 16. Next actions

Before running SOLWEIG:

```text
1. Review this runbook.
2. Confirm Core 8 list.
3. Confirm forcing_id.
4. Confirm input layer vintages.
5. Prepare run_manifest.csv.
6. Run Wave 0 only.
7. Inspect Wave 0 raster and summary.
8. Then decide whether to continue Wave 1.
```

Do not start full 80-run matrix before Wave 0 passes.
