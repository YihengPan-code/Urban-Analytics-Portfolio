# OpenHeat-ToaPayoh — Codex / AI Agent Instructions

This repository is the OpenHeat-ToaPayoh urban heat project. Treat this file as binding project guidance for Codex and any coding agent.

## Current canonical identity

OpenHeat is currently:

> A WBGT-gated, SOLWEIG-informed, surrogate-assisted local heat hazard ranking prototype for Toa Payoh, Singapore.

It is **not** a validated 100m-cell local WBGT prediction system, not a real-time public health warning system, and not a completed risk model.

## Current priority

Only work on the current v1.1 tracks unless the task explicitly says otherwise:

1. `v1.1-beta-formal`: frozen-snapshot formal calibration closeout for System A.
2. `v1.1-ops-gha-migration`: GitHub Actions archive continuity.
3. `v1.1-beta-formula`: companion WBGT formula audit, not retroactive recalibration.
4. `v1.1-beta-evidence`: report / quality note / one-pager / docs index.

Do **not** start v1.2 SOLWEIG, surrogate ML, risk maps, dashboards, or 150-cell batch work unless the issue explicitly asks for it.

## Claim boundaries

Never silently upgrade claims.

Allowed wording:

- calibrated hourly WBGT temporal baseline;
- simulation-informed local radiative modifier;
- WBGT-gated local radiative hazard score;
- first-order local heat hazard prioritisation;
- future risk overlay after exposure and vulnerability are explicit.

Disallowed wording:

- validated local WBGT prediction;
- real-time heat risk forecast;
- SOLWEIG Tmrt equals WBGT;
- ML surrogate calibrates observed local WBGT;
- hazard map equals risk map;
- feature importance proves real-world causal heat-risk drivers.

## Development rules

- Use `pathlib`, type hints, docstrings, small functions, and clear CLI arguments.
- Prefer additive scripts and docs over hot-path refactors.
- Do not touch the archive collector hot path unless the task explicitly asks for it.
- Formal comparisons must use a frozen snapshot, never a live-growing archive.
- Every new script must declare inputs, outputs, and saved metrics in its docstring / `--help`.
- Every diagnostic script must write machine-readable CSV/JSON plus a short Markdown summary.
- Use deterministic seeds where randomness is involved.
- Avoid random train/test splits for station/time/spatial data; use LOSO, blocked-time, spatial/scenario/typology holdouts as appropriate.

## Git hygiene: do not commit heavy or raw files

Never commit:

```text
*.tif
*.tiff
svfs.zip
data/solweig/
data/rasters/
data/archive/
data/raw/buildings_v10/
outputs/*forecast_live/*hourly_grid_heatstress_forecast*.csv
patch zip packages
raw API dumps
```

For GitHub Actions archive continuity, only commit controlled compact artifacts when explicitly configured, such as:

```text
data/calibration/v11/live_chunks/*.csv.gz
outputs/v11_archive_ops/*.json
outputs/v11_archive_ops/*.md
outputs/v11_archive_ops/*.csv
```

If a file is larger than the configured guard threshold, stop and ask for review rather than committing it.

## H10 standard

The v1.1 H10 invariant is strict:

```text
M5_v10_morphology_ridge, M6_v10_overhead_ridge, and M7_compact_weather_ridge
must be identical to 6 decimal places in formal H10 checks.
```

Do not weaken this to "near identical". If identity breaks, audit schema / aggregator / imputer / station_to_cell mapping first. Do not claim morphology suddenly works.

## Formal pass interpretation rules

Pre-register counterfactual handling:

- If M4-M3 bootstrap CI includes 0, downgrade wording to "not distinguishable under the formal snapshot".
- If M4 loses regression advantage, report honestly; do not force it as winner.
- If M7 fixed_31 F1 drops below the stability threshold, downgrade threshold classification claims.
- If ≥33 events remain dominated by S142, keep ≥33 modeling exploratory.
- If row attrition is large, diagnose target/proxy missingness before interpreting metrics.

## Codex workflow expectation

Open a branch, keep PRs small, and include:

- changed files list;
- exact commands run;
- key outputs and paths;
- known limitations;
- whether any generated data are intentionally uncommitted.

For PR review, focus on: claim boundary, frozen-snapshot correctness, archive safety, large-file safety, and reproducibility.
