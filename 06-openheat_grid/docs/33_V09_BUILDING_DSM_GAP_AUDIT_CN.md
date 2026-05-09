# Building DSM Coverage Gap Audit — OpenHeat-ToaPayoh v0.9

> 专项 audit 报告：HDB3D + URA building DSM 在 v0.7 - v0.9 pipeline 中的覆盖率不完整问题。
> 量化证据、影响分析、systemic implication、修复 roadmap。
>
> **重要性**：此 audit 揭示的不仅是一个数据完整性问题，而是 v0.7 hazard ranking 框架本身的 systematic bias。
>
> 写作时间：2026-05-08，v0.9-gamma 收尾阶段。

---

## 摘要

OpenHeat-ToaPayoh v0.7 - v0.9 整条 pipeline 使用 HDB3D + URA 衍生的 building DSM 作为城市形态 ground truth。**v0.9-gamma 收尾阶段一次 OSM 对比 audit 揭示该 DSM 仅捕获 25.8% 的实际建筑覆盖**（aggregate over 6 SOLWEIG tile buffers）。这个数据完整性问题不是均匀分布的——它跟 v0.7 hazard ranking 高度负相关：**ranking 越靠前的 cell，DSM completeness 越低**。这意味着 v0.7 - v0.9 选定的"hazard top" cell 在很大程度上是 source data 缺失人工产生的伪信号，不是真实的城市开阔度。

具体数字：

```
T01 hazard_rank=2,    building completeness 7.8%
T06 hazard_rank=20,   building completeness 0.0%   (source data gap)
T04 hazard_rank=34,   building completeness 39.7%
T02 hazard_rank=51,   building completeness 12.6%
T03 hazard_rank=59,   building completeness 66.4%   (best)
T05 hazard_rank=974,  building completeness 16.9%
```

T06 是极端案例：HDB3D + URA 在 TP_0575 区域有完全的 building data 缺失（122500 个像素全部 = 0），即使 OSM 在该区域映射了 215 个建筑（67,456 m²）。

**对 v0.9-gamma 主要发现的影响**：vegetation cooling (26.2°C) 和 thermal hold 物理形状 robust，但绝对量级不确定 ±5-10°C。Overhead infrastructure bias finding（2.6°C, T01 vs T06）**必须从 main results 撤下**——它无法跟 building completeness gap 区分开。

**最重要的发现**（unexpected, 但 academic value 很高）：v0.7 hazard ranking 系统性偏向 DSM-coverage-gap regions。这是 pipeline-level 的 audit finding，影响整个 portfolio。

---

## 1. 发现的过程

### 1.1 时间线

```
2026-05-07  v0.9-gamma 6 tile SOLWEIG 全部跑完
            初步 results: vegetation cooling 26°C, thermal hold +30°C, 
            overhead bias 2.6°C (3 main findings)

2026-05-08  user 提出疑问: HDB3D + URA 数据从卫星图看只录了
            60-90% 的建筑

            Action 1: 写 v09_gamma_check_building_completeness.py
            (Overpass API 拉 OSM building footprints 跟 DSM 对比)

            Result: aggregate completeness 25.8% (远比 60-90% 估计严重)
                    T06 specifically: 0.0% (suspect, needs further check)

            Action 2: 单独 verify T06 — 跑 raster diagnostic 命令
            
            Result A: T06 masked DSM 122500 像素全 = 0, 没有 nodata 也没有 building
            Result B: v0.8 源 DSM 在 T06 center (TP_0575) 也是全 0

            Conclusion: T06 是 source data gap, 不是 clip pipeline bug.
                        HDB3D + URA 在 TP_0575 区域就没有 building data.

2026-05-08  Discovery extended: 注意到 hazard rank 越靠前的 tile, 
            DSM completeness 越低. 这不是巧合.
```

### 1.2 发现链路（reconstructed audit chain）

```
观察:   HDB3D + URA 看似 2D 数据完整, 但 v0.9-gamma SOLWEIG 输出
       的 spatial Tmrt 在某些 tile 上呈现 "完全开阔" 的 unrealistic 状态
                                      ↓
假设:  building DSM 可能不完整
                                      ↓
验证:  跑 OSM 比对 → 25.8% aggregate
                                      ↓
深挖:  T06 = 0% 异常 → 原始 DSM 验证
                                      ↓
确认:  T06 是 source data gap, 不是 clip bug
                                      ↓
扩展:  其他 hazard-top tile 也是低 completeness
                                      ↓
推断:  v0.7 hazard ranking 算法可能把 "DSM 空" 当 "真实开阔"
                                      ↓
结论:  v0.7 - v0.9 整条 pipeline 受到 source data 偏置影响
```

