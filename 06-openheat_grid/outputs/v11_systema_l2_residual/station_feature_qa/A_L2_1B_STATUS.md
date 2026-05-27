# A-L2.1b Status

Status: PASS_FEATURE_QA_READY_FOR_SCOPED_MODEL
Branch: codex/systema-l2-station-feature-qa
Scope: station buffer feature QA / collinearity / residual-readiness gate only; no residual modelling.

Commands run:
- C:\Users\CloudStar\anaconda3\envs\openheat\python.exe scripts/v11_l2_run_station_feature_qa.py --config configs/v11/systema_l2_station_feature_qa.yaml
- CLI equivalent: python scripts/v11_l2_run_station_feature_qa.py --config configs/v11/systema_l2_station_feature_qa.yaml

Key results:
- Primary candidate feature count: 8
- Top residual-associated features: water_fraction_100m:high-tail residual r=0.509460;distance_to_water_m_100m:high-tail residual r=-0.471453;distance_to_water_m_250m:high-tail residual r=-0.471453;distance_to_water_m_500m:high-tail residual r=-0.471453;distance_to_water_m_50m:high-tail residual r=-0.471453
- Excluded high-collinearity groups: C004:distance_to_water_m_250m excludes distance_to_water_m_50m;distance_to_water_m_100m;distance_to_water_m_500m;C005:road_density_m_per_ha_250m excludes road_length_m_250m;C008:distance_to_park_or_green_m_250m excludes distance_to_park_or_green_m_50m;distance_to_park_or_green_m_100m;distance_to_park_or_green_m_500m;green_space_fraction_100m
- Key station caveats: S142:n_ge31=15,score_resid=0.772569,high_tail=2.239617,context_extremes=11;S139:n_ge31=1,score_resid=-0.310600,high_tail=0.110892,context_extremes=14;S137:n_ge31=13,score_resid=0.774637,high_tail=1.347448,context_extremes=20;S128:n_ge31=11,score_resid=0.121816,high_tail=1.158280,context_extremes=10;S145:n_ge31=8,score_resid=-0.165699,high_tail=0.884977,context_extremes=15
- A-L2.1c recommendation: A-L2.1c may proceed only as a station-level n=27 scoped preflight model using the small primary set and sensitivity checks; no station-adjusted WBGT or causal correction.

Caveats:
- No model trained.
- No station-context causal correction claimed.
- No station-adjusted WBGT or local 100 m WBGT created.
- Probability-error screens are secondary because A-L2.0 found weaker station signal.
- Station-static features must be used only at station-level n=27 in any future scoped preflight.

Files created / modified:
- outputs/v11_systema_l2_residual/station_feature_qa/station_feature_qa_summary.csv
- outputs/v11_systema_l2_residual/station_feature_qa/station_feature_distribution_summary.csv
- outputs/v11_systema_l2_residual/station_feature_qa/station_feature_collinearity_pairs.csv
- outputs/v11_systema_l2_residual/station_feature_qa/station_feature_correlation_clusters.csv
- outputs/v11_systema_l2_residual/station_feature_qa/station_feature_buffer_redundancy.csv
- outputs/v11_systema_l2_residual/station_feature_qa/station_residual_association_screen.csv
- outputs/v11_systema_l2_residual/station_feature_qa/station_context_profiles_key_stations.csv
- outputs/v11_systema_l2_residual/station_feature_qa/station_feature_candidate_set.csv
- outputs/v11_systema_l2_residual/station_feature_qa/station_feature_manual_review_table.csv
- outputs/v11_systema_l2_residual/station_feature_qa/station_feature_qa_report.md
- outputs/v11_systema_l2_residual/station_feature_qa/A_L2_1B_STATUS.md
- docs/v11/OpenHeat_SystemA_L2_station_feature_QA_CN.md

Safe to commit: controlled config/script/docs and compact CSV/Markdown outputs after review.
Not safe to commit: raw spatial layers, rasters, archives, SOLWEIG/System B outputs, or large forecast/live CSVs.

Next recommended action: A-L2.1c may proceed only as a station-level n=27 scoped preflight model using the small primary set and sensitivity checks; no station-adjusted WBGT or causal correction.
