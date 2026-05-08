# v0.7.1.2 Census parser hotfix

This fixes a bug in the first hotfix patch script where `re.subn()` treated `\d` inside the replacement function as a replacement-template escape.

Run from project root:

```bat
python scripts\patch_v071_census_parser_v2.py
python scripts\v071_build_risk_exposure_features.py --config configs\v071_risk_exposure_config.example.json
```

The new parser dynamically detects all `Total_*` age-band columns with starting age >= 65, so it no longer depends on one exact 90+ column name.
