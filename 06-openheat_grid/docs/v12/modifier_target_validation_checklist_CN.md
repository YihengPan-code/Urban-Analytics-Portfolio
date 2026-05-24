# v1.2-alpha modifier target validation checklist

Use this checklist before moving from v1.2-alpha to v1.2-beta SOLWEIG typology pilot.

## Target definition

- [ ] `tmrt_p90_c` defined.
- [ ] `delta_tmrt_p90_c` defined.
- [ ] `m_rad_pct` defined.
- [ ] `m_rad_robust01` defined.
- [ ] Reference method explicitly defined as same-hour/same-scenario median `tmrt_p90_c` over the reference domain.
- [ ] Normalization domain explicitly defined.
- [ ] No local-WBGT conversion formula is introduced.

## Claim boundaries

- [ ] Does not call ΔTmrt ΔWBGT.
- [ ] Does not call Tmrt WBGT.
- [ ] Does not call hazard risk.
- [ ] Does not call surrogate calibration.
- [ ] Does not claim observed truth.

## Pilot readiness

- [ ] 8-12 cells selected.
- [ ] v10 anchors included: `TP_0565`, `TP_0986`, `TP_0088`, `TP_0916`, `TP_0433`.
- [ ] Required typologies covered.
- [ ] Hours fixed to 10, 12, 13, 15, 16 SGT.
- [ ] Scenario IDs fixed.
- [ ] Forcing IDs fixed.
- [ ] Output schema fixed.
- [ ] Proposed non-anchor candidate cells have been manually checked before SOLWEIG execution.

## Sanity checks

- [ ] Open sunlit cells hotter than shaded cells.
- [ ] TP_0433-like shaded reference low and stable.
- [ ] TP_0986-like null control near-zero base/overhead delta.
- [ ] TP_0088 / TP_0916 overhead scenarios reduce Tmrt.
- [ ] p90 adds information beyond mean.
- [ ] No surrogate training if sanity checks fail.
- [ ] No hazard-map production until modifier outputs pass pilot checks.
- [ ] No risk-layer spatial-product wording unless exposure and vulnerability are explicitly integrated later.
