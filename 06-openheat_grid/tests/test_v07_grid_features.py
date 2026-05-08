from pathlib import Path
import sys
import importlib.util
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

spec = importlib.util.spec_from_file_location("v07_build_grid_features", ROOT / "scripts" / "v07_build_grid_features.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_v07_grid_features_sample_fixture_runs(tmp_path):
    cfg = mod.load_config(ROOT / "configs/v07_grid_features_config.sample_fixture.json")
    cfg["out_grid_dir"] = str(tmp_path / "grid")
    cfg["out_features_dir"] = str(tmp_path / "features")
    cfg["out_outputs_dir"] = str(tmp_path / "outputs")
    files = mod.build_grid_features(cfg)
    df = pd.read_csv(files["features_csv"])
    required = [
        "cell_id", "lat", "lon", "building_density", "road_fraction", "gvi_percent",
        "svf", "shade_fraction", "park_distance_m", "elderly_proxy", "outdoor_exposure_proxy", "land_use_hint",
    ]
    for c in required:
        assert c in df.columns
    assert len(df) > 0
    assert df["building_density"].between(0, 1).all()
    assert df["svf"].between(0, 1).all()
    assert df["shade_fraction"].between(0, 1).all()
    assert Path(files["qa_report"]).exists()
