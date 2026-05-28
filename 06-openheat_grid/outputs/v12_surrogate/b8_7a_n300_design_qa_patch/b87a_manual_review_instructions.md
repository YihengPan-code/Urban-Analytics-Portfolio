# B8.7a N300 Manual QA Instructions

Manual input found: `yes`.

Use `b87a_manual_review_template.csv` as the review worksheet. If you choose
to provide manual decisions, save a CSV with the same columns at:

`outputs/v12_surrogate/b8_7a_n300_design_qa_patch/manual_inputs/b87a_manual_candidate_review.csv`

Valid `manual_decision` values are: `keep`, `exclude`, `replace`,
`source_review`, `unsure`, and `not_reviewed`.

## Review Order

1. Focus first on water / river / pure surface candidates.
2. Then review `west_south`.
3. Then review TP_0037 / TP_0433 anchor-like candidates.
4. Then review neutral diversity candidates.
5. Then review `park_open_space` / commercial undercoverage and residential /
   transport overconcentration.

It is okay to review only obvious exclusions. Uncertain rows can stay as
`unsure` or `not_reviewed`; Codex will keep uncertain rows as REVIEW rather
than auto-excluding them.

## Guardrails

- Do not run QGIS.
- Do not run SOLWEIG.
- Do not use rasters.
- Use lightweight map/table inspection only if you choose.
- This worksheet is not B9, not AOI-wide prediction, not local WBGT, not a
  hazard/risk/exposure/vulnerability score, not observed truth, and not causal
  feature importance.
