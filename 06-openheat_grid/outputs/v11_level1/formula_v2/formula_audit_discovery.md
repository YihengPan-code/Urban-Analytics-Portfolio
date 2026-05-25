# Sprint 3A formula-audit discovery

Existing reusable assets were found for the v1.1 companion WBGT formula audit.

| path                                                             | exists | bytes   |
| ---------------------------------------------------------------- | ------ | ------- |
| scripts/v11_formula_audit_compare.py                             | True   | 24904   |
| configs/v11/v11_formula_audit_config.example.json                | True   | 1154    |
| outputs/v11_formula_audit/System_A_WBGT_formula_audit_report.md  | True   | 27404   |
| outputs/v11_formula_audit/formula_bias_mae_rmse_table.csv        | True   | 1249    |
| outputs/v11_formula_audit/formula_threshold_operating_points.csv | True   | 5459    |
| outputs/v11_formula_audit/formula_comparison_by_row.csv.gz       | True   | 1687454 |
| docs/v11/System_A_WBGT_formula_audit_CN.md                       | True   | 19371   |

Reusable implementation:

- `scripts/v11_formula_audit_compare.py` provides `build_variants`, including `existing_v09_proxy`, `reconstructed_from_v09_components`, and the Stull wet-bulb plus simplified globe k-sweep family.
- `configs/v11/v11_formula_audit_config.example.json` documents the canonical v09 inputs, `wind_offset=0.25`, and the audited k-sweep lineage.
- Existing outputs show `existing_v09_proxy`, `reconstructed_from_v09_components`, and `stull_simple_globe_k0p0045` are identical in the previous 15-minute audit.

Scope boundary:

No advanced Liljegren/Kong-Huber/Brimicombe implementation was found in the v1.1 formula audit lane. Those candidates are treated as feasibility-only in Sprint 3A.
