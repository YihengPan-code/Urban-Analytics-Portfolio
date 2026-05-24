# OpenHeat v1.2-alpha Modifier Target Specification

**Document date:** 2026-05-24  
**Project:** OpenHeat-ToaPayoh  
**Stage:** v1.2-alpha  
**Status:** proposed target freeze / ready for review  
**Scope:** Define the SOLWEIG-derived local radiative modifier target before any scaled SOLWEIG, surrogate, or hazard-score work.

---

## 0. TL;DR

v1.2-alpha freezes the meaning of `modifier`.

Canonical target:

```text
tmrt_p90_c(cell, hour, scenario)
= 90th percentile of valid SOLWEIG Tmrt pixels inside a 100m cell

tmrt_ref_p90_c(hour, scenario, reference_domain)
= reference Tmrt p90 for the same hour and scenario

delta_tmrt_p90_c(cell, hour, scenario)
= tmrt_p90_c(cell, hour, scenario) - tmrt_ref_p90_c(hour, scenario)

m_rad_pct(cell, hour, scenario)
= percentile_rank(delta_tmrt_p90_c within same hour/scenario/reference_domain)
```

Primary modelling target for future surrogate:

```text
delta_tmrt_p90_c
```

Primary hazard-score modifier:

```text
m_rad_pct
```

This is:

```text
local radiative penalty / modifier
unit of delta_tmrt_p90_c = °C Tmrt difference
unit of m_rad_pct = 0..1 percentile modifier
```

It is not:

```text
ΔWBGT
local WBGT
observed truth
risk
health outcome
```

---

## 1. Layer identity

This task belongs to:

```text
Layer C — SOLWEIG / Tmrt layer
```

It feeds later:

```text
Layer D — surrogate / emulator
Layer E — WBGT-gated local radiative hazard score
```

It does not modify:

```text
Layer A — System A calibrated WBGT temporal baseline
v1.1-beta-formal results
v1.1-beta-formula audit results
```

---

## 2. Non-goals

Do not do these in v1.2-alpha:

```text
run full 50/100/150-cell SOLWEIG batch
train surrogate / ML model
compute final hazard maps
compute exposure/vulnerability-integrated spatial risk products
convert ΔTmrt to ΔWBGT
claim validated local WBGT
claim real-time operational warning system
```

v1.2-alpha only freezes the target definition, reference definition, output schema, pilot cell list format, and validation gates.

---

## 3. Target hierarchy

### 3.1 Pixel-level SOLWEIG input

For each cell/hour/scenario, SOLWEIG produces a raster:

```text
Tmrt_average.tif
```

or equivalent Tmrt raster output.

Valid pixels are pixels with finite Tmrt values inside the 100m cell mask.

### 3.2 Cell-level raw summaries

For each `cell_id × hour_sgt × scenario_id`, compute:

```text
tmrt_mean_c
tmrt_p50_c
tmrt_p75_c
tmrt_p90_c
tmrt_p95_c
tmrt_max_c
n_valid_pixels
```

Canonical cell-level target:

```text
tmrt_p90_c
```

Reason:

```text
p90 captures upper-tail pedestrian-relevant radiant exposure pockets.
mean can hide exposed micro-pockets inside partially shaded cells.
max is too sensitive to isolated pixels / raster edge artefacts.
```

### 3.3 Reference target

Reference is same-hour, same-scenario.

Primary production reference:

```text
tmrt_ref_p90_c(hour_sgt, scenario_id)
= median(tmrt_p90_c across reference_domain cells for that hour/scenario)
```

For v1.2-beta typology pilot, because the reference domain is only 8-12 cells, this should be labelled:

```text
pilot_batch_hour_median_reference
```

For scaled 50/100/150-cell runs, this becomes:

```text
stratified_sample_hour_median_reference
```

For future full-domain SOLWEIG/surrogate inference, this becomes:

```text
domain_hour_median_reference
```

Secondary diagnostic references:

```text
shaded_reference_cell
open_sun_reference_cell
typology_specific_reference
```

These may be reported, but are not the primary target unless v1.2-alpha is explicitly revised.

### 3.4 Delta target

