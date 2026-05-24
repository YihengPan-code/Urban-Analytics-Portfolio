"""
v12 SOLWEIG Wave 0 smoke run — QGIS Python Console script.

This script reuses the validated v10-epsilon TP_0986 prepared tile rasters/SVF/wall rasters
and writes a new v12 output directory. It is intended to verify QGIS/UMEP/SOLWEIG execution
before preparing or running the v12 Core-8 pilot matrix.

How to run:
  1. Open QGIS with UMEP installed.
  2. Plugins > Python Console.
  3. Show Editor.
  4. Paste or open this script.
  5. Run.

Do not run this with normal python.exe. It requires QGIS processing.
"""

from pathlib import Path
import traceback
import processing

PROJECT_ROOT = r"C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid"
ALGORITHM_ID = "umep:Outdoor Thermal Comfort: SOLWEIG"

V10_TILE = "E02_confident_hot_anchor_2_TP_0986"
TILE_DIR = f"{PROJECT_ROOT}/data/solweig/v10_epsilon_tiles/{V10_TILE}"
FORCING = f"{PROJECT_ROOT}/data/solweig/v09_met_forcing_2026_05_07_S128_h13.txt"
OUTPUT_DIR = f"{PROJECT_ROOT}/outputs/v12_solweig_typology_pilot/wave0_reuse_v10_TP0986_h13_base"
LOG_FILE = f"{PROJECT_ROOT}/outputs/v12_solweig_typology_pilot/wave0_reuse_v10_TP0986_h13_base_log.txt"


def make_params():
    return {
        "INPUT_DSM":         f"{TILE_DIR}/dsm_buildings_tile.tif",
        "INPUT_SVF":         f"{TILE_DIR}/svf_base/svfs.zip",
        "INPUT_HEIGHT":      f"{TILE_DIR}/wall_height.tif",
        "INPUT_ASPECT":      f"{TILE_DIR}/wall_aspect.tif",
        "INPUT_CDSM":        f"{TILE_DIR}/dsm_vegetation_tile_base.tif",
        "INPUT_TDSM":        None,
        "INPUT_DEM":         f"{TILE_DIR}/dsm_dem_flat_tile.tif",
        "INPUT_LC":          None,
        "INPUT_ANISO":       "",
        "INPUT_WALLSCHEME":  "",
        "TRANS_VEG":         3,
        "INPUT_THEIGHT":     25.0,
        "LEAF_START":        1,
        "LEAF_END":          366,
        "CONIFER_TREES":     False,
        "USE_LC_BUILD":      False,
        "SAVE_BUILD":        False,
        "WALLTEMP_NETCDF":   False,
        "WALL_TYPE":         0,
        "ALBEDO_WALLS":      0.20,
        "ALBEDO_GROUND":     0.15,
        "EMIS_WALLS":        0.90,
        "EMIS_GROUND":       0.95,
        "ABS_S":             0.70,
        "ABS_L":             0.95,
        "POSTURE":           0,
        "CYL":               True,
        "INPUTMET":          FORCING,  # IMPORTANT: dict key is INPUTMET, not INPUT_MET
        "ONLYGLOBAL":        False,
        "UTC":               8,
        "WOI_FILE":          None,
        "WOI_FIELD":         "",
        "POI_FILE":          None,
        "POI_FIELD":         "",
        "AGE":               35,
        "ACTIVITY":          80.0,
        "CLO":               0.9,
        "WEIGHT":            75,
        "HEIGHT":            180,
        "SEX":               0,
        "SENSOR_HEIGHT":     10.0,
        "OUTPUT_TMRT":       True,
        "OUTPUT_KDOWN":      False,
        "OUTPUT_KUP":        False,
        "OUTPUT_LDOWN":      False,
        "OUTPUT_LUP":        False,
        "OUTPUT_SH":         False,
        "OUTPUT_TREEPLANTER": False,
        "OUTPUT_DIR":        OUTPUT_DIR,
    }


def main():
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

    params = make_params()
    lines = []
    lines.append("v12 Wave 0 SOLWEIG smoke run\n")
    lines.append(f"algorithm={ALGORITHM_ID}\n")
    lines.append(f"tile={V10_TILE}\n")
    lines.append(f"forcing={FORCING}\n")
    lines.append(f"output_dir={OUTPUT_DIR}\n")

    print("=" * 70)
    print("v12 Wave 0 SOLWEIG smoke run")
    print("=" * 70)
    print("Algorithm:", ALGORITHM_ID)
    print("Input tile:", TILE_DIR)
    print("Forcing:", FORCING)
    print("Output:", OUTPUT_DIR)

    try:
        result = processing.run(ALGORITHM_ID, params)
        print("[OK]", result)
        lines.append("status=OK\n")
        lines.append(f"result={result}\n")
    except Exception as exc:
        print("[FAIL]", exc)
        tb = traceback.format_exc()
        print(tb)
        lines.append("status=FAIL\n")
        lines.append(f"error={exc}\n")
        lines.append(tb)
        raise
    finally:
        Path(LOG_FILE).write_text("".join(lines), encoding="utf-8")
        print("Log saved:", LOG_FILE)


if __name__ == "__console__":
    main()
elif __name__ == "__main__":
    print("This script must be run inside QGIS Python Console.")
