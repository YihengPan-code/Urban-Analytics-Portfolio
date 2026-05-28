"""B87F2 cell geometry loader wrapper.

Inputs:
    --config configs/v12/systemb_b87f2_true_vector_feature_patch.yaml

Outputs:
    All B87F2 compact CSV/Markdown artifacts, including
    b87f2_cell_geometry_audit.csv.

Saved metrics:
    N300 cell centroid/geometry availability, patched feature coverage,
    surrogate metrics, and stop/go decision.
"""

from v12_b87f2_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("cell_geometry_loader"))
