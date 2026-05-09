# OpenHeat-ToaPayoh v0.9-gamma Final Report  
## SOLWEIG Selected-Tile Validation of Radiant Heat Exposure

**Project:** OpenHeat-ToaPayoh  
**Version:** v0.9-gamma final  
**Study area:** Toa Payoh-centred neighbourhood-edge AOI, Singapore  
**Grid:** 100 m grid, EPSG:3414 / SVY21  
**Forcing station:** S128 Bishan Street / Bishan Stadium  
**SOLWEIG simulation date:** 2026-05-07  
**SOLWEIG hours:** 10:00, 12:00, 13:00, 15:00, 16:00 SGT  
**Prepared for:** OpenHeat v0.9 physical-validation and dissertation/portfolio reporting

---

## 1. Executive summary

OpenHeat v0.9-gamma extends the v0.8 UMEP building+canopy morphology layer by running selected-tile SOLWEIG simulations to explicitly estimate **mean radiant temperature (Tmrt)**. The purpose is not to replace the full neighbourhood forecast model, but to test whether the v0.8 hotspot logic is physically consistent under a more detailed radiation model.

The v0.9-gamma experiment supports three main findings:

1. **SOLWEIG confirms large radiant-exposure heterogeneity.**  
   Under the same S128 meteorological forcing, the clean hazard tile and clean shaded reference differed by **26.2°C in focus-cell Tmrt at 13:00**. This confirms that vegetation, canopy geometry, sky exposure and shade can create very large local radiant-load differences even when air temperature forcing is identical.

2. **SOLWEIG supports the afternoon radiant-load underrepresentation hypothesis.**  
   In v0.9-beta, the empirical WBGT proxy showed a residual pattern suggesting that afternoon high-WBGT conditions were underrepresented. SOLWEIG showed that, in the clean hazard tile, Tmrt remained very high at 15:00 even after shortwave radiation declined. The SOLWEIG-minus-empirical-globe-term delta was **+30.70°C at 13:00** and still **+29.79°C at 15:00**, a decline of only **0.91°C** despite a substantial decline in incoming shortwave radiation.

3. **Overhead infrastructure is a quantified blind spot.**  
   The overhead-confounded hazard tile remained only **2.6°C cooler** than the clean hazard tile at 13:00. Because the current building+canopy DSM does not explicitly represent elevated roads, rail viaducts, covered walkways and pedestrian bridges, SOLWEIG cannot fully distinguish overhead-confounded cells from clean exposed cells. This provides a strong justification for a future transport/covered-walkway DSM layer.

Overall, v0.9-gamma shows that v0.8 heat-hazard hotspots are physically meaningful radiant-exposure locations, but also reveals that overhead pedestrian and transport infrastructure remains an important missing morphology layer.

---

## 2. Motivation

Earlier OpenHeat versions used empirical or proxy morphology layers to estimate heat stress. v0.8 replaced proxy SVF and shade with UMEP-derived building+canopy SVF and shadow fractions. This strongly changed hotspot ranking, showing that local morphology and canopy treatment are high-sensitivity components of the model.

v0.9-alpha and v0.9-beta then showed that the raw WBGT proxy systematically underpredicted official WBGT, especially during high-WBGT afternoon periods. In particular, v0.9-beta identified a residual pattern consistent with delayed radiant heating or thermal storage: the strongest residual did not simply coincide with instantaneous shortwave radiation, suggesting that the empirical proxy did not fully capture the radiative environment.

v0.9-gamma therefore asks:

> Do selected OpenHeat hotspots also show high SOLWEIG Tmrt under detailed radiation modelling, and can SOLWEIG help explain the afternoon radiant-load residual detected in v0.9-beta?

---

## 3. Methods

### 3.1 Selected-tile strategy

The final v0.9-gamma experiment used an **overhead-aware selected-tile design** rather than the original rank-only tile design. The first tile set was rejected because all five original tiles intersected overhead structures such as elevated roads, elevated rail, pedestrian bridges and covered walkways.

The final tile set contains six tiles:

| Tile | Type | Purpose | Interpretation |
|---|---|---|---|
| T01 | clean_hazard_top | Clean physical heat-hazard hotspot | Main high-radiant-load tile |
| T02 | conservative_risk_top | Conservative intervention-priority hotspot | High hazard + vulnerability/exposure |
| T03 | social_risk_top | Social-sensitive priority hotspot | Stronger vulnerability/exposure emphasis |
| T04 | open_paved_hotspot | Open paved / road-dominated heat hotspot | Exposed hard-surface morphology |
| T05 | clean_shaded_reference | Low-hazard shaded reference | Main cooling/reference tile |
| T06 | overhead_confounded_hazard_case | Diagnostic overhead-confounded tile | Not a clean tile; used for infrastructure blind-spot analysis |

The final selection imposed three design constraints:

- low overhead-confounding for clean tiles;
- spatial separation between selected tiles;
- reference-tile purity: low hazard, high shade/green signal, and low overhead contamination.

The overhead-aware selection produced six strict tiles with no major warnings. The clean hazard tile (T01) and clean reference tile (T05) both had zero overhead fraction at the focus cell, while the diagnostic T06 deliberately retained high overhead overlap.

### 3.2 Input morphology

The SOLWEIG workflow used the v0.8 building+canopy morphology stack:

- 2 m building DSM derived from HDB3D and URA footprints;
- 2 m vegetation DSM derived from ETH Global Canopy Height 2020, resampled to the building DSM grid;
- vegetation transmissivity set to 3%;
- trunk zone height set to 25% of canopy height;
- flat terrain DEM, consistent with the HDB3D terrain assumption and the relatively flat Toa Payoh/Bishan context.

### 3.3 Meteorological forcing

The meteorological forcing was derived from S128 Bishan Street / Bishan Stadium on 2026-05-07, covering five representative hours:

| Hour | Tair (°C) | Shortwave radiation (W/m²) | Wind speed (m/s) | Empirical globe-term proxy (°C) |
|---:|---:|---:|---:|---:|
| 10:00 | 28.4 | 346 | 1.42 | 29.60 |
| 12:00 | 30.1 | 750 | 1.91 | 32.40 |
| 13:00 | 29.5 | 753 | 2.25 | 31.64 |
| 15:00 | 29.0 | 576 | 1.97 | 30.74 |
| 16:00 | 28.9 | 352 | 1.39 | 30.14 |

This day was selected because it corresponds to the 24-hour calibration archive used in v0.9-alpha/beta and includes high WBGT conditions near the Toa Payoh/Bishan context.

### 3.4 SOLWEIG implementation

SOLWEIG was run in QGIS/UMEP v2025a. Because SOLWEIG v2025a returned time-averaged Tmrt when provided with multiple-hour meteorological files, the workflow was adapted to run separate single-hour simulations. Each single-hour meteorological file was duplicated into two identical rows to avoid a known single-row array bug in the SOLWEIG processing script.

For each tile and hour, SOLWEIG produced a Tmrt raster. These rasters were consolidated and then aggregated back to the 100 m grid. The analysis used **focus-cell statistics** for the main interpretation because buffered tile means dilute the microclimatic signal by including surrounding context and buffer pixels.

---

## 4. Quality assurance

### 4.1 Time parsing and row counts

The final SOLWEIG analysis successfully parsed the intended hourly labels:

```text
1000, 1200, 1300, 1500, 1600
```

No rows were labelled as `2026` or `unknown` after the time-parsing and duplicate-filtering hotfix. The final merged SOLWEIG analysis table contained **1,225 rows**, corresponding to the selected tiles, grid cells and five SOLWEIG hours.

### 4.2 Focus-cell versus tile-mean interpretation

Tile-level means are useful for contextual QA but should not be used as the main scientific result, because each 700 m buffered tile contains a mixture of focus-cell morphology and surrounding context. Focus-cell Tmrt provides the clearest test of whether the selected hotspot or reference cell behaves as expected.

Therefore, this report uses focus-cell values as the primary evidence and tile means only as supporting diagnostics.

### 4.3 Overhead-infrastructure QA

The project identified overhead infrastructure as a non-negligible confounder. The final selected-tile design separates clean tiles from an overhead-confounded diagnostic case:

- T01–T05 are the primary comparison tiles;
- T06 is retained as a diagnostic case only;
- T06 should not be interpreted as a clean heat-hazard tile.

---

## 5. Results

### 5.1 Focus-cell Tmrt by tile type and hour

| Hour | Clean hazard T01 | Conservative risk T02 | Social risk T03 | Open paved T04 | Shaded reference T05 | Overhead diagnostic T06 |
|---:|---:|---:|---:|---:|---:|---:|
| 10:00 | 46.3 | 44.9 | 42.7 | 41.9 | 32.9 | 44.4 |
| 12:00 | 62.1 | 60.2 | 59.4 | 57.8 | 36.0 | 59.6 |
| 13:00 | 62.3 | 60.3 | 58.8 | 57.6 | 36.1 | 59.7 |
| 15:00 | 60.5 | 58.5 | 55.4 | 55.0 | 35.9 | 57.8 |
| 16:00 | 51.5 | 49.9 | 46.7 | 46.2 | 34.5 | 49.3 |

The clean hazard, conservative-risk, social-risk, open-paved and overhead-confounded tiles all showed high Tmrt at midday and early afternoon. The clean shaded reference remained much cooler throughout the day.

The key contrast is between T01 and T05:

| Hour | T01 − T05 Tmrt difference (°C) |
|---:|---:|
| 10:00 | 13.4 |
| 12:00 | 26.1 |
| 13:00 | 26.2 |
| 15:00 | 24.6 |
| 16:00 | 17.0 |

