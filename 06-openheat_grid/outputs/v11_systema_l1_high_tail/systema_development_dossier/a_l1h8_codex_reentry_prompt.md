# Codex Re-entry Prompt: Resume System A After Formal Snapshot Exists

You are working inside the OpenHeat-ToaPayoh project subdirectory.

Current lane: System A formal snapshot re-entry after A-L1H.8 frozen handoff.

Before starting:
- Check current directory, git root, branch, `git status -sb -uno`, and `git status --short -- .`.
- Read `outputs/v11_systema_l1_high_tail/systema_development_dossier/A_L1H8_STATUS.md`.
- Read `outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_report.md`.
- Read `outputs/v11_systema_l1_high_tail/systema_development_dossier/a_l1h8_formal_snapshot_waiting_register.csv`.
- Read the frozen A-L1H.5 model card and output contract.
- Confirm the new formal snapshot candidate is real, compact, reviewed, and not a live-growing archive.

Rules:
- Do not train new models unless promotion gates fail and the user explicitly opens a new lane.
- Do not modify A-L1H.5 contract decisions before evaluation.
- Do not modify A-L1H.6 or A-L1H.7 gates without explicit user scope.
- Do not modify archive collector.
- Do not touch System B or SOLWEIG outputs.
- Do not create station-adjusted WBGT, local 100 m WBGT, official warning probability, risk_score, hazard_score, or System A/B coupling output.
- Do not create fake formal snapshot rows.

Re-entry path:
1. If A-L1H.7 has not yet written a frozen snapshot, run a reviewed dry-run/write_snapshot procedure using:

```bash
python scripts/v11_l1h7_run_formal_snapshot_freezer.py --config configs/v11/systema_l1h7_formal_snapshot_freezer.yaml
```

2. After the frozen snapshot manifest and validation pass, rerun:

```bash
python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml
```

3. Evaluate P_ge31 promotion gates against fixed_31 recall/miss behavior, precision/false-alarm behavior, Brier/ECE, and station caveats.
4. Keep P_ge33 exploratory unless support and calibration thresholds are explicit.
5. Update the model card only after formal prospective evidence supports a change.
6. Report exact commands, outputs, limitations, and any generated data intentionally uncommitted.
