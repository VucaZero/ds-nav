# backtrack_target_node v1 规则选择器设计（v2.2）

版本：`v2.2`
更新时间：2026-03-10
文档定位：为 `TEN` 的 `BACKTRACK(target_node)` 设计第一版可落地的规则目标选择器，并明确未来如何接入主线代码。本文档只定义原型方案，不直接修改主线实现。

## 1. 问题定义
当前主线里的 `BACKTRACK` 已经可以触发，但 `backtrack_target_node` 仍然是常量占位。这导致系统虽然知道“该退”，却不知道“退到哪里最合理”。因此第一版选择器要解决的是：

给定当前 episode 的局部拓扑状态、历史触发日志和若干候选节点，选择一个最值得回退的目标节点 `target_node_id`，同时输出可解释的分项打分，便于后续日志、消融和校准分析。

## 2. 设计目标
第一版规则选择器不追求最优，只追求三件事：

1. 不再返回常量占位，目标节点有实际区分度；
2. 选择依据是可解释的，便于验证“为什么选它”；
3. 接口和字段设计为后续 learned selector 留出演化空间。

## 3. 输入输出

### 3.1 输入
选择器接收两类输入。

第一类是运行上下文 `SelectionContext`：
- `current_node_id`
- `theta`
- `conflict_k`
- `stagnation_steps`
- `budget_left`
- `cooldown_left`
- `steps_since_last_rewind`
- `visited_count`
- `frontier_count`

第二类是候选节点列表 `BacktrackCandidate`。每个节点至少包含：
- `node_id`
- `topo_distance`
- `graph_hops`
- `visit_count`
- `last_seen_step_gap`
- `historical_recovery_rate`
- `progress_gain`
- `expected_info_gain`
- `conflict_support`
- `uncertainty_support`
- `is_frontier_parent`
- `is_recent_anchor`
- `reachable`

### 3.2 输出
输出为 `SelectionResult`：
- `selected_node_id`
- `selected_score`
- `should_backtrack`
- `reason`
- `score_breakdown`
- `ranked_candidates`

其中 `ranked_candidates` 会保留每个候选点的总分和分项分，方便落日志和做 case study。

## 4. v1 规则

### 4.1 硬过滤
以下节点直接过滤：
- `reachable == False`
- `node_id == current_node_id`
- `topo_distance > max_backtrack_distance`
- `last_seen_step_gap < min_step_gap`

### 4.2 打分项
v1 使用线性加权打分，重点体现“信息收益、恢复经验、距离成本、循环风险”四类因素：

`score(v) = reward(v) - penalty(v)`

奖励项：
- `expected_info_gain`：回退后预期能减少多少歧义；
- `historical_recovery_rate`：该节点历史上是否经常作为有效恢复锚点；
- `conflict_support`：当前冲突是否支持回退到该节点；
- `progress_gain`：回退到该节点后是否更可能恢复任务推进；
- `anchor_bonus`：若节点是近期稳定锚点或 frontier parent，给予加分。

惩罚项：
- `distance_penalty`：图距离越远，代价越高；
- `revisit_penalty`：重复回到高频失败节点要扣分；
- `staleness_penalty`：太久没见、证据陈旧的节点扣分；
- `loop_penalty`：最近刚回退过或反复进入的节点扣分。

### 4.3 预算耦合
第一版选择器不直接决定“要不要回退”，但会结合预算对分数做抑制：
- 当 `budget_left` 很低时，提高距离惩罚；
- 当 `stagnation_steps` 很高且 `conflict_k` 很高时，提高信息收益项的权重；
- 当 `cooldown_left > 0` 时，选择器可以返回 `should_backtrack=False` 作为上层保护信号。

## 5. 为什么这一版是合理的
第一版不是终局算法，但它有三个现实优点：

1. 它和当前主线最兼容，只需要把已有 step log、visited/frontier 统计、基础 topo 状态转成候选节点即可；
2. 它的每一项分数都可解释，因此消融和错误分析能直接追到分项；
3. 它天然支持后续升级为 learned selector，因为输入输出形式已经稳定。

## 6. 未来升级方向
从 v1 到真正的证据时序网络，建议按以下顺序升级：

1. v1：规则 selector
- 基于手工构造特征和分项打分选择回退目标。

2. v2：节点级证据 selector
- 每个候选节点不再只有启发式特征，而是持有 `m(H) / m(not H) / m(Theta) / K`。
- `expected_info_gain` 不再是规则估计，而是证据熵下降的近似值。

3. v3：可学习 selector
- 用 ranking head 或分类头学习 `p(rewind_to=v)`。
- 保留规则打分作为 teacher 或 safety fallback。

## 7. 未来接入主线时的代码文件级改造点

### 7.1 新增文件
1. `vln_ce_baseline/topo/backtrack_target_selector.py`
- 放置正式版 selector。
- 对外暴露 `select_backtrack_target(context, candidates)`。

2. `vln_ce_baseline/topo/topo_state.py`
- 维护 visited/frontier/node metadata。
- 对 selector 提供候选节点列表。

3. `vln_ce_baseline/topo/node_memory.py`
- 后续升级到节点级证据记忆时使用。

### 7.2 需改文件
1. `vln_ce_baseline/vlnce_integration/inference_hook.py`
- 在触发 `BACKTRACK` 前构造 `SelectionContext`；
- 调用 selector 产出 `backtrack_target_node`；
- 将 `selected_score` 和 `reason` 写入 step log。

2. `vln_ce_baseline/vlnce_integration/action_primitives.py`
- 现阶段可继续沿用统一 BACKTRACK 轨迹；
- 第二阶段需扩展为和 `target_node_id` 关联的回退策略或目标规划接口。

3. `vln_ce_baseline/disambig_controller.py`
- 保持是否触发 `BACKTRACK` 的职责；
- 不负责目标节点选择，避免职责耦合过重。

### 7.3 日志字段新增建议
至少新增：
- `backtrack_target_score`
- `backtrack_target_reason`
- `backtrack_ranked_candidates`
- `backtrack_distance`
- `backtrack_expected_info_gain`
- `backtrack_loop_penalty`

## 8. 当前建议
如果只做一个最小可验证版本，建议执行顺序如下：

1. 在 `v2.2` 下把 selector 原型跑通；
2. 用一组手写候选样例验证排序逻辑；
3. 再决定主线里先接日志还是先接真正的 topo state。

当前最重要的判断标准不是“选得是否全局最优”，而是“输出是否稳定、可解释、非常量”。
