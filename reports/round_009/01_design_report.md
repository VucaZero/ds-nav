# Round 009 设计报告（E3 全量对比完成）

## 1. 本轮目标
1. 执行 E3 Plan C 全量对比（1839ep）主线 run。
2. 以 Round008 冻结候选 TEN-R v6 作为首发全量验证对象。
3. 输出可直接进入 E4 的全量基准证据。
4. 补齐统一任务级 evaluator，离线导出 `SR/SPL/NE/TL`。

## 2. 执行矩阵（本轮完成状态）
- `e3_full_ten_r_v6_1839`
  - method: `TEN-R`
  - 参数：`ten_window=20, scan_budget=0.45, cooldown_steps=10`
  - status: `completed`
- `e3_full_b1_1839`
  - method: `B1`
  - 参数：`NUM_ENVIRONMENTS=4, IL.batch_size=4`
  - status: `completed`
- `e3_full_ours_r_1839`
  - method: `Ours-R`
  - 参数：`NUM_ENVIRONMENTS=4, IL.batch_size=4`
  - status: `completed`

## 3. 口径与门禁
- 指标口径遵循 `EXPERIMENT_DESIGN.md`。
- 过程指标：`trigger_rate / bt_sum / conflict_k_nonzero_count / action_count_sum`。
- 任务指标：`SR / SPL / NE / TL`。
- 新增硬门禁：`action_count_sum` 相对冻结候选不得无约束膨胀。
- 吞吐配置：Round009 全量 run 统一：
  - `NUM_ENVIRONMENTS=4`
  - `IL.batch_size=4`

## 4. 产物要求
- `logs/`：运行日志。
- `raw/`：predictions + episode_logs + task_metrics。
- `summary/`：json + md（含 Analysis）。

## 5. 轮次结论
- `TEN-R`、`B1`、`Ours-R` 三个主对比组的全量 raw 与任务级指标已全部补齐。
- 从过程指标与任务指标联合看，`TEN-R` 是当前唯一兼顾稳定性、成本和任务性能的主线方案。
- `B1` 与 `Ours-R` 在任务级指标上同样显著弱于 `TEN-R`，进一步确认它们不适合作为后续主线。
