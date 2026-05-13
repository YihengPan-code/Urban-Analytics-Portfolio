# OpenHeat-ToaPayoh: Project Synthesis

**Author**: Yiheng Pan
**Date**: 2026-05-11
**Project status**: v1.1-β.1 v2.2 FINAL canonical · archive collector loop active · 14-day formal pass scheduled
**Document version**: Synthesis v1 (first comprehensive umbrella doc)
**Repo**: `Urban-Analytics-Portfolio/06-openheat_grid`
**Conda env**: `openheat`

---

## 0. 关于本文档

### 0.1 这是什么

这是 OpenHeat-ToaPayoh 项目的**第一份 umbrella synthesis**——把从 v0.5 (2026-04) 到 v1.1-β.1 (2026-05) 跨越 13-14 个版本里程碑、127 份 markdown 文档、160+ Python 脚本的项目, 浓缩成**一个统一作者视角、按时间线讲完整故事**的 30 页综述。

它**不重复** detailed findings reports 的内容, 而是**指向**它们。

### 0.2 给谁看

| 读者 | 用什么节奏读 |
|---|---|
| **未来的我** (半年后回来 / EDSML 入学后) | 全文一遍, 重点 §2 personal trajectory + §3 story + §7 roadmap |
| **我的导师 / 可能的协作者** | §1 一句话定位 + §3.4-3.6 v0.9→v10→v11 + §4 architecture + §6 what works/what doesn't |
| **GitHub 访客 / 朋友** | §1 + §9 repo navigation 即可 onboard |

### 0.3 详细内容看哪 — Canonical docs pointer table

本 synthesis 是**第五层** narrative。每一层处理不同的细节深度:

| Layer | Doc | 覆盖范围 | 详细程度 |
|---|---|---|---|
| L1 (this) | **`OpenHeat_ProjectSynthesis_v1.md`** | v0.5 → v11-β.1 全周期 | umbrella narrative |
| L2 | `docs/handoff/OPENHEAT_HANDOFF_CN.md` | v0.6 → v0.9 audit freeze | handoff |
| L2 | `docs/handoff/OpenHeat_v10_to_v11_HANDOFF_CN.md` | v0.6 → v10-ε → v11 启动 | handoff (703 行) |
| L3 | `docs/v09_freeze/32_V09_COMPLETE_WORK_RECORD_CN.md` | v0.9α/β/γ 完整 lab notebook | detailed (34 KB) |
| L3 | `docs/v10/V10_Integrated_final_findings_report_CN_FINAL_WITH_EPSILON.md` | v10 全周期 final findings | detailed (45 KB) |
| L3 | `docs/v11/OpenHeat_v11_beta1_findings_report_CN_v2_2_FINAL.md` | v11-β.1 四轮 audit + 关键 findings | canonical (32 KB) |
| L4 | 17 个 `README/README_V*.md` | per-patch 启动说明 | granular |
| L4 | 90+ 个 `docs/v*/V*_GUIDE_CN.md` | per-feature 实施 guides | granular |

**Reading recipe**: 想全景就读本 doc; 想 v0.9 audit 细节读 L3 v09; 想 v10 SOLWEIG 物理验证读 L3 v10; 想 v11 calibration ladder + 4 轮 audit 读 L3 v11; 想跑某个 patch 读 L4。

### 0.4 维护

- **更新触发**: 14-day formal pass 跑完 (预计 5/25 左右) → 加 §3.7 v1.1-β formal results
- **下一次大改**: v1.1-γ ML pilot 启动 / archive 跨 1 个月 / 出现 v5 重要 audit
- **文档关系图**: 见附录 B

---

## 1. 一段话定位 + 当前状态

### 1.1 一段话

OpenHeat-ToaPayoh 是一个针对新加坡 Toa Payoh HDB 老城区的**fine-scale urban heat-risk prediction system**, 用 100m grid + UMEP 形态学 + Open-Meteo gridded forcing + NEA WBGT 观测 + SOLWEIG 物理验证 + ridge calibration 构建。当前 v1.1-β.1 阶段在做 long-term WBGT archive collection 配合 4 个 calibration model (M0-M7) 的 LOSO 评估, 准备进入 14-day formal pass 后启动 ML residual learning。

### 1.2 现在在哪 (snapshot, 2026-05-11)

```text
┌─────────────────────────────────────────────────────────────────┐
│ Current state: v1.1-β.1 v2.2 FINAL (canonical)                  │
│                                                                  │
│ Archive: 6,372 行 NEA-Open-Meteo paired observations            │
│         15-min cadence × 27 stations × ~4 days                  │
│         → 1,674 hourly buckets after aggregation                │
│                                                                  │
│ Calibration:                                                     │
│   M3 (weather ridge):    LOSO MAE 0.605°C (hourly_mean, 4d)     │
│   M4 (+ inertia lag):    LOSO MAE 0.593°C  (+0.012 vs M3)       │
│   M5/M6 (+ morph):       LOSO MAE 0.631°C  (= M7, audit-proof)  │
│   M7 (compact):          LOSO MAE 0.631°C, F1@31°C = 0.639     │
│                                                                  │
│ Operational primary:                                             │
│   M4 + hourly_max + fixed 31°C threshold                        │
│   P = 0.68, R = 0.59, F1 = 0.63 (no threshold tuning)           │
│                                                                  │
│ Engineering: 4 rounds peer audit, 22 patches, zero collector    │
│              touch across all audit rounds                       │
│                                                                  │
│ Next: archive loop 持续 10+ days → 14-day formal snapshot →     │
│       formal beta pass H1-H11 hypothesis testing →              │
│       conditional ML residual pilot at 30 days                   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 项目**不是**什么

| 不是 | 因为 |
|---|---|
| 一张 final heat map | v10 audit 证明任何 single ranking 都 sensitive to morphology + overhead handling; 当前最稳的是 "Map A base + Map B overhead sensitivity + Map C confident interpretation" 三图框架 |
| 操作级公共健康预警系统 | calibration LOSO MAE ~0.6°C 仍属研究阶段; 14d formal + 30d ML pilot 之前不发部署级 alerting |
| morphology / overhead 没物理影响 | 当前 27-station NEA 网络 + station-level ridge calibration **无法识别** morphology contribution。这是 network sparsity binding constraint, 不是物理结论 |
| Plymouth dissertation 的延伸 | Plymouth diss 是 GEMA × mobile monitoring 行人体验研究; 本项目是 grid-scale 预测系统。**方法论 lineage** 一致 (微气候 + 数据驱动), 但研究问题不同 |

---

## 2. 个人研究 trajectory: 为什么是这个项目

### 2.1 起点: 苏州夏天

我对 climate / urban heat 的关注最早不是来自学术训练, 而是来自一个具体的观察——某年暑假回苏州时, 突然意识到**童年印象里的苏州正在变热**。这不是抽象的气候变化, 是穿过老城区一条特定街道时身体感受到的某种"不对"。

这个感受后来被认知化为**两个相关但不同的问题**:
1. 我家乡这样的中国二线城市, 谁在系统地测、谁在系统地建模?
2. 同样的热, 落在不同的人 (老人、户外工作者) + 不同的城市形态 (老旧多层、现代高层、林荫道) 上, 是不同的故事——但**预警系统通常只有一个城市级阈值**。

### 2.2 中间: 设计院实习 (水-热联系的起源)

本科期间我在某设计院的**海绵城市 / 给排水部门**实习。那段经历最重要的不是学到了具体的 design code, 而是**把"水"和"热"这两件本来分开看的事接上了**:

- 城市高温 → 蒸发降温潜力 → 透水率 + 绿量 + 水体距离
- 城市内涝 → 不透水率 + 排水容量 + 极端降雨 → 也是 climate risk
- 海绵设施 (LID, bioretention, permeable pavement) → 同时缓解热岛 + 内涝

这是后来我研究兴趣里"**urban water-heat nexus**"的起源。OpenHeat 当前阶段只做了 heat side; water side 是未来扩展方向 (§7.3)。

### 2.3 学术训练: Plymouth Y3 dissertation

2026-04 我提交了 BSc dissertation:
> *"Effects of environmental conditions and perceptions on mental wellbeing in urban environments in Plymouth: A mobile monitoring and GEMA study"*

- 方法: mobile environmental monitoring (sound dB(A), PET, GVI, NO2/PM2.5/PM10) + Geographic Ecological Momentary Assessment (GEMA) 同步 subjective appraisal (noise annoyance, thermal discomfort, perceived greenery, perceived AQ)
- 样本: 6 名男性志愿者, 16 POIs, 176 participant-POI observations, 冬季 Plymouth 校园周边两条 transects
- 模型: linear mixed-effects, participant-level random intercepts
- 核心发现: **subjective appraisal 显著 mediate objective conditions → wellbeing 的关系**。加入 appraisal 后, objective coefficients 衰减 69.3-93.3% 并失去统计显著性; appraisal variables 保持显著
- 次级发现: greenery 的 moderation pathway-specific, 主要走 acoustic appraisal route; exploratory reverse-appraisal model 暗示 affect ↔ environment evaluation 可能是双向关系

**这给了 OpenHeat 两件礼物**:
1. **方法论纪律**: 不要只看 objective forcing, 要保留 subjective / behavioral exposure 这条线 (OpenHeat 当前还没接上, 但 §7 有 placeholder)
2. **空间尺度感**: 行人尺度的微气候非常 noisy, 同一 100m grid 内不同站点 PET 可以差 5°C+。这是后来 OpenHeat **不**敢轻易 claim "morphology 物理上没有效果"的认识基础——网络稀疏 ≠ 信号不存在

### 2.4 政策视角: Cooling Toa Payoh 组队项目

差不多同时期, 我参加了一个组队 project: *"Cooling Toa Payoh: A Two-Part Package—Cool Roofs and a Local Heat-Resilient System"*。Focus 在 Toa Payoh HDB 老城区 (1960-70s built, 22.3% 老龄人口, 85k 居民) 的**实际干预**:

- Solution 1: 20 栋老旧 HDB 楼顶 cool paint, 屋顶 -10~15°C / 顶层室内 -1~2°C, ROI ~0.6 年, S$240-760k CapEx
- Solution 2: 4-6 WBGT sensors + 10-15 indoor loggers + 4 priority shade nodes (mature trees + misting shelters) + 9-人本地 Heat Committee → reports to national Mercury Taskforce
- KPI: -10% top-floor heat load (CDH28), <5min unshaded wait, 90% shaded coverage, >80% complaints closed in 7 days

**这给了 OpenHeat 两件礼物**:
1. **AOI 定锚**: Toa Payoh 100m grid 不是抽象 case study, 是有具体居民、具体 vulnerable group (老人、户外工作者、市场/巴士站等候者)、具体可干预对象 (cool roofs + nodes) 的真实地方
2. **预测系统的 use case 终点**: 我做 OpenHeat 不是为了产生学术 ranking, 是为了**给 Solution 2 那种 local Heat Committee 提供 hotspot prioritization 和 alert 输入**。这影响了 v10 的 "Map A + Map B + Map C 三图框架"决定—— committee 需要 confident anchors (TP_0565/TP_0986) 而不是 single ranking

### 2.5 当前定位: 从测量到预测

四件事的累积:

```text
苏州夏天               → 个人 motivation
设计院 sponge city 实习 → urban water-heat nexus 视角
Plymouth GEMA diss      → mobile monitoring + appraisal mediation 方法论
Cooling Toa Payoh       → policy use case + 地点锚定
                          ↓
              OpenHeat-ToaPayoh (技术系统)
              ↓
              ICL EDSML postgrad (2026 fall →)
              ↓
              future research direction: 
                fine-scale urban climate risk prediction
                + water-heat nexus
                + ML/AI for sub-city-scale forecasting
