# ds-nav 实验过程记录（第4类文档）

最后更新：2026-03-06  
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

## 5. Round 009 Review（E3 全量对比进行中）

### 5.1 轮次目标
- 以 Round008 冻结候选 TEN-R v6 为起点，启动 E3 全量（1839ep）对比。
- 输出可供 B1/Ours-R 对齐比较的全量基线证据。

### 5.2 实验证据路径
- 设计报告：`reports/round_009/01_design_report.md`
- 结构报告：`reports/round_009/02_file_structure_report.md`
- 结果报告：`reports/round_009/03_experiment_result_report.md`
- 结构化汇总：
  - `reports/round_009/summary/round_status.json`
  - `reports/round_009/summary/e3_full_metrics.json`
  - `reports/round_009/summary/ROUND_009_SUMMARY.md`
- 已完成 run：
  - 日志：`reports/round_009/logs/01_e3_full_ten_r_v6_1839.log`
  - raw：`reports/round_009/raw/e3_full_ten_r_v6_1839/TEN-R/`

### 5.3 结果汇总（当前）
- `e3_full_ten_r_v6_1839` 已完成（1839ep）：
  - `avg_trigger_rate=0.0918`
  - `max_trigger_rate=0.1200`
  - `la_sum=9165`
  - `bt_sum=18972`
  - `bt_ratio=0.0617`
  - `conflict_k_max=0.2404`
  - `conflict_k_nonzero_count=306873`
  - `runtime=08:40:00`
- 当前门禁检查通过；但 B1/Ours-R 全量尚未完成，轮次仍为 `in_progress`。

### 5.4 Bad Case（阶段性）
1. 存在极低触发样本（`min_trigger_rate=0.004`），提示仍有时序盲区样本。
2. 长时运行（8h40m）期间个别 episode 耗时波动较大，需要在对比阶段纳入效率归因。

### 5.5 归因判断（框架 vs 方法）
- 框架侧：全量 run 顺利完成并产出完整，执行链路稳定。
- 方法侧：TEN-R 主体稳定，但“低触发尾部样本”仍需针对性诊断。

### 5.6 Potential Optimization
1. 完成 B1/Ours-R 全量后，增加“低触发尾部样本”专题分析。
2. 在 E3 全量对比结论中加入运行时成本指标（总时长、动作总量）作为并列判据。
3. 进入 E4 前固定 TEN-R v6 作为鲁棒性主线，避免参数漂移。

### 5.7 异常与流程改进
- 本轮出现“run 已完成但报告未回填”的流程缺口。
- 根因：执行与回填未绑定自动收尾动作，导致 `round_009` 停留在初始化模板。
- 已修复：本次已补齐 `round_009` 报告与 summary，并同步更新总过程日志。