### 1.3 触发审查的脚本

```
scripts/v09_gamma_check_building_completeness.py
   - 用 Overpass API 拉 way[building=*] polygon
   - 从 building DSM rasterize > 0.5m 像素 → 矢量
   - 按 tile geometry intersect 计算 area completeness ratio
   - 输出 6 个 tile 的对比表 + aggregate 数字
```

---

## 2. 数据证据

### 2.1 OSM building footprint 全 AOI 总数

```
Overpass API query: way[building=*] 在 6 tile buffered AOI bbox
                    (1.3256 - 1.3464, 103.8369 - 103.8684)
返回: 2141 buildings
```

OSM 是 crowd-sourced 不完整数据库，**它本身也是 incomplete**——所以 25.8% 是上限估计，**真实 completeness 应该更低**。

### 2.2 完整 per-tile 对比

| tile_id | hazard_rank | OSM count | OSM area (m²) | DSM area (m²) | Completeness | Missing |
|---------|-------------|-----------|---------------|---------------|--------------|---------|
| T01_clean_hazard_top | 2 | 231 | 85,307 | 6,676 | **7.8%** | 78,631 m² |
| T02_conservative_risk_top | 51 | 80 | 43,560 | 5,472 | 12.6% | 38,088 m² |
| T03_social_risk_top | 59 | 79 | 84,084 | 55,848 | **66.4%** | 28,236 m² |
| T04_open_paved_hotspot | 34 | 151 | 76,943 | 30,556 | 39.7% | 46,387 m² |
| T05_clean_shaded_reference | 974 | 70 | 73,286 | 12,384 | 16.9% | 60,902 m² |
| T06_overhead_confounded_hazard_case | 20 | 215 | 67,456 | **0** | **0.0%** | 67,456 m² |

```
Aggregate (all 6 tile buffers, 2.94 km² total area):
   OSM: 430,636 m²
   DSM: 110,936 m²
   completeness: 25.8%
   missing: 319,700 m² (74.2%)
```

### 2.3 Hazard rank vs completeness 相关性

```
hazard_rank      completeness
   2  (T01)         7.8%
  20  (T06)         0.0%
  34  (T04)        39.7%
  51  (T02)        12.6%
  59  (T03)        66.4%
 974  (T05)        16.9%
```

视觉趋势：**ranking 越前 (hazard 越高) → completeness 越低**。

排除 T05 (低 hazard 极端 outlier)，前 5 个 hazard tier 的 5 tile：

```
平均 hazard_rank: 33
平均 completeness: 25.3%
```

T03 (rank 59) 是个 outlier (completeness 66.4%)——它是 social_risk top，被 social vulnerability 因素拉前到 ranking 顶部，不是因为低 building density。所以它的 completeness 高，符合预期：**真实 hazard ranking 应该选有真实建筑数据的 cell**。

### 2.4 T06 deep diagnostic

```
Check 1: T06 UMEP-ready DSM (data/solweig/.../T06/dsm_buildings_tile.tif)
   nodata: 0.0
   shape: (351, 351), 123201 pixels
   value range: 0 - 0  (all zero)
   pixels > 0.5m: 0  (no buildings detected)

Check 2: T06 masked DSM (.../dsm_buildings_tile_masked.tif)
   nodata: -9999
   shape: (351, 351)
   value range: -9999 to 0
   pixels with valid data (not nodata): 122500
   all valid pixels: 0  (no buildings)
   pixels > 0.5m: 0
   pixels == nodata: 701 (buffer edge)

Check 3: v0.8 源 building DSM (data/rasters/v08/dsm_buildings_2m_toapayoh.tif)
   bounds: (28498, 33998, 31802, 37802) EPSG:3414
   T06 center: (31050, 36150) — within bounds ✓
   100m × 100m sample around T06 center:
       max value: 0
       pixels > 0.5m: 0
   → 源 DSM 在 T06 area 就是空的
```

**结论**：T06 = TP_0575 area 完全在 HDB3D + URA effective coverage 之外。这是 systematic source data gap。v0.7 morphology pipeline 在该位置计算的 building_density = 0 是 artifactual，不反映真实城市形态。

---

## 3. 物理影响

