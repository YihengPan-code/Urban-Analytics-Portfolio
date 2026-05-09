"""
Create a project-level .gitignore for 06-openheat_grid/.

Run from inside 06-openheat_grid/:
    python make_gitignore.py

This avoids Windows cmd's flaky multi-line echo handling.
"""
from pathlib import Path

GITIGNORE_CONTENT = """\
# ============================================
# 06-openheat_grid project-level .gitignore
# (supplements the portfolio-level .gitignore)
# ============================================

# ===== Python =====
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
.pytest_cache/
.venv/
venv/
env/
.ipynb_checkpoints/

# ===== Editor / OS =====
.vscode/
.idea/
.DS_Store
Thumbs.db
*.lnk
desktop.ini

# ===== Large archives - never commit =====
*.zip
*.tar.gz
*.tar.bz2
*.7z
*.rar

# ===== QGIS workspace temp =====
*.qgz~
*.qgs~

# ===== Raw source data (re-downloadable, see DATA_SOURCES.md) =====
data/raw/ura_masterplan2019_*.geojson
data/raw/hdb3d/
data/raw/canopy/

# ===== Large UMEP intermediate files (regenerable) =====
data/rasters/v08/umep_svf/
data/rasters/v08/umep_svf_with_veg/
data/solweig/v09_tiles_overhead_aware/*/svf_outputs/svfs.zip
data/solweig/v09_tiles_overhead_aware/*/svf_outputs/shadowmats.npz
data/solweig/v09_tiles_overhead_aware/*/solweig_outputs_h*/svfs.zip
data/solweig/v09_tiles_overhead_aware/*/solweig_outputs_h*/shadowmats.npz

# ===== Large hourly forecast CSVs (regenerable) =====
outputs/v07_forecast_live/
outputs/v07_beta_forecast_live/
outputs/v07_beta_final_forecast_live/
outputs/v07_beta_impervfix_forecast_live/
outputs/v08_umep_with_veg_forecast_live/
outputs/v071_risk_exposure/v071_hourly_grid_heatstress_forecast_with_risk.csv

# ===== Logs and temp =====
*.log
*.tmp
*.bak
*.swp
*~

# ===== Cache =====
.cache/
node_modules/
"""


def main() -> None:
    target = Path(".gitignore")
    target.write_text(GITIGNORE_CONTENT, encoding="utf-8", newline="\n")
    print(f"[OK] wrote {target.absolute()}")
    print(f"     {len(GITIGNORE_CONTENT.splitlines())} lines, "
          f"{len(GITIGNORE_CONTENT.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
