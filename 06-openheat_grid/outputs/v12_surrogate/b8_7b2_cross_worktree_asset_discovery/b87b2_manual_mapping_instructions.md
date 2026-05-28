# B8.7b.2 Manual Mapping Instructions

Fill `b87b2_manual_mapping_template.csv` only for cells marked unresolved or ambiguous.

Valid `user_decision` values:

- `use`: use `user_selected_asset_folder` for the future B87C prepackage lane.
- `missing`: confirmed no local asset folder exists.
- `ambiguous`: multiple folders remain plausible.
- `exclude`: exclude the cell from a future package decision.
- `unknown`: leave unresolved pending local review.

Rules: provide paths only as metadata. Do not copy assets into Git. Do not create `.tif`, `.tiff`, `.vrt`, `.asc`, `.img`, `.nc`, or `.grib` files. This file is not a run manifest and does not authorize QGIS or SOLWEIG.