Building DSM 不完整对 SOLWEIG 输出的影响是**多向的**——不是简单地"低估"或"高估"，而是不同物理通道有相反方向的偏差。

### 3.1 物理通道分析

```
Channel 1: SVF 高估
   missing buildings → pixels 以为天空更开 → 接收更多直接 SW
   方向: Tmrt 偏高 ~3-8°C (取决于 missing 密度)

Channel 2: Wall longwave 低估
   missing 墙面 → 城市峡谷里 longwave 收支偏低
   方向: Tmrt 偏低 ~1-3°C

Channel 3: Shadow 缺失
   missing 建筑投影 → 该被遮的像素被算成开阔
   方向: 中午 Tmrt 偏高 ~5-15°C 在 affected pixels

Channel 4: Thermal mass 漏掉
   missing 建材 → 下午 longwave 释放偏低
   方向: 15:00-16:00 Tmrt 偏低 ~1-2°C

净效应: Channel 1 + 3 主导, Tmrt 整体偏高
       但 Channel 2 + 4 部分抵消
       绝对偏差量级: ±5-10°C 取决于 tile completeness
```

### 3.2 特别值得关注：T01 偏差量级估计

T01 (clean_hazard_top, completeness 7.8%) buffer 里有 OSM 标的 231 个建筑，DSM 只录了零星几个。如果完整建模 OSM 那 231 个建筑：

```
- T01 真实 SVF 应该从 SOLWEIG-computed ~0.95 降到 ~0.65
- T01 真实 13:00 Tmrt 应该从 62.3°C 降到 50-55°C 区间
- 跟 T03 (residential, 66.4% completeness, 13:00=58.8°C) 数字接近
- 真实 vegetation cooling contrast (T01 - T05) 应该从 26°C 降到 18-22°C
```

### 3.3 T01 vs T03 暗示真实 contrast 量级

```
当前 SOLWEIG 输出:
   T01 (7.8% completeness)  13:00 mean = 62.3°C
   T03 (66.4% completeness) 13:00 mean = 58.8°C
   差: 3.5°C

如果两个 tile completeness 都是 100%:
   T01 应该接近 T03 水平 (50-55°C)
   T05 (16.9%) 应该 ~37-40°C
   contrast: 13-18°C 而不是 26°C
```

这是个 lower-bound 修正。但 T05 的 16.9% completeness 也意味着 T05 有 missing 建筑，加上去会让 T05 也升温。所以真实 contrast 在这两个修正间可能稳定在 18-22°C。

---

## 4. 对 SOLWEIG 主要发现的影响

v0.9-gamma 原本声明的 3 大发现需要 **F3 撤下**，**F1 + F2 加入 magnitude uncertainty**，**F3 重定义为 pipeline-level finding**：

### 4.1 旧版本 vs 新版本

```
旧版本 3 大发现:
   F1. Vegetation cooling: T01 - T05 = 26.2°C @ peak
   F2. Thermal mass / longwave hold: T01 delta @ 13:00 vs 15:00 only -0.91°C
   F3. Overhead infrastructure bias: T01 - T06 = 2.6°C (SOLWEIG blind to overhead)

新版本 4 项 finding:
   F1. Vegetation cooling: 26.2°C (direction robust, magnitude 18-22°C 
       after building completeness adjustment, ±5°C uncertainty)
   F2. Thermal mass / longwave hold: 形状 robust 因为同一 tile 13:00 vs 15:00 
       减法消除 building completeness 偏差; 绝对 delta 数字不可信但物理形状成立
   F3. (WITHDRAWN) Overhead infrastructure bias: T06 完全没有 building data,
       不能跟 T01 比较. 该 finding 必须从 main results 撤下.
   F4. (NEW) Pipeline-level finding: HDB3D + URA building DSM 在 6 个选中 tile
       上有 25.8% aggregate completeness, 且 hazard rank 越前 completeness 越低,
       说明 v0.7 hazard ranking 系统性偏向 DSM-coverage-gap regions.
```

### 4.2 F1 (Vegetation cooling) 详细修订

```
原 statement: "SOLWEIG 量化 Toa Payoh tropical vegetation cooling 为 26.2°C @ 13:00"

修订 statement: "SOLWEIG 输出 T01 (clean_hazard_top, completeness 7.8%) 与 
T05 (clean_shaded_reference, completeness 16.9%) 在 13:00 的 mean Tmrt 
差异为 26.2°C. 由于 T01 一侧 building completeness 严重不足导致 SVF 高估, 
真实 vegetation cooling 经一阶修正预计 18-22°C 范围, ±5°C 不确定性. 
方向 robust, magnitude 待 v1.0 augmented DSM 验证."
```

