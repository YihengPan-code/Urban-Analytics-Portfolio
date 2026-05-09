from pathlib import Path
import pandas as pd


IN_CSV = Path("outputs/v08_umep_with_veg_forecast_live/v08_umep_with_veg_hotspot_ranking_with_grid_features.csv")
OUT_CSV = Path("outputs/v08_umep_with_veg_forecast_live/v08_risk_hotspot_ranking_conditioned.csv")


def main():
    if not IN_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {IN_CSV}")

    df = pd.read_csv(IN_CSV)

    required = ["cell_id", "hazard_score", "max_utci_c"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")

    # True physical heat-hazard ranks
    df["hazard_rank_true_v08"] = (
        df["hazard_score"].rank(method="min", ascending=False).astype(int)
    )
    df["utci_rank_true_v08"] = (
        df["max_utci_c"].rank(method="min", ascending=False).astype(int)
    )

    # Use v0.7.1 vulnerability/exposure if present.
    # If missing, fall back to zero so the script can still run.
    if "vulnerability_score_v071" in df.columns:
        vulnerability = df["vulnerability_score_v071"].fillna(0).clip(0, 1)
    else:
        print("[WARN] vulnerability_score_v071 missing; using 0.")
        vulnerability = 0

    if "outdoor_exposure_score_v071" in df.columns:
        exposure = df["outdoor_exposure_score_v071"].fillna(0).clip(0, 1)
    else:
        print("[WARN] outdoor_exposure_score_v071 missing; using 0.")
        exposure = 0

    # Hazard-conditioned candidate gate:
    # Only the top 25% hazard cells receive full vulnerability/exposure amplification.
    hazard_p75 = df["hazard_score"].quantile(0.75)
    df["hazard_candidate_p75_v08"] = df["hazard_score"] >= hazard_p75

    # Main v0.8 conditioned risk score:
    # heat hazard remains dominant; vulnerability and exposure amplify hazard.
    df["risk_priority_score_v08_conditioned"] = (
        0.75 * df["hazard_score"]
        + 0.15 * (df["hazard_score"] * vulnerability)
        + 0.10 * (df["hazard_score"] * exposure)
    )

    # Non-candidate cells are not allowed to jump into top risk ranking
    # purely because of social/exposure proxy.
    non_candidate = ~df["hazard_candidate_p75_v08"]
    df.loc[non_candidate, "risk_priority_score_v08_conditioned"] = (
        0.50 * df.loc[non_candidate, "hazard_score"]
    )

    df["risk_rank_v08_conditioned"] = (
        df["risk_priority_score_v08_conditioned"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)

    print("[OK] Wrote:", OUT_CSV)
    print("hazard_score p75:", round(hazard_p75, 4))

    cols = [
        "risk_rank_v08_conditioned",
        "cell_id",
        "hazard_rank_true_v08",
        "max_utci_c",
        "hazard_score",
        "risk_priority_score_v08_conditioned",
        "vulnerability_score_v071",
        "outdoor_exposure_score_v071",
    ]
    cols = [c for c in cols if c in df.columns]

    print("\nTop 25 v0.8 conditioned risk cells:")
    print(
        df.sort_values("risk_rank_v08_conditioned")[cols]
        .head(25)
        .to_string(index=False)
    )

    h = set(df.nsmallest(20, "hazard_rank_true_v08")["cell_id"])
    r = set(df.nsmallest(20, "risk_rank_v08_conditioned")["cell_id"])

    print("\nTop20 overlap v08 hazard vs v08 conditioned risk:", len(h & r), "/ 20")
    print("risk-only cells:", sorted(r - h))
    print("hazard-only cells:", sorted(h - r))

    top = df.nsmallest(20, "risk_rank_v08_conditioned")
    print("\nRisk top20 UTCI min/mean/max:",
          round(top["max_utci_c"].min(), 2),
          round(top["max_utci_c"].mean(), 2),
          round(top["max_utci_c"].max(), 2))
    print("Risk top20 hazard min/mean/max:",
          round(top["hazard_score"].min(), 3),
          round(top["hazard_score"].mean(), 3),
          round(top["hazard_score"].max(), 3))


if __name__ == "__main__":
    main()