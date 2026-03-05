# ds-nav 当前方法诊断与优化方向报告（v2.1）

版本：`v2.1`  
更新时间：2026-03-05  
证据范围：`reports/round_007`、`reports/round_008`、`vln_ce_baseline/*`

## 1. 结论摘要
- 当前 TEN 实现已具备“可运行 + 触发率可控”能力，但仍未形成“结构化不确定性驱动纠错”的闭环。
- 关键门禁未过：`conflict_k` 非零分布缺失、`BACKTRACK` 未触发。
- 根因偏“方法结构问题”，不是简单阈值调参问题。

## 2. 证据与现象
- Round008 结果：`bt_sum=0`、`conflict_k_max=0`，门禁失败。
- step 日志分布：
  - `action_type` 仅 `FOLLOW/LOOK_AROUND`；
  - `backtrack_target_node` 恒为 `-1`；
  - `topo_node_id` 恒为 `-1`，`frontier_count` 恒为 `0`。
- 触发主要受 `uncertainty` 和冷却机制影响，`conflict` 分支几乎未参与决策。

## 3. 辩证分析（定义 / 融合 / 使用）
1. 定义层问题
- 文档目标是命题级 `m(H), m(not H), m(Theta)`，但实现中 `not H` 缺失，冲突难以有效表达。
- `uncertainty` 同时混入 DS 与策略熵，语义未解耦，导致“可解释性弱 + 可控性弱”。

2. 融合层问题
- 当前采用 `uncertainty = max(ds_uncertainty, entropy_norm)`，DS 容易被熵下限接管。
- conflict 经过压缩后动态范围过小，难以越过回退阈值，造成 BACKTRACK 长期失活。
- 时序趋势仅使用简化 slope，且窗口实际利用不足，时序建模能力偏弱。

3. 使用层问题
- 纠错动作参数化不足：`BACKTRACK(target_node)` 没有真正落地，回退目标不可学习、不可验证。
- budget/cooldown 在工程上可控，但目前更像“安全裁剪器”，不是“证据驱动器”。

## 4. 潜在优化方向（按优先级）
1. 高优先级（先过方法正确性门禁）
- 不确定性解耦：拆分 `U_epi(Theta)`、`U_con(K)`、`U_pol(entropy)`，禁止直接 `max` 融合。
- 显式三元质量函数：落地 `m(H), m(not H), m(Theta)` 与源可靠度折扣 `alpha_s(t)`。
- 回退目标参数化：实现 `BACKTRACK(target_node_id)` 与目标选择准则（可信度/信息增益）。

2. 中优先级（形成稳定增益）
- 节点级时序证据图：证据绑定 topo node/landmark，并支持冲突累积与传播。
- 决策升级：从硬阈值改为“期望信息增益 - 动作代价”约束决策。
- TEN-L 训练化：先离线标注门控监督，再在线微调安全约束。

3. 高创新优先级（冲击顶刊）
- 统一框架：把“不确定性估计 + 纠错决策 + 成本约束 + 校准评估”合为单一理论闭环。
- 跨骨干正交性：证明 TEN 在 CMA/DUET/HAMT/ETPNav 上都可复用并有一致收益。
- 可靠性指标体系：ECE/Brier/风险-覆盖曲线/扰动退化斜率全套报告。

## 5. 风险提示
- 若继续只做阈值扫描，极可能重复 Round007/008 的“两极化触发”问题。
- 若不先补 `conflict/backtrack/topo` 三条链路，TEN 论文贡献会退化为工程调参。
