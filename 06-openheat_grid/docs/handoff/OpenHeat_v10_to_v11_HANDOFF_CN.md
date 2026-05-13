# OpenHeat-ToaPayoh 项目交接文档：v10 → v11

> 版本：2026-05-10 交接版  
> 项目目录：`C:\Users\CloudStar\Documents\GitHub\Urban-Analytics-Portfolio\06-openheat_grid`  
> 当前建议状态：**v10 sprint 基本完成，进入 v11 archive / calibration / ML handoff 阶段**  
> 适用场景：迁移到新的 ChatGPT 对话窗口、新 AI 助手接手、GitHub 项目整理、后续 v1.1 开发。

---

## 0. 给新对话窗口的超短提示词

把下面这一段直接粘给新 AI，可以让它快速进入状态：

```text
我在开发 OpenHeat-ToaPayoh，一个基于 Toa Payoh 100m grid 的城市热风险建模项目。当前已经完成 v10 sprint：

1. v0.9 audit freeze：发现旧 HDB3D+URA building DSM coverage gap 会制造 false hotspots。
2. v10-alpha / alpha.3：整合 OSM + HDB3D + URA + manual missing buildings，生成 reviewed augmented building DSM。
3. v10-beta / beta.1：重算 building morphology，识别 old DSM-gap false-positive candidates，做 height/geometry correction。
4. v10-gamma：用 reviewed height-QA DSM 重跑 UMEP SVF / shadow，生成 reviewed-DSM base hazard ranking，并做 v08 vs v10 ranking comparison。
5. v10-gamma robustness：修正 TP_0315 分类、处理 false-positive candidate circularity、做 dense-cell sanity check。
6. v10-delta：建立 overhead infrastructure layer，做 overhead-shade sensitivity ranking，发现 v10-gamma top set 对高架/连廊/车站遮罩高度敏感。
7. v10-epsilon：5 selected cells × 2 scenarios × 5 hours 的 SOLWEIG physical validation，验证 v10-delta overhead sensitivity 的方向，确认 TP_0565 / TP_0986 是 confident hot anchors，TP_0088 / TP_0916 是 overhead-confounded/saturated cases。

现在准备进入 v1.1/v11：archive QA + calibration baseline + ML residual learning。请先基于 handoff doc 理解项目，不要直接跳深度学习；ML 应定位为 physics proxy residual learning + uncertainty，而不是替代 Open-Meteo 或 WBGT/UTCI 公式。
```

---

## 1. 项目一句话定位

**OpenHeat-ToaPayoh** 是一个使用开放数据、UMEP/SOLWEIG、实时/历史气象 archive、100m grid morphology 和后续 physics-informed ML calibration 的 tropical urban heat-risk modelling pipeline。

当前 v10 的核心贡献不是“生成一张最终热图”，而是构建了一个完整的：

```text
audit → correct → validate
```

方法闭环：

```text
发现旧 building DSM coverage gap
→ 修复 augmented/reviewed DSM
→ 重跑 UMEP morphology 和 hazard ranking
→ 识别 overhead infrastructure confounding
→ 用 selected-cell SOLWEIG 物理验证 sensitivity 方向
```

---

## 2. 当前版本状态总览

### v0.6–v0.8：早期系统与风险场景

早期已经完成：

- Open-Meteo / NEA live API pipeline。
- thermal index / WBGT proxy / UTCI / heatstress forecast。
- Toa Payoh 100m grid features。
- v0.8 UMEP-with-vegetation morphology merge。
- v0.8 risk scenarios：hazard-only、conservative conditioned、social conditioned、candidate policy。

这些版本现在主要作为 **历史 baseline** 和 **v10 对比对象**。

---

### v0.9：calibration + SOLWEIG + audit freeze

v0.9 做过几件重要事情：

