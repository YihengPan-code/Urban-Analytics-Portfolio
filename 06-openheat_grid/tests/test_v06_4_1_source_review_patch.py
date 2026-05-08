from pathlib import Path
import json
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from openheat_forecast.live_api import fetch_official_wbgt
from openheat_forecast.thermal_indices import estimate_local_microclimate
from openheat_forecast.live_pipeline import filter_wbgt_station_observations, attach_nearest_nea_stations_to_grid
from openheat_forecast.calibration import make_paired_wbgt_table

ROOT = Path(__file__).resolve().parents[1]


def test_fetch_official_wbgt_forces_v2_even_if_caller_passes_v1(monkeypatch):
    calls = {}

    def fake_fetch(api, **kwargs):
        calls["api"] = api
        calls.update(kwargs)
        payload = json.loads((ROOT / "data/fixtures/nea_wbgt_v2_current_schema_sample.json").read_text())
        payload["_openheat_api_name"] = api
        payload["_openheat_api_version"] = kwargs.get("api_version")
        return payload

    monkeypatch.setattr("openheat_forecast.live_api.fetch_datagov_realtime_api", fake_fetch)
    df = fetch_official_wbgt(api_version="v1")
    assert calls["api"] == "wbgt"
    assert calls["api_version"] == "v2"
    assert "official_wbgt_c" in df.columns
    assert len(df) == 27


def test_microclimate_review_coefficients_wind_cap_gvi60_park_exp_and_wall_lw():
    forecast = pd.DataFrame({
        "time": ["2026-05-06 12:00"],
        "temperature_2m": [32.0],
        "relative_humidity_2m": [70.0],
        "wind_speed_10m_ms": [2.0],
        "shortwave_radiation": [800.0],
    })
    grid = pd.DataFrame({
        "cell_id": ["open", "canyon"],
        "lat": [1.33, 1.331],
        "lon": [103.85, 103.851],
        "building_density": [0.0, 0.8],
        "road_fraction": [0.2, 0.8],
        "gvi_percent": [60.0, 30.0],
        "park_distance_m": [0.0, 500.0],
        "svf": [1.0, 0.2],
        "shade_fraction": [0.0, 0.2],
    })
    out = estimate_local_microclimate(forecast, grid)
    assert (out["wind_local_ms"] <= out["wind_speed_10m_ms"] + 1e-12).all()
    assert out.loc[out.cell_id == "open", "gvi_norm_for_screening"].iloc[0] == 1.0
    assert out.loc[out.cell_id == "canyon", "gvi_norm_for_screening"].iloc[0] == 0.5
    assert out.loc[out.cell_id == "open", "park_cooling_exp250"].iloc[0] > out.loc[out.cell_id == "canyon", "park_cooling_exp250"].iloc[0]
    assert out.loc[out.cell_id == "canyon", "tmrt_wall_longwave_gain_c"].iloc[0] > 0


def test_nearest_station_matching_filters_to_wbgt_only(tmp_path):
    grid = pd.DataFrame({"cell_id": ["A"], "lat": [1.0], "lon": [1.0]})
    grid_csv = tmp_path / "grid.csv"
    grid.to_csv(grid_csv, index=False)
    obs = pd.DataFrame({
        "variable": ["air_temperature_c", "official_wbgt_c"],
        "value": [30.0, 31.0],
        "station_id": ["AIR_NEAR", "WBGT_FAR"],
        "station_name": ["near air temp", "far wbgt"],
        "station_lat": [1.0001, 1.01],
        "station_lon": [1.0001, 1.01],
    })
    wbgt = filter_wbgt_station_observations(obs)
    assert wbgt["station_id"].tolist() == ["WBGT_FAR"]
    nearest = attach_nearest_nea_stations_to_grid(grid_csv, obs)
    assert nearest.loc[0, "nearest_station_id"] == "WBGT_FAR"


def test_make_paired_wbgt_table_accepts_long_archive_and_nearest_station_id():
    pred = pd.DataFrame({
        "time": ["2026-05-06T09:45:00+08:00"],
        "nearest_station_id": ["S128"],
        "wbgt_proxy_c": [30.0],
    })
    obs = pd.DataFrame({
        "variable": ["official_wbgt_c", "air_temperature_c"],
        "value": [30.6, 31.0],
        "timestamp": ["2026-05-06T09:45:00+08:00", "2026-05-06T09:45:00+08:00"],
        "station_id": ["S128", "S128"],
    })
    paired = make_paired_wbgt_table(pred, obs)
    assert len(paired) == 1
    assert abs(float(paired.loc[0, "official_wbgt_c"]) - 30.6) < 1e-9