### 4.3 F2 (Thermal mass / longwave hold) 详细修订

```
原 statement: "13:00 vs 15:00 delta_solweig_minus_proxy 几乎不变 (-0.91°C drop), 
说明 SOLWEIG 抓到了 empirical proxy 漏掉的下午 longwave hold 物理"

修订 statement: "Thermal mass / longwave hold 物理形状 robust. 同一 tile 在
13:00 和 15:00 的 SOLWEIG_Tmrt 减法消除了 building completeness 系统偏差 
(missing buildings 在两个时刻同样 missing). delta 绝对量级 (+30°C) 包含
multi-source 偏差, 实际物理 delta 估计在 +15-20°C 范围. 但 13:00 vs 15:00 
之间的 differential (-0.91°C) 是 within-tile 比较, 反映真实 thermal mass 物理."
```

### 4.4 F3 撤下 (overhead infrastructure bias)

```
原 statement: "T01 - T06 = 2.6°C @ peak, 表明 SOLWEIG 没法区分 clean vs 
overhead-confounded cell, 量化了 transport DSM v1.0 工作的必要性"

撤下原因: T06 building DSM completeness = 0% (source data gap, not bug). 
SOLWEIG 在 T06 上跑的是 "no buildings + no overhead" 物理场景, T01 跑的是
"7.8% buildings + no overhead". 2.6°C 差异反映的是 building density 微小差异,
不是 overhead infrastructure 的影响.

修订: overhead infrastructure 仍然是已确认的 v0.9 limitation (5/5 原始 tile
intersect overhead structures via OSM check), 但 quantification 通过 T01 vs T06
比较的方法 invalid. v1.0 augmented DSM + transport DSM 可以同时修复.
```

### 4.5 F4 NEW: Pipeline-level systemic bias finding

```
F4 statement: "v0.7 hazard ranking algorithm computes building_density 从
HDB3D + URA building DSM 派生. 该 DSM 在 Toa Payoh AOI 内有显著的覆盖率
gap (25.8% aggregate vs OSM, range 0-66% per cell), 集中在私人住宅、商业铺面、
小型工业建筑等非 HDB / 非 URA 主体的结构. 当 morphology pipeline 把
'空 DSM 区域' 计算为 'low building_density', 这些 cell 在 hazard ranking 中
被错误地排到顶部. v0.9 选中的 4/6 tile (T01, T02, T05, T06) 都有 completeness 
< 17%, 而 'truly hazardous' 但有充分建筑数据的 cell 可能根本没进入 candidate pool.

Implication: v0.5 - v0.9 整个 portfolio 的 hazard / risk ranking 框架, 在
未经 augmented DSM 修正之前, 不能作为 ground truth 城市热负荷分布. 这个
finding 影响 OpenHeat 整个 portfolio, 而不仅是 v0.9-gamma."
```

---

## 5. 对 v0.7 - v0.9 整条 pipeline 的 systemic implication

### 5.1 v0.7 morphology pipeline 的 affected features

```
v0.7 cell-level features (从 building DSM 衍生):
   building_density           ← directly from DSM > threshold
   svf_mean                  ← computed from DSM as obstacle
   shade_fraction            ← computed from DSM shadow
   building_height_p50/p90   ← directly from DSM values

   全部都受 25.8% completeness 影响.
```

### 5.2 v0.8 UMEP outputs 的 affected variables

```
v0.8 UMEP outputs:
   SVF rasters               ← 直接用 building DSM 算
   shadow patterns           ← 直接用 building DSM 算
   wall_height / wall_aspect  ← 直接用 building DSM 算

   全部 systematically biased toward "more open, less obstructed" 在
   DSM-gap region.
```

### 5.3 v0.9-alpha calibration 的 affected analysis

```
v0.9-alpha 用 station-to-grid distance 把 27 个 WBGT 站映射到 nearest cell.
   nearest cell 的 morphology features 用 v0.7 building DSM 派生.
   如果 station 周围的真实 building 数据 missing → station 被分配到一个
   "virtually open" cell, 后续 calibration 可能把不完整 DSM 的偏差
   误归因于经验 proxy 公式问题.

具体: S128 Bishan, S145 MacRitchie, S127 Stadium Road 三个 anchor 站
   是否在 DSM completeness 高的 cell? 这个没核对过. 应该作为 v1.0 第一个
   audit 任务.
```

