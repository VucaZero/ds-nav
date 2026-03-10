# 冲顶刊补强计划（v2.2）

版本：`v2.2`
更新时间：2026-03-10
文档定位：基于 `02_senior_reviewer_critique.md` 反推一版面向顶会/顶刊的补强路线，按优先级拆成实验、方法、写作三条 TODO，并回答两个关键战略问题：如何把当前 `TEN` 扩展成真正的证据时序网络，以及是否应把 backbone 扩展到 `DUET/HAMT`。

## 0. 一句话判断
当前最合理的冲顶刊路径不是“继续细调 `TEN-R` 阈值”，而是走一条三阶段收敛路线：
- 第一阶段，把当前 `TEN-R` 从“有效规则系统”打磨成“证据结构明确、实验闭环完整的强系统论文”；
- 第二阶段，把 `TEN` 从规则门控升级为真正的节点级证据时序网络；
- 第三阶段，再用 `DUET/HAMT` 验证其跨 backbone 正交性，完成从“方法可用”到“方法可发表”的跃迁。

如果顺序反过来，先急着换 backbone，再补理论和闭环，风险很高，因为那样只会把当前的启发式缺口放大，而不是补强。

## 1. 总体优先级

### 1.1 P0：三个月内必须打实的东西
- 完成 `E3-E9` 中最关键的闭环缺口：强 baseline、消融、鲁棒、校准、多 seed。
- 把 `BACKTRACK(target_node)` 从占位变量改成真实决策模块。
- 把论文主张从“泛证据图愿景”收缩为“节点级证据时序网络原型 + 约束纠错决策”。

### 1.2 P1：决定能不能冲 `ICRA/RAL`
- 证明 `TEN` 的增益不是只在 `CMA` 和一组手调参数上成立。
- 给出更系统的 embodied 解释：什么时候应该 scan，什么时候应该 rewind，rewind 到哪里，代价是什么。

### 1.3 P2：决定能不能冲更强方法类 venue
- 把 `TEN-L` 做成真正有增益的 learning-based 版本。
- 把解耦不确定性、证据传播、校准可靠性完整做实，形成更强理论闭环。

## 2. 三条 TODO

### 2.1 实验 TODO

#### P0-Experiment：先把“能发系统论文”的证据补齐
1. 补齐 `E3` 主表协议
- 目标：同一 evaluator、同一吞吐配置、同一日志口径下，给出 `B0 / B1 / Ours-R / TEN-R` 的清晰主表。
- 产物：主表 md/json、统一图表、对齐版 summary。
- 验收：所有方法均含 `SR/SPL/NE/TL + trigger_rate + bt_ratio + action_count_sum + runtime`。

2. 补齐 `E4` 对照矩阵
- 目标：至少完成 `TEN-R / B0 / B1 / Ours-R` 在视觉噪声下的统一探针矩阵。
- 最低配置：`p010/p020/p030` 三档强度，固定 seed，固定 episode 子集。
- 验收：给出退化斜率图，而不是只给单点表格。

3. 完成 `E5-E7` 消融
- 目标：回答“到底是哪一部分在起作用”。
- 必做项：`w/o temporal`、`w/o conflict`、`w/o topo-target`、`w/o budget/cooldown`、`w/o rewind`。
- 验收：每个模块都要能解释一类收益或一类失败恢复能力。

4. 完成多 seed 和统计显著性
- 目标：避免被认为是单次 lucky run。
- 最低配置：主表和关键消融做 `3 seeds`，报告均值和标准差。
- 验收：关键结论至少有一种统计显著性或稳健区间证明。

5. 增强 qualitative evidence
- 目标：把过程日志转成论文证据。
- 必做项：成功样例、失败样例、触发热图、rewind case study、噪声下轨迹对比图。
- 验收：至少有 4 类 case taxonomy，每类有图和对应指标。

#### P1-Experiment：决定能不能冲更高档次
1. 完成 `E8` 跨 backbone 正交性
- 目标：证明 `TEN` 不是绑定 `CMA` 的特殊技巧。
- 推荐顺序：`CMA -> DUET -> HAMT`。
- 验收：至少一个 transformer-based backbone 上仍有稳定增益。

2. 完成 `E9` 可靠性与校准
- 目标：把“trigger probability 可解释”从口号变成结果。
- 必做项：`ECE`、`Brier`、risk-coverage、AURC。
- 验收：`TEN` 在可靠性指标上优于纯熵门控和旧规则门控。

3. 增加效率报告
- 目标：适配 `ICRA/RAL` 的系统审稿口味。
- 必做项：额外决策时延、额外显存、episode runtime 增量、成功恢复成本。
- 验收：把“更强”改写成“更强且代价可接受”。

### 2.2 方法 TODO

