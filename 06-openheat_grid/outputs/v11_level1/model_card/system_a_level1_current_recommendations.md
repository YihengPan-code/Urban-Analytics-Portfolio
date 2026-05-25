# System A Level 1 当前推荐

## 当前回归分数

使用 `M4_like_inertia_ridge` 作为当前默认 `wbgt_a_score_c`。推荐措辞是“WBGT-like background heat-stress score”或“Level 1 背景热应激分数”，不要写成 validated local WBGT。

## 当前 P_ge31 诊断伴随输出

使用 `M4_like_inertia_ridge + logistic_score_calibration + blocked_date_calibration`，输出名为 `p_ge31_diagnostic`。它表示回顾性诊断概率：官方 WBGT >=31 的概率信号。它不是官方预警概率，也不是前瞻 forecast。

## 不应使用

- 不使用 ge33 作为运营输出；ge33 只保留探索性状态。
- 不把 M7_like、L1_full_dynamic、L1_proxy_radiation 提升为默认，只列为敏感性候选。
- 不输出 `cell_id`、`local_wbgt_c`、`wbgt_cell_c`、`delta_wbgt_cell`、`risk_score`、`m_rad`、`tmrt`、`solweig`、`exposure` 或 `vulnerability`。
- 不把 station residual 当成 cell modifier。
- 不创建完整预测大导出；Sprint 4A 只允许小样本或 schema。

## 下一步

1. Sprint 4B: 设计 prospective forecast evaluation。
2. Sprint 4C: 加固 `p_ge31_diagnostic` 导出、reliability 和质量标记。
3. Advanced formula implementation 作为独立 track，不回填本模型卡。
4. Level 2 station-context preflight 稍后再做。
5. 模型族比较等输出/前瞻边界清楚后再进入。

## 可提交内容

可提交本 Sprint 4A 的小型文档、YAML 契约、证据 ledger、claim boundary matrix、recommendations、integration report，以及 <=200 行的样本 CSV。

## 应保持本地或不纳入本 sprint 的内容

不要提交大预测导出、raw archive、raster/SOLWEIG/QGIS/v12 产物、patch zip packages、任何 `.tif/.tiff`，以及非本 sprint 需要的历史未跟踪文件。
