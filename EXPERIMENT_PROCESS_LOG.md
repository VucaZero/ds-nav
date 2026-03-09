# ds-nav 实验过程记录（第4类文档）

最后更新：2026-03-10
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

## 5. Round 009 Review（E3 全量对比完成）

### 5.1 轮次目标
- 以 Round008 冻结候选 TEN-R v6 为起点，完成 E3 全量（1839ep）对比。
- 输出可供后续 E4-E9 使用的全量基线证据。

### 5.2 实验证据路径
- 设计报告：`reports/round_009/01_design_report.md`
- 结构报告：`reports/round_009/02_file_structure_report.md`
- 结果报告：`reports/round_009/03_experiment_result_report.md`
- 结构化汇总：
  - `reports/round_009/summary/round_status.json`
  - `reports/round_009/summary/e3_full_metrics.json`
  - `reports/round_009/summary/ROUND_009_SUMMARY.md`
- 完成 run：
  - `reports/round_009/logs/01_e3_full_ten_r_v6_1839.log`
  - `reports/round_009/logs/02_e3_full_b1_1839.log`
  - `reports/round_009/logs/03_e3_full_ours_r_1839.log`
  - `reports/round_009/raw/e3_full_ten_r_v6_1839/TEN-R/`
  - `reports/round_009/raw/e3_full_b1_1839/B1/`
  - `reports/round_009/raw/e3_full_ours_r_1839/Ours-R/`
- 历史失败/中断留痕：
  - `reports/round_009/logs/archive/`
  - `reports/round_009/raw/archive/`

### 5.3 结果汇总（最终）
- `e3_full_ten_r_v6_1839` 已完成（1839ep）：
  - `avg_trigger_rate=0.0918`
  - `max_trigger_rate=0.1200`
  - `la_sum=9165`
  - `bt_sum=18972`
  - `bt_ratio=0.0617`
  - `conflict_k_max=0.2404`
  - `conflict_k_nonzero_count=306873`
  - `runtime=08:40:00`
- `e3_full_b1_1839` 已完成（1839ep）：
  - `avg_trigger_rate=0.1218`
  - `max_trigger_rate=0.1260`
  - `la_sum=111959`
  - `bt_sum=0`
  - `action_count_sum=918560`
  - `conflict_k_nonzero_count=0`
  - `runtime=10:59:33`
- `e3_full_ours_r_1839` 已完成（1839ep）：
  - `avg_trigger_rate=0.9631`
  - `max_trigger_rate=1.0000`
  - `la_sum=885428`
  - `bt_sum=0`
  - `action_count_sum=918164`
  - `conflict_k_nonzero_count=820047`
  - `runtime=13:07:46`

### 5.4 Bad Case
1. `B1`：触发率看似健康，但 `bt_sum=0` 且 `action_count_sum` 相对 TEN-R 膨胀近 3 倍，说明其主要问题是“高成本扫描”而非越界触发。
2. `Ours-R`：`avg_trigger_rate=0.9631`、`max_trigger_rate=1.0`，几乎每步触发，已经明显违反当前 safety 约束。
3. `Ours-R`：虽然 `conflict_k_nonzero_count` 很高，但未形成任何 `BACKTRACK`，反而造成了极端扫描成本，说明规则门控在全量场景下发生了失稳。
4. `TEN-R`：仍存在极低触发尾部样本（`min_trigger_rate=0.004`），后续在 E4/E9 中仍值得继续观察。

### 5.5 归因判断（框架 vs 方法）
- 框架侧：三组全量 raw 均已完整落盘，说明执行链路最终可用。
- 方法侧：
  - `TEN-R` 保持稳定，是当前唯一可进入下一阶段的主线方法；
  - `B1` 主要暴露效率问题；
  - `Ours-R` 主要暴露触发失控问题。

### 5.6 Potential Optimization
1. 按阶段计划进入 `E4` 噪声鲁棒性实验，主线固定 `TEN-R v6`。
2. 在 E4 中保留 `B1` 和 `Ours-R` 作为退化对照，但不再作为主线候选推进。
3. 若需要补齐任务级 `SR/SPL/NE/TL` 结论，应先补一个统一 evaluator 导出流程。
4. 在后续轮次中继续把 `action_count_sum` 与 runtime 作为硬门禁，避免“过程触发正常但成本不可接受”的假阳性。

### 5.7 本轮阶段结论
- Round009 已完成 E3 全量对比的三组主实验。
- 当前推荐路线明确：`TEN-R v6` 进入下一阶段；`B1` 与 `Ours-R` 保留为对照与失败案例。