1. 使用 24h archive 做 calibration pilot。
2. 讨论 M1/M2/M3/M4 calibration：global bias、linear proxy、weather/radiation/inertia features。
3. 做 threshold scan extension。
4. 做 selected-tile SOLWEIG。
5. 发现 building DSM gap 和 overhead issue。
6. 最终 freeze v0.9：旧 hazard ranking 不再被当作 ground truth。

v0.9 的意义：

```text
它不是最终模型，而是发现数据完整性问题和物理建模缺口的 audit checkpoint。
```

---

### v10-alpha：Augmented DSM pilot

目标：修复旧 building DSM coverage gap。

主要内容：

- 整合 HDB3D / URA / OSM building footprints。
- dedup building footprints。
- height imputation。
- rasterize augmented building DSM。
- 注意：building DSM `nodata` 必须是 `None`，地面高度 0 是 valid value，不能设为 nodata。
- alpha.1 修复 min_area config / nodata / OSM height promotion 等问题。
- alpha.2 生成 QA targets。
- alpha.3 应用 manual QA：manual missing buildings、overhead candidates、reviewed DSM。

关键文件：

```text
configs/v10/v10_alpha_augmented_dsm_config.example.json
configs/v10/v10_alpha3_manual_qa_config.example.json
scripts/v10_standardize_building_sources.py
scripts/v10_extract_osm_buildings.py
scripts/v10_deduplicate_building_footprints.py
scripts/v10_assign_building_heights.py
scripts/v10_rasterize_augmented_dsm.py
scripts/v10_alpha3_apply_manual_qa_decisions.py
scripts/v10_alpha3_reviewed_completeness_audit.py
scripts/v10_rasterize_reviewed_dsm.py
```

重要输出：

```text
data/rasters/v10/dsm_buildings_2m_augmented_reviewed.tif
data/rasters/v10/dsm_buildings_2m_augmented_reviewed_heightqa.tif
outputs/v10_dsm_audit/*.md / *.csv
```

注意：`.tif` 不应上传 Git。

---

### v10-beta：basic morphology shift audit

目标：检查 reviewed DSM 是否真的改变了 building morphology，并定位 old DSM-gap false positives。

主要内容：

- old vs reviewed DSM building morphology。
- building density / open fraction / height statistics。
- morphology shift audit。
- height geometry correction：修正 `v10_bldg_000001` / `v10_bldg_000002` 等高度/复合体问题。
- 识别 old DSM-gap false-positive candidates。

关键脚本：

```text
scripts/v10_beta_compute_basic_morphology.py
scripts/v10_beta_build_morphology_shift_audit.py
scripts/v10_beta_morphology_shift_audit.py
scripts/v10_beta1_apply_height_geometry_corrections.py
scripts/v10_beta1_rasterize_heightqa_dsm.py
scripts/v10_run_beta_basic_morphology_pipeline.bat
scripts/v10_run_beta1_height_geometry_pipeline.bat
```

重要输出：

```text
data/grid/v10/toa_payoh_grid_v10_basic_morphology.csv
outputs/v10_morphology/v10_basic_morphology_QA_report.md
outputs/v10_ranking_audit/v10_beta_morphology_shift_audit_report.md
outputs/v10_ranking_audit/v10_old_false_positive_candidates.csv
```

重要解释：

```text
v10-beta 证明旧 high-rank cells 中存在由 building DSM gap 造成的 artificial open-space signal。
```

---

### v10-gamma：reviewed DSM UMEP rerun

目标：用 reviewed height-QA building DSM 重跑 UMEP SVF / shadow，得到 corrected base hazard ranking。

QGIS/UMEP 关键输入：

```text
Building DSM:
data/rasters/v10/dsm_buildings_2m_augmented_reviewed_heightqa.tif

Vegetation DSM:
data/rasters/v08/dsm_vegetation_2m_toapayoh.tif
```

保持 v08 参数一致，不额外启用 K-means wall SVF，确保 v08 vs v10 对比只主要改变 building DSM。

关键脚本：

