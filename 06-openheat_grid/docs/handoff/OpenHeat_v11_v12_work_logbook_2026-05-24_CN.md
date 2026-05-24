# OpenHeat-ToaPayoh v1.1 / v1.2 工作日志与交接手册

**日期**：2026-05-24  
**项目路径**：`Urban-Analytics-Portfolio/06-openheat_grid`  
**当前重点**：从 v1.1 formal closeout 进入 v1.2 SOLWEIG-derived local radiative modifier pilot。  
**用途**：给未来的自己、新对话窗口、Codex/Claude/GPT 接手时使用，避免忘记 v1.1/v1.2 做过什么、文件在哪、坑在哪里、下一步该做什么。

---

## 0. 一页 TL;DR

当前项目已经完成了 v1.1 的核心 closeout，并且 v1.2 已经从目标定义推进到 SOLWEIG Core 8 pilot 的 base + overhead 全矩阵。

```text
v1.1 GHA archive lane:
  ✅ GitHub Actions archive continuity lane 已实现并通过 manual smoke。
  ✅ tabulate dependency bug 已修。
  ✅ GHA 可写 live_chunks / manifest / commit 回 repo。
  ⏳ cron stability 仍应持续观察。

v1.1 beta formal:
  ✅ 17.778-day / 40,419-row frozen snapshot 完成。
  ✅ formal baselines、H10、bootstrap、threshold scan、ablation、diagnostics、formal report、archive quality note 已完成。
  ✅ stale cv_splits bug 已发现并修正/规避。
  ✅ H10 仍成立，M5/M6/M7 在 6 位小数上等价。

v1.1 formula audit:
  ✅ System A raw v09 proxy 公式敏感性审计完成。
  ✅ 发现 raw proxy 结构性低估 / high-tail compression。
  ✅ 简单 globe coefficient 调参无法恢复 31/33°C fixed-threshold crossing。

v1.2-alpha modifier target spec:
  ✅ modifier 目标冻结为 tmrt_p90_c → delta_tmrt_p90_c → m_rad_pct。
  ✅ reference 定义为 same-hour same-scenario median cell-level tmrt_p90_c。
  ✅ candidate manual GIS QA 完成。
  ✅ Core 8 经人工修订。

v1.2-beta SOLWEIG typology pilot:
  ✅ Wave 0 TP0986 h13 base smoke PASS。
  ✅ Wave 1 TP0986/TP0542/TP0059 base 9-run PASS。
  ✅ Core 8 base 40-run PASS。
  ✅ QGIS Wall H/A + SVF 自动化 runner 可用。
  ✅ Core 8 overhead_as_canopy 40-run PASS。
  ✅ TP0542 h15 distribution diagnostic 解释通过：mapped pedestrian-overhead shade case，不是异常。

下一步：
  1. 暂停继续跑模型。
  2. 写 `docs/v12/OpenHeat_v12_SOLWEIG_typology_pilot_interim_findings_CN.md`。
  3. 将 docs/configs/scripts/small summaries 做一次干净 checkpoint。
  4. 再决定是否进入 formal-hot-day forcing QA 或 optional diagnostics。
```

---

## 1. 当前阶段定位

现在不再是 v1.1，也不是刚开始 v1.2-alpha。当前准确位置是：

```text
v1.2-beta SOLWEIG typology pilot — v10-epsilon forcing technical/physical sanity pass completed.
```

注意：这还不是 final local heat map，不是 risk map，不是 surrogate/ML 阶段。当前所有 v1.2-beta 结果都应解释为：

```text
SOLWEIG-derived 100m mixed-cell Tmrt summaries and local radiative modifier evidence.
```

禁止解释为：

```text
local WBGT prediction
validated 100m WBGT
risk map
observed truth
real-time heat warning
```

---

## 2. v1.1 工作回顾

### 2.1 GHA archive continuity lane

本轮先把 archive loop 从本地长跑迁移到 GitHub Actions continuity lane。

关键过程：

```text
1. 初始 workflow 放在错误路径或 working-directory 不对，Actions 页面看不到或无法正确运行。
2. 修正为 repo root `.github/workflows/v11_archive_collector.yml`，内部设置 `working-directory: 06-openheat_grid`。
3. 第一次 run collector once 失败：缺少 `tabulate`。
4. 修复依赖后，manual workflow_dispatch 成功。
5. 成功 manifest 示例：
   rows_fetched = 27
   rows_added = 27
   stations_seen = 27
   api_status = warn
   warnings = Open-Meteo ReadTimeout for S132/S145
6. GHA 成功 commit：`chore(v11): archive collector run ...`
```

