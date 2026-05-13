# OpenHeat v10-beta Basic Morphology Patch

解压到项目根目录后运行：

```bat
scripts\v10_run_beta_basic_morphology_pipeline.bat
```

核心输出：

```text
data/grid/v10/toa_payoh_grid_v10_basic_morphology.csv
outputs/v10_morphology/v10_basic_morphology_QA_report.md
outputs/v10_ranking_audit/v10_beta_morphology_shift_audit_report.md
outputs/v10_ranking_audit/v10_old_false_positive_candidates.csv
```

请注意：v10-beta 只是 basic morphology recomputation 和 old-vs-new audit，不是最终 hazard ranking。最终 ranking 需要后续用 reviewed DSM 重跑 UMEP SVF / shadow。
