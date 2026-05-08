from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print("\n$ " + " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run v0.7.1 risk/exposure feature + ranking pipeline")
    parser.add_argument("--config", default="configs/v071_risk_exposure_config.example.json")
    parser.add_argument("--download", action="store_true", help="Download raw datasets before building features")
    parser.add_argument("--forecast-dir", default=None, help="Forecast output directory containing v06_live_hotspot_ranking.csv")
    args = parser.parse_args()

    py = sys.executable
    if args.download:
        run([py, "scripts/v071_download_risk_exposure_data.py"])
    run([py, "scripts/v071_build_risk_exposure_features.py", "--config", args.config])
    apply_cmd = [py, "scripts/v071_apply_risk_to_forecast.py", "--config", args.config]
    if args.forecast_dir:
        apply_cmd += ["--forecast-dir", args.forecast_dir]
    run(apply_cmd)
    print("\n[OK] v0.7.1 full risk/exposure pipeline completed")


if __name__ == "__main__":
    main()
