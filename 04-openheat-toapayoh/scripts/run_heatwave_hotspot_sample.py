from pathlib import Path
import sys
import pandas as pd

# allow running without package installation
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from openheat_forecast.data_sources import load_sample_forecast, load_sample_grid
from openheat_forecast.hotspot_engine import run_grid_forecast, summarize_hotspots, detect_event_windows

forecast = load_sample_forecast(ROOT / 'data/sample/openmeteo_heatwave_forecast_sample.csv')
grid = load_sample_grid(ROOT / 'data/sample/toa_payoh_grid_sample.csv')

grid_forecast = run_grid_forecast(forecast, grid)
hotspots = summarize_hotspots(grid_forecast)
events = detect_event_windows(grid_forecast)

out = ROOT / 'outputs'
out.mkdir(exist_ok=True)
grid_forecast.to_csv(out / 'sample_hourly_grid_heatstress_forecast.csv', index=False)
hotspots.to_csv(out / 'sample_hotspot_ranking.csv', index=False)
events.to_csv(out / 'sample_event_windows.csv', index=False)

print('Wrote:')
print(out / 'sample_hourly_grid_heatstress_forecast.csv')
print(out / 'sample_hotspot_ranking.csv')
print(out / 'sample_event_windows.csv')
print('\nTop 10 hotspot cells:')
print(hotspots[['rank','cell_id','max_wbgt_proxy_c','moderate_wbgt_hours','high_wbgt_hours','max_utci_c','risk_priority_score','gvi_percent','shade_fraction','building_density']].head(10).to_string(index=False))