```text
scripts/v10_gamma_pre_umep_pipeline.bat
scripts/v10_gamma_post_umep_morphology_pipeline.bat
scripts/v10_gamma_run_forecast_and_compare.bat
scripts/v10_gamma_zonal_umep_to_grid.py
scripts/v10_gamma_merge_umep_morphology_to_grid.py
scripts/v10_gamma_finalize_forecast_outputs.py
scripts/v10_gamma_compare_v08_v10_rankings.py
```

重要输出：

```text
data/grid/v10/toa_payoh_grid_v10_umep_morphology_with_veg.csv
data/grid/v10/toa_payoh_grid_v10_features_umep_with_veg.csv
outputs/v10_umep_morphology/*.md
outputs/v10_gamma_comparison/v10_vs_v08_forecast_ranking_comparison.md
outputs/v10_gamma_comparison/v10_vs_v08_rank_comparison.csv
```

核心发现：

```text
v10 ranking 与 v08 全局仍高度相关，但 top20 发生明显重排。
旧 top20 中一批 DSM-gap candidates 离开 top20。
```

---

### v10-gamma robustness audit

目标：让 v10-gamma 结果 dissertation-ready。

处理问题：

- TP_0315 不是 old-top20 retained false positive，而是 entering v10 top20 fp candidate。
- false-positive candidate definition 可能 co-derived，需要明确 circularity。
- 做 FP vs non-FP old-top20 leaving-rate baseline。
- 做 TP_0945 dense / fully-built edge-case sanity check。
- 解释 Spearman 高但 top20 变化大的 nuance。

关键脚本：

```text
scripts/v10_gamma_robustness_audit.py
scripts/v10_run_gamma_robustness_audit.bat
```

重要输出：

```text
outputs/v10_gamma_robustness/v10_gamma_robustness_audit_report.md
outputs/v10_gamma_robustness/v10_gamma_top20_transition_classes.csv
outputs/v10_gamma_robustness/v10_gamma_fp_vs_nonfp_top20_contingency.csv
```

重要措辞：

```text
v10-gamma does not independently prove every diagnosed candidate is false positive.
It shows that old DSM-gap candidates were disproportionately affected by reviewed-DSM morphology correction.
```

---

### v10-delta：overhead infrastructure sensitivity

目标：把高架桥、连廊、人行天桥、车站 canopy 等 overhead infrastructure 从“模型看不见的误差源”转成可量化 layer。

核心原则：

```text
不要把 overhead 直接烧进 building DSM。
高架是 two-layer infrastructure：桥面可能热，桥下行人空间可能阴凉。
```

主要内容：

- 构建 overhead canonical layer。
- per-cell overhead metrics。
- overhead shade proxy。
- overhead sensitivity ranking。
- base v10 vs overhead sensitivity comparison。

关键脚本：

```text
scripts/v10_delta_build_overhead_layer.py
scripts/v10_delta_cell_overhead_metrics.py
scripts/v10_delta_apply_overhead_sensitivity.py
scripts/v10_delta_compare_base_vs_overhead.py
scripts/v10_delta_opacity_sensitivity_sweep.py
scripts/v10_run_delta_overhead_pipeline.bat
scripts/v10_run_delta_overhead_forecast_compare.bat
```

重要输出：

```text
data/features_3d/v10/overhead/overhead_structures_v10.geojson
data/grid/v10/toa_payoh_grid_v10_features_overhead_sensitivity.csv
outputs/v10_overhead_qa/*.md / *.csv / *.geojson
outputs/v10_delta_overhead_comparison/*.md / *.csv
```

核心发现：

```text
Overhead sensitivity 后 top20 overlap 只有 8/20，说明 v10-gamma top set 对 overhead handling 高度敏感。
TP_0088 等 base hotspots 是 overhead-confounded。
TP_0565 / TP_0986 是较稳定的 hot anchors。
```

---

### v10-epsilon：selected-cell SOLWEIG physical validation

目标：用 SOLWEIG v2025a 物理验证 v10-delta overhead sensitivity 的方向。

实验设计：