代表文件：

```text
.github/workflows/v11_archive_collector.yml
configs/v11/v11_archive_gha_config.json
scripts/v11_archive_gha_collect_once.py
outputs/v11_archive_ops/gha_run_manifest_latest.json
outputs/v11_archive_ops/gha_run_manifest_*.json
```

重要边界：

```text
GHA schedule 是 best-effort cadence，不是 sensor-grade exact 15-minute cadence。
GHA 进入观察期后，本地 archive loop 不要立刻停，至少并行观察一段时间。
```

### 2.2 v1.1 beta formal snapshot 与 formal matrix

冻结 snapshot 时，Windows batch 中 `wmic` 不存在，导致 label 生成出现 `~0,8` 这类坏名字。后续手动 rename 到稳定命名：

```text
data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419.csv
data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_v091.csv
data/calibration/v11/snapshots/v11_pairs_14d_formal_20260524_40419_hourly.csv
```

formal snapshot 核心规模：

```text
total rows = 40,419
official_wbgt_c non-null = 40,389
official_wbgt_c missing = 30
span_days = 17.778
unique_stations = 27
unique_timestamps = 1,497
```

核心 formal 输出目录：

```text
outputs/v11_beta_formal/all_stations/
outputs/v11_beta_formal/no_S142/
outputs/v11_beta_formal/hourly_mean/
outputs/v11_beta_formal/hourly_max/
outputs/v11_beta_formal/diagnostics/
outputs/v11_beta_formal/h10/
```

核心报告：

```text
docs/v11/OpenHeat_17d_archive_quality_note_CN.md
docs/v11/OpenHeat_v11_beta_formal_findings_report_CN.md
docs/v11/OpenHeat_v11_beta_formal_run_log_20260524_CN.md
```

### 2.3 stale `cv_splits` bug

中途发现 formal bootstrap / OOF 里 `all_stations` 与 `no_S142` 只有 4 folds / 5,988 rows 之类异常现象。排查后确认是 stale `cv_splits_csv` 导致使用了旧 split，而不是自动 LOSO。修复/规避后，full LOSO 恢复到：

```text
all_stations: 27 folds / 40,389 rows
no_S142:      26 folds / 38,893 rows
hourly_mean:  27 folds / 10,473 rows
hourly_max:   27 folds / 10,473 rows
```

经验：

```text
formal configs 中不能默默继承 stale cv_splits。
如果是 LOSO formal pass，应明确 auto LOSO 或禁用旧 cv_splits。
```

### 2.4 H10 strict identity check

H10 的目标是确认 morphology / overhead / compact weather 三组在 formal 条件下仍不可区分：

```text
M5_v10_morphology_ridge
M6_v10_overhead_ridge
M7_compact_weather_ridge
```

中途 bug：H10 脚本最初找不到 prediction column，因为 OOF 文件里实际列名是：

```text
prediction_wbgt_c
```

修正 alias 后，H10 通过：metrics 与 OOF predictions 6 位小数一致。结论：

```text
morphology calibration 仍不可识别；不要把 v10 morphology/overhead features 当成已被 station data 校准。
```

### 2.5 Archive diagnostics

`v11_formal_archive_diagnostics.py` 一开始无法推断 timestamp/station columns，因为 snapshot 中时间列是：

```text
timestamp_sgt
timestamp_utc
```

修正后生成：

```text
outputs/v11_beta_formal/diagnostics/OpenHeat_17d_archive_diagnostics_summary.md
outputs/v11_beta_formal/diagnostics/archive_health_summary.json
outputs/v11_beta_formal/diagnostics/event_counts_by_day.csv
outputs/v11_beta_formal/diagnostics/event_counts_by_station.csv
outputs/v11_beta_formal/diagnostics/row_attrition_diagnostic.csv
outputs/v11_beta_formal/diagnostics/station_day_completeness.csv
outputs/v11_beta_formal/diagnostics/timestamp_cadence_diagnostic.csv
```

关键发现：

```text
Top heat-event days: 2026-05-19 / 2026-05-20 等。
S142 高尾贡献仍重要，但 formal 中 ≥33 share 下降到约 35.8%。
GHA cadence 应写成 best-effort schedule。
```

### 2.6 Formula audit

