# Data sources and limitations

## Live weather and official calibration

- Open-Meteo forecast: background hourly weather forecast.
- data.gov.sg NEA realtime weather readings: temperature, humidity, wind and rainfall at station level.
- data.gov.sg NEA WBGT observations: official nowcast-style WBGT for calibration.

## Spatial data for Toa Payoh

- URA Master Plan 2019 building layer: indicative building footprints.
- HDB Property Information: HDB block attributes including max floor level and year completed.
- NParks parks and nature reserves / park facilities: green-space boundaries and facilities.
- Google Open Buildings 2.5D: building height raster where official height is incomplete.
- OSM/OneMap: road, path, POI and geocoding support.

## Minimum spatial features

For each grid cell:

```text
building_density
mean/max building height
SVF proxy
shade fraction
GVI / NDVI / tree canopy
road/impervious fraction
park/water distance
elderly/exposure proxy
```

## Biggest limitations

- Open weather forecasts are too coarse for street canyons.
- Wind and Tmrt dominate pedestrian heat stress but are hardest to model.
- WBGT proxy needs calibration; official WBGT is station/network based.
- Building footprints without heights are insufficient for shade/SVF.
- Without local sensors, the system should report relative risk ranking, not operational alerts.
