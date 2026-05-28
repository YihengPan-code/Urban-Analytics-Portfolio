"""B87F2 input inventory wrapper.

Inputs:
    --config configs/v12/systemb_b87f2_true_vector_feature_patch.yaml

Outputs:
    All B87F2 compact CSV/Markdown artifacts, including
    b87f2_input_inventory.csv.

Saved metrics:
    Required/optional input existence, source readiness, patched feature
    metrics, transfer/rank audits, and stop/go decision via the shared runner.
"""

from v12_b87f2_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("input_inventory"))
