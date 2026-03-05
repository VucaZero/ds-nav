# ds-nav 实验过程记录（第4类文档）

最后更新：2026-03-05  
范围：`/home/data/czh/ds-nav`

## 1. 文档定位
- 记录每一轮实验/规划结束后的证据闭环：
  - 运行事实
  - 结果汇总
  - 归因分析
  - 优化方向

## 2. 维护规则（强制）
1. 每轮结束后必须更新本文档。
2. 必须包含证据路径（`raw`/`logs`/`summary`）。
3. 每轮必须有 `Bad Case` 与 `Optimization`。
4. 必须明确判断“框架问题 vs 方法问题”。

## 3. Round 007 Review（复盘轮）

### 3.1 证据路径
- `reports/round_007/raw/`
- `reports/round_007/logs/`
- `reports/round_007/summary/`

### 3.2 结果汇总
- E1：完成，B0 全量 1839 ep。
- E2：触发恢复但未收敛；0.68 触发偏强，0.85 触发不足。

### 3.3 Bad Case
- 高触发样本（`trigger_rate` 约 0.55~0.59）出现轨迹接近 500 步上限。

### 3.4 归因判断
- 框架可跑且可复现，主因是方法设计缺陷（`conflict` 分支失活，`BACKTRACK` 未触发）。

### 3.5 Optimization
- 引入 TEN 时序证据与参数化回退。
- 加入 budget/cooldown 限制触发爆炸。

## 4. Round 008 Review（v2 激活 + TEN 时序校准）

### 4.1 轮次目标
- 完成文档版本治理切换（v1 归档，v2 激活）。
- 执行 TEN-R，修复 `conflict_k=0` 与 `bt_sum=0`。
- 验证 Plan A/B 补充矩阵，检查 TEN-R 稳定性与 TEN-L 对照收益。

### 4.2 实验证据路径
- 设计报告：`reports/round_008/01_design_report.md`
- 结构报告：`reports/round_008/02_file_structure_report.md`
- 结果报告：`reports/round_008/03_experiment_result_report.md`
- 结构化汇总：
  - `reports/round_008/summary/round_status.json`
  - `reports/round_008/summary/e3_metrics.json`
  - `reports/round_008/summary/ROUND_008_SUMMARY.md`
- 关键运行日志：
  - `reports/round_008/logs/05_e3_ten_r_w20_budget045_cd10.log`
  - `reports/round_008/logs/06_e3_ten_r_w20_budget045_cd10_temporal_fix_probe10.log`
  - `reports/round_008/logs/07_e3_ten_r_w20_budget045_cd10_temporal_fix_probe10_v2.log`
  - `reports/round_008/logs/08_e3_ten_r_w20_budget045_cd10_temporal_fix_probe10_v3.log`
  - `reports/round_008/logs/09_e3_ten_r_w20_budget045_cd10_temporal_fix_probe5_v4.log`
  - `reports/round_008/logs/10_e3_ten_r_w20_budget045_cd10_temporal_fix_probe3_v5.log`
  - `reports/round_008/logs/11_e3_ten_r_w20_budget045_cd10_temporal_fix_50ep_v6.log`
  - `reports/round_008/logs/12_e3_ten_r_w10_budget045_cd10.log`
  - `reports/round_008/logs/13_e3_ten_r_w20_budget035_cd10.log`
  - `reports/round_008/logs/14_e3_ten_r_w20_budget045_cd06.log`
  - `reports/round_008/logs/15_e3_ten_l_head_w20_budget045_cd10.log`
  - `reports/round_008/logs/16_e3_ten_l_head_w20_budget035_cd10.log`

### 4.3 结果汇总
- TEN-R 最优候选仍为 `e3_ten_r_w20_budget045_cd10_temporal_fix_50ep_v6`：
  - `avg_trigger_rate=0.0923`
  - `max_trigger_rate=0.1026`
  - `bt_sum=403`
  - `bt_ratio=0.0639`
  - `conflict_k_max=0.2404`
- Plan A 追加两组：
  - `w10/budget0.45/cd10` 与 `w20/budget0.35/cd10` 与 v6 几乎一致，说明在当前触发区间下参数不敏感。
  - `w20/budget0.45/cd6` 触发密度显著上升（`avg_trigger_rate=0.1410`），动作总量翻倍（`13171`）。
- Plan B（TEN-L）两组：
  - `avg_trigger_rate` 仅 `0.0440~0.0457`，低于或接近下界；
  - `action_count_sum` 高达 `18059~18574`，明显高成本。

### 4.4 Bad Case
1. `e3_ten_r_w20_budget045_cd06`：`cooldown` 缩短导致频繁干预，episode 长尾显著。
2. `e3_ten_l_head_w20_budget045_cd10`：触发偏低但动作总量极高，表现为“保守触发 + 高时延”的不良组合。
3. `e3_ten_l_head_w20_budget035_cd10`：预算收紧后 learned/backtrack 占比发生漂移，但整体成本问题未解决。

### 4.5 归因判断（框架 vs 方法）
- 框架侧健康：环境、脚本、日志与 raw 产物完整，所有矩阵 run 均正常完成。
- 问题主要在方法侧：
  - TEN-R：`cooldown` 过短会导致时序干预过密。
  - TEN-L：learned gating 对不确定性/冲突的时序处理仍不够稳健，导致成本-收益失衡。

### 4.6 Potential Optimization
1. 保持 TEN-R v6 为冻结候选，推进 E4-E9。
2. 将 `action_count_sum` 与 episode 耗时纳入硬门禁，防止仅靠触发率掩盖成本退化。
3. TEN-L 若重启，优先做时序平滑/稀疏触发改造，再考虑预算阈值微调。

### 4.7 本轮阶段结论
- Round008 已完成 Plan A/B E3 矩阵。
- 当前推荐路线：`TEN-R v6` 进入下一阶段；TEN-L 暂不扩展。
