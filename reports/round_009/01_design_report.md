# Round 009 设计报告（E3 全量对比启动）

## 1. 本轮目标
1. 执行 E3 Plan C 全量对比（1839ep）主线 run。
2. 以 Round008 冻结候选 TEN-R v6 作为首发全量验证对象。
3. 输出可直接进入 E4 的全量基准证据。

## 2. 执行矩阵（本轮）
- `e3_full_ten_r_v6_1839`（优先执行）
  - method: `TEN-R`
  - 参数：`ten_window=20, scan_budget=0.45, cooldown_steps=10`
- `e3_full_b1_1839`（待执行）
- `e3_full_ours_r_1839`（待执行）

## 3. 口径与门禁
- 指标口径遵循 `EXPERIMENT_DESIGN.md`。
- 新增硬门禁：`action_count_sum` 相对冻结候选不得无约束膨胀。

## 4. 产物要求
- `logs/`：运行日志。
- `raw/`：predictions + episode_logs。
- `summary/`：json + md（含 Analysis）。