```

OpenHeat 是我目前**技术深度最高**的 personal project, 同时也是面向未来 EDSML 阶段研究方向的**基底案例**——证明用开放数据可以做到 100m × hourly 的 calibration; 同时也踏过了所有 trap: DSM completeness, overhead confounding, station network sparsity, statistical vs practical significance。

我希望 OpenHeat 在 EDSML 阶段能扩展为:
- **同 AOI / 同方法 → Suzhou 复制版** (家乡 case)
- **同 AOI / 加水维度 → water-heat coupled risk** (内涝 + 高温双重 hazard)
- **同 AOI / 加 ML residual** (v1.1-γ pipeline, archive 跨 30+ days 后)
- **同 AOI / 加 behavioral exposure** (借 Plymouth GEMA 经验, 加 walking-trajectory exposure 模型)

任何一条都是 PhD-tractable thesis topic 的种子。

---

## 3. The story so far: v0.5 → v11-β.1

每个版本一段, 描述**解决什么问题、引入什么、留下什么坑**。详细数字 / 脚本路径见 pointer 到 L2/L3 docs。

### 3.1 v0.5 – v0.6.4 (2026-04 → 05 早): live API + WBGT proxy + archive 基础

**解决什么**: 把 "Open-Meteo forecast → WBGT proxy → NEA observation validation" 的最小可运行 pipeline 跑起来。

**做了**:
- 接入 Open-Meteo live forecast (hourly T/RH/wind/SW radiation/cloud)
- 接入 NEA / data.gov.sg WBGT + temperature + RH + wind observations
- 修复 WBGT v1 → v2 API schema (v0.6.2 / v0.6.3 / v0.6.4)
- 把 NEA observation archive 改成 **long format** (每行 = station × variable × timestamp)
- 初步 hotspot ranking + event-window pipeline
- v0.6.4.1: source review hotfix, 修复 WBGT-only matching / wind cap / GVI cap / park-cooling decay / Tmrt low-SVF wall longwave / calibration pairing 6 个问题

**留下什么 / 关键决策**:
- ✅ Long-format archive: 后续 v0.7-v11 都受益, 是 schema 决策
- ✅ Official WBGT 用于 **calibration / validation**, 不重新计算成另一个 WBGT
- ⚠️ Toa Payoh grid 是 **sample/synthetic** features, 不是真实街区
- ⚠️ `tmrt_proxy_c` / `wbgt_proxy_c` 是 screening proxy, 不是 SOLWEIG/UMEP

**Pointer**: `docs/01_V06_LIVE_API_AND_CALIBRATION_GUIDE_CN.md` + `README_CN.md` (top-level)

---

### 3.2 v0.7 / v0.7.1 (2026-05 早): 真实 100m grid + vulnerability/exposure

**解决什么**: 从 sample grid 转向真实 Toa Payoh 100m grid + 加入人口/暴露维度。

**做了**:
- 真实 100m grid (Toa Payoh AOI 984 cells)
- URA / NParks / road / park / land-use features
- GEE 导出: GHSL building height, Dynamic World tree/grass/water/built-up, Sentinel-2 NDVI
- 修复 `impervious_fraction` 过高
- **v0.7.1 加 vulnerability + outdoor exposure** (Subzone 老龄/儿童比例, bus stop / MRT exit / sports facility 行人密度, hawker / eldercare / preschool 节点)
- 定义 `vulnerability_score_v071` + `outdoor_exposure_score_v071`
- hazard-conditioned **risk ranking** (跟 hazard-only ranking 分开)

**留下什么**:
- ✅ `data/grid/toa_payoh_grid_v07_features_beta_final.csv` (基础 grid features file)
- ✅ Hazard ranking vs risk ranking 分开解释——v07_071 起这个 distinction 一直保持
- 🔑 **关键洞察**: top hazard cells 倾向于 low green / low shade / high road_fraction / high SVF 的 open/paved cells——physical 直觉对了, 但当时还不知道这部分高 SVF 是 building DSM gap 造成的 (v0.9 才发现)
- ⚠️ `impervious_fraction` 修复后 ranking 不变, 说明它主要是 diagnostic feature, 不是 main rank driver

**Pointer**: `docs/13_V07_GRID_FEATURES_PIPELINE_CN.md` + `docs/16_V071_RISK_EXPOSURE_GUIDE_CN.md`

---

### 3.3 v0.8 (2026-05 中): UMEP morphology layer (第一次有物理深度)

**解决什么**: 把 grid features 从 land-use proxies 升级为 UMEP-based physical morphology.

**做了**:
- Building DSM: HDB3D + URA 2m 分辨率
- Vegetation DSM: ETH GlobalCanopyHeight 2020 10m → 2m bilinear
- UMEP SVF + shadow + WBGT proxy
- 固定在 2026-03-20 春分 + 等向天空 + vegetation transmissivity 3% + trunk zone height 25%
- Building + canopy SVF/shade merge

**留下什么**:
- ✅ UMEP morphology 是后续 v0.9-γ + v10 epsilon SOLWEIG 的基础
- ✅ 三种 risk scenarios (hazard-only, conservative conditioned, social conditioned, candidate policy) 引入
- ⚠️ Building DSM 没有人审过——后来证明这是 v0.9 audit freeze 的根本原因

**Pointer**: `docs/21_V08_UMEP_WITH_VEGETATION_MERGE_FORECAST_CN.md` + `docs/23_V08_RISK_SCENARIOS_CN.md`

---

### 3.4 v0.9 α/β/γ (2026-05-07 → 05-08): calibration + SOLWEIG + **大转折 audit freeze** 🌟

**这是项目第一个重要转折点。**

**v0.9-α (calibration data foundation, 5/7 02:00 → 5/8 02:03 SGT)**: 24 小时 archive loop, 15-min cadence, 96 archive runs, 27 NEA WBGT stations, **2,564 paired observations**。这是 v0.9-β / v10 / v11 三个阶段的 ground truth dataset 起点。

**v0.9-β (calibration M1-M4)**: 在 2,564 pairs 上跑非-ML calibration ladder。
- M1 global bias correction
- M2 linear proxy
- M3 weather + radiation ridge regression
- M4 + thermal inertia (1h/2h SW lag, 3h SW mean, dT/dt, period sin/cos)
- LOSO + time_block CV
- **核心数字**: M3 LOSO MAE = 0.595°C, M4 ≈ 0.595°C (24h 单日 inertia 没发挥)
- **副产品**: M0 raw proxy bias = -1.140°C (proxy 系统性 under-predict)
- Threshold scan: WBGT ≥ 31°C event detection 在 calibrated model scores 上需要**比 31°C 低**的 decision threshold

**v0.9-γ (SOLWEIG selected-tile)**: 在 6 个选定 tile (T01-T06) 上跑 UMEP-SOLWEIG。**目的不是生成最终热图, 是物理验证 morphology proxy**。

**🌟 关键发现 (v0.9-γ 后期 audit)**: 旧 HDB3D + URA building DSM 相对 OSM-mapped building area 只有 **25.8% completeness**。具体:

```text
T06 (overhead-confounded tile):
  OSM 在 buffer 内 map 215 buildings, 67,456 m² building area
  HDB3D+URA DSM 在 buffer 内 0% completeness
  → SOLWEIG 把这片读成 "real open space" → high SVF, low shade, high hazard
  → 但**真实城市形态不是开阔的**, 只是 DSM source 没记
```

旧 hazard ranking 中的 high-rank cell 很多都是这种 **DSM-gap 制造的 artificial open-space signal**。

**结论 (v0.9 freeze note)**: v0.9 被 freeze 为 `v0.9-audit-freeze` 分支。v0.7-v0.9 的 hazard ranking 不再作为 ground truth, 而是 **"audit checkpoint that revealed both the potential and the limitations of the current open-data morphology pipeline"**。

**这次 audit 是项目方法论成熟的标志**: 第一次完成 *"build → discover → freeze → fix"* 循环, 而不是继续在错的基底上加复杂度。

**Pointer**:
- 详细 lab notebook: `docs/v09_freeze/32_V09_COMPLETE_WORK_RECORD_CN.md` (34 KB)
- Findings report: `docs/v09_freeze/25.5_V09_BETA_FINDINGS_REPORT_CN.md` (19 KB)
- Freeze note: `docs/v09_freeze/V09_FREEZE_NOTE_CN.md`
- DSM gap audit: `docs/v09_freeze/33_V09_BUILDING_DSM_GAP_AUDIT_CN.md`

---

### 3.5 v10 α/β/γ/δ/ε (2026-05-08 → 05-10): **audit → correct → validate 完整循环** 🌟🌟

**这是项目最实质的 sprint, 三天产出的内容比之前两周加起来还多。**

**核心方法论**: 不增加模型复杂度, 而是**修复 morphology ground truth**。

#### v10-α/α.3: reviewed augmented building DSM

构建 OSM + HDB3D + URA + manual missing buildings → dedup → height imputation → manual QA → reviewed DSM。Manual QA 处理:
- 5,313 canonical buildings reviewed
- 89 applied decisions
- 68 missing buildings manually appended
- 20 conflict candidates merged
- 1 overhead candidate identified (station canopy)

**completeness 跳跃**:
```text
6 critical SOLWEIG tile buffers:
  old vs OSM completeness:      0.263
  reviewed vs OSM completeness: 1.069  (3-4x 改善)
