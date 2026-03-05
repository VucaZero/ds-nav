# ds-nav 项目结构说明（静态结构唯一说明）

最后更新：2026-03-05

## 1. 范围说明
本文件统一替代原有：
- `PROJECT_STRUCTURE_SPEC.md`
- `EXPERIMENT_FILE_LAYOUT.md`

用于说明 `ds-nav` 的静态目录结构、实验输入输出布局、与上级目录的归档关系。

## 2. 顶层结构（`/home/data/czh/ds-nav`）
- `AGENTS.md`：协作与执行规范。
- `EXPERIMENT_DESIGN.md`：实验设计唯一命名源。
- `METHOD_STRUCTURE.md`：方法路径文档（当前不改动）。
- `PROJECT_STRUCTURE.md`：当前文档（结构说明）。
- `EXPERIMENT_PROCESS_LOG.md`：每轮实验过程记录（证据与归因）。
- `programs/`：官方平台代码（`VLN-CE`, `habitat-lab`）。
- `vln_ce_baseline/`：方法实现代码。
- `scripts/`：实验入口与自动化脚本。
- `reports/`：正式实验报告与原始结果。
- `eval_results_official/`：官方基线结果（B0）。
- `experiment_workspace/`：实验工作区（环境、工具、临时脚本）。

## 3. 关键子目录规范

### 3.1 代码
- `scripts/run_official_vlnce_inference.py`：统一 CLI 入口。
- `scripts/run_official_vlnce.py`：官方推理循环集成。
- `vln_ce_baseline/vlnce_integration/inference_hook.py`：每步门控注入。
- `vln_ce_baseline/disambig_controller.py`：门控决策规则/网络。
- `vln_ce_baseline/ds_belief_filter.py`：DS 不确定性。
- `vln_ce_baseline/vlnce_integration/action_primitives.py`：动作原语与日志。

### 3.2 数据与模型
- `programs/VLN-CE/data/scene_datasets/mp3d`：场景数据。
- `programs/VLN-CE/data/datasets/R2R_VLNCE_v1-3_preprocessed`：R2R 预处理。
- `programs/VLN-CE/data/checkpoints/CMA_PM_DA_Aug.pth`：CMA 权重。
- `programs/VLN-CE/data/ddppo-models/gibson-2plus-resnet50.pth`：DDPPO 权重。

### 3.3 报告
- `reports/round_xxx/01_design_report.md`
- `reports/round_xxx/02_file_structure_report.md`
- `reports/round_xxx/03_experiment_result_report.md`
- `reports/round_xxx/logs/`：stdout/stderr 日志
- `reports/round_xxx/raw/`：每组实验原始输出
- `reports/round_xxx/summary/`：结构化汇总与分析

## 4. 运行期目录命名规范

### 4.1 raw 目录命名
`e<stage>_<method_or_fix>_<key_params>`，示例：
- `e2_ours_r`
- `e2_fix_u068_c030_one_step`
- `e2_probe_u110_c030`

### 4.2 日志命名
`<序号>_<实验名>.log`，示例：
- `13_e2_fix_u068_c030_one_step.log`

## 5. 上级目录归档关系（`/home/data/czh`）
为减少 `ds-nav` 干扰内容，目录归档状态如下：
- `/home/data/czh/history`
- `/home/data/czh/LTE_Nav`

`ds-nav` 内仅保留当前实验主线所需内容。

## 6. 文档最小集合（执行时优先）
后续实验以以下四份为主：
1. `EXPERIMENT_DESIGN.md`
2. `PROJECT_STRUCTURE.md`
3. `METHOD_STRUCTURE.md`
4. `EXPERIMENT_PROCESS_LOG.md`