#### P0-Method：先把当前 `TEN-R` 变成真正的“节点级证据时序网络原型”
1. 拆分三类不确定性，不再继续 `max` 融合
- 当前问题：`uncertainty = max(ds_uncertainty, entropy_norm)` 太启发式。
- 改造目标：显式维护 `U_epi`、`U_con`、`U_pol`。
- 最小落地：step log 中直接输出三者及其趋势项，而不是只输出混合 `theta`。

2. 引入节点级证据状态
- 当前问题：`TEN-R` 的时序状态基本还是 episode 级标量，缺少真正的 node memory。
- 改造目标：对每个 topo node 维护 `m(H)`、`m(not H)`、`m(Theta)` 与 `K`。
- 最小落地：先做稀疏 node memory，只维护 visited/frontier 节点，不做全图爆炸式存储。

3. 让 `BACKTRACK(target_node)` 成为真实优化问题
- 当前问题：`backtrack_target_node=0` 说明回退目标并未被建模。
- 改造目标：根据 expected information gain、历史成功恢复率、拓扑距离三者联合选点。
- 最小落地：先做规则 ranking，再做 learned selector。

4. 从“触发规则”升级到“约束决策”
- 当前问题：现在更像是一组规则在串联触发。
- 改造目标：高层动作为 `FOLLOW / SCAN(k) / REWIND(v*)`，用统一目标函数决策：
  - `maximize expected_info_gain - action_cost`
  - `subject to trigger_budget, rewind_budget, cooldown`
- 最小落地：先做 rule-based constrained scorer，而不是直接上 RL。

5. 把日志字段升级成论文级中间变量
- 必加字段：`u_epi`、`u_con`、`u_pol`、`delta_u_epi`、`delta_u_con`、`rewind_target_score`、`expected_info_gain`、`constraint_violation_*`。
- 作用：后续所有方法解释、消融和校准都依赖这些中间量。

#### P1-Method：把 `TEN` 扩展成真正的证据时序网络
这里给出我建议的结构化升级路线。

1. Layer A：多源质量构造
- 输入源至少分成 `align`、`geometry`、`progress`、`policy` 四类。
- 每个源对每个 node-claim 产出三元质量：`m_s(H)`、`m_s(not H)`、`m_s(Theta)`。
- 每个源带动态可靠度 `alpha_s(t)`，避免某个单源长期统治融合结果。

2. Layer B：节点级时序记忆
- 对每个节点维护时序记忆：
  - `m_t^v = Fuse(lambda * m_{t-1}^v, current_evidence)`
- 这里的关键不是简单滑窗平均，而是“折扣后的证据累积 + 冲突显式保留”。

3. Layer C：图上传播
- 对邻接节点传播有限证据，而不是只在当前节点自循环。
- 推荐只做局部传播：当前节点、父节点、frontier 节点，避免图扩散失控。
- 传播目的：让“回退到哪里”与“下一步该不该看”共享同一个证据底座。

4. Layer D：高层约束策略
- 用风险向量 `z_t = [U_epi, U_con, U_pol, delta, frontier, visited, margin, value]` 驱动高层动作。
- 高层策略不直接替代 backbone，而是决定是否插入 `SCAN` 或 `REWIND`。

5. Layer E：校准与学习
- 当规则版稳定后，再引入 `TEN-L`：
  - 门控头预测 `p(trigger)`；
  - selector 预测 `p(rewind_to=v)`；
  - 校准头约束触发概率的可靠性。

一句话说，真正的证据时序网络不只是“多几个 temporal feature”，而是要满足三个条件：
- 证据是节点绑定的；
- 冲突和无知是显式状态，不是后处理标量；
- 高层动作是在统一证据图上做约束决策，而不是在 episode 级规则上做局部修补。

#### P2-Method：`DUET/HAMT` 是否是合理强化路径
结论是：合理，但必须放在第二阶段，而不是立刻切主线。

原因如下。

1. 为什么合理
- `DUET/HAMT` 的表征更强，通常比 `CMA` 更不容易被 reviewer 视为“老旧弱骨干 + 外挂规则”的组合。
- 如果 `TEN` 在更强 backbone 上仍有增益，论文主张会从“修补弱骨干”升级为“与 backbone 正交的纠错层”。
- 对 `ICLR/ICRA/RAL` 来说，跨 backbone 正交性是很强的说服点。

2. 为什么不能现在就切
- 当前 `TEN` 的方法实体还没完全做实，直接切 `DUET/HAMT` 会把接口适配、日志对齐、训练细节差异全部混进来。
- 一旦结果不好，你会分不清是 backbone 迁移问题，还是 TEN 自身问题。
- 审稿上也不划算，因为你还没先在一个 backbone 上讲清楚原理，就急着做广度扩展。

3. 最合理的执行顺序
- Step 1：先在 `CMA` 上完成节点级证据状态、真实 rewind target、关键消融和校准。
- Step 2：优先迁移到 `DUET`，因为它对结构化历史和 cross-modal 关系更敏感，比较适合验证 `TEN` 的图式收益。
- Step 3：再迁移到 `HAMT`，把它作为更强的 transformer backbone 佐证正交性。

