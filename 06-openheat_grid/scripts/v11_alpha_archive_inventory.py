from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from v11_lib import read_json, expand_globs, read_table, ensure_dir, write_md, df_to_md_table


def inspect_file(path: Path, kind: str) -> dict:
    row = {"kind": kind, "path": str(path), "exists": path.exists(), "rows": None, "columns": None, "error": ""}
    try:
        df = read_table(path)
        row["rows"] = len(df)
        row["columns"] = ";".join(map(str, df.columns.tolist()))
    except Exception as e:
        row["error"] = str(e)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v11/v11_alpha_archive_config.example.json")
    args = ap.parse_args()
    cfg = read_json(args.config)
    out_dir = ensure_dir(cfg["paths"].get("output_dir", "outputs/v11_alpha_archive"))

    nea_paths = expand_globs(cfg["archive"].get("nea_wbgt_globs", []))
    weather_paths = expand_globs(cfg["archive"].get("weather_globs", []))
    extra_paths = expand_globs(cfg["archive"].get("extra_globs", []))

    rows = []
    for p in nea_paths:
        rows.append(inspect_file(p, "nea_wbgt"))
    for p in weather_paths:
        rows.append(inspect_file(p, "weather"))
    for p in extra_paths:
        rows.append(inspect_file(p, "extra"))
    inv = pd.DataFrame(rows)
    inv_path = out_dir / "v11_archive_inventory.csv"
    inv.to_csv(inv_path, index=False)

    summary = inv.groupby("kind", dropna=False).agg(n_files=("path", "count"), rows=("rows", "sum"), n_errors=("error", lambda x: int((x.astype(str) != "").sum()))).reset_index() if not inv.empty else pd.DataFrame()
    report = [
        "# OpenHeat v1.1-alpha archive inventory report",
        "",
        f"Config: `{args.config}`",
        "",
        "## Summary",
        df_to_md_table(summary),
        "",
        "## File inventory sample",
        df_to_md_table(inv[["kind", "path", "rows", "error"]] if not inv.empty else inv),
        "",
        "## Notes",
        "- This step only inventories available archive files; it does not validate station/weather pairing quality.",
        "- If expected files are missing, edit `archive.nea_wbgt_globs` and `archive.weather_globs` in the config.",
    ]
    report_path = out_dir / "v11_archive_inventory_report.md"
    write_md(report_path, "\n".join(report))
    print(f"[OK] inventory CSV: {inv_path}")
    print(f"[OK] report: {report_path}")


if __name__ == "__main__":
    main()
