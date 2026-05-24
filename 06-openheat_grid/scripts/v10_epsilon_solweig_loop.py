"""
v10-epsilon SOLWEIG batch loop — runs entirely in QGIS Python Console.

Bypasses the QGIS 3.44.3 batch dialog "QVariant not JSON serializable" bug
by calling processing.run() directly in a loop.

How to use:
    1. Open QGIS.
    2. Plugins > Python Console (Ctrl+Alt+P).
    3. Click the "Show Editor" icon, paste this whole file.
    4. Click "Run Script" (green triangle).
    5. Watch the Console output — it prints progress for each of the 50 runs.

The 50 runs = 5 tiles × 2 scenarios × 5 forcing-hours.
Each run takes ~2-5 minutes; total ~1.5-3 hours.

Per-run output: data/solweig/v10_epsilon_tiles/<E0X_*>/solweig_<scenario>/Tmrt_*.tif

If a run fails, it prints the traceback and continues with the next one.
At the end, a summary of OK/FAIL counts is printed.
"""

import os
import traceback
from pathlib import Path
import processing


# ============================================================
# Configuration — edit if your project root differs
# ============================================================
PROJECT_ROOT = r"C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid"

TILES = [
    "E01_confident_hot_anchor_1_TP_0565",
    "E02_confident_hot_anchor_2_TP_0986",
    "E03_overhead_confounded_rank1_case_TP_0088",
    "E04_saturated_overhead_case_TP_0916",
    "E05_clean_shaded_reference_TP_0433",
]
SCENARIOS = ["base", "overhead"]
HOURS = [10, 12, 13, 15, 16]

ALGORITHM_ID = "umep:Outdoor Thermal Comfort: SOLWEIG"  # if this fails, see "Algorithm ID lookup" below

LOG_FILE = f"{PROJECT_ROOT}/outputs/v10_epsilon_solweig/v10_epsilon_solweig_loop_log.txt"


# ============================================================
# Algorithm parameters per (tile, scenario, hour)
# Keys are exactly as defined in solweig_algorithm.py v2025a.
# Note: INPUT_MET constant maps to dict-key 'INPUTMET' (no underscore).
# ============================================================
def make_params(tile: str, scenario: str, hour: int) -> dict:
    tdir = f"{PROJECT_ROOT}/data/solweig/v10_epsilon_tiles/{tile}"
    forcing = f"{PROJECT_ROOT}/data/solweig/v09_met_forcing_2026_05_07_S128_h{hour:02d}.txt"

    return {
        # ---- Required input rasters / files ----
        "INPUT_DSM":         f"{tdir}/dsm_buildings_tile.tif",
        "INPUT_SVF":         f"{tdir}/svf_{scenario}/svfs.zip",
        "INPUT_HEIGHT":      f"{tdir}/wall_height.tif",
        "INPUT_ASPECT":      f"{tdir}/wall_aspect.tif",
        "INPUT_CDSM":        f"{tdir}/dsm_vegetation_tile_{scenario}.tif",  # vegetation canopy
        "INPUT_TDSM":        None,                                           # trunk DSM (we don't have)
        "INPUT_DEM":         f"{tdir}/dsm_dem_flat_tile.tif",                # flat DEM = all zeros
        "INPUT_LC":          None,                                           # land cover (we don't have)
        "INPUT_ANISO":       "",                                            # anisotropic shadow npz (empty per v0.9 history)
        "INPUT_WALLSCHEME":  "",                                            # wall temp npz (empty per v0.9 history)
        # ---- Vegetation parameters ----
        "TRANS_VEG":         3,           # Transmissivity %
        "INPUT_THEIGHT":     25.0,        # Trunk zone height % of canopy
        "LEAF_START":        1,            # Tropical evergreen: leaves all year (matches v0.9-gamma)
        "LEAF_END":          366,
        "CONIFER_TREES":     False,
        # ---- Land cover ----
        "USE_LC_BUILD":      False,
        "SAVE_BUILD":        False,
        # ---- Wall scheme & netcdf ----
        "WALLTEMP_NETCDF":   False,
        "WALL_TYPE":         0,           # Brick (irrelevant since wall scheme off)
        # ---- Albedo & emissivity ----
        "ALBEDO_WALLS":      0.20,
        "ALBEDO_GROUND":     0.15,
        "EMIS_WALLS":        0.90,
        "EMIS_GROUND":       0.95,
        # ---- Tmrt / pedestrian ----
        "ABS_S":             0.70,        # Shortwave absorption of human
        "ABS_L":             0.95,        # Longwave absorption of human
        "POSTURE":           0,           # 0 = Standing, 1 = Sitting
        "CYL":               True,        # Cylinder model (recommended)
        # ---- Meteorology ----
        "INPUTMET":          forcing,     # NB: dict-key is 'INPUTMET', not 'INPUT_MET'
        "ONLYGLOBAL":        False,       # We have direct + diffuse from forcing
        "UTC":               8,           # Singapore = UTC+8
        # ---- Advanced (POI, WOI, PET) — defaults / empty ----
        "WOI_FILE":          None,
        "WOI_FIELD":         "",
        "POI_FILE":          None,
        "POI_FIELD":         "",
        "AGE":               35,
        "ACTIVITY":          80.0,
        "CLO":               0.9,
        "WEIGHT":            75,
        "HEIGHT":            180,
        "SEX":               0,           # 0 = Male, 1 = Female
        "SENSOR_HEIGHT":     10.0,
        # ---- Output toggles ----
        "OUTPUT_TMRT":       True,        # Always save Tmrt
        "OUTPUT_KDOWN":      False,
        "OUTPUT_KUP":        False,
        "OUTPUT_LDOWN":      False,
        "OUTPUT_LUP":        False,
        "OUTPUT_SH":         False,
        "OUTPUT_TREEPLANTER": False,
        # ---- Output folder ----
        # Nested layout: solweig_<scenario>/solweig_outputs_h<HH>/
        # Per-hour subfolder isolates non-Tmrt SOLWEIG outputs across runs.
        "OUTPUT_DIR":        f"{tdir}/solweig_{scenario}/solweig_outputs_h{hour:02d}",
    }


