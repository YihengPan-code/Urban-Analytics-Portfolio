"""Run B87E N300 surrogate benchmark end to end.

Inputs:
    configs/v12/systemb_b87e_n300_surrogate_benchmark.yaml,
    B87D N300 pairwise labels, B87D PASS status, and compact feature source
    candidates.

Outputs:
    Required B87E CSV/Markdown artifacts under
    outputs/v12_surrogate/b87e_n300_surrogate_benchmark/ and
    docs/v12/OpenHeat_SystemB_B87E_N300_surrogate_benchmark_CN.md.

Config path:
    --config configs/v12/systemb_b87e_n300_surrogate_benchmark.yaml

Saved metrics:
    Feature inventory/matrix/schema/missingness/leakage audit, target summary,
    split and model registries, model metrics by split and summary, OOF and
    holdout predictions, error strata, top-k/rank metrics, diagnostic feature
    importance, promotion matrix, blockers, next-lane recommendation, report,
    and status.

Claim boundaries:
    Benchmarks surrogate/emulator models for SOLWEIG-derived delta Tmrt only.
    Does not run QGIS/SOLWEIG, read/write rasters, create AOI/B9 prediction,
    convert to WBGT, produce hazard/risk/exposure/vulnerability output, or make
    causal feature-importance claims. Random split is diagnostic only.
"""

from __future__ import annotations

from v12_b87e_common import main_runner


if __name__ == "__main__":
    raise SystemExit(main_runner())
