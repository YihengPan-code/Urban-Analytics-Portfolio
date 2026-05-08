from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import pandas as pd

from openheat_forecast.live_api import normalise_realtime_station_readings, attach_nearest_station
from openheat_forecast.calibration import fit_linear_calibration, apply_linear_calibration, station_skill_metrics

ROOT = Path(__file__).resolve().parents[1]


def test_normalise_realtime_station_readings_fixture():
    payload = json.loads((ROOT / 'data/fixtures/nea_wbgt_sample.json').read_text())
    df = normalise_realtime_station_readings(payload, 'official_wbgt_c')
    assert len(df) == 3
    assert {'station_id', 'station_lat', 'station_lon', 'official_wbgt_c'}.issubset(df.columns)
    assert df['official_wbgt_c'].between(25, 40).all()


def test_attach_nearest_station_fixture():
    payload = json.loads((ROOT / 'data/fixtures/nea_wbgt_sample.json').read_text())
    stations = normalise_realtime_station_readings(payload, 'official_wbgt_c')
    points = pd.DataFrame({'cell_id': ['x'], 'lat': [1.3343], 'lon': [103.8563]})
    out = attach_nearest_station(points, stations)
    assert out.loc[0, 'nearest_station_id'] in {'S109', 'S111', 'S43'}
    assert out.loc[0, 'nearest_station_distance_m'] > 0


def test_linear_calibration_reduces_or_equal_error():
    df = pd.DataFrame({
        'station_id': ['a','b','c','d','e'],
        'wbgt_proxy_c': [29.5, 30.5, 31.5, 32.5, 33.5],
        'official_wbgt_c': [30.0, 31.0, 32.0, 33.0, 34.0],
    })
    model = fit_linear_calibration(df)
    out = apply_linear_calibration(df, model)
    assert model.n == 5
    assert model.rmse_after <= model.rmse_before + 1e-9
    skill = station_skill_metrics(out, 'wbgt_calibrated_c', 'official_wbgt_c')
    assert skill.loc[0, 'mae'] < 1e-6
