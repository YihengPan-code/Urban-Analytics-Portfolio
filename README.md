# Urban Analytics Portfolio

Yiheng Pan  
Department of Environmental Science, University of Plymouth

This repo is a compact portfolio-style collection of 3 mini projects to demonstrate:
- GIS + spatial statistics in urban problems (QGIS / R)
- spatially-aware modelling decisions (avoid leakage / heterogeneity)
- building small tools for reproducible environmental metrics (HTML/JS)

## Projects

### 1) Heat Exposure Prediction — Explainable ML + Spatial Block CV
**Story:** Random CV can be overly optimistic under spatial autocorrelation; spatial blocking is a more honest evaluation.  
**Stack:** Python, scikit-learn, explainability (feature importance), spatial block CV  
- Folder: `projects/01-heat-exposure-ml/`  
- Key files: `README.md`, `requirements.txt`, `talk_track.md`, `OnePager_TechnicalSummary.pdf`

### 2) Bristol Burglary vs Deprivation — Spatial Heterogeneity (R + QGIS)
**Story:** Burglary hotspots are not confined to the most deprived areas; the poverty–crime relationship is spatially non-stationary.  
**Stack:** R, QGIS, DBSCAN hotspot detection, GWR, non-parametric tests  
- Folder: `projects/02-bristol-burglary-imd/`

### 3) Green View Index (GVI) Quantification Tool — HSV Segmentation + Artifact Exclusion
**Story:** A lightweight, configurable browser tool to quantify street-level greenness with transparent parameters and exportable masks/results.  
**Stack:** HTML/JS, image processing (HSV), parameter presets, batch export  
- Folder: `projects/03-gvi-tool/`

## Repo layout (recommended)