```

T06 从 0% → 99.9% completeness。

#### v10-β/β.1: morphology shift audit + height-QA

用 reviewed DSM 重算 building morphology (986 cells):
- `building_density` mean: 0.0746 → 0.2148 (+0.140)
- `open_pixel_fraction` mean: 0.9254 → 0.7852 (-0.140)

**识别出 34 个 old DSM-gap false-positive candidates**, 典型 e.g. TP_0116 (old rank 2, density 0 → v10 density 0.176), TP_0985 (old rank 9 → density 0 → v10 0.425), TP_0986 (old rank 10 → density 0 → v10 0.428)。

**β.1 height/geometry corrections** (人工修正):
- `v10_bldg_000001`: 原 85m, 与相邻 71m building + Google Street View 对比不合理 → 改 30m
- `v10_bldg_000002`: 原 block-complex polygon 把 tower + podium 一起赋 93.7m → 拆分为 tower / podium 分别赋高

输出: `dsm_buildings_2m_augmented_reviewed_heightqa.tif`

#### v10-γ + robustness: reviewed DSM UMEP rerun + audit hardening

用 height-QA DSM 重跑 UMEP SVF / shadow。v10-γ vs v0.8 ranking:
- Spearman 0.9705 (全局保持)
- Top20 overlap = 10/20 (high-priority intervention set 实质重排)

**FP candidate 离开率统计** (FP vs non-FP baseline, 解决 circularity 担忧):
```text
old top20 中 12 个 DSM-gap candidates:  9/12 离开 (75%)
old top20 中 8 个 non-candidates:        1/8 离开 (12.5%)
Fisher exact p ≈ 0.0198
```

**关键 framing**: 不是 "v10 prove every diagnosed FP is true FP"; 而是 **"被诊断的 candidates 在 reviewed-DSM morphology correction 后发生了 disproportionate 排名下降"**——审稿 robust framing。

#### v10-δ (overhead infrastructure layer)

修了 building DSM gap 后**暴露出第二类系统性误差**: overhead infrastructure mis-attribution。高架道路、人行天桥、连廊、车站 canopy——**既不是 building 也不是 open space, 是 two-layer infrastructure**:
- 桥面: 可能很热但不是普通行人暴露面
- 桥下: 显著遮阴, 地面行人 Tmrt 可能较低

v10-δ 构建**独立 overhead layer** (不烧进 building DSM):
- 952 canonical overhead features, 672,186 m² 总面积
- 类型: 538 covered walkway + 166 elevated rail + 127 elevated road + 83 pedestrian bridge + 38 viaduct

**overhead sensitivity (base vs overhead-as-canopy)**:
- Spearman 0.9327, Top20 overlap = 8/20 (overhead handling 关键)
- 离开 base top20 的 cells 多为 transport_deck_or_viaduct 或 mixed_pedestrian_and_transport_overhead
- **典型: TP_0088 base rank 1 → overhead rank 224, overhead_fraction = 0.732** → 不应作 ordinary pedestrian hotspot 解读

#### v10-ε (selected-cell SOLWEIG physical validation) 🎯

**目标**: 用 SOLWEIG v2025a 物理验证 v10-δ overhead sensitivity 的方向。**这是项目第一次用物理模型而不是统计模型做 ground-truth validation**。

**实验设计** (50 SOLWEIG outputs):
```text
5 cells × 2 scenarios × 5 hours

cells:
  TP_0565  confident hot anchor 1
  TP_0986  confident hot anchor 2 / perfect null control
  TP_0088  overhead-confounded rank-1 case
  TP_0916  saturated overhead case
  TP_0433  shaded reference

scenarios:
  base      v10-γ geometry
  overhead  overhead-as-canopy approximation

hours: 10, 12, 13, 15, 16 SGT
```

**核心结果** (13:00 SGT mean ground Tmrt):

| Cell | Base | Overhead | Interpretation |
|---|---:|---:|---|
| **TP_0565** | ~60.06°C | ~60°C (≈ same) | ✅ confident hotspot |
| **TP_0986** | ~60.67°C | ~60°C (≈ same) | ✅ confident hotspot |
| **TP_0088** | 61.74°C | **44.98°C** (-17°C) | ⚠️ overhead-confounded, downgrade |
| **TP_0916** | high | -20°C+ reduction | ⚠️ saturated overhead |
| **TP_0433** | ~36.09°C | ~36°C | ✅ shaded reference (control) |

**conclusion**: corrected geometry 下 confident hotspot 与 shaded reference 之间 **Tmrt 差 ~24°C**——这是 v10 final 最稳的 dissertation-citable 数字。

**Pointer**:
- Integrated final findings (v10 全成果): `docs/v10/V10_Integrated_final_findings_report_CN_FINAL_WITH_EPSILON.md` (45 KB)
- v10-ε SOLWEIG detail: `docs/v10/V10_EPSILON_SOLWEIG_final_findings_report_CN.md`
- δ overhead sensitivity: `docs/v10/V10_Delta_final_findings_report_CN_REVISED.md`

#### v10 final figures (fig01-fig08)

dissertation-quality 8 张图 deliverable, 迭代 v2 → v3 → v4 (`scripts/figures_v4/`):

```text
fig01_hazard_map.py         Map A v10-γ base hazard
fig02_tmrt_comparison.py    v10-ε base vs overhead 5-cell Tmrt
fig03_scope_taxonomy.py     confident / overhead-confounded / FP-corrected 分类
fig04_canyon_vs_canopy.py   urban canyon vs natural canopy reference
fig05_workflow_diagram.py   audit → correct → validate flow chart
fig06_dsm_audit.py          old DSM vs reviewed DSM completeness
fig07_overhead_layer.py     overhead infrastructure layer visualization
fig08_bimodal_tp0916.py     TP_0916 base vs overhead Tmrt 分布双峰
```

这是项目目前**最 portfolio-ready 的 artifact**。

---

### 3.6 v11 α/β/β.1 (2026-05-10 → 05-11): 长期 archive + 4 轮 audit + calibration 系统化 🌟🌟🌟

**这是项目当前所在阶段, 也是最严苛 audit discipline 的体现。**

#### v11-α: archive QA + collector

把 v0.9-α 的 24h 一次性 archive 升级为**长期 collector loop**:
- 15-min cadence, 持续抓取
- 27 NEA WBGT stations × Open-Meteo hourly forcing
- pair 表 long-format, 每行 station × variable × timestamp
- archive QA pipeline: collector run-id, retrospective vs operational pairing flags, migration flag (区分 migrated v0.9/v10 segments vs fresh v11 collector)
- `v11_run_alpha_archive_from_collector_pipeline.bat` 是 idempotent re-build

#### v11-β: calibration ladder M0-M7 + 4 rounds peer audit

在 long-term archive 上跑 8-model calibration ladder:
- M0 raw proxy
- M1 global bias
- M1b period bias (lifted from v0.9)
- M2 linear proxy
- M3 weather ridge (14 features)
- M4 inertia ridge (+ 4 lag/derivative features)
- M5 v10 morphology ridge (+ 7 morph features, S128 only has non-NaN)
- M6 v10 overhead ridge (+ 9 overhead features)
- M7 compact_weather_ridge (8-feature honest baseline, third audit 引入)

**4 rounds peer audit** 演化:

| Round | 关键修正 | 修了多少 patches |
|---|---|---:|
| 1 (5/10) | M4 time-aware lag features bug · S142 sensitivity · hourly aggregation 缺失 · v0.9 production proxy promotion · pairing diagnostic | 6 |
| 2 (5/10) | retrospective vs operational flag semantics · stale-dilution ablation A/B/C/D · hourly aggregation 跑通 | 7 |
| 3 (5/10) | "inherent floor" → "practical floor hypothesis" · "independent archives" → "framings" · **M5 morphology winner 误称 → M7 compact baseline** · hourly aggregator 状态矛盾 · row count 缺解释 | 5 |
| 4 (5/11) | terminology 收紧 · framing vs sample disambiguation · **M4-M3 bootstrap CI** · **threshold 4 operating points** · **H10 假说: aggregator forward morph 后 M5/M6/M7 还 bit-identical 吗** | 4 |

#### 🌟 H10 keystone: morphology unidentifiability 单机制 audit-proof

v2.1 的论证: M5/M6 ≡ M7 因为 (1) aggregator silent drop morph + (2) imputer drop all-NaN + StandardScaler neutralize。**两个机制叠加, 审稿人可以质疑 (1) 是 code-path artifact**。

**v2.2 fourth audit H10 测试**: 让 aggregator **主动 forward** 17 候选 / 15 实际存在的 static morph/overhead/grid 列 (PATCH 3), 重跑 hourly baselines。结果:

```text
hourly_max LOSO (n=1,674):
  M5_v10_morphology_ridge    (15 feat)  MAE = 0.682441  F1 = 0.639344
  M6_v10_overhead_ridge      (17 feat)  MAE = 0.682441  F1 = 0.639344
  M7_compact_weather_ridge   ( 8 feat)  MAE = 0.682441  F1 = 0.639344
                                             ↑ 6 位小数完全相同
                                             ↑ 混淆矩阵 cell-level 也相同
```

**单机制 audit-proof framing 成立**: M5/M6 ≡ M7 **仅靠 imputer + StandardScaler 数学等价**, 不依赖 aggregator 行为。**morphology calibration unidentifiable under current 27-station network** 是 signal-level constraint, 不是 code artifact。审稿人无法再质疑这条线。

#### 关键数字 (v2.2 FINAL)

```text
Calibration (hourly_mean, n=1,674, 4 days):
  M3 LOSO MAE = 0.605°C
  M4 LOSO MAE = 0.593°C
  M5/M6/M7    = 0.631°C  (bit-identical)