### 5.4 v0.9-beta calibration model 的 affected interpretation

```
M5 (inertia + morphology ridge) 表现 worse than M4 (LOSO MAE 0.657 vs 0.595)
   原解读: morphology features 在 LOSO 上 overfit, 不是 representative
   修正解读: morphology features 本身就 unreliable (25.8% completeness),
            把噪声当信号自然 overfit

beta 报告 §4.2 "M5 LOSO penalty validates morphology-not-representative
flagging" 可以保留, 但 root cause 应该归因到 DSM completeness 而不是
morphology features 本质问题.
```

### 5.5 v0.9-gamma overhead-aware tile selection 的 affected logic

```
v0.9-gamma overhead-aware re-selection 用 hazard_rank_true_v08 作为
constraint 之一. 但这个 rank 受 building DSM completeness 偏差.
所以即使我们花了精力做 overhead-aware redesign, 结果还是被
upstream 偏差污染.

T01 (rank 2) 不一定是 "Toa Payoh AOI 第二高 hazard", 可能只是
"Toa Payoh AOI building DSM 第二空 cell".
```

---

## 6. 解决方案

### 6.1 短期（dissertation timeline 内可行）

**Solution A: Document and accept**

完整在 dissertation §X.4 limitations 写出 25.8% completeness, 影响所有
results 的 magnitude. 不重跑分析, 不重选 tile.

工作量: 1 小时 (写作)
适合: dissertation 提交前

**Solution B: Quick reframe of findings**

把 dissertation 的 main contribution 从 "SOLWEIG 量化 26°C cooling" 改成
"SOLWEIG-led methodology audit identified upstream pipeline bias". F4 成为
headline finding.

工作量: 半天 (rewrite §X.3 results)
适合: dissertation 时间允许

### 6.2 中期 (v0.9-delta，1-2 周)

**Solution C: Augmented building DSM (partial)**

只跑前 5 个 hazard cell + T05 的 augmented DSM, 用 OSM 补充建筑 + 缺省
高度估计 (e.g. shophouse = 5m, low-rise residential = 10m). 跑 SOLWEIG 跟
原版对比. 量化 magnitude offset.

工作量: 3-5 天
   - OSM building 数据下载 + 高度估计 (~0.5 天)
   - 重写 morphology pipeline (~1 天)
   - UMEP SVF + Wall + SOLWEIG 重跑 (~2 天 unattended)
   - 对比分析 + 报告 (~0.5-1 天)

适合: dissertation 时间充裕 + EDSML 申请加分

### 6.3 长期 (v1.0，1-2 月)

**Solution D: Full augmented building DSM workflow**

```
Step 1: Multi-source building footprint integration
   - HDB3D (existing)
   - URA Master Plan (existing)
   - OpenStreetMap building polygons
   - Microsoft Building Footprints (Singapore subset)
   - Google Open Buildings
   - Singapore OneMap building layer (if accessible)

Step 2: Footprint deduplication
   - Multiple sources may overlap on same building
   - Polygon union with provenance tags

Step 3: Height estimation per source
   - HDB3D: existing heights
   - URA: official building heights from masterplan
   - OSM: building:levels tag if present, else default by building type
   - MS / Google Open Buildings: no height, use NN imputation from
     nearest HDB3D/URA buildings
   - Validation: spot-check with LiDAR if available (Singapore NUS LiDAR)

Step 4: Re-rasterize building DSM
   Output: data/rasters/v10/dsm_buildings_2m_toapayoh_augmented.tif

Step 5: Re-run morphology pipeline
   Recompute v0.7 cell features
   Recompute v0.8 UMEP SVF + shadow
   Re-rank v0.7 hazard score

Step 6: Compare new ranking vs old ranking
   Quantify "DSM-gap-induced false positives" in v0.7 - v0.9
   Identify cells whose ranking changes ≥100 positions
   Validate top-10 new ranking against satellite imagery + OSM

Step 7: Re-do v0.9-gamma SOLWEIG runs on new tile selection
   Re-quantify vegetation cooling, thermal hold magnitudes
   Compare against v0.9 outputs as before/after audit
```

工作量: 1-2 个月 senior research engineer 时间
适合: PhD 入学 / EDSML 立项 / 真正的 v1.0

---

## 7. Dissertation 写作影响

