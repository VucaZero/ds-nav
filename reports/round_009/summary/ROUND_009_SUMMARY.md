# Round 009 Summary

## Overview
- `plan_version`：`v2.0-active`
- E3 全量对比现已完成：`TEN-R`、`B1`、`Ours-R` 三组全量 raw 全部落盘。
- 从过程指标和 safety 约束看，`TEN-R v6` 是当前唯一稳定且成本可控的主线方案。
- `B1` 和 `Ours-R` 都不适合继续作为后续主线方法推进。

## Metrics Snapshot
- `TEN-R episodes=1839, avg_trigger_rate=0.0918, max_trigger_rate=0.1200, bt_sum=18972, runtime=08:40:00`
- `B1 episodes=1839, avg_trigger_rate=0.1218, max_trigger_rate=0.1260, bt_sum=0, action_count_sum=918560, runtime=10:59:33`
- `Ours-R episodes=1839, avg_trigger_rate=0.9631, max_trigger_rate=1.0000, bt_sum=0, action_count_sum=918164, runtime=13:07:46`

## Analysis
### 成功
- `TEN-R` 全量 run 继续通过当前过程门禁，且保留有效回退链路。
- E3 三个主对比组的完整 raw 证据已全部补齐，Round009 达到报告闭环要求。

### 失败
- `B1` 的动作成本相对 `TEN-R` 膨胀约 `+198.5%`，并且没有回退能力。
- `Ours-R` 几乎全程触发，`avg_trigger_rate` 与 `max_trigger_rate` 都明显越界，是当前最不稳定的一组。
- 当前 inference 入口未同步生成统一的官方任务指标文件，因此本轮最终结论以过程与安全指标为主。

### 证据映射
- `reports/round_009/logs/01_e3_full_ten_r_v6_1839.log`
- `reports/round_009/logs/02_e3_full_b1_1839.log`
- `reports/round_009/logs/03_e3_full_ours_r_1839.log`
- `reports/round_009/raw/e3_full_ten_r_v6_1839/TEN-R/`
- `reports/round_009/raw/e3_full_b1_1839/B1/`
- `reports/round_009/raw/e3_full_ours_r_1839/Ours-R/`
- `reports/round_009/summary/e3_full_metrics.json`

## Next
- 按实验设计进入 `E4` 噪声鲁棒性实验。
- 主线固定 `TEN-R v6`；`B1` 与 `Ours-R` 作为对照与失败案例保留。
