# 90-second talk track (non-fluent English is OK)

## What did you build?
I built an explainable ML pipeline to predict seasonal mean temperature (heat exposure proxy) from urban form and greenness indicators,
and I evaluated it with spatially-aware cross-validation to avoid spatial leakage.

## Why not random KFold?
Because nearby locations are similar (spatial autocorrelation). Random splits mix neighboring samples between train and test,
so the model indirectly “sees” the test area and metrics become overly optimistic.

## How did you avoid leakage?
I created spatial blocks (regular 0.02° grid) and used GroupKFold so that entire blocks are held out in each fold.
As a sensitivity check, I also ran leave-location-out CV using location IDs.

## How to read the results?
Report RMSE/MAE/R² and compare Random CV vs Spatial CV. A performance drop under Spatial CV indicates leakage in the random split.
I also map residuals to see where the model under/over-predicts spatially.

## What is the biggest limitation?
The features are proxies (street-view/land-use summaries) and may not capture microclimate drivers; there may be temporal mismatch.
The model is a decision-support prototype and may not generalize to other cities or years without recalibration.
