# OpenHeat v10-gamma robustness audit patch

解压到项目根目录后运行：

```bat
scripts\v10_run_gamma_robustness_audit.bat
```

这个 patch 只读已有 v10-gamma 输出，不修改任何模型文件。它用于：

- 修正 TP_0315 分类歧义；
- 说明 false-positive candidate 定义与 v10 信息的依赖关系；
- 计算 FP candidates vs non-FP old-top20 cells 的 leaving-rate baseline；
- 检查 fully-built / dense cells，例如 TP_0945。

主要输出：

```text
outputs/v10_gamma_robustness/v10_gamma_robustness_audit_report.md
outputs/v10_gamma_robustness/v10_gamma_final_findings_addendum.md
```
