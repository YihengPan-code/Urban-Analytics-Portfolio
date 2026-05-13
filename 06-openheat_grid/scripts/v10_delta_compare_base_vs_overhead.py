"""Compare v10-gamma base ranking against v10-delta overhead-shade sensitivity ranking."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd


def read_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def rank_by_metric(df: pd.DataFrame, metric: str, suffix: str) -> pd.DataFrame:
    if "cell_id" not in df.columns:
        raise KeyError("ranking must contain cell_id")
    if metric not in df.columns:
        raise KeyError(f"metric not found in ranking: {metric}")
    out = df[["cell_id", metric]].copy()
    out[metric] = pd.to_numeric(out[metric], errors="coerce")
    out[f"rank_{suffix}_{metric}"] = out[metric].rank(method="min", ascending=False, na_option="bottom")
    out = out.rename(columns={metric: f"{metric}_{suffix}"})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v10/v10_delta_overhead_config.example.json")
    args = ap.parse_args()

    cfg = read_json(Path(args.config))
    inp = cfg["inputs"]
    out = cfg["outputs"]
    cmp_cfg = cfg.get("comparison", {})
    metric = cmp_cfg.get("metric", "hazard_score")
    top_n = int(cmp_cfg.get("top_n", 20))

    base_path = Path(inp.get("v10_base_ranking_csv", ""))
    overhead_path = Path(cmp_cfg.get("overhead_ranking_csv", ""))
    overhead_cell_path = Path(out["overhead_per_cell_csv"])
    if not base_path.exists():
        raise FileNotFoundError(f"Base v10 ranking not found: {base_path}")
    if not overhead_path.exists():
        raise FileNotFoundError(f"Overhead sensitivity ranking not found: {overhead_path}. Run forecast using overhead sensitivity grid first.")

    base = pd.read_csv(base_path)
    oh = pd.read_csv(overhead_path)
    b = rank_by_metric(base, metric, "base_v10")
    o = rank_by_metric(oh, metric, "overhead_sens")
    m = b.merge(o, on="cell_id", how="inner")
    old_rank_col = f"rank_base_v10_{metric}"
    new_rank_col = f"rank_overhead_sens_{metric}"
    m["rank_change_base_minus_overhead"] = m[old_rank_col] - m[new_rank_col]
    m["score_change_overhead_minus_base"] = m[f"{metric}_overhead_sens"] - m[f"{metric}_base_v10"]

    if overhead_cell_path.exists():
        oc = pd.read_csv(overhead_cell_path)
        keep = [c for c in ["cell_id", "overhead_fraction_total", "overhead_shade_proxy", "pedestrian_shelter_fraction", "transport_deck_fraction", "overhead_confounding_flag", "overhead_interpretation"] if c in oc.columns]
        m = m.merge(oc[keep], on="cell_id", how="left")

    clean = m.dropna(subset=[old_rank_col, new_rank_col])
    spearman = clean[old_rank_col].corr(clean[new_rank_col], method="spearman")
    base_top = set(clean.nsmallest(top_n, old_rank_col)["cell_id"])
    oh_top = set(clean.nsmallest(top_n, new_rank_col)["cell_id"])
    overlap = len(base_top & oh_top)
    entering = sorted(oh_top - base_top)
    leaving = sorted(base_top - oh_top)

    csv_path = Path(out["base_vs_overhead_comparison_csv"])
    ensure_dir(csv_path)
    m.to_csv(csv_path, index=False)

    # Topset details.
    top_details = clean[(clean["cell_id"].isin(base_top)) | (clean["cell_id"].isin(oh_top))].copy()
    top_details["in_base_top"] = top_details["cell_id"].isin(base_top)
    top_details["in_overhead_top"] = top_details["cell_id"].isin(oh_top)
    details_path = Path(out["topset_details_csv"])
    ensure_dir(details_path)
    top_details.sort_values(new_rank_col).to_csv(details_path, index=False)

    report_path = Path(out["base_vs_overhead_comparison_report"])
    ensure_dir(report_path)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# v10-delta base vs overhead-shade sensitivity comparison\n\n")
        f.write(f"Metric: `{metric}`\n\n")
        f.write(f"Merged cells: **{len(m)}**\n\n")
        f.write(f"Clean compared cells: **{len(clean)}**\n\n")
        f.write(f"Spearman rank correlation: **{spearman:.4f}**\n\n")
        f.write(f"Top {top_n} overlap: **{overlap} / {top_n}**\n\n")
        f.write("## Entering overhead-sensitivity top set\n\n")
        f.write(", ".join(entering) if entering else "None")
        f.write("\n\n## Leaving base v10 top set\n\n")
        f.write(", ".join(leaving) if leaving else "None")
        f.write("\n\n## Largest rank drops under overhead sensitivity\n\n```text\n")
        cols = ["cell_id", f"{metric}_base_v10", old_rank_col, f"{metric}_overhead_sens", new_rank_col, "rank_change_base_minus_overhead", "overhead_fraction_total", "overhead_shade_proxy", "overhead_confounding_flag", "overhead_interpretation"]
        cols = [c for c in cols if c in clean.columns]
        f.write(clean.sort_values("rank_change_base_minus_overhead").head(25)[cols].to_string(index=False))
        f.write("\n```\n\n")
        f.write("## Largest rank gains under overhead sensitivity\n\n```text\n")
        f.write(clean.sort_values("rank_change_base_minus_overhead", ascending=False).head(25)[cols].to_string(index=False))
        f.write("\n```\n\n")
        f.write("## Interpretation note\n")
        f.write("- This comparison tests a ground-level overhead-shade sensitivity, not a final overhead-aware physical model.\n")
        f.write("- Cells dominated by elevated transport decks should be flagged separately from pedestrian exposure cells.\n")
        f.write("- Large rank drops in major overhead cells indicate locations where the v10 base hazard may overstate ground-level radiant exposure.\n")

    print(f"[OK] comparison CSV: {csv_path}")
    print(f"[OK] details CSV: {details_path}")
    print(f"[OK] report: {report_path}")
    print(f"spearman: {spearman:.4f}")
    print(f"top{top_n}_overlap: {overlap} / {top_n}")


if __name__ == "__main__":
    main()
