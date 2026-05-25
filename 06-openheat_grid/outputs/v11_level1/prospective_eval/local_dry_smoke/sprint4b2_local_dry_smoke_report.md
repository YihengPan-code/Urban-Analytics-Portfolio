# Sprint 4B.2 — Local-only Prospective Metadata Dry Smoke

## Status
PASS

## Scope
- local-only
- offline
- synthetic prospective rows
- no API
- no archive modification
- no collector runtime modification
- no model training
- no forecast skill

## Inputs
- `scripts/v11_prospective_metadata_helpers.py`
- `scripts/v11_test_prospective_metadata_schema.py`
- `configs/v11/system_a_prospective_metadata_config.example.yaml`
- `configs/v11/system_a_local_prospective_dry_smoke_config.example.yaml`
- `docs/v11/SystemA_prospective_metadata_schema_CN.md`
- `outputs/v11_level1/prospective_eval/metadata_patch/sprint4b1_metadata_patch_report.md`
- `outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.csv`
- `outputs/v11_level1/prospective_eval/metadata_patch/prospective_metadata_schema_smoke.md`
- `outputs/v11_level1/prospective_eval/prospective_metadata_gap_audit.csv`
- `docs/v11/SystemA_Level1_prospective_eval_design_CN.md`

## Outputs
- `outputs\v11_level1\prospective_eval\local_dry_smoke\synthetic_prospective_rows.csv`
- `outputs\v11_level1\prospective_eval\local_dry_smoke\legacy_compatibility_rows.csv`
- `outputs\v11_level1\prospective_eval\local_dry_smoke\local_dry_smoke_manifest.json`
- `outputs\v11_level1\prospective_eval\local_dry_smoke\local_dry_smoke_manifest.md`
- `outputs\v11_level1\prospective_eval\local_dry_smoke\local_dry_smoke_validation.csv`
- `outputs\v11_level1\prospective_eval\local_dry_smoke\local_dry_smoke_validation.md`
- `outputs\v11_level1\prospective_eval\local_dry_smoke\sprint4b2_local_dry_smoke_report.md`

## Synthetic prospective rows
- Row count: 63
- Station count: 3
- Lead-time bins: [0, 1, 3, 6, 24]
- Valid_time range: 2026-05-26T00:00:00Z to 2026-05-27T00:00:00Z
- Quality_flag counts: {'missing_forecast_issue_time': 3, 'missing_lead_time': 3, 'missing_model_run_time': 3, 'ok_prospective_metadata': 60}
- Issue_valid_pair_id uniqueness: True

## Fail-closed checks
- Missing issue/model time rows with null lead_time: 3
- Missing flags present: checked in validation output.
- No row with missing_lead_time is eligible for skill evaluation.

## Legacy compatibility
- Legacy rows sampled: yes, 10 rows from `data\calibration\v11\live_chunks\wbgt_pairs_2026-05-24.csv.gz`.
- legacy_missing_prospective_metadata flags confirmed: True.
- Forecast lead time is null for the legacy compatibility view.

## Validation checks
- Checks passed: 11/11
- Overall validation status: PASS

## What this proves
- helper/schema can produce future prospective metadata-shaped rows
- quality flags and fail-closed behavior work locally
- manifest structure is ready for review

## What this does not prove
- no live collection
- no Open-Meteo provider run metadata
- no NEA retrieval delay measurement
- no prospective forecast skill
- no GHA/local parity
- no operational forecast

## Next recommended action
- Review helper/schema before any live smoke.

## Safety statements
- no forbidden files touched
- no API calls
- no archive modification
- no collector runtime modification
- no model training
- no System B/v12 touched
- no commit/stage performed