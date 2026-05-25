"""
v12 QGIS preprocessing runner for Wall Height/Aspect + Sky View Factor.

Run inside QGIS Python Console only.

Default manifest:
  configs/v12/v12_solweig_preprocess_wave1_base_manifest.csv

Expected manifest columns:
  preprocess_id, tile_id, cell_id, typology_label, scenario_id, tile_dir,
  input_dsm, input_cdsm, wall_height, wall_aspect,
  svf_output_dir, svf_output_file, svf_zip_expected,
  run_wall_height_aspect, run_svf

What this does:
  1. Runs UMEP Wall Height and Aspect once per tile if wall rasters are missing.
  2. Runs UMEP Sky View Factor once per manifest row/scenario if svfs.zip is missing.
  3. Writes a CSV + text log under outputs/v12_solweig_typology_pilot/qgis_preprocess_formal_hotday_smoke/.

What this does NOT do:
  - Does not run SOLWEIG.
  - Does not create Tmrt rasters.
  - Does not train surrogate/ML.
  - Does not create hazard/risk maps.

Algorithm IDs and parameters verified from local QGIS/UMEP discovery and Processing History:
  Wall H/A:
    "umep:Urban Geometry: Wall Height and Aspect"
    INPUT, INPUT_LIMIT, OUTPUT_HEIGHT, OUTPUT_ASPECT

  SVF:
    "umep:Urban Geometry: Sky View Factor"
    INPUT_DSM, INPUT_CDSM, TRANS_VEG, INPUT_TDSM, INPUT_THEIGHT, ANISO,
    WALL_SCHEME, KMEANS, CLUSTERS, INPUT_DEM, INPUT_SVFHEIGHT,
    OUTPUT_DIR, OUTPUT_FILE
"""

from __future__ import annotations

from pathlib import Path
import csv
import traceback
import processing


PROJECT_ROOT = r"C:/Users/CloudStar/Documents/GitHub/Urban-Analytics-Portfolio/06-openheat_grid"
MANIFEST = f"{PROJECT_ROOT}/configs/v12/v12_solweig_preprocess_formal_hotday_smoke_manifest.csv"
OUT_DIR = Path(PROJECT_ROOT) / "outputs/v12_solweig_typology_pilot/qgis_preprocess_formal_hotday_smoke"
LOG_TXT = OUT_DIR / "v12_qgis_preprocess_formal_hotday_smoke_log.txt"
LOG_CSV = OUT_DIR / "v12_qgis_preprocess_formal_hotday_smoke_log.csv"

WALL_ALGORITHM_ID = "umep:Urban Geometry: Wall Height and Aspect"
SVF_ALGORITHM_ID = "umep:Urban Geometry: Sky View Factor"

# Keep v10-epsilon / UMEP settings.
WALL_INPUT_LIMIT_M = 3.0
TRANS_VEG = 3
INPUT_THEIGHT = 25.0
ANISO = True
WALL_SCHEME = False
KMEANS = True
CLUSTERS = 5
INPUT_SVFHEIGHT = 1.0

# Safety: avoid rerunning heavy preprocessing unless outputs are missing.
OVERWRITE_WALL = False
OVERWRITE_SVF = False


def as_abs(path_str: str) -> str:
    p = Path(path_str)
    if not p.is_absolute():
        p = Path(PROJECT_ROOT) / p
    return p.as_posix()


def exists(path_str: str) -> bool:
    return Path(as_abs(path_str)).exists()


def require_input(path_str: str, label: str) -> None:
    p = Path(as_abs(path_str))
    if not p.exists():
        raise FileNotFoundError(f"Missing {label}: {p}")


def wall_outputs_exist(row: dict[str, str]) -> bool:
    return exists(row["wall_height"]) and exists(row["wall_aspect"])


def svf_outputs_exist(row: dict[str, str]) -> bool:
    return exists(row["svf_zip_expected"])


def make_wall_params(row: dict[str, str]) -> dict:
    return {
        "INPUT": as_abs(row["input_dsm"]),
        "INPUT_LIMIT": WALL_INPUT_LIMIT_M,
        "OUTPUT_HEIGHT": as_abs(row["wall_height"]),
        "OUTPUT_ASPECT": as_abs(row["wall_aspect"]),
    }


def make_svf_params(row: dict[str, str]) -> dict:
    svf_dir = Path(as_abs(row["svf_output_dir"]))
    svf_dir.mkdir(parents=True, exist_ok=True)

    return {
        "INPUT_DSM": as_abs(row["input_dsm"]),
        "INPUT_CDSM": as_abs(row["input_cdsm"]),
        "TRANS_VEG": TRANS_VEG,
        "INPUT_TDSM": None,
        "INPUT_THEIGHT": INPUT_THEIGHT,
        "ANISO": ANISO,
        "WALL_SCHEME": WALL_SCHEME,
        "KMEANS": KMEANS,
        "CLUSTERS": CLUSTERS,
        "INPUT_DEM": None,
        "INPUT_SVFHEIGHT": INPUT_SVFHEIGHT,
        "OUTPUT_DIR": str(svf_dir),
        "OUTPUT_FILE": as_abs(row["svf_output_file"]),
    }


