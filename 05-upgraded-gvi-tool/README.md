# Adaptive GVI/VVI Calculator v0.5

v0.5 是在 v0.4 precision 版基础上的 **ground-refinement** 修正版。

你反馈 v0.4 已经明显减少了绿色告示牌、玻璃等人工物误识别，但在公园场景中仍有一个集中问题：

- 被阳光照射的铺装 / 硬质地面
- 带青苔或灰绿表面的地面
- 低饱和、灰绿、褐绿的地面阴影区域

这些区域有时会被 semantic segmentation 判成 grass / vegetation，从而进入 VVI，部分又进入 GVI。

v0.5 的核心目标是：**在不大幅牺牲真实草地 / 树木识别的前提下，进一步压低下半幅地面误识别。**

---

## 核心变化

### 1. 新增 Ground Quality Filter

v0.4 已经有 ground guard，但它主要在 VVI 生成前排除显而易见的道路、地面和平滑阳光铺装。

v0.5 新增第二道后处理：

```text
semantic VVI candidate
   ↓
second-pass lower-frame ground quality check
   ↓
final VVI / GVI
```

这一步专门检查画面下半部分的“疑似草地”是否真的有足够的植被绿色证据。

它综合使用：

- ExG / normalized green excess
- Lab a* greenness
- green channel ratio
- saturation
- vegetation probability vs ground/artificial probability margin
- lower-frame / foreground location
- connected component geometry
- tree/shrub/canopy label protection

### 2. 不再简单相信“模型说是 grass”

如果语义模型把青苔铺装或阳光地面判成 grass，v0.4 仍可能保留。

v0.5 会继续追问：

```text
这个区域虽然语义上像 vegetation，
但它在颜色质量、语义概率边际和前景地面几何上，是否真的像草地？
```

如果答案是否定的，它会被标红移除。

### 3. 保护树木和灌木

地面过滤只针对 lower-frame grass/paving ambiguity。带有 tree / shrub / bush / palm / trunk / branch 等标签的区域会被保护，避免把下方树干、大树根、低矮树冠误删。

---

## 文件结构

```text
adaptive_gvi_vvi_v0_5/
  adaptive_gvi_vvi_backend_v0_5.py
  semantic_segmentation_hf_v0_5.py
  api_server_v0_5.py
  frontend_adaptive_gvi_vvi_v0_5.html
  requirements-v0.5.txt
  README.md
  MIGRATION_NOTES_v0_4_to_v0_5.md
```

---

## 安装和运行

```bash
cd adaptive_gvi_vvi_v0_5
python -m venv .venv
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

安装依赖：

```bash
pip install -r requirements-v0.5.txt
```

启动后端：

```bash
uvicorn api_server_v0_5:app --reload --host 127.0.0.1 --port 8000
```

然后打开：

```text
frontend_adaptive_gvi_vvi_v0_5.html
```

---

## 推荐参数

### 默认推荐

```text
Preset: Standard
Recovery mode: Balanced
Ground guard: Strong
Ground quality filter: Balanced
Artifact guard: Strong
Muted grey-green as GVI: Off
GVI requires semantic support: On
Hard negative veto: On
Rectangular panel guard: On
Ground filter starts at y ≥ 0.46
Front-ground strict zone y ≥ 0.68
Ground semantic margin ≥ 0.10
```

### 如果阳光地面 / 青苔地面仍然偏多

```text
Ground quality filter: Strict
Ground filter starts at y ≥ 0.42–0.46
Front-ground strict zone y ≥ 0.60–0.66
Ground semantic margin ≥ 0.14–0.18
Preset: Sunny 或 Standard
Muted grey-green as GVI: Off
```

### 如果真实草地被删太多

```text
Ground quality filter: Balanced
Ground filter starts at y ≥ 0.50–0.55
Front-ground strict zone y ≥ 0.72–0.78
Ground semantic margin ≥ 0.06–0.10
Ground guard: Balanced
```

### 如果围栏后植物又开始漏检

```text
Recovery mode: Balanced
Soft recovery prob: 0.10–0.12
Safe recovery prob: 0.08–0.10
Recovery radius: 14–18
Ground quality filter: Balanced，不建议直接关掉
```

---

## 命令行批量运行

默认语义模型：

```bash
python adaptive_gvi_vvi_backend_v0_5.py \
  --input ./photos \
  --output ./out_v05 \
  --segmenter hf \
  --preset standard \
  --recovery-mode balanced \
  --ground-guard strong \
  --ground-filter-mode balanced \
  --artifact-guard strong
```

更强地面过滤：

```bash
python adaptive_gvi_vvi_backend_v0_5.py \
  --input ./photos \
  --output ./out_v05_strict_ground \
  --segmenter hf \
  --preset sunny \
  --recovery-mode balanced \
  --ground-guard strong \
  --ground-filter-mode strict \
  --artifact-guard strong \
  --ground-veg-prob-margin 0.16 \
  --front-ground-start 0.62
```

---

## 输出字段重点

CSV 新增字段：

```text
ground_quality_removed_pct
component_artifact_removed_pct
removed_artifact_pct
```

其中：

```text
ground_quality_removed_pct
```

表示 v0.5 新增地面质量过滤移除的比例。这个数值如果明显上升，说明此前的误识别主要确实来自下半幅地面。

---

## Overlay 颜色

```text
绿色 = GVI-green
蓝青色 = semantic VVI-only
橙色 = recovery VVI-only
红色 = removed artifacts / ground / high-vis / panel / glass
```

v0.5 测试时重点看红色区域：

- 阳光地面是否变红？
- 青苔铺装是否变红？
- 真草地是否仍为绿色或蓝青色？
- 树冠、树干、灌木是否仍保留？

---

## 注意

v0.5 比 v0.4 更适合你当前这批公园照片，但它不是“绝对更宽松”或“绝对更严格”，而是加入了更有针对性的地面过滤层。

如果后续数据中出现很多真实近景草地，建议使用 Balanced；如果是街道、人行道、公园路径很多的路线，建议使用 Strict。
