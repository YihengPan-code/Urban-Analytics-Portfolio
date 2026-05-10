# OpenHeat v10-gamma robustness audit patch

## 文件

```text
configs/v10/v10_gamma_robustness_config.example.json
scripts/v10_gamma_robustness_audit.py
scripts/v10_run_gamma_robustness_audit.bat
docs/v10/V10_GAMMA_ROBUSTNESS_AUDIT_GUIDE_CN.md
```

## 用法

解压到项目根目录后运行：

```bat
scripts\v10_run_gamma_robustness_audit.bat
```

输出在：

```text
outputs/v10_gamma_robustness/
```

## 作用

这个 patch 不改任何模型输出，只生成 v10-gamma robustness audit，帮助你把 v10-gamma report 修订到 dissertation-ready。