v1.1-beta-formula audit 的目标是解释为什么 formal fixed_31 recall 弱、raw proxy under-predict。

主要文件：

```text
configs/v11/v11_formula_audit_config.example.json
scripts/v11_formula_audit_compare.py
docs/v11/System_A_WBGT_formula_audit_CN.md
outputs/v11_formula_audit/
```

关键结论：

```text
existing_v09_proxy ≡ reconstructed_from_v09_components ≡ k0.0045
提高 globe coefficient 到 k0.0065 只把 MAE 改善约 0.020°C
所有 raw formula variants 的 max 都低于 31°C / 33°C fixed thresholds
mean-bias correction 后仍无 fixed_31 / fixed_33 positives
问题是 high-tail compression / structural under-prediction，不是简单调 globe coefficient 能解决
```

边界：

```text
formula audit 是 companion sensitivity，不 retroactively rewrite v1.1-beta-formal。
Liljegren/PyWBGT route 留给 future formula-v2 implementation validation。
```

---

## 3. v1.2-alpha：modifier target spec

### 3.1 目标定义

v1.2-alpha 冻结了 modifier 的数学定义：

```text
tmrt_p90_c(cell, hour, scenario)
  = 100m cell 内有效 SOLWEIG Tmrt pixels 的 p90

tmrt_ref_p90_c(hour, scenario, reference_domain)
  = 同一 hour / scenario / reference domain 中 cell-level tmrt_p90_c 的 median

delta_tmrt_p90_c
  = tmrt_p90_c - tmrt_ref_p90_c

m_rad_pct
  = delta_tmrt_p90_c 在同一 reference domain 内的 percentile rank
```

主 surrogate future target：

```text
delta_tmrt_p90_c
```

主 hazard-score modifier：

```text
m_rad_pct
```

仍然禁止：

```text
ΔTmrt = ΔWBGT
SOLWEIG Tmrt = local WBGT
hazard = risk
surrogate = observed local calibration
```

代表文件：

```text
docs/v12/OpenHeat_modifier_target_spec_CN.md
docs/v12/modifier_reference_definition_CN.md
docs/v12/modifier_target_validation_checklist_CN.md
configs/v12/v12_modifier_target_config.example.json
data/grid/v12/solweig_typology_cell_candidates.csv
```

### 3.2 文献/外部依据核对

已核对：

```text
WBGT 用作 temporal heat-stress baseline 有 OSHA / Lemke & Kjellstrom 等支持。
SOLWEIG / UMEP 用于 urban radiation / Tmrt spatial variation 有 Lindberg / UMEP 文档支持。
shade / SVF / vegetation / morphology 对 Tmrt 影响有文献支持。
ML surrogate 只能作为 SOLWEIG-derived ΔTmrt / M_rad emulator，不是 observed local WBGT calibration。
hazard 与 risk 分开有 IPCC 风险框架支持。
```

但以下属于 OpenHeat 工程设计选择，不是文献标准答案：

```text
tmrt_p90_c 作为 100m cell 主 summary
same-hour same-scenario median reference
m_rad_pct percentile normalization
8–12 cell typology pilot size
```

所以文档中要写成：

```text
OpenHeat design choice / operational definition
```

不要写成：

```text
literature-proven universal standard
```

---

## 4. v1.2 candidate manual GIS QA

### 4.1 为什么 QA 必要

Codex 初始候选是 feature-screened proposal，不是最终样本。人工 GIS QA 发现很多原始 candidate 的现实语义不适合 Core：

```text
TP0088: 高架桥交汇，车行道主导，不适合作 pedestrian Core。
TP0916: Bishan Depot / 铁轨棚状结构，不适合作 pedestrian Core。
TP0433: 河边纯树林，无明显步道，行人相关弱。
TP0492: PUB Waterworks / grass / tree mixed，行人相关弱。
TP0828: 2020 草地 → 2024 工地 → 2026 棚状建筑/Bishan Ridges，时相冲突严重。
```

随后人工新增/替换：

```text
TP0542: 河边树荫步道，替代 TP0433。
TP0627: 街道峡谷 / 贴墙 / 低SVF走廊，替代 TP0828。
TP0326: 稳定高层住宅小区，替代/优于 TP0857。
TP0208: 学校门口小遮阴走廊，但未被 DSM/overhead layer 表达，因此只是 unmapped micro-shelter diagnostic。
```

### 4.2 mapped overhead vs unmapped micro-shelter

这是本轮最重要的概念澄清之一。

