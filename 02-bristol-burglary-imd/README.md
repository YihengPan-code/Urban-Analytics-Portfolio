# Bristol Burglary & Deprivation (IMD) — Spatial Heterogeneity in R + QGIS

Portfolio-style GIS + spatial statistics mini project (GEES3109).  
Instead of assuming a single city-wide “poverty → crime” gradient, this project tests whether the
burglary–deprivation relationship is **spatially non-stationary** and whether **hotspots** align with deprivation.

**Core takeaway:** global correlations at LSOA level are weak, while hotspot patterns and GWR outputs suggest
**strong spatial heterogeneity** (city-centre opportunity structure vs peripheral neighbourhood effects).

---

## Questions (what I tested)

- **RQ1:** Is burglary density correlated with deprivation (IMD 2019) across Bristol LSOAs?
- **RQ2:** Where are burglary hotspots? Do they appear only in the most deprived areas?
- **RQ3:** Within affluent areas, does being **near deprived LSOAs** increase burglary density?

---

## Workflow (R → QGIS → R)

### Data preparation (R)
- Merge 24 monthly Police street-level crime CSVs (2021–2022)
- Filter `Crime.type == "Burglary"`
- Remove missing coordinates
- Export cleaned burglary points for GIS

### GIS workflow (QGIS)
- Project to **EPSG:27700 (British National Grid)**
- Join **IMD 2019** to **LSOA 2011** boundaries via `LSOA11CD`
- Point-in-polygon counts + density (incidents per km²)
- Export LSOA table back to CSV for statistics

### Stats + clustering (R)
- Normality check: Shapiro–Wilk → non-normal → non-parametric tests
- **Spearman** correlations (IMD indicators vs burglary density/count)
- **Mann–Whitney U** test for RQ3 (“affluent near deprived” vs “affluent far”)
- **DBSCAN** hotspot detection (two-stage parameterisation)
  - Global: eps = 350 m, minPts = 20
  - City-centre micro: eps = 200 m, minPts = 30
  - Parameter support: k-distance plots (k=20, k=30)

### Local modelling (GWR)
- Univariate GWR modelling burglary density ~ IMD score
- Used to visualise **local coefficients** and **local R²** (non-stationarity)

---

## Key outputs (maps)

### GWR — Intercept (baseline burglary level, independent of IMD)
![GWR intercept](<GWR1_intercept.png>)

### GWR — Slope coefficient (how strongly IMD associates with burglary locally)
![GWR slope](<GWR1_slope.png>)

### GWR — Local R² (where deprivation explains burglary better/worse)
![GWR local R2](<GWR1_r_square.png>)

### DBSCAN hotspots (global pattern)
![DBSCAN global](<DBSCAN global.png>)

### DBSCAN hotspots (city-centre micro hotspots)
![DBSCAN city-centre micro](<DBSCAN city-centre micro.png>)

**Interpretation (portfolio-level):**
- Hotspots concentrate strongly in the city centre / major activity corridors, which is consistent with
  **Routine Activity / opportunity structure** explanations.
- GWR outputs indicate the deprivation–burglary association is **not spatially uniform**:
  some areas show stronger local association than others, while large parts of the city show weak explanatory power.

---

## What’s in this folder

- `Bristol_Analysis_Script.R` — merge/clean Police CSVs + non-parametric tests + DBSCAN parameter support
- `GWR1_intercept.png` / `GWR1_slope.png` / `GWR1_r_square.png` — GWR map outputs
- `DBSCAN global.png` / `DBSCAN city-centre micro.png` — clustering map outputs

---

## Data sources (not committed)

Raw data are not committed due to size/licensing. The workflow is reproducible once downloaded:
- Police.uk street-level crime data (Bristol; Jan 2021–Dec 2022; filter Burglary)
- IMD 2019 (England) — score/decile/rank
- ONS Open Geography Portal — LSOA (Dec 2011) boundaries

---

## Reproducibility notes (file expectations)

The current script expects two GIS exports (filenames can be adjusted in the script):
- `bristol_burglary_data.csv`  (LSOA-level table with IMD join + density)
- `burglary_bng.shp`           (burglary points projected to EPSG:27700)

---

## Limitations (honest)

- MAUP: LSOA is a coarse unit; street-level patterns are partially smoothed.
- Police-recorded data: under-reporting + location uncertainty.
- No offender residence data → limited journey-to-crime inference.
- Covariates limited (future: land use, accessibility, nightlife density, student/HMO intensity).

---

## Context
Coursework essay: *“Burglary, Deprivation and Spatial Heterogeneity in Bristol: A Big Data and GIS Analysis”* (GEES3109).
