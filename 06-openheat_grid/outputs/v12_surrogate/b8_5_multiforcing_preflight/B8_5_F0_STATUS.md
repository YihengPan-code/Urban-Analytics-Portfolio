# B8.5-F0 Status

Generated: 2026-05-26

## Status

PASS

## Branch

`codex/b85-multiforcing-preflight`

## Scope

Preflight / protocol / manifest design only for System B multi-forcing sensitivity. No QGIS, no SOLWEIG, no rasters, no AOI-wide inference, no local WBGT, no `hazard_score`, no `risk_score`, and no System A/B coupling output.

## Commands Run

- `C:/Users/CloudStar/anaconda3/envs/openheat/python.exe scripts/v12_b85_run_multiforcing_preflight.py --config configs/v12/systemb_b85_multiforcing_preflight.yaml`
- B8.5-F0b documentation hygiene patch only; no QGIS/SOLWEIG execution.

## Key Results

- N24 cells: `24`
- N24 provenance: `original_retained_n24_cells`
- N24 fallback used: `no`
- Selected forcing days: `FD01_high_shortwave_hot_20260507`, `FD02_humid_hot_cloudy_or_diffuse_20260508`
- FD01 interpretation: GE31-rich high-shortwave/hot forcing day.
- FD02 interpretation: contrast day for humidity/cloud/diffuse/radiation diversity; official GE31 observations are unavailable in the local paired station file and the day is not treated as GE31-rich.
- Run matrix rows: `480`
- QGIS/SOLWEIG executed: `no`

## Caveats

- A-L1H weather-regime outputs were not present in this B8 worktree and are marked missing in the candidate inventory.
- Available forcing-day selection relies on configured System A/archive weather sources, especially v09 hourly forecast rows when A-L1H files are absent.
- This does not validate local WBGT prediction and does not approve B9 AOI-wide inference.

## Files Created / Modified

- `docs/v12/OpenHeat_SystemB_B8_5_multiforcing_preflight_CN.md`
- `outputs/v12_surrogate/b8_5_multiforcing_preflight/candidate_forcing_day_inventory.csv`
- `outputs/v12_surrogate/b8_5_multiforcing_preflight/selected_forcing_days.csv`
- `outputs/v12_surrogate/b8_5_multiforcing_preflight/b85_f0_stability_metrics_protocol.md`
- `outputs/v12_surrogate/b8_5_multiforcing_preflight/b85_f0_qgis_execution_readme.md`
- `outputs/v12_surrogate/b8_5_multiforcing_preflight/B8_5_F0_STATUS.md`

## Safe To Commit

Protocol scripts, config, docs, and compact CSV/Markdown outputs listed above after human review.

## Not Safe To Commit

Any rasters, `data/solweig/`, `data/rasters/`, raw archive dumps, large forecast CSVs, or generated SOLWEIG execution products outside this compact preflight output set.

## Next Recommended Action

Review the B8.5-F0 manifest and selected forcing days. If accepted, run the future QGIS/SOLWEIG execution lane against this manifest, then compute the stability metrics before any B9 AOI-wide inference decision.
