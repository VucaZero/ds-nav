# backtrack_target_node 原型接线图（v2.2）

版本：`v2.2`
更新时间：2026-03-10
文档定位：把 `backtrack_target_node` 第一版规则选择器拆到具体代码文件级，明确以后正式接入主线时每个文件该做什么。

## 1. 当前事实
当前主线里 `BACKTRACK` 的触发逻辑已经在：
- `vln_ce_baseline/vlnce_integration/inference_hook.py`

但目标节点没有真正选择，触发后直接写：
- `backtrack_target_node = 0`

因此当前问题不是“有没有 BACKTRACK”，而是“BACKTRACK 没有 target selection”。

## 2. v2.2 原型文件
本次仅在 `docs/branch/v2.2` 下新增原型，不改主线：
- `docs/branch/v2.2/code/backtrack_target_selector_v1.py`
- `docs/branch/v2.2/code/demo_backtrack_target_selector_v1.py`
- `docs/branch/v2.2/04_backtrack_target_selector_design.md`

## 3. 未来正式接入主线的文件级改造点

### 3.1 `vln_ce_baseline/vlnce_integration/inference_hook.py`
职责：主接线文件。

需要新增的逻辑：
- 在判定 `action_type == BACKTRACK` 后，不再直接把 `backtrack_target_node` 写成常量；
- 从运行态构造 `SelectionContext`；
- 从 topo/visited/frontier 状态构造 `BacktrackCandidate` 列表；
- 调用 selector 得到 `selected_node_id`、`selected_score`、`reason`；
- 若 `should_backtrack=False`，允许降级为 `LOOK_AROUND` 或 `FOLLOW`；
- 把排序前几名和分项打分写进 step log。

建议新增内部函数：
- `_build_backtrack_selection_context(...)`
- `_build_backtrack_candidates(...)`
- `_resolve_backtrack_action(...)`

### 3.2 `vln_ce_baseline/topo/backtrack_target_selector.py`
职责：正式版 selector 模块。

建议内容：
- 从原型迁移 `SelectionContext`、`BacktrackCandidate`、`SelectionResult`；
- 增加和主线 topo state 的类型适配层；
- 保留 `ranked_candidates` 输出，方便调试和日志落盘。

### 3.3 `vln_ce_baseline/topo/topo_state.py`
职责：拓扑状态与候选节点提供者。

建议内容：
- 维护 `node_id -> metadata`；
- 为 selector 提供：
  - `topo_distance`
  - `visit_count`
  - `last_seen_step_gap`
  - `is_frontier_parent`
  - `reachable`
- 这个文件未来应成为 `rewind target` 的主要数据源。

### 3.4 `vln_ce_baseline/topo/node_memory.py`
职责：节点级证据状态。

建议内容：
- 后续存储 `m(H)`、`m(not H)`、`m(Theta)`、`K`；
- 为 `expected_info_gain`、`conflict_support`、`historical_recovery_rate` 提供更可靠估计。

### 3.5 `vln_ce_baseline/vlnce_integration/action_primitives.py`
职责：动作原语执行与日志。

需要扩展的字段：
- `backtrack_target_score`
- `backtrack_target_reason`
- `backtrack_ranked_candidates`
- `backtrack_distance`

第一阶段不一定改动作轨迹本身，但日志必须先接上。

### 3.6 `vln_ce_baseline/disambig_controller.py`
职责：是否触发，而不是选哪个 target。

建议：
- 保持 `BACKTRACK` 与否的职责；
- 不把 target selection 混入 controller，避免 controller 过重；
- 最多只回传一个 `need_target_selection=True` 的信号。

## 4. 正式接入时的最小 patch 顺序
1. 新增 `topo/backtrack_target_selector.py`
2. 在 `inference_hook.py` 构造 context/candidates 并调用 selector
3. 在 `action_primitives.py` 增加 selector 结果日志字段
4. 先做离线日志验证，再决定是否把 target node 接入更真实的 motion planner

## 5. 当前最小可验证目标
正式接入前的最低目标不是“回退真的到那个节点”，而是：
- `backtrack_target_node` 不再是常量；
- 候选节点排序稳定；
- 每次回退都能解释“为什么选这个点”；
- bad case 中能分析出“选错节点”还是“该点本就不该回退”。
