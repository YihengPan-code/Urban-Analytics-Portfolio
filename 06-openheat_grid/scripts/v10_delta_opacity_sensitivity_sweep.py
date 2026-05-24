"""v10-delta opacity sensitivity sweep.

This script tests how sensitive the v10-delta overhead shade sensitivity is
to the chosen `type_opacity` prior. It does NOT rerun the forecast or hazard
engine — it only varies the opacity assumptions, recomputes the cell-level
overhead_shade_proxy and shade_fraction_overhead_sens, and reports how much
the resulting shade fraction (and its delta from base) varies across
scenarios.

Why this matters
----------------
The default v10-delta config uses prior opacity values that are not backed
by empirical measurements:
    covered_walkway: 0.90, station_canopy: 0.95, elevated_road: 0.75, ...
A dissertation reviewer will ask "how robust is the conclusion to these
priors?". This script gives a quantitative answer: it sweeps over five
scenarios — `low`, `default`, `high`, `pedestrian_strong`, `transport_strong` —
and reports per-scenario summary statistics plus a focused table of the
cells you specifically care about (the v10-gamma "stubborn" candidates +
"entering" cells).

Output
------
- per_scenario_summary.csv: stats per scenario (mean / std of shade_new and
                            delta, top/bottom cells)
- focus_cells_sweep.csv:    14 focus cells (configurable) × 5 scenarios,
                            showing how their shade_new varies
- opacity_sweep_report.md:  human-readable summary

Note: this script does NOT change the canonical apply_overhead_sensitivity
output. Run it as a side-channel diagnostic AFTER the main v10-delta
pipeline.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


# Five scenarios. Default mirrors the patch config; others perturb priors.
SCENARIOS: Dict[str, Dict[str, float]] = {
    "low_opacity": {
        "covered_walkway": 0.70,
        "pedestrian_bridge": 0.60,
        "station_canopy": 0.75,
        "elevated_rail": 0.60,
        "elevated_road": 0.55,
        "viaduct": 0.55,
        "unknown_overhead": 0.40,
    },
    "default": {  # matches v10_delta_overhead_config.example.json
        "covered_walkway": 0.90,
        "pedestrian_bridge": 0.80,
        "station_canopy": 0.95,
        "elevated_rail": 0.80,
        "elevated_road": 0.75,
        "viaduct": 0.75,
        "unknown_overhead": 0.60,
    },
    "high_opacity": {
        "covered_walkway": 0.98,
        "pedestrian_bridge": 0.95,
        "station_canopy": 1.00,
        "elevated_rail": 0.95,
        "elevated_road": 0.90,
        "viaduct": 0.90,
        "unknown_overhead": 0.80,
    },
    "pedestrian_strong": {
        # If we believe pedestrian shelters are nearly opaque but transport
        # decks are partial (gaps between rails, openings between road pillars).
        "covered_walkway": 0.98,
        "pedestrian_bridge": 0.95,
        "station_canopy": 1.00,
        "elevated_rail": 0.65,
        "elevated_road": 0.60,
        "viaduct": 0.60,
        "unknown_overhead": 0.60,
    },
    "transport_strong": {
        # Inverse: if transport decks have continuous concrete underside but
        # walkways are translucent / gappy.
        "covered_walkway": 0.65,
        "pedestrian_bridge": 0.55,
        "station_canopy": 0.70,
        "elevated_rail": 0.95,
        "elevated_road": 0.95,
        "viaduct": 0.95,
        "unknown_overhead": 0.60,
    },
}


# v10-gamma stubborn FP candidates + entering cells. Edit if your set differs.
DEFAULT_FOCUS_CELLS: List[str] = [
    # Remaining FP (still high in v10-gamma)
    "TP_0564", "TP_0565", "TP_0986",
    # Entering v10 top20
    "TP_0120", "TP_0171", "TP_0315", "TP_0344", "TP_0373",
    "TP_0572", "TP_0766", "TP_0888", "TP_0916", "TP_0973",
    # TP_0945 fully-built degenerate case — useful sanity check
    "TP_0945",
]


def read_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def recompute_proxy(per_cell: pd.DataFrame, opacity_map: Dict[str, float]) -> pd.Series:
    """Recompute overhead_shade_proxy (cell-area scope) for a given opacity map.

    Reads per-type intersection area columns: overhead_area_<type>_m2,
    weights by the scenario's opacity, divides by cell_area_m2.
    """
    weighted_area = pd.Series(0.0, index=per_cell.index)
    for t, op in opacity_map.items():
        col = f"overhead_area_{t}_m2"
        if col in per_cell.columns:
            weighted_area = weighted_area + pd.to_numeric(per_cell[col], errors="coerce").fillna(0) * float(op)
    cell_area = pd.to_numeric(per_cell["cell_area_m2"], errors="coerce").fillna(1.0).clip(lower=1.0)
    return (weighted_area / cell_area).clip(0, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v10/v10_delta_overhead_config.example.json")
    ap.add_argument("--focus-cells", default=None,
                    help="Comma-separated list of cell_ids to track per scenario. "
                            "Default: 13 v10-gamma stubborn/entering cells + TP_0945.")
    ap.add_argument(
        "--out-dir", default="outputs/v10_overhead_qa",
        help="Where to write per_scenario_summary, focus_cells_sweep, sweep report.",
    )
    args = ap.parse_args()

    cfg = read_json(Path(args.config))
    inp = cfg["inputs"]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    per_cell_path = Path(cfg["outputs"]["overhead_per_cell_csv"])
    grid_path = Path(inp["v10_grid_csv"])
    if not per_cell_path.exists():
        raise FileNotFoundError(
            f"overhead per-cell CSV not found: {per_cell_path}. "
            "Run v10_delta_cell_overhead_metrics.py first."
        )
    if not grid_path.exists():
        raise FileNotFoundError(grid_path)

    per_cell = pd.read_csv(per_cell_path)
    grid = pd.read_csv(grid_path)
    if "cell_id" not in per_cell.columns or "cell_id" not in grid.columns:
        raise KeyError("Both per-cell and grid CSVs must contain cell_id")

    base_shade_col = cfg.get("sensitivity", {}).get("base_shade_column", "shade_fraction")
    if base_shade_col not in grid.columns:
        raise KeyError(f"Base shade column not found in grid: {base_shade_col}")

    open_frac_col = "open_pixel_fraction_v10"
    has_open_frac = open_frac_col in grid.columns

    base_shade = pd.to_numeric(grid[base_shade_col], errors="coerce").fillna(0).clip(0, 1)
    if has_open_frac:
        open_frac = pd.to_numeric(grid[open_frac_col], errors="coerce").fillna(1.0).clip(0.01, 1.0)
    else:
        print(f"[WARN] {open_frac_col} not in grid. Using cell-scope proxy directly.")
        open_frac = pd.Series(1.0, index=grid.index)

    # Focus cells.
    if args.focus_cells:
        focus = [c.strip() for c in args.focus_cells.split(",") if c.strip()]
    else:
        focus = DEFAULT_FOCUS_CELLS
    print(f"[INFO] tracking {len(focus)} focus cells across {len(SCENARIOS)} scenarios")

    # Per-scenario aggregate stats.
    summary_rows: List[Dict[str, Any]] = []
    # Wide table: cell_id, base_shade, then one shade_new column per scenario.
    focus_cell_table = grid[grid["cell_id"].isin(focus)][["cell_id"]].copy()
    focus_cell_table = focus_cell_table.merge(
        grid[["cell_id", base_shade_col, open_frac_col] if has_open_frac else ["cell_id", base_shade_col]],
        on="cell_id", how="left",
    )
    focus_cell_table = focus_cell_table.rename(columns={base_shade_col: "shade_base"})

    for scenario_name, opacity_map in SCENARIOS.items():
        proxy_cell = recompute_proxy(per_cell, opacity_map)
        merged = grid[["cell_id"]].merge(
            pd.DataFrame({"cell_id": per_cell["cell_id"], "proxy_cell": proxy_cell.values}),
            on="cell_id", how="left",
        )
        proxy_cell_full = pd.to_numeric(merged["proxy_cell"], errors="coerce").fillna(0).clip(0, 1)
        proxy_open = (proxy_cell_full / open_frac).clip(0, 1)
        shade_new = (1.0 - (1.0 - base_shade) * (1.0 - proxy_open)).clip(0, 1)
        delta = shade_new - base_shade

        summary_rows.append({
            "scenario": scenario_name,
            "shade_new_mean": float(shade_new.mean()),
            "shade_new_std": float(shade_new.std()),
            "delta_mean": float(delta.mean()),
            "delta_std": float(delta.std()),
            "delta_max": float(delta.max()),
            "delta_p95": float(delta.quantile(0.95)),
            "n_cells_with_delta_gt_0p05": int((delta > 0.05).sum()),
            "n_cells_with_delta_gt_0p10": int((delta > 0.10).sum()),
        })

        # Add focus-cell shade_new for this scenario.
        focus_lookup = pd.DataFrame({
            "cell_id": grid["cell_id"],
            f"shade_new__{scenario_name}": shade_new.values,
            f"delta__{scenario_name}": delta.values,
        })
        focus_cell_table = focus_cell_table.merge(focus_lookup, on="cell_id", how="left")

    summary_df = pd.DataFrame(summary_rows)
    summary_path = out_dir / "v10_opacity_sweep_per_scenario_summary.csv"
    summary_df.to_csv(summary_path, index=False)

    focus_path = out_dir / "v10_opacity_sweep_focus_cells.csv"
    focus_cell_table.to_csv(focus_path, index=False)

    # Volatility per focus cell: how much does shade_new range across scenarios?
    shade_new_cols = [c for c in focus_cell_table.columns if c.startswith("shade_new__")]
    if shade_new_cols:
        focus_cell_table["shade_new_range"] = (
            focus_cell_table[shade_new_cols].max(axis=1)
            - focus_cell_table[shade_new_cols].min(axis=1)
        )

    # Report.
    report_path = out_dir / "v10_opacity_sensitivity_sweep_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# v10-delta opacity sensitivity sweep report\n\n")
        f.write("This sweep tests robustness of the v10-delta overhead shade "
                "sensitivity to the prior `type_opacity` values.\n\n")
        f.write("## Scenarios\n\n")
        for name, om in SCENARIOS.items():
            f.write(f"### `{name}`\n\n```text\n")
            for t, v in om.items():
                f.write(f"{t:24s} {v:.2f}\n")
            f.write("```\n\n")
        f.write("## Per-scenario aggregate stats\n\n```text\n")
        f.write(summary_df.to_string(index=False))
        f.write("\n```\n\n")
        f.write("## Focus cells across scenarios\n\n")
        f.write(f"Tracking {len(focus_cell_table)} cells (of {len(focus)} requested):\n\n")
        f.write("```text\n")
        f.write(focus_cell_table.to_string(index=False))
        f.write("\n```\n\n")
        f.write("## How to read this\n\n")
        f.write("- If `shade_new` for a focus cell varies by < 0.05 across all five "
                "scenarios, the sensitivity result for that cell is robust to opacity prior.\n")
        f.write("- If `shade_new_range` > 0.15 for a cell, the prior is a critical "
                "assumption for that cell — call this out as a limitation in dissertation.\n")
        f.write("- If `n_cells_with_delta_gt_0p10` differs by an order of magnitude "
                "between `low_opacity` and `high_opacity`, the overall fraction-affected "
                "claim is opacity-dependent.\n")
        f.write("- The `pedestrian_strong` vs `transport_strong` contrast tells you "
                "whether the v10-gamma stubborn cells move based on pedestrian or "
                "transport overhead — useful for the dual-interpretation framing.\n")

    print(f"[OK] per-scenario summary: {summary_path}")
    print(f"[OK] focus cells sweep:    {focus_path}")
    print(f"[OK] sweep report:         {report_path}")


if __name__ == "__main__":
    main()
