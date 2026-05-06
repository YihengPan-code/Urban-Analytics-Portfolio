# Migration notes: v0.4 -> v0.5

## 为什么升级

v0.4 主要解决绿色告示牌、窗户玻璃、人工绿色物体误识别。实际测试后，这类误识别已经显著减少，但公园场景中仍有较多下半幅地面误识别：阳光铺装、灰绿硬质地面、青苔地面、压实土壤等。

## 核心变化

v0.5 加入 `ground_quality_removed_mask()`，在 VVI candidate 形成之后进行第二次地面质量过滤。

v0.4:

```text
semantic vegetation + recovery
→ horizontal ground guard
→ panel/sign/glass guard
→ VVI/GVI
```

v0.5:

```text
semantic vegetation + recovery
→ horizontal ground guard
→ lower-frame ground quality guard
→ panel/sign/glass guard
→ VVI/GVI
```

## 新增 API 参数

```text
ground_filter_mode: off | balanced | strict
enable_ground_quality_guard: true | false
ground_quality_bottom_start: float
front_ground_start: float
ground_veg_prob_margin: float
ground_negative_prob_min: float
```

## 推荐迁移方式

旧 v0.4 命令：

```bash
python adaptive_gvi_vvi_backend_v0_4.py --input ./photos --output ./out --segmenter hf --ground-guard strong
```

新 v0.5 命令：

```bash
python adaptive_gvi_vvi_backend_v0_5.py \
  --input ./photos \
  --output ./out_v05 \
  --segmenter hf \
  --ground-guard strong \
  --ground-filter-mode balanced \
  --artifact-guard strong
```

如果地面仍然误判：

```bash
--ground-filter-mode strict --ground-veg-prob-margin 0.16 --front-ground-start 0.62
```

如果真实草地被删太多：

```bash
--ground-filter-mode balanced --front-ground-start 0.75 --ground-veg-prob-margin 0.06
```
