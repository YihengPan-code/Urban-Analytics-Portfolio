"""B87F input inventory wrapper.

Inputs:
    configs/v12/systemb_b87f_n300_surrogate_promotion_review.yaml and the
    B87D/B87E compact artifacts declared there.

Outputs:
    b87f_input_inventory.csv plus dependent B87F review artifacts under the
    configured output directory.

Saved metrics:
    Required/optional artifact existence, file sizes, and pass/warn/fail input
    status. The shared workflow also writes the compact B87F model diagnostics.
"""

from __future__ import annotations

from v12_b87f_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("input_inventory"))
