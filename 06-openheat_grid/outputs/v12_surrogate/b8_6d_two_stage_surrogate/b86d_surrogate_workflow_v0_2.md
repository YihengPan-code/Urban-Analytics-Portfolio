# B8.6d Surrogate Workflow v0.2

Generated: 2026-05-27 20:29:14

## Contract

1. Use F5 compact pairwise labels and B8.6c safe compact features only.
2. Keep `delta_tmrt_p90_c` as the primary hot-pocket / upper-tail target.
3. Stage 1 classifies neutral boundary versus meaningful cooling; positive or weak warming is tracked but not promoted.
4. Stage 2 regresses/ranks non-neutral magnitudes.
5. Combined prediction is conservative: Stage 1 neutral or other-positive rows receive 0.0 delta; meaningful-cooling rows receive Stage 2 delta.
6. Evidence uses forcing-day, cell-group, spatial, typology, and hour holdouts. Random row split is not main evidence.
7. Feature importance is diagnostic only and non-causal.
8. B9, AOI-wide prediction, local WBGT, hazard_score, risk_score, raster, QGIS/SOLWEIG, Tmrt-to-WBGT conversion, and System A/B coupling remain forbidden in this lane.