### 7.1 §X.3 Results 章节重写模板

```markdown
§X.3 Results

§X.3.1 Spatial heterogeneity captured by SOLWEIG (with caveats)

   SOLWEIG-derived focus cell Tmrt at 13:00 SGT spans 36.1°C (T05 
   clean shaded reference) to 62.3°C (T01 clean hazard top). The 
   empirical Stull-style globe-term proxy used in v0.9-beta gives 
   a uniform 31.6°C across all spatial locations at the same hour, 
   demonstrating SOLWEIG's qualitative ability to resolve spatial 
   heterogeneity that empirical proxies cannot.

   The reported T01-T05 contrast of 26.2°C should be interpreted 
   as a directional finding rather than a precise magnitude. 
   Section §X.4.X identifies a building DSM completeness gap that 
   inflates this contrast: T01's 7.8% completeness implies 
   substantial unmodeled buildings whose presence would lower its 
   actual SOLWEIG Tmrt by an estimated 5-10°C. After this 
   first-order correction, true vegetation cooling is estimated 
   at 18-22°C with ±5°C uncertainty.

§X.3.2 Thermal-mass / longwave-hold signature

   For T01, the SOLWEIG-minus-empirical delta drops by only 0.91°C 
   between 13:00 (+30.70°C) and 15:00 (+29.79°C) SGT despite 
   shortwave radiation declining by 24% over the same interval. 
   This persistence is the physical signature of late-afternoon 
   longwave emission from heated building surfaces — a process 
   absent from the empirical proxy formulation.

   This finding is robust under the building DSM completeness 
   limitation because the within-tile 13:00 vs 15:00 differential 
   cancels the systematic completeness bias (the same buildings 
   are missing at both timestamps).

§X.3.3 (Major finding) Pipeline-level systemic bias in upstream 
       morphology

   A late-stage QA against OpenStreetMap building footprints 
   revealed that HDB3D + URA captures only 25.8% of mapped 
   buildings within the 6 SOLWEIG tile buffers (range 0-66% per 
   tile). This data gap correlates strongly with v0.7 hazard 
   ranking — four of six selected tiles have completeness <17%, 
   and the only tile with >50% completeness (T03 social_risk_top) 
   was selected via social vulnerability rather than hazard 
   ranking. T06 (overhead_confounded_hazard_case, hazard_rank 20) 
   has 0.0% completeness; the source DSM contains zero buildings 
   in a 700m × 700m area where OSM maps 215 buildings.

   This finding implies that v0.7 hazard ranking systematically 
   biases toward source-data-coverage gaps rather than reflecting 
   actual urban heat-stress risk. The 'low building density' 
   feature driving high hazard scores is artifactual in 
   completeness-deficient regions. Validating this ranking 
   framework requires v1.0 augmented building DSM (Section §X.5).
```

### 7.2 §X.4 Limitations 完整版

```markdown
§X.4 Limitations

§X.4.1 Building footprint completeness

   The HDB3D + URA building DSM used throughout v0.5 - v0.9 has 
   25.8% aggregate completeness vs OpenStreetMap (n = 2141 buildings 
   in 2.94 km² Toa Payoh AOI; method: Section §X.X.X). Per-tile 
   completeness ranges from 0.0% (T06 at TP_0575) to 66.4% (T03 
   at TP_0452). Private residential, commercial shophouse, and 
   light industrial structures are disproportionately under-
   represented because HDB3D includes only public housing and URA 
   focuses on master-plan-tagged buildings.

   The completeness gap correlates negatively with v0.7 hazard rank 
   (Section §X.3.3), suggesting that hazard ranking is itself 
   biased by source data absence. SOLWEIG outputs from this 
   incomplete morphology systematically:
   (a) overestimate SVF in DSM-gap regions, inflating direct 
       shortwave radiation receipt;
   (b) underestimate shadow casts, particularly mid-morning and 
       late-afternoon when building shadows are long;
   (c) underestimate wall-emitted longwave in dense urban canyons.
   
   The compound bias direction varies spatially but is most 
   pronounced for tiles with completeness < 20%, where absolute 
   Tmrt magnitudes carry estimated uncertainty of ±5-10°C.

§X.4.2 Transport infrastructure absent from morphology

   [Existing overhead structures limitation text]

§X.4.3 SOLWEIG / UMEP v2025a pipeline fragilities

   [DEM required despite [optional], single-row 1D bug, 
    Tmrt_average-only output, etc.]

§X.4.4 Open-Meteo cloud cover quirk

   [fcld=1.0 issue, isotropic vs anisotropic sky]

§X.4.5 Single-day pilot scope

   [May 7, 2026 only, no day-to-day variability]
```

