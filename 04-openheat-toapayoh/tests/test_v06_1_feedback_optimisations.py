from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import pandas as pd

from openheat_forecast.live_api import (
    normalise_realtime_station_readings,
    attach_nearest_station,
    fetch_openmeteo_forecast_multi,
    Location,
)
from openheat_forecast.calibration import make_paired_wbgt_table, calibration_readiness_check
from openheat_forecast.time_utils import to_singapore_timestamp

ROOT = Path(__file__).resolve().parents[1]


def test_v1_normaliser_handles_nulls_and_metadata():
    payload = json.loads((ROOT / 'data/fixtures/nea_wbgt_v1_sample.json').read_text())
    df = normalise_realtime_station_readings(payload, 'official_wbgt_c')
    assert len(df) == 3
    assert df['api_version'].iloc[0] == 'v1'
    assert 'fetch_timestamp_utc' in df.columns
    assert df['official_wbgt_c'].isna().sum() == 1
    assert df['value_missing'].sum() == 1
    assert str(df['timestamp'].iloc[0].tzinfo) in {'Asia/Singapore', 'UTC+08:00', 'pytz.FixedOffset(480)'}


def test_timezone_pairing_treats_openmeteo_naive_as_sgt():
    pred = pd.DataFrame({
        'station_id': ['S43'],
        'time': ['2026-05-05T15:45:00'],  # Open-Meteo local clock string
        'wbgt_proxy_c': [30.5],
    })
    obs = pd.DataFrame({
        'station_id': ['S43'],
        'timestamp': ['2026-05-05T15:45:00+08:00'],
        'official_wbgt_c': [31.0],
    })
    paired = make_paired_wbgt_table(pred, obs)
    assert len(paired) == 1
    assert paired.loc[0, 'official_wbgt_c'] == 31.0


def test_nearest_station_representativeness_flag():
    payload = json.loads((ROOT / 'data/fixtures/nea_wbgt_v1_sample.json').read_text())
    stations = normalise_realtime_station_readings(payload, 'official_wbgt_c')
    points = pd.DataFrame({'cell_id': ['toa_payoh'], 'lat': [1.3343], 'lon': [103.8563]})
    out = attach_nearest_station(points, stations)
    assert out.loc[0, 'nearest_station_distance_m'] > 0
    assert out.loc[0, 'station_representativeness'] in {'nearby_proxy', 'regional_proxy'}


def test_calibration_readiness_requires_event_diversity():
    df = pd.DataFrame({
        'station_id': ['S1'] * 30,
        'time': pd.date_range('2026-05-01 10:00', periods=30, freq='H'),
        'official_wbgt_c': [30.0] * 30,
    })
    chk = calibration_readiness_check(df)
    assert chk['paired_observations'] == 30
    assert chk['has_moderate_wbgt_31plus'] is False
    assert 'Not enough event diversity' in chk['recommendation']
