from __future__ import annotations

import argparse
import csv
from pathlib import Path
import pandas as pd


def parse_csv_list(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description="Create QGIS preprocessing manifest for v12 SOLWEIG tiles.")
    ap.add_argument("--tile-metadata", default="data/solweig/v12_typology_tiles/v12_typology_tile_metadata.csv")
    ap.add_argument("--out", default="configs/v12/v12_solweig_preprocess_wave1_base_manifest.csv")
    ap.add_argument("--cells", default="TP_0986,TP_0542,TP_0059")
    ap.add_argument("--scenarios", default="base")
    args = ap.parse_args()

    meta_path = Path(args.tile_metadata)
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing tile metadata: {meta_path}")

    cells = set(parse_csv_list(args.cells))
    scenarios = parse_csv_list(args.scenarios)

    meta = pd.read_csv(meta_path)
    if "cell_id" not in meta.columns or "tile_dir" not in meta.columns:
        raise KeyError("tile metadata must include cell_id and tile_dir")

    meta = meta[meta["cell_id"].astype(str).isin(cells)].copy()
    if meta.empty:
        raise ValueError(f"No metadata rows matched cells: {sorted(cells)}")

    missing = cells.difference(set(meta["cell_id"].astype(str)))
    if missing:
        print("[WARN] requested cells missing from tile metadata:", ", ".join(sorted(missing)))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for _, r in meta.iterrows():
        tile_dir = Path(str(r["tile_dir"]))
        for scenario in scenarios:
            if scenario == "base":
                cdsm = tile_dir / "dsm_vegetation_tile_base.tif"
                svf_dir = tile_dir / "svf_base"
            elif scenario == "overhead_as_canopy":
                cdsm = tile_dir / "dsm_vegetation_tile_overhead.tif"
                svf_dir = tile_dir / "svf_overhead"
            else:
                raise ValueError(f"Unsupported scenario: {scenario}")

            rows.append({
                "preprocess_id": f"prep_{r['cell_id']}_{scenario}",
                "tile_id": r.get("tile_id", ""),
                "cell_id": r["cell_id"],
                "typology_label": r.get("typology_label", ""),
                "scenario_id": scenario,
                "tile_dir": tile_dir.as_posix(),
                "input_dsm": (tile_dir / "dsm_buildings_tile.tif").as_posix(),
                "input_cdsm": cdsm.as_posix(),
                "wall_height": (tile_dir / "wall_height.tif").as_posix(),
                "wall_aspect": (tile_dir / "wall_aspect.tif").as_posix(),
                "svf_output_dir": svf_dir.as_posix(),
                "svf_output_file": (svf_dir / "svf.tif").as_posix(),
                "svf_zip_expected": (svf_dir / "svfs.zip").as_posix(),
                "run_wall_height_aspect": "yes",
                "run_svf": "yes",
                "status": "planned",
                "notes": "",
            })

    with out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"[write] {out}")
    print(f"[rows] {len(rows)}")
    print("Cells:", ", ".join(sorted(set(x["cell_id"] for x in rows))))
    print("Scenarios:", ", ".join(scenarios))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
