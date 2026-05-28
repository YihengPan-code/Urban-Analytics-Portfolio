"""Write B8.6g3 decisions, reports, prompts, status, and CN documentation.

Inputs:
    B8.6g3 input/source inventories, source-review closeout, v4 design,
    true-vector readiness/gap register, execution-precheck matrix, and AOI/B9
    blocker matrix.
Outputs:
    b86g3_next_lane_decision_matrix.csv, future Codex prompts, b86g3_report.md,
    B8_6G3_STATUS.md, and
    docs/v12/OpenHeat_SystemB_B8_6g3_true_vector_source_review_CN.md.
Saved metrics:
    Source-review pass/readiness statuses, closed source-review cells, N300 v4
    row count, N150 overlap, duplicate count, connected shade corridor verdict,
    pedestrian network verdict, building/canyon verdict, B8.7b readiness,
    AOI/B9 blocker headline, and recommended next lanes. This script creates no
    raster, QGIS/SOLWEIG, N300 manifest, AOI-wide prediction, B9, WBGT,
    hazard/risk, observed-truth, causal feature-importance, Tmrt-to-WBGT, or
    System A/B coupling output.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from v12_b86g3_input_inventory import (
    CLAIM_BOUNDARY,
    DEFAULT_CONFIG,
    config_list,
    current_n150_cells,
    load_config,
    md_table,
    output_path,
    read_csv,
    write_csv,
    write_text,
)


@dataclass(frozen=True)
class WorkflowDecisionResult:
    """B8.6g3 workflow decision result."""

    status: str
    ready_for_b87b: bool
    needs_external_vector_source: bool
    recommended_next_lane: str


CREATED_FILES = [
    "configs/v12/systemb_b86g3_true_vector_source_review.yaml",
    "scripts/v12_b86g3_input_inventory.py",
    "scripts/v12_b86g3_source_inventory.py",
    "scripts/v12_b86g3_cell_source_closeout.py",
    "scripts/v12_b86g3_vector_source_review.py",
    "scripts/v12_b86g3_execution_gate.py",
    "scripts/v12_b86g3_workflow_decision.py",
    "scripts/v12_b86g3_run_true_vector_source_review.py",
    "docs/v12/OpenHeat_SystemB_B8_6g3_true_vector_source_review_CN.md",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_input_inventory.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_source_inventory.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_true_vector_source_readiness.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_connected_shade_corridor_review.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_pedestrian_network_review.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_covered_walkway_review.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_building_canyon_review.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_tree_building_interaction_review.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_overhead_geometry_review.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_water_park_edge_review.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_manual_source_review_closeout.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_n300_design_v4_source_reviewed.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_n300_v4_diff_vs_b87a.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_execution_precheck_readiness_matrix.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_aoi_b9_blocker_matrix.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_source_gap_register.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_next_lane_decision_matrix.csv",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_codex_prompt_B87B_N300_execution_precheck.md",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_codex_prompt_B86G4_external_vector_acquisition.md",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_codex_prompt_B87C_N300_QGIS_execution_package.md",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_report.md",
    "outputs/v12_surrogate/b8_6g3_true_vector_source_review/B8_6G3_STATUS.md",
]


def lookup(frame: pd.DataFrame, key_col: str, key: str, value_col: str, default: str = "") -> str:
    """Look up one string value in a compact matrix."""
    row = frame.loc[frame[key_col].astype(str).eq(key)] if key_col in frame.columns else pd.DataFrame()
    return str(row[value_col].iloc[0]) if not row.empty and value_col in row.columns else default


def count_closed_source_review(closeout: pd.DataFrame, cells: list[str]) -> int:
    """Count source-review cells closed as keep-with-caveat."""
    return int(
        closeout.loc[closeout["source_review_cell"].astype(str).isin(cells), "recommended_closeout"]
        .astype(str)
        .eq("KEEP_WITH_CAVEAT")
        .sum()
    )


def execution_headline(exec_matrix: pd.DataFrame) -> str:
    """Return execution-precheck readiness headline."""
    blockers = exec_matrix.loc[
        exec_matrix["blocker_type"].astype(str).eq("execution_precheck_blocker")
        & exec_matrix["status"].astype(str).isin(["FAIL", "BLOCKED"])
    ]
    return "B8.7b N300 execution precheck may proceed as a precheck-only lane; B8.6g3 creates no execution artifact." if blockers.empty else "B8.7b precheck is blocked by candidate-design/source-review failures."


def aoi_b9_headline(aoi_matrix: pd.DataFrame) -> str:
    """Return AOI/B9 blocker headline."""
    return "AOI_PREFLIGHT_BLOCKED and B9_BLOCKED because connected shade corridor and tree/building true-vector gaps remain."


def decision_status(config: dict[str, Any]) -> tuple[str, bool, bool, dict[str, Any]]:
    """Compute primary B8.6g3 statuses and summary metrics."""
    closeout = read_csv(output_path(config, "manual_source_review_closeout_path"))
    v4 = read_csv(output_path(config, "n300_design_v4_source_reviewed_path"))
    readiness = read_csv(output_path(config, "true_vector_source_readiness_path"))
    gaps = read_csv(output_path(config, "source_gap_register_path"))
    exec_matrix = read_csv(output_path(config, "execution_precheck_readiness_matrix_path"))
    aoi_matrix = read_csv(output_path(config, "aoi_b9_blocker_matrix_path"))
    source_cells = config_list(config, "source_review_cells")
    closed = count_closed_source_review(closeout, source_cells)
    overlap = len(set(v4["cell_id"].astype(str)).intersection(current_n150_cells(config)))
    duplicates = int(v4["cell_id"].astype(str).duplicated().sum())
    expected = int(config.get("expected_n300_count", 150))
    input_ok = len(v4) == expected and overlap == 0 and duplicates == 0
    source_ok = closed == len(source_cells)
    exec_blockers = exec_matrix.loc[
        exec_matrix["blocker_type"].astype(str).eq("execution_precheck_blocker")
        & exec_matrix["status"].astype(str).isin(["FAIL", "BLOCKED"])
    ]
    ready_for_b87b = bool(input_ok and source_ok and exec_blockers.empty)
    needs_external = bool(gaps["blocking_for_aoi_b9"].astype(str).isin(["yes", "partial"]).any())
    if not input_ok:
        status = "B86G3_BLOCKED_INPUT"
    elif not source_ok:
        status = "B86G3_BLOCKED_SOURCE_REVIEW"
    else:
        status = "B86G3_SOURCE_REVIEW_PASS"
    metrics: dict[str, Any] = {
        "source_review_cells_closed": closed,
        "v4_rows": len(v4),
        "n150_overlap": overlap,
        "duplicate_count": duplicates,
        "connected_verdict": lookup(readiness, "source_category", "connected_shade_corridor", "validity_verdict"),
        "pedestrian_verdict": lookup(readiness, "source_category", "pedestrian_network", "validity_verdict"),
        "building_verdict": lookup(readiness, "source_category", "building_canyon", "validity_verdict"),
        "tree_verdict": lookup(readiness, "source_category", "tree_building_interaction", "validity_verdict"),
        "execution_headline": execution_headline(exec_matrix),
        "aoi_b9_headline": aoi_b9_headline(aoi_matrix),
    }
    return status, ready_for_b87b, needs_external, metrics


def next_lane_decision_matrix(status: str, ready_for_b87b: bool, needs_external: bool) -> pd.DataFrame:
    """Create B8.6g3 next-lane decision matrix."""
    rows = [
        {
            "future_lane": "B8.7b_N300_execution_precheck",
            "decision_status": "B86G3_READY_FOR_B87B_PRECHECK" if ready_for_b87b else "WAIT",
            "priority": "high",
            "allowed_scope": "precheck-only inspection of sample design and SOLWEIG asset/readiness requirements; no actual QGIS/SOLWEIG run",
            "forbidden_actions": "no raster read/write/copy, no N300 execution manifest in B8.6g3, no runner, no AOI/B9, no WBGT/hazard/risk",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "future_lane": "B8.6g4_external_vector_acquisition",
            "decision_status": "B86G3_NEEDS_EXTERNAL_VECTOR_SOURCE" if needs_external else "OPTIONAL_QA",
            "priority": "high",
            "allowed_scope": "acquire/QA connected shade corridor, pedestrian network, covered walkway, tree canopy, building/canyon vector sources",
            "forbidden_actions": "no raster, no QGIS/SOLWEIG, no AOI-wide prediction, no B9, no local WBGT, no risk/hazard scoring",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "future_lane": "B8.7c_N300_QGIS_execution_package",
            "decision_status": "NOT_NOW_PLACEHOLDER",
            "priority": "later_only",
            "allowed_scope": "placeholder only after B8.7b precheck and explicit reviewer authorization",
            "forbidden_actions": "do not create this package in B8.6g3",
            "claim_boundary": CLAIM_BOUNDARY,
        },
        {
            "future_lane": "AOI_B9",
            "decision_status": "BLOCKED",
            "priority": "none",
            "allowed_scope": "none in this lane",
            "forbidden_actions": "keep AOI_PREFLIGHT_BLOCKED and B9_BLOCKED",
            "claim_boundary": CLAIM_BOUNDARY,
        },
    ]
    out = pd.DataFrame(rows)
    out["b86g3_primary_status"] = status
    return out


def prompt_b87b() -> str:
    """Return future B8.7b precheck prompt."""
    return """# Future Codex Prompt: B8.7b N300 Execution Precheck

