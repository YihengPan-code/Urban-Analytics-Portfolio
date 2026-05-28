"""B87F2 model-card patch wrapper.

Inputs:
    --config configs/v12/systemb_b87f2_true_vector_feature_patch.yaml

Outputs:
    All B87F2 compact CSV/Markdown artifacts, including
    b87f2_model_card_patch_summary.csv.

Saved metrics:
    Candidate feature set/model, scope, promotion decision, no-pickle/no-AOI
    assertions, and claim-boundary summary.
"""

from v12_b87f2_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("model_card_patch"))
