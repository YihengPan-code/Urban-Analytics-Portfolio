"""Compare two hotspot ranking files, typically pre/post feature-engineering fix."""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--old", required=True)
    p.add_argument("--new", required=True)
    p.add_argument("--out", default="outputs/v07_beta1_ranking_stability_comparison.csv")
    p.add_argument("--top-n", type=int, default=20)
    args = p.parse_args()
    old = pd.read_csv(args.old)
    new = pd.read_csv(args.new)
    if "rank" not in old.columns or "rank" not in new.columns:
        raise ValueError("Both files must contain rank.")
    m = old[["cell_id", "rank", "risk_priority_score"]].rename(columns={"rank": "rank_old", "risk_priority_score": "risk_old"}).merge(
        new[["cell_id", "rank", "risk_priority_score"]].rename(columns={"rank": "rank_new", "risk_priority_score": "risk_new"}),
        on="cell_id",
        how="inner",
    )
    m["rank_change"] = m["rank_old"] - m["rank_new"]
    top_old = set(m.nsmallest(args.top_n, "rank_old")["cell_id"])
    top_new = set(m.nsmallest(args.top_n, "rank_new")["cell_id"])
    corr = m["rank_old"].corr(m["rank_new"], method="spearman")
    overlap = len(top_old & top_new)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    m.to_csv(out, index=False)
    print("Spearman rank corr:", corr)
    print(f"Top{args.top_n} overlap:", overlap, f"/ {args.top_n}")
    print("Wrote:", out)
    print(m.sort_values("rank_new").head(args.top_n).to_string(index=False))

if __name__ == "__main__":
    main()
