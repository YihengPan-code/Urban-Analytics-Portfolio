# Future Codex Prompt: B8.6g4 External/Vector Acquisition

Work inside the OpenHeat-ToaPayoh project subdirectory.

Lane: B8.6g4 external/vector acquisition.

Acquire or integrate source-backed vector data for connected shade corridor,
pedestrian footpath/walkway network, covered walkway/sheltered path geometry,
building footprint/height/canyon geometry, tree canopy, tree/building
interaction, and water/park/road/hardscape edge context.

Validity requirements:
- Connected shade corridor requires line/polygon network geometry or an
  explicit vector-derived connectivity table.
- Do not infer corridor continuity from centroid distance, generic shade
  fraction, or compact cell fractions.
- Covered walkway must use covered/sheltered tags or equivalent source.
- Tree/building interaction needs both tree canopy and building geometry, or a
  trusted vector-derived interaction table.

Forbidden:
No raster reads/writes/copies, no QGIS/SOLWEIG, no AOI-wide prediction, no B9,
no local WBGT, no hazard_score, no risk_score, no exposure/vulnerability score,
no observed-truth or causal claims, no Tmrt-to-WBGT conversion, and no System
A/B coupling.
