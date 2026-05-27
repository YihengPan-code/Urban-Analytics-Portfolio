# B8.5-F4 Surrogate Role Decision

Generated: 2026-05-27 16:12:41

## Decision

`SURROGATE_PROTOCOL_READY_N24_STRESS_VALIDATION_NO_TRAINING_IN_F4`

## Proceed / Do Not Proceed

- Surrogate target-card / protocol suite: `ALLOW`.
- Baseline surrogate training on existing N150 labels: `ALLOW_AS_SEPARATE_REVIEWED_LANE`; no training is performed in F4.
- N24 as multi-forcing stress-validation set: `ALLOW`.
- N150 multi-forcing expansion: `ALLOW_N150_CONTROLLED_EXECUTION_AFTER_PRECHECK`.

## Boundary

System B may use N24 as a stress-validation set for SOLWEIG-derived radiative modifier labels. It must not claim observed WBGT calibration, risk, causal feature importance, B9 readiness, or System A/B coupling from F4.
