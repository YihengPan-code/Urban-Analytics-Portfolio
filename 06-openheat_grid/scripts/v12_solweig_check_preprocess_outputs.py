from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def as_path(p: str) -> Path:
    return Path(p)


def main() -> int:
    ap = argparse.ArgumentParser(description="Check v12 QGIS preprocessing outputs before SOLWEIG Wave 1.")
    ap.add_argument("--manifest", default="configs/v12/v12_solweig_preprocess_wave1_base_manifest.csv")
    ap.add_argument("--out-dir", default="outputs/v12_solweig_typology_pilot/qgis_preprocess")
    args = ap.parse_args()

    manifest = Path(args.manifest)
    if not manifest.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(manifest)
    rows: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        rec = {
            "preprocess_id": r.get("preprocess_id", ""),
            "cell_id": r.get("cell_id", ""),
            "scenario_id": r.get("scenario_id", ""),
            "input_dsm_exists": as_path(r["input_dsm"]).exists(),
            "input_cdsm_exists": as_path(r["input_cdsm"]).exists(),
            "wall_height_exists": as_path(r["wall_height"]).exists(),
            "wall_aspect_exists": as_path(r["wall_aspect"]).exists(),
            "svf_zip_exists": as_path(r["svf_zip_expected"]).exists(),
            "svf_tif_exists": as_path(r.get("svf_output_file", "")).exists() if isinstance(r.get("svf_output_file", ""), str) else False,
            "wall_height": r["wall_height"],
            "wall_aspect": r["wall_aspect"],
            "svf_zip_expected": r["svf_zip_expected"],
        }
        rec["ready_for_solweig"] = bool(
            rec["input_dsm_exists"]
            and rec["input_cdsm_exists"]
            and rec["wall_height_exists"]
            and rec["wall_aspect_exists"]
            and rec["svf_zip_exists"]
        )
        rows.append(rec)

    result = {
        "manifest": str(manifest),
        "rows": rows,
        "n_rows": len(rows),
        "n_ready": sum(1 for r in rows if r["ready_for_solweig"]),
        "n_not_ready": sum(1 for r in rows if not r["ready_for_solweig"]),
    }

    json_path = out_dir / "v12_preprocess_output_check.json"
    md_path = out_dir / "v12_preprocess_output_check.md"

    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = ["# v12 QGIS preprocessing output check\n\n"]
    lines.append(f"- Manifest: `{manifest}`\n")
    lines.append(f"- Rows: `{result['n_rows']}`\n")
    lines.append(f"- Ready: `{result['n_ready']}` / `{result['n_rows']}`\n\n")
    lines.append("| preprocess_id | cell_id | scenario | input_dsm | input_cdsm | wall_height | wall_aspect | svfs.zip | ready |\n")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|\n")
    for r in rows:
        lines.append(
            f"| {r['preprocess_id']} | {r['cell_id']} | {r['scenario_id']} | "
            f"{r['input_dsm_exists']} | {r['input_cdsm_exists']} | "
            f"{r['wall_height_exists']} | {r['wall_aspect_exists']} | "
            f"{r['svf_zip_exists']} | {r['ready_for_solweig']} |\n"
        )

    if result["n_not_ready"]:
        lines.append("\n## Missing outputs\n\n")
        for r in rows:
            if r["ready_for_solweig"]:
                continue
            missing = []
            for key in ["input_dsm_exists", "input_cdsm_exists", "wall_height_exists", "wall_aspect_exists", "svf_zip_exists"]:
                if not r[key]:
                    missing.append(key)
            lines.append(f"- `{r['preprocess_id']}`: {', '.join(missing)}\n")

    md_path.write_text("".join(lines), encoding="utf-8")

    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("[write]", md_path)
    return 0 if result["n_not_ready"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
