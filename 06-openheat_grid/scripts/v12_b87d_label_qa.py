"""B87D N300 label QA wrapper.

Inputs, outputs, config path, saved metrics, and claim boundaries are declared
in scripts/v12_b87d_common.py. This step writes QA, blocker, distribution,
status, report, and next-lane artifacts.
"""

from __future__ import annotations

from v12_b87d_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("label_qa"))
