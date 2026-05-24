# Codex task: OpenHeat v1.1-beta-formula audit

You are working in `Urban-Analytics-Portfolio/06-openheat_grid`.

Task scope: implement and validate a companion System A WBGT formula sensitivity audit.

Do not:
- modify v1.1-beta-formal outputs;
- rerun calibration baselines unless explicitly asked;
- start ML;
- start v1.2 SOLWEIG / surrogate / hazard maps;
- commit snapshot CSVs, OOF prediction CSVs, rasters, SOLWEIG outputs, raw archive, or large forecast CSVs.

Read first:
- AGENTS.md
- docs/v11/OpenHeat_v11_beta_formal_findings_report_CN.md
- docs/v11/OpenHeat_17d_archive_quality_note_CN.md
- docs/v11/OpenHeat_v11_beta_formal_run_log_20260524_CN.md
- docs/handoff/OpenHeat_v1_1_v1_2_canonical_development_handoff_2026-05-24.md

Branch:
`feat/v11-beta-formula-audit`

Implement or review these files:
- `configs/v11/v11_formula_audit_config.example.json`
- `scripts/v11_formula_audit_compare.py`
- `docs/v11/System_A_WBGT_formula_audit_CN_TEMPLATE.md`

Minimum audit:
1. Load frozen v091 snapshot.
2. Compare existing `wbgt_proxy_v09_c` with transparent formula variants.
3. Report bias/MAE/RMSE/R² vs `official_wbgt_c`.
4. Report threshold confusion at 31°C and 33°C.
5. Report threshold crossing flips vs existing v09 proxy.
6. Report by-station and by-day bias.
7. Write a Markdown audit report under `outputs/v11_formula_audit/`.

Optional but preferred:
- Try a validated Liljegren/PyWBGT route only if dependency installation and input mapping are stable.
- If not stable, document it as deferred instead of faking a result.

Validation commands:
```bat
python -m py_compile scripts\v11_formula_audit_compare.py
python scripts\v11_formula_audit_compare.py --config configs\v11\v11_formula_audit_config.example.json
python scripts\v11_archive_commit_guard.py --repo-root . --staged-only --max-mb 25
```

Before finishing, report:
1. changed files;
2. commands run;
3. outputs generated;
4. any failed commands;
5. interpretation caveats.

Do not push or open PR until the user approves the diff.
