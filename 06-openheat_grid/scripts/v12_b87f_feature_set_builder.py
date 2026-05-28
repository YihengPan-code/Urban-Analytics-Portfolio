"""B87F feature-set builder wrapper.

Inputs:
    B87E exact main feature set, feature quality audit, and correlation clusters.

Outputs:
    b87f_feature_set_registry.csv plus dependent compact B87F artifacts.

Saved metrics:
    Membership for exact B87E, pruned, physical-core, context-plus-physical,
    context-residual, no-coordinate/no-design, and old-to-new robust feature
    sets.
"""

from __future__ import annotations

from v12_b87f_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("feature_set_builder"))
