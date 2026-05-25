"""Compare Core-8 v10-epsilon summaries with formal-hot-day QA summaries.

Inputs:
    - epsilon base `tmrt_cell_summary_long.csv`
    - epsilon overhead `tmrt_cell_summary_long.csv`
    - formal-hot-day `tmrt_cell_summary_long.csv`

Outputs:
    - row-level CSV with formal-minus-epsilon metric differences
    - short Markdown robustness diagnostic

This script only reads tabular SOLWEIG aggregation outputs. It does not import
QGIS, run SOLWEIG, or write raster outputs.

Example:
    python scripts/v12_solweig_compare_formal_hotday_vs_epsilon.py ^
      --epsilon-base outputs/v12_solweig_typology_pilot/core8_base_summary/tmrt_cell_summary_long.csv ^
      --epsilon-overhead outputs/v12_solweig_typology_pilot/core8_overhead_summary/tmrt_cell_summary_long.csv ^
      --formal-summary outputs/v12_solweig_typology_pilot/formal_hotday_smoke_summary/tmrt_cell_summary_long.csv ^
      --out-csv outputs/v12_solweig_typology_pilot/formal_hotday_smoke_summary/formal_vs_epsilon_comparison.csv ^
      --out-md outputs/v12_solweig_typology_pilot/formal_hotday_smoke_summary/formal_vs_epsilon_comparison.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
KEY_COLS = ["cell_id", "hour_sgt", "scenario_id"]
CANDIDATE_METRIC_COLS = [
    "n_valid_pixels",
    "valid_pixel_fraction",
    "tmrt_mean_c",
    "tmrt_p50_c",
    "tmrt_p75_c",
    "tmrt_p90_c",
    "tmrt_p95_c",
    "tmrt_max_c",
    "tmrt_min_c",
]
REQUIRED_METRIC_COLS = ["tmrt_mean_c", "tmrt_p90_c", "tmrt_max_c"]


def _project_path(path_text: str | Path) -> Path:
    """Resolve a path relative to the repository root unless it is absolute."""
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _read_summary(path: Path, label: str) -> pd.DataFrame:
    """Read a cell summary and keep comparable metric columns."""
    if not path.exists():
        raise FileNotFoundError(f"Missing {label} summary: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig")

    missing_keys = set(KEY_COLS) - set(df.columns)
    if missing_keys:
        raise ValueError(f"{path} missing key columns: {sorted(missing_keys)}")

    missing_metrics = [col for col in REQUIRED_METRIC_COLS if col not in df.columns]
    if missing_metrics:
        raise ValueError(f"{path} missing required metric columns: {missing_metrics}")

    metric_cols = [col for col in CANDIDATE_METRIC_COLS if col in df.columns]
    out = df[KEY_COLS + metric_cols].copy()
    out["cell_id"] = out["cell_id"].astype(str)
    out["scenario_id"] = out["scenario_id"].astype(str)
    out["hour_sgt"] = out["hour_sgt"].astype(int)
    return out


def _combine_epsilon(base_path: Path, overhead_path: Path) -> pd.DataFrame:
    """Combine base and overhead Core-8 summaries into one lookup table."""
    base = _read_summary(base_path, "epsilon base")
    overhead = _read_summary(overhead_path, "epsilon overhead")
    epsilon = pd.concat([base, overhead], ignore_index=True)
    return epsilon.drop_duplicates(subset=KEY_COLS, keep="first")


def compare(epsilon: pd.DataFrame, formal: pd.DataFrame) -> pd.DataFrame:
    """Return row-level formal-minus-epsilon differences where keys overlap."""
    metric_cols = [col for col in CANDIDATE_METRIC_COLS if col in formal.columns and col in epsilon.columns]
    merged = formal.merge(epsilon, on=KEY_COLS, how="left", suffixes=("_formal", "_epsilon"))
    for col in metric_cols:
        formal_col = f"{col}_formal"
        epsilon_col = f"{col}_epsilon"
        merged[f"delta_{col}_formal_minus_epsilon"] = merged[formal_col] - merged[epsilon_col]
    merged["epsilon_match_found"] = merged[[f"{col}_epsilon" for col in REQUIRED_METRIC_COLS]].notna().all(axis=1)
    return merged


def _markdown_table(df: pd.DataFrame) -> str:
    """Render a DataFrame as a Markdown table with a CSV fallback."""
    try:
        return df.to_markdown(index=False)
    except ImportError:
        return "```csv\n" + df.to_csv(index=False).strip() + "\n```"


def write_report(df: pd.DataFrame, out_md: Path) -> None:
    """Write a concise Markdown robustness diagnostic."""
    out_md.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# v12 formal-hot-day smoke vs v10-epsilon comparison",
        "",
        "This diagnostic compares existing Core-8 output against formal-hot-day QA output.",
        "It is a robustness check for SOLWEIG-derived Tmrt summaries.",
        "",
        "## Coverage",
        "",
        f"- rows compared: `{len(df)}`",
        f"- epsilon matches found: `{int(df['epsilon_match_found'].sum())}`",
        f"- cells: `{df['cell_id'].nunique()}`",
        f"- scenarios: `{', '.join(sorted(df['scenario_id'].dropna().astype(str).unique()))}`",
        "",
    ]

    delta_col = "delta_tmrt_p90_c_formal_minus_epsilon"
    if delta_col in df.columns:
        summary = (
            df.groupby(["cell_id", "scenario_id"], dropna=False)[delta_col]
            .agg(["count", "mean", "min", "max"])
            .reset_index()
            .round(3)
        )
        lines.extend(
            [
                "## Tmrt p90 difference",
                "",
                _markdown_table(summary),
                "",
            ]
        )

    mean_col = "delta_tmrt_mean_c_formal_minus_epsilon"
    if mean_col in df.columns:
        summary = (
            df.groupby(["cell_id", "scenario_id"], dropna=False)[mean_col]
            .agg(["count", "mean", "min", "max"])
            .reset_index()
            .round(3)
        )
        lines.extend(
            [
                "## Tmrt mean difference",
                "",
                _markdown_table(summary),
                "",
            ]
        )

    lines.extend(
        [
            "## Review notes",
            "",
            "- Compare direction, rank stability, and expected null or sensitivity roles.",
            "- If roles flip unexpectedly, audit forcing, masks, tile geometry, SVF, and aggregation before scaling.",
            "- Treat this as QA evidence for pre-scale design, not as an operational product.",
        ]
    )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--epsilon-base",
        default="outputs/v12_solweig_typology_pilot/core8_base_summary/tmrt_cell_summary_long.csv",
        help="Existing Core-8 base tmrt_cell_summary_long.csv.",
    )
    parser.add_argument(
        "--epsilon-overhead",
        default="outputs/v12_solweig_typology_pilot/core8_overhead_summary/tmrt_cell_summary_long.csv",
        help="Existing Core-8 overhead tmrt_cell_summary_long.csv.",
    )
    parser.add_argument("--formal-summary", required=True, help="Formal-hot-day tmrt_cell_summary_long.csv.")
    parser.add_argument("--out-csv", required=True, help="Output comparison CSV path.")
    parser.add_argument("--out-md", required=True, help="Output Markdown report path.")
    return parser.parse_args()


def main() -> None:
    """Run the comparison diagnostic."""
    args = parse_args()
    epsilon = _combine_epsilon(_project_path(args.epsilon_base), _project_path(args.epsilon_overhead))
    formal = _read_summary(_project_path(args.formal_summary), "formal-hot-day")
    compared = compare(epsilon=epsilon, formal=formal)

    out_csv = _project_path(args.out_csv)
    out_md = _project_path(args.out_md)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    compared.to_csv(out_csv, index=False, encoding="utf-8-sig")
    write_report(compared, out_md)
    print(f"[OK] wrote {out_csv}")
    print(f"[OK] wrote {out_md}")


if __name__ == "__main__":
    main()
