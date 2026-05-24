# Model design and validation notes

## Prediction task

The system predicts future hourly heat stress at grid/POI scale:

```text
Y[cell, t] = UTCI / WBGT category / exceedance duration
```

The useful product is not only the maximum value. For heatwave response, duration matters:

```text
moderate_wbgt_hours = count(WBGT >= 31)
high_wbgt_hours = count(WBGT >= 33)
strong_utci_hours = count(UTCI >= 32)
```

## Why local-offset modelling is safer

Do not directly predict microclimate from scratch. Model local deviation from background forecast:

```text
Tair_local = Tair_forecast + ΔT_urban
wind_local = wind_forecast × wind_reduction_factor
Tmrt_local = radiation + shade + SVF + GVI function
```

Then compute UTCI/WBGT.

This makes the system transferable and easier to validate.

## v0.5 formula logic

v0.5 uses simplified screening equations:

- high building density and road fraction raise local air temperature;
- GVI and park proximity reduce local air temperature;
- building density and low SVF reduce local wind;
- shortwave radiation, low shade and high SVF raise Tmrt;
- UTCI uses `pythermalcomfort` if available;
- WBGT proxy uses approximate wet-bulb + globe proxy.

This is good enough for a coding prototype, not enough for final science.

## Validation ladder

1. Unit tests: formulas and output columns.
2. Station validation: forecast T/RH/wind vs NEA observations.
3. WBGT calibration: WBGT proxy vs official Singapore WBGT observations.
4. Spatial plausibility: hotspot pattern vs LST/LCZ/building density.
5. Local field validation: Toa Payoh mobile monitoring or fixed sensors.
6. Event validation: compare heatwave days vs normal days.

## Model outputs to show in portfolio

- top 10 hotspot grid cells;
- event windows when ≥30% of cells exceed moderate WBGT;
- map of max WBGT / max UTCI;
- uncertainty band after calibration;
- intervention scenario comparison.
