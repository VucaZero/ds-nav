# ds-nav 方法结构说明（TEN v2 / Temporal Evidence Network）

最后更新：2026-03-05（v2 草案）
适用范围：`/home/data/czh/ds-nav`

> 关键词：时序证据网络 TEN、结构化证据/冲突、可学习门控、与 DUET/HAMT/ETPNav 兼容、宏观序列地标任务

---

## 0. 文档定位
- 本文件描述 ds-nav 的**方法路径 v2**（TEN：Temporal Evidence Network）；
- 与 `EXPERIMENT_DESIGN.md` 的关系：
  - 本文件负责“方法结构与接口约束”
  - `EXPERIMENT_DESIGN.md` 负责“术语/变量/阶段命名的唯一源”
- 与 `PROJECT_STRUCTURE.md` 的关系：
  - 本文件定义**新增模块**如何落在项目结构内（不改动原有骨干）
- 与 `EXPERIMENT_PROCESS_LOG.md` 的关系：
  - 本文件修复 Round007 指出的设计缺陷：conflict 长期为 0、BACKTRACK 不触发、DS 被熵吞噬

---

## 1. v1（当前初版）回顾与缺陷定位（必须显式声明）

### 1.1 v1 方法目标（已实现）
v1 以 VLN-CE 官方推理链路为骨架，实现：
- DS 不确定性估计：`uncertainty/conflict/ignorance`
- 高层门控：`FOLLOW / LOOK_AROUND / BACKTRACK`
- step/episode 日志闭环输出

### 1.2 v1 的关键实现口径（冻结说明）
- v1 Ours-R：规则门控（阈值规则 + DS/熵融合）
- 当前为了“恢复触发”，采用：
  - `uncertainty = max(ds_uncertainty, entropy_norm)`（熵下限校准）
  - E2 使用“单步纠偏 / LOOK_AROUND 轻量序列”
- E2 现状：阈值 0.68 触发过强（max_trigger_rate 超上限），0.85 触发不足（avg_trigger_rate 不达标）

### 1.3 v1 缺陷（Round007 结论）
结论：主要是**方法设计问题**，非仅调参问题
- conflict 全程接近 0 → Conflict 分支结构性失活 → BACKTRACK 从未触发
- 触发几乎全由 LOOK_AROUND + uncertainty_threshold 单一控制
- `max(ds, entropy)` 使 DS 对决策贡献被吞噬：DS 不能形成“可控的冲突/无知驱动”

---

## 2. v2 核心：Temporal Evidence Network（TEN）

### 2.1 设计目标（v2 必达）
把 v1 的“单步 DS 指标 + 阈值门控”升级为：
1) **时序证据网络**：证据在时间与结构上可累积、可回溯、可解释；
2) **冲突可产生**：K/conflict 在真实运行中非零，且可触发纠错链路；
3) **门控可学习/可约束**：从单阈值触发升级为连续门控（带预算与冷却）；
4) **可插拔兼容强骨干**：TEN 作为外挂层，可接 DUET/HAMT/ETPNav 等 backbone，
   骨干输出 logits/waypoints，TEN 输出风险与纠错调制信号。

> 参考：DUET 强调“在线拓扑图 + dual-scale 规划”:contentReference[oaicite:12]{index=12}；
> HAMT 强调“长历史编码”:contentReference[oaicite:13]{index=13}；
> ETPNav 强调“在线拓扑规划 + 高低层分解”:contentReference[oaicite:14]{index=14}。

---

## 3. v2 方法总览：四层闭环（L0-L3）

### L0 Backbone 执行层（保持不动）
- 输入：instruction + obs + history
- 输出：action logits / waypoint / stop decision
- 兼容：CMA（当前 B0/B1）、DUET:contentReference[oaicite:15]{index=15}、HAMT:contentReference[oaicite:16]{index=16}、ETPNav:contentReference[oaicite:17]{index=17}

### L1 结构载体层（Topo/History 载体，TEN 绑定对象）
- Topo 节点：由 DUET/ETPNav 的在线拓扑图或本项目轻量 topo（v2 新增）
- History 片段：窗口内 obs embedding（可用 HAMT history 编码作载体）

### L2 TEN 证据层（核心）
对“结构节点/地标命题”维护 DS belief state：
- 对每个命题 i：
  - `m_i(H), m_i(¬H), m_i(Θ)` 以及 `K_i`（冲突）
- 支持：
  - 多源证据（语言-视觉对齐 / 几何一致性 / 进度一致性）
  - 时序更新（折扣 + 衰减 + 滞回 + 窗口融合）
- 关键：证据绑定到**节点或地标**而非单步，从而让冲突积累可见。

### L3 门控与纠错层（Gating + Rewind/Backtrack）
- 输入：TEN 输出（Θ/K 及其趋势）、policy 不确定性（entropy/margin/value）、结构信息（frontier/visited）
- 输出：连续门控信号：
  - `p_scan`：LOOK_AROUND/scan 强度（可映射为 scan steps）
  - `p_rewind`：回退倾向（选择回退目标节点）
  - `budget/cooldown`：预算与冷却（安全约束）

---

## 4. v2 的关键机制（替代 v1 “阈值触发”）

### 4.1 证据构造：从观测到 DS 质量函数（Mass Construction）
对每步 t、命题 i：
- 证据源拆分（至少三类）：
  1) Align evidence（instruction-landmark grounding）
  2) Geometry evidence（topo/pose consistency）
  3) Progress evidence（toward-next-landmark）
- 输出单步质量：
  - `m_t(H_i), m_t(¬H_i), m_t(Θ)`（显式三元质量）
- 源可靠度折扣：
  - `α_s(t)`：对每类证据源动态折扣（可学习/可标定）

> 目的：让 conflict 不再长期为 0，并让 Θ 可被“主动观测”降低。

### 4.2 时序融合（Temporal Update）
对同一命题 i：
- `m_i^{t} = TemporalFuse(m_i^{t-1}, m_t)`，同时更新 `K_i^t`
- 包含：时间衰减、滞回、窗口统计（均值/斜率/方差）
- 输出可解释趋势特征：`Θ_slope`, `K_slope`, `post_scan_deltaΘ`

### 4.3 回退机制（Backtrack / Rewind）必须参数化
v1 的 BACKTRACK 未触发（bt_sum=0），
v2 要求 BACKTRACK 具备“回退到哪里”的显式目标：
- `BACKTRACK(target_node_id)`：回退到“最近可信节点/信息增益最大节点/前沿”
- 回退触发条件：
  - `K` 持续高（T 步）且 scan 无法降低 Θ
  - 或 “进度一致性”长期背离

### 4.4 门控从阈值升级为可学习（Policy-aware gating head）
- v1：`uncertainty > threshold` 单触发 → 两极分化（0.68 爆炸/0.85 沉默）
- v2：学习一个轻量 gating head（可先离线监督）
  - 输入：TEN 特征 + policy 特征 + topo 特征
  - 输出：`p_scan, p_rewind, budget`
  - 约束：触发率上限（安全）、连续触发抑制（cooldown）

---

## 5. 与 DUET/HAMT/ETPNav 的兼容策略（v2 工程原则）
原则：TEN 是“外挂层”，不侵入 backbone 主干训练。
- DUET：直接复用其在线 topo 图作为 TEN node 载体:contentReference[oaicite:20]{index=20}
- HAMT：复用其 history encoding 作为 TEN 的“证据缓存/一致性特征”:contentReference[oaicite:21]{index=21}
- ETPNav：TEN 输出风险信号，调制 high-level planner 的 waypoint 排序与回退目标:contentReference[oaicite:22]{index=22}

---

## 6. v2 需要新增的日志口径（顶刊/复现必需）
在现有 `episode_logs.json.step_log` 基础上新增字段：
- TEN per-step：
  - `theta`, `conflict_k`, `bel_h`, `bel_not_h`
  - `theta_slope`, `k_slope`, `post_scan_delta_theta`
- Gating：
  - `p_scan`, `p_rewind`, `budget_left`, `cooldown_left`
  - `backtrack_target_node`
- Topo/History：
  - `topo_node_id`, `frontier_count`, `visited_count`

---

## 7. v2 最小可交付（MVP）清单（用于下一轮落地）
1) TEN 时序更新（Θ/K 有趋势与滞回）
2) BACKTRACK 参数化（target_node）
3) budget + cooldown（安全约束）
4) 门控由“阈值”升级为“趋势规则”（无需训练）
5) 可选：gating head 离线训练（先标定后学习）
