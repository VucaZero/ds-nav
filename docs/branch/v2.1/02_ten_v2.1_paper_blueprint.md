# TEN v2.1 可发论文版方法蓝图

版本：`v2.1`  
更新时间：2026-03-05  
目标：形成可投稿顶刊/顶会的完整方法方案（理论 + 算法 + 实验 + 工程）

## 1. 研究问题与创新主张
- 任务：视觉语言导航中的在线消歧与纠错。
- 核心痛点：单步阈值门控无法稳定处理“无知（ignorance）与矛盾（conflict）”。
- 创新主张：
  1. 节点级时序证据网络（Node-centric Temporal Evidence Graph, NTEG）。
  2. 解耦不确定性（epistemic / contradiction / policy ambiguity）并联合建模。
  3. 基于期望信息增益与约束优化的纠错策略（Scan/Rewind）。

## 2. 数学定义（可写入论文方法章节）
1. 命题与状态
- 在时刻 `t`，对每个拓扑节点 `v` 与命题 `i` 定义框架：
  - `Omega_i = {H_i, not H_i, Theta_i}`
  - 质量函数 `m_{i,t}^v: 2^{Omega_i} -> [0,1]`, `sum_A m_{i,t}^v(A)=1`

2. 多源证据质量构造
- 证据源 `s in {align, geo, progress}` 产出 `m_{i,t}^{v,s}`。
- 动态可靠度折扣：
  - `tilde{m}_{i,t}^{v,s}(A)=alpha_s(t) m_{i,t}^{v,s}(A), A != Theta`
  - `tilde{m}_{i,t}^{v,s}(Theta)=1-alpha_s(t)+alpha_s(t)m_{i,t}^{v,s}(Theta)`

3. 时序融合
- 节点级记忆更新：
  - `m_{i,t}^v = Fuse(lambda m_{i,t-1}^v, {tilde{m}_{i,t}^{v,s}}_s)`
  - `lambda in (0,1]` 为时间折扣。
- 冲突：
  - `K_{i,t}^v = sum_{B cap C = empty} m_1(B)m_2(C)`（多源扩展）

4. 三类不确定性解耦
- `U_epi(t) = mean_{v,i} m_{i,t}^v(Theta_i)`
- `U_con(t) = mean_{v,i} K_{i,t}^v`
- `U_pol(t) = H(pi_t) / log(|A|)`（策略熵归一化）
- 总体风险特征向量：
  - `z_t = [U_epi, U_con, U_pol, dU_epi/dt, dU_con/dt, frontier, visited, margin, value]`

5. 纠错决策（约束优化）
- 高层动作 `a_t^h in {FOLLOW, SCAN(k), REWIND(v*)}`
- 目标：
  - `max E[Delta I_t(a_t^h)] - c_scan * C_scan - c_rew * C_rew`
  - s.t. `trigger_rate <= scan_budget`, `cooldown >= c0`
- 其中 `Delta I_t` 为动作后证据熵下降的期望值（信息增益）。

## 3. 训练目标（TEN-L 主线）
1. 门控头损失
- `L_gate = CE(y_gate, p_gate)`，标签由“是否带来正向后效”生成。
- 正向后效定义：触发后 `N` 步内 `Delta SR_proxy > 0` 或 `Delta U_epi < 0`。

2. 回退目标损失
- `L_rewind = CE(y_node, p_node)` 或 `ListNet` 排序损失。
- 标签由“回退后恢复进度/信息增益最大”的节点构造。

3. 校准损失
- `L_calib = Brier(p_corr, y_corr) + beta * ECE_bin`

4. 安全与成本约束
- `L_safe = gamma1 * ReLU(trigger_rate - budget)^2 + gamma2 * ReLU(bt_rate - bt_budget)^2`

5. 总损失
- `L = L_gate + w1 L_rewind + w2 L_calib + w3 L_safe`

## 4. 实验矩阵（论文主表 + 消融 + 鲁棒）
1. 主对比（E3）
- `B0 / B1 / Ours-R / TEN-R / TEN-L`
- 指标：`SR, SPL, NE, TL, trigger_rate, bt_sum, conflict_nonzero`

2. 鲁棒性（E4）
- 扰动：视觉噪声、指令扰动、观测延迟
- 指标：退化斜率、恢复速度、稳定区间

3. 消融（E5-E7）
- `w/o temporal`, `w/o topo`, `w/o budget/cooldown`, `w/o U_con`, `w/o U_epi`

4. 骨干正交性（E8）
- `CMA / DUET / HAMT / ETPNav` + TEN
- 指标：绝对增益 + 相对增益 + 统计显著性

5. 可靠性与校准（E9）
- `ECE, Brier, NLL, Risk-Coverage, AURC`
- 证明“触发概率可解释且可校准”

## 5. 落地改造清单（工程实施）
1. 新增模块
- `vln_ce_baseline/evidence_graph/`
  - `mass_builder.py`：三元质量构造与源折扣
  - `node_memory.py`：节点级证据记忆
- `vln_ce_baseline/temporal_fusion/`
  - `ds_temporal.py`：折扣融合与冲突累计
- `vln_ce_baseline/gating/`
  - `risk_head.py`：TEN-L 门控头
  - `constrained_policy.py`：预算与冷却约束求解
- `vln_ce_baseline/topo/`
  - `node_selector.py`：回退目标选择

2. 兼容改造
- `vln_ce_baseline/vlnce_integration/inference_hook.py`
  - 接入 `z_t` 特征与约束决策；
  - 落实 `BACKTRACK(target_node_id)`。
- `vln_ce_baseline/vlnce_integration/action_primitives.py`
  - 参数化 `SCAN(k)` 和 `REWIND(v*)`。
- `vln_ce_baseline/disambig_controller.py`
  - 从硬阈值接口升级为风险向量 + 约束决策接口。

3. 日志口径增强（必须）
- 新增：
  - `u_epi`, `u_con`, `u_pol`, `delta_u_epi`, `delta_u_con`
  - `expected_info_gain`, `rewind_target_score`, `rewind_target_node`
  - `constraint_violation_budget`, `constraint_violation_cooldown`

## 6. 里程碑与验收门禁
1. M1（正确性）
- `conflict_k_nonzero_count > 0`
- `bt_sum > 0`
- `rewind_target_node` 非常量

2. M2（稳定性）
- `avg_trigger_rate in [0.05, 0.45]`
- `max_trigger_rate <= scan_budget`

3. M3（性能与可靠性）
- TEN-R/TEN-L 在 `SR/SPL` 不弱于 B1
- `ECE/Brier` 明显改善

4. M4（可发表性）
- 跨骨干正交增益成立
- 消融证明每个关键模块均有独立贡献

## 7. 论文叙事建议
- 标题方向：`Uncertainty as Structured Evidence: Constrained Temporal Evidence Graphs for VLN`
- 主线叙事：
  - 先证明传统阈值门控为何失效；
  - 再给出解耦不确定性 + 节点级时序证据图；
  - 最后展示“可靠性提升 + 成本可控 + 跨骨干泛化”。
