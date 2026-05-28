# OpenHeat Active Development Board - 2026-05-28

## Latest Stable Checkpoints

- System A: `A_L1H8_DOSSIER_PASS`, frozen/waiting, `wbgt_a_c` primary.
- System B: `B87G0_EXTERNAL_SOURCE_REQUIRED`; best local-source checkpoint remains `B87F2_FEATURE_PATCH_PARTIAL_NO_AOI`.
- B87C raw SOLWEIG: `3000/3000` success, 150 cells, 2 forcing days, 5 hours, 2 scenarios, 0 missing/empty Tmrt.
- B87D labels: 3000 N300 pairwise rows, 300 cells, 0 old/new overlap.

## Active / Paused Lanes

| lane | state | next |
| --- | --- | --- |
| System A formal snapshot | paused | wait for real compact formal snapshot |
| System A prospective eval | paused | run only after A-L1H.7 frozen snapshot |
| System B surrogate | blocked | external true-vector source acquisition or close phase |
| AOI/B9 | blocked | source gates plus explicit approval required |
| Product C coupling | deferred | needs System A formal pass and System B AOI preflight |
| Risk | deferred | needs explicit exposure/vulnerability layer |

## Recommended Next Lane

`System B external true-vector acquisition or closure note`; for System A, `formal snapshot reactivation` only if a real reviewed snapshot exists.

## Branches If Known

- Primary current branch at devlog start: `codex/b87g0-source-breakthrough-attempt`.
- System A evidence sibling branch: `codex/systema-development-dossier`.

## Forbidden Files

- `*.tif`
- `*.tiff`
- `*.vrt`
- `*.asc`
- `*.img`
- `*.nc`
- `*.grib`
- `svfs.zip`
- `data/solweig/`
- `data/rasters/`
- `data/archive/`
- `data/raw/buildings_v10/`
- `outputs/*forecast_live/*hourly_grid_heatstress_forecast*.csv`
- `patch zip packages`
- `raw API dumps`

## Claim Boundaries

- System A = calibrated hourly WBGT_A temporal baseline.
- System B = SOLWEIG-derived Tmrt/radiative spatial layer.
- Product C = future WBGT-conditioned radiative priority.
- Risk = future hazard x exposure x vulnerability, not started.

## Do Not Run Now

- QGIS, SOLWEIG, expensive raster processing, AOI prediction, B9, ML benchmark reruns, WBGT conversion, hazard/risk/exposure/vulnerability output.

## Run Only After Explicit Approval

- QGIS or SOLWEIG execution.
- Expensive raster processing.
- Any AOI/B9 preflight or prediction.
- Any WBGT conversion or Product C coupling lane.
- Any risk/exposure/vulnerability layer.
- Any external data acquisition that changes source licensing or reproducibility.
