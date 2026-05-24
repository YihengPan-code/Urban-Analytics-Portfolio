from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask

BASE = Path("outputs/v12_solweig_typology_pilot/core8_base/TP_0542/h15/Tmrt_average.tif")
OVER = Path("outputs/v12_solweig_typology_pilot/core8_overhead/TP_0542/h15/Tmrt_average.tif")
FOCUS = Path("data/solweig/v12_typology_tiles/V12C04_TP_0542_river_edge_shaded_walkway/focus_cell.geojson")
OUT = Path("outputs/v12_solweig_typology_pilot/core8_overhead_summary/tp0542_h15_distribution")
OUT.mkdir(parents=True, exist_ok=True)

def values(path: Path) -> np.ndarray:
    gdf = gpd.read_file(FOCUS)
    with rasterio.open(path) as src:
        gdf = gdf.to_crs(src.crs)
        arr, _ = mask(src, list(gdf.geometry), crop=True, filled=False)
        band = arr[0]
        vals = band.compressed() if np.ma.isMaskedArray(band) else band[np.isfinite(band)]
    return vals[np.isfinite(vals)]

b = values(BASE)
o = values(OVER)

qs = [0, 1, 5, 10, 25, 50, 75, 80, 85, 90, 95, 99, 100]
qrows = []
for q in qs:
    qrows.append({
        "quantile": q,
        "base_tmrt_c": float(np.percentile(b, q)),
        "overhead_tmrt_c": float(np.percentile(o, q)),
        "delta_overhead_minus_base_c": float(np.percentile(o, q) - np.percentile(b, q)),
    })
qdf = pd.DataFrame(qrows)
qdf.to_csv(OUT / "tp0542_h15_quantiles.csv", index=False)

thresholds = [35, 40, 45, 50, 55, 60]
trows = []
for t in thresholds:
    trows.append({
        "threshold_c": t,
        "base_pct_ge_threshold": float((b >= t).mean() * 100),
        "overhead_pct_ge_threshold": float((o >= t).mean() * 100),
        "delta_pct_point": float((o >= t).mean() * 100 - (b >= t).mean() * 100),
    })
tdf = pd.DataFrame(trows)
tdf.to_csv(OUT / "tp0542_h15_threshold_area.csv", index=False)

md = []
md.append("# TP0542 h15 base vs overhead distribution diagnostic\n\n")
md.append("## Quantiles\n\n")
md.append(qdf.round(3).to_markdown(index=False))
md.append("\n\n## Area above thresholds\n\n")
md.append(tdf.round(2).to_markdown(index=False))
md.append("\n\n## Interpretation note\n\n")
md.append(
    "TP0542 h15 is interpreted as a mapped pedestrian-overhead shade case. "
    "A large p90 decrease with unchanged max means overhead adds shaded/low-Tmrt pixels "
    "while a small number of hot pixels remains. This supports p90 as a mixed-cell upper-tail target.\n"
)
(OUT / "tp0542_h15_distribution_diagnostic.md").write_text("".join(md), encoding="utf-8")

print("[write]", OUT / "tp0542_h15_quantiles.csv")
print("[write]", OUT / "tp0542_h15_threshold_area.csv")
print("[write]", OUT / "tp0542_h15_distribution_diagnostic.md")
print(qdf.round(3).to_string(index=False))
print(tdf.round(2).to_string(index=False))