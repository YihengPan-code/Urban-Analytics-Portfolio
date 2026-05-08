from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import pandas as pd
from openheat_forecast.hotspot_engine import run_grid_forecast, summarize_hotspots


def test_run_grid_forecast_outputs_columns():
    root = Path(__file__).resolve().parents[1]
    f = pd.read_csv(root / 'data/sample/openmeteo_heatwave_forecast_sample.csv').head(3)
    g = pd.read_csv(root / 'data/sample/toa_payoh_grid_sample.csv').head(2)
    out = run_grid_forecast(f, g)
    assert {'utci_c', 'wbgt_proxy_c', 'wbgt_category_sg'}.issubset(out.columns)
    assert len(out) == 6


def test_hotspot_summary_ranks():
    root = Path(__file__).resolve().parents[1]
    f = pd.read_csv(root / 'data/sample/openmeteo_heatwave_forecast_sample.csv').head(6)
    g = pd.read_csv(root / 'data/sample/toa_payoh_grid_sample.csv').head(5)
    out = summarize_hotspots(run_grid_forecast(f, g))
    assert out['rank'].is_monotonic_increasing
    assert out['risk_priority_score'].between(0, 1).all()