Work inside the OpenHeat-ToaPayoh project subdirectory.

Lane: B8.7b N300 execution precheck.

Use B8.6g3 outputs as design/source-review inputs. This future lane may inspect
sample design validity, required SOLWEIG asset readiness, local-only execution
boundaries, and manifest requirements. It must still be a precheck: do not run
QGIS or SOLWEIG, and do not create raster outputs, AOI-wide predictions, B9
outputs, local WBGT, hazard_score, risk_score, exposure/vulnerability scores,
observed-truth claims, causal feature-importance claims, Tmrt-to-WBGT
conversion, or System A/B coupling.

Required starting inputs:
- outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_n300_design_v4_source_reviewed.csv
- outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_execution_precheck_readiness_matrix.csv
- outputs/v12_surrogate/b8_6g3_true_vector_source_review/b86g3_manual_source_review_closeout.csv

Keep no-raster commit hygiene. Any actual SOLWEIG/QGIS execution package belongs
to a later explicitly authorized lane, not B8.7b precheck.
"""


def prompt_b86g4() -> str:
    """Return future B8.6g4 external/vector acquisition prompt."""
    return """# Future Codex Prompt: B8.6g4 External/Vector Acquisition

Work inside the OpenHeat-ToaPayoh project subdirectory.

Lane: B8.6g4 external/vector acquisition.

