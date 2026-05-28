"""B87E feature leakage audit wrapper.

Inputs, outputs, config path, saved metrics, and claim boundaries are declared
in scripts/v12_b87e_common.py. This step checks that target, Tmrt, cell ID,
source/protocol, status/path, and diagnostic-only metadata are not used as main
predictors.
"""

from __future__ import annotations

from v12_b87e_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("feature_leakage_audit"))