```text
mapped overhead:
  当前 DSM / overhead layer / QGIS processing 中已表达的大型/中型遮挡结构。
  可进入 overhead_as_canopy scenario。

unmapped micro-shelter:
  Google Street View 看到的小型遮阳走廊、门廊、候车棚等，
  但 DSM / overhead / OSM / HDB3D 图层未表达。
  不能作为 base confirmed geometry，也不能进入 canonical overhead_as_canopy。
```

TP0208 属于：

```text
unmapped micro-shelter diagnostic
```

TP0542 后来确认属于：

```text
mapped pedestrian-overhead shade case
```

---

## 5. v1.2 Core 8 最终标签

当前 Core 8 更新版：

| cell_id | final typology | 中文解释 | 当前角色 |
|---|---|---|---|
| TP_0565 | `school_gate_asphalt_road_edge_hot_anchor` | 幼儿园门口 / 柏油道路边界热锚点 | Core |
| TP_0986 | `low_rise_residential_high_exposure_null_control` | 低层分散住宅 / 高暴露 null-control | Core |
| TP_0366 | `school_gate_bus_stop_mixed_waiting_node` | 学校门口 + 公交候车混合等待节点 | Core |
| TP_0542 | `river_edge_shaded_walkway_with_mapped_pedestrian_overhead` | 河边树荫步道 / mapped pedestrian overhead 遮阴样本 | Core |
| TP_0627 | `street_canyon_wall_adjacent_low_svf_corridor` | 街道峡谷 / 贴墙 / 低SVF走廊 | Core |
| TP_0326 | `stable_high_rise_residential_estate` | 稳定高层住宅小区 | Core |
| TP_0059 | `open_paved_hardscape_parking_lot` | 开阔硬质铺装 / 露天停车场诊断样本 | Core with caveat |
| TP_0835 | `wooded_green_space_low_radiative_diagnostic` | 植被覆盖树林 / 低辐射绿地诊断样本 | Core relabelled |

Optional / legacy / drop：

```text
TP0208: optional unmapped micro-shelter diagnostic
TP0802: optional river-edge / station-rail mixed
TP0088: legacy vehicle-overhead stress-test
TP0916: rail/depot overhead diagnostic
TP0433: forest canopy lower-bound, replaced by TP0542
TP0857: conditional newly completed HDB canyon, replaced by TP0326 unless DSM/HDB3D current
TP0492: drop/replace
TP0828: drop/replace due to construction/time-vintage conflict
```

---

## 6. v10 SOLWEIG source-of-truth recovery

### 6.1 Final source-of-truth

v10-epsilon 最终链条已恢复：

```text
building DSM:
  data/rasters/v10/dsm_buildings_2m_augmented_reviewed_heightqa.tif

vegetation DSM:
  data/rasters/v08/dsm_vegetation_2m_toapayoh.tif

overhead canonical layer:
  data/features_3d/v10/overhead/overhead_structures_v10.geojson

forcing:
  data/solweig/v09_met_forcing_2026_05_07_S128_h10.txt
  data/solweig/v09_met_forcing_2026_05_07_S128_h12.txt
  data/solweig/v09_met_forcing_2026_05_07_S128_h13.txt
  data/solweig/v09_met_forcing_2026_05_07_S128_h15.txt
  data/solweig/v09_met_forcing_2026_05_07_S128_h16.txt

execution:
  QGIS Python Console
  processing.run("umep:Outdoor Thermal Comfort: SOLWEIG", params)
```

关键参数：

```text
INPUTMET, not INPUT_MET
LEAF_START = 1
LEAF_END = 366
TRANS_VEG = 3
INPUT_THEIGHT = 25
UTC = 8
flat DEM = all-zero dsm_dem_flat_tile.tif
```

v10 loop 文件：

```text
scripts/v10_epsilon_solweig_loop.py
```

v10 成功证据：

```text
outputs/v10_epsilon_solweig/v10_epsilon_solweig_loop_log.txt
ok=50/50 fail=0/50
50 Tmrt_average.tif outputs
```

### 6.2 v1.2 复用策略

v1.2 不覆盖 v10 输出。v10 只作为 provenance / source-of-truth。

v1.2 输出使用：

```text
data/solweig/v12_typology_tiles/
outputs/v12_solweig_typology_pilot/
```

---

## 7. v1.2 SOLWEIG 自动化 workflow

### 7.1 核心脚本

当前 v1.2 SOLWEIG workflow 相关脚本：

