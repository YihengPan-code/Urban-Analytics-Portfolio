from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def read_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def classify(delta: float) -> str:
    if pd.isna(delta): return "missing"
    if delta <= -15: return "large_reduction"
    if delta <= -8: return "moderate_reduction"
    if delta <= -3: return "small_reduction"
    if abs(delta) < 3: return "little_change"
    return "increase_or_unexpected"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v10/v10_epsilon_solweig_config.example.json")
    args = ap.parse_args()
    cfg = read_json(Path(args.config))
    out_root = Path(cfg["paths"]["output_root"])
    p = out_root / "v10_epsilon_focus_tmrt_summary.csv"
    if not p.exists():
        raise FileNotFoundError(f"Run aggregation first: {p}")
    df = pd.read_csv(p)
    key = ["tile_id", "cell_id", "role", "tmrt_time_label", "tmrt_hour_sgt"]
    piv = df.pivot_table(index=key, columns="scenario", values="tmrt_mean_c", aggfunc="mean").reset_index()
    piv.columns.name = None
    for col in ["base", "overhead"]:
        if col not in piv.columns:
            piv[col] = np.nan
    piv["delta_overhead_minus_base_c"] = piv["overhead"] - piv["base"]
    piv["delta_class"] = piv["delta_overhead_minus_base_c"].apply(classify)
    out_csv = out_root / "v10_epsilon_base_vs_overhead_tmrt_comparison.csv"
    piv.to_csv(out_csv, index=False)
    role = piv.groupby("role").agg(
        n=("delta_overhead_minus_base_c", "count"),
        mean_delta=("delta_overhead_minus_base_c", "mean"),
        min_delta=("delta_overhead_minus_base_c", "min"),
        max_delta=("delta_overhead_minus_base_c", "max"),
    ).reset_index()
    report = out_root / "v10_epsilon_solweig_comparison_report.md"
    lines = ["# v10-epsilon SOLWEIG base vs overhead scenario comparison", ""]
    lines.append("This is a selected-cell physical sensitivity check, not a full overhead-aware operational model.\n")
    lines += ["## Focus-cell comparison", "```text", piv.sort_values(["tile_id", "tmrt_hour_sgt"]).to_string(index=False), "```"]
    lines += ["\n## Mean delta by role", "```text", role.to_string(index=False), "```"]
    lines += ["\n## Interpretation", "- TP_0565 / TP_0986 should show little change if they are true low-overhead hot anchors.", "- TP_0088 / TP_0916 should show meaningful Tmrt reduction if v10-delta overhead sensitivity is directionally supported.", "- If saturated overhead cells only show small SOLWEIG reductions, the v10-delta algebraic shade sensitivity is too aggressive for exact magnitude, though still useful as a confounding flag."]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] comparison csv: {out_csv}")
    print(f"[OK] report: {report}")


if __name__ == "__main__":
    main()
