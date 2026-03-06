# Round 009 Summary

## Overview
- E3 全量对比已启动并完成首个主线 run：`e3_full_ten_r_v6_1839`。
- 当前轮次状态：`in_progress`（B1/Ours-R 全量待补齐）。

## Metrics Snapshot
- `episodes=1839`
- `avg_trigger_rate=0.0918`
- `max_trigger_rate=0.1200`
- `la_sum=9165`
- `bt_sum=18972`
- `bt_ratio=0.0617`
- `conflict_k_max=0.2404`
- `runtime=08:40:00`

## Analysis
### 成功
- TEN-R 全量 run 通过当前过程门禁，触发率与回退比例保持在安全区间。
- 冲突证据与回退链路在大规模样本下保持稳定激活。

### 失败
- 轮次仍未闭环：B1/Ours-R 全量结果缺失，无法得出 E3 终局对比结论。
- 极低触发样本仍存在，需在下一步 bad case 分析中拆解。

### 证据映射
- `reports/round_009/logs/01_e3_full_ten_r_v6_1839.log`
- `reports/round_009/raw/e3_full_ten_r_v6_1839/TEN-R/`
- `reports/round_009/summary/e3_full_metrics.json`

## Next
- 继续执行 `e3_full_b1_1839` 与 `e3_full_ours_r_1839`，完成 E3 全量对比闭环。