Acquire or integrate source-backed vector data for connected shade corridor,
pedestrian footpath/walkway network, covered walkway/sheltered path geometry,
building footprint/height/canyon geometry, tree canopy, tree/building
interaction, and water/park/road/hardscape edge context.

Validity requirements:
- Connected shade corridor requires line/polygon network geometry or an
  explicit vector-derived connectivity table.
- Do not infer corridor continuity from centroid distance, generic shade
  fraction, or compact cell fractions.
- Covered walkway must use covered/sheltered tags or equivalent source.
- Tree/building interaction needs both tree canopy and building geometry, or a
  trusted vector-derived interaction table.

Forbidden:
No raster reads/writes/copies, no QGIS/SOLWEIG, no AOI-wide prediction, no B9,
no local WBGT, no hazard_score, no risk_score, no exposure/vulnerability score,
no observed-truth or causal claims, no Tmrt-to-WBGT conversion, and no System
A/B coupling.
"""


def prompt_b87c() -> str:
    """Return NOT_NOW placeholder prompt for a future execution package lane."""
    return """# Future Placeholder: B8.7c N300 QGIS Execution Package

Status: NOT_NOW.

Do not use this in B8.6g3. This placeholder only records that any actual N300
QGIS/SOLWEIG execution package would require a later explicit lane after B8.7b
precheck and reviewer authorization.

Forbidden now:
No QGIS runner, no SOLWEIG run, no raster reads/writes/copies, no N300 execution
manifest, no AOI-wide prediction, no B9, no WBGT/hazard/risk outputs, and no
System A/B coupling.
"""


def report_text(config: dict[str, Any], status: str, ready: bool, needs_external: bool, metrics: dict[str, Any]) -> str:
    """Create English B8.6g3 report."""
    closeout = read_csv(output_path(config, "manual_source_review_closeout_path"))
    readiness = read_csv(output_path(config, "true_vector_source_readiness_path"))
    exec_matrix = read_csv(output_path(config, "execution_precheck_readiness_matrix_path"))
    aoi = read_csv(output_path(config, "aoi_b9_blocker_matrix_path"))
    return f"""# B8.6g3 True-Vector Source Review And Source-Review Closeout

