06-openheat_grid/
├─.github/
│ └─workflows/
│   └─archive_nea_observations.yml
├─.gitignore
├─.pytest_cache/
│ ├─.gitignore
│ ├─CACHEDIR.TAG
│ ├─README.md
│ └─v/
│   └─cache/
│     ├─lastfailed
│     └─nodeids
├─backup_conda_explicit.txt
├─backup_pip.txt
├─configs/
│ ├─v071_risk_exposure_config.example.json
│ ├─v07_grid_features_config.example.json
│ ├─v07_grid_features_config.sample_fixture.json
│ ├─v09_alpha_config.example.json
│ ├─v09_beta_config.example.json
│ ├─v09_beta_threshold_config.example.json
│ ├─v09_gamma_overhead_aware_config.example.json
│ ├─v09_gamma_solweig_config.example.json
│ └─v10/
│   └─.gitkeep
├─data/
│ ├─archive/
│ │ ├─nea_realtime_observations.csv
│ │ └─openmeteo_forecast_snapshots/
│ ├─calibration/
│ │ ├─v09_historical_forecast_by_station_hourly.csv
│ │ └─v09_wbgt_station_pairs.csv
│ ├─features/
│ │ ├─building_density.csv
│ │ ├─land_use_hint.csv
│ │ ├─park_distances.csv
│ │ ├─provenance/
│ │ │ ├─building_density.yaml
│ │ │ ├─land_use_hint.yaml
│ │ │ ├─park_distance_m.yaml
│ │ │ └─road_fraction.yaml
│ │ ├─road_fraction.csv
│ │ ├─v071/
│ │ │ ├─v071_node_scores_raw.csv
│ │ │ ├─v071_public_nodes_clean.geojson
│ │ │ ├─v071_risk_exposure_features.csv
│ │ │ └─v071_subzone_demographic_vulnerability.csv
│ │ └─water_distance.csv
│ ├─features_3d/
│ │ ├─aoi_buffered_200m.geojson
│ │ ├─hdb3d_buildings_toapayoh.geojson
│ │ ├─hdb3d_raw.geojson
│ │ ├─merged_buildings_height_v08.geojson
│ │ ├─ura_buildings_toapayoh.geojson
│ │ └─v10/
│ ├─fixtures/
│ │ ├─nea_air_temperature_sample.json
│ │ ├─nea_relative_humidity_sample.json
│ │ ├─nea_wbgt_sample.json
│ │ ├─nea_wbgt_v1_sample.json
│ │ ├─nea_wbgt_v2_current_schema_sample.json
│ │ └─nea_wind_speed_sample.json
│ ├─grid/
│ │ ├─toa_payoh_grid_v07.csv
│ │ ├─toa_payoh_grid_v07.geojson
│ │ ├─toa_payoh_grid_v07_features.csv
│ │ ├─toa_payoh_grid_v07_features.geojson
│ │ ├─toa_payoh_grid_v07_features_alpha.csv
│ │ ├─toa_payoh_grid_v07_features_alpha_backup.csv
│ │ ├─toa_payoh_grid_v07_features_beta_final.csv
│ │ ├─toa_payoh_grid_v07_features_beta_final_v071_risk.csv
│ │ ├─toa_payoh_grid_v07_features_beta_gee.csv
│ │ ├─toa_payoh_grid_v07_features_beta_gee_impervfix.csv
│ │ ├─toa_payoh_grid_v07_for_ee.cpg
│ │ ├─toa_payoh_grid_v07_for_ee.dbf
│ │ ├─toa_payoh_grid_v07_for_ee.prj
│ │ ├─toa_payoh_grid_v07_for_ee.shp
│ │ ├─toa_payoh_grid_v07_for_ee.shx
│ │ ├─toa_payoh_grid_v08_features_umep_with_veg.csv
│ │ ├─toa_payoh_grid_v08_umep_morphology.csv
│ │ ├─toa_payoh_grid_v08_umep_morphology_with_veg.csv
│ │ └─v10/
│ │   └─.gitkeep
│ ├─rasters/
│ │ ├─v08/
│ │ │ ├─dsm_buildings_2m_toapayoh.tif
│ │ │ ├─dsm_buildings_2m_toapayoh.tif.aux.xml
│ │ │ ├─dsm_vegetation_2m_toapayoh.tif
│ │ │ ├─dsm_vegetation_2m_toapayoh.tif.aux.xml
│ │ │ ├─umep_shadow/
│ │ │ │ ├─Shadow_20260320_0800_LST.tif
│ │ │ │ ├─Shadow_20260320_0900_LST.tif
│ │ │ │ ├─Shadow_20260320_1000_LST.tif
│ │ │ │ ├─Shadow_20260320_1100_LST.tif
│ │ │ │ ├─Shadow_20260320_1200_LST.tif
│ │ │ │ ├─Shadow_20260320_1300_LST.tif
│ │ │ │ ├─Shadow_20260320_1400_LST.tif
│ │ │ │ ├─Shadow_20260320_1500_LST.tif
│ │ │ │ ├─Shadow_20260320_1600_LST.tif
│ │ │ │ ├─Shadow_20260320_1700_LST.tif
│ │ │ │ ├─Shadow_20260320_1800_LST.tif
│ │ │ │ └─Shadow_20260320_1900_LST.tif
│ │ │ ├─umep_shadow_with_veg/
│ │ │ │ ├─Shadow_20260320_0800_LST.tif
│ │ │ │ ├─Shadow_20260320_0900_LST.tif
│ │ │ │ ├─Shadow_20260320_1000_LST.tif
│ │ │ │ ├─Shadow_20260320_1100_LST.tif
│ │ │ │ ├─Shadow_20260320_1200_LST.tif
│ │ │ │ ├─Shadow_20260320_1300_LST.tif
│ │ │ │ ├─Shadow_20260320_1400_LST.tif
│ │ │ │ ├─Shadow_20260320_1500_LST.tif
│ │ │ │ ├─Shadow_20260320_1600_LST.tif
│ │ │ │ ├─Shadow_20260320_1700_LST.tif
│ │ │ │ ├─Shadow_20260320_1800_LST.tif
│ │ │ │ └─Shadow_20260320_1900_LST.tif
│ │ │ ├─umep_svf/
│ │ │ │ ├─shadowmats.npz
│ │ │ │ ├─SkyViewFactor.tif
│ │ │ │ └─svfs.zip
│ │ │ └─umep_svf_with_veg/
│ │ │   ├─shadowmats.npz
│ │ │   ├─SkyViewFactor.tif
│ │ │   ├─SkyViewFactor.tif.aux.xml
│ │ │   └─svfs.zip
│ │ └─v10/
│ │   └─.gitkeep
│ ├─raw/
│ │ ├─boundaries/
│ │ │ └─ura_mp19_subzone_no_sea.geojson
│ │ ├─buildings_v10/
│ │ ├─canopy/
│ │ │ └─canopy_height_10m_toapayoh.tif
│ │ ├─demographics/
│ │ │ └─singstat_subzone_age_2020.csv
│ │ ├─gee_height_vegetation_by_grid.csv
│ │ ├─hdb3d/
│ │ │ └─hdb3d-data/
│ │ │   ├─.git/
│ │ │   │ ├─config
│ │ │   │ ├─description
│ │ │   │ ├─HEAD
│ │ │   │ ├─hooks/
│ │ │   │ │ ├─applypatch-msg.sample
│ │ │   │ │ ├─commit-msg.sample
│ │ │   │ │ ├─fsmonitor-watchman.sample
│ │ │   │ │ ├─post-update.sample
│ │ │   │ │ ├─pre-applypatch.sample
│ │ │   │ │ ├─pre-commit.sample
│ │ │   │ │ ├─pre-merge-commit.sample
│ │ │   │ │ ├─pre-push.sample
│ │ │   │ │ ├─pre-rebase.sample
│ │ │   │ │ ├─pre-receive.sample
│ │ │   │ │ ├─prepare-commit-msg.sample
│ │ │   │ │ ├─push-to-checkout.sample
│ │ │   │ │ ├─sendemail-validate.sample
│ │ │   │ │ └─update.sample
│ │ │   │ ├─index
│ │ │   │ ├─info/
│ │ │   │ │ └─exclude
│ │ │   │ ├─logs/
│ │ │   │ │ ├─HEAD
│ │ │   │ │ └─refs/
│ │ │   │ │   ├─heads/
│ │ │   │ │   │ └─master
│ │ │   │ │   └─remotes/
│ │ │   │ │     └─origin/
│ │ │   │ │       └─HEAD
│ │ │   │ ├─objects/
│ │ │   │ │ ├─info/
│ │ │   │ │ └─pack/
│ │ │   │ │   ├─pack-b7c1281f93a48e5e496a827fca63e8d9f10bb73f.idx
│ │ │   │ │   ├─pack-b7c1281f93a48e5e496a827fca63e8d9f10bb73f.pack
│ │ │   │ │   └─pack-b7c1281f93a48e5e496a827fca63e8d9f10bb73f.rev
│ │ │   │ ├─packed-refs
│ │ │   │ └─refs/
│ │ │   │   ├─heads/
│ │ │   │   │ └─master
│ │ │   │   ├─remotes/
│ │ │   │   │ └─origin/
│ │ │   │   │   └─HEAD
│ │ │   │   └─tags/
│ │ │   ├─.gitignore
│ │ │   ├─CITATION
│ │ │   ├─hdb.json
│ │ │   ├─hdb.obj
│ │ │   ├─LICENSE
│ │ │   ├─README.md
│ │ │   └─_images/
│ │ │     ├─azul-hdb.png
│ │ │     ├─hdb3d-c1_att.png
│ │ │     ├─hdb3d-c3_att.png
│ │ │     └─hdb3d-mapbox.png
│ │ ├─nparks_parks_nature_reserves.geojson
│ │ ├─osm_roads_toa_payoh.geojson
│ │ ├─osm_roads_toa_payoh.qmd
│ │ ├─osm_water_toa_payoh.geojson
│ │ ├─osm_water_toa_payoh.qmd
│ │ ├─poi/
│ │ │ ├─ecda_preschools.geojson
│ │ │ ├─lta_bus_stops.geojson
│ │ │ ├─lta_mrt_exits.geojson
│ │ │ ├─moh_eldercare_services.geojson
│ │ │ ├─nea_hawker_centres.geojson
│ │ │ └─sportsg_facilities.geojson
│ │ ├─ura_masterplan2019_buildings.geojson
│ │ └─ura_masterplan2019_land_use.geojson
│ ├─sample/
│ │ ├─openmeteo_heatwave_forecast_sample.csv
│ │ ├─toa_payoh_grid_sample.csv
│ │ ├─toa_payoh_pois_sample.csv
│ │ └─v07_raw_fixtures/
│ │   ├─sample_buildings.geojson
│ │   ├─sample_land_use.geojson
│ │   ├─sample_parks.geojson
│ │   ├─sample_roads.geojson
│ │   └─sample_water.geojson
│ ├─solweig/
│ │ ├─v09_met_forcing_2026_05_07_S128.txt
│ │ ├─v09_met_forcing_2026_05_07_S128_h10.txt
│ │ ├─v09_met_forcing_2026_05_07_S128_h12.txt
│ │ ├─v09_met_forcing_2026_05_07_S128_h13.txt
│ │ ├─v09_met_forcing_2026_05_07_S128_h15.txt
│ │ ├─v09_met_forcing_2026_05_07_S128_h16.txt
│ │ ├─v09_tiles/
│ │ │ ├─T01_hazard_top_TP_0088/
│ │ │ │ ├─dsm_buildings_tile.tif
│ │ │ │ ├─dsm_buildings_tile.tif.aux.xml
│ │ │ │ ├─dsm_buildings_tile_masked.tif
│ │ │ │ ├─dsm_vegetation_tile.tif
│ │ │ │ ├─dsm_vegetation_tile.tif.aux.xml
│ │ │ │ ├─dsm_vegetation_tile_masked.tif
│ │ │ │ └─README_SOLWEIG_STEPS.txt
│ │ │ ├─T02_conservative_risk_top_TP_0378/
│ │ │ │ ├─dsm_buildings_tile.tif
│ │ │ │ ├─dsm_buildings_tile_masked.tif
│ │ │ │ ├─dsm_vegetation_tile.tif
│ │ │ │ ├─dsm_vegetation_tile.tif.aux.xml
│ │ │ │ ├─dsm_vegetation_tile_masked.tif
│ │ │ │ └─README_SOLWEIG_STEPS.txt
│ │ │ ├─T03_social_risk_top_TP_0452/
│ │ │ │ ├─dsm_buildings_tile.tif
│ │ │ │ ├─dsm_buildings_tile.tif.aux.xml
│ │ │ │ ├─dsm_buildings_tile_masked.tif
│ │ │ │ ├─dsm_vegetation_tile.tif
│ │ │ │ ├─dsm_vegetation_tile_masked.tif
│ │ │ │ └─README_SOLWEIG_STEPS.txt
│ │ │ ├─T04_candidate_policy_top_TP_0366/
│ │ │ │ ├─dsm_buildings_tile.tif
│ │ │ │ ├─dsm_buildings_tile.tif.aux.xml
│ │ │ │ ├─dsm_buildings_tile_masked.tif
│ │ │ │ ├─dsm_vegetation_tile.tif
│ │ │ │ ├─dsm_vegetation_tile_masked.tif
│ │ │ │ └─README_SOLWEIG_STEPS.txt
│ │ │ ├─T05_shaded_reference_TP_0892/
│ │ │ │ ├─dsm_buildings_tile.tif
│ │ │ │ ├─dsm_buildings_tile_masked.tif
│ │ │ │ ├─dsm_vegetation_tile.tif
│ │ │ │ ├─dsm_vegetation_tile.tif.aux.xml
│ │ │ │ ├─dsm_vegetation_tile_masked.tif
│ │ │ │ └─README_SOLWEIG_STEPS.txt
│ │ │ ├─v09_solweig_tiles.geojson
│ │ │ ├─v09_solweig_tiles_buffered.geojson
│ │ │ └─v09_solweig_tile_metadata.csv
│ │ ├─v09_tiles_overhead_aware/
│ │ │ ├─T01_clean_hazard_top/
│ │ │ │ ├─dem_flat.tif
│ │ │ │ ├─dem_flat.tif.aux.xml
│ │ │ │ ├─dsm_buildings_tile.tif
│ │ │ │ ├─dsm_buildings_tile.tif.aux.xml
│ │ │ │ ├─dsm_buildings_tile_masked.tif
│ │ │ │ ├─dsm_vegetation_tile.tif
│ │ │ │ ├─dsm_vegetation_tile.tif.aux.xml
│ │ │ │ ├─dsm_vegetation_tile_masked.tif
│ │ │ │ ├─README_SOLWEIG_STEPS.txt
│ │ │ │ ├─solweig_outputs/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ ├─Tmrt_2026_127_1000D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1200D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1300D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1500D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1600D.tif
│ │ │ │ │ ├─Tmrt_average.tif
│ │ │ │ │ └─Tmrt_average.tif.aux.xml
│ │ │ │ ├─solweig_outputs_h10/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h12/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h13/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h15/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h16/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─svf_outputs/
│ │ │ │ │ ├─shadowmats.npz
│ │ │ │ │ ├─SkyViewFactor.tif
│ │ │ │ │ ├─SkyViewFactor.tif.aux.xml
│ │ │ │ │ └─svfs.zip
│ │ │ │ ├─tile_boundary_buffered.geojson
│ │ │ │ ├─wall_aspect.tif
│ │ │ │ ├─wall_aspect.tif.aux.xml
│ │ │ │ ├─wall_height.tif
│ │ │ │ └─wall_height.tif.aux.xml
│ │ │ ├─T02_conservative_risk_top/
│ │ │ │ ├─dem_flat.tif
│ │ │ │ ├─dem_flat.tif.aux.xml
│ │ │ │ ├─dsm_buildings_tile.tif
│ │ │ │ ├─dsm_buildings_tile.tif.aux.xml
│ │ │ │ ├─dsm_buildings_tile_masked.tif
│ │ │ │ ├─dsm_vegetation_tile.tif
│ │ │ │ ├─dsm_vegetation_tile.tif.aux.xml
│ │ │ │ ├─dsm_vegetation_tile_masked.tif
│ │ │ │ ├─README_SOLWEIG_STEPS.txt
│ │ │ │ ├─solweig_outputs/
│ │ │ │ │ ├─Tmrt_2026_127_1000D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1200D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1300D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1500D.tif
│ │ │ │ │ └─Tmrt_2026_127_1600D.tif
│ │ │ │ ├─solweig_outputs_h10/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h12/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h13/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h15/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h16/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─svf_outputs/
│ │ │ │ │ ├─shadowmats.npz
│ │ │ │ │ ├─SkyViewFactor.tif
│ │ │ │ │ ├─SkyViewFactor.tif.aux.xml
│ │ │ │ │ └─svfs.zip
│ │ │ │ ├─tile_boundary_buffered.geojson
│ │ │ │ ├─wall_aspect.tif
│ │ │ │ ├─wall_aspect.tif.aux.xml
│ │ │ │ ├─wall_height.tif
│ │ │ │ └─wall_height.tif.aux.xml
│ │ │ ├─T03_social_risk_top/
│ │ │ │ ├─dem_flat.tif
│ │ │ │ ├─dem_flat.tif.aux.xml
│ │ │ │ ├─dsm_buildings_tile.tif
│ │ │ │ ├─dsm_buildings_tile.tif.aux.xml
│ │ │ │ ├─dsm_buildings_tile_masked.tif
│ │ │ │ ├─dsm_vegetation_tile.tif
│ │ │ │ ├─dsm_vegetation_tile.tif.aux.xml
│ │ │ │ ├─dsm_vegetation_tile_masked.tif
│ │ │ │ ├─README_SOLWEIG_STEPS.txt
│ │ │ │ ├─solweig_outputs/
│ │ │ │ │ ├─Tmrt_2026_127_1000D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1200D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1300D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1500D.tif
│ │ │ │ │ └─Tmrt_2026_127_1600D.tif
│ │ │ │ ├─solweig_outputs_h10/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h12/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h13/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h15/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h16/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─svf_outputs/
│ │ │ │ │ ├─shadowmats.npz
│ │ │ │ │ ├─SkyViewFactor.tif
│ │ │ │ │ ├─SkyViewFactor.tif.aux.xml
│ │ │ │ │ └─svfs.zip
│ │ │ │ ├─tile_boundary_buffered.geojson
│ │ │ │ ├─wall_aspect.tif
│ │ │ │ ├─wall_aspect.tif.aux.xml
│ │ │ │ ├─wall_height.tif
│ │ │ │ └─wall_height.tif.aux.xml
│ │ │ ├─T04_open_paved_hotspot/
│ │ │ │ ├─dem_flat.tif
│ │ │ │ ├─dem_flat.tif.aux.xml
│ │ │ │ ├─dsm_buildings_tile.tif
│ │ │ │ ├─dsm_buildings_tile.tif.aux.xml
│ │ │ │ ├─dsm_buildings_tile_masked.tif
│ │ │ │ ├─dsm_vegetation_tile.tif
│ │ │ │ ├─dsm_vegetation_tile.tif.aux.xml
│ │ │ │ ├─dsm_vegetation_tile_masked.tif
│ │ │ │ ├─README_SOLWEIG_STEPS.txt
│ │ │ │ ├─solweig_outputs/
│ │ │ │ │ ├─Tmrt_2026_127_1000D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1200D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1300D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1500D.tif
│ │ │ │ │ └─Tmrt_2026_127_1600D.tif
│ │ │ │ ├─solweig_outputs_h10/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h12/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h13/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h15/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h16/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─svf_outputs/
│ │ │ │ │ ├─shadowmats.npz
│ │ │ │ │ ├─SkyViewFactor.tif
│ │ │ │ │ ├─SkyViewFactor.tif.aux.xml
│ │ │ │ │ └─svfs.zip
│ │ │ │ ├─tile_boundary_buffered.geojson
│ │ │ │ ├─wall_aspect.tif
│ │ │ │ ├─wall_aspect.tif.aux.xml
│ │ │ │ ├─wall_height.tif
│ │ │ │ └─wall_height.tif.aux.xml
│ │ │ ├─T05_clean_shaded_reference/
│ │ │ │ ├─dem_flat.tif
│ │ │ │ ├─dem_flat.tif.aux.xml
│ │ │ │ ├─dsm_buildings_tile.tif
│ │ │ │ ├─dsm_buildings_tile.tif.aux.xml
│ │ │ │ ├─dsm_buildings_tile_masked.tif
│ │ │ │ ├─dsm_vegetation_tile.tif
│ │ │ │ ├─dsm_vegetation_tile.tif.aux.xml
│ │ │ │ ├─dsm_vegetation_tile_masked.tif
│ │ │ │ ├─README_SOLWEIG_STEPS.txt
│ │ │ │ ├─solweig_outputs/
│ │ │ │ │ ├─Tmrt_2026_127_1000D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1200D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1300D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1500D.tif
│ │ │ │ │ └─Tmrt_2026_127_1600D.tif
│ │ │ │ ├─solweig_outputs_h10/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h12/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h13/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h15/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h16/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─svf_outputs/
│ │ │ │ │ ├─shadowmats.npz
│ │ │ │ │ ├─SkyViewFactor.tif
│ │ │ │ │ ├─SkyViewFactor.tif.aux.xml
│ │ │ │ │ └─svfs.zip
│ │ │ │ ├─tile_boundary_buffered.geojson
│ │ │ │ ├─wall_aspect.tif
│ │ │ │ ├─wall_aspect.tif.aux.xml
│ │ │ │ ├─wall_height.tif
│ │ │ │ └─wall_height.tif.aux.xml
│ │ │ ├─T06_overhead_confounded_hazard_case/
│ │ │ │ ├─dem_flat.tif
│ │ │ │ ├─dem_flat.tif.aux.xml
│ │ │ │ ├─dsm_buildings_tile.tif
│ │ │ │ ├─dsm_buildings_tile.tif.aux.xml
│ │ │ │ ├─dsm_buildings_tile_masked.tif
│ │ │ │ ├─dsm_vegetation_tile.tif
│ │ │ │ ├─dsm_vegetation_tile.tif.aux.xml
│ │ │ │ ├─dsm_vegetation_tile_masked.tif
│ │ │ │ ├─README_SOLWEIG_STEPS.txt
│ │ │ │ ├─solweig_outputs/
│ │ │ │ │ ├─Tmrt_2026_127_1000D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1200D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1300D.tif
│ │ │ │ │ ├─Tmrt_2026_127_1500D.tif
│ │ │ │ │ └─Tmrt_2026_127_1600D.tif
│ │ │ │ ├─solweig_outputs_h10/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h12/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h13/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h15/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─solweig_outputs_h16/
│ │ │ │ │ ├─configsolweig.ini
│ │ │ │ │ ├─metforcing.txt
│ │ │ │ │ ├─solweig_parameters.json
│ │ │ │ │ └─Tmrt_average.tif
│ │ │ │ ├─svf_outputs/
│ │ │ │ │ ├─shadowmats.npz
│ │ │ │ │ ├─SkyViewFactor.tif
│ │ │ │ │ ├─SkyViewFactor.tif.aux.xml
│ │ │ │ │ └─svfs.zip
│ │ │ │ ├─tile_boundary_buffered.geojson
│ │ │ │ ├─wall_aspect.tif
│ │ │ │ ├─wall_aspect.tif.aux.xml
│ │ │ │ ├─wall_height.tif
│ │ │ │ └─wall_height.tif.aux.xml
│ │ │ ├─v09_solweig_tiles_overhead_aware.geojson
│ │ │ ├─v09_solweig_tiles_overhead_aware_buffered.geojson
│ │ │ ├─v09_solweig_tile_metadata_overhead_aware.csv
│ │ │ └─v09_solweig_tile_selection_overhead_aware_QA_report.md
│ │ └─v10_all_cells/
│ │   └─.gitkeep
│ └─solweig.zip
├─data - 快捷方式.lnk
├─docs/
│ ├─v09_freeze/
│ │ ├─01_HEAT_STRESS_PREDICTION_SYSTEM_ROADMAP_CN.md
│ │ ├─01_V06_LIVE_API_AND_CALIBRATION_GUIDE_CN.md
│ │ ├─02_IF_THIS_FAILS_DO_THIS_CN.md
│ │ ├─02_MODEL_DESIGN_AND_VALIDATION_CN.md
│ │ ├─03_DATA_SOURCES_AND_LIMITATIONS_CN.md
│ │ ├─03_V06_TO_V07_TASKLIST_CN.md
│ │ ├─04_PLYMOUTH_DATA_ROLE_CN.md
│ │ ├─04_V06_METHOD_LIMITATIONS_CN.md
│ │ ├─05_ARCHIVING_FOR_CALIBRATION_CN.md
│ │ ├─06_V06_1_FEEDBACK_OPTIMISATION_CN.md
│ │ ├─07_GITHUB_ACTIONS_ARCHIVING_CN.md
│ │ ├─08_V06_1_TO_V07_PRIORITY_CN.md
│ │ ├─09_V06_2_WBGT_SCHEMA_HOTFIX_CN.md
│ │ ├─10_V06_3_WBGT_V2_SCHEMA_FIX_CN.md
│ │ ├─11_V06_4_ARCHIVE_AND_ALERT_HOTFIX_CN.md
│ │ ├─12_V06_4_1_SRC_REVIEW_PATCH_CN.md
│ │ ├─13_V07_GRID_FEATURES_PIPELINE_CN.md
│ │ ├─14_V07_BETA_GEE_INTEGRATION_CN.md
│ │ ├─15_V07_BETA1_QA_AND_FINALISATION_CN.md
│ │ ├─16_V071_RISK_EXPOSURE_GUIDE_CN.md
│ │ ├─17_V071_CENSUS_PARSER_HOTFIX_CN.md
│ │ ├─18_V071_CENSUS_PARSER_HOTFIX_V2_CN.md
│ │ ├─21_V08_UMEP_WITH_VEGETATION_MERGE_FORECAST_CN.md
│ │ ├─22_V08_REVIEW_HOTFIX_CN.md
│ │ ├─23_V08_RISK_SCENARIOS_CN.md
│ │ ├─24_V08_RISK_SCENARIOS_HOTFIX_CN.md
│ │ ├─24_V09_ALPHA_CALIBRATION_GUIDE_CN.md
│ │ ├─25.5_V09_BETA_FINDINGS_REPORT_CN.md
│ │ ├─25_V09_BETA_CALIBRATION_GUIDE_CN.md
│ │ ├─26_V09_BETA_THRESHOLD_SCAN_AND_CONCLUSION_CN.md
│ │ ├─27_V09_GAMMA_SOLWEIG_GUIDE_CN.md
│ │ ├─28_V09_ARCHIVE_COLLECTION_CN.md
│ │ ├─29_V09_GAMMA_HOTFIX_CN.md
│ │ ├─30_V09_GAMMA_OVERHEAD_AWARE_TILE_SELECTION_CN.md
│ │ ├─32_V09_COMPLETE_WORK_RECORD_CN.md
│ │ ├─33_V09_BUILDING_DSM_GAP_AUDIT_CN.md
│ │ ├─V09_FREEZE_NOTE_CN.md
│ │ └─V09_REVISED_FINDINGS_CN.md
│ └─v10/
│   ├─.gitkeep
│   └─V10_PROJECT_STRUCTURE_CN.md
├─earth_engine/
│ └─v07_export_height_vegetation_to_grid.js
├─logs/
├─notebooks/
│ ├─03_heatwave_hotspot_prediction_mvp.ipynb
│ └─04_live_forecast_and_calibration_v06.ipynb
├─openheat.zip
├─outputs/
│ ├─sample_event_windows.csv
│ ├─sample_hotspot_preview.png
│ ├─sample_hotspot_ranking.csv
│ ├─sample_hourly_grid_heatstress_forecast.csv
│ ├─tmp_archive_test.csv
│ ├─V06_1_COMPLETION_REPORT_CN.md
│ ├─v06_1_file_manifest.txt
│ ├─v06_1_fixture_archive_test.csv
│ ├─v06_1_grid_nearest_wbgt_station.csv
│ ├─v06_1_nea_station_observations_schema_check.csv
│ ├─v06_1_offline_hotspot_preview.png
│ ├─V06_3_COMPLETION_REPORT_CN.md
│ ├─V06_4_1_COMPLETION_REPORT_CN.md
│ ├─v06_4_1_fixture_archive_long.csv
│ ├─V06_4_COMPLETION_REPORT_CN.md
│ ├─v06_4_fixture_archive_long.csv
│ ├─v06_4_hotspot_preview.png
│ ├─V06_COMPLETION_REPORT_CN.md
│ ├─v06_fixture_grid_nearest_stations.csv
│ ├─v06_fixture_station_observations.csv
│ ├─v06_offline_event_windows.csv
│ ├─v06_offline_hotspot_preview.png
│ ├─v06_offline_hotspot_ranking.csv
│ ├─v06_offline_hourly_grid_heatstress_forecast.csv
│ ├─v06_sample_calibration_demo.csv
│ ├─v06_sample_calibration_model.json
│ ├─v06_sample_calibration_skill.csv
│ ├─v071_risk_exposure/
│ │ ├─.Rhistory
│ │ ├─v071_final_ranking_QA_summary.md
│ │ ├─v071_grid_risk_exposure_features.geojson
│ │ ├─v071_hazard_vs_risk_comparison.csv
│ │ ├─v071_hourly_grid_heatstress_forecast_with_risk.csv
│ │ ├─v071_risk_exposure_QA_report.md
│ │ ├─v071_risk_hotspot_ranking.csv
│ │ ├─v071_risk_hotspot_ranking.geojson
│ │ ├─v071_risk_hotspot_ranking_conditioned.csv
│ │ ├─v071_risk_hotspot_ranking_conditioned_checked.csv
│ │ ├─v071_risk_hotspot_ranking_final.csv
│ │ ├─v071_risk_hotspot_ranking_final.geojson
│ │ ├─v071_risk_hotspot_ranking_gated.csv
│ │ └─v071_risk_ranking_QA_report.md
│ ├─v07_beta_final_forecast_live/
│ │ ├─v06_live_event_windows.csv
│ │ ├─v06_live_hotspot_ranking.csv
│ │ ├─v06_live_hourly_grid_heatstress_forecast.csv
│ │ ├─v06_live_openmeteo_forecast_raw.csv
│ │ ├─v07_beta1_feature_diagnostics.json
│ │ ├─v07_beta1_hazard_vs_risk_comparison.csv
│ │ ├─v07_beta1_hotspot_QA_report.md
│ │ ├─v07_beta1_hotspot_ranking_with_grid_features.csv
│ │ ├─v07_beta1_hotspot_ranking_with_grid_features.geojson
│ │ ├─v07_beta1_top_vs_all_summary.csv
│ │ ├─v07_beta_hotspot_ranking_with_grid_features.csv
│ │ └─v07_beta_hotspot_ranking_with_grid_features.geojson
│ ├─v07_beta_forecast_live/
│ │ ├─v06_live_event_windows.csv
│ │ ├─v06_live_hotspot_ranking.csv
│ │ ├─v06_live_hourly_grid_heatstress_forecast.csv
│ │ ├─v06_live_openmeteo_forecast_raw.csv
│ │ ├─v07_beta_hotspot_ranking_with_grid_features.csv
│ │ └─v07_beta_hotspot_ranking_with_grid_features.geojson
│ ├─v07_beta_gee_integration_QA_report.md
│ ├─v07_beta_impervfix_forecast_live/
│ │ ├─v06_live_event_windows.csv
│ │ ├─v06_live_hotspot_ranking.csv
│ │ ├─v06_live_hourly_grid_heatstress_forecast.csv
│ │ ├─v06_live_openmeteo_forecast_raw.csv
│ │ └─v07_beta_hotspot_ranking_with_grid_features.csv
│ ├─v07_file_manifest.txt
│ ├─v07_forecast_live/
│ │ ├─v06_live_event_windows.csv
│ │ ├─v06_live_hotspot_ranking.csv
│ │ ├─v06_live_hourly_grid_heatstress_forecast.csv
│ │ └─v06_live_openmeteo_forecast_raw.csv
│ ├─V07_GRID_FEATURES_COMPLETION_REPORT_CN.md
│ ├─v07_grid_features_QA_report.md
│ ├─v07_grid_features_QA_report_alpha.md
│ ├─v07_grid_feature_preview.png
│ ├─v07_sample_forecast_test/
│ │ ├─v06_offline_event_windows.csv
│ │ ├─v06_offline_hotspot_ranking.csv
│ │ └─v06_offline_hourly_grid_heatstress_forecast.csv
│ ├─v07_six_features_check.png
│ ├─v08_umep_with_veg_comparison/
│ │ ├─v08_proxy_vs_umep_with_veg_forecast_comparison.md
│ │ ├─v08_proxy_vs_umep_with_veg_rank_comparison.csv
│ │ └─v08_proxy_vs_umep_with_veg_rank_comparison_clean.csv
│ ├─v08_umep_with_veg_forecast_live/
│ │ ├─risk_scenarios/
│ │ │ ├─v08_risk_scenario_metadata.json
│ │ │ ├─v08_risk_scenario_QA_report.md
│ │ │ ├─v08_risk_scenario_rankings.csv
│ │ │ ├─v08_risk_scenario_rankings.geojson
│ │ │ ├─v08_risk_scenario_topn_overlap.csv
│ │ │ ├─v08_risk_scenario_topn_summary.csv
│ │ │ └─v08_risk_scenario_top_cells.csv
│ │ ├─v06_live_event_windows.csv
│ │ ├─v06_live_hotspot_ranking.csv
│ │ ├─v06_live_hourly_grid_heatstress_forecast.csv
│ │ ├─v06_live_openmeteo_forecast_raw.csv
│ │ ├─v08_risk_hotspot_ranking_conditioned.csv
│ │ ├─v08_risk_hotspot_ranking_conditioned.geojson
│ │ ├─v08_risk_hotspot_ranking_conditioned_social.csv
│ │ ├─v08_umep_with_veg_hotspot_QA_report.md
│ │ ├─v08_umep_with_veg_hotspot_ranking_with_grid_features.csv
│ │ └─v08_umep_with_veg_hotspot_ranking_with_grid_features.geojson
│ ├─v08_umep_with_veg_morphology_merge_QA.json
│ ├─v08_umep_with_veg_morphology_merge_QA.md
│ ├─v08_umep_with_veg_morphology_uploaded_QA_report.md
│ ├─v09_alpha_calibration/
│ │ ├─v09_archive_QA_report.md
│ │ ├─v09_archive_variable_summary.csv
│ │ ├─v09_baseline_calibration_diagnostics.md
│ │ ├─v09_baseline_event_detection_metrics.csv
│ │ ├─v09_baseline_metrics_by_station.csv
│ │ ├─v09_baseline_overall_metrics.csv
│ │ ├─v09_historical_forecast_fetch_report.md
│ │ ├─v09_raw_proxy_baseline_metrics.csv
│ │ ├─v09_raw_proxy_metrics_by_station.csv
│ │ ├─v09_residual_by_hour.csv
│ │ ├─v09_wbgt_category_counts.csv
│ │ ├─v09_wbgt_pairing_QA_report.md
│ │ └─v09_wbgt_station_summary.csv
│ ├─v09_beta_calibration/
│ │ ├─v09_beta_calibration_report.md
│ │ ├─v09_beta_calibration_report.zip
│ │ ├─v09_beta_engineered_pairs.csv
│ │ ├─v09_beta_event_detection_metrics.csv
│ │ ├─v09_beta_focus_station_timeline.csv
│ │ ├─v09_beta_linear_slope_diagnostics.csv
│ │ ├─v09_beta_metrics_by_station.csv
│ │ ├─v09_beta_model_metadata.csv
│ │ ├─v09_beta_model_metrics.csv
│ │ ├─v09_beta_predictions_long.csv
│ │ └─v09_beta_residual_by_hour.csv
│ ├─v09_beta_threshold_scan/
│ │ ├─v09_beta_threshold_scan_focus_station_timeline.csv
│ │ ├─v09_beta_threshold_scan_metrics.csv
│ │ ├─v09_beta_threshold_scan_report.md
│ │ └─v09_beta_threshold_scan_summary.csv
│ ├─v09_gamma_analysis/
│ │ ├─OpenHeat_v09_gamma_final_report_CN.md
│ │ ├─v09_gamma_focus_cell_solweig_vs_proxy.csv
│ │ ├─v09_gamma_solweig_vs_proxy_per_cell.csv
│ │ ├─v09_gamma_solweig_vs_proxy_REPORT.md
│ │ └─v09_gamma_tiletype_hour_summary.csv
│ ├─v09_gamma_qa/
│ │ ├─v09_building_completeness_per_tile.csv
│ │ ├─v09_osm_buildings.geojson
│ │ ├─v09_overhead_cell_QA_report.md
│ │ ├─v09_overhead_structures.geojson
│ │ ├─v09_overhead_structures_footprints.geojson
│ │ ├─v09_overhead_structures_per_cell.csv
│ │ ├─v09_overhead_structures_per_cell.geojson
│ │ └─v09_overhead_structures_per_tile.csv
│ ├─v09_solweig/
│ │ ├─v09_solweig_tmrt_grid_summary_overhead_aware.csv
│ │ └─v09_solweig_tmrt_grid_summary_overhead_aware_report.md
│ ├─v10_dsm_audit/
│ │ └─.gitkeep
│ ├─v10_morphology/
│ │ └─.gitkeep
│ ├─v10_ranking_audit/
│ │ └─.gitkeep
│ └─v10_solweig/
│   └─.gitkeep
├─pyproject.toml
├─qgis/
│ ├─cliped_polygon.cpg
│ ├─cliped_polygon.csv
│ ├─cliped_polygon.dbf
│ ├─cliped_polygon.prj
│ ├─cliped_polygon.qmd
│ ├─cliped_polygon.shp
│ ├─cliped_polygon.shx
│ ├─cliped_polygon2.0.cpg
│ ├─cliped_polygon2.0.dbf
│ ├─cliped_polygon2.0.prj
│ ├─cliped_polygon2.0.shp
│ ├─cliped_polygon2.0.shx
│ ├─cliped_roadline.cpg
│ ├─cliped_roadline.dbf
│ ├─cliped_roadline.prj
│ ├─cliped_roadline.shp
│ ├─cliped_roadline.shx
│ ├─cliped_road_multiline.cpg
│ ├─cliped_road_multiline.dbf
│ ├─cliped_road_multiline.prj
│ ├─cliped_road_multiline.shp
│ ├─cliped_road_multiline.shx
│ ├─Conditioned risk-priority map.png
│ ├─heat Hazard.png
│ └─openheat.qgz
├─README/
│ └─README_V09_BETA_EXTENSION_GAMMA_CN.md
├─README_CN.md
├─README_V09_BETA_CN.md
├─requirements.txt
├─requirements_v07_geospatial.txt
├─requirements_v09_beta.txt
├─scripts/
│ ├─archive_nea_observations.py
│ ├─check_features.py
│ ├─debug_fetch_wbgt_raw.py
│ ├─download_v071_safely.bat
│ ├─make_gitignore.py
│ ├─patch_v071_census_parser.py
│ ├─patch_v071_census_parser_v2.py
│ ├─plot_v06_hotspots.py
│ ├─run_heatwave_hotspot_sample.py
│ ├─run_live_forecast_v06.py
│ ├─run_nea_api_schema_check.py
│ ├─run_v09_archive_loop.bat
│ ├─v071_apply_risk_to_forecast.py
│ ├─v071_build_risk_exposure_features.py
│ ├─v071_build_risk_exposure_features.py.bak_v071_census_parser_v2
│ ├─v071_download_risk_exposure_data.py
│ ├─v071_run_full_pipeline.py
│ ├─v07_beta1_compare_rankings.py
│ ├─v07_beta1_finalize_forecast_outputs.py
│ ├─v07_beta_apply_gee_to_grid_features.py
│ ├─v07_beta_fix_impervious.py
│ ├─v07_build_grid_features.py
│ ├─v07_download_official_geodata.py
│ ├─v07_extract_osm_roads_water.py
│ ├─v08_apply_umep_morphology_with_veg.py
│ ├─v08_clip_buildings_to_aoi.py
│ ├─v08_compare_proxy_vs_umep_with_veg_forecast.py
│ ├─v08_diagnose_ura_vs_hdb3d.py
│ ├─v08_finalize_risk_scenarios_hotfix.py
│ ├─v08_finalize_umep_with_veg_forecast_outputs.py
│ ├─v08_generate_risk_scenarios.py
│ ├─v08_hdb3d_to_geojson.py
│ ├─v08_make_conditioned_risk_ranking.py
│ ├─v08_merge_buildings_with_height.py
│ ├─v08_prepare_vegetation_dsm.py
│ ├─v08_rasterize_building_dsm.py
│ ├─v08_run_umep_with_veg_forecast_workflow.bat
│ ├─v08_zonal_umep_to_grid.py
│ ├─v08_zonal_umep_to_grid_with_veg.py
│ ├─v09_archive_qa.py
│ ├─v09_beta_fit_calibration_models.py
│ ├─v09_beta_make_conclusion_report.py
│ ├─v09_beta_run_pipeline.bat
│ ├─v09_beta_threshold_scan.py
│ ├─v09_build_wbgt_station_pairs.py
│ ├─v09_common.py
│ ├─v09_evaluate_wbgt_pairs_baseline.py
│ ├─v09_fetch_historical_forecast_for_archive.py
│ ├─v09_gamma_aggregate_solweig_tmrt.py
│ ├─v09_gamma_aggregate_solweig_tmrt_overhead_aware.py
│ ├─v09_gamma_analyze_solweig_vs_proxy.py
│ ├─v09_gamma_build_overhead_cell_qa.py
│ ├─v09_gamma_check_building_completeness.py
│ ├─v09_gamma_check_overhead_structures.py
│ ├─v09_gamma_check_per_hour_tmrt.py
│ ├─v09_gamma_clip_tiles_overhead_aware.py
│ ├─v09_gamma_clip_tile_rasters.py
│ ├─v09_gamma_compare_tmrt_proxy_vs_solweig.py
│ ├─v09_gamma_consolidate_per_hour_tmrt.py
│ ├─v09_gamma_make_flat_dem.py
│ ├─v09_gamma_make_umep_met.py
│ ├─v09_gamma_overhead_aware_post_umep_pipeline.bat
│ ├─v09_gamma_overhead_aware_pre_umep_pipeline.bat
│ ├─v09_gamma_run_post_umep_pipeline.bat
│ ├─v09_gamma_run_pre_umep_pipeline.bat
│ ├─v09_gamma_select_solweig_tiles.py
│ ├─v09_gamma_select_tiles_overhead_aware.py
│ ├─v09_gamma_split_met_per_hour.py
│ ├─v09_run_alpha_pipeline.bat
│ └─__pycache__/
│   ├─v071_build_risk_exposure_features.cpython-313.pyc
│   ├─v07_build_grid_features.cpython-313.pyc
│   └─v09_common.cpython-310.pyc
├─src/
│ ├─openheat_forecast/
│ │ ├─calibration.py
│ │ ├─data_sources.py
│ │ ├─hotspot_engine.py
│ │ ├─live_api.py
│ │ ├─live_pipeline.py
│ │ ├─thermal_indices.py
│ │ ├─time_utils.py
│ │ ├─validation.py
│ │ ├─__init__.py
│ │ └─__pycache__/
│ │   ├─hotspot_engine.cpython-310.pyc
│ │   ├─hotspot_engine.cpython-313.pyc
│ │   ├─live_api.cpython-310.pyc
│ │   ├─live_api.cpython-313.pyc
│ │   ├─live_pipeline.cpython-310.pyc
│ │   ├─live_pipeline.cpython-313.pyc
│ │   ├─thermal_indices.cpython-310.pyc
│ │   ├─thermal_indices.cpython-313.pyc
│ │   ├─time_utils.cpython-310.pyc
│ │   ├─time_utils.cpython-313.pyc
│ │   ├─__init__.cpython-310.pyc
│ │   └─__init__.cpython-313.pyc
│ ├─openheat_grid/
│ │ ├─features.py
│ │ ├─geospatial.py
│ │ ├─grid.py
│ │ ├─provenance.py
│ │ ├─__init__.py
│ │ └─__pycache__/
│ │   ├─features.cpython-310.pyc
│ │   ├─features.cpython-313.pyc
│ │   ├─geospatial.cpython-310.pyc
│ │   ├─geospatial.cpython-313.pyc
│ │   ├─grid.cpython-310.pyc
│ │   ├─grid.cpython-313.pyc
│ │   ├─provenance.cpython-310.pyc
│ │   ├─provenance.cpython-313.pyc
│ │   ├─__init__.cpython-310.pyc
│ │   └─__init__.cpython-313.pyc
│ └─openheat_v10/
└─tests/
  ├─test_engine.py
  ├─test_v06_1_feedback_optimisations.py
  ├─test_v06_3_wbgt_v2_schema.py
  ├─test_v06_4_1_source_review_patch.py
  ├─test_v06_4_archive_and_alerts.py
  ├─test_v06_live_api_and_calibration.py
  ├─test_v071_risk_helpers.py
  ├─test_v07_grid_features.py
  └─__pycache__/
    ├─test_v071_risk_helpers.cpython-313-pytest-9.0.2.pyc
    └─test_v07_grid_features.cpython-313-pytest-9.0.2.pyc