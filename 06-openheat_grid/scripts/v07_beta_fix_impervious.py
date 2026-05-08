import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--in-grid",
        default="data/grid/toa_payoh_grid_v07_features_beta_gee.csv",
        help="Input v0.7-beta grid feature CSV."
    )
    parser.add_argument(
        "--out-grid",
        default="data/grid/toa_payoh_grid_v07_features_beta_gee_impervfix.csv",
        help="Output grid feature CSV with revised impervious_fraction."
    )
    parser.add_argument("--vector-weight", type=float, default=0.50)
    parser.add_argument("--dw-weight", type=float, default=0.50)
    parser.add_argument("--green-coef", type=float, default=0.50)
    parser.add_argument("--water-coef", type=float, default=0.75)
    args = parser.parse_args()

    in_path = Path(args.in_grid)
    out_path = Path(args.out_grid)

    df = pd.read_csv(in_path)

    required = [
        "building_density",
        "road_fraction",
        "built_up_fraction",
        "water_fraction",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    bd = df["building_density"].fillna(0).clip(0, 1)
    road = df["road_fraction"].fillna(0).clip(0, 1)
    built_dw = df["built_up_fraction"].fillna(0).clip(0, 1)
    water = df["water_fraction"].fillna(0).clip(0, 1)

    if "greenery_fraction_beta" in df.columns:
        green = df["greenery_fraction_beta"].fillna(0).clip(0, 1)
    else:
        tree = df.get("tree_canopy_fraction", pd.Series(0, index=df.index)).fillna(0).clip(0, 1)
        grass = df.get("grass_fraction", pd.Series(0, index=df.index)).fillna(0).clip(0, 1)
        ndvi = df.get("ndvi_mean", pd.Series(0, index=df.index)).fillna(0).clip(0, 1)
        green = np.maximum.reduce([tree.to_numpy(), grass.to_numpy(), ndvi.to_numpy()])
        green = pd.Series(green, index=df.index).clip(0, 1)

    vector_imperv = (bd + road).clip(0, 1)

    old = df["impervious_fraction"].copy() if "impervious_fraction" in df.columns else pd.Series(np.nan, index=df.index)

    revised = (
        args.vector_weight * vector_imperv
        + args.dw_weight * built_dw
        - args.green_coef * green
        - args.water_coef * water
    ).clip(0, 1)

    df["impervious_fraction_old_beta"] = old
    df["impervious_fraction_vector_component"] = vector_imperv
    df["impervious_fraction_dw_component"] = built_dw
    df["impervious_fraction_green_component"] = green
    df["impervious_fraction"] = revised

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    print("[OK] Wrote:", out_path)
    print("\nOld impervious_fraction:")
    print(old.describe().to_string())
    print("\nRevised impervious_fraction:")
    print(df["impervious_fraction"].describe().to_string())
    print("\nDiagnostics:")
    print("share old >= 0.95:", float((old >= 0.95).mean()))
    print("share revised >= 0.95:", float((df["impervious_fraction"] >= 0.95).mean()))
    print("share revised <= 0.05:", float((df["impervious_fraction"] <= 0.05).mean()))


if __name__ == "__main__":
    main()