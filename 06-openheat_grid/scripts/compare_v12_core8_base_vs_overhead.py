from __future__ import annotations

from pathlib import Path
import pandas as pd

BASE = Path("outputs/v12_solweig_typology_pilot/core8_base_summary/modifier_targets_long.csv")
OVER = Path("outputs/v12_solweig_typology_pilot/core8_overhead_summary/modifier_targets_long.csv")
OUT_DIR = Path("outputs/v12_solweig_typology_pilot/core8_overhead_summary")
OUT_CSV = OUT_DIR / "core8_base_vs_overhead_delta.csv"
OUT_BY_CELL = OUT_DIR / "core8_base_vs_overhead_delta_by_cell.csv"
OUT_MD = OUT_DIR / "core8_base_vs_overhead_delta_report.md"

key = ["cell_id", "hour_sgt"]

base = pd.read_csv(BASE)
over = pd.read_csv(OVER)

base = base[base["scenario_id"].astype(str).eq("base")].copy()
over = over[over["scenario_id"].astype(str).eq("overhead_as_canopy")].copy()

cols = key + ["typology_label", "tmrt_mean_c", "tmrt_p90_c", "tmrt_max_c", "m_rad_pct"]
b = base[cols].rename(columns={
    "typology_label": "typology_label_base",
    "tmrt_mean_c": "tmrt_mean_base",
    "tmrt_p90_c": "tmrt_p90_base",
    "tmrt_max_c": "tmrt_max_base",
    "m_rad_pct": "m_rad_pct_base",
})
o = over[cols].rename(columns={
    "typology_label": "typology_label_overhead",
    "tmrt_mean_c": "tmrt_mean_overhead",
    "tmrt_p90_c": "tmrt_p90_overhead",
    "tmrt_max_c": "tmrt_max_overhead",
    "m_rad_pct": "m_rad_pct_overhead",
})

m = b.merge(o, on=key, how="outer", validate="one_to_one")

for metric in ["tmrt_mean", "tmrt_p90", "tmrt_max", "m_rad_pct"]:
    m[f"delta_{metric}_overhead_minus_base"] = m[f"{metric}_overhead"] - m[f"{metric}_base"]

m["abs_delta_tmrt_p90"] = m["delta_tmrt_p90_overhead_minus_base"].abs()
m["flag_p90_large_change"] = m["abs_delta_tmrt_p90"] >= 1.0
m["flag_p90_increase"] = m["delta_tmrt_p90_overhead_minus_base"] > 0.1
m["flag_mean_large_but_p90_small"] = (
    (m["delta_tmrt_mean_overhead_minus_base"].abs() >= 1.0)
    & (m["delta_tmrt_p90_overhead_minus_base"].abs() < 0.5)
)

m = m.sort_values(["cell_id", "hour_sgt"]).reset_index(drop=True)

by_cell = (
    m.groupby("cell_id", as_index=False)
    .agg(
        n=("hour_sgt", "count"),
        mean_delta_mean=("delta_tmrt_mean_overhead_minus_base", "mean"),
        min_delta_mean=("delta_tmrt_mean_overhead_minus_base", "min"),
        max_delta_mean=("delta_tmrt_mean_overhead_minus_base", "max"),
        mean_delta_p90=("delta_tmrt_p90_overhead_minus_base", "mean"),
        min_delta_p90=("delta_tmrt_p90_overhead_minus_base", "min"),
        max_delta_p90=("delta_tmrt_p90_overhead_minus_base", "max"),
        max_abs_delta_p90=("abs_delta_tmrt_p90", "max"),
        n_large_p90_change=("flag_p90_large_change", "sum"),
        n_p90_increase=("flag_p90_increase", "sum"),
        n_mean_large_p90_small=("flag_mean_large_but_p90_small", "sum"),
    )
    .sort_values("max_abs_delta_p90", ascending=False)
)

OUT_DIR.mkdir(parents=True, exist_ok=True)
m.to_csv(OUT_CSV, index=False)
by_cell.to_csv(OUT_BY_CELL, index=False)

lines = []
lines.append("# v12 Core 8 base vs overhead_as_canopy delta report\n\n")
lines.append(f"- Base: `{BASE}`\n")
lines.append(f"- Overhead: `{OVER}`\n")
lines.append(f"- Rows compared: `{len(m)}`\n\n")

lines.append("## By-cell delta summary\n\n")
lines.append(by_cell.round(3).to_markdown(index=False))
lines.append("\n\n")

flags = m[m["flag_p90_large_change"] | m["flag_p90_increase"] | m["flag_mean_large_but_p90_small"]].copy()
lines.append("## Flagged rows\n\n")
if flags.empty:
    lines.append("_No flagged rows._\n\n")
else:
    show = [
        "cell_id", "hour_sgt",
        "tmrt_mean_base", "tmrt_mean_overhead", "delta_tmrt_mean_overhead_minus_base",
        "tmrt_p90_base", "tmrt_p90_overhead", "delta_tmrt_p90_overhead_minus_base",
        "tmrt_max_base", "tmrt_max_overhead", "delta_tmrt_max_overhead_minus_base",
        "flag_p90_large_change", "flag_p90_increase", "flag_mean_large_but_p90_small",
    ]
    lines.append(flags[show].round(3).to_markdown(index=False))
    lines.append("\n\n")

lines.append("## Interpretation notes\n\n")
lines.append("- `flag_p90_large_change` means |overhead p90 - base p90| >= 1°C.\n")
lines.append("- `flag_p90_increase` means overhead p90 is >0.1°C warmer than base; this may be numerical/contextual and should be inspected before interpretation.\n")
lines.append("- `flag_mean_large_but_p90_small` means overhead changes the average strongly while upper-tail exposure remains stable; this supports using p90 as primary target.\n")
lines.append("- This comparison remains a mapped-overhead sensitivity diagnostic, not local WBGT and not risk.\n")

OUT_MD.write_text("".join(lines), encoding="utf-8")

print("[write]", OUT_CSV)
print("[write]", OUT_BY_CELL)
print("[write]", OUT_MD)
print(by_cell.round(3).to_string(index=False))
