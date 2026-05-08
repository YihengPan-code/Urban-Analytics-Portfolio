// OpenHeat-ToaPayoh v0.7-beta optional Earth Engine export
// Purpose: export GHSL height + Dynamic World tree/built/water fractions + Sentinel-2 NDVI by 100m grid cell.
// Step 1: upload data/grid/toa_payoh_grid_v07.geojson to Earth Engine as an asset.
// Step 2: replace the asset path below.
// Step 3: run and export CSV to Google Drive.

var grid = ee.FeatureCollection('users/YOUR_USERNAME/toa_payoh_grid_v07');  // TODO: replace
var aoi = grid.geometry();

// GHSL 2018 average building height, 100m.
var ghsl = ee.Image('JRC/GHSL/P2023A/GHS_BUILT_H/2018').select('built_height');

// Dynamic World 10m land-cover probabilities. Choose recent 12 months; adjust dates if needed.
var start = '2025-01-01';
var end = '2025-12-31';
var dw = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
  .filterBounds(aoi)
  .filterDate(start, end)
  .select(['trees', 'built', 'grass', 'water'])
  .mean();

// Sentinel-2 SR Harmonized NDVI, cloud-filtered simple median.
function maskS2sr(image) {
  var scl = image.select('SCL');
  var mask = scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)).and(scl.neq(11));
  return image.updateMask(mask);
}
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(aoi)
  .filterDate(start, end)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 60))
  .map(maskS2sr)
  .median();
var ndvi = s2.normalizedDifference(['B8', 'B4']).rename('ndvi_mean');

var stack = ghsl.rename('mean_building_height_m')
  .addBands(dw.select('trees').rename('tree_canopy_fraction'))
  .addBands(dw.select('built').rename('built_up_fraction'))
  .addBands(dw.select('grass').rename('grass_fraction'))
  .addBands(dw.select('water').rename('water_fraction'))
  .addBands(ndvi);

var reduced = stack.reduceRegions({
  collection: grid,
  reducer: ee.Reducer.mean(),
  scale: 10,
  crs: 'EPSG:4326',
  tileScale: 4
});

Export.table.toDrive({
  collection: reduced,
  description: 'openheat_v07_height_vegetation_by_grid',
  fileFormat: 'CSV'
});

Map.centerObject(aoi, 14);
Map.addLayer(grid, {}, 'OpenHeat grid');
Map.addLayer(dw.select('trees'), {min: 0, max: 1, palette: ['white', 'green']}, 'Dynamic World trees');
Map.addLayer(ndvi, {min: 0, max: 0.8, palette: ['white', 'lime', 'darkgreen']}, 'NDVI');
