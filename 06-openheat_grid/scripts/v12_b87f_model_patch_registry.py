"""B87F model patch registry wrapper.

Inputs:
    B87F feature-set registry and N150-compatible model configuration.

Outputs:
    b87f_model_patch_registry.csv plus dependent compact B87F artifacts.

Saved metrics:
    Headline registry rows for featureless_mean, context_mean, ridge,
    elasticnet, random_forest, extra_trees, and hist_gradient_boosting only.
"""

from __future__ import annotations

from v12_b87f_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("model_patch_registry"))
