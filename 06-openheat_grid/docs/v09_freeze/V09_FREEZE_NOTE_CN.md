# OpenHeat-ToaPayoh v0.9 Freeze Note

> Status: Frozen as `v0.9-audit-freeze`  
> Next branch: `v10-augmented-dsm`  
> Purpose: Freeze the v0.9 calibration, SOLWEIG and audit outputs before beginning v1.0 augmented building DSM development.

---

## 1. Why v0.9 is being frozen

OpenHeat-ToaPayoh v0.9 completed a full methodological cycle:

1. NEA official WBGT archive QA and paired calibration dataset;
2. non-ML WBGT proxy calibration using LOSO-CV;
3. threshold scanning for official WBGT >=31°C detection;
4. UMEP/SOLWEIG selected-tile Tmrt experiment;
5. overhead-aware tile selection;
6. building DSM completeness audit.

However, the late-stage building DSM audit revealed that the HDB3D + URA building DSM used from v0.7 to v0.9 is not sufficiently complete to support final heat-hazard ranking claims. Across the six SOLWEIG tile buffers, the current DSM captured only **25.8% of OSM-mapped building area**, with several high-hazard tiles showing particularly low completeness. The audit also found that T06 had **0% DSM building completeness** despite OSM mapping 215 buildings and 67,456 m² of building area in the buffer. This indicates a source-data gap rather than a clipping or SOLWEIG processing bug.

Therefore, v0.9 is frozen as a **current-HDB3D+URA DSM experiment and audit checkpoint**, not as the final morphology-corrected OpenHeat version.

---

## 2. Frozen interpretation of v0.9

v0.9 should now be interpreted as:

> A calibration and SOLWEIG-led diagnostic prototype that revealed both the potential and the limitations of the current open-data morphology pipeline.

It should **not** be interpreted as:

> A final validated street-level heat-stress model for Toa Payoh.

The key reason is that building morphology incompleteness can create artificial “open” cells. These cells may receive high SVF, low building density, low shade and therefore high hazard ranking, even when the real urban form is not actually open.

---

## 3. Findings retained

The following v0.9 findings are retained.

### 3.1 Calibration pipeline validity

The v0.9-alpha and v0.9-beta calibration workflow is valid as a station-level WBGT proxy calibration pipeline. It successfully created paired official WBGT observations and historical weather forcing, then evaluated raw and calibrated WBGT proxy models.

The raw weather-only WBGT proxy was shown to underpredict official WBGT, motivating calibration. Ridge-based weather-regime and thermal-inertia calibration improved overall, daytime and peak-window MAE relative to the raw proxy.

### 3.2 Threshold scan value

The v0.9-beta threshold scan remains valid as a post-hoc decision-threshold analysis. It showed that calibrated model scores require lower decision thresholds than the official WBGT threshold when detecting official WBGT >=31°C events.

This does **not** redefine the official WBGT threshold. It only identifies model-score thresholds for event detection under the current 24-hour pilot archive.

### 3.3 SOLWEIG workflow validity

The v0.9-gamma SOLWEIG workflow is valid as a selected-tile physical modelling experiment. It successfully demonstrated the technical workflow:

- overhead-aware tile selection;
- single-hour UMEP/SOLWEIG execution;
- Tmrt aggregation to 100 m grid cells;
- focus-cell and tile-level comparison;
- proxy-vs-SOLWEIG Tmrt diagnostics.

### 3.4 Directional radiant heterogeneity

SOLWEIG showed large directional differences in Tmrt between selected exposed and shaded tiles under the available DSM. This supports the qualitative conclusion that local morphology and canopy strongly structure pedestrian radiant exposure.

---

## 4. Findings downgraded

The following findings are retained only as **current-DSM estimates**, not final physical magnitudes.

### 4.1 T01–T05 vegetation / shade contrast

Original statement:

> T01 clean hazard and T05 clean shaded reference differed by 26.2°C Tmrt at 13:00.

Revised statement:

> Under the current HDB3D+URA DSM, SOLWEIG produced a 26.2°C focus-cell Tmrt contrast between T01 and T05 at 13:00. Because the building DSM completeness audit found severe underrepresentation of mapped buildings in several tiles, this number should be interpreted as a current-DSM directional contrast rather than a final physical magnitude.

The direction is likely robust: exposed, low-shade cells are hotter than shaded reference cells.