```text
5 selected cells × 2 scenarios × 5 hours = 50 SOLWEIG outputs

cells:
TP_0565 confident hot anchor 1
TP_0986 confident hot anchor 2 / perfect null control
TP_0088 overhead-confounded rank-1 case
TP_0916 saturated overhead case
TP_0433 shaded reference

scenarios:
base = v10-gamma geometry
overhead = overhead-as-canopy approximation

hours:
10, 12, 13, 15, 16 SGT
```

关键 methodological nuance：

```text
v10-delta overhead metrics are 100m cell-level.
v10-epsilon SOLWEIG tiles are 700m × 700m tile-context.
A focus cell can have zero cell-level overhead but nonzero tile-context overhead.
This is not a contradiction.
```

关键脚本：

```text
scripts/v10_epsilon_select_cells.py
scripts/v10_epsilon_prepare_rasters.py
scripts/v10_epsilon_solweig_loop.py
scripts/v10_epsilon_aggregate_tmrt.py
scripts/v10_epsilon_compare_tmrt.py
scripts/v10_epsilon_pre_solweig_pipeline.bat
scripts/v10_epsilon_post_solweig_pipeline.bat
```

重要输出：

```text
outputs/v10_epsilon_solweig/v10_epsilon_focus_tmrt_summary.csv
outputs/v10_epsilon_solweig/v10_epsilon_base_vs_overhead_tmrt_comparison.csv
outputs/v10_epsilon_solweig/v10_epsilon_aggregate_tmrt_report.md
outputs/v10_epsilon_solweig/v10_epsilon_solweig_comparison_report.md
```

核心结果：

```text
TP_0565 / TP_0986 13:00 Tmrt ≈ 60°C，overhead scenario 几乎不变。
TP_0088 overhead scenario 13:00 Tmrt 大幅下降，支持其 overhead-confounded 解释。
TP_0916 overhead scenario peak reduction 超过 20°C，支持 v10-delta saturation 方向。
TP_0433 13:00 Tmrt ≈ 36°C，是 shaded reference。
```

v10-epsilon 不是 full overhead-aware model，而是 selected-cell physical validation。

---

## 3. v10-final 成果框架

v10 final 不应该只输出一张 single hazard map，而应该输出三类图/表：

### Map A: v10-gamma reviewed-DSM base hazard

含义：

```text
reviewed building DSM + vegetation UMEP morphology 的 base hazard ranking。
```

### Map B: v10-delta overhead sensitivity

含义：

```text
如果 overhead 被作为 ground-level shade source，ranking 如何变化。
```

### Map C: confident / caveated hotspot interpretation map

分类：

```text
confident_hotspot
    v10-gamma high, v10-delta stable/low-overhead, v10-epsilon selected validation if applicable
    examples: TP_0565, TP_0986

overhead_confounded
    v10-gamma high, v10-delta drops, v10-epsilon supports overhead reduction if selected
    examples: TP_0088, TP_0916

building_dsm_gap_corrected
    v08 high, v10-gamma drops, old completeness low

dense_built_edge_case
    fully/near fully built, no open-pixel SVF
    example: TP_0945

shaded_reference
    example: TP_0433
```

---

## 4. 当前 Git 状态和注意事项

当前分支曾经是：

```text
v10-augmented-dsm
```

建议 v10 final 分支：

```text
final/v10-audit-correct-validate
```

曾经 push 失败原因：两个超大 CSV 被误提交：

```text
outputs/v10_delta_overhead_forecast_live/v06_live_hourly_grid_heatstress_forecast.csv  ~378MB
outputs/v10_gamma_forecast_live/v06_live_hourly_grid_heatstress_forecast.csv           ~334MB
```

解决方法：

