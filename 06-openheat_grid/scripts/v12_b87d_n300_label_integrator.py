"""B87D N300 label integrator wrapper.

Inputs, outputs, config path, saved metrics, and claim boundaries are declared
in scripts/v12_b87d_common.py. This step integrates F5 existing N150 and B87C
new150 pairwise SOLWEIG-derived labels and does not create AOI/B9 output.
"""

from __future__ import annotations

from v12_b87d_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("n300_label_integrator"))
