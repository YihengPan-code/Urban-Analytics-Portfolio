# 新对话启动提示词

复制下面内容到新的 ChatGPT 对话中，并同时上传建议文件。

---

我正在继续 OpenHeat-ToaPayoh 项目。当前项目根目录是：

`C:\Users\CloudStar\Documents\GitHub\Urban-Analytics-Portfolio\06-openheat_grid`

请先阅读我上传的这些文件：

1. `OPENHEAT_HANDOFF_CN.md`
2. `docs/v09_freeze/V09_FREEZE_NOTE_CN.md`
3. `docs/v09_freeze/V09_REVISED_FINDINGS_CN.md`
4. `docs/v09_freeze/33_V09_BUILDING_DSM_GAP_AUDIT_CN.md`
5. `directory_structure.md`

项目当前状态：v0.9 已 freeze。v0.9 发现 HDB3D+URA building DSM 相对 OSM-mapped building area completeness 只有约 25.8%，并且 high hazard tiles 往往是 DSM coverage gap regions。因此 v0.7–v0.9 的 hazard ranking 不能再视为最终真实热风险排序，只能作为 current-DSM baseline。

我现在进入 v1.0，目标是构建 augmented multi-source building DSM。第一阶段先做 HDB3D + URA + OSM augmented DSM pilot，然后重算 morphology features、重跑 hazard ranking，并做 rank-shift audit，识别旧 ranking 中由 DSM coverage gap 造成的 false positives。

请遵守以下规则：

- 不要继续把旧 `hazard_rank_true_v08` 当最终热风险结果。
- 不要覆盖 v08/v09 文件；v10 新结果都写进 `data/features_3d/v10/`、`data/rasters/v10/`、`data/grid/v10/`、`outputs/v10_*`、`docs/v10/`。
- v1.0 优先级是 augmented building DSM，不是 ML、dashboard 或全新加坡扩展。
- 先帮我做 v10-alpha：OSM building extraction / standardisation / dedup / height imputation / rasterize / completeness audit / rank-shift audit。
