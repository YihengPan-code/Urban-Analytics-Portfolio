"""Compatibility wrapper for OpenHeat v1.0-beta morphology shift audit.

Some v10-beta batch files call `v10_beta_morphology_shift_audit.py`, while the
actual implementation introduced by the patch is named
`v10_beta_build_morphology_shift_audit.py`. This wrapper forwards all command-line
arguments to the implementation script so either filename works.
"""
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
impl = HERE / "v10_beta_build_morphology_shift_audit.py"

if not impl.exists():
    raise FileNotFoundError(
        f"Expected implementation script not found: {impl}\n"
        "Please make sure `scripts/v10_beta_build_morphology_shift_audit.py` "
        "exists, or re-extract the v10-beta patch."
    )

# Preserve argv exactly as if the implementation script had been called.
sys.argv[0] = str(impl)
runpy.run_path(str(impl), run_name="__main__")