Status: `{status}`

Companion statuses: `{'B86G3_READY_FOR_B87B_PRECHECK' if ready else 'B86G3_NOT_READY_FOR_B87B_PRECHECK'}`; `{'B86G3_NEEDS_EXTERNAL_VECTOR_SOURCE' if needs_external else 'B86G3_EXTERNAL_VECTOR_OPTIONAL'}`.

## 1. Why B8.6g3 follows B8.7a

B8.7a produced a patched N300 v3 design with 150 rows, zero N150 overlap, zero
duplicates, three replaced pure-water cells, and three retained source-review
cells. B8.6g3 closes those source-review caveats and separates N300 execution
precheck blockers from surrogate/AOI/B9 feature blockers.

## 2. B8.7a Patched Design Summary

- N300 v4 rows: {metrics['v4_rows']}
- N150 overlap: {metrics['n150_overlap']}
- Duplicate cell IDs: {metrics['duplicate_count']}
- Source-review cells closed: {metrics['source_review_cells_closed']}/3
- Diff versus B8.7a: metadata-only source-review closeout.

## 3. Manual Source-Review Facts

{md_table(closeout, ['source_review_cell', 'recommended_closeout', 'source_closeout_status', 'execution_precheck_blocker', 'surrogate_feature_blocker', 'caveat_text'], 12)}

## 4. TP_0103 / TP_0104 / TP_0464 Closeout

TP_0103 and TP_0104 are kept with river-edge mixed-bank caveats. TP_0464 is
kept with utility-site / woodland / pedestrian-relevance caveat. None of the
three is an execution-precheck blocker after B8.6g3 closeout.

## 5. True-Vector Source Inventory

{md_table(readiness, ['source_category', 'status', 'validity_verdict', 'blocker_type', 'recommended_next_action'], 12)}

## 6. Connected Shade Corridor Verdict

`{metrics['connected_verdict']}`. Covered walkway and overhead geometry are
useful sources, but they are not an explicit connected pedestrian shade-network
or connectivity table. This blocks AOI/B9 surrogate promotion, not B8.7b
precheck start.

## 7. Blocker Separation

{md_table(exec_matrix, ['readiness_item', 'status', 'blocker_type', 'next_action'], 20)}

## 8. N300 v4 Design Status

The v4 design keeps the B8.7a 150 rows and only adds source-review metadata.
No SOLWEIG manifest, QGIS runner, local runner, raster, AOI prediction, B9,
WBGT, hazard, risk, or System A/B coupling output was created.

## 9. B8.7b Readiness

{metrics['execution_headline']}

## 10. B8.6g4 Recommendation

B8.6g4 external/vector acquisition remains recommended because connected shade
corridor, full pedestrian network, and tree/building true-vector interaction
gaps remain open for AOI/B9.

## 11. AOI/B9 Boundary

{md_table(aoi, ['blocker_item', 'status', 'evidence', 'next_action'], 12)}

## 12. Claim Boundaries

- Not B9.
- Not AOI-wide prediction.
- Not local WBGT.
- Not risk / hazard score.
- Not exposure/vulnerability score.
- Not observed truth.
- Not causal feature importance.
- No raster.
- No QGIS / SOLWEIG.
- No N300 execution manifest.
- No Tmrt-to-WBGT conversion.
- No System A/B coupling.
"""


def cn_doc_text(config: dict[str, Any], status: str, ready: bool, needs_external: bool, metrics: dict[str, Any]) -> str:
    """Create valid UTF-8 Chinese documentation."""
    return f"""# OpenHeat System B B8.6g3 真矢量来源审查与来源复核收口说明

## 结论

- B8.6g3 状态：`{status}`
- B8.7b execution precheck：`{'B86G3_READY_FOR_B87B_PRECHECK' if ready else 'B86G3_NOT_READY_FOR_B87B_PRECHECK'}`
- 外部 / 真矢量来源：`{'B86G3_NEEDS_EXTERNAL_VECTOR_SOURCE' if needs_external else 'B86G3_EXTERNAL_VECTOR_OPTIONAL'}`
- N300 v4 行数：`{metrics['v4_rows']}`
- N150 重叠：`{metrics['n150_overlap']}`
- duplicate cell_id：`{metrics['duplicate_count']}`
- AOI / B9：继续阻断

