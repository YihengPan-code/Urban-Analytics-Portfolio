# OpenHeat v0.7.1 Census parser hotfix

This hotfix makes `parse_census_age_table()` robust to Census 2020 column-name variants such as `Total_90_Over`, `Total_90_and_Over`, or related normalised forms.

Apply from the project root:

```bat
python scripts\patch_v071_census_parser.py
```

Then rerun:

```bat
python scripts\v071_build_risk_exposure_features.py --config configs\v071_risk_exposure_config.example.json
```