Primary delta target:

```text
delta_tmrt_p90_c(cell, hour, scenario)
= tmrt_p90_c(cell, hour, scenario) - tmrt_ref_p90_c(hour, scenario)
```

Interpretation:

```text
positive = hotter / stronger local radiative penalty than reference
near zero = reference-like
negative = cooler / shaded / less radiatively exposed than reference
```

### 3.5 Normalized radiative modifier

Primary normalized modifier:

```text
m_rad_pct(cell, hour, scenario)
= percentile_rank(delta_tmrt_p90_c within same hour/scenario/reference_domain)
```

Range:

```text
0..1
```

Secondary normalized modifier:

```text
m_rad_robust01
= clip((delta_tmrt_p90_c - p05_delta) / (p95_delta - p05_delta), 0, 1)
```

Where `p05_delta` and `p95_delta` are computed within the same hour/scenario/reference domain.

Rationale:

```text
percentile rank is robust for prioritisation and top-k stability.
robust01 preserves approximate distance while clipping extremes.
```

### 3.6 Future hazard-score integration

Later v1.2-delta uses:

```text
LocalHeatHazard(cell, hour)
= S_WBGT(hour) × [1 + λ × M_rad(cell, hour)]
```

where:

```text
S_WBGT(hour) comes from System A calibrated WBGT_A(hour)
M_rad is m_rad_pct or m_rad_robust01
λ ∈ {0.25, 0.5, 1.0}
```

This is a hazard score, not risk and not local WBGT.

---

## 4. Required output table schema

Canonical long table:

```text
outputs/v12_modifier_targets/modifier_targets_long.csv
```

Required columns:

```text
cell_id
scenario_id
scenario_family
date_sgt
hour_sgt
forcing_id
solweig_run_id
tmrt_mean_c
tmrt_p50_c
tmrt_p75_c
tmrt_p90_c
tmrt_p95_c
tmrt_max_c
n_valid_pixels
cell_area_m2
valid_pixel_fraction
reference_method
reference_domain_id
tmrt_ref_p90_c
delta_tmrt_p90_c
m_rad_pct
m_rad_robust01
typology_label
scope_class
is_v10_anchor
qa_status
qa_notes
```

Reference table:

```text
outputs/v12_modifier_targets/modifier_reference_table.csv
```

Required columns:

```text
reference_domain_id
scenario_id
date_sgt
hour_sgt
reference_method
n_reference_cells
tmrt_ref_p90_c
delta_p05_c
delta_p50_c
delta_p95_c
notes
```

Normalization parameter table:

```text
outputs/v12_modifier_targets/modifier_normalization_params.csv
```

Required columns:

```text
reference_domain_id
scenario_id
date_sgt
hour_sgt
normalization_method
delta_min_c
delta_p05_c
delta_p50_c
delta_p95_c
delta_max_c
n_cells
notes
```

---

## 5. v1.2-beta typology pilot defaults

### 5.1 Cells

Start with 8-12 cells.

Must include v10 continuity anchors:

```text
TP_0565 — confident hot anchor
TP_0986 — clean confident hot anchor / null-control
TP_0088 — overhead-confounded transport-deck case
TP_0916 — overhead-saturated case
TP_0433 — shaded reference
```

Additional candidate typologies:

```text
open paved high-SVF
HDB canyon
wall-adjacent
covered walkway / overhead
near water
grass / park open
exposed bus-stop / waiting node
dense shaded low-SVF
```

### 5.2 Hours

Pilot hours:

```text
10, 12, 13, 15, 16 SGT
```

Reason:

```text
continuity with v10-epsilon;
captures morning, solar noon / peak radiation, afternoon, late afternoon;
small enough for manual SOLWEIG QA.
```

### 5.3 Scenarios

Initial pilot scenarios:

```text
base
overhead_as_canopy
```

Use `overhead_as_canopy` only where relevant; for clean null-control cells it should produce near-zero difference.

### 5.4 Weather forcing

Pilot forcing should reuse the v10-epsilon hot-day forcing where possible for continuity.

Future scenarios may include:

```text
formal_archive_hot_day_2026_05_19
formal_archive_hot_day_2026_05_20
cloudy_hot_day
clear_hot_day
```

