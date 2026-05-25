# OpenHeat v1.2-beta SOLWEIG typology pilot closeout

**Document date:** 2026-05-25
**Stage:** v1.2-beta.2 closeout
**Status:** closeout note for the Core-8 v10-epsilon-forcing pilot

## 0. Closeout decision

The v1.2-beta Core-8 SOLWEIG typology pilot is accepted as a technical and physical sanity pass for the local radiative modifier target:

```text
tmrt_p90_c -> delta_tmrt_p90_c -> m_rad_pct
```

This closeout does not claim local WBGT, observed truth, hazard map, or risk map.

## 1. What passed

Completed technical stages:

```text
Wave 0: TP0986 h13 base smoke - PASS
Wave 1: TP0986 / TP0542 / TP0059 x h10/h13/h16 base - PASS
Core 8 base: 8 cells x 5 hours x base = 40 runs - PASS
Overhead smoke: TP0986 / TP0059 / TP0565 h13 overhead_as_canopy = 3 runs - PASS
Core 8 overhead: 8 cells x 5 hours x overhead_as_canopy = 40 runs - PASS
TP0542 h15 distribution diagnostic - PASS / interpretable
```

Core technical criteria:

```text
Core 8 base raster exists: 40 / 40
Core 8 base focus cell exists: 40 / 40
Core 8 base qa_status: all ok
Core 8 overhead raster exists: 40 / 40
Core 8 overhead focus cell exists: 40 / 40
Core 8 overhead qa_status: all ok
```

## 2. What was learned

### 2.1 `tmrt_p90_c` is accepted as the current primary target

The Core-8 pilot supports `tmrt_p90_c` as the most useful mixed-cell upper-tail summary:

```text
tmrt_mean_c = general cell condition; useful but can be diluted by cool pixels
tmrt_p90_c  = primary upper-tail mixed-cell target
tmrt_max_c  = diagnostic only; too extreme-pixel-sensitive for primary target
```

### 2.2 Core-8 typology roles are coherent

Current Core-8 interpretation:

| cell_id | role |
|---|---|
| TP_0986 | high-exposure low-rise residential null-control |
| TP_0565 | school-gate / asphalt road-edge hot anchor |
| TP_0059 | open paved hardscape / parking-lot diagnostic |
| TP_0627 | street-canyon / wall-adjacent low-SVF corridor |
| TP_0366 | school-gate / bus-stop mixed waiting node |
| TP_0326 | stable high-rise residential estate |
| TP_0542 | river-edge shaded walkway / mapped pedestrian-overhead shade case |
| TP_0835 | wooded green-space low-radiative diagnostic |

### 2.3 TP0542 h15 is evidence, not anomaly

TP0542 h15 shows:

```text
base p90 = 50.729 C
overhead p90 = 39.148 C
p95 / p99 / max nearly unchanged
```

Interpretation:

```text
mapped overhead / shade geometry shifts enough top-decile pixels into lower/intermediate Tmrt bands;
extreme hot pixels remain, so p95/p99/max do not move much.
```

This supports the mixed-cell p90 framing.

## 3. Claim boundary

Allowed wording:

```text
SOLWEIG-derived Tmrt modifier evidence
100m mixed-cell upper-tail radiative modifier evidence
delta_tmrt_p90_c / m_rad_pct local radiative modifier
```

Disallowed wording:

```text
local WBGT
validated 100m WBGT
observed truth
risk
risk map
hazard map
real-time public health warning
Tmrt converted to WBGT
```

## 4. Remaining limitations

```text
Current forcing = v10-epsilon forcing, not formal-hot-day forcing.
m_rad_pct is batch-relative, not full-domain Toa Payoh modifier.
100m cell is mixed-cell, not point-level pedestrian truth.
overhead_as_canopy is a sensitivity approximation.
unmapped micro-shelter remains outside canonical overhead_as_canopy.
```

## 5. Closeout action

Recommended next gate:

```text
formal-hot-day forcing QA before scale design
```

Do not proceed directly to:

```text
50/100/150-cell scale sample
surrogate / ML
hazard map
risk map
```