```bat
git rm --cached -- "outputs/v10_delta_overhead_forecast_live/v06_live_hourly_grid_heatstress_forecast.csv"
git rm --cached -- "outputs/v10_gamma_forecast_live/v06_live_hourly_grid_heatstress_forecast.csv"

echo outputs/v10_delta_overhead_forecast_live/v06_live_hourly_grid_heatstress_forecast.csv>>.gitignore
echo outputs/v10_gamma_forecast_live/v06_live_hourly_grid_heatstress_forecast.csv>>.gitignore
echo outputs/*forecast_live/*hourly_grid_heatstress_forecast*.csv>>.gitignore

git add .gitignore
git commit --amend --no-edit
```

之后确认：

```bat
git ls-tree -r --name-only HEAD | findstr /I "v06_live_hourly_grid_heatstress_forecast"
```

理想情况无输出。

不要把以下文件提交 Git：

```text
*.tif / *.tiff
svfs.zip
data/solweig/
data/rasters/v10/*.tif
data/archive/
data/raw/buildings_v10/
large hourly forecast CSV
patch zip packages
```

---

## 5. 推荐 Git 提交内容

应该提交：

```text
configs/v10/*.json
scripts/v10_*.py
scripts/v10_*.bat
scripts/figures_v4/
docs/v10/
docs/v09_freeze/
docs/handoff/
README/README_V10*.md
src/openheat_v10/
outputs/v10_*/*.md
outputs/v10_*/*.csv
outputs/v10_*/*.geojson
outputs/v10_final_figures_v4/**/*.png
outputs/v10_final_figures_v4/**/*.svg
```

谨慎提交：

```text
data/grid/v10/*.csv / *.geojson
data/features_3d/v10/manual_qa/
data/features_3d/v10/overhead/
```

不要提交：

```text
data/rasters/
data/solweig/
data/archive/
outputs/*forecast_live/*hourly_grid_heatstress_forecast*.csv
```

---

## 6. v11 / v1.1 开发方向

v1.1 定位为：

```text
archive / calibration / ML handoff sprint
```

不要直接跳复杂 ML。先做：

```text
v1.1-alpha: Archive QA + station-weather paired dataset
v1.1-beta: Calibration baselines replay + threshold scan
v1.1-gamma: ML residual learning pilot
v1.1-delta: uncertainty / quantile / conformal prediction
v1.1-epsilon: operational threshold interpretation
```

已经有 v11 alpha/beta package：

```text
configs/v11/v11_alpha_archive_config.example.json
configs/v11/v11_beta_calibration_config.example.json
configs/v11/station_to_cell.example.csv
scripts/v11_alpha_archive_inventory.py
scripts/v11_alpha_build_pairs.py
scripts/v11_alpha_archive_qa.py
scripts/v11_alpha_make_cv_splits.py
scripts/v11_beta_calibration_baselines.py
scripts/v11_beta_threshold_scan.py
scripts/v11_run_alpha_archive_pipeline.bat
scripts/v11_run_beta_calibration_pipeline.bat
```

---

## 7. Archive 的作用

后台 archive 不只是“存数据”。它的作用包括：

1. 验证 raw physics proxy 是否长期有系统偏差。
2. 复现并升级 v0.9 calibration baseline。
3. threshold scan：找到 model score 与 official WBGT≥31 / ≥33 的最佳关系。
4. ML residual learning：让 ML 学 `official_WBGT - physics_proxy`。
5. uncertainty：quantile / conformal / prediction interval。
6. drift monitoring：检查不同天气 regime 下模型稳定性。
7. sensor placement future work：哪里需要新 WBGT station。

ML 不应该替代 Open-Meteo、UTCI/WBGT 公式或 GIS features。最合理位置是：

```text
physics proxy + v10 morphology + overhead + weather regime → ML residual
```

也就是：

```text
final prediction = physics/calibrated proxy + ML_residual
```

不要先上 LSTM / Transformer / GNN。当前 station 数量有限，时间自相关强，容易 overfit。优先：

```text
Ridge / ElasticNet
small RandomForest
LightGBM / XGBoost residual
quantile / conformal uncertainty
```

---

## 8. 新对话最需要上传/提供的文件

如果迁移到新对话，优先上传：

