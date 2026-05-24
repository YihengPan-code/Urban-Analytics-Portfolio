"""
v12 SOLWEIG manifest-driven QGIS Python Console loop — path-safe fixed version.

Why this version exists
-----------------------
The first Wave 1 attempt failed because manifest paths such as
`data/solweig/.../dsm_buildings_tile.tif` were passed to QGIS Processing as
relative paths. QGIS Processing does not reliably resolve those against the
repo root. This version converts all manifest paths to absolute paths using
PROJECT_ROOT before calling UMEP SOLWEIG.

Run inside QGIS Python Console only:

from pathlib import Path
exec(compile(Path('C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid/scripts/v12_solweig_qgis_loop.py').read_text(), 'v12_solweig_qgis_loop.py', 'exec'))
"""

from __future__ import annotations

from pathlib import Path
import csv
import traceback
import processing

PROJECT_ROOT = Path(r"C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid")
ALGORITHM_ID = "umep:Outdoor Thermal Comfort: SOLWEIG"
MANIFEST = PROJECT_ROOT / "configs/v12/v12_solweig_core8_overhead_manifest.csv"
LOG_FILE = PROJECT_ROOT / "outputs/v12_solweig_typology_pilot/v12_solweig_qgis_loop_log.txt"

SCENARIO_MAP = {
    "base": {
        "svf_suffix": "base",
        "cdsm_suffix": "base",
        "output_suffix": "base",
    },
    "overhead_as_canopy": {
        "svf_suffix": "overhead",
        "cdsm_suffix": "overhead",
        "output_suffix": "overhead_as_canopy",
    },
}


def as_abs(path_value: str | Path) -> str:
    """Resolve repo-relative manifest paths to absolute QGIS-safe paths."""
    p = Path(str(path_value))
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p.as_posix()


def path_exists(path_value: str | Path) -> bool:
    return Path(as_abs(path_value)).exists()


def require_file(path_value: str | Path, label: str) -> str:
    p = Path(as_abs(path_value))
    if not p.exists():
        raise FileNotFoundError(f"Missing {label}: {p}")
    return p.as_posix()


def make_params(row: dict[str, str]) -> dict:
    scenario_id = row["scenario_id"]
    if scenario_id not in SCENARIO_MAP:
        raise ValueError(f"Unknown scenario_id: {scenario_id}")

    sc = SCENARIO_MAP[scenario_id]
    tile_dir = Path(as_abs(row["tile_dir"]))
    forcing = require_file(row["forcing_file"], "forcing_file")

    # Resolve every path before passing to QGIS Processing.
    input_dsm = require_file(tile_dir / "dsm_buildings_tile.tif", "INPUT_DSM")
    input_svf = require_file(tile_dir / f"svf_{sc['svf_suffix']}" / "svfs.zip", "INPUT_SVF")
    input_height = require_file(tile_dir / "wall_height.tif", "INPUT_HEIGHT")
    input_aspect = require_file(tile_dir / "wall_aspect.tif", "INPUT_ASPECT")
    input_cdsm = require_file(tile_dir / f"dsm_vegetation_tile_{sc['cdsm_suffix']}.tif", "INPUT_CDSM")
    input_dem = require_file(tile_dir / "dsm_dem_flat_tile.tif", "INPUT_DEM")

    if row.get("output_dir"):
        output_dir = as_abs(row["output_dir"])
    else:
        output_dir = (tile_dir / f"solweig_{sc['output_suffix']}" / f"solweig_outputs_h{int(row['hour_sgt']):02d}").as_posix()
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    return {
        "INPUT_DSM":         input_dsm,
        "INPUT_SVF":         input_svf,
        "INPUT_HEIGHT":      input_height,
        "INPUT_ASPECT":      input_aspect,
        "INPUT_CDSM":        input_cdsm,
        "INPUT_TDSM":        None,
        "INPUT_DEM":         input_dem,
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
        "INPUTMET":          forcing,  # IMPORTANT: key is INPUTMET, not INPUT_MET.
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
        "OUTPUT_DIR":        output_dir,
    }


