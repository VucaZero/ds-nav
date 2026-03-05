# ds-nav 项目结构说明（v2 主线）

最后更新：2026-03-05  
版本：`v2.0-active`

## 1. 范围说明
本文件定义 `ds-nav` 的静态目录结构、文档版本布局、实验输入输出布局。

## 2. 顶层结构（`/home/data/czh/ds-nav`）
- `AGENTS.md`：协作与执行规范。
- `EXPERIMENT_DESIGN.md`：实验设计唯一命名源（激活版）。
- `PROJECT_STRUCTURE.md`：当前结构说明（激活版）。
- `METHOD_STRUCTURE.md`：方法结构说明（激活版）。
- `EXPERIMENT_PROCESS_LOG.md`：轮次证据与归因记录（激活版）。
- `docs/`：文档治理目录（草案与归档）。
- `programs/`：官方平台代码（`VLN-CE`、`habitat-lab`）。
- `vln_ce_baseline/`：方法实现代码。
- `scripts/`：实验入口与自动化脚本。
- `reports/`：正式实验报告与原始结果。
- `eval_results_official/`：官方基线结果（B0）。
- `experiment_workspace/`：环境与辅助工具区。

## 3. 文档版本目录（新增）
- `docs/DOC_VERSIONING.md`：版本治理总规范。
- `docs/proposals/<version>/`：草案文档。
- `docs/archive/<date>_<version>/`：冻结文档。

当前状态：
- v1 归档：`docs/archive/2026-03-05_v1/`
- v2 草案快照：`docs/proposals/v2_draft/`

## 4. 关键代码与插入点

### 4.1 入口与主循环
- `scripts/run_official_vlnce_inference.py`：统一 CLI 入口。
- `scripts/run_official_vlnce.py`：官方推理循环。

### 4.2 v1/v2 共享插入点（必须保持）
- `vln_ce_baseline/vlnce_integration/inference_hook.py`
- `vln_ce_baseline/disambig_controller.py`
- `vln_ce_baseline/vlnce_integration/action_primitives.py`

### 4.3 v2 新增模块目录（TEN）
- `vln_ce_baseline/evidence_graph/`
- `vln_ce_baseline/temporal_fusion/`
- `vln_ce_baseline/gating/`
- `vln_ce_baseline/topo/`

## 5. 报告结构（强制）
`reports/round_xxx/` 下必须包含：
- `01_design_report.md`
- `02_file_structure_report.md`
- `03_experiment_result_report.md`
- `logs/`
- `raw/`
- `summary/`（json + md，且 md 必含 `Analysis`）

## 6. 命名规范

### 6.1 raw 命名
规则：`e<stage>_<method>_<key_params>`  
示例：
- `e3_ten_r_w20_budget045_cd10`
- `e3_ten_l_head_w20_budget045_cd10`
- `e4_noise_shuffle_p30_ten_r_rules`

### 6.2 日志命名
规则：`<序号>_<实验名>.log`  
示例：
- `05_e3_ten_r_w20_budget045_cd10.log`

## 7. 上级目录归档关系（`/home/data/czh`）
- `ds-nav` 仅保留当前主线实验内容。
- 历史或无关目录迁移到上级管理（如 `history`、`LTE_Nav`）。
