# Round 009 实验结果报告（E3 全量对比进行中）

## 1. 执行状态
- 轮次状态：`in_progress`
- 已完成：`e3_full_ten_r_v6_1839`（TEN-R，全量 1839ep）
- 待执行：`e3_full_b1_1839`、`e3_full_ours_r_1839`

## 2. 当前已完成 run 结果

| run | method | episodes | la_sum | bt_sum | disambig_sum | action_count_sum | avg_trigger_rate | min_trigger_rate | max_trigger_rate | bt_ratio | conflict_k_max | conflict_k_nonzero_count | runtime |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `e3_full_ten_r_v6_1839` | TEN-R | 1839 | 9165 | 18972 | 28137 | 307681 | 0.0918 | 0.0040 | 0.1200 | 0.0617 | 0.2404 | 306873 | 08:40:00 |

门禁判定（TEN-R 全量）：
- `avg_trigger_rate in [0.05, 0.45]`：通过（0.0918）
- `max_trigger_rate <= scan_budget(0.45)`：通过（0.1200）
- `bt_ratio <= 0.08`：通过（0.0617）
- `conflict_k_nonzero_count > 0`：通过（306873）
- `bt_sum > 0`：通过（18972）

## 3. Analysis
### 成功项
1. TEN-R 在 1839 全量上保持了与 Round008 一致的触发稳定区间，没有出现触发爆炸或回退失活。
2. `conflict_k` 与 `BACKTRACK` 链路在全量数据上持续激活，说明时序证据机制具备规模稳定性。
3. 全量运行在单次执行内完成，原始产物完整落盘（predictions + episode_logs）。

### 失败项
1. 本轮只完成 TEN-R，B1/Ours-R 全量尚未跑完，E3 全量对比结论还不能闭环。
2. `min_trigger_rate=0.004` 显示仍有极低触发样本，需在后续 bad case 中定位是否存在时序盲区。

### 证据对应
- 日志：`reports/round_009/logs/01_e3_full_ten_r_v6_1839.log`
- raw：`reports/round_009/raw/e3_full_ten_r_v6_1839/TEN-R/`
- 结构化汇总：`reports/round_009/summary/e3_full_metrics.json`

## 4. 下一步
1. 执行 `e3_full_b1_1839`。
2. 执行 `e3_full_ours_r_1839`。
3. 完成 E3 全量横向对比并收敛到 E4 噪声鲁棒性实验。
