# OpenHeat System B N24 Companion Metric Plan

## Purpose
`tmrt_p90_c` remains the provisional primary System B target candidate because Sprint B1 showed strong hour stability and strong agreement with p75, but it is not canonical yet. N=24 validation is required before any canonical target claim.

## Required companions
- `tmrt_mean_c`: mixed-cell background radiant exposure.
- `tmrt_p75_c`: lower upper-tail shoulder check.
- `tmrt_p95_c`: more extreme upper-tail check.
- `tmrt_max_c`: upper-bound sensitivity only.
- `delta_tmrt_p90_c`: p90-derived scenario/reference-normalized physical delta.
- `m_rad_pct`: p90/delta-derived normalized rank modifier.
- `pct_pixels_tmrt_ge_40/45/50/55`: future threshold-area companions to add in the next aggregation pass where available.

## N24 validation questions
N=24 should test p90 vs p95, p90 vs max, p90 vs area-above-threshold, overhead sensitivity, hour stability, typology interpretability, and pedestrian relevance. The sample is designed to include exposed hardscape, shaded/canopy references, street canyon or wall-adjacent contexts, water/blue-green contexts, pedestrian waiting nodes, and overhead/viaduct sensitivity diagnostics.

## Boundary
This plan is System B only. It does not create local WBGT, observed heat truth, risk, official warnings, hazard maps, or System A/B coupling.
