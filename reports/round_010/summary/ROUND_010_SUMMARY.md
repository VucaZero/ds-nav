# Round 010 Summary

## Overview
- `plan_version`：`v2.0-active`
- `E4` 第一轮矩阵已补全：`TEN-R p010/p020/p030`、`B1 p010`、`Ours-R p010` 全部完成。
- 当前结论已经很清晰：`TEN-R` 是唯一在噪声下仍保持稳定门控且任务性能退化更可控的方法。

## Metrics Snapshot
- `TEN-R p030`: `SR=0.2264`, `SPL=0.1745`, `NE=6.7390`, `TL=13.1291`
- `B1 p010`: `SR=0.0192`, `SPL=0.0192`, `NE=8.6636`, `TL=1.8927`
- `Ours-R p010`: `SR=0.0577`, `SPL=0.0536`, `NE=9.7951`, `TL=1.0639`

## Analysis
### 成功
- `TEN-R` 建立了清晰的噪声强度退化曲线。
- `B1` 和 `Ours-R` 对照都没有显示出比 `TEN-R` 更好的鲁棒性。

### 失败
- 当前矩阵样本量仍偏小，更适合作为阶段性结论而非最终论文级结论。

### 证据映射
- `reports/round_010/logs/01_e4_noise_visual_gaussian_p010_ten_r_v6_probe50.log`
- `reports/round_010/logs/02_e4_noise_visual_gaussian_p020_ten_r_v6_probe50.log`
- `reports/round_010/logs/03_e4_noise_visual_gaussian_p030_ten_r_v6_probe50.log`
- `reports/round_010/logs/04_e4_noise_visual_gaussian_p010_b1_probe50.log`
- `reports/round_010/logs/05_e4_noise_visual_gaussian_p010_ours_r_probe50.log`
- `reports/round_010/summary/task_metrics_round010.json`

## Next
- 可选方向：
  - 冻结 `E4` 第一轮结论并进入下一阶段
  - 或继续扩大 `TEN-R` 样本量/噪声 profile 以强化结论
