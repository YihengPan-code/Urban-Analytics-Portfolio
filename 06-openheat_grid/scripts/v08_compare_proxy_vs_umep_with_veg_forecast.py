"""Compare v0.7 proxy-morphology forecast ranking with v0.8 UMEP+vegetation ranking.

Patch notes (v0.8-beta review hotfix):
- Coerces metric columns to numeric and reports NaN counts.
- Computes ranks on nullable data without crashing when metrics contain NaN.
- Uses a clean non-NaN subset for Spearman and top-N overlap.
- Reports how many cells were excluded from comparison.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def rank_by_metric(df: pd.DataFrame, metric: str, name: str) -> pd.DataFrame:
    if metric not in df.columns:
        raise ValueError(f"Metric `{metric}` not found in {name}. Available examples: {df.columns[:20].tolist()}")
    out = df[["cell_id", metric]].copy()
    out[metric] = pd.to_numeric(out[metric], errors="coerce")
    out[f"rank_{name}_{metric}"] = out[metric].rank(method="min", ascending=False)
    return out.rename(columns={metric: f"{metric}_{name}"})


def _fmt_spearman(x: float | None) -> str:
    if x is None or pd.isna(x):
        return "NA"
    return f"{x:.4f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-ranking", default="outputs/v07_beta_final_forecast_live/v06_live_hotspot_ranking.csv")
    parser.add_argument("--new-ranking", default="outputs/v08_umep_with_veg_forecast_live/v06_live_hotspot_ranking.csv")
    parser.add_argument("--metric", default="hazard_score")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--out-dir", default="outputs/v08_umep_with_veg_comparison")
    args = parser.parse_args()

    old = pd.read_csv(args.old_ranking)
    new = pd.read_csv(args.new_ranking)
    old_r = rank_by_metric(old, args.metric, "proxy_v07")
    new_r = rank_by_metric(new, args.metric, "umep_veg_v08")
    m = old_r.merge(new_r, on="cell_id", how="inner")

    old_metric_col = f"{args.metric}_proxy_v07"
    new_metric_col = f"{args.metric}_umep_veg_v08"
    old_rank_col = f"rank_proxy_v07_{args.metric}"
    new_rank_col = f"rank_umep_veg_v08_{args.metric}"

    n_nan_old_metric = int(m[old_metric_col].isna().sum())
    n_nan_new_metric = int(m[new_metric_col].isna().sum())
    n_nan_old_rank = int(m[old_rank_col].isna().sum())
    n_nan_new_rank = int(m[new_rank_col].isna().sum())
    clean = m.dropna(subset=[old_rank_col, new_rank_col]).copy()

    print(f"[INFO] merged cells: {len(m)}")
    print(f"[INFO] NaN metric values: old={n_nan_old_metric}, new={n_nan_new_metric}")
    print(f"[INFO] NaN rank values: old={n_nan_old_rank}, new={n_nan_new_rank}")
    print(f"[INFO] clean comparison cells: {len(clean)}")

    if len(clean) < 2:
        spearman = None
        print("[WARN] Fewer than 2 clean cells; Spearman correlation is undefined.")
    else:
        spearman = clean[old_rank_col].corr(clean[new_rank_col], method="spearman")

    # Rank change is only meaningful for clean cells. Keep NaN rows in CSV too.
    m["rank_change_proxy_minus_umep"] = m[old_rank_col] - m[new_rank_col]
    clean["rank_change_proxy_minus_umep"] = clean[old_rank_col] - clean[new_rank_col]

    old_top = set(clean.nsmallest(args.top_n, old_rank_col)["cell_id"])
    new_top = set(clean.nsmallest(args.top_n, new_rank_col)["cell_id"])
    overlap = len(old_top & new_top)
    entering = sorted(new_top - old_top)
    leaving = sorted(old_top - new_top)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "v08_proxy_vs_umep_with_veg_rank_comparison.csv"
    m.to_csv(out_csv, index=False)

    out_clean_csv = out_dir / "v08_proxy_vs_umep_with_veg_rank_comparison_clean.csv"
    clean.to_csv(out_clean_csv, index=False)

    lines = ["# v0.7 proxy vs v0.8 UMEP+vegetation forecast comparison", ""]
    lines.append(f"Metric: `{args.metric}`")
    lines.append(f"Merged cells: **{len(m)}**")
    lines.append(f"Clean compared cells: **{len(clean)}**")
    lines.append(f"NaN metric values: old={n_nan_old_metric}, new={n_nan_new_metric}")
    lines.append(f"NaN rank values: old={n_nan_old_rank}, new={n_nan_new_rank}")
    lines.append(f"Spearman rank correlation: **{_fmt_spearman(spearman)}**")
    lines.append(f"Top {args.top_n} overlap: **{overlap} / {args.top_n}**")
    lines.append("")
    lines.append("## Entering v0.8 UMEP+veg top set")
    lines.append(", ".join(entering) if entering else "None")
    lines.append("")
    lines.append("## Leaving v0.7 proxy top set")
    lines.append(", ".join(leaving) if leaving else "None")
    lines.append("")
    if len(clean):
        lines.append("## Largest rank changes toward UMEP+veg top")
        lines.append(clean.sort_values("rank_change_proxy_minus_umep", ascending=False).head(25).to_string(index=False))
        lines.append("")
        lines.append("## Largest rank drops under UMEP+veg")
        lines.append(clean.sort_values("rank_change_proxy_minus_umep", ascending=True).head(25).to_string(index=False))
    else:
        lines.append("No clean rows available for rank-change tables.")

    out_md = out_dir / "v08_proxy_vs_umep_with_veg_forecast_comparison.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print("[OK] Comparison complete")
    print("report:", out_md)
    print("csv:", out_csv)
    print("clean_csv:", out_clean_csv)
    print("spearman:", _fmt_spearman(spearman))
    print(f"top{args.top_n}_overlap:", overlap, "/", args.top_n)


if __name__ == "__main__":
    main()
