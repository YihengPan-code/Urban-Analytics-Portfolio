from pathlib import Path
from datetime import datetime
import pandas as pd

ROOT = Path(".")

FILES = {
    "outputs/v12_solweig_n150_execution/n150_new_solweig_run_log.csv": 1260,
    "outputs/v12_solweig_n150_execution/n150_new_focus_tmrt_summary.csv": 1260,
    "outputs/v12_solweig_n150_execution/n150_new_base_vs_overhead_delta.csv": 630,
    "outputs/v12_solweig_n150_execution/n150_focus_tmrt_summary_merged.csv": 1500,
    "outputs/v12_solweig_n150_execution/n150_base_vs_overhead_delta_merged.csv": 750,
    "outputs/v12_solweig_n150_execution/n150_modifier_targets_b5.csv": 1500,
    "outputs/v12_solweig_n150_execution/n150_reference_values_b5.csv": 10,
}

OUT_DIR = ROOT / "outputs/v12_solweig_n150_execution"
REPORT_MD = OUT_DIR / "sprint_b7_2_n150_schema_cleanup_report.md"
REPORT_CSV = OUT_DIR / "b7_2_schema_cleanup_validation.csv"

def harmonize_hour_columns(path: Path, expected_rows: int | None) -> dict:
    row = {
        "file": str(path),
        "exists": path.exists(),
        "expected_rows": expected_rows,
        "observed_rows": "",
        "had_hour": False,
        "had_hour_sgt": False,
        "changed": False,
        "status": "PASS",
        "note": "",
    }

    if not path.exists():
        row["status"] = "MISSING"
        row["note"] = "file not found"
        return row

    df = pd.read_csv(path)
    row["observed_rows"] = len(df)
    row["had_hour"] = "hour" in df.columns
    row["had_hour_sgt"] = "hour_sgt" in df.columns

    if expected_rows is not None and len(df) != expected_rows:
        row["status"] = "FAIL"
        row["note"] = f"row count mismatch: expected {expected_rows}, observed {len(df)}"
        return row

    if "hour" not in df.columns and "hour_sgt" not in df.columns:
        row["note"] = "no hour/hour_sgt columns; skipped"
        return row

    if "hour_sgt" not in df.columns and "hour" in df.columns:
        df["hour_sgt"] = df["hour"]
        row["changed"] = True

    if "hour" not in df.columns and "hour_sgt" in df.columns:
        df["hour"] = df["hour_sgt"]
        row["changed"] = True

    # Normalize both to numeric nullable integer where possible.
    hour = pd.to_numeric(df["hour"], errors="coerce")
    hour_sgt = pd.to_numeric(df["hour_sgt"], errors="coerce")

    missing_hour = hour.isna() & hour_sgt.notna()
    missing_hour_sgt = hour_sgt.isna() & hour.notna()

    if missing_hour.any():
        hour.loc[missing_hour] = hour_sgt.loc[missing_hour]
        row["changed"] = True

    if missing_hour_sgt.any():
        hour_sgt.loc[missing_hour_sgt] = hour.loc[missing_hour_sgt]
        row["changed"] = True

    comparable = hour.notna() & hour_sgt.notna()
    mismatches = comparable & (hour.astype("Int64") != hour_sgt.astype("Int64"))
    if mismatches.any():
        bad = df.loc[mismatches, ["cell_id"] if "cell_id" in df.columns else []].head(5).to_dict("records")
        row["status"] = "FAIL"
        row["note"] = f"hour/hour_sgt mismatch rows={int(mismatches.sum())}; examples={bad}"
        return row

    df["hour"] = hour.astype("Int64")
    df["hour_sgt"] = hour_sgt.astype("Int64")

    if row["changed"]:
        df.to_csv(path, index=False)

    row["note"] = "hour/hour_sgt present and consistent"
    return row

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = [harmonize_hour_columns(ROOT / rel, expected) for rel, expected in FILES.items()]
    report = pd.DataFrame(rows)
    report.to_csv(REPORT_CSV, index=False)

    failed = report[report["status"] == "FAIL"]
    missing = report[report["status"] == "MISSING"]

    lines = [
        "# Sprint B7.2 — N150 schema cleanup",
        "",
        "## Status",
        "PASS" if failed.empty and missing.empty else "FAIL",
        "",
        "## Scope",
        "- Tiny schema cleanup only.",
        "- No QGIS.",
        "- No SOLWEIG rerun.",
        "- No raw raster reads.",
        "- No selected-cell or manifest changes.",
        "- No local WBGT, hazard_score, risk_score, surrogate, or System A/B coupling.",
        "",
        "## Purpose",
        "Ensure B7/B8 downstream tables consistently expose both `hour_sgt` and `hour`, with identical values where both exist.",
        "",
        "## Result",
        f"- Files checked: {len(report)}",
        f"- Files changed: {int(report['changed'].sum())}",
        f"- Failed checks: {len(failed)}",
        f"- Missing files: {len(missing)}",
        "",
        "## Validation table",
        "",
        report.to_markdown(index=False),
        "",
        "## Downstream rule",
        "B8 should prefer `hour_sgt` as the canonical hour field. The `hour` column is retained only as a compatibility alias.",
        "",
        f"Generated at: {datetime.now().isoformat(timespec='seconds')}",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

    if not failed.empty or not missing.empty:
        raise SystemExit("B7.2 schema cleanup validation failed. See report.")

    print(f"[OK] wrote {REPORT_CSV}")
    print(f"[OK] wrote {REPORT_MD}")

if __name__ == "__main__":
    main()