Each scenario must have its own reference and normalization.

---

## 6. Sanity checks before surrogate training

A typology pilot must pass these checks before v1.2-gamma surrogate work:

```text
1. Open sunlit / high-SVF cells should rank hotter than shaded reference cells.
2. TP_0433-like shaded reference should remain low and stable.
3. TP_0986 clean null-control should show near-zero base vs overhead delta.
4. TP_0088 / TP_0916 overhead scenarios should reduce Tmrt_p90 or mean meaningfully.
5. p90 should reveal exposure pockets that mean hides in mixed cells.
6. max should not drive conclusions unless p90 / p95 corroborate it.
7. Hourly rank stability should be plausible; major flips require geometry/forcing audit.
8. Surface/material effects should not dominate shade/SVF/direct-sun without explanation.
9. No surrogate training if SOLWEIG typology results are physically implausible.
```

---

## 7. Validation hierarchy for later surrogate

Not part of v1.2-alpha implementation, but target spec must preserve this design:

```text
Level 0: internal accuracy vs SOLWEIG-derived delta_tmrt_p90_c
Level 1: spatial / typology holdout
Level 2: temporal / solar-angle holdout
Level 3: scenario holdout
Level 4: real-world local measurement validation
```

Without Level 4, claims remain simulation-informed.

---

## 8. Claim boundaries

Allowed wording:

```text
SOLWEIG-derived local radiative modifier
ΔTmrt_p90 local radiative penalty
normalized M_rad modifier
WBGT-gated local radiative hazard score
simulation-informed local heat hazard ranking
```

Disallowed wording:

```text
local WBGT prediction
validated 100m WBGT
risk-layer spatial product
real-time heat risk forecast
ML calibration of observed heat exposure
ΔTmrt converted to ΔWBGT
```

Operationally, this means v1.2-alpha does not define any formula that turns the
SOLWEIG-derived Tmrt modifier into a local WBGT estimate.

Any future physical bridge from Tmrt to WBGT would need a separate task, separate validation, and explicit exploratory labelling. The mainline route remains:

```text
System A WBGT_A(hour) gates temporal heat severity.
SOLWEIG-derived delta_tmrt_p90_c / M_rad ranks local radiative penalty.
The combined output is a WBGT-gated local radiative hazard score, not a local WBGT map.
```

---

## 9. Files to create in v1.2-alpha

```text
docs/v12/OpenHeat_modifier_target_spec_CN.md
docs/v12/modifier_reference_definition_CN.md
docs/v12/modifier_target_validation_checklist_CN.md
configs/v12/v12_modifier_target_config.example.json
data/grid/v12/solweig_typology_cell_candidates.csv
docs/codex/CODEX_TASK_v12_alpha_modifier_target_spec.md
```

---

## 10. Hard gates before later work

Do not start v1.2-gamma surrogate training until:

```text
1. v1.2-alpha target and reference definitions are reviewed.
2. The 8-12 cell SOLWEIG typology pilot has run.
3. The typology pilot passes the physical sanity checks in the validation checklist.
4. Failed or ambiguous typologies have been audited for geometry, DSM/vegetation, timezone, forcing, and cell-mask issues.
```

Do not produce hazard maps until both System A and the radiative modifier layer are ready for v1.2-delta.

Do not use risk-layer spatial-product wording until exposure and vulnerability layers are explicitly integrated in v1.3 or later.

---

## 11. Decision summary

v1.2-alpha freezes:

```text
raw SOLWEIG summary = tmrt_p90_c
delta target = delta_tmrt_p90_c
hazard modifier = m_rad_pct, with m_rad_robust01 as secondary
primary reference = same-hour same-scenario median tmrt_p90_c over the reference domain
pilot cell count = 8-12
pilot hours = 10 / 12 / 13 / 15 / 16 SGT
pilot scenarios = base + overhead_as_canopy
```

The next step after this spec is:

```text
v1.2-beta SOLWEIG typology pilot
```

not:

```text
scaled 150-cell SOLWEIG
surrogate training
hazard map
risk-layer spatial product
```
