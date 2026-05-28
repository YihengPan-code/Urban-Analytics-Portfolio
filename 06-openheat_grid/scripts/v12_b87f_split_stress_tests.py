"""B87F split stress-test registry wrapper.

Inputs:
    B87E feature matrix with cell_id, sample_group, forcing_day_id, hour_sgt,
    and optional typology/spatial/role columns.

Outputs:
    b87f_split_stress_test_registry.csv plus dependent compact B87F artifacts.

Saved metrics:
    GroupKFold, old-to-new, new-to-old, forcing-day, hour, spatial-bin,
    typology, primary-role, and diagnostic random split train/test counts and
    cell overlap checks.
"""

from __future__ import annotations

from v12_b87f_common import wrapper_cli


if __name__ == "__main__":
    raise SystemExit(wrapper_cli("split_stress_tests"))