4. 怎么判断值不值得继续迁移
- 如果 `TEN` 在 `DUET` 上仍能带来：
  - 稳定非零 `rewind_target_node` 分布；
  - `SR/SPL` 正增益；
  - 过程成本不过量；
  - 可靠性指标改善；
  那么继续上 `HAMT` 是有价值的。
- 如果连 `DUET` 都不能稳定复现收益，那优先回头检查 TEN 的方法假设，而不是盲目铺更多 backbone。

我的建议很明确：`DUET` 是优先级高于 `HAMT` 的第一扩展站，`HAMT` 是用来强化发表说服力的第二站，不应成为当前主线替代品。

### 2.3 写作 TODO

#### P0-Writing：先让论文主张和现实证据一致
1. 收缩标题和摘要主张
- 不要写成“完整结构化证据图已实现”。
- 应写成“node-aware temporal evidence guided corrective policy”这一档表述。

2. 重写贡献列表
- 贡献 1：提出一类面向在线消歧的时序证据约束框架。
- 贡献 2：实现可运行的 `TEN-R` 原型，并用过程日志证明其回退与成本控制机制有效。
- 贡献 3：在主对比和噪声探针中优于内部对照，并给出失败归因分析。

3. 先把 `TEN-L` 降级为 future work 或扩展项
- 在没有强结果前，不要让学习版承担主贡献。

4. 加强问题动机部分
- 不要只说“我们的模型更好”。
- 要先用失败证据证明：传统阈值门控为何会在“触发不足/触发爆炸”之间失稳。

#### P1-Writing：按顶刊风格组织正文
1. Introduction 要突出三条线
- 问题真：在线消歧和纠错是 embodied VLN 的真实难点。
- 现有方法弱：单步阈值和单源不确定性不能稳定驱动纠错。
- 你的贡献清晰：时序证据 + 约束动作选择。

2. Method 只讲已经做实的结构
- 先讲当前 `TEN-R` 实体；
- 再讲证据网络扩展作为下一阶段或扩展版；
- 避免把蓝图写成既成事实。

3. Experiments 必须从结果导向改成问题导向
- 主表回答：是否有效；
- 消融回答：为何有效；
- 鲁棒性回答：何时失效；
- 校准回答：是否可信；
- 跨骨干回答：是否正交。

4. Discussion 主动承认局限
- 审稿人最容易打的点，你自己先写出来。
- 这会让整体可信度明显提升。

#### P2-Writing：为不同 venue 做版本化包装
1. `ICRA/RAL` 版本
- 更强调 system design、failure recovery、runtime-cost tradeoff、robotic interpretability。

2. `ICLR` 版本
- 更强调 uncertainty decomposition、evidence fusion、calibration、generalization。

3. 当前最现实的写作路线
- 第一版按 `ICRA/RAL` 系统论文口味写；
- 等 `TEN-L + E8 + E9` 站住，再升级成更强方法类版本。

## 3. 建议的实际排期

### 第 1 周到第 2 周
- 把 `BACKTRACK(target_node)` 做实。
- 补齐 `E3` 同协议主表。
- 开始整理 qualitative cases。

### 第 3 周到第 4 周
- 完成 `E4` 统一噪声矩阵。
- 完成 `E5-E7` 最小消融。
- 增加多 seed 和统计汇总。

### 第 5 周到第 6 周
- 引入节点级证据状态和 `U_epi/U_con/U_pol` 日志。
- 初版 `rewind target selector` 落地。
- 起草 `ICRA/RAL` 版正文。

### 第 7 周到第 9 周
- 迁移到 `DUET`。
- 验证跨 backbone 正交性。
- 若 `DUET` 站住，再决定是否扩展到 `HAMT`。

### 第 10 周以后
- 若 `TEN-L` 有明确增益，再准备更强方法类投稿；
- 若 `TEN-L` 仍不稳定，则坚持规则版系统论文路线，不强讲 learning story。

## 4. 最终建议
- 短期目标：按 `ICRA/RAL` 水准补齐系统闭环，不要直接按 `ICLR` 标准包装自己。
- 方法重心：优先把 `TEN` 做成真正的节点级证据时序网络，尤其是 `rewind target` 和解耦不确定性。
- backbone 路线：`CMA` 打实后先上 `DUET`，再看 `HAMT`；这是合理加强路径，但不是当前第一优先级。
- 写作策略：先讲已经被结果证明的东西，再把更大蓝图作为扩展路线，而不是反过来。

如果只允许我给一个最关键动作，那就是：先把 `backtrack_target_node` 从常量变成真正的决策变量。因为这一步一旦做实，`TEN` 才开始真正接近“证据时序网络”，而不只是“更聪明的扫描规则”。
