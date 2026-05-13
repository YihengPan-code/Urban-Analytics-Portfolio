from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def rank_metric(df: pd.DataFrame, metric: str, label: str) -> pd.DataFrame:
    out = df[["cell_id", metric]].copy()
    out[metric] = pd.to_numeric(out[metric], errors="coerce")
    out[f"rank_{label}_{metric}"] = out[metric].rank(method="min", ascending=False)
    out = out.rename(columns={metric: f"{metric}_{label}"})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare v08/current DSM vs v10-gamma reviewed-DSM forecast rankings.")
    parser.add_argument("--config", default="configs/v10/v10_gamma_umep_config.example.json")
    args = parser.parse_args()

    cfg = read_json(Path(args.config))
    paths = cfg["paths"]
    st = cfg.get("settings", {})
    metric = st.get("compare_metric", "hazard_score")
    top_n = int(st.get("top_n", 20))

    old_path = Path(paths["old_v08_ranking_csv"])
    new_path = Path(paths["forecast_dir"]) / "v06_live_hotspot_ranking.csv"
    out_dir = Path(paths["comparison_dir"])
    fp_path = Path(paths.get("false_positive_candidates_csv", ""))
    out_dir.mkdir(parents=True, exist_ok=True)

    if not old_path.exists():
        raise FileNotFoundError(old_path)
    if not new_path.exists():
        raise FileNotFoundError(new_path)

    old = pd.read_csv(old_path)
    new = pd.read_csv(new_path)
    if metric not in old.columns or metric not in new.columns:
        raise KeyError(f"Metric {metric} must be present in both ranking files")

    o = rank_metric(old, metric, "v08")
    n = rank_metric(new, metric, "v10")
    m = o.merge(n, on="cell_id", how="inner")
    old_rank = f"rank_v08_{metric}"
    new_rank = f"rank_v10_{metric}"
    m["rank_change_v08_minus_v10"] = m[old_rank] - m[new_rank]

    clean = m.dropna(subset=[old_rank, new_rank])
    spearman = clean[old_rank].corr(clean[new_rank], method="spearman")
    old_top = set(clean.nsmallest(top_n, old_rank)["cell_id"])
    new_top = set(clean.nsmallest(top_n, new_rank)["cell_id"])
    entering = sorted(new_top - old_top)
    leaving = sorted(old_top - new_top)

    # Attach false-positive candidate flag if available.
    fp_summary = "false_positive_candidates_csv not found"
    if fp_path.exists():
        fp = pd.read_csv(fp_path)
        fp_cells = set(fp.get("cell_id", []))
        m["is_old_dsm_gap_false_positive_candidate"] = m["cell_id"].isin(fp_cells)
        old_top_fp = len(old_top & fp_cells)
        leaving_fp = len(set(leaving) & fp_cells)
        fp_summary = f"old_top{top_n}_false_positive_candidates={old_top_fp}; leaving_top{top_n}_false_positive_candidates={leaving_fp}"

    out_csv = out_dir / "v10_vs_v08_rank_comparison.csv"
    m.to_csv(out_csv, index=False)

    # Details for entering/leaving.
    detail = m[m["cell_id"].isin(sorted(old_top | new_top))].copy()
    detail["status"] = detail["cell_id"].apply(lambda c: "stayed" if c in old_top and c in new_top else ("entered_v10" if c in new_top else "left_v08"))
    detail_csv = out_dir / "v10_vs_v08_topset_details.csv"
    detail.sort_values(["status", new_rank]).to_csv(detail_csv, index=False)

    report = []
    report.append("# v10-gamma v08-v10 forecast ranking comparison\n")
    report.append(f"Metric: `{metric}`\n")
    report.append(f"Merged cells: **{len(m)}**\n")
    report.append(f"Clean compared cells: **{len(clean)}**\n")
    report.append(f"Spearman rank correlation: **{spearman:.4f}**\n")
    report.append(f"Top {top_n} overlap: **{len(old_top & new_top)} / {top_n}**\n")
    report.append(f"False-positive diagnostic: `{fp_summary}`\n")
    report.append("## Entering v10 top set\n")
    report.append(", ".join(entering) or "None")
    report.append("\n## Leaving v08 top set\n")
    report.append(", ".join(leaving) or "None")
    report.append("\n## Largest rank changes toward v10 top\n")
    report.append("```text")
    cols = ["cell_id", f"{metric}_v08", old_rank, f"{metric}_v10", new_rank, "rank_change_v08_minus_v10"]
    if "is_old_dsm_gap_false_positive_candidate" in m.columns:
        cols.append("is_old_dsm_gap_false_positive_candidate")
    report.append(m.sort_values("rank_change_v08_minus_v10", ascending=False)[cols].head(25).to_string(index=False))
    report.append("```\n")
    report.append("## Largest rank drops under v10\n")
    report.append("```text")
    report.append(m.sort_values("rank_change_v08_minus_v10", ascending=True)[cols].head(25).to_string(index=False))
    report.append("```\n")
    report.append("## Interpretation note\n")
    report.append("- This is the first reviewed-DSM forecast/ranking comparison using v10 UMEP morphology.\n")
    report.append("- If many old false-positive candidates leave the top set, this supports the v0.9 audit finding that old hazard ranking was affected by building-DSM coverage gaps.\n")
    report_path = out_dir / "v10_vs_v08_forecast_ranking_comparison.md"
    report_path.write_text("\n".join(report), encoding="utf-8")

    print(f"[OK] report: {report_path}")
    print(f"[OK] csv: {out_csv}")
    print(f"[OK] details: {detail_csv}")
    print(f"spearman: {spearman:.4f}")
    print(f"top{top_n}_overlap: {len(old_top & new_top)} / {top_n}")


if __name__ == "__main__":
    main()
