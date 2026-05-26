# A-L1H.1 Status

Status: PASS
Diagnostic decision: WEAK_OR_NEGATIVE
Generated: 2026-05-26
Branch: codex/systema-l1h-formula-proxy-audit

## Scope

Formula-v2 / physical proxy diagnostic audit for System A L1H high-tail compression. No ML training, probability calibration, high-tail regression, A-L2, System B, SOLWEIG, raster, raw archive, or archive collector changes.

## Command

- `python scripts/v11_l1h_run_formula_proxy_audit.py --config configs/v11/systema_l1h_formula_proxy_audit.yaml`

## Files Created / Modified

- `outputs/v11_systema_l1_high_tail/formula_proxy_audit/formula_input_inventory.csv`
- `outputs/v11_systema_l1_high_tail/formula_proxy_audit/formula_candidate_registry.csv`
- `outputs/v11_systema_l1_high_tail/formula_proxy_audit/formula_candidate_predictions.csv.gz`
- `outputs/v11_systema_l1_high_tail/formula_proxy_audit/formula_component_diagnostics.csv`
- `outputs/v11_systema_l1_high_tail/formula_proxy_audit/formula_overall_metrics.csv`
- `outputs/v11_systema_l1_high_tail/formula_proxy_audit/formula_threshold_metrics_31_33.csv`
- `outputs/v11_systema_l1_high_tail/formula_proxy_audit/formula_residual_by_observed_bin.csv`
- `outputs/v11_systema_l1_high_tail/formula_proxy_audit/formula_residual_by_radiation_regime.csv`
- `outputs/v11_systema_l1_high_tail/formula_proxy_audit/formula_ge31_miss_by_regime.csv`
- `outputs/v11_systema_l1_high_tail/formula_proxy_audit/formula_physics_audit_report.md`
- `outputs/v11_systema_l1_high_tail/formula_proxy_audit/A_L1H_1_STATUS.md`

## Key Results

- Best diagnostic formula candidate: stull_globe_shortwave_radiation_k0p012_wf0p25
- Best formula note: Least-compressed raw formula/proxy by observed-ge31 residual was stull_globe_shortwave_radiation_k0p012_wf0p25; MAE=1.359 C, max_pred=29.777 C, best-F1 ge31 threshold=27.05 C.
- Comparator reference: M7_compact_weather_ridge
- High-tail comparison: stull_globe_shortwave_radiation_k0p012_wf0p25 mean observed-ge31 residual=3.854 C versus M7_compact_weather_ridge=0.873 C (positive means official minus prediction; improvement=-2.981 C).
- Fixed_31 result: No raw formula/proxy candidate produced fixed_31 crossings.
- Radiation-hot result: stull_globe_shortwave_radiation_k0p012_wf0p25 radiation-hot ge31 miss rate=1.000; M7_compact_weather_ridge radiation-hot ge31 miss rate=0.428.
- Next recommended action: A-L1H.2 probability / threshold calibration review is the more direct next action; keep deeper formula-v2 and high-tail regression behind review gates, and start A-L2 only after Level 1 high-tail / regime control.

## Caveats

- A-L1H.0c supports prioritising formula/proxy audit; it does not prove v09 caused compression.
- Formula candidates are screening diagnostics and are not canonical WBGT_A replacements.
- ge33 remains exploratory.

## Safe To Commit

- Config, scripts, docs, and compact diagnostic outputs from this lane after review.

## Not Safe To Commit

- Raw archives, rasters, SOLWEIG outputs, tif/tiff files, svfs.zip, patch zip packages, or large hourly forecast CSVs.
