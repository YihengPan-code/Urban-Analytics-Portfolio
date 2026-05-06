# Adaptive GVI/VVI Calculator v0.7

This version refines v0.6 by targeting the remaining **VVI false positives on sunlit / mossy / compacted lower-ground surfaces**.

## Main change from v0.6

v0.6 improved GVI by adding a semantic-gated wide HSV layer for dark / steel-green shadow leaves. However, in strong-sun park scenes the semantic model can still label lower-frame paving, mossy ground or compacted soil as vegetation, inflating VVI.

v0.7 adds a final **VVI-only lower-ground cleanup**:

```text
final GVI is computed first
    ↓
look only at lower-frame VVI-only pixels
    ↓
remove pixels/components that fail grass/leaf quality tests
    ↓
GVI remains unchanged; VVI is reduced where false ground vegetation occurs
```

This pass never removes GVI pixels. It is intended to fix blue/cyan VVI-only ground artifacts in overlays while preserving the GVI result.

## Recommended settings for the user-provided park images

```text
Preset: Semantic Shadow / Steel-green GVI
Ground guard: Strong
Ground quality filter: Balanced
VVI-only ground cleanup: Balanced
Artifact guard: Strong
Semantic-only GVI expansion: On
Muted grey-green as GVI: Off
```

If sunlit ground still enters VVI:

```text
VVI-only ground cleanup: Strict
Ground quality filter: Strict
VVI cleanup starts at y ≥ 0.40–0.44
VVI front strict zone y ≥ 0.56–0.62
```

Use `Ultra` only when VVI is clearly inflated and you accept a conservative VVI.

## Run API

```bash
pip install -r requirements-v0.7.txt
uvicorn api_server_v0_7:app --reload --host 127.0.0.1 --port 8000
```

Then open:

```text
frontend_adaptive_gvi_vvi_v0_7.html
```

## Batch CLI

```bash
python adaptive_gvi_vvi_backend_v0_7.py \
  --input ./photos \
  --output ./out_v07 \
  --segmenter hf \
  --preset semantic_shadow \
  --ground-guard strong \
  --ground-filter-mode balanced \
  --vvi-ground-cleanup-mode balanced \
  --artifact-guard strong
```

More aggressive VVI ground cleanup:

```bash
python adaptive_gvi_vvi_backend_v0_7.py \
  --input ./photos \
  --output ./out_v07_strict \
  --segmenter hf \
  --preset semantic_shadow \
  --ground-guard strong \
  --ground-filter-mode strict \
  --vvi-ground-cleanup-mode strict \
  --artifact-guard strong
```

## New output field

```text
vvi_ground_cleanup_removed_pct
```

This is the percentage of pixels removed by the new post-GVI VVI-only cleanup. If this value rises while GVI stays stable, the filter is doing exactly what it is designed to do.

## Overlay colours

```text
Green = final GVI
Cyan/blue = semantic VVI-only
Orange = recovery VVI-only
Red = removed artifacts / ground / sign / glass / high-vis
```
