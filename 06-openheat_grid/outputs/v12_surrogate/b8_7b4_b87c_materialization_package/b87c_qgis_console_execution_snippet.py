from pathlib import Path
import os
import sys

runner = Path(r"C:\OpenHeat-local\solweig\b87c_n300\runners\v12_b87b4_qgis_svf_materialization_runner_LOCAL.py")
code = runner.read_text(encoding="utf-8-sig")
globals()["__file__"] = str(runner)
sys.argv = [str(runner)]
os.chdir(str(runner.parent))
exec(compile(code, str(runner), "exec"), globals())
