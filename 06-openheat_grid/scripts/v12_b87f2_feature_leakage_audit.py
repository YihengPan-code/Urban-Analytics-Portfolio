"""B87F2 feature leakage audit wrapper.

Inputs:
    --config configs/v12/systemb_b87f2_true_vector_feature_patch.yaml

Outputs:
    All B87F2 compact CSV/Markdown artifacts, including
    b87f2_feature_leakage_audit.csv.

Saved metrics:
    Forbidden target/Tmrt/delta/status/path/ID/coordinate checks for each
    feature set plus downstream retest and stop/go decision.
"""

from v12_b87f2_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("feature_leakage_audit"))
