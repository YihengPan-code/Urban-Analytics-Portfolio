# B8.6g Status

Status: B86G_FEATURE_ACQUISITION_PASS
Branch: codex/b86g-vector-compact-feature-acquisition
Scope: System B vector/compact feature acquisition for surrogate spatial closure.

## Commands Run By Suite

- `python scripts/v12_b86g_run_feature_acquisition.py --config configs/v12/systemb_b86g_feature_acquisition.yaml`

## Key Results

- Sources scanned: 1256
- Usable sources: 982
- High-priority feature families computed: pedestrian-accessible shaded fraction, overhead geometry shape descriptors, sunlit-hot-pocket area fraction, tree/building shadow interaction, canyon orientation / height roughness
- N150 feature dataset shape: (150, 41)
- N300 candidate feature dataset shape: (150, 41)
- Retest readiness: PARTIAL_RETEST_ONLY
- AOI/B9 status: AOI_PREFLIGHT_BLOCKED / B9_BLOCKED
- Recommended next lane: B8.6g2 partial feature-upgraded retest plus B8.7-N300-PRE design freeze

## Caveats

B8.6g creates feature tables, schema, readiness, failure-context joins, and future prompts only. It does not train a final surrogate, create AOI-wide prediction, create B9 output, run QGIS/SOLWEIG, read/write rasters, produce local WBGT, hazard/risk score, observed-truth claims, causal feature-importance claims, Tmrt-to-WBGT conversion, or System A/B coupling.

## Safe To Commit After Review

Controlled B8.6g config, scripts, docs, CSV, and Markdown outputs.

## Not Safe To Commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, raw SOLWEIG/archive files, patch zip packages, AOI-wide prediction outputs, B9 outputs, WBGT, hazard_score, risk_score, and System A/B coupling outputs.
