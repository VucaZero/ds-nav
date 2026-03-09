# Round 009 设计报告（E3 全量对比完成）

## 1. 本轮目标
1. 执行 E3 Plan C 全量对比（1839ep）主线 run。
2. 以 Round008 冻结候选 TEN-R v6 作为首发全量验证对象。
3. 输出可直接进入 E4 的全量基准证据。

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
- 新增硬门禁：`action_count_sum` 相对冻结候选不得无约束膨胀。
- 吞吐配置：Round009 全量 run 统一：
  - `NUM_ENVIRONMENTS=4`
  - `IL.batch_size=4`
- 注意：当前正式落盘并回填的仍以过程指标为主；本轮推理链路未额外产出统一的官方任务指标文件（`SR/SPL/NE/TL`）。

## 4. 产物要求
- `logs/`：运行日志。
- `raw/`：predictions + episode_logs。
- `summary/`：json + md（含 Analysis）。

## 5. 轮次结论
- `TEN-R`、`B1`、`Ours-R` 三个主对比组的全量 raw 已全部落盘。
- 从过程指标看，`TEN-R` 是唯一同时满足触发率健康区间、回退链路有效、动作成本可控的主线方法。
- `B1` 虽处于触发率安全区间，但动作成本相对 TEN-R 显著膨胀。
- `Ours-R` 出现近乎全程触发的极端行为，已明显违反当前 safety 约束，不适合作为后续主线。
