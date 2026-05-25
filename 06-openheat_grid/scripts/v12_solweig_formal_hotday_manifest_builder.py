"""Build v1.2-beta formal-hot-day SOLWEIG manifests from a planned QA matrix.

This helper does not run QGIS or SOLWEIG. It converts a small planned
formal-hot-day QA matrix into:

1. a SOLWEIG run manifest consumable by scripts/v12_solweig_qgis_loop.py;
2. a QGIS preprocessing manifest consumable by scripts/qgis/v12_qgis_preprocess_from_manifest.py.

The script intentionally reuses existing v12 Core-8 tile directories and scenario
semantics. It is meant for the post-Core-8, pre-scale-design QA gate.

Example:
    python scripts/v12_solweig_formal_hotday_manifest_builder.py ^
      --plan configs/v12/v12_solweig_formal_hotday_smoke_plan.csv ^
      --base-manifest configs/v12/v12_solweig_core8_base_manifest.csv ^
      --overhead-manifest configs/v12/v12_solweig_core8_overhead_manifest.csv ^
      --out-solweig-manifest configs/v12/v12_solweig_formal_hotday_smoke_manifest.csv ^
      --out-preprocess-manifest configs/v12/v12_solweig_preprocess_formal_hotday_smoke_manifest.csv ^
      --allow-missing-forcing
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALID_SCENARIOS = {"base", "overhead_as_canopy"}


@dataclass(frozen=True)
class ManifestPaths:
    plan: Path
    base_manifest: Path
    overhead_manifest: Path
    out_solweig_manifest: Path
    out_preprocess_manifest: Path


def _project_path(path_text: str | Path) -> Path:
    """Resolve a path relative to the repository root unless already absolute."""
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required CSV: {path}")
    return pd.read_csv(path, encoding="utf-8-sig")


def _normalise_cell_id(cell_id: str) -> str:
    cell = str(cell_id).strip()
    if not cell:
        raise ValueError("Empty cell_id in plan")
    return cell if cell.startswith("TP_") else cell.replace("TP", "TP_")


def _format_hour(hour: int | str) -> str:
    hour_int = int(hour)
    if not 0 <= hour_int <= 23:
        raise ValueError(f"Invalid hour_sgt: {hour!r}")
    return f"h{hour_int:02d}"


def _load_core8_lookup(base_manifest: Path, overhead_manifest: Path) -> dict[tuple[str, str], dict[str, str]]:
    """Return lookup keyed by (cell_id, scenario_id)."""
    frames = []
    for path in (base_manifest, overhead_manifest):
        df = _read_csv(path)
        required = {"cell_id", "scenario_id", "tile_dir", "typology_label"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"{path} missing columns: {sorted(missing)}")
        frames.append(df[list(required)].drop_duplicates())
    lookup_df = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["cell_id", "scenario_id"])
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in lookup_df.to_dict(orient="records"):
        cell = _normalise_cell_id(row["cell_id"])
        scenario = str(row["scenario_id"]).strip()
        out[(cell, scenario)] = {
            "cell_id": cell,
            "scenario_id": scenario,
            "tile_dir": str(row["tile_dir"]).strip(),
            "typology_label": str(row["typology_label"]).strip(),
        }
    return out


def _validate_plan_columns(plan: pd.DataFrame) -> None:
    required = {
        "qa_run_id",
        "cell_id",
        "hour_sgt",
        "scenario_id",
        "forcing_file",
        "qa_role",
        "expected_direction",
        "notes",
    }
    missing = required - set(plan.columns)
    if missing:
        raise ValueError(f"Plan CSV missing columns: {sorted(missing)}")


def build_manifests(paths: ManifestPaths, allow_missing_forcing: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    plan = _read_csv(paths.plan)
    _validate_plan_columns(plan)
    lookup = _load_core8_lookup(paths.base_manifest, paths.overhead_manifest)

    solweig_rows: list[dict[str, str | int]] = []
    preprocess_rows_by_key: dict[tuple[str, str], dict[str, str]] = {}
    errors: list[str] = []

    for i, raw in enumerate(plan.to_dict(orient="records"), start=1):
        cell_id = _normalise_cell_id(raw["cell_id"])
        scenario = str(raw["scenario_id"]).strip()
        if scenario not in VALID_SCENARIOS:
            errors.append(f"row {i}: invalid scenario_id {scenario!r}")
            continue
        hour = int(raw["hour_sgt"])
        hour_label = _format_hour(hour)
        forcing_file = str(raw["forcing_file"]).strip()
        if not forcing_file:
            errors.append(f"row {i}: empty forcing_file")
            continue
        if not allow_missing_forcing and not _project_path(forcing_file).exists():
            errors.append(f"row {i}: forcing_file does not exist: {forcing_file}")
            continue

        key = (cell_id, scenario)
        if key not in lookup:
            errors.append(f"row {i}: no Core-8 tile lookup for {key}")
            continue
        tile = lookup[key]
        typology_label = tile["typology_label"]
        output_stage = "formal_hotday_smoke"
        scenario_folder = "base" if scenario == "base" else "overhead"
        output_dir = f"outputs/v12_solweig_typology_pilot/{output_stage}/{scenario_folder}/{cell_id}/{hour_label}"
        run_id = str(raw["qa_run_id"]).strip() or f"v12_formal_hotday_{cell_id}_{scenario}_{hour_label}"

        solweig_rows.append(
            {
                "run_id": run_id,
                "cell_id": cell_id,
                "typology_label": typology_label,
                "hour_sgt": hour,
                "scenario_id": scenario,
                "tile_dir": tile["tile_dir"],
                "forcing_file": forcing_file,
                "output_dir": output_dir,
                "qa_role": str(raw["qa_role"]).strip(),
                "expected_direction": str(raw["expected_direction"]).strip(),
                "notes": str(raw["notes"]).strip(),
            }
        )

        if key not in preprocess_rows_by_key:
            tile_dir = tile["tile_dir"]
            svf_suffix = "base" if scenario == "base" else "overhead"
            cdsm_suffix = "base" if scenario == "base" else "overhead"
            preprocess_rows_by_key[key] = {
                "preprocess_id": f"prep_formal_hotday_{cell_id}_{scenario}",
                "tile_id": Path(tile_dir).name,
                "cell_id": cell_id,
                "typology_label": typology_label,
                "scenario_id": scenario,
                "tile_dir": tile_dir,
                "input_dsm": f"{tile_dir}/dsm_buildings_tile.tif",
                "input_cdsm": f"{tile_dir}/dsm_vegetation_tile_{cdsm_suffix}.tif",
                "wall_height": f"{tile_dir}/wall_height.tif",
                "wall_aspect": f"{tile_dir}/wall_aspect.tif",
                "svf_output_dir": f"{tile_dir}/svf_{svf_suffix}",
                "svf_output_file": f"{tile_dir}/svf_{svf_suffix}/svf.tif",
                "svf_zip_expected": f"{tile_dir}/svf_{svf_suffix}/svfs.zip",
                "run_wall_height_aspect": "yes",
                "run_svf": "yes",
                "status": "planned",
                "notes": "formal-hot-day smoke QA; reuse existing v12 Core-8 tile geometry",
            }

    if errors:
        joined = "\n".join(f"- {e}" for e in errors)
        raise ValueError(f"Manifest build failed with {len(errors)} error(s):\n{joined}")

    solweig_df = pd.DataFrame(solweig_rows)
    preprocess_df = pd.DataFrame(preprocess_rows_by_key.values())

    paths.out_solweig_manifest.parent.mkdir(parents=True, exist_ok=True)
    paths.out_preprocess_manifest.parent.mkdir(parents=True, exist_ok=True)
    solweig_df.to_csv(paths.out_solweig_manifest, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    preprocess_df.to_csv(paths.out_preprocess_manifest, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    return solweig_df, preprocess_df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", default="configs/v12/v12_solweig_formal_hotday_smoke_plan.csv")
    parser.add_argument("--base-manifest", default="configs/v12/v12_solweig_core8_base_manifest.csv")
    parser.add_argument("--overhead-manifest", default="configs/v12/v12_solweig_core8_overhead_manifest.csv")
    parser.add_argument("--out-solweig-manifest", default="configs/v12/v12_solweig_formal_hotday_smoke_manifest.csv")
    parser.add_argument("--out-preprocess-manifest", default="configs/v12/v12_solweig_preprocess_formal_hotday_smoke_manifest.csv")
    parser.add_argument("--allow-missing-forcing", action="store_true", help="Allow planned forcing files that do not exist yet.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = ManifestPaths(
        plan=_project_path(args.plan),
        base_manifest=_project_path(args.base_manifest),
        overhead_manifest=_project_path(args.overhead_manifest),
        out_solweig_manifest=_project_path(args.out_solweig_manifest),
        out_preprocess_manifest=_project_path(args.out_preprocess_manifest),
    )
    solweig_df, preprocess_df = build_manifests(paths, allow_missing_forcing=args.allow_missing_forcing)
    print(f"[OK] SOLWEIG manifest rows: {len(solweig_df)} -> {paths.out_solweig_manifest}")
    print(f"[OK] Preprocess manifest rows: {len(preprocess_df)} -> {paths.out_preprocess_manifest}")
    print("[NOTE] This script only writes manifests; QGIS preprocessing and SOLWEIG runs are separate local steps.")


if __name__ == "__main__":
    main()