def run_wall(row: dict[str, str]) -> tuple[str, str]:
    require_input(row["input_dsm"], "input_dsm")

    if wall_outputs_exist(row) and not OVERWRITE_WALL:
        return "skipped_existing", "wall_height/wall_aspect already exist"

    print("  [WALL] running", WALL_ALGORITHM_ID)
    params = make_wall_params(row)
    processing.run(WALL_ALGORITHM_ID, params)

    if not wall_outputs_exist(row):
        raise RuntimeError(
            f"Wall H/A algorithm completed but expected outputs not found: "
            f"{as_abs(row['wall_height'])}, {as_abs(row['wall_aspect'])}"
        )

    return "ok", "wall_height/wall_aspect generated"


def run_svf(row: dict[str, str]) -> tuple[str, str]:
    require_input(row["input_dsm"], "input_dsm")
    require_input(row["input_cdsm"], "input_cdsm")

    if svf_outputs_exist(row) and not OVERWRITE_SVF:
        return "skipped_existing", "svfs.zip already exists"

    print("  [SVF] running", SVF_ALGORITHM_ID)
    params = make_svf_params(row)
    result = processing.run(SVF_ALGORITHM_ID, params)

    if not svf_outputs_exist(row):
        # The SVF tool should create svfs.zip in OUTPUT_DIR. If it does not,
        # fail explicitly instead of allowing SOLWEIG to later fail obscurely.
        raise RuntimeError(
            f"SVF algorithm completed but svfs.zip not found at {as_abs(row['svf_zip_expected'])}. "
            f"Processing result was: {result}"
        )

    return "ok", "svfs.zip generated"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest_path = Path(MANIFEST)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")

    rows = list(csv.DictReader(open(manifest_path, encoding="utf-8-sig")))
    if not rows:
        raise ValueError(f"Manifest has no rows: {manifest_path}")

    print("=" * 72)
    print("v12 QGIS preprocessing runner")
    print("=" * 72)
    print("Manifest:", manifest_path)
    print("Rows:", len(rows))
    print("Wall algorithm:", WALL_ALGORITHM_ID)
    print("SVF algorithm:", SVF_ALGORITHM_ID)
    print("Output log:", LOG_TXT)
    print("=" * 72)

    log_rows: list[dict[str, str]] = []
    text_lines = [
        "v12 QGIS preprocessing log\n",
        f"manifest={manifest_path}\n",
        f"wall_algorithm={WALL_ALGORITHM_ID}\n",
        f"svf_algorithm={SVF_ALGORITHM_ID}\n",
        f"rows={len(rows)}\n\n",
    ]

    ok = 0
    fail = 0

    for idx, row in enumerate(rows, start=1):
        tag = f"[{idx:03d}/{len(rows):03d}] {row.get('preprocess_id')} {row.get('cell_id')} {row.get('scenario_id')}"
        print("\n" + tag)
        row_log = {
            "preprocess_id": row.get("preprocess_id", ""),
            "cell_id": row.get("cell_id", ""),
            "scenario_id": row.get("scenario_id", ""),
            "tile_dir": row.get("tile_dir", ""),
            "wall_status": "",
            "svf_status": "",
            "status": "",
            "message": "",
        }

        try:
            # Wall H/A is shared by scenarios. If the manifest has both base
            # and overhead rows for a tile, the second one will skip.
            if row.get("run_wall_height_aspect", "yes").lower() == "yes":
                wall_status, wall_msg = run_wall(row)
            else:
                wall_status, wall_msg = "disabled", "run_wall_height_aspect != yes"

            # SVF is scenario-specific because CDSM differs between base/overhead.
            if row.get("run_svf", "yes").lower() == "yes":
                svf_status, svf_msg = run_svf(row)
            else:
                svf_status, svf_msg = "disabled", "run_svf != yes"

            row_log["wall_status"] = wall_status
            row_log["svf_status"] = svf_status
            row_log["status"] = "ok"
            row_log["message"] = f"{wall_msg}; {svf_msg}"
            ok += 1
            print("  [OK]", row_log["message"])
            text_lines.append(f"OK   {tag} :: {row_log['message']}\n")

        except Exception as exc:
            tb = traceback.format_exc()
            row_log["status"] = "fail"
            row_log["message"] = str(exc)
            fail += 1
            print("  [FAIL]", exc)
            print(tb)
            text_lines.append(f"FAIL {tag} :: {exc}\n{tb}\n")

        log_rows.append(row_log)

    text_lines.insert(5, f"ok={ok}/{len(rows)} fail={fail}/{len(rows)}\n\n")
    LOG_TXT.write_text("".join(text_lines), encoding="utf-8")

    with LOG_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(log_rows[0].keys()))
        writer.writeheader()
        writer.writerows(log_rows)

    print("\n" + "=" * 72)
    print(f"DONE ok={ok}/{len(rows)} fail={fail}/{len(rows)}")
    print("Text log:", LOG_TXT)
    print("CSV log:", LOG_CSV)
    print("=" * 72)

    if fail:
        raise RuntimeError(f"{fail} preprocessing rows failed. See log.")


if __name__ == "__console__":
    main()
elif __name__ == "__main__":
    print("This script must be run inside QGIS Python Console.")