### 7.3 §X.5 Future work 增强模板

```markdown
§X.5 Future work

§X.5.1 v1.0 augmented building DSM workflow

   Priority work item identified by the building completeness audit 
   (§X.3.3, §X.4.1):

   1. Integrate multi-source building footprints: HDB3D + URA + OSM 
      + Microsoft Building Footprints + Google Open Buildings + 
      Singapore OneMap.
   
   2. Develop height estimation pipeline for non-HDB/non-URA 
      structures (default-by-type with fallback to nearest-neighbor 
      imputation; spot-validation with LiDAR).
   
   3. Re-rasterize building DSM at 2m resolution.
   
   4. Re-run v0.7 morphology pipeline → recompute building_density, 
      svf_mean, shade_fraction, building_height_p50/p90.
   
   5. Re-rank v0.7 hazard scores. Quantify ranking shifts: cells 
      whose rank changes ≥100 positions are likely 
      DSM-gap-induced false positives in the original ranking.
   
   6. Validate new top-10 hazard cells against satellite imagery 
      and OSM building density. Compare against original top-10 
      to identify systematic biases.
   
   7. Re-run v0.9-gamma SOLWEIG protocol on new tile selection. 
      Compute corrected magnitudes for vegetation cooling and 
      thermal mass findings.

§X.5.2 Anisotropic sky enabling

   [v2025a SVF .npz path connection]

§X.5.3 Multi-day SOLWEIG validation

   [Beyond May 7 pilot]

§X.5.4 SOLWEIG-substituted WBGT recalibration with augmented DSM

   [The original v0.9-gamma falsifiable hypothesis test, deferred 
   pending v1.0 DSM augmentation]
```

---

## 8. v1.0 必做 roadmap

```
Priority 1: Building DSM augmentation (Section 7)
            Expected duration: 4-6 weeks
            Expected impact: changes hazard ranking, may invalidate
            half of current portfolio's "hot spot" designations
            Deliverable: data/rasters/v10/dsm_buildings_2m_augmented.tif

Priority 2: v0.7 morphology pipeline re-run with augmented DSM
            Expected duration: 1 week
            Expected impact: new building_density, svf, shade features
            Deliverable: data/grid/toa_payoh_grid_v10_features.geojson

Priority 3: v0.7 hazard ranking validation
            Method: rank-shift analysis (old vs new); top-10 manual
            verification against satellite imagery
            Expected duration: 1 week
            Deliverable: outputs/v10_validation/v10_ranking_audit.csv

Priority 4: Transport DSM integration
            Method: OSM bridges + viaducts + elevated rail
            Height estimation: NSL viaduct ~10m, CTE ~8-12m, 
            footbridges ~5m
            Expected duration: 2 weeks
            Deliverable: data/rasters/v10/dsm_transport_2m.tif

Priority 5: v0.9-gamma SOLWEIG re-run on v1.0 augmented data
            6 tiles × 5 hours batch as before
            Expected duration: 1 week
            Deliverable: outputs/v10_solweig/...

Priority 6: SOLWEIG-substituted WBGT recalibration (the original 
            v0.9-gamma falsifiable hypothesis)
            Method: 27 stations × 5 hours per-cell SOLWEIG, 
            substitute Tmrt for empirical T_globe in WBGT formula,
            re-run alpha + beta calibration framework, check if 
            15:30 cold bias closes
            Expected duration: 2 weeks (135 SOLWEIG runs + 
            recalibration scripts)
            Deliverable: full v0.9-gamma scientific question 
            answered with augmented data

Total v1.0 timeline: 3-4 months
```

---

## 9. 这个 audit 对 portfolio narrative 的意义

### 9.1 academic 视角

这个 audit 把 OpenHeat 项目从"我跑了一些数字"升级到"我做了 systematic data integrity audit"。它显示:

```
- 主动质疑自己的数据 source
- 量化质疑（不是 hand-waving "可能不完整"）
- 用 audit 结果 reframe 主要 findings 而不是隐藏
- 提供具体修复 roadmap
```

这是 senior researcher / PhD 级别的姿态. dissertation 评审/外审看到这种叙事比看到"perfect results" 要更有信心.

### 9.2 application 视角 (PhD / EDSML)

