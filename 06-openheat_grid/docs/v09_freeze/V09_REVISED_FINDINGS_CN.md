# OpenHeat-ToaPayoh v0.9 Revised Findings

> This document replaces the original v0.9-gamma findings after the building DSM completeness audit.

---

## 1. Why findings were revised

The original v0.9-gamma results were based on a building DSM created from HDB3D and URA building footprints. A late-stage comparison against OSM-mapped building footprints found that this DSM is incomplete in the selected SOLWEIG tiles.

Across the six SOLWEIG tile buffers, the DSM captured only 25.8% of OSM-mapped building area. The incompleteness was not evenly distributed. Several high-hazard tiles had very low completeness, including T01 at 7.8% and T06 at 0.0%. This means that the previous heat-hazard ranking may have promoted some cells because their building data were missing, not because they were truly open or high-exposure.

Therefore, the v0.9 findings must be revised.

---

## 2. Revised finding 1: SOLWEIG reveals strong radiant heterogeneity, but magnitude is DSM-dependent

### Original finding

SOLWEIG quantified a 26.2°C Tmrt difference between T01 clean hazard and T05 clean shaded reference at 13:00.

### Revised finding

SOLWEIG produced a 26.2°C focus-cell Tmrt contrast between T01 and T05 under the current HDB3D+URA DSM. This is a strong directional result showing that local shade, tree canopy and radiative geometry can create very large pedestrian radiant-exposure differences.

However, the exact magnitude is uncertain because both T01 and T05 are affected by building DSM incompleteness. T01 in particular has very low building completeness, which likely inflates SVF and reduces modelled building shade. Therefore, the 26.2°C difference should be interpreted as a current-DSM estimate, not a final measured physical truth.

### Final interpretation

> SOLWEIG confirms strong radiant-exposure heterogeneity between exposed and shaded urban cells, but the reported magnitude requires augmented-DSM sensitivity testing.

---

## 3. Revised finding 2: Afternoon radiant-load persistence remains a useful physical signal

### Original finding

T01 showed a SOLWEIG-minus-empirical-proxy delta of +30.70°C at 13:00 and +29.79°C at 15:00. The small decline despite lower shortwave radiation was interpreted as evidence of late-afternoon thermal mass / longwave hold.

### Revised finding

This interpretation remains plausible, but the absolute delta values are affected by the incomplete DSM and by differences between SOLWEIG Tmrt and the empirical globe-temperature proxy.

The more robust signal is the temporal shape within the same tile: the SOLWEIG-minus-proxy difference remained high into the afternoon even after shortwave radiation declined. This supports the hypothesis that empirical WBGT proxy formulations underrepresent delayed radiant exposure from heated urban surfaces.

However, because missing buildings have time-dependent effects on shadow and longwave radiation, even within-tile temporal comparisons are not fully immune to DSM completeness bias.

### Final interpretation

> SOLWEIG provides evidence consistent with afternoon radiant-load persistence, but the absolute magnitude and precise physical attribution require augmented DSM and multi-day sensitivity testing.

---

## 4. Withdrawn finding: T01–T06 overhead infrastructure bias

### Original finding

T01 and T06 differed by only 2.6°C at 13:00, suggesting that SOLWEIG failed to distinguish clean hazard cells from overhead-confounded cells.

### Revision

This finding is withdrawn from main results.

T06 was later found to have 0% building DSM completeness. The source DSM contains no valid building pixels around TP_0575, despite OSM mapping 215 buildings in the buffer. Therefore, the T01–T06 comparison cannot isolate overhead-infrastructure effects.

### Final interpretation

> Overhead infrastructure remains an important unmodelled heat-exposure component, but T01–T06 cannot be used to quantify it because T06 is confounded by complete building DSM absence.

---

## 5. New finding: Building DSM incompleteness systematically biases hazard ranking

The most important revised finding is that HDB3D+URA building DSM incompleteness appears to bias OpenHeat hazard ranking.

The original hazard ranking used morphology features derived from the current DSM. In DSM-gap regions, missing buildings are interpreted as low building density, high sky exposure and low shade. These conditions increase heat-hazard score. Therefore, missing building data can generate false high-hazard signals.

The audit found that several high-ranked hazard tiles had very low building completeness:

```text
T01 hazard_rank=2,    completeness=7.8%
T06 hazard_rank=20,   completeness=0.0%
T04 hazard_rank=34,   completeness=39.7%
T02 hazard_rank=51,   completeness=12.6%
T03 hazard_rank=59,   completeness=66.4%
T05 hazard_rank=974,  completeness=16.9%
```

This pattern suggests that the old hazard ranking may partly reflect source-data gaps.

### Final interpretation

> The v0.7–v0.9 hazard-ranking framework cannot be treated as final until the building DSM is augmented and morphology features are recomputed.

---

## 6. Revised v0.9 findings list

### Retained

1. The NEA WBGT archive and paired calibration pipeline work.
2. Raw weather-only WBGT proxy underpredicts official WBGT.
3. M3/M4 calibration models improve MAE and moderate-event detection.
4. SOLWEIG selected-tile workflow is technically valid.
5. SOLWEIG shows strong spatial radiant-exposure differences under the available DSM.
6. Afternoon radiant-load persistence is a plausible explanation for part of the WBGT residual structure.

### Downgraded

1. The 26.2°C T01–T05 contrast is a current-DSM directional estimate, not a final magnitude.
2. SOLWEIG-minus-proxy deltas are diagnostic, not direct Tmrt validation against observation.
3. v0.8/v0.9 hazard maps are current-DSM maps, not final corrected heat-risk maps.

### Withdrawn

1. T01–T06 2.6°C overhead infrastructure bias quantification.
2. Any claim that T06 represents a clean overhead-confounded heat case.

### Newly elevated

1. Building DSM completeness is a dominant upstream uncertainty.
2. Hazard ranking is likely biased toward DSM-coverage-gap cells.
3. v1.0 must rebuild the building DSM before final ranking or ML interpretation.

---

## 7. Revised dissertation / portfolio contribution

The main contribution should shift from:

> OpenHeat precisely quantified tropical vegetation cooling and overhead infrastructure bias.

to:

> OpenHeat developed a transparent open-data heat-risk modelling pipeline and used calibration, SOLWEIG and data-integrity auditing to reveal how upstream morphology incompleteness can systematically bias urban heat-hazard ranking.

This is a stronger and more honest contribution.

---

## 8. Implications for v1.0

v1.0 should focus on augmented morphology rather than ML or dashboarding.

Required v1.0 tasks:

1. integrate HDB3D, URA, OSM, Microsoft and Google building footprints where appropriate;
2. deduplicate footprints with provenance;
3. impute heights with confidence fields;
4. rasterize augmented DSM;
5. recompute building-density, SVF, shade and height features;
6. rerun hazard ranking;
7. quantify rank shifts;
8. rerun selected SOLWEIG experiments;
9. identify DSM-gap false positives from v0.9.

---

## 9. Suggested one-paragraph summary

OpenHeat v0.9 successfully established a calibration and SOLWEIG workflow, but a late-stage building DSM audit changed the interpretation of the results. The HDB3D+URA DSM captured only 25.8% of OSM-mapped building area across the six SOLWEIG tile buffers, and several high-ranked hazard tiles had very low completeness. This suggests that the previous hazard ranking partly reflected source-data gaps rather than true urban openness. Therefore, v0.9 is frozen as a current-DSM diagnostic prototype. Its calibration and SOLWEIG workflows remain valuable, but final heat-hazard ranking requires a v1.0 augmented multi-source building DSM.