```text
scripts/v12_solweig_provenance_check.py
scripts/v12_solweig_wave0_reuse_v10_qgis.py
scripts/v12_solweig_select_cells.py
scripts/v12_solweig_prepare_rasters.py
scripts/v12_solweig_make_preprocess_manifest.py
scripts/qgis/v12_qgis_preprocess_from_manifest.py
scripts/v12_solweig_check_preprocess_outputs.py
scripts/v12_solweig_qgis_loop.py
scripts/v12_solweig_aggregate_tmrt.py
compare_v12_core8_base_vs_overhead.py
diagnose_v12_tp0542_h15_distribution.py
```

### 7.2 v12 workflow 逻辑

```text
1. v12_solweig_select_cells.py
   从 grid 中生成 Core 8 tile folders、focus_cell.geojson、tile_boundary.geojson。

2. v12_solweig_prepare_rasters.py
   用 v10 reviewed building DSM、v08 vegetation DSM、v10 overhead layer 生成：
   - dsm_buildings_tile.tif
   - dsm_vegetation_tile_base.tif
   - dsm_overhead_canopy_tile.tif
   - dsm_vegetation_tile_overhead.tif
   - dsm_dem_flat_tile.tif

3. v12_solweig_make_preprocess_manifest.py
   生成 Wall H/A + SVF preprocessing manifest。

4. scripts/qgis/v12_qgis_preprocess_from_manifest.py
   在 QGIS Python Console 中自动跑：
   - Wall Height and Aspect
   - Sky View Factor

5. scripts/v12_solweig_check_preprocess_outputs.py
   检查 wall_height、wall_aspect、svfs.zip 是否 ready。

6. scripts/v12_solweig_qgis_loop.py
   在 QGIS Python Console 中跑 SOLWEIG，必须 path-safe absolute resolving。

7. scripts/v12_solweig_aggregate_tmrt.py
   聚合 Tmrt_average.tif 到 cell-level summary，支持 Wave 0 与 Wave 1+ manifest schema。
```

### 7.3 QGIS/UMEP confirmed algorithms

```text
Wall Height and Aspect:
  algorithm = umep:Urban Geometry: Wall Height and Aspect
  params = INPUT, INPUT_LIMIT, OUTPUT_HEIGHT, OUTPUT_ASPECT

Sky View Factor:
  algorithm = umep:Urban Geometry: Sky View Factor
  params = INPUT_DSM, INPUT_CDSM, TRANS_VEG, INPUT_TDSM, INPUT_THEIGHT,
           ANISO, WALL_SCHEME, KMEANS, CLUSTERS, INPUT_DEM,
           INPUT_SVFHEIGHT, OUTPUT_DIR, OUTPUT_FILE

SOLWEIG:
  algorithm = umep:Outdoor Thermal Comfort: SOLWEIG
  params include INPUTMET, INPUT_DSM, INPUT_SVF, INPUT_HEIGHT, INPUT_ASPECT, INPUT_CDSM, INPUT_DEM, OUTPUT_DIR
```

---

## 8. v1.2 SOLWEIG run history

### 8.1 Wave 0 — TP0986 h13 base smoke

```text
cell = TP0986
hour = 13
scenario = base
forcing = v10_epsilon 2026-05-07 S128 h13
source tile = v10 E02
status = PASS
```

Result:

```text
tmrt_mean_c = 60.673
tmrt_p90_c  = 62.4636
qa_status = ok
```

### 8.2 Wave 1 — 3 cells × 3 hours × base

```text
cells = TP0986, TP0542, TP0059
hours = 10, 13, 16
scenario = base
runs = 9
status = PASS
```

Main finding:

```text
TP0542 shaded river walkway much cooler than TP0986 / TP0059.
TP0542 h13 mean = 39.12, p90 = 55.49, max = 62.58, proving mixed-cell p90 value.
```

### 8.3 Core 8 base — 8 cells × 5 hours

```text
runs = 40
status = PASS
Raster exists = 40/40
Focus cell exists = 40/40
qa_status all ok
```

Stable p90 ranking:

```text
TP0986 highest
TP0565 second
TP0059 / TP0627 / TP0366 middle-high
TP0326 middle-low
TP0542 low
TP0835 lowest
```

Important interpretation:

```text
TP0835 is not open grass. It is wooded green-space / low-radiative diagnostic.
TP0542 and TP0326 strongly demonstrate mean–p90 gaps in mixed cells.
```