## 为什么 B8.6g3 接在 B8.7a 后面

B8.7a 已经把 N300 v3 候选设计修补为 150 行，且无 N150 重叠、无重复，并替换了 TP_0830、TP_0858、TP_0943 三个基本水面单元。但 TP_0103、TP_0104、TP_0464 仍是 source_review，connected shade corridor 也仍然缺少真矢量连通性来源。因此 B8.6g3 只做来源审查、来源复核收口、设计闸门判断和未来提示词，不创建任何执行包。

## B8.7a patched design 摘要

本轮从 B8.7a v3 patched design 出发。B8.6g3 v4 仍保持 150 行、0 个 N150 重叠、0 个 duplicate cell_id。如果没有必须替换的 source_review 单元，v4 与 B8.7a 的差异只是来源复核元数据。

## 人工来源复核事实

- TP_0103：混合河道与两岸，河面约四分之一，不是纯水面；保留，但记录 river-edge caveat。
- TP_0104：同 TP_0103；保留，但记录 river-edge caveat。
- TP_0464：约 37% waterworks、63% woodland，不是纯水面；保留，但记录 utility-site / pedestrian-relevance caveat。
- TP_0159：2022 年为施工场地，但 2026 年为 Toa Payoh Sport Hall；保留，并记录时间性土地利用错配。
- TP_0519：woodland；保留为 vegetation/canopy/green-control candidate。
- TP_0830、TP_0858、TP_0943：基本水面，已在 B8.7a 排除并替换。

## TP_0103 / TP_0104 / TP_0464 收口

三个 source_review 单元均收口为 keep-with-caveat，不再阻断 B8.7b execution precheck。它们的 caveat 是文档和后续 QA 约束，不是 AOI/B9 特征闭合证据。

## 真矢量来源审查

- connected shade corridor：`{metrics['connected_verdict']}`。缺少显式行人遮阴网络或连通性表，不能从质心距离、普通 shade fraction 或紧凑单元比例推断。
- pedestrian network：`{metrics['pedestrian_verdict']}`。covered walkway / pedestrian bridge 来源有帮助，但还不是完整 footpath / walkway 网络。
- building / canyon：`{metrics['building_verdict']}`。建筑 footprint / height 来源可用于未来 canyon derivation，但不能升级为 observed local WBGT 证据。
- tree / building interaction：`{metrics['tree_verdict']}`。建筑来源存在，但仍需要 tree-canopy vector 或可信的 vector-derived interaction table。

## 三类 blocker 的区分

1. execution-precheck blocker：候选数量、N150 重叠、duplicate、source_review 单元未收口等会阻断 B8.7b precheck。B8.6g3 当前未发现这些阻断。
2. surrogate / AOI / B9 feature blocker：connected shade corridor、tree/building interaction 和完整 pedestrian network 等真矢量缺口仍阻断 AOI/B9。
3. documentation caveat only：TP_0103、TP_0104、TP_0464 的混合水边 / utility woodland caveat 属于文档 caveat，不自动阻断 B8.7b precheck。

## N300 v4 设计状态

v4 是 source-reviewed design，不是 run-ready manifest。它没有创建 SOLWEIG manifest、QGIS runner、本地执行说明、raster、AOI-wide prediction、B9、local WBGT、hazard_score、risk_score 或 System A/B coupling。

## B8.7b readiness

{metrics['execution_headline']}

## B8.6g4 建议

建议后续开启 B8.6g4 external/vector acquisition，专门获取或整合 connected shade corridor、pedestrian footpath / walkway、covered walkway、tree canopy、building/canyon 和 water/park/road edge 的真矢量来源。AOI/B9 在这些缺口关闭前继续阻断。

## 声明边界