# ============================================================
# Main loop
# ============================================================
def main():
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    log_lines = []

    total = len(TILES) * len(SCENARIOS) * len(HOURS)
    ok_count = 0
    fail_count = 0
    fail_details = []

    print(f"\n{'='*70}")
    print(f"v10-epsilon SOLWEIG batch loop — {total} runs")
    print(f"{'='*70}")
    print(f"Algorithm: {ALGORITHM_ID}")
    print(f"Log file: {LOG_FILE}")
    print(f"{'='*70}\n")

    counter = 0
    for tile in TILES:
        for scenario in SCENARIOS:
            for hour in HOURS:
                counter += 1
                tag = f"[{counter:02d}/{total}] {tile[:20]} / {scenario} / {hour:02d}:00"
                print(f"\n{tag}")

                params = make_params(tile, scenario, hour)
                try:
                    result = processing.run(ALGORITHM_ID, params)
                    print(f"  [OK] output: {params['OUTPUT_DIR']}")
                    log_lines.append(f"OK   {tag}")
                    ok_count += 1
                except Exception as e:
                    err_str = str(e)
                    tb_str = traceback.format_exc()
                    print(f"  [FAIL] {err_str}")
                    log_lines.append(f"FAIL {tag} :: {err_str}")
                    fail_details.append((tag, err_str, tb_str))
                    fail_count += 1

    # Final summary
    print(f"\n{'='*70}")
    print(f"DONE  ok={ok_count}/{total}  fail={fail_count}/{total}")
    print(f"{'='*70}")

    if fail_details:
        print("\nFailures:")
        for tag, err, _ in fail_details:
            print(f"  {tag}")
            print(f"    {err[:200]}")

    # Write log
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"v10-epsilon SOLWEIG batch loop log\n")
        f.write(f"ok={ok_count}/{total}  fail={fail_count}/{total}\n\n")
        for line in log_lines:
            f.write(line + "\n")
        if fail_details:
            f.write("\n\nFull tracebacks:\n")
            for tag, _, tb in fail_details:
                f.write(f"\n{'='*70}\n{tag}\n{'='*70}\n{tb}\n")

    print(f"\nLog saved: {LOG_FILE}")


# ============================================================
# Algorithm ID lookup (run only if main() fails on first call with
# "Algorithm not found" or similar)
# ============================================================
def lookup_algorithm_id():
    from qgis.core import QgsApplication
    reg = QgsApplication.processingRegistry()
    print("\nSearching for SOLWEIG algorithm in registry...")
    candidates = []
    for a in reg.algorithms():
        if "solweig" in a.id().lower() or "solweig" in a.displayName().lower():
            candidates.append(a)
            print(f"  Found: id='{a.id()}'  display='{a.displayName()}'")
    if not candidates:
        print("  No SOLWEIG algorithm found. UMEP plugin loaded?")
        print("  Listing all UMEP algorithms:")
        for a in reg.algorithms():
            if "umep" in a.id().lower():
                print(f"    {a.id()}")
    return candidates


# ============================================================
# Entry point
# ============================================================
if __name__ == "__console__":
    # Running from QGIS Python Console
    main()
elif __name__ == "__main__":
    # Direct python execution (won't work — requires QGIS environment)
    print("This script must be run from inside QGIS Python Console.")
    print("Open QGIS → Plugins → Python Console → Show Editor → paste this file → Run.")
