# OpenHeat v1.2-beta SOLWEIG typology pilot runbook — updated after Core 8 base

**Document date:** 2026-05-24  
**Update reason:** Core 8 base matrix completed; manual GIS interpretation updated for TP0835 / TP0565 / TP0059 / TP0986.  
**Status:** ready for overhead smoke planning.

---

## 0. Current status

Completed:

```text
Wave 0:
  TP0986 h13 base smoke test — PASS

Wave 1:
  TP0986 / TP0542 / TP0059 × h10/h13/h16 base — PASS

Core 8 base:
  8 cells × 5 hours × base = 40 SOLWEIG runs — PASS
```

Technical pass criteria met:

```text
Raster exists: 40 / 40
Focus cell exists: 40 / 40
qa_status: all ok
```

---

## 1. Updated Core 8 labels

| cell_id | updated typology | 中文标签 | base interpretation |
|---|---|---|---|
| TP_0565 | `school_gate_asphalt_road_edge_hot_anchor` | 幼儿园门口 / 柏油道路边界热锚点 | 高 p90 稳定；可能与 cell 内较大柏油路面/道路边界有关 |
| TP_0986 | `low_rise_residential_high_exposure_null_control` | 低层分散住宅 / 高暴露 null-control | 低矮分散住宅、低植被、硬质面/道路暴露强；base p90 稳定最高 |
| TP_0366 | `school_gate_bus_stop_mixed_waiting_node` | 学校门口 + 公交候车混合等待节点 | 行人相关性强，中高暴露 |
| TP_0542 | `river_edge_shaded_pedestrian_walkway` | 河边树荫步道 | mean 低、p90 捕捉中午暴晒 pocket，支持 p90 target |
| TP_0627 | `street_canyon_wall_adjacent_low_svf_corridor` | 街道峡谷 / 贴墙 / 低SVF走廊 | 中高暴露，代表街谷/低SVF走廊 |
| TP_0326 | `stable_high_rise_residential_estate` | 稳定高层住宅小区 | mean 较低但 p90 较高，说明高层小区是 mixed-cell |
| TP_0059 | `open_paved_hardscape_parking_lot` | 开阔硬质铺装 / 露天停车场诊断样本 | 高暴露 hardscape，但不应预设为最热 |
| TP_0835 | `wooded_green_space_low_radiative_diagnostic` | 植被覆盖树林 / 低辐射绿地诊断样本 | 极低且几乎无空间变化，说明模型中为强、均质植被遮阴 |

---

## 2. Core 8 base interpretation update

### 2.1 TP0835 relabel

TP0835 must no longer be described as open grass.

Manual QGIS and 2026 Google Satellite review indicate that this cell has changed from open field / grass to vegetation-covered wooded green space. Its SOLWEIG output is extremely low and almost spatially uniform:

```text
mean ≈ p90 ≈ max
```

Interpretation:

```text
TP0835 = dense vegetation / wooded green-space low-radiative diagnostic
```

### 2.2 TP0059 hardscape caveat

TP0059 is a surface/hardscape diagnostic, not a pedestrian hotspot.

Interpretation:

```text
TP0059 = open paved hardscape / parking-lot diagnostic
```

It should not be expected to outrank TP0986 / TP0565 in all hours.

### 2.3 TP0986 null-control

TP0986 is a low-rise, low-vegetation residential high-exposure null-control.

Interpretation:

```text
No mapped overhead should mean overhead_as_canopy delta is near zero.
```

### 2.4 TP0565 asphalt road-edge hot anchor

TP0565 is a school/kindergarten gate and road-edge mixed cell. Its high p90 likely reflects nearby asphalt road fraction and hardscape exposure.

Interpretation:

```text
TP0565 = school-gate / asphalt road-edge hot anchor
```

---

## 3. 100m mixed-cell interpretation rule

All results are 100m mixed-cell summaries.

Do not interpret them as point-level pedestrian Tmrt.

Use:

```text
tmrt_mean_c
tmrt_p90_c
tmrt_max_c
```

together.

Interpretation rule:

```text
mean = general cell condition
p90 = stable upper-tail pedestrian-relevant radiant exposure pocket
max = extreme pixels; diagnostic only unless supported by p90/p95
```

---

## 4. Updated Optional / Diagnostic cells

| cell_id | status | interpretation |
|---|---|---|
| TP_0208 | optional diagnostic | unmapped micro-shelter / school-gate shade corridor; not mapped overhead |
| TP_0802 | optional diagnostic | river-edge / station-rail mixed |
| TP_0088 | legacy diagnostic | vehicle-overhead stress-test; not pedestrian Core |
| TP_0916 | legacy diagnostic | rail/depot overhead diagnostic; not pedestrian Core |
| TP_0433 | optional diagnostic | forest canopy lower-bound; replaced by TP0542 for pedestrian shaded reference |
| TP_0857 | conditional optional | newly completed HDB canyon; use only if DSM/HDB3D current |
| TP_0492 | drop/replace | utility / grass / tree mixed, weak pedestrian relevance |
| TP_0828 | drop/replace | construction/time-vintage conflict |

---

## 5. Next action: overhead smoke, not full overhead matrix

Before running the full Core 8 overhead matrix, run a 3-run h13 smoke:

```text
TP0986 h13 overhead_as_canopy
TP0059 h13 overhead_as_canopy
TP0565 h13 overhead_as_canopy
```

Purpose:

```text
TP0986:
  null-control; overhead delta should be near zero.

TP0059:
  parking-lot hardscape; if focus cell has little mapped overhead, delta should be limited.

TP0565:
  asphalt road-edge hot anchor; check whether mapped-overhead context causes unexpected change.
```

Do not run:

```text
Core8 × 5h × overhead_as_canopy
```

until overhead smoke passes.

---

## 6. Required overhead smoke preprocessing

Generate overhead SVF for the smoke cells:

```text
TP0986
TP0059
TP0565
```

Scenario:

```text
overhead_as_canopy
```

Use existing preprocessing runner:

```text
scripts/qgis/v12_qgis_preprocess_from_manifest.py
```

with an overhead manifest.

---

## 7. Claim boundaries

Allowed:

```text
SOLWEIG-derived local radiative modifier
100m mixed-cell Tmrt_p90
delta_tmrt_p90_c local radiative penalty
m_rad_pct relative local radiative ranking
```

Disallowed:

```text
local WBGT prediction
validated 100m WBGT
risk map
real-time heat risk forecast
Tmrt converted to WBGT
SOLWEIG output equals observed truth
```

---

## 8. Do-not-commit list

Do not commit:

```text
*.tif
*.tiff
wall_height.tif
wall_aspect.tif
svf_base/
svf_overhead/
svfs.zip
Tmrt_average.tif
raw SOLWEIG output folders
```

Small summaries, manifests, docs, and QA CSV/MD may be committed after review.