The magnitude is uncertain and requires augmented DSM sensitivity testing.

### 4.2 Afternoon thermal-hold signal

Original statement:

> SOLWEIG supports a late-afternoon thermal mass / longwave hold mechanism because the SOLWEIG-minus-proxy delta remained high from 13:00 to 15:00.

Revised statement:

> The within-tile 13:00–15:00 pattern remains a useful diagnostic signal, but the absolute SOLWEIG-minus-proxy magnitude is affected by DSM completeness and forcing assumptions. The result should be interpreted as evidence consistent with afternoon radiant-load persistence, not as a fully validated quantification of wall longwave heat storage.

---

## 5. Findings withdrawn from main results

### 5.1 T01–T06 overhead infrastructure bias quantification

Original statement:

> T01–T06 differed by only 2.6°C at 13:00, showing that SOLWEIG cannot distinguish clean hazard cells from overhead-confounded cells.

This finding is withdrawn from main results.

Reason:

T06 is not only overhead-confounded. The building completeness audit showed that T06 has **0% building DSM completeness** in the source DSM. Therefore, T01–T06 cannot isolate overhead-infrastructure effects. The comparison confounds:

1. overhead infrastructure absence;
2. building DSM source-data gap;
3. missing building shade;
4. missing wall longwave;
5. artificial low building density.

Overhead infrastructure remains an important limitation and future-work item, but T01–T06 cannot quantify its effect.

---

## 6. New primary v0.9 audit finding

The most important v0.9 finding is now:

> The HDB3D+URA building DSM incompleteness systematically biases OpenHeat hazard ranking toward source-data-coverage-gap regions.

This finding is more important than the original SOLWEIG magnitude findings.

The audit found that the selected high-hazard tiles often had low DSM completeness. In the six SOLWEIG tile buffers, aggregate DSM completeness relative to OSM-mapped building area was 25.8%. T01, T02, T05 and T06 all had completeness below 17%, while T06 had 0% completeness despite OSM mapping 215 buildings in the same buffer. This suggests that part of the old hazard ranking may reflect missing building data rather than true urban openness.

This transforms the v0.9 conclusion from:

> SOLWEIG quantified exact heat exposure differences.

to:

> SOLWEIG and DSM auditing revealed that upstream morphology data integrity is a dominant uncertainty in open-data heat-risk modelling.

---

## 7. Consequences for previous versions

### v0.7

v0.7 hazard ranking should now be treated as a **current-DSM baseline**, not as final ground truth. Its building-density, SVF and shade-related features are affected by building DSM incompleteness.

### v0.8

v0.8 UMEP+vegetation morphology remains methodologically valuable, but its absolute SVF/shade/Tmrt interpretation is limited by the incomplete building DSM.

### v0.9

v0.9 remains valid as:

- a calibration pipeline;
- a SOLWEIG workflow demonstration;
- a methodology audit;
- a data-integrity finding.

It is not final as:

- a definitive heat-hazard ranking;
- a complete 3D urban morphology simulation;
- a validated operational warning model.

---

## 8. Frozen output status

The following outputs are frozen as v0.9 audit evidence:

```text
outputs/v09_beta_calibration/
outputs/v09_beta_threshold_scan/
outputs/v09_gamma_analysis/
outputs/v09_gamma_qa/
outputs/v09_solweig/
docs/32_V09_COMPLETE_WORK_RECORD_CN.md
docs/33_V09_BUILDING_DSM_GAP_AUDIT_CN.md
```

These should not be overwritten in v1.0.

---

## 9. Why v1.0 is required

v1.0 is required because the next valid modelling step is not ML, dashboarding or additional calibration. The next valid step is rebuilding the morphology foundation.

v1.0 must:

1. construct a multi-source augmented building footprint layer;
2. assign heights with provenance and confidence;
3. rasterize an augmented 2 m building DSM;
4. re-run morphology features;
5. re-run hazard ranking;
6. quantify rank shifts;
7. identify old DSM-gap false positives;
8. rerun selected SOLWEIG experiments with corrected morphology.

---

## 10. v0.9 final status

v0.9 is frozen as:

> A successful calibration and SOLWEIG methodology prototype that discovered a critical upstream building-DSM completeness bias.

v1.0 begins as:

> An augmented multi-source building DSM and hazard-ranking correction project.
