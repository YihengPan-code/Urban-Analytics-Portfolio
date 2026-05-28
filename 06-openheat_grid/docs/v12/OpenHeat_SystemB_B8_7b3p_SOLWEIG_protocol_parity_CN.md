# OpenHeat System B B8.7b.3p SOLWEIG 协议一致性审计

状态：`B87B3P_PASS_WITH_NONFINAL_SMOKE_DIFFERENCES`

本审计在 N300 SOLWEIG 执行之前检查标签来源和协议是否一致，避免早期 8 个单元、N24、N150 和后续 N300 使用不同 DSM、CDSM、SVF、DEM、landcover、forcing 或 SOLWEIG 参数后仍被混入同一个 ML 标签家族。

## 主要结论

- 当前 ML 标签来源：`b85_f5_n150_multiforcing`。
- N150 protocol_id：`F5_N150_QA_DSM_V08_CDSM_PER_TILE_SCENARIO_SVF_FLATDEM_NOLC_FD01_FD02_H10_12_13_15_16`。
- 计划 N300 protocol_id：`B87C_PLANNED_QA_DSM_V08_CDSM_V07_GRID_SCENARIO_SVF_FLATDEM_NOLC_FD01_FD02_H10_12_13_15_16`。
- DSM：DSM PASS: final F5 and planned B87C use reviewed_heightqa / qa_corrected_final lineage.
- CDSM：CDSM PASS: final F5 and planned B87C use v08 dsm_vegetation_2m_toapayoh lineage.
- SVF：SVF PASS_WITH_ASSERTION: final F5 uses separate base/overhead per-tile SVF; planned B87C must materialize scenario-specific overhead SVF and not reuse base SVF.
- DEM / landcover：DEM/landcover PASS: flat DEM convention and INPUT_LC=None / USE_LC_BUILD=false are consistent.
- forcing、tile、SOLWEIG 参数：Forcing/tile/SOLWEIG PASS: FD01+FD02, hours 10/12/13/15/16, base+overhead_as_canopy, 100m+100m buffer at 2m, and SOLWEIG core parameters are compatible.
- 非最终 smoke 差异：5 nonfinal smoke/deprecated caveat rows; treated as WARN_NONFINAL_PROTOCOL_DIFFERENCE, not final ML mixing.
- blockers：`none`。

## 对 B8.7b.4 的要求

B8.7b.4 若继续，只能在显式授权后进行，并且必须写入 protocol_id 与一致性断言：建筑 DSM、植被 CDSM、grid 几何来源、flat DEM、禁用 landcover、base/overhead SVF 分离、overhead CDSM 的 max 规则、forcing day、小时、情景和 delta 方向都必须被检查。

## 边界

本 lane 没有运行 QGIS 或 SOLWEIG；没有复制、移动、写入 raster；没有读取 raster 像元；没有打开 `svfs.zip`；没有创建 run-ready manifest 或 runner；没有创建 AOI、B9、WBGT、risk、hazard、exposure、vulnerability 或 System A/B coupling 输出。
