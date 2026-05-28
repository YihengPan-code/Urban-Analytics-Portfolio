"""B87D F5 schema alignment wrapper.

Inputs, outputs, config path, saved metrics, and claim boundaries are declared
in scripts/v12_b87d_common.py. This step aligns final F5 N150 labels to the
B87D N300 schema without retroactive recalibration.
"""

from __future__ import annotations

from v12_b87d_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("f5_schema_alignment"))
