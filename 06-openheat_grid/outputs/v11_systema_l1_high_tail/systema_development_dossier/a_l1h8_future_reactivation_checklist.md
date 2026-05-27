# A-L1H.8 Future Reactivation Checklist

Generated: 2026-05-27
Status: System A frozen/waiting.

- [ ] Confirm current branch and worktree status before changing anything.
- [ ] Verify A-L1H.5 contract files still exist and have not been modified.
- [ ] Confirm a real compact formal snapshot candidate exists under a configured candidate path.
- [ ] Review candidate schema for required fields, forbidden fields, row support, ge31/ge33 support, numeric WBGT fields, model/version metadata, quality flags, and retrospective/prospective labels.
- [ ] Run A-L1H.7 freezer in dry-run mode first if the candidate is new.
- [ ] If dry-run checks pass, switch A-L1H.7 config to write_snapshot through a reviewed change and run:

```bash
python scripts/v11_l1h7_run_formal_snapshot_freezer.py --config configs/v11/systema_l1h7_formal_snapshot_freezer.yaml
```

- [ ] Review frozen snapshot manifest and validation outputs.
- [ ] Rerun A-L1H.6 prospective evaluation:

```bash
python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml
```

- [ ] Evaluate P_ge31 promotion gates against fixed_31, calibration, precision/false-alarm behavior, and station caveats.
- [ ] Keep P_ge33 exploratory unless support and calibration thresholds are explicit.
- [ ] Update the model card only after reviewed prospective evidence exists.
- [ ] Do not train new models unless promotion gates fail and the user explicitly opens a new lane.
- [ ] Do not create station-adjusted WBGT, local 100 m WBGT, official warning probability, System A/B coupling output, risk_score, or hazard_score.
