# Modifier reference definition — OpenHeat v1.2-alpha

**Document date:** 2026-05-24  
**Status:** companion reference definition for `OpenHeat_modifier_target_spec_CN.md`

---

## 1. Why a reference is needed

Absolute `Tmrt_p90_c` is scenario- and hour-dependent. A 13:00 clear-hot scenario and a 16:00 cloudy-hot scenario cannot be compared directly without a same-hour/same-scenario reference.

Therefore the local modifier is defined as:

```text
delta_tmrt_p90_c = tmrt_p90_c - tmrt_ref_p90_c
```

and normalized as:

```text
m_rad_pct = percentile_rank(delta_tmrt_p90_c)
```

---

## 2. Primary reference

Primary reference:

```text
same-hour same-scenario median of tmrt_p90_c across the reference domain
```

Formal notation:

```text
tmrt_ref_p90_c(h, s, D)
= median({tmrt_p90_c(cell, h, s) for cell in reference_domain D})
```

Where:

```text
h = hour_sgt
s = scenario_id
D = reference_domain_id
```

This reference is deliberately defined on the same SOLWEIG cell summary used by the target:

```text
reference statistic = median over cell-level tmrt_p90_c values
not pixel-level median Tmrt
not WBGT
not a fixed all-hours climatology
```

---

## 3. Reference domains by phase

### v1.2-beta typology pilot

Reference domain:

```text
pilot_typology_batch
```

Label:

```text
pilot_batch_hour_median_reference
```

Caveat:

```text
This reference is useful for sanity checking, not final AOI-wide ranking.
```

### v1.2-beta-scale

Reference domain:

```text
stratified_50_cell_sample
stratified_100_cell_sample
stratified_150_cell_sample
```

Label:

```text
stratified_sample_hour_median_reference
```

### v1.2-delta or later full-domain inference

Reference domain:

```text
toa_payoh_all_cells_or_modelled_domain
```

Label:

```text
domain_hour_median_reference
```

---

## 4. Secondary diagnostic references

### 4.1 Shaded reference cell

Example:

```text
TP_0433
```

Use:

```text
delta_vs_shaded_reference_c
```

Purpose:

```text
interpretability / public communication / sanity check
```

Do not use as primary reference because one cell may encode idiosyncratic vegetation, geometry, or raster behaviour.

### 4.2 Open-sun reference cell

Use:

```text
delta_vs_open_reference_c
```

Purpose:

```text
intervention framing: how much cooler/hotter than an exposed open baseline
```

Not primary because open reference can be extreme and unstable across solar angle.

### 4.3 Typology-specific reference

Use:

```text
delta_vs_typology_median_c
```

Purpose:

```text
within-typology comparison
```

Not primary because it removes between-typology differences that are important for hazard ranking.

---

## 5. Normalization details

Primary:

```text
m_rad_pct = rank_percentile(delta_tmrt_p90_c)
```

Within:

```text
reference_domain_id × scenario_id × date_sgt × hour_sgt
```

Tie handling:

```text
average rank
```

Range:

```text
0..1
```

Secondary:

```text
m_rad_robust01 = clip((delta - p05_delta) / (p95_delta - p05_delta), 0, 1)
```

Edge case:

```text
if p95_delta == p05_delta, set m_rad_robust01 = 0.5 and flag qa_status = degenerate_normalization
```

---

## 6. Reporting rule

Always report together:

```text
tmrt_p90_c
tmrt_ref_p90_c
delta_tmrt_p90_c
m_rad_pct
reference_method
reference_domain_id
```

Never report `M_rad` without stating reference and normalization.

Never describe `tmrt_ref_p90_c` or `delta_tmrt_p90_c` as a measured local WBGT baseline. They are SOLWEIG-derived Tmrt reference quantities for the radiative modifier layer only.
