"""Run B87D N300 label integration end to end.

Inputs:
    configs/v12/systemb_b87d_n300_label_integration.yaml, B87C manifest,
    B87C local run log, final F5 N150 pairwise labels, final F5 cell-hour
    summary, final F5 raster QA evidence, and existing local B87C
    Tmrt_average.tif rasters.

Outputs:
    Required B87D CSV/Markdown artifacts under
    outputs/v12_surrogate/b87d_n300_label_integration/ and
    docs/v12/OpenHeat_SystemB_B87D_N300_label_integration_CN.md.

Config path:
    --config configs/v12/systemb_b87d_n300_label_integration.yaml

Saved metrics:
    Input inventory, run-log audit, manifest audit summary, Tmrt inventory,
    extraction convention audit, per-run Tmrt stats, pairwise deltas, schema
    alignment, N300 labels, QA matrix, distribution summary, protocol lineage,
    blockers, and next-lane decision.

Claim boundaries:
    Reads existing local Tmrt rasters for compact statistics only. Does not run
    QGIS/SOLWEIG, write/copy/move rasters, create WBGT, AOI/B9 predictions,
    hazard maps, risk maps, exposure/vulnerability output, observed-truth
    claims, or causal feature-importance claims.
"""

from __future__ import annotations

from v12_b87d_common import main_runner


if __name__ == "__main__":
    raise SystemExit(main_runner())