### 8.4 Overhead smoke — 3 cells × h13

```text
cells = TP0986, TP0059, TP0565
hour = 13
scenario = overhead_as_canopy
runs = 3
status = PASS
```

Findings:

```text
TP0986 p90 delta = 0.000  → null-control works.
TP0565 p90 delta = 0.000  → asphalt road-edge hot anchor unaffected.
TP0059 mean delta = -2.767, p90 delta = -0.176 → mean changes, upper-tail remains.
```

### 8.5 Core 8 overhead — 8 cells × 5 hours

```text
runs = 40
status = PASS
Raster exists = 40/40
Focus cell exists = 40/40
qa_status all ok
```

Main base-vs-overhead findings:

```text
TP0986: overhead delta = 0 across hours.
TP0565: p90 delta = 0 across hours.
TP0835: no change; already strong vegetation shading.
TP0059: mean decreases substantially, p90 changes little.
TP0542: h15 p90 drops sharply due to mapped pedestrian overhead / bridge shade.
```

### 8.6 TP0542 h15 distribution diagnostic

Diagnostic result:

```text
p85: base 37.859 → overhead 37.070   delta -0.789
p90: base 50.729 → overhead 39.148   delta -11.581
p95: base 56.381 → overhead 56.228   delta -0.152
p99/max: nearly unchanged
```

Interpretation:

```text
TP0542 h15 is a valid mapped pedestrian-overhead shade case.
Overhead adds low/intermediate Tmrt pixels and shifts the top-decile boundary.
Extreme hot pixels remain, so p95/p99/max remain nearly unchanged.
This validates p90 as a useful mixed-cell upper-tail target.
```

---

## 9. Bugs encountered and fixes

### 9.1 GHA workflow path / working-directory

Issue:

```text
Actions 页面看不到 workflow 或 workflow 不在 root .github/workflows。
```

Fix:

```text
Move workflow to repo root `.github/workflows/`.
Use `working-directory: 06-openheat_grid`.
```

### 9.2 Missing tabulate in GHA

Issue:

```text
ImportError: No module named tabulate
```

Fix:

```text
Add tabulate dependency in workflow install step.
```

### 9.3 Windows `wmic` missing during snapshot

Issue:

```text
'wmic' 不是内部或外部命令
snapshot label became ~0,8 / weird names
```

Fix:

```text
Manually rename frozen snapshots to stable names.
Future: replace wmic timestamp logic with Python datetime.
```

### 9.4 `ren` failed on `~0,8`

Issue:

```text
Windows cmd special handling of `~` substring syntax caused command syntax error.
```

Fix:

```text
Use quoted paths or PowerShell/Python rename.
```

### 9.5 One-line Python command pasted with backslash failed in Windows cmd

Issue:

```text
SyntaxError: unexpected EOF
Windows cmd does not treat backslash as multiline continuation.
```

Fix:

```text
Use .py script or single-line semicolon syntax carefully.
```

### 9.6 stale `cv_splits_csv`

Issue:

```text
LOSO unexpectedly only 4 folds / 5,988 rows in some bootstrap/checks.
```

Fix:

```text
Disable stale cv_splits; force auto LOSO; re-run formal outputs.
```

### 9.7 H10 checker prediction column mismatch

Issue:

```text
checker looked for y_pred/prediction but OOF column was prediction_wbgt_c.
```

Fix:

```text
Add alias / normalize prediction column.
```

### 9.8 Archive diagnostics timestamp inference failed

Issue:

```text
Could not infer timestamp/station columns
```

Fix:

```text
Use timestamp_sgt / station_id explicitly.
```

### 9.9 Git staging accidentally included unrelated zip / .Rhistory

Issue:

```text
05-upgraded-gvi-tool.zip and .Rhistory got staged from repo root.
```

Fix:

```text
git restore --staged :/
Add root .gitignore rules.
Use whitelist git add.
```

### 9.10 Formula audit all raw variants zero predicted positives

Issue:

```text
raw formula confusion matrix at 31/33 was all TP=0.
```

Resolution:

```text
Not script error. All raw variants max below 31°C.
Extended audit with distribution, threshold sweep, bias correction, required shift.
```

### 9.11 QGIS SOLWEIG loop relative path bug

Issue:

```text
QGIS Processing could not find data/solweig/.../dsm_buildings_tile.tif
```

Cause:

```text
Manifest paths were relative; QGIS Processing did not resolve them from repo root.
```

Fix:

