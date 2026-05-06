from pathlib import Path
import json
import pandas as pd

from openheat_forecast.live_api import normalise_realtime_station_readings, attach_nearest_station

ROOT = Path(__file__).resolve().parents[1]


def test_current_v2_wbgt_records_item_readings_schema():
    payload = json.loads((ROOT / 'data/fixtures/nea_wbgt_v2_current_schema_sample.json').read_text())
    df = normalise_realtime_station_readings(payload, 'official_wbgt_c')

    assert len(df) == 27
    assert {'station_id', 'station_name', 'station_town_center', 'station_lat', 'station_lon', 'official_wbgt_c', 'heat_stress_category'}.issubset(df.columns)

    bishan = df.loc[df['station_id'] == 'S128'].iloc[0]
    assert bishan['station_name'] == 'Bishan Street'
    assert bishan['station_town_center'] == 'Bishan Stadium'
    assert abs(float(bishan['station_lat']) - 1.354825) < 1e-6
    assert abs(float(bishan['station_lon']) - 103.852219) < 1e-6
    assert abs(float(bishan['official_wbgt_c']) - 30.6) < 1e-6
    assert bishan['heat_stress_category'] == 'Low'


def test_current_v2_wbgt_nearest_station_for_toa_payoh_sample_grid():
    payload = json.loads((ROOT / 'data/fixtures/nea_wbgt_v2_current_schema_sample.json').read_text())
    stations = normalise_realtime_station_readings(payload, 'official_wbgt_c')
    grid = pd.read_csv(ROOT / 'data/sample/toa_payoh_grid_sample.csv')
    nearest = attach_nearest_station(grid, stations)

    assert 'nearest_station_id' in nearest.columns
    assert nearest['nearest_station_id'].notna().all()
    # For the bundled Toa Payoh sample grid, the nearest-station assignment should now work.
    # Most cells use Bishan Stadium, while edge cells may be closer to MacRitchie/Kallang.
    assert 'S128' in set(nearest['nearest_station_id'].unique())
    assert nearest['nearest_station_distance_m'].notna().all()
    assert nearest['station_representativeness'].isin({'nearby_proxy', 'regional_proxy', 'local'}).all()
