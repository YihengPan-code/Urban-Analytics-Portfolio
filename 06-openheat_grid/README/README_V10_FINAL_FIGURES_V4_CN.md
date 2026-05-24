# OpenHeat v10 final figures / maps package v4

这版基于你的最新反馈做了精修：

## 修复点

1. **Chart 00 workflow schematic**
   - 修复编号圆点与文字重叠的问题。
   - 重写 box 内部布局，badge 改成固定小尺寸。
   - 修正 robustness box 与箭头/说明文字遮挡。

2. **Chart 01 恢复上一版单图折线风格**
   - 不再使用 v3 的 small-multiples。
   - 保留上一版你认为更好的整体折线图逻辑。
   - 仅微调上下边距，避免标题/footer 轻微冲突。

3. **Satellite basemap bug 修复**
   - 修复 `'<=' not supported between instances of 'int' and 'NoneType'`。
   - 原因是 `contextily.add_basemap(..., zoom=None)` 在部分版本会报错。
   - v4 中 `zoom: "auto"` 或 `null` 都会自动省略 zoom 参数，让 contextily 自己选择。

4. **地图布局保持 v3 逻辑**
   - 比例尺：右下角。
   - 指北针：右上角。
   - 主题层透明叠加到卫星底图。

## 关于 libpng iCCP warning

`libpng warning: iCCP: known incorrect sRGB profile` 通常来自在线瓦片 PNG 的嵌入色彩配置文件。
它不会影响图像数值、坐标或地图渲染结果。v4 修复的是真正导致底图加载失败的 `zoom=None` 错误。

如果你不想看到这些 warning，可以临时关闭卫星底图：

```json
"basemap": { "enabled": false }
```

## 运行方式

在项目根目录运行：

```bat
scripts\v10_run_final_figures_pipeline_v4.bat
```

输出目录：

```text
outputs/v10_final_figures_v4/
```

## 如果卫星底图没有出现

请安装：

```bash
pip install contextily xyzservices
```

并确认网络可以访问瓦片服务。
