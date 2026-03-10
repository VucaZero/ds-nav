# Round 009 实验结果报告（E3 全量对比完成）

## 1. 执行状态
- `plan_version`：`v2.0-active`
- 轮次状态：`completed`
- 已完成：
  - `e3_full_ten_r_v6_1839`
  - `e3_full_b1_1839`
  - `e3_full_ours_r_1839`
- 历史失败/中断尝试已归档到 `reports/round_009/logs/archive/` 与 `reports/round_009/raw/archive/`。

## 2. 当前 run 结果

| run | method | status | episodes | SR | SPL | NE | TL | avg_trigger_rate | max_trigger_rate | bt_sum | action_count_sum | runtime | note |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `e3_full_ten_r_v6_1839` | TEN-R | completed | 1839 | 0.2947 | 0.2470 | 7.1512 | 11.0727 | 0.0918 | 0.1200 | 18972 | 307681 | 08:40:00 | 全量完成，门禁通过 |
| `e3_full_b1_1839` | B1 | completed | 1839 | 0.0587 | 0.0585 | 8.1638 | 1.8389 | 0.1218 | 0.1260 | 0 | 918560 | 10:59:33 | 触发率安全，但无回退且任务性能显著偏弱 |
| `e3_full_ours_r_1839` | Ours-R | completed | 1839 | 0.0185 | 0.0176 | 8.7313 | 0.6707 | 0.9631 | 1.0000 | 0 | 918164 | 13:07:46 | 任务性能与 safety 约束同时失稳 |

附加成本对比（相对 `TEN-R`）：
- `B1`：
  - `action_count_sum` `+198.5%`
  - `runtime` `+26.8%`
- `Ours-R`：
  - `action_count_sum` `+198.4%`
  - `runtime` `+51.5%`

## 3. Analysis
### 成功项
1. `TEN-R` 在全量数据上同时保持了最佳任务级指标和稳定的过程门控行为。
2. 统一离线 evaluator 已补齐 `SR/SPL/NE/TL`，Round009 的任务级与过程级证据现已闭环。
3. `TEN-R` 的 `SR/SPL` 明显高于 `B1` 和 `Ours-R`，说明时序门控确实转化为了任务性能增益，而非仅仅过程稳定。

### 失败项
1. `B1` 的 `SR=0.0587`、`SPL=0.0585`，且 `bt_sum=0`，说明其行为退化为高频扫描但无法有效修正路径。
2. `Ours-R` 的 `SR=0.0185`、`SPL=0.0176`，并伴随 `avg_trigger_rate=0.9631`，已经明显处于失控状态。
3. `B1/Ours-R` 的 `TL` 极低，说明它们大部分动作消耗在局部转向/扫描，未形成有效位移推进。

### 证据对应
- TEN-R 日志：`reports/round_009/logs/01_e3_full_ten_r_v6_1839.log`
- B1 日志：`reports/round_009/logs/02_e3_full_b1_1839.log`
- Ours-R 日志：`reports/round_009/logs/03_e3_full_ours_r_1839.log`
- TEN-R raw：`reports/round_009/raw/e3_full_ten_r_v6_1839/TEN-R/`
- B1 raw：`reports/round_009/raw/e3_full_b1_1839/B1/`
- Ours-R raw：`reports/round_009/raw/e3_full_ours_r_1839/Ours-R/`
- 统一任务指标：`reports/round_009/summary/task_metrics_round009.json`
- 结构化过程汇总：`reports/round_009/summary/e3_full_metrics.json`

## 4. 结论
- 这轮 E3 全量对比最终验证了：
  1. `TEN-R v6` 是当前唯一同时满足任务性能、过程稳定和成本约束的方案；
  2. `B1` 的主要问题是“高成本扫描 + 低任务完成率”；
  3. `Ours-R` 的主要问题是“触发失控 + 任务性能进一步退化”。
- 因此，后续阶段固定采用 `TEN-R v6` 作为主线方法；`B1` 与 `Ours-R` 仅保留为对照与失败案例。

## 5. 下一步
1. 在统一 evaluator 已就绪的前提下，进入 `E4` 噪声鲁棒性实验。
2. 首轮先执行 `TEN-R` 主线噪声探针，验证新噪声 profile 和任务级指标链路。
3. 待 TEN-R 主线噪声结果稳定后，再扩展 `B1/Ours-R` 对照。
