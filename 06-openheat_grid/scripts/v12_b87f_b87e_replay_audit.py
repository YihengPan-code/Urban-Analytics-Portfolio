"""B87F B87E replay audit wrapper.

Inputs:
    B87D/B87E status, feature matrix, schema, leakage, metrics, and promotion
    artifacts declared by the B87F config.

Outputs:
    b87f_b87e_replay_audit.csv plus dependent compact B87F artifacts.

Saved metrics:
    Prior B87D/B87E statuses, B87E matrix shape, B87E best GroupKFold model,
    prior extra_trees MAE, best old-to-new model, and no-AOI/B9 gate state.
"""

from __future__ import annotations

from v12_b87f_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("b87e_replay_audit"))