- 不是 B9。
- 不是 AOI-wide prediction。
- 不是 local WBGT。
- 不是 risk / hazard score。
- 不是 exposure / vulnerability score。
- 不是 observed truth。
- 不是 causal feature importance。
- 没有读取、打开、复制、创建或写入 raster。
- 没有运行 QGIS 或 SOLWEIG。
- 没有创建 N300 execution manifest。
- 没有 Tmrt-to-WBGT conversion。
- 没有 System A/B coupling。
"""


def status_text(config: dict[str, Any], status: str, ready: bool, needs_external: bool, metrics: dict[str, Any]) -> str:
    """Create B8.6g3 lane status Markdown."""
    files = "\n".join(f"- `{path}`" for path in CREATED_FILES)
    return f"""# B8.6g3 Status

Status: {status}
Companion Statuses: {'B86G3_READY_FOR_B87B_PRECHECK' if ready else 'B86G3_NOT_READY_FOR_B87B_PRECHECK'} / {'B86G3_NEEDS_EXTERNAL_VECTOR_SOURCE' if needs_external else 'B86G3_EXTERNAL_VECTOR_OPTIONAL'}
Branch: codex/b86g3-true-vector-source-review
Scope: true-vector source review and B8.7a source-review closeout only; no execution artifacts.

## Commands Run By Suite

- `python scripts/v12_b86g3_run_true_vector_source_review.py --config configs/v12/systemb_b86g3_true_vector_source_review.yaml`

## Key Results

- Source-review cells closed: {metrics['source_review_cells_closed']}/3
- N300 v4 row count: {metrics['v4_rows']}
- N150 overlap count: {metrics['n150_overlap']}
- Duplicate cell count: {metrics['duplicate_count']}
- Connected shade corridor verdict: {metrics['connected_verdict']}
- Pedestrian network verdict: {metrics['pedestrian_verdict']}
- Building/canyon verdict: {metrics['building_verdict']}
- Execution-precheck readiness: {metrics['execution_headline']}
- AOI/B9 blocker headline: {metrics['aoi_b9_headline']}
- Recommended next lane: B8.7b N300 execution precheck plus B8.6g4 external/vector acquisition before AOI/B9.

## Files Created / Modified

{files}

## Caveats

B8.6g3 is source-review and design-gate work only. It does not create SOLWEIG
manifests, QGIS runners, local execution runners, raster outputs, AOI-wide
predictions, B9 outputs, local WBGT, hazard_score, risk_score,
exposure/vulnerability score, observed-truth claims, causal feature-importance
claims, Tmrt-to-WBGT conversion, or System A/B coupling.

## Safe To Commit After Review

Controlled B8.6g3 config, scripts, docs, compact CSV, and Markdown outputs.

## Not Safe To Commit

Rasters, `.tif`, `.tiff`, `svfs.zip`, raw SOLWEIG/archive files, patch zip
packages, AOI-wide predictions, B9 outputs, WBGT, hazard_score, risk_score,
exposure/vulnerability score, and System A/B coupling outputs.
"""


def run(config_path: Path = DEFAULT_CONFIG) -> WorkflowDecisionResult:
    """Run B8.6g3 workflow decision/reporting step."""
    config = load_config(config_path)
    status, ready, needs_external, metrics = decision_status(config)
    next_lanes = next_lane_decision_matrix(status, ready, needs_external)
    write_csv(next_lanes, output_path(config, "next_lane_decision_matrix_path"))
    write_text(prompt_b87b(), output_path(config, "codex_prompt_b87b_path"))
    write_text(prompt_b86g4(), output_path(config, "codex_prompt_b86g4_path"))
    write_text(prompt_b87c(), output_path(config, "codex_prompt_b87c_path"))
    write_text(report_text(config, status, ready, needs_external, metrics), output_path(config, "report_path"))
    write_text(status_text(config, status, ready, needs_external, metrics), output_path(config, "status_path"))
    write_text(cn_doc_text(config, status, ready, needs_external, metrics), output_path(config, "cn_doc_path"))
    recommendation = "B8.7b N300 execution precheck next; B8.6g4 external/vector acquisition remains required before AOI/B9."
    return WorkflowDecisionResult(
        status=status,
        ready_for_b87b=ready,
        needs_external_vector_source=needs_external,
        recommended_next_lane=recommendation,
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Write B8.6g3 decision matrices, future prompts, report, status, "
            "and CN doc. No raster/QGIS/SOLWEIG/manifest/AOI/B9/WBGT/hazard/"
            "risk output."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(run(args.config))


if __name__ == "__main__":
    main()
