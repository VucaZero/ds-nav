# v2.2 分支研究索引

版本：`v2.2`
更新时间：2026-03-10
适用范围：`/home/data/czh/ds-nav`
定位：基于当前主线激活文档与 Round008-010 证据，对主线方法和实验做一版可直接用于沟通/写作的研究总结。

## 文件清单
- `01_mainline_paper_brief.md`
  - 论文形式的简报版本
  - 聚焦当前主线方法、实验设置、核心结果、局限与下一步
- `02_senior_reviewer_critique.md`
  - 以资深审稿人视角对当前工作做强批判性评估
  - 聚焦与 `ICLR`、`ICRA`、`RAL` 水准相比的主要差距
- `03_top_tier_reinforcement_plan.md`
  - 基于审稿人锐评反推的补强计划
  - 按实验、方法、写作三条 TODO 组织，并补充 `TEN -> 证据时序网络` 与 `DUET/HAMT` 路线判断
- `04_backtrack_target_selector_design.md`
  - `backtrack_target_node` 第一版规则选择器设计
  - 定义输入输出、评分项、升级路线与主线接入位点
- `05_backtrack_selector_code_integration_map.md`
  - 将 selector 拆到未来主线文件级的接线图
  - 明确 `inference_hook`、`topo`、`action_primitives` 的后续改造边界
- `code/backtrack_target_selector_v1.py`
  - 独立运行的规则选择器原型
  - 输出 `selected_node_id`、分项打分和候选排序
- `code/demo_backtrack_target_selector_v1.py`
  - 原型演示脚本
  - 用手写样例验证 selector 输出不是常量

## 证据来源
- 激活文档：
  - `EXPERIMENT_DESIGN.md`
  - `METHOD_STRUCTURE.md`
  - `PROJECT_STRUCTURE.md`
  - `EXPERIMENT_PROCESS_LOG.md`
- 分支研究历史：
  - `docs/branch/v2.1/01_method_diagnosis_and_optimization_report.md`
  - `docs/branch/v2.1/02_ten_v2.1_paper_blueprint.md`
- 关键实验摘要：
  - `reports/round_008/summary/ROUND_008_SUMMARY.md`
  - `reports/round_009/summary/ROUND_009_SUMMARY.md`
  - `reports/round_010/summary/ROUND_010_SUMMARY.md`
  - `reports/round_009/summary/e3_full_metrics.json`
  - `reports/round_010/summary/task_metrics_round010.json`

## 使用说明
- 本目录是 `docs/branch/` 下的研究沉淀，不直接作为实验执行口径。
- 若后续要把其中稳定结论提升为主线，请先同步到 `EXPERIMENT_DESIGN.md` 和 `METHOD_STRUCTURE.md`。
