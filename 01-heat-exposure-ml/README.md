# Heat Exposure Prediction — Explainable ML + Spatial Block CV

This is a compact portfolio-style mini project to demonstrate:
- reproducible ML workflow on urban data
- awareness of **spatial leakage**
- explainability (feature importance) with planning-relevant interpretation

## What you need
- Python 3.10+ (or Google Colab)
- install deps: `pip install -r requirements.txt`

## Data
Place your dataset CSV as:

- `data_output.csv` in the repo root **OR**
- edit `DATA_PATH` in the notebook.

(Do not commit raw data to GitHub if licensing is unclear.)

## Run
Open and run:

- `notebooks/HeatRisk_SpatialCV.ipynb`

It will produce:
- `outputs/summary.json`
- `outputs/rmse_comparison.png`
- `outputs/residual_map_block.png`
- `outputs/feature_importance.png`
- `onepager/OnePager_TechnicalSummary.pdf` (provided as an example format)

## Method summary
- Target: `mean_t` (seasonal mean temperature)
- Model: RandomForestRegressor (tabular ML baseline)
- Validation:
  - Random 5-fold KFold (optimistic baseline)
  - Spatial Block CV via GroupKFold using a 0.02° grid (~2km) to reduce spatial leakage
  - Sensitivity check: leave-location-out CV using location id

## Notes for portfolio / PS
The key story is the **gap between random CV and spatial CV**: it shows you understand why spatial validation matters in environmental ML.

Generated example results (from current data):
- Random KFold RMSE ≈ 0.61°C
- Spatial Block CV RMSE ≈ 1.14°C