def preflight(rows: list[dict[str, str]]) -> None:
    """Fail before running SOLWEIG if any expected input is missing."""
    print("\nPreflight input check...")
    errors = []
    for row in rows:
        scenario_id = row["scenario_id"]
        sc = SCENARIO_MAP.get(scenario_id)
        if sc is None:
            errors.append(f"{row.get('run_id')}: unknown scenario_id={scenario_id}")
            continue

        tile_dir = Path(as_abs(row["tile_dir"]))
        expected = [
            ("tile_dir", tile_dir),
            ("INPUT_DSM", tile_dir / "dsm_buildings_tile.tif"),
            ("INPUT_SVF", tile_dir / f"svf_{sc['svf_suffix']}" / "svfs.zip"),
            ("INPUT_HEIGHT", tile_dir / "wall_height.tif"),
            ("INPUT_ASPECT", tile_dir / "wall_aspect.tif"),
            ("INPUT_CDSM", tile_dir / f"dsm_vegetation_tile_{sc['cdsm_suffix']}.tif"),
            ("INPUT_DEM", tile_dir / "dsm_dem_flat_tile.tif"),
            ("forcing_file", Path(as_abs(row["forcing_file"]))),
        ]
        for label, path in expected:
            if not Path(path).exists():
                errors.append(f"{row.get('run_id')}: missing {label}: {path}")

    if errors:
        print("[PREFLIGHT FAIL]")
        for e in errors:
            print("  -", e)
        raise RuntimeError(f"Preflight failed with {len(errors)} missing inputs.")
    print("[PREFLIGHT OK] all inputs exist.")


def main() -> None:
    if not MANIFEST.exists():
        raise FileNotFoundError(f"Missing manifest: {MANIFEST}")

    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8-sig")))
    if not rows:
        raise ValueError(f"Manifest has no rows: {MANIFEST}")

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("v12 SOLWEIG QGIS loop — path-safe version")
    print("Manifest:", MANIFEST)
    print("Runs:", len(rows))
    print("Algorithm:", ALGORITHM_ID)
    print("=" * 70)

    preflight(rows)

    ok = 0
    fail = 0
    lines = [
        "v12 SOLWEIG QGIS loop log\n",
        f"manifest={MANIFEST.as_posix()}\n",
        f"algorithm={ALGORITHM_ID}\n",
        "path_mode=absolute_resolved\n\n",
    ]

    for idx, row in enumerate(rows, start=1):
        tag = f"[{idx:03d}/{len(rows):03d}] {row.get('run_id')} {row.get('cell_id')} h{row.get('hour_sgt')} {row.get('scenario_id')}"
        print("\n" + tag)
        try:
            params = make_params(row)
            result = processing.run(ALGORITHM_ID, params)
            tmrt = Path(params["OUTPUT_DIR"]) / "Tmrt_average.tif"
            if not tmrt.exists():
                raise RuntimeError(f"SOLWEIG completed but Tmrt_average.tif not found: {tmrt}")
            print("  [OK]", params["OUTPUT_DIR"])
            lines.append(f"OK   {tag} :: {params['OUTPUT_DIR']}\n")
            ok += 1
        except Exception as exc:
            print("  [FAIL]", exc)
            tb = traceback.format_exc()
            print(tb)
            lines.append(f"FAIL {tag} :: {exc}\n{tb}\n")
            fail += 1

    lines.insert(3, f"ok={ok}/{len(rows)} fail={fail}/{len(rows)}\n")
    LOG_FILE.write_text("".join(lines), encoding="utf-8")

    print("=" * 70)
    print(f"DONE ok={ok}/{len(rows)} fail={fail}/{len(rows)}")
    print("Log saved:", LOG_FILE.as_posix())
    print("=" * 70)

    if fail:
        raise RuntimeError(f"{fail} SOLWEIG runs failed. See log: {LOG_FILE}")


if __name__ == "__console__":
    main()
elif __name__ == "__main__":
    print("This script must be run inside QGIS Python Console.")
