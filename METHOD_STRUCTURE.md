# ds-nav 方法结构说明（TEN v2 主线）

最后更新：2026-03-05  
版本：`v2.0-active`  
适用范围：`/home/data/czh/ds-nav`

## 0. 文档定位
- 本文件定义 v2 方法结构、模块边界、接口约束。
- 术语和变量名以 `EXPERIMENT_DESIGN.md` 为唯一命名源。
- v1 冻结版位置：`docs/archive/2026-03-05_v1/METHOD_STRUCTURE.md`。

## 1. v2 目标（由 Round007 问题反推）
Round007 证据显示：`conflict≈0`、`bt_sum=0`、门控基本退化为单阈值触发。  
v2 目标：
1. 让 `conflict_k` 在真实运行中可观测且可触发回退。
2. 把“单步阈值”升级为“时序趋势 + 预算 + 冷却”的门控。
3. 保留与 CMA/B1/Ours-R 的对比兼容，不破坏现有入口与报告链路。

## 2. v2 四层闭环

### L0 Backbone 执行层
- 输入：instruction、obs、history。
- 输出：action logits / waypoint。
- 兼容：CMA（当前主用），后续可接 DUET/HAMT/ETPNav。

### L1 结构载体层
- Topo 载体：node、frontier、visited。
- History 载体：滑窗缓存（TEN window）。

### L2 TEN 证据层（核心）
- 每个命题维护：`bel_h`、`bel_not_h`、`theta`、`conflict_k`。
- 时序更新：折扣、衰减、滞回、窗口统计（`theta_slope`、`k_slope`）。
- 当前实现新增：
  - `historical_visibility` 滑窗融合（默认窗口 20，融合实际用最近 6 帧）
  - 冲突校准（避免 DS 合并后 conflict 饱和）
  - `temporal_uncertainty/temporal_conflict/stagnation_steps` step 级输出

### L3 门控与纠错层
- 输入：TEN 特征 + policy 特征 + topo 特征。
- 输出：`p_scan`、`p_rewind`、`scan_steps`、`backtrack_target_node`。
- 约束：`scan_budget` + `cooldown_steps`。
- 当前实现新增：
  - 时序停滞触发回退（`stagnation_steps` + `theta/conflict` 联合条件）
  - `bt_budget`（默认 0.08）抑制回退过多
  - 回退预算超限自动降级为 `LOOK_AROUND/FOLLOW`

## 3. 工程落点与接口

### 3.1 必改插入点（保持三处骨干）
1. `vln_ce_baseline/vlnce_integration/inference_hook.py`
- 初始化 TEN 状态。
- 每步更新 TEN 并写 step 日志。

2. `vln_ce_baseline/disambig_controller.py`
- 在原接口上升级决策：输出 `action_type`、`scan_steps`、`backtrack_target_node`。

3. `vln_ce_baseline/vlnce_integration/action_primitives.py`
- 支持参数化 `LOOK_AROUND(steps)`。
- 支持参数化 `BACKTRACK(target_node_id)`。

### 3.2 v2 新模块
- `vln_ce_baseline/evidence_graph/`：命题状态与证据图。
- `vln_ce_baseline/temporal_fusion/`：时序融合与冲突累计。
- `vln_ce_baseline/gating/`：规则门控、可学习门控、预算管理。
- `vln_ce_baseline/topo/`：topo 构建与回退目标规划。

## 4. 日志字段约束（只增不删）
必须新增并落盘到 `episode_logs.json.step_log`：
- TEN 字段：`theta`、`conflict_k`、`bel_h`、`bel_not_h`、`theta_slope`、`k_slope`。
- 门控字段：`p_scan`、`p_rewind`、`budget_left`、`cooldown_left`。
- 回退字段：`backtrack_target_node`。
- 结构字段：`topo_node_id`、`frontier_count`、`visited_count`。

## 5. 新版实验与方法设计具体计划（执行顺序）
1. P1（实现门禁）
- 完成 TEN-R 最小链路：`theta/conflict_k` 可更新、可记录。
- 验收：50ep 下 `conflict_k_max > 0`。

2. P2（纠错链路）
- 打通参数化 BACKTRACK。
- 验收：50ep 下 `bt_sum > 0`。

2.1 P2-Calibration（时序校准）
- 避免“冲突全 0”与“冲突饱和”两端失衡。
- 关键指标：
  - `conflict_k_nonzero_count > 0`
  - `bt_ratio <= 0.08`
  - `avg_trigger_rate` 不高于 `scan_budget`

3. P3（安全约束）
- 加入 budget + cooldown。
- 验收：`max_trigger_rate <= scan_budget`。

4. P4（主对比）
- 在 E3 做 `B0/B1/Ours-R/TEN-R/TEN-L` 对比。
- 验收：TEN-R 不弱于 B1，且日志可解释性完整。

5. P5（鲁棒与消融）
- 执行 E4-E7 与 E8-E9。
- 验收：完成退化曲线、消融结论、校准指标。
