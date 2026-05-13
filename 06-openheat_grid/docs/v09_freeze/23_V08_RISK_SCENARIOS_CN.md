# OpenHeat v0.8 risk scenarios

这个补丁新增 `scripts/v08_generate_risk_scenarios.py`，用于从 v0.8 UMEP+vegetation 的 heat-hazard ranking 中生成三套风险优先级情景：

1. `hazard_rank_true_v08`：纯热危险排名。
2. `risk_rank_v08_conditioned`：保守型 heat-hazard-first 风险排名。
3. `risk_rank_v08_social_conditioned`：社会敏感型 hazard-conditioned 风险排名。
4. `risk_rank_v08_candidate_policy`：先筛选 top hazard candidate，再按 hazard + vulnerability + exposure 重排的政策情景。

## 默认运行

```bat
python scripts\v08_generate_risk_scenarios.py
```

默认输入：

```text
outputs/v08_umep_with_veg_forecast_live/v08_risk_hotspot_ranking_conditioned.csv
```

默认输出：

```text
outputs/v08_umep_with_veg_forecast_live/risk_scenarios/
```

## 推荐解释

- `hazard_rank_true_v08` 用于说明哪里物理热压力最高。
- `risk_rank_v08_conditioned` 用作保守工程干预排序。
- `risk_rank_v08_social_conditioned` 用作公平/脆弱性敏感情景。
- `risk_rank_v08_candidate_policy` 用作政策敏感性分析，不应解释为健康风险概率。

## 核心默认权重

Conservative:

```text
risk = 0.75h + 0.15hv + 0.10he
```

Social-sensitive:

```text
risk = 0.55h + 0.30hv + 0.15he
```

Candidate-policy:

```text
within high-hazard candidates:
priority = 0.50 hazard_within_candidate + 0.35 vulnerability + 0.15 exposure
```

低于 p75 hazard 的 cell 默认使用 `0.50 × hazard_score` 惩罚项，避免低热但社会 proxy 高的 cell 冲到热风险优先级前列。
