# ds-nav 项目结构说明（TEN v2 扩展版）

最后更新：2026-03-05（v2 草案）
适用范围：`/home/data/czh/ds-nav`

## 1. 文档定位
- 本文件在不破坏 v1 工程规范的前提下，新增 TEN v2 所需模块落点。
- v1 静态结构约束仍然有效：
  - 顶层目录、reports 布局、scripts 入口、vln_ce_baseline 插入点不变

---

## 2. 顶层结构（保持不变）
- `AGENTS.md`
- `EXPERIMENT_DESIGN.md`（唯一术语源）
- `METHOD_STRUCTURE.md`（v1/v2 说明文件）
- `PROJECT_STRUCTURE.md`
- `EXPERIMENT_PROCESS_LOG.md`（每轮证据归因）
- `programs/`
- `vln_ce_baseline/`
- `scripts/`
- `reports/`
- `eval_results_official/`
- `experiment_workspace/`

---

## 3. v2 新增模块（仅新增，不改动原有文件功能）

### 3.1 新增目录：TEN 证据与图结构
放置位置：`vln_ce_baseline/`

新增：
- `vln_ce_baseline/evidence_graph/`
  - `ten_graph.py`：TEN 节点/边数据结构（landmark layer + topo layer）
  - `node_state.py`：每个 node 的 DS belief state（H/¬H/Θ/K + trend stats）
- `vln_ce_baseline/temporal_fusion/`
  - `ds_temporal_update.py`：折扣、衰减、滞回、窗口融合
  - `conflict_accumulator.py`：冲突累计与触发统计
- `vln_ce_baseline/gating/`
  - `gating_rules_v2.py`：趋势规则门控（无训练版本）
  - `gating_head.py`：可学习门控 head（可选）
  - `budget_manager.py`：预算与冷却窗口

### 3.2 新增目录：Topo 支撑（兼容 DUET/ETPNav）
- `vln_ce_baseline/topo/`
  - `topo_builder.py`：轻量在线 topo（若不直接接 DUET/ETPNav）
  - `frontier_scoring.py`：frontier/回退目标打分
  - `rewind_planner.py`：选择 backtrack_target_node

---

## 4. v2 必改动点（仅允许动 3 个插入点文件，其他不动）

> 插入点必须沿用 v1 的三处骨干文件，避免工程发散

### 4.1 `vln_ce_baseline/vlnce_integration/inference_hook.py`
新增职责：
- 初始化并持久化 TEN state（跨 step）
- 每步：
  - 收集 evidence features（来自 obs/instruction/backbone 输出）
  - 调用 `ds_temporal_update` 更新 belief state
  - 调用 gating（rules/head）输出 `p_scan/p_rewind/budget`
  - 将 gating 结果写入 step_log

### 4.2 `vln_ce_baseline/disambig_controller.py`
v1：`rule_based_decision()` 输出 FOLLOW/LOOK_AROUND/BACKTRACK
v2：保留接口，升级内部逻辑：
- 输入：TEN 输出 + policy feature + topo feature
- 输出：
  - `action_type`（FOLLOW/LOOK_AROUND/BACKTRACK）
  - `scan_steps`（由 p_scan 映射）
  - `backtrack_target_node`（参数化）

### 4.3 `vln_ce_baseline/vlnce_integration/action_primitives.py`
v1：动作原语 + 日志
v2：新增参数化动作：
- `LOOK_AROUND(steps=scan_steps)`
- `BACKTRACK(target_node_id)`（必须可执行、可记录）

---

## 5. scripts 与 reports 规范（保持 v1，不新增口径）

### 5.1 统一入口脚本（不变）
- `scripts/run_official_vlnce_inference.py`

### 5.2 reports 布局（不变）
- `reports/round_xxx/{01,02,03}_*.md`
- `reports/round_xxx/logs/`
- `reports/round_xxx/raw/`
- `reports/round_xxx/summary/`

### 5.3 raw 目录命名（新增 v2 变量，但规则不变）
延续：`e<stage>_<method>_<key_params>`
示例：
- `e3_ten_r_rules_w20_budget045_cd10`
- `e3_ten_l_head_w20_budget045_cd10`
- `e4_noise_shuffle_p30_ten_r_rules`

---

## 6. 代码风格与工程规约（Codex 强制）
1) 所有新增模块必须可通过 `vln_ce_baseline` 顶层 import
2) 日志字段只增不删，旧字段保留（保证旧分析脚本可跑）
3) 任何新增参数必须登记到 `EXPERIMENT_DESIGN.md` 的变量表与默认值
4) 任何新增实验阶段必须登记到 `EXPERIMENT_DESIGN.md` 的阶段表