```text
1. 本 handoff doc
2. docs/v10/V10_Integrated_final_findings_report_CN_FINAL_WITH_EPSILON.md
3. docs/v10/V10_EPSILON_SOLWEIG_final_findings_report_CN.md
4. docs/v10/V10_Delta_final_findings_report_CN_REVISED.md
5. docs/v10/OpenHeat_v10_integrated_final_findings_report_CN.md 或最终版 integrated report
6. outputs/v10_epsilon_solweig/v10_epsilon_base_vs_overhead_tmrt_comparison.csv
7. outputs/v10_gamma_robustness/v10_gamma_robustness_audit_report.md
8. outputs/v10_delta_overhead_comparison/v10_base_vs_overhead_sensitivity_comparison.md
9. outputs/v10_final_figures_v4/ 中最终图 PNG/SVG，如需要视觉审图
10. v11 alpha/beta package 或 configs/scripts
```

不需要上传：

```text
large tif
SOLWEIG Tmrt raster
svfs.zip
archive raw full dump
```

除非新任务专门需要 debug raster / QGIS / SOLWEIG。

---

## 9. 当前文件结构建议

推荐保留结构：

```text
06-openheat_grid/
├─ configs/
│  ├─ v10/
│  └─ v11/
├─ scripts/
│  ├─ v10_*.py / .bat
│  ├─ figures_v4/
│  ├─ v11_*.py / .bat
│  └─ create_openheat_transition_package.py
├─ docs/
│  ├─ v09_freeze/
│  ├─ v10/
│  ├─ v10_final/
│  ├─ v11/
│  └─ handoff/
├─ data/
│  ├─ grid/v10/
│  ├─ features_3d/v10/manual_qa/
│  ├─ features_3d/v10/overhead/
│  ├─ rasters/          # local only, heavy
│  ├─ solweig/          # local only, heavy
│  └─ archive/          # local only unless small QA samples
├─ outputs/
│  ├─ v10_dsm_audit/
│  ├─ v10_morphology/
│  ├─ v10_gamma_robustness/
│  ├─ v10_delta_overhead_comparison/
│  ├─ v10_epsilon_solweig/
│  ├─ v10_final_figures_v4/
│  └─ v11_alpha_archive/ / v11_beta_calibration/
└─ qgis/
```

---

## 10. 下一步建议清单

### 立即做

1. 修正 Git 提交中的大文件问题。
2. 成功 push `final/v10-audit-correct-validate`。
3. 打 tag：

```bat
git tag -a v10-final-audit-correct-validate -m "OpenHeat v10 final: reviewed DSM, overhead sensitivity, selected-cell SOLWEIG validation"
git push origin v10-final-audit-correct-validate
```

4. 生成 v10 transition package。

### 然后做

1. 运行 v11-alpha archive QA。
2. 修 `station_to_cell.example.csv`。
3. 检查 event count 和 missingness。
4. 再决定是否跑 v11-beta calibration baseline。

---

## 11. 对新 AI 的注意事项

1. 不要让用户把 heavy raster 全部上传。
2. 不要建议 random train/test split；archive 强自相关，必须 LOSO / blocked-time CV。
3. 不要把 v10-delta 当 final physical model；它是 overhead sensitivity layer。
4. 不要把 v10-epsilon 当 full AOI SOLWEIG；它是 selected-cell physical validation。
5. 不要把 ML 放在替代 physics 的位置；ML 应学习 residual 和 uncertainty。
6. 任何 Git 操作前先检查 staged 是否含大文件。
7. 任何 QGIS/UMEP 操作前确认 DSM nodata：building DSM 0 是 valid ground，不是 nodata。

---

## 12. 一句话总评

当前项目已经完成了 v10 的核心 scientific contribution：

```text
Open data heat-hazard modelling must explicitly audit and correct building DSM completeness and overhead infrastructure confounding.
```

v11 的任务是把这个 corrected spatial hazard framework 接到 archive / calibration / ML residual learning 上，形成：

```text
physics-informed, calibrated, uncertainty-aware heat forecast system.
```