```text
Path-safe `v12_solweig_qgis_loop.py`: convert all paths to absolute PROJECT_ROOT paths before processing.run().
```

### 9.12 Aggregator manifest schema bug

Issue:

```text
KeyError: 'tmrt_raster_path'
```

Cause:

```text
Wave 0 manifest had tmrt_raster_path/focus_cell_geojson.
Wave 1+ manifest had output_dir/tile_dir.
```

Fix:

```text
Update `v12_solweig_aggregate_tmrt.py` to infer:
output_dir/Tmrt_average.tif
and tile_dir/focus_cell.geojson
```

### 9.13 Wall/SVF automation parameter discovery

Issue:

```text
Could not safely guess UMEP Wall H/A and SVF algorithm IDs/params.
```

Fix:

```text
Run QGIS discovery + use Processing History.
Final runner uses:
Wall: umep:Urban Geometry: Wall Height and Aspect
SVF:  umep:Urban Geometry: Sky View Factor
```

### 9.14 wallheight vs wall_height naming mismatch

Issue:

```text
QGIS history used wallheight.tif / wallaspect.tif, but v10 SOLWEIG loop expects wall_height.tif / wall_aspect.tif.
```

Fix:

```text
Final v12 preprocessing runner outputs wall_height.tif / wall_aspect.tif.
```

---

## 10. Current important file map

### v1.1 reports and evidence

```text
docs/v11/OpenHeat_17d_archive_quality_note_CN.md
docs/v11/OpenHeat_v11_beta_formal_findings_report_CN.md
docs/v11/OpenHeat_v11_beta_formal_run_log_20260524_CN.md
docs/v11/System_A_WBGT_formula_audit_CN.md

outputs/v11_beta_formal/
outputs/v11_formula_audit/
```

### v1.2 alpha spec

```text
docs/v12/OpenHeat_modifier_target_spec_CN.md
docs/v12/modifier_reference_definition_CN.md
docs/v12/modifier_target_validation_checklist_CN.md
configs/v12/v12_modifier_target_config.example.json
data/grid/v12/solweig_typology_cell_candidates.csv
```

### v1.2 beta pilot docs / tables

```text
docs/v12/SOLWEIG_typology_pilot_runbook_CN.md
data/grid/v12/solweig_typology_pilot_cells_revised_v2.csv
data/grid/v12/OpenHeat_v12_pilot_cells_revised_v2_CN.xlsx
configs/v12/v12_solweig_overhead_smoke_h13_manifest.csv
```

### v1.2 SOLWEIG configs/manifests

```text
configs/v12/v12_solweig_typology_config.example.json
configs/v12/v12_solweig_wave0_reuse_v10_manifest.csv
configs/v12/v12_solweig_core8_run_matrix_planned.csv
configs/v12/v12_solweig_preprocess_wave1_base_manifest.csv
configs/v12/v12_solweig_preprocess_core8_base_manifest.csv
configs/v12/v12_solweig_preprocess_core8_overhead_manifest.csv
configs/v12/v12_solweig_wave1_base_manifest.csv
configs/v12/v12_solweig_core8_base_manifest.csv
configs/v12/v12_solweig_core8_overhead_manifest.csv
```

### v1.2 scripts

```text
scripts/v12_solweig_provenance_check.py
scripts/v12_solweig_wave0_reuse_v10_qgis.py
scripts/v12_solweig_select_cells.py
scripts/v12_solweig_prepare_rasters.py
scripts/v12_solweig_make_preprocess_manifest.py
scripts/qgis/v12_qgis_preprocess_from_manifest.py
scripts/v12_solweig_check_preprocess_outputs.py
scripts/v12_solweig_qgis_loop.py
scripts/v12_solweig_aggregate_tmrt.py
compare_v12_core8_base_vs_overhead.py
diagnose_v12_tp0542_h15_distribution.py
```

### v1.2 outputs

```text
outputs/v12_solweig_typology_pilot/provenance/
outputs/v12_solweig_typology_pilot/wave0_summary/
outputs/v12_solweig_typology_pilot/wave1_base_summary/
outputs/v12_solweig_typology_pilot/core8_base_summary/
outputs/v12_solweig_typology_pilot/overhead_smoke_summary/
outputs/v12_solweig_typology_pilot/core8_overhead_summary/
outputs/v12_solweig_typology_pilot/core8_overhead_summary/tp0542_h15_distribution/
```

### Heavy local artifacts: do not commit

