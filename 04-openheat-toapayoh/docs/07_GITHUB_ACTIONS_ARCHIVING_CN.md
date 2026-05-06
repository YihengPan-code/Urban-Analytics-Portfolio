# 用 GitHub Actions 长期归档 NEA/WBGT observations

v0.6.1 增加了 `.github/workflows/archive_nea_observations.yml`，用于自动拉取 NEA realtime observations 并追加到：

```text
data/archive/nea_realtime_observations.csv
```

## 快速启用

1. 把项目 push 到 GitHub。
2. 进入 GitHub repo 的 `Actions` 页面，确认 workflow 已启用。
3. 手动点一次 `Run workflow`，确认能运行。
4. 等待 schedule 每 15 分钟执行。

## 本地等价命令

```bash
python scripts/archive_nea_observations.py --mode live --api-version v1
```

## 不需要 API key

v0.6.1 默认不要求 `DATA_GOV_SG_API_KEY`。

如果以后 data.gov.sg 读接口策略改变，或者你注册了更高 rate limit，可以在 GitHub Secrets 中设置：

```text
DATA_GOV_SG_API_KEY
```

workflow 会自动作为环境变量传给脚本。

## 什么时候可以开始 calibration？

最低：

```text
≥ 30 paired observations
≥ 2 unique days
至少包含 WBGT ≥ 31°C 的 moderate period
```

更理想：

```text
跨 sunny / overcast / pre-thundershower regimes
包含 WBGT ≥ 33°C high heat-stress period
覆盖多个时段：late morning, noon, afternoon
```

## 重要提醒

每 15 分钟 commit 一次 CSV 适合 prototype，但不适合长期生产系统。长期版本建议：

```text
PostgreSQL/PostGIS
DuckDB/Parquet
S3/R2/Object Storage
Google Cloud Storage
```

GitHub repo 适合展示，不适合无限增长的数据仓库。
