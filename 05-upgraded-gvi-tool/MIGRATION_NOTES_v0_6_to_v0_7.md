# Migration notes: v0.6 → v0.7

## Why v0.7 exists

v0.6 solved a GVI undercount issue for dark / steel-green shadow leaves by adding semantic-gated wide HSV expansion. In testing, the remaining problem was not GVI but VVI: sunlit ground, mossy paths and compacted soil could still be labelled as vegetation by the semantic model.

## What changed

v0.7 adds:

- `enable_vvi_ground_cleanup`
- `vvi_ground_cleanup_mode`: `off | balanced | strict | ultra`
- `vvi_cleanup_bottom_start`
- `vvi_cleanup_front_start`
- `vvi_cleanup_green_ratio_min`
- `vvi_cleanup_exg_min`
- `vvi_cleanup_lab_min`
- result field: `vvi_ground_cleanup_removed_pct`

The cleanup is applied **after** GVI is computed and only targets **VVI-only lower-ground pixels**. This means it can reduce inflated VVI without reducing GVI.

## Suggested use

Start with:

```text
vvi_ground_cleanup_mode = balanced
```

Use strict if cyan/blue ground remains. Use ultra only for difficult audit cases.