```text
*.tif
*.tiff
data/rasters/**/*.tif
data/solweig/v12_typology_tiles/**/dsm_*.tif
data/solweig/v12_typology_tiles/**/wall_*.tif
data/solweig/v12_typology_tiles/**/svf_*/
data/solweig/v12_typology_tiles/**/solweig_*/
outputs/v12_solweig_typology_pilot/**/Tmrt_average.tif
raw archive
large hourly forecast CSV
OOF prediction CSVs
```

---

## 11. Current next actions

Do this next:

```text
1. Write interim findings note:
   docs/v12/OpenHeat_v12_SOLWEIG_typology_pilot_interim_findings_CN.md

2. Include results from:
   - wave1_base_summary
   - core8_base_summary
   - core8_overhead_summary
   - core8_base_vs_overhead_delta_report.md
   - tp0542_h15_distribution_diagnostic.md
   - revised_v2 pilot table

3. Do not run more SOLWEIG until the interim note is reviewed.

4. After note review, decide one of:
   A. small Git checkpoint;
   B. formal-hot-day forcing QA;
   C. optional diagnostics;
   D. pilot closeout package.
```

Recommended next document outline:

```text
# OpenHeat v1.2-beta SOLWEIG Typology Pilot Interim Findings

1. Scope and claim boundary
2. Source-of-truth recovery from v10-epsilon
3. Core 8 manual QA and final labels
4. Run matrix summary
5. Base scenario results
6. Overhead_as_canopy results
7. TP0542 h15 distribution diagnostic
8. What p90 tells us that mean/max do not
9. Mapped overhead vs unmapped micro-shelter
10. Bugs fixed and pipeline automation status
11. Current limitations
12. Next development decisions
```

---

## 12. Handoff prompt for a new AI conversation

Copy/paste this into a new window if needed:

```text
You are helping with OpenHeat-ToaPayoh in Urban-Analytics-Portfolio/06-openheat_grid.

Current state:
- v1.1 formal closeout is completed.
- v1.1 formula audit is completed and found raw v09 proxy high-tail compression.
- v1.2-alpha modifier target spec is completed: target = tmrt_p90_c, delta_tmrt_p90_c, m_rad_pct.
- v1.2-beta SOLWEIG typology pilot has completed under v10-epsilon forcing:
  Wave 0 TP0986 h13 base PASS;
  Wave 1 TP0986/TP0542/TP0059 base 9-run PASS;
  Core 8 base 40-run PASS;
  Core 8 overhead_as_canopy 40-run PASS;
  TP0542 h15 distribution diagnostic PASS / interpretable.

Current Core 8:
TP0565 school_gate_asphalt_road_edge_hot_anchor
TP0986 low_rise_residential_high_exposure_null_control
TP0366 school_gate_bus_stop_mixed_waiting_node
TP0542 river_edge_shaded_walkway_with_mapped_pedestrian_overhead
TP0627 street_canyon_wall_adjacent_low_svf_corridor
TP0326 stable_high_rise_residential_estate
TP0059 open_paved_hardscape_parking_lot
TP0835 wooded_green_space_low_radiative_diagnostic

Important boundaries:
- Do not call results local WBGT.
- Do not call hazard risk.
- Do not train surrogate yet.
- Do not run more SOLWEIG until interim findings note is written/reviewed.
- Distinguish mapped overhead from unmapped micro-shelter.
- Do not commit .tif, svf folders, wall rasters, raw SOLWEIG outputs, raw archive, or OOF predictions.

Next task:
Write docs/v12/OpenHeat_v12_SOLWEIG_typology_pilot_interim_findings_CN.md using existing summary outputs, especially core8_base, core8_overhead, base-vs-overhead delta, and TP0542 h15 distribution diagnostic.
```

---

## 13. Final status snapshot

```text
Project position after this 10-hour session:

v1.1:
  formal evidence complete;
  formula audit complete;
  GHA archive lane implemented / observing.

v1.2-alpha:
  target spec complete;
  candidate manual QA complete;
  Core 8 revised.

v1.2-beta:
  v10-epsilon forcing pilot technical/physical sanity complete;
  QGIS preprocessing and SOLWEIG automation hardened;
  Core 8 base + overhead complete;
  TP0542 distribution diagnostic interpretable.

Immediate next:
  write interim findings note;
  then checkpoint docs/config/scripts/small summaries;
  then decide formal-hot-day forcing QA vs optional diagnostics.
```