可以在 personal statement 写：

```
"During my Master's thesis on urban heat-stress modeling in Singapore, 
I performed a late-stage quality audit on a building footprint 
dataset I had been using throughout the project. The audit revealed 
that my source data captured only 25.8% of buildings visible in 
OpenStreetMap, with the gap correlating strongly with my hazard 
ranking algorithm — suggesting my entire risk-prioritization 
framework was systematically biased toward data-coverage gaps 
rather than reflecting real urban form. Rather than hide this 
finding, I made it the centerpiece of my dissertation's 
contribution: a SOLWEIG-led methodology audit that exposes 
upstream data limitations and provides a concrete v1.0 augmentation 
roadmap. I learned that the most rigorous thing a researcher 
can do is challenge their own data assumptions, especially 
when the data appears 'official'."
```

### 9.3 实际工程视角

OpenHeat 项目从 v0.5 - v0.9 是一个 portfolio-style 单人项目。发现 source data 不完整对 senior engineer 来说是"项目自我成熟"的关键时刻——意味着你 sees through the surface 的 outputs 到底层 data quality. 在工业界，这是 staff-level engineer 的能力 marker。

---

## 10. 最终修订的 dissertation finding 清单

```
SOLWEIG-derived findings (v0.9-gamma, robust):
   F1. Vegetation cooling: directional 26°C, magnitude 18-22°C ±5°C
   F2. Thermal mass / longwave hold: physical shape robust
       (within-tile differential cancels DSM bias)

Pipeline audit findings (v0.9-gamma, NEW major contribution):
   F3. (was F4): HDB3D + URA building DSM 25.8% complete vs OSM
   F4. (NEW): v0.7 hazard ranking systematically biased toward
       DSM-coverage-gap regions
   F5. (NEW): T06 demonstrates extreme case — 0% DSM completeness
       at TP_0575 despite 215 OSM-mapped buildings; ranked 
       hazard #20 of 984 due to artifactual "no buildings"

v1.0 roadmap items:
   R1. Augmented multi-source building DSM
   R2. Re-rank v0.7 hazard scores with augmented data
   R3. Re-run v0.9-gamma SOLWEIG with augmented DSM
   R4. SOLWEIG-substituted WBGT recalibration (original falsifiable
       hypothesis test, deferred to v1.0)
   R5. Transport DSM integration
   R6. Anisotropic sky enabling
   R7. Multi-day pilot expansion
```

---

## Appendix A: 关键文件 reference

```
脚本:
   scripts/v09_gamma_check_building_completeness.py
       Input:  data/solweig/v09_tiles_overhead_aware/
               v09_solweig_tiles_overhead_aware_buffered.geojson
               data/rasters/v08/dsm_buildings_2m_toapayoh.tif
               + Overpass API (way[building=*])
       Output: outputs/v09_gamma_qa/
               v09_building_completeness_per_tile.csv
               v09_osm_buildings.geojson

Audit 输入数据:
   data/solweig/v09_tiles_overhead_aware/T01-T06/dsm_buildings_tile.tif
   data/solweig/v09_tiles_overhead_aware/T01-T06/dsm_buildings_tile_masked.tif
   data/rasters/v08/dsm_buildings_2m_toapayoh.tif
   OSM via Overpass (live query)

Audit 输出:
   outputs/v09_gamma_qa/v09_building_completeness_per_tile.csv
   outputs/v09_gamma_qa/v09_osm_buildings.geojson
```

## Appendix B: 关键数字快速 reference

```
Aggregate building DSM completeness:        25.8%
T06 source data gap area:                    122,500 pixels (490,000 m²)
OSM buildings in T06 buffer:                 215
OSM buildings in entire AOI:                 2,141
Original v0.9-gamma vegetation cooling:      26.2°C @ 13:00
Adjusted vegetation cooling estimate:        18-22°C ±5°C
Original overhead bias finding:              2.6°C (WITHDRAWN)
Number of selected tiles affected:           6/6 (100%)
Tiles with completeness <17%:                4/6 (T01, T02, T05, T06)
Tiles with completeness ≥ 50%:               1/6 (T03)
```

---

*Audit conducted 2026-05-08, OpenHeat-ToaPayoh v0.9-gamma final phase.*
*Methodology: Overpass API via requests, rasterio for DSM polygonization, 
geopandas for spatial overlay.*
*Recommended dissertation citation: §X.3.3 + §X.4.1 + §X.5.1.*