At 13:00, the clean hazard focus cell was **26.2°C hotter in Tmrt** than the clean shaded reference. This is the strongest evidence that local canopy and radiation geometry strongly structure pedestrian radiant exposure.

### 5.2 SOLWEIG Tmrt versus empirical globe-term proxy

The empirical globe-term proxy used in the WBGT screening model is much lower than SOLWEIG Tmrt in exposed cells. The table below shows:

```text
SOLWEIG Tmrt − empirical globe-term proxy
```

| Hour | Clean hazard T01 | Conservative risk T02 | Social risk T03 | Open paved T04 | Shaded reference T05 | Overhead diagnostic T06 |
|---:|---:|---:|---:|---:|---:|---:|
| 10:00 | +16.72 | +15.30 | +13.07 | +12.31 | +3.32 | +14.78 |
| 12:00 | +29.74 | +27.78 | +26.97 | +25.39 | +3.63 | +27.16 |
| 13:00 | +30.70 | +28.67 | +27.11 | +25.94 | +4.48 | +28.06 |
| 15:00 | +29.79 | +27.72 | +24.69 | +24.26 | +5.18 | +27.06 |
| 16:00 | +21.40 | +19.71 | +16.55 | +16.04 | +4.36 | +19.17 |

The clean hazard tile remained about 30°C above the empirical globe-term proxy at both 13:00 and 15:00. This indicates that the empirical proxy does not capture the full local radiant heat environment in exposed urban settings.

### 5.3 Evidence for afternoon radiant-load persistence

At T01, incoming shortwave radiation declined from 753 W/m² at 13:00 to 576 W/m² at 15:00. However, the SOLWEIG-minus-empirical-globe-term difference barely changed:

```text
13:00 delta = +30.70°C
15:00 delta = +29.79°C
change = −0.91°C
```

This supports the v0.9-beta hypothesis that afternoon WBGT residuals are partly linked to radiant-heat processes that are not represented by the empirical proxy, including delayed surface heating, longwave emission from sunlit urban surfaces, and geometry-dependent radiation exposure.

This does not prove that heated-wall longwave radiation is the only mechanism. However, it is consistent with the earlier beta calibration finding that afternoon residuals persisted after instantaneous shortwave radiation had already declined.

### 5.4 Overhead-infrastructure blind spot

The overhead-confounded tile T06 had substantial overhead-infrastructure presence and was deliberately retained as a diagnostic case. Despite this, its SOLWEIG Tmrt was only slightly lower than the clean hazard tile:

| Hour | T01 − T06 Tmrt difference (°C) |
|---:|---:|
| 10:00 | 1.9 |
| 12:00 | 2.5 |
| 13:00 | 2.6 |
| 15:00 | 2.7 |
| 16:00 | 2.2 |

At 13:00, T06 was only **2.6°C cooler** than T01. Because the current DSM includes buildings and tree canopy but not elevated transport or covered pedestrian infrastructure, SOLWEIG cannot fully capture the overhead shading that may occur under viaducts, elevated rail, flyovers, pedestrian bridges or covered walkways.

This is not a failure of the tile experiment; it is a quantified blind spot. It indicates that future versions should develop a separate overhead infrastructure layer or transport/covered-walkway DSM.

---

## 6. Interpretation

### 6.1 SOLWEIG validates the physical relevance of v0.8 hotspots

The clean hazard and open-paved hotspots selected from the v0.8 UMEP+vegetation model remain high-Tmrt locations under SOLWEIG. This supports the interpretation that OpenHeat v0.8 heat-hazard hotspots are not merely artifacts of proxy feature engineering; they correspond to high radiant-load environments when evaluated with a more detailed radiation model.

### 6.2 Risk-priority tiles are not always the hottest, but remain heat-relevant

The conservative-risk and social-risk tiles are slightly cooler than the clean hazard tile but still experience high Tmrt. This supports the v0.8 risk-scenario logic: intervention-priority locations need not be the absolute hottest cells if they combine sufficiently high heat hazard with higher vulnerability or public outdoor exposure.

### 6.3 Shaded reference performance confirms canopy importance

The shaded reference tile remains much cooler than the hazard tiles across all hours. This is direct evidence that canopy and shade can substantially reduce radiant heat exposure. The magnitude of the T01–T05 contrast is much larger than typical air-temperature differences and should be interpreted specifically as a radiant-exposure / Tmrt contrast.

### 6.4 Overhead infrastructure should become a future morphology layer

The T06 diagnostic result shows that overhead infrastructure is not merely a cartographic detail. It can materially affect pedestrian radiant exposure but is not represented in the current building+canopy DSM. This motivates a future v1.0 layer for elevated roads, rail viaducts, pedestrian bridges and covered walkways.

