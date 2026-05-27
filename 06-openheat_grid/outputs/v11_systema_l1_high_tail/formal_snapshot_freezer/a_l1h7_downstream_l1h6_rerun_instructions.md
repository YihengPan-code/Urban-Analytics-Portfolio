# Downstream A-L1H.6 Rerun Instructions

Run A-L1H.6 only after A-L1H.7 has written and reviewed a real frozen formal
snapshot table. A-L1H.7 does not run A-L1H.6 automatically.

```bash
python scripts/v11_l1h6_run_prospective_eval_harness.py --config configs/v11/systema_l1h6_prospective_eval_harness.yaml
```

Expected setup before rerun:

- The frozen snapshot is a compact CSV/CSV.GZ/Parquet table under a configured
  A-L1H.6 candidate path.
- Required A-L1H.6 columns are present exactly or safely bridged by A-L1H.7.
- Forbidden columns are absent.
- Prospective rows are real rows, not placeholders.
- `p_ge31_optional` remains an optional diagnostic companion.
- `p_ge33_optional` remains exploratory unless future support and calibration
  evidence meet the registered gates.
