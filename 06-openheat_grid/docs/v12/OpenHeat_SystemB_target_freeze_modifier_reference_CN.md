# OpenHeat System B 目标冻结与修饰因子参考域定义（Sprint B5）

## 1. 为什么需要 B5

B5 的任务不是再跑 SOLWEIG，也不是生成地图，而是在 B3 完成 N24 执行、B4 完成目标稳健性复核之后，把 System B 的目标家族、参考域规则、修饰因子归一化方法、输出 schema 和下游声明边界固定下来。这样后续 B6/N150、代理模型和 System A/B 条件化耦合不会各自重新定义目标。

## 2. B4 已经决定了什么

B4 的结论是 PASS。`tmrt_p90_c` 被保留为 N24 支持的 primary candidate：它代表混合 100m cell 内较高尾部的辐射暴露，而不是观测真值。`tmrt_p75_c`、`tmrt_p95_c`、`tmrt_mean_c`、`tmrt_max_c` 和四个 threshold-area 指标继续保留为 companion / sensitivity。B4 中的 delta 和 `m_rad` 仍然是 N24 内部的派生/临时量，不是最终 AOI-wide `M_rad`。

## 3. 现在冻结什么

- 目标家族：主目标为 `tmrt_p90_c`，主物理 delta 为 `delta_tmrt_p90_c`，规范化候选修饰因子为 `m_rad_pct01`。
- 参考规则：同一 `reference_domain_version`、同一小时、同一 scenario 内，用 eligible cells 的 `tmrt_p90_c` 中位数作为 `tmrt_ref_p90_c`。
- 归一化方法：先计算差值，再在同小时同 scenario 参考域内做 average rank，公式为 `(rank_average - 1) / (n_reference_cells - 1)`。
- schema / contract：未来 target 表必须显式写出 target version、reference domain、source、quality flag 和 companion metrics。

## 4. 现在不冻结什么

B5 不冻结最终 AOI-wide `M_rad` map，不产生 N150 输出，不训练 surrogate，不计算 `hazard_score`，不计算 `risk_score`，不计算 local WBGT，也不做 System A/B coupling。

## 5. 为什么 p90 是主目标但不能单独使用

`tmrt_p90_c` 比 mean 更能捕捉部分遮阴 cell 内残留的高辐射口袋，又比 max 更少受单个像元和边缘异常影响。它适合作为 System B 的主物理目标候选。但 p90 仍然是 SOLWEIG 模拟派生的 cell-level 指标，不是观测真值；因此必须同时保留 p75、p95、mean、max 和 threshold-area companions，用来检查肩部、尾部、背景均值、极端像元和热面积占比。

## 6. delta 与 m_rad_pct01 的区别

`delta_tmrt_p90_c` 是物理差值：

```text
delta_tmrt_p90_c = tmrt_p90_c - tmrt_ref_p90_c
```

它仍然以摄氏度 Tmrt 差值表达。`m_rad_pct01` 是排序归一化修饰因子：

```text
m_rad_pct01 = (rank_average(delta_tmrt_p90_c) - 1) / (n_reference_cells - 1)
```

它表达的是在同小时、同 scenario、同参考域内的相对位置。禁止使用摄氏度比值，例如把 cell Tmrt 除以平均 Tmrt。

## 7. 为什么 N24 reference 只能内部使用

`n24_internal_b3` 只包含 24 个已完成 N24 cells。它足够用于 B4/B5 的方法检查和可追溯性，但不能代表完整 AOI，也不能产生最终 AOI-wide `M_rad`。最终 AOI-wide modifier 只能在 N150 标签、可接受的 surrogate 和 full-AOI prediction contract 成立后再定义。

## 8. N150 与未来 surrogate 应如何使用

B6 应先设计并冻结 N150 sample/manifest，再按 B5 target family 生成 SOLWEIG 标签。未来 surrogate 的优先 supervised label candidate 是 `delta_tmrt_p90_c`，次级候选是 `tmrt_p90_c`；`m_rad_pct01` 应在预测后按 reference domain 计算，不应默认作为唯一回归标签，除非另有明确论证。

## 9. 声明边界

这些 B5 输出不是 local WBGT，不是 risk，不是 observed truth，不是 official warning，也不是 System A/B coupling。允许的表述是：System B 现在拥有一个 N24 支持、面向下一尺度的辐射目标家族与修饰因子参考域定义。