---

## 7. Limitations

1. **Single-day pilot**  
   SOLWEIG was run for one event day, 2026-05-07, using S128 forcing. Results should be interpreted as a selected-tile validation experiment, not a full seasonal validation.

2. **Selected tiles, not full-domain SOLWEIG**  
   The analysis covers six selected tiles. It validates representative microclimatic contexts but does not provide a full-domain SOLWEIG Tmrt map for all 986 grid cells.

3. **Empirical globe-term proxy is not Tmrt**  
   The comparison is between SOLWEIG Tmrt and an empirical globe-temperature term used in the WBGT screening proxy. This is useful for diagnosing radiant-load underrepresentation, but it is not a strict Tmrt-vs-Tmrt validation.

4. **Overhead infrastructure not modelled**  
   Elevated roads, viaducts, covered walkways and pedestrian bridges are not included in the current DSM. T06 demonstrates that this can lead to overestimated radiant exposure in overhead-confounded cells.

5. **Isotropic sky assumption**  
   Anisotropic sky was not enabled in the final SOLWEIG runs. This may introduce a modest systematic Tmrt bias but is expected to have less impact on inter-tile contrasts than on absolute Tmrt.

6. **Cloud and longwave forcing simplification**  
   The cloud parameterisation used in the forcing may not fully represent optical cloud transmissivity. This can affect longwave estimates and absolute Tmrt.

7. **Tile-mean dilution**  
   Buffered tile means dilute the focus-cell signal. Scientific interpretation should prioritise focus-cell results and use tile means only as contextual diagnostics.

8. **Vegetation parameter assumptions**  
   Vegetation transmissivity was set to 3% and trunk-zone height to 25% of canopy height. These assumptions should be tested in a future transmissivity sensitivity analysis.

---

## 8. Implications for OpenHeat

### 8.1 For v0.9-beta calibration

The SOLWEIG results support the idea that part of the v0.9-beta afternoon residual pattern is physical rather than purely statistical. The empirical WBGT proxy underrepresents radiant heat in exposed urban settings, especially during early afternoon when surfaces remain radiatively hot.

### 8.2 For v0.9-delta sensitivity

Two sensitivity experiments should follow:

1. **Vegetation transmissivity sensitivity**  
   Test transmissivity values such as 3%, 10% and 20% to quantify how strongly canopy optical assumptions affect Tmrt and hotspot ranking.

2. **Multi-date SOLWEIG sensitivity**  
   Repeat selected-tile SOLWEIG for additional dates, such as equinox, June solstice, December solstice and future high-WBGT event days.

### 8.3 For v1.0 morphology development

The overhead-infrastructure blind spot should become a dedicated morphology-development task. Potential approaches include:

- extracting bridges, viaducts, elevated rail and covered walkways from OSM / LTA / municipal data;
- converting them into an overhead canopy or transport-DSM layer;
- testing whether T06 Tmrt decreases when overhead infrastructure is represented;
- comparing building+canopy-only versus building+canopy+overhead SOLWEIG.

### 8.4 For ML residual learning

The SOLWEIG experiment strengthens the case for **physics-informed residual learning** rather than black-box heat-stress prediction. ML should learn residuals after the best available physical/radiation representation, not replace the physical model. The current 24-hour archive is still too short for robust ML training, but the gamma results help identify which physical features should enter future residual models.

---

## 9. Final conclusion

v0.9-gamma provides the strongest physical validation so far in the OpenHeat workflow. The selected-tile SOLWEIG experiment shows that:

- clean heat-hazard tiles experience very high Tmrt under the same meteorological forcing;
- shaded reference areas remain dramatically cooler in radiant-exposure terms;
- the empirical WBGT globe-term proxy substantially underrepresents local radiant heat in exposed cells;
- afternoon radiant load persists even after shortwave radiation declines;
- overhead infrastructure is a real and quantifiable blind spot in the current building+canopy DSM.

Therefore, v0.9-gamma successfully bridges the v0.8 spatial heat-risk screening system and the next stage of physically richer heat-stress modelling. It supports the use of SOLWEIG/Tmrt as the next physical upgrade layer and identifies transport / covered-walkway infrastructure as a high-priority future morphology component.

---

## 10. Recommended next steps

1. Use this report as the final v0.9-gamma findings section.
2. Generate three figures:
   - focus-cell Tmrt diurnal profile by tile type;
   - T01–T05 Tmrt contrast by hour;
   - SOLWEIG-minus-empirical proxy delta by hour.
3. Run vegetation transmissivity sensitivity at 3%, 10% and 20%.
4. Repeat selected-tile SOLWEIG on at least one additional date.
5. Design an overhead-infrastructure DSM / canopy layer for v1.0.
6. Continue NEA archive collection until at least 14–30 days are available before starting robust ML residual learning.
