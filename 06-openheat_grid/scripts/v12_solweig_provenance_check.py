from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_info(path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "path": path.as_posix(),
        "exists": exists,
        "size_bytes": path.stat().st_size if exists and path.is_file() else None,
        "is_file": path.is_file() if exists else False,
        "is_dir": path.is_dir() if exists else False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Check v10/v12 SOLWEIG source-of-truth files before Wave 0.")
    ap.add_argument("--config", default="configs/v12/v12_solweig_typology_config.example.json")
    ap.add_argument("--out-dir", default="outputs/v12_solweig_typology_pilot/provenance")
    args = ap.parse_args()

    cfg = read_json(Path(args.config))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = cfg["paths"]
    v10 = cfg["v10_wave0_reuse"]

    checks: list[dict[str, Any]] = []
    for label, p in [
        ("building_dsm", paths["building_dsm"]),
        ("vegetation_dsm", paths["vegetation_dsm"]),
        ("overhead_structures_geojson", paths["overhead_structures_geojson"]),
        ("grid_geojson", paths["grid_geojson"]),
        ("v10_tile_root", paths["v10_tile_root"]),
        ("v10_wave0_tile_dir", f"{paths['v10_tile_root']}/{v10['tile']}"),
        ("v10_wave0_focus_cell", v10["focus_cell_geojson"]),
        ("v10_wave0_forcing", v10["forcing_file"]),
        ("v10_wave0_dsm_tile", f"{paths['v10_tile_root']}/{v10['tile']}/dsm_buildings_tile.tif"),
        ("v10_wave0_dem_tile", f"{paths['v10_tile_root']}/{v10['tile']}/dsm_dem_flat_tile.tif"),
        ("v10_wave0_cdsm_base", f"{paths['v10_tile_root']}/{v10['tile']}/dsm_vegetation_tile_base.tif"),
        ("v10_wave0_wall_height", f"{paths['v10_tile_root']}/{v10['tile']}/wall_height.tif"),
        ("v10_wave0_wall_aspect", f"{paths['v10_tile_root']}/{v10['tile']}/wall_aspect.tif"),
        ("v10_wave0_svf_base", f"{paths['v10_tile_root']}/{v10['tile']}/svf_base/svfs.zip"),
    ]:
        item = file_info(Path(p))
        item["label"] = label
        checks.append(item)

    for hour, p in cfg.get("forcing_files_by_hour", {}).items():
        item = file_info(Path(p))
        item["label"] = f"forcing_h{hour}"
        checks.append(item)

    missing = [c for c in checks if not c["exists"]]

    result = {
        "config": args.config,
        "n_checked": len(checks),
        "n_missing": len(missing),
        "missing": missing,
        "checks": checks,
    }

    json_path = out_dir / "v12_solweig_provenance_check.json"
    md_path = out_dir / "v12_solweig_provenance_check.md"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = ["# v12 SOLWEIG provenance check\n\n"]
    lines.append(f"- Config: `{args.config}`\n")
    lines.append(f"- Checked: `{len(checks)}`\n")
    lines.append(f"- Missing: `{len(missing)}`\n\n")
    lines.append("| label | exists | size_bytes | path |\n|---|---:|---:|---|\n")
    for c in checks:
        lines.append(f"| {c['label']} | {c['exists']} | {c['size_bytes']} | `{c['path']}` |\n")
    if missing:
        lines.append("\n## Missing files\n\n")
        for c in missing:
            lines.append(f"- `{c['label']}`: `{c['path']}`\n")
    else:
        lines.append("\nAll checked files exist.\n")

    md_path.write_text("".join(lines), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("[write]", md_path)
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
