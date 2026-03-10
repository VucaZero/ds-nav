# Round 009 Summary

## Overview
- `plan_version`：`v2.0-active`
- E3 全量对比现已完成：`TEN-R`、`B1`、`Ours-R` 三组全量 raw 与任务级指标全部补齐。
- `TEN-R v6` 是当前唯一在任务指标、过程指标和运行成本上同时保持可接受表现的主线方案。

## Metrics Snapshot
- `TEN-R: SR=0.2947, SPL=0.2470, NE=7.1512, TL=11.0727, avg_trigger_rate=0.0918`
- `B1: SR=0.0587, SPL=0.0585, NE=8.1638, TL=1.8389, avg_trigger_rate=0.1218`
- `Ours-R: SR=0.0185, SPL=0.0176, NE=8.7313, TL=0.6707, avg_trigger_rate=0.9631`

## Analysis
### 成功
- `TEN-R` 在任务级指标上显著领先于 `B1` 和 `Ours-R`，且保留有效回退链路。
- 统一 evaluator 已建立，Round009 的任务级与过程级证据已经闭环。

### 失败
- `B1` 任务性能显著偏弱，说明高频熵门控扫描并未转化为有效导航收益。
- `Ours-R` 同时表现出任务级退化与过程级触发爆炸，是当前最不稳定的一组。
- `B1/Ours-R` 都没有形成可替代 `TEN-R` 的证据。

### 证据映射
- `reports/round_009/logs/01_e3_full_ten_r_v6_1839.log`
- `reports/round_009/logs/02_e3_full_b1_1839.log`
- `reports/round_009/logs/03_e3_full_ours_r_1839.log`
- `reports/round_009/summary/task_metrics_round009.json`
- `reports/round_009/summary/e3_full_metrics.json`

## Next
- 进入 `E4` 噪声鲁棒性实验。
- 首轮先执行 `TEN-R` 主线噪声探针。
