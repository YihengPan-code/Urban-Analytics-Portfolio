from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import rasterio


def read_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def exists_msg(path: str) -> str:
    p = Path(path)
    return f"{'[OK]' if p.exists() else '[MISSING]'} {path}"


def raster_msg(path: str) -> list[str]:
    p = Path(path)
    if not p.exists():
        return [f"[MISSING] raster: {path}"]
    try:
        with rasterio.open(p) as src:
            lines = [
                f"[OK] raster: {path}",
                f"    shape: {src.height} x {src.width}",
                f"    crs: {src.crs}",
                f"    resolution: {src.res}",
                f"    nodata: {src.nodata}",
                f"    bounds: {src.bounds}",
            ]
            if src.nodata == 0:
                lines.append("    [WARN] nodata is 0.0; ground should be valid 0.0 for building DSM.")
            return lines
    except Exception as e:
        return [f"[ERROR] could not read raster {path}: {e}"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Check v10-beta morphology input files.")
    parser.add_argument("--config", default="configs/v10/v10_beta_morphology_config.example.json")
    args = parser.parse_args()

    cfg = read_json(Path(args.config))
    paths = cfg.get("paths", {})
    out_report = Path(cfg.get("outputs", {}).get("input_check_report", "outputs/v10_morphology/v10_beta_input_check_report.md"))
    out_report.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# v10-beta input check report")
    lines.append("")
    lines.append(f"Config: `{args.config}`")
    lines.append("")

    for key, path in paths.items():
        lines.append(f"## {key}")
        if key.endswith("dsm") or "dsm" in key:
            lines.extend(raster_msg(path))
        else:
            lines.append(exists_msg(path))
        lines.append("")

    out_report.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\n[OK] report: {out_report}")


if __name__ == "__main__":
    main()
