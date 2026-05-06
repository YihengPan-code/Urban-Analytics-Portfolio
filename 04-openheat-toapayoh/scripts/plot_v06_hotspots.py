from __future__ import annotations
from pathlib import Path
import sys
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]


def main():
    out_dir = ROOT / 'outputs'
    candidates = [out_dir / 'v06_offline_hotspot_ranking.csv', out_dir / 'v06_fallback_hotspot_ranking.csv', out_dir / 'sample_hotspot_ranking.csv']
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        raise FileNotFoundError('Run scripts/run_live_forecast_v06.py --mode sample first.')
    df = pd.read_csv(path).head(15)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(df['cell_id'][::-1], df['risk_priority_score'][::-1])
    ax.set_xlabel('Risk priority score')
    ax.set_ylabel('Grid cell')
    ax.set_title('OpenHeat v0.6.1 sample hotspot ranking')
    fig.tight_layout()
    out = out_dir / 'v06_1_offline_hotspot_preview.png'
    fig.savefig(out, dpi=200)
    print(out)

if __name__ == '__main__':
    main()