Operational (hourly_max + fixed_31°C):
  M4: P=0.682, R=0.588, F1=0.632
  M3: P=0.673, R=0.515, F1=0.583  (M4 +0.049 F1)
  M5/M6/M7: P=0.722, R=0.574, F1=0.639  (compact 略高 F1, 略低 recall)

M4-M3 advantage bootstrap (8 framings, 5,000 iter):
  6/8 CI 排除 0 (p < 0.05)
  最强 D_migrated: Δ=-0.0179, CI=[-0.029, -0.007], p=0.002
  all |Δ| < 0.030°C (friend's "practically meaningful" threshold)
  → statistically distinguishable but practically small

H8 calibration floor:
  v0.9 24h M3 MAE = 0.595°C
  v11 hourly_mean M3 MAE = 0.605°C
  差 0.010°C → "practical floor hypothesis ~0.6°C" 在 4d archive 上保持
```

**Pointer**: `docs/v11/OpenHeat_v11_beta1_findings_report_CN_v2_2_FINAL.md` (32 KB, canonical)

---

### 3.7 当前 (2026-05-11 后): archive loop 持续 → 14d formal pass

archive collector 现在每 15min 一行进 archive, 全程 zero collector touch 跨越 4 轮 audit。14 天后预计 ~36,000 行, 触发 formal pass:
- `v11_beta_freeze_snapshot.bat 14d_formal` 锁定 snapshot
- 用 frozen snapshot 重跑 all 8 framings + bootstrap + threshold scan
- 测 H1-H11 hypotheses (见 v2.2 FINAL §10)
- 30 天 archive 触发 v1.1-γ ML pilot 启动条件评估

---

## 4. Data + pipeline architecture

### 4.1 数据源 inventory

| 源 | 类型 | 时空分辨率 | OpenHeat 用法 | 起始版本 |
|---|---|---|---|---|
| **NEA / data.gov.sg WBGT** | 官方观测 | 27 stations × 15-min | calibration ground truth + station-level validation | v0.6 (live API) |
| **NEA Realtime Weather** | 官方观测 | ~50 stations × 1-min (sub-sampled to 15-min) | pair table aux features (T, RH, wind, rain) | v0.6 |
| **Open-Meteo Forecast API** | gridded reanalysis-derived forecast | hourly, past_days + forecast, best_match composite | M0 proxy 物理输入 + M3-M7 calibration features | v0.5 |
| **HDB3D building footprints** | open data | 2m | base building DSM | v0.8 |
| **URA building polygons** | open data | polygon | base building DSM (merged with HDB3D) | v0.8 |
| **OSM buildings** (Singapore) | open data | polygon | v10-α augmented DSM 主源 (修复 25.8% gap) | v10-α |
| **OSM overhead** (rail, road, bridge, walkway) | open data | line + polygon | v10-δ overhead infrastructure layer | v10-δ |
| **GEE GHSL building height** | satellite-derived | varying | v0.7 building height feature | v0.7 |
| **GEE Dynamic World** | satellite, 10m, near-real-time | tree/grass/water/built-up fraction | v0.7 vegetation + impervious features | v0.7 |
| **Sentinel-2 NDVI** | satellite, 10m | GVI 代理 | v0.7 vegetation feature | v0.7 |
| **ETH GlobalCanopyHeight 2020** | satellite, 10m → 2m bilinear | vegetation DSM | v0.8 UMEP morphology | v0.8 |
| **Landsat 8-9 LST** | satellite, 30m, 10:30 LT | hotspot validation (Cooling TP project 用过) | not yet in OpenHeat pipeline | (used in Cooling TP) |
| **SingStat Census 2020** | static | subzone | v0.7.1 vulnerability scoring (elderly/children share) | v0.7.1 |
| **NParks / LTA / road datasets** | open data | polygon/line | v0.7 land-use features | v0.7 |

**关键 caveat (v2.2 FINAL terminology)**:
- 我们的不同 "datasets" 实际是同一 base archive 的不同 **framings** (filter / aggregation 出来的 view), **不是 source-independent**。v1.1 archive 含 migrated v0.9/v10 segments + fresh v11 collector。
- evaluator-independent across CV folds / station sets / aggregation cadences ✓
- source-independent ✗ (审稿 framing 需要诚实区分)

### 4.2 Pipeline 主流 (current)

```text
Open-Meteo Forecast API ──┐
                          │
NEA WBGT 27 stations ─────┼─→ v11_archive_collect_once.py (every 15 min, idempotent)
                          │   ↓
NEA realtime weather ─────┘   data/calibration/v11/v11_station_weather_pairs.csv  
                              (long format, 6,372 行 → growing)
                              ↓
                              v11_beta_build_features.py
                              ↓ adds v0.9 proxy + lag features + retrospective + migration flags
                              data/calibration/v11/v11_station_weather_pairs_v091.csv (6,372 × 495 cols)
                              ↓
                              v11_beta_aggregate_hourly.py  (v2.2 PATCH 3 + STATIC_FIRST_COLS)
                              ↓
                              data/calibration/v11/v11_station_weather_pairs_hourly.csv (1,674 × 70 cols)
                              ↓
                              ├──── v11_beta_calibration_baselines.py (4 configs)
                              │     ↓
                              │     outputs/v11_beta_calibration/{all_stations, no_S142, 
                              │                                   ablation_A/B/C/D,
                              │                                   hourly_mean, hourly_max}/
                              │       ├── v11_beta_calibration_metrics.csv
                              │       ├── v11_beta_oof_predictions.csv
                              │       └── v11_beta_calibration_baseline_report.md
                              │
                              ├──── v11_beta_bootstrap_advantage.py
                              │     ↓
                              │     bootstrap_M4_minus_M3.csv (8 framings × 5000 iter)
                              │     fold_level_M3_M4_delta_by_dataset.csv
                              │
                              └──── v11_beta_threshold_scan.py
                                    ↓
                                    threshold_operating_points.csv (4 ops × 4 models)
                                    threshold_scan_full.csv
```

### 4.3 历史 pipeline (v10, frozen)

```text
HDB3D + URA + OSM buildings ──┐
                              ├─→ v10_alpha_* (augmented DSM)
manual QA decisions ──────────┘   ↓
                                  dsm_buildings_2m_augmented_reviewed_heightqa.tif
                                  ↓
                                  v10_gamma_* (UMEP SVF / shadow rerun)
                                  ↓
                                  toa_payoh_grid_v10_features_umep_with_veg.csv
                                  ↓
                                  ├──── v10_delta_* (overhead infrastructure sensitivity)
                                  │     ↓
                                  │     v10_base_vs_overhead_sensitivity_comparison.csv
                                  │
                                  └──── v10_epsilon_* (selected-cell SOLWEIG)
                                        ↓
                                        v10_epsilon_focus_tmrt_summary.csv
                                        v10_epsilon_base_vs_overhead_tmrt_comparison.csv
```

### 4.4 重要 repo paths (current as of v11-β.1)

```
06-openheat_grid/
├── README_CN.md                        v0.6.4 era top-level README (outdated but kept)
├── README_V09_BETA_CN.md               v0.9-β era README
├── README/                             17 个 patch-level READMEs (v09 → v11)
├── configs/
│   ├── v10/                            v10 morphology + augmented DSM configs
│   └── v11/                            v11 calibration configs (4 v091 variants)
├── data/
│   ├── grid/                           Toa Payoh 100m grid features
│   ├── features_3d/v10/                v10 augmented DSM source layers
│   ├── rasters/v10/                    reviewed/heightqa DSM .tif (NOT in git)
│   ├── archive/                        NEA realtime archive (long format)
│   └── calibration/v11/                pair tables (raw, v091, hourly, snapshots/)
├── docs/
│   ├── 01-33_*.md                      v0.5-v0.9 dev guides
│   ├── handoff/                        4 个 handoff docs
│   ├── v09_freeze/                     v0.9 era frozen docs
│   ├── v10/                            v10 sprint docs + findings
│   └── v11/                            v11 docs (4 个 archived + 1 canonical v2.2 FINAL)
├── outputs/
│   ├── v06_live_*                      v0.6 hotspot + event-window outputs
│   ├── v09_*                           v0.9 calibration + SOLWEIG outputs
│   ├── v10_*                           v10 sprint outputs (含 audit reports)
│   ├── v10_final_figures_v4/           8 dissertation-ready figures
│   └── v11_beta_calibration/           current calibration metrics + OOF predictions
└── scripts/
    ├── archive_nea_observations.py     (v0.6 era, still used)
    ├── v09_*.py                        v0.9 calibration scripts
    ├── v10_alpha_*.py                  augmented DSM
    ├── v10_beta_*.py                   morphology audit
    ├── v10_gamma_*.py                  UMEP rerun
    ├── v10_delta_*.py                  overhead sensitivity
    ├── v10_epsilon_*.py                SOLWEIG validation
    ├── v11_archive_collect_once.py     long-term collector
    ├── v11_beta_*.py                   calibration ladder
    ├── v11_beta_bootstrap_advantage.py  (v2.2 新)
    ├── v11_beta_threshold_scan.py       (v2.2 新)
    ├── v11_beta_freeze_snapshot.bat     (v2.2 新)
    └── figures/, figures_v2/, figures_v3/, figures_v4/   8 figures × 4 iterations
```

---

## 5. Cumulative findings: 什么是真的 / 什么是限制

### 5.1 已证实 (audit-proof)

| Finding | 哪个版本 | 证据 |
|---|---|---|
| v0.9 proxy 系统性 under-predict | v0.9-β | M0 LOSO bias = -1.140°C (v0.9 24h, n=2,564); v11 multi-day framings 复现 -1.04 ~ -1.35°C |
| 旧 HDB3D + URA building DSM 严重不完整 | v0.9-γ audit | 25.8% completeness vs OSM in 6 critical tile buffers; T06 = 0% |
| Reviewed DSM 修复 DSM-gap false positives | v10-γ + robustness | FP candidates: 9/12 离开 old top20; non-candidates: 1/8 离开; Fisher p≈0.02 |
| 旧 hazard ranking top set 对 overhead handling 高度敏感 | v10-δ | base vs overhead Spearman 0.93, top20 overlap = 8/20 |
| TP_0565 / TP_0986 是 confident hotspot anchors | v10-ε SOLWEIG | 13:00 Tmrt ~60°C, overhead scenario 几乎不变, vs shaded ref ~36°C → ~24°C 差 |
| TP_0088 是 transport-deck / viaduct confounded | v10-δ + v10-ε | base 13:00 Tmrt 61.74°C → overhead 44.98°C (Δ=-17°C) |
| Calibration M3 LOSO MAE 在 ~0.6°C 附近稳定 | v11-β.1 | v0.9 24h M3=0.595, v11 hourly_mean M3=0.605, 差 0.010°C |
| Stale-dilution hypothesis 是 false | v11-β.1 second audit | A_all M3 ≡ B_retrospective M3 bit-identical; bootstrap CI 也 bit-identical |
| **M5/M6/M7 morphology contribution = 0** (under current 27-station network) | v11-β.1 fourth audit H10 | bit-identical 6 decimal places, 4 framings, aggregator forward 后仍成立 |
| M4 thermal inertia advantage statistically distinguishable | v11-β.1 fourth audit | 6/8 framings bootstrap CI 排除 0, max effect D_migrated -0.0179°C, p=0.002 |

### 5.2 已 falsify

| 旧 Claim | 哪里 falsified | 替代 |
|---|---|---|
| "Stale rows dilute calibration MAE" (v1 finding 4.7) | v11-β.1 second audit A/B ablation | A_all ≡ B_retrospective bit-identical → false |
| "0.6°C is inherent calibration floor" (v2) | third audit | softened to "practical floor hypothesis" pending 14d H8 test |
| "v11 evaluates 4 independent datasets" (v2) | third + fourth audit | actually 8 framings of single base archive; reframed as "evaluation framings" |
| "M5 morphology model is operational winner" (v2) | third audit | M5 = M6 = M7 bit-identical; M7 是 honest 8-feature baseline |
| "M5/M6 = M7 because aggregator drops morph" (v2.1 mechanism 1) | fourth audit H10 | aggregator forward 后仍 bit-identical → single-mechanism (imputer drop + scaler neutralize) |

### 5.3 当前限制 (open / structural)

| 限制 | 来源 | 何时可能松动 |
|---|---|---|
| **Morphology calibration unidentifiable** | 27 stations 中仅 S128 在 TP grid AOI 内 → LOSO 下 imputer drop + scaler neutralize | 需要 ≥ 5 stations per AOI grid quartile, 现实中不太可能 (NEA 网络密度固定) |
| **Calibration MAE 在 0.6°C floor** | 物理 noise + Open-Meteo forcing 精度 + Stull 公式 residual | 可能要 site-specific forcing (e.g. micro-network) 或 non-ridge model class (ML residual) |
| **Threshold detection F1 ceiling ~0.72-0.73** | 跨 M3/M4/M7, best-tuned 都到这个范围 | inertia features 不破; 可能要新 feature class (LST, behavioral) |
| **15-min precision_70 unreachable** | precision plateau at ~0.43 due to within-hour noise | hourly_max 是 operational primary 的强论据 |
| **4-day archive 不足以判定 M4 effect size** | C_fresh single-day p=0.92, hourly_mean border p=0.06 | 14d formal pass + 30d ML pilot 数据扩充 |
| **没有 behavioral exposure 层** | 当前 grid hazard 是 environmental only, 没接 pedestrian trajectory | 这是 Plymouth diss 留下的接口, EDSML 阶段可能接入 (§7.3) |
| **没有 water 维度** | OpenHeat 只做 heat, 没接 sponge city / flood / drainage | water-heat nexus 是 EDSML 阶段计划方向 (§7.3) |

---

## 6. What's working / what's not / what's open

### 6.1 Ship-ready ✅

可以直接拿出去给人看 / 写进 portfolio 的:

- **v10 final figures (fig01-fig08)**: dissertation-quality, 迭代 v4, 8 张图覆盖 hazard map + Tmrt comparison + workflow + DSM audit + overhead layer + 双峰分布
- **v10 Map A / B / C 三图框架** + 2 confident hotspot anchors (TP_0565, TP_0986)
- **v10-ε SOLWEIG 实验**: 50 outputs, 5 cells × 2 scenarios × 5 hours, base vs overhead Tmrt comparison
- **v11-β.1 calibration ladder + 4 rounds peer audit**: M0-M7 8 models, audit-proof H10 keystone, 22 patches
- **operational baseline**: M4 + hourly_max + fixed_31°C, F1 = 0.63, no tuning required at deployment
- **bootstrap-confirmed statistical evidence**: 6/8 framings M4 advantage CI 排除 0, monotonic by regime diversity

### 6.2 ⚠️ Working-但-需要-caveat

需要带 caveat / 仍 work-in-progress:

- **Calibration MAE ~0.6°C**: 4-day archive 上看着 stable, 但 H8 假说在 14d formal pass 之前未正式验证
- **M4 inertia advantage**: 统计显著 (6/8) 但 |Δ| 全部 < 0.030°C friend threshold → "statistically detectable but practically small"
- **F1 = 0.63 operational**: 4 days, 204 ≥31°C events, 14d formal pass 看是否 stable
- **27-station network morphology unidentifiability**: 这是已 audit-proof 的限制, 但每次提 morphology 都要带这个 caveat

### 6.3 ❌ 已知 broken / 没做

- **operational forecast pipeline** (v06_live_*) 在 v10+ 之后没保持 maintain, top-level README 是 v0.6.4 era 的, 跟当前 v11 不同步
- **没有 behavioral exposure 层**: Plymouth diss 留下的方法 (mobile monitoring + GEMA) 还没接到 OpenHeat
- **没有 water 维度**: water-heat nexus 是 stated future direction 但还没动
- **ML residual learning**: 当前还是 ridge, 没启动 ML pilot (有 gates: 30d archive, 1,500+ ≥31°C events, M4 F1 ≥ 0.55)
- **Forecast 部署**: 当前 calibration 是 retrospective; prospective forecast use case 没 systematically 评估
- **跨城市 portability**: Suzhou case 的 collector 接口 / station mapping 没建

### 6.4 Open questions

- **H8 calibration floor**: 14d / 30d archive 后 M3 LOSO MAE 还在 [0.55, 0.70] 吗?
- **M4 advantage scaling**: archive 越长, regime 越多样, |Δ| 会不会 cross 0.03 threshold 变 "meaningful"?
- **ML residual class**: gradient boosting / neural / Gaussian process? 何种最 robust under 当前 ridge ceiling?
- **TP_0565/TP_0986 validation 跨季节**: v10-ε 跑的是 2026-03-20 春分; monsoon / dry season 下还是 confident anchors 吗?
- **可不可以拿 v10 reviewed DSM + v11 calibration ladder 给 Cooling TP 项目里的 Heat Committee 用?** 这是 use case 闭环测试
- **Suzhou 复制可行性**: 中国二线城市 NEA 等价物 (气象局站点) 数据可获取性? OSM building coverage?

---

## 7. Roadmap

### 7.1 Immediate (2 weeks, 现在 → 2026-05-25)

**Auto-pilot mode**: archive collector loop 持续, zero manual intervention.

```text
Day 1-14 (5/11 → 5/25):
  - v11_archive_collect_once.py every 15 min (already running)
  - 预期 archive 增长: 6,372 → ~36,000+ 行
  - 预期 hourly buckets: 1,674 → ~10,000
  - 预期 ≥31°C events: 204 → ~1,200+ (4× current)
  - 零 collector touch
```

**On Day 14** (5/25 左右, 触发 formal pass):
```text
1. scripts\v11_beta_freeze_snapshot.bat 14d_formal
   → 锁定 frozen snapshot for reproducibility
2. 重跑 all 4 configs (all_stations, no_S142, hourly_mean, hourly_max)
   + ablation A/B/C/D
   + bootstrap M4 advantage
   + threshold scan
3. H1-H11 hypothesis verification (v2.2 FINAL §10)
4. 写 OpenHeat_v11_beta_formal_findings_report_CN.md
```

### 7.2 Near (1-2 months, 5/25 → 7/15)

**条件性 trigger v1.1-γ ML residual pilot**, 当满足:

```text
✓ archive ≥ 30 days
✓ WBGT ≥31 events ≥ 1,500 (hourly_max)
✓ WBGT ≥33 events ≥ 100
✓ ≥ 3 weather regimes (rainfall / dry / monsoon)
✓ hourly_max fixed_31 F1 ≥ 0.55 stable
✓ M3/M4 LOSO + time_block CV 都 stable
```

**v1.1-γ 设计 (preliminary)**:
- **Target**: residual = official_wbgt - M4_prediction (M4 是 best calibration baseline)
- **Features**: weather + lag + period + station-level random effect + (optional) morph if formal pass H6/H10 仍 confirm unidentifiability
- **Model classes 候选**: gradient boosting (xgboost/lightgbm), small MLP, Gaussian process (small-sample regime), conformal prediction for uncertainty
- **Eval**: LOSO + blocked-time CV, F1@31°C improvement vs M4 baseline, calibration of predicted uncertainty
- **Philosophy** (carried from v0.9 freeze note): **ML 只做 residual learning, 永远不替代 Open-Meteo / WBGT 公式 / GIS features**

**也可能 trigger** (取决于 v1.1-β formal pass 结果):
- **v1.2 设计文档**: 如果 M5/M6/M7 在 14d/30d 还是 bit-identical, 写 *"morphology calibration requires denser AOI network — proposal"* doc, 评估 supplementing NEA WBGT 与 micro-loggers (借鉴 Cooling TP Solution 2 的 10-15 indoor loggers) 的可行性
- **Operational forecast pipeline 更新**: 把 v06_live 的 forecast workflow 跟当前 v11 calibration 接上 (e.g. M4 model 在 Open-Meteo forecast 上做 prospective inference)

### 7.3 Mid (3-6 months, 7/15 → 11/15, ~EDSML 入学前后)

**EDSML 入学前** (7-9 月):
- 整理 portfolio: 把 v10 final figures + Cooling TP PPT + v2.2 FINAL summary + 本 synthesis 打包成可分享版本
- (可选) 投个 conference abstract / workshop paper: 类似 *"Open-data fine-scale urban heat-hazard ranking with audit-driven morphology correction: a Toa Payoh case study"*
- 准备 EDSML 入学方向交流材料: 跟导师讨论是否要深化 OpenHeat 还是 pivot

**EDSML 入学后** (10-11 月起), **三个候选 expansion 方向** (估计选 1-2):

#### 方向 A: Water-heat nexus extension (家乡 origin 故事的延续)

把 OpenHeat 从 heat-only 扩展为 heat + flood + drainage coupled:
- 加 PUB sponge city data / SUTD impermeable layer / OSM drainage features
- coupled risk: dry-season heat × monsoon flood × elderly walking exposure
- 借鉴设计院 sponge city 视角: bioretention / permeable pavement / detention pond 同时影响 microclimate + flood capacity
- Output: Toa Payoh 100m grid × (heat hazard, flood hazard, coupled risk) tri-map

#### 方向 B: Behavioral exposure 层 (Plymouth diss 接口)

把 GEMA 经验接入 OpenHeat:
- pedestrian trajectory data (synthetic 或 OSM-routing-based)
- exposure = ∫ hazard(trajectory) dt
- 跟 v0.7.1 vulnerability score 结合: vulnerable population × trajectory × hazard
- 借 Plymouth diss 的 appraisal mediation 发现: 即使有 mobile data 也要保留 subjective comfort 通路
- Output: exposure-weighted hotspot ranking + intervention priority (跟 Cooling TP Solution 2 直接挂)

#### 方向 C: ML residual + uncertainty quantification (techniques 深化)

如果 v1.1-γ pilot 跑得好, 进一步深化:
- physics-informed ML 在 calibration residual 上的 application
- conformal prediction for operational alert
- transfer learning: Toa Payoh → 别的 HDB town → 别的城市
- 适合 EDSML 学位真正的 thesis 方向

#### 方向 D (more speculative): Suzhou case 复制

- 中国二线城市 NEA 等价数据: 气象局站点 + 数据可获取性?
- OSM building coverage 在中国 city 一般低于 SG, augmented DSM 的 manual QA 工作量大
- 但是 personal motivation 最深, 值得起码做一个 feasibility doc

### 7.4 Long-term (12+ months, EDSML 后期 → 可能的 PhD)

**OpenHeat 作为 personal portfolio anchor**:
- demonstrates: end-to-end pipeline 能力 (data engineering + physical modeling + statistical inference + audit discipline)
- positions: "我对 fine-scale urban climate risk 有 specific case study + 4-round audit experience" — 比抽象兴趣陈述强很多
- 可发展成 EDSML thesis 的 backbone case (任何方向 A/B/C/D 都可以)
- 可发展成 PhD application 的 demonstration project

**潜在 PhD 方向种子**:
1. *Coupled water-heat risk in tropical / sub-tropical cities under climate stress* (方向 A 深化)
2. *Physics-informed ML for sub-city-scale urban climate forecasting with audit-driven robustness* (方向 C 深化)
3. *Behavioral exposure modeling: from mobile monitoring to predictive risk mapping* (Plymouth diss + 方向 B 融合)

每个种子在 OpenHeat 当前阶段都已有部分基础, 不是 zero start。

---

## 8. Engineering discipline 与 lessons learned

这是 "personal project" 框架下最有价值的反思部分。把方法论 sin / 方法论 wins 都记下来给未来的我。

### 8.1 Loop-not-stopped principle (zero collector touch)

v11 阶段引入的核心 discipline: **archive collector loop 在 4 轮 audit 全程不中断**。所有 audit 修订都是 offline / downstream, 不动 collector。

**为什么重要**:
- archive 本身是 ground truth, 中断 = 永久数据 loss
- 任何 collector 修改都要重 deploy + 重测试, 这会 invalidate 之前 archive
- offline patch + retrospective re-build 是 idempotent 的, 不会破坏现有 archive

**lessons**:
- 如果未来某个 audit point 说 "我们要改 collector 的 X", 先问: "X 是 retrospective 可以 patch 的吗?" 99% 是。
- 这条 principle 在 SBT (sustainable build tool) / data engineering 里叫 *"hot path 不动, cold path 任意改"*

### 8.2 4 rounds peer audit 演化

| Audit | Trigger | Output |
|---|---|---|
| 1 (first) | M4 跑出 weird negative advantage | 发现 lag features 没正确 windowed; 加 S142 sensitivity; hourly aggregation 缺失 |
| 2 (second) | A/B/C/D ablation 想跑 | retrospective vs operational flag semantics 拆分; 改 build_features 不动 collector |
| 3 (third) | v2 doc review | "inherent floor" 措辞 / "independent archives" 措辞 / **M5 morphology winner misleading** → 加 M7; hourly aggregator 状态矛盾 |
| 4 (fourth) | v2.1 doc review | terminology 收紧; **bootstrap CI** on M4-M3; **4 operating points** on hourly_max F1; **H10 假说** test |

**lessons**:
- 每一轮 audit **不只是 doc review, 也是 code patch**——4 轮总共 22 个 patches
- audit 的最大价值在 **catch wrong framing** 而不是 bug: "M5 morphology winner" 是 wrong framing 不是 wrong code; 加 M7 + bit-identity proof 才是真正诚实
- 朋友 audit > self-audit. 第三轮 audit catch 的 "M5 winner misleading" 我自己读 v2 文档时是看不见的
- **Decision log** 在 audit 之间起到 institutional memory 作用——v2.2 FINAL §11 list 了 25 个 decisions

### 8.3 Bit-identity regression test (H10 keystone 例子)

v2.2 fourth audit 引入的最 elegant audit technique:

> "如果你的 framework 对一个 transformation invariant, 那么 transformation 后 metric 应该 bit-identical 而不是 statistically similar."

H10 例子:
- v2.1 论证: morphology contribution = 0 because (1) aggregator drops + (2) imputer + scaler neutralize
- 朋友 audit: "(1) 是 code artifact 不是 signal evidence"
- v2.2 实验: 让 aggregator 主动 forward morph (PATCH 3), 重跑
- 结果: M5/M6/M7 MAE 仍 = 0.682441 到 6 位小数
- conclusion: **single-mechanism (只剩 imputer + scaler) 仍能 reproduce bit-identity → audit-proof**

**lessons**:
- 不是所有 audit 都要 statistical test; 有时 bit-identity 是更强证据
- 提前为 "如果 X 改了, 我希望 Y 仍 = old Y" 这种 invariant 设计 regression test, 是 ML pipeline 的 hygiene

### 8.4 Sandbox vs production 分离 (v10 学到的)

v10 sprint 期间 build augmented DSM 时碰到的问题:
- 写 augmented DSM script → 测试 → 满意 → 但 git push 失败 (超大 .tif 被误提交)
- 学习: `.tif`, `.zip`, hourly forecast CSV 这种**大 binary / 大派生数据**不应该进 git, 应该在 `.gitignore` 加 patterns

```text
data/rasters/v10/*.tif
data/solweig/
data/archive/
outputs/*forecast_live/*.csv (hourly grids 经常 300+ MB)
patch zip packages
```

**lessons**:
- Git 是 code + small docs + small data, **不是** large rasters / archives / model outputs
- production outputs 应该可重建, 不应该 commit 死的
- 用 patch packages (`create_openheat_handoff_package.bat`) 来 ship snapshot, 不靠 git history

### 8.5 Statistical significance ≠ practical significance (v2.2 fourth audit lesson)

v2.2 bootstrap 显示 M4 advantage 在 6/8 framings CI 排除 0 (p < 0.05) 但全部 |Δ| < 0.030°C friend threshold。**正确诚实 framing**:

> "M4 inertia advantage is statistically distinguishable from zero in 6 of 8 framings but practically small (|Δ| ≤ 0.018°C below the 0.030°C threshold for practically meaningful contribution)."

**lessons**:
- 别用 p < 0.05 当 "we found something" 的免死金牌
- 要同时报告 effect size + threshold for "meaningful"
- 这是个朋友 fourth audit 直接 force 改的 framing, 改之前 v2.1 自己看不出来问题

### 8.6 Sources of truth 分层 (v0.9 audit 学到的)

v0.9-γ audit 发现 building DSM 25.8% completeness → 直接重 ranking。**核心 insight**:

> "Ground truth 在多个 source 之间不重叠时, 别假设 majority/recent source 是 right one。Audit cross-source completeness 是 mandatory 而不是 optional."

旧 pipeline 假设 HDB3D + URA 是完整 source, 没 cross-check OSM。结果 25% gap, 整个 hazard ranking 误读 high-rank cells。

**lessons**:
- For any "ground truth" data source, 至少有 2 个 independent comparison source
- Completeness audit 应该是 pipeline init 阶段的 mandatory step, 不是 later afterthought
- 如果 audit 发现 gap > 5-10%, 应该立刻 freeze + investigate, 而不是 patch and continue

### 8.7 Audit-driven framing > model-class push

v0.9-v10 整个 sprint 的 meta lesson:

> "When pipeline 出 weird result, default 不是加 model complexity (ML / deeper net / more features), 而是 audit existing pipeline。"

v0.9-γ hazard ranking 出意外 → audit 发现 DSM gap → v10 重做 ground truth → 简单 ridge 也能给出 confident hotspots。如果当时直接上 deep learning, 结果可能"看起来更准"但仍然在 broken DSM 上算。

**lessons**:
- ML 之前先 audit data + pipeline 是 PhD-level discipline
- "audit → correct → validate" 比 "more complex model → metric +0.01" 更长寿
- 这条原则 carried into v1.1-γ ML pilot 设计: ML 只学 residual, 不替代 physical scaffolding

---

## 9. Repo navigation: "I want to do X, where do I start?"

### 9.1 Setup (fresh clone)

```bat
git clone <repo>
cd 06-openheat_grid
conda env create -f environment.yml   # if available, else conda env create -n openheat python=3.10
conda activate openheat
pip install -r requirements.txt
```

### 9.2 任务 cookbook

| 我想… | 第一步看什么 |
|---|---|
| Run live forecast | `README_CN.md` (v0.6 era) + `scripts/run_live_forecast_v06.py --mode sample` |
| Validate forecast against NEA observation | `scripts/archive_nea_observations.py --mode live` |
| Re-run v10 morphology correction | `docs/v10/V10_PROJECT_STRUCTURE_CN.md` + `scripts/v10_alpha_*.py` (alpha → beta → gamma → delta → epsilon 顺序) |
| 看 SOLWEIG selected-cell physical validation | `docs/v10/V10_EPSILON_SOLWEIG_final_findings_report_CN.md` + `scripts/v10_epsilon_*.py` |
| Re-generate 8 dissertation figures | `cd scripts/figures_v4 && python run_all.py` |
| Start long-term archive collector | `scripts\v11_archive_loop.bat` |
| Run current calibration ladder | §9.1 of v2.2 FINAL doc |
| Verify H10 keystone (M5≡M6≡M7) | `python -c "import pandas as pd; m=pd.read_csv('outputs/v11_beta_calibration/hourly_max/v11_beta_calibration_metrics.csv'); loso=m[m['cv_scheme']=='loso']; print(loso[['model','n_features','mae']].round(6).to_string(index=False))"` |
| Bootstrap M4 advantage | `python scripts\v11_beta_bootstrap_advantage.py` |
| Threshold scan 4 operating points | `python scripts\v11_beta_threshold_scan.py --config configs\v11\v11_beta_calibration_config_v091_hourly_max.json` |
| 14d formal pass (when ready) | `scripts\v11_beta_freeze_snapshot.bat 14d_formal` then re-run all calibration configs on frozen snapshot |

### 9.3 Doc navigation by topic

| 想搞清楚… | 看这个 |
|---|---|
| Project 整体故事 | 本 doc |
| v0.6-v0.8 早期 pipeline 决策 | `docs/01_*.md` 到 `docs/23_*.md` |
| v0.9 calibration 数学 + LOSO 设计 | `docs/24_V09_ALPHA_CALIBRATION_GUIDE_CN.md` + `docs/25_V09_BETA_CALIBRATION_GUIDE_CN.md` |
| v0.9 audit freeze 决策依据 | `docs/v09_freeze/V09_FREEZE_NOTE_CN.md` + `33_V09_BUILDING_DSM_GAP_AUDIT_CN.md` |
| v10 完整 sprint | `docs/v10/V10_Integrated_final_findings_report_CN_FINAL_WITH_EPSILON.md` |
| v10 augmented DSM 工程细节 | `docs/v10/V10_ALPHA_AUGMENTED_DSM_GUIDE_CN.md` + `V10_ALPHA2_QA_TARGET_GENERATION_GUIDE_CN.md` |
| v10 SOLWEIG selected-cell | `docs/v10/V10_EPSILON_SOLWEIG_GUIDE_CN.md` |
| v11 collector + archive design | `docs/v11/V11_LONGTERM_ARCHIVE_GUIDE_CN.md` |
| v11 calibration ladder + 4 audit rounds | `docs/v11/OpenHeat_v11_beta1_findings_report_CN_v2_2_FINAL.md` |
| v11 fourth audit Plan A 代码细节 | v2.2 FINAL §3 + §11 |

---

## Appendix A: 完整 version timeline (table)

| Version | Date | Key deliverable | Pointer doc |
|---|---|---|---|
| v0.5 | ~2026-04 | first prototype: Open-Meteo + UTCI/WBGT proxy | `docs/01_HEAT_STRESS_PREDICTION_SYSTEM_ROADMAP_CN.md` |
| v0.6 | 2026-04 末 | live API + NEA WBGT/realtime weather + hotspot ranking | `docs/01_V06_LIVE_API_AND_CALIBRATION_GUIDE_CN.md` |
| v0.6.1 | | feedback optimization | `docs/06_V06_1_FEEDBACK_OPTIMISATION_CN.md` |
| v0.6.2 | | WBGT v1 endpoint schema 修复 | `docs/09_V06_2_WBGT_SCHEMA_HOTFIX_CN.md` |
| v0.6.3 | | WBGT v2 schema | `docs/10_V06_3_WBGT_V2_SCHEMA_FIX_CN.md` |
| v0.6.4 | | long-format archive, UTCI/WBGT alert split, hotspot hazard saturation fix | `docs/11_V06_4_ARCHIVE_AND_ALERT_HOTFIX_CN.md` |
| v0.6.4.1 | 2026-05-06 | 6-point source-review hotfix | `docs/12_V06_4_1_SRC_REVIEW_PATCH_CN.md` |
| v0.7-α/β | 2026-05 早 | 真实 100m grid + URA/NParks/GEE features | `docs/13_V07_GRID_FEATURES_PIPELINE_CN.md` |
| v0.7-β GEE | | GEE integration | `docs/14_V07_BETA_GEE_INTEGRATION_CN.md` |
| v0.7.1 | | vulnerability + outdoor exposure + risk scenarios | `docs/16_V071_RISK_EXPOSURE_GUIDE_CN.md` |
| v0.8 | 2026-05 中 | UMEP morphology (building + canopy SVF/shade) | `docs/21_V08_UMEP_WITH_VEGETATION_MERGE_FORECAST_CN.md` |
| v0.8 risk scenarios | | hazard-only / conservative / social / candidate policy | `docs/23_V08_RISK_SCENARIOS_CN.md` |
| **v0.9-α** | 2026-05-07 → 05-08 | 24h archive, 2,564 pairs, calibration foundation | `docs/24_V09_ALPHA_CALIBRATION_GUIDE_CN.md` |
| **v0.9-β** | 2026-05-08 | calibration M1-M4 ladder, threshold scan | `docs/25.5_V09_BETA_FINDINGS_REPORT_CN.md` |
| **v0.9-γ** | 2026-05-08 | SOLWEIG selected-tile, overhead-aware selection | `docs/27_V09_GAMMA_SOLWEIG_GUIDE_CN.md` |
| v0.9 audit freeze | 2026-05-08/09 | **DSM gap discovered, freeze v0.9 as audit checkpoint** | `docs/v09_freeze/V09_FREEZE_NOTE_CN.md` |
| **v10-α/α.1/α.2/α.3** | 2026-05-08 → 05-09 | augmented DSM, OSM-first, manual QA | `docs/v10/V10_ALPHA_AUGMENTED_DSM_GUIDE_CN.md` |
| **v10-β/β.1** | 2026-05-09 | morphology shift audit, height-QA correction | `docs/v10/V10_BETA_BASIC_MORPHOLOGY_GUIDE_CN.md` |
| **v10-γ + robustness** | 2026-05-09 | reviewed-DSM UMEP rerun, FP candidate baseline | `docs/v10/V10_GAMMA_UMEP_MORPHOLOGY_GUIDE_CN.md` + `V10_GAMMA_ROBUSTNESS_AUDIT_GUIDE_CN.md` |
| **v10-δ** | 2026-05-09 | overhead infrastructure layer, sensitivity ranking | `docs/v10/V10_DELTA_OVERHEAD_SENSITIVITY_GUIDE_CN.md` |
| **v10-ε** | 2026-05-09 → 05-10 | 5-cell × 2-scenario × 5-hour SOLWEIG validation | `docs/v10/V10_EPSILON_SOLWEIG_GUIDE_CN.md` |
| **v10 final figures** | 2026-05-10 | 8 dissertation-quality figures (v4 iteration) | `docs/v10/V10_FINAL_FIGURE_MAP_GUIDE_V4_CN.md` |
| v11-α | 2026-05-10 | archive QA + long-term collector | `docs/v11/V11_ALPHA_ARCHIVE_QA_GUIDE_CN.md` + `V11_LONGTERM_ARCHIVE_GUIDE_CN.md` |
| v11-β | 2026-05-10 | calibration baselines M0-M7, 4 configs | `docs/v11/V11_BETA_CALIBRATION_GUIDE_CN.md` |
| **v11-β.1** v1 | 2026-05-10 | first audit findings (5 points) | `docs/v11/...v1_archived.md` |
| v11-β.1 v2 | 2026-05-10 | second audit (3 points), ablation, hourly | `docs/v11/...v2_archived.md` |
| v11-β.1 v2.1 | 2026-05-10 | third audit (5 points), M7 + M5/M6/M7 bit-identity | `docs/v11/...v2_1_archived.md` |
| **v11-β.1 v2.2 FINAL** | 2026-05-11 | fourth audit (4+1 points), H10 keystone, bootstrap + threshold | `docs/v11/OpenHeat_v11_beta1_findings_report_CN_v2_2_FINAL.md` |

**当前状态**: v1.1-β.1 v2.2 FINAL canonical, archive 6,372 行, 等待 14-day formal pass.

---

## Appendix B: Document relationship graph

```text
              docs/01_HEAT_STRESS_PREDICTION_SYSTEM_ROADMAP_CN.md
                                      │
                                      ▼ (v0.5-v0.6 era)
              README_CN.md (v0.6.4.1 era top-level)
                                      │
                                      ▼
              docs/01-30_V*_*_CN.md (per-version dev guides)
                                      │
                                      ▼ (v0.9 audit)
              docs/v09_freeze/V09_FREEZE_NOTE_CN.md
              docs/v09_freeze/25.5_V09_BETA_FINDINGS_REPORT_CN.md
              docs/v09_freeze/32_V09_COMPLETE_WORK_RECORD_CN.md  ← L3
              docs/v09_freeze/33_V09_BUILDING_DSM_GAP_AUDIT_CN.md
                                      │
                                      ▼ (v0.9 freeze → v10 start)
              docs/handoff/OPENHEAT_HANDOFF_CN.md  ← L2 (first handoff)
                                      │
                                      ▼ (v10 sprint)
              docs/v10/V10_*_GUIDE_CN.md (per-stage guides)
              docs/v10/V10_Delta_final_findings_report_CN_REVISED.md
              docs/v10/V10_EPSILON_SOLWEIG_final_findings_report_CN.md
              docs/v10/V10_Integrated_final_findings_report_CN_FINAL_WITH_EPSILON.md  ← L3
                                      │
                                      ▼ (v10 → v11)
              docs/handoff/OpenHeat_v10_to_v11_HANDOFF_CN.md  ← L2 (second handoff)
                                      │
                                      ▼ (v11 sprint)
              docs/v11/V11_*_GUIDE_CN.md
              docs/v11/OpenHeat_v11_beta1_findings_report_CN_v1_archived.md
              docs/v11/OpenHeat_v11_beta1_findings_report_CN_v2_archived.md
              docs/v11/OpenHeat_v11_beta1_findings_report_CN_v2_1_archived.md
              docs/v11/OpenHeat_v11_beta1_findings_report_CN_v2_2_FINAL.md  ← L3 (canonical)
                                      │
                                      ▼ (umbrella)
              docs/OpenHeat_ProjectSynthesis_v1.md  ← L1 (this doc)
                                      │
                                      ▼ (future)
              docs/v11/OpenHeat_v11_beta_formal_findings_report_CN.md  (14d, pending)
              docs/v11/OpenHeat_v11_gamma_findings_report_CN.md         (30d ML, conditional)
```

---

## Appendix C: Glossary

| Term | Meaning |
|---|---|
| **WBGT** | Wet Bulb Globe Temperature, 综合温/湿/风/辐射的 outdoor heat stress index. Singapore NEA 用 31°C 作 alerting threshold |
| **UTCI** | Universal Thermal Climate Index, 类似 WBGT 但 derivation 不同, EU 系常用 |
| **Tmrt** | Mean Radiant Temperature, SOLWEIG 输出的 radiative heat exposure 主要 metric |
| **PET** | Physiological Equivalent Temperature, Plymouth dissertation 用的 personal thermal comfort 指标 |
| **GEMA** | Geographic Ecological Momentary Assessment, mobile in-situ subjective survey, Plymouth diss 用法 |
| **GVI** | Green View Index, 街景图片估算的人眼绿视率 |
| **SVF** | Sky View Factor (0-1), 由地面看天空的开阔度, urban morphology 核心 metric |
| **UMEP** | Urban Multi-scale Environmental Predictor, QGIS plugin, 提供 SVF/shadow/SOLWEIG |
| **SOLWEIG** | SOlar and LongWave Environmental Irradiance Geometry, UMEP 内 physics module, 算 Tmrt |
| **LST** | Land Surface Temperature, Landsat / Sentinel-3 卫星反演, Cooling TP 用过 |
| **AOI** | Area of Interest. 本项目 = Toa Payoh HDB town. 100m grid 986 cells |
| **NEA** | National Environment Agency (Singapore), 提供 WBGT + realtime weather |
| **HDB** | Housing Development Board, 新加坡公共住房机构. Toa Payoh 是典型 HDB town |
| **HDB3D / URA** | HDB + Urban Redevelopment Authority building footprint data, v0.8 era building DSM source |
| **DSM / DEM** | Digital Surface Model / Digital Elevation Model. building DSM = ground + buildings; vegetation DSM = ground + canopy |
| **LOSO** | Leave-One-Station-Out cross-validation. 每个 fold 把一个 NEA station 当 test, 其他训练 |
| **M0-M7** | calibration ladder. M0=raw proxy, M1=global bias, M1b=period bias, M2=linear, M3=weather ridge, M4=+inertia, M5=+morph, M6=+overhead, M7=8-feat compact |
| **fixed_31 / best_F1 / recall_90 / precision_70** | 4 operating points on threshold scan: 固定 31°C / F1 最大 / recall ≥ 0.90 中 precision 最大 / precision ≥ 0.70 中 recall 最大 |
| **ablation A/B/C/D** | A = all stations, B = retrospective-eligible only, C = fresh v11 only, D = migrated only |
| **stale-dilution** | v1 era 假设: 旧/远 forecast paired observations 稀释 M3 MAE. v2 ablation **falsified** |
| **DSM-gap false positive** | v0.9 audit 发现: 旧 HDB3D+URA DSM 没记录的 buildings 导致 cell 被读成 open space → 假 high hazard. v10 修 |
| **overhead infrastructure** | 高架道路 / 高架轨道 / 人行天桥 / 连廊 / 车站 canopy. v10-δ 独立 layer 处理 (不烧进 building DSM) |
| **confident hotspot** | v10-ε SOLWEIG validation 后 base + overhead Tmrt 都高的 cell. TP_0565 / TP_0986 |
| **H10 keystone** | v11-β.1 fourth audit hypothesis: aggregator forward morph 后 M5/M6/M7 仍 bit-identical. **Confirmed**, 单机制 audit-proof framing |
| **bit-identity** | metric 等到所有 decimal 都相同 (vs statistically similar). v2.2 fourth audit 用作 regression invariant test |
| **practical significance threshold** | friend audit 4.3 设的 |Δ| ≥ 0.030°C 作 "meaningful contribution" cutoff. M4 advantage 全部 < 0.030°C |
| **Mercury Taskforce** | Singapore 国家级跨 37 机构 heat readiness 协调, 2025-03 成立 (Cooling TP Solution 2 reports into) |
| **Cooling TP** | Yiheng 早期组队项目 "Cooling Toa Payoh", 提了 cool roof + heat-resilient governance package. AOI 与本项目重合 |
| **EDSML** | Environmental Data Science & Machine Learning, Imperial College London MSc. Yiheng 准研究生方向 |
| **海绵城市** (sponge city) | 中国 / Singapore 系城市内涝 + 水资源管理思路, 强调 LID + 透水 + 绿色基建. Yiheng 实习方向, water-heat nexus 起源 |

---

## Appendix D: Connecting OpenHeat to my other work

| OpenHeat element | Plymouth diss connection | Cooling TP connection |
|---|---|---|
| **v0.7.1 vulnerability + exposure score** | (similar) Plymouth diss 测 individual-level wellbeing as function of objective + subjective exposure | Cooling TP Solution 2 用 elderly rate × walking exposure 算 priority hotspots |
| **v10-ε confident hotspots TP_0565 / TP_0986** | (placeholder) 这些 cells 是 Cooling TP 提案里 Solution 2 priority nodes 的候选 | Cooling TP Solution 2 "4 priority nodes" 的物理 grounding |
| **v11-β.1 M4 + hourly_max + fixed_31°C operational** | (placeholder) 类比 Plymouth GEMA 的 momentary appraisal: 每 small bucket 都要 separate evaluation | Cooling TP Solution 1 cool roof KPI 是 -10% CDH28, 同样 hourly-bucket cumulative; framework 一致 |
| **bit-identity audit (H10)** | (no direct link) | (no direct link). 是 v11 阶段独立学到的 audit technique |
| **water-heat nexus future direction** | (no direct link) | Cooling TP 没涉及 water dimension, 是 §7.3 方向 A 独立加入 |
| **AOI: Toa Payoh** | (no direct link, Plymouth 在英国) | **直接继承**: Cooling TP 选 Toa Payoh 是因 22.3% elderly + 1960-70s HDB + walking-dependent; OpenHeat AOI = 同一边界 |

---

## Appendix E: Anti-checklist (我**不**做的事)

为防 scope creep, 记录决定不做的事:

| 不做 | 为什么 |
|---|---|
| 替代 Open-Meteo 做 numerical weather prediction | OpenHeat scope 是 downscaling + calibration, 不重新发明 NWP |
| 替代 WBGT / UTCI 公式 | 用 published physics + calibration, 不重新发明 thermal index |
| Deep learning for full WBGT prediction | ML 只做 residual, philosophy 自 v0.9 freeze note 起 |
| 全新加坡 10m UTCI map | scope 是 Toa Payoh 100m, 不 over-extend |
| 真实 health outcome 预测 (中暑人数) | 数据不可得, 是 epidemiology task 不是 OpenHeat scope |
| 街道级 CFD wind field | 不是 OpenHeat 工程深度 (需要 specialized CFD team) |
| Operational public-health alert deployment | 还没到 14d formal pass + 30d ML pilot, 不发布 |
| 跨国 case study (Suzhou + 东京 + Phoenix) | EDSML 期间最多再加 1 城; 不分散 |
| 添加 social media / mobility data 做 exposure | 隐私 + 数据可得性 problem; behavioral exposure 走 GEMA-style 路径 |
| 加 building energy simulation (cooling load) | 跟 cool roof CapEx 相关但不是 OpenHeat 核心 |

---

## Appendix F: Quick-reference key numbers (for talking points)

| 数字 | 含义 | 来源 |
|---|---|---|
| **6,372** | current archive 行数 (5/11) | v11-β.1 |
| **27** | NEA WBGT stations | v0.6+ |
| **986** | Toa Payoh 100m grid cells | v0.7 |
| **1 of 27** | NEA stations in TP grid AOI (S128) → morphology unidentifiability 根源 | v11 H10 keystone |
| **25.8%** | 旧 HDB3D+URA building DSM completeness vs OSM (6 critical tile buffers) | v0.9-γ audit |
| **0.595°C / 0.605°C** | v0.9 24h M3 LOSO MAE / v11 hourly_mean M3 LOSO MAE | calibration floor evidence |
| **0.682441** | M5/M6/M7 hourly_max LOSO MAE, bit-identical 到 6 位小数 | H10 keystone confirmed |
| **0.639344** | M5/M6/M7 hourly_max ≥31°C F1 (fixed_31, 4 framings) | H10 / operational |
| **0.632** | M4 hourly_max fixed_31 F1 (operational primary) | v11-β.1 |
| **-1.140°C → -1.13~-1.04°C** | v0.9 M0 bias → v11 multi-day framings 复现 | proxy structural under-prediction |
| **~60°C / ~36°C** | TP_0565/TP_0986 vs TP_0433 SOLWEIG 13:00 Tmrt | v10-ε validation |
| **-17°C** | TP_0088 base → overhead scenario Tmrt drop | v10-ε overhead confounding evidence |
| **6/8** | bootstrap framings 中 M4-M3 CI 排除 0 | v2.2 fourth audit |
| **|Δ| < 0.030°C** | M4-M3 advantage all framings, below "practical meaningful" threshold | v2.2 fourth audit |
| **4 rounds** | peer audit completed | v11-β.1 |
| **22 patches** | cumulative across 4 audit rounds | v2.2 §2 patch lineage |
| **204** | ≥31°C events in 1,674 hourly buckets (4-day archive) | v11-β.1 |
| **~36,000** | expected archive 行数 at 14-day formal pass | projected |
| **1,500+** | required ≥31°C events for v1.1-γ ML pilot trigger | gates |

---

**Document end.**

*Maintainer*: Yiheng Pan
*First synthesis*: 2026-05-11
*Next review*: 14-day formal pass completion (~2026-05-25), 加 §3.7 formal pass results
*License*: personal project documentation

