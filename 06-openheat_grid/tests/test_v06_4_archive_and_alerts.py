from pathlib import Path
import json
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from openheat_forecast.hotspot_engine import run_grid_forecast, summarize_hotspots, detect_event_windows
from openheat_forecast.live_api import normalise_realtime_station_readings
from openheat_forecast.live_pipeline import station_observations_to_long

ROOT = Path(__file__).resolve().parents[1]


def test_v06_4_event_windows_have_separate_alerts():
    forecast = pd.read_csv(ROOT / "data/sample/openmeteo_heatwave_forecast_sample.csv").head(12)
    grid = pd.read_csv(ROOT / "data/sample/toa_payoh_grid_sample.csv").head(6)
    hourly = run_grid_forecast(forecast, grid)
    events = detect_event_windows(hourly)
    assert {"wbgt_alert", "utci_alert", "combined_alert", "neighbourhood_alert", "p90_utci_c"}.issubset(events.columns)
    assert events["wbgt_alert"].isin({"low", "moderate", "high"}).all()
    assert events["utci_alert"].isin({"low", "moderate", "strong", "very_strong", "extreme"}).all()
    assert events["combined_alert"].isin({"low", "watch", "elevated", "high"}).all()


def test_v06_4_hotspot_hazard_score_is_continuous_not_constant():
    forecast = pd.read_csv(ROOT / "data/sample/openmeteo_heatwave_forecast_sample.csv").head(24)
    grid = pd.read_csv(ROOT / "data/sample/toa_payoh_grid_sample.csv").head(20)
    ranking = summarize_hotspots(run_grid_forecast(forecast, grid))
    assert {"hazard_utci_intensity_score", "hazard_utci_relative_score", "hazard_wbgt_intensity_score", "peak_utci_category", "peak_wbgt_category_sg"}.issubset(ranking.columns)
    assert ranking["hazard_score"].between(0, 1).all()
    # The old v0.6.3 score could be identical across cells on non-WBGT days.
    assert ranking["hazard_score"].nunique() > 1


def test_v06_4_wbgt_station_observations_archive_long_format_preserves_metadata():
    payload = json.loads((ROOT / "data/fixtures/nea_wbgt_v2_current_schema_sample.json").read_text())
    wbgt = normalise_realtime_station_readings(payload, "official_wbgt_c")
    long = station_observations_to_long(wbgt, variable="official_wbgt_c", value_col="official_wbgt_c", unit="deg C")
    assert len(long) == 27
    assert {"variable", "value", "unit", "timestamp", "station_id", "station_name", "station_lat", "station_lon", "heat_stress_category"}.issubset(long.columns)
    bishan = long.loc[long["station_id"] == "S128"].iloc[0]
    assert bishan["variable"] == "official_wbgt_c"
    assert abs(float(bishan["value"]) - 30.6) < 1e-6
    assert bishan["station_name"] == "Bishan Street"
    assert abs(float(bishan["station_lat"]) - 1.354825) < 1e-6
    assert pd.notna(bishan["timestamp"])
