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

| run | method | status | episodes | la_sum | bt_sum | disambig_sum | action_count_sum | avg_trigger_rate | min_trigger_rate | max_trigger_rate | bt_ratio | conflict_k_max | conflict_k_nonzero_count | runtime | note |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `e3_full_ten_r_v6_1839` | TEN-R | completed | 1839 | 9165 | 18972 | 28137 | 307681 | 0.0918 | 0.0040 | 0.1200 | 0.0617 | 0.2404 | 306873 | 08:40:00 | 全量完成，门禁通过 |
| `e3_full_b1_1839` | B1 | completed | 1839 | 111959 | 0 | 111959 | 918560 | 0.1218 | 0.0000 | 0.1260 | 0.0000 | 0.0000 | 0 | 10:59:33 | 触发率安全，但无回退且动作成本显著膨胀 |
| `e3_full_ours_r_1839` | Ours-R | completed | 1839 | 885428 | 0 | 885428 | 918164 | 0.9631 | 0.0870 | 1.0000 | 0.0000 | 0.2299 | 820047 | 13:07:46 | 几乎全程触发，严重违反 safety 约束 |

附加成本对比（相对 `TEN-R`）：
- `B1`：
  - `action_count_sum` `+198.5%`
  - `la_sum` `+1121.4%`
  - `runtime` `+26.8%`
- `Ours-R`：
  - `action_count_sum` `+198.4%`
  - `la_sum` `+9558.1%`
  - `runtime` `+51.5%`

门禁判定：
- `TEN-R`：全部通过。
- `B1`：
  - `avg_trigger_rate in [0.05, 0.45]`：通过
  - `max_trigger_rate <= 0.45`：通过
  - `action_count_sum` 不得相对主线无约束膨胀：失败
  - `bt_sum > 0`：不适用，但说明无回退能力
- `Ours-R`：
  - `avg_trigger_rate in [0.05, 0.45]`：失败
  - `max_trigger_rate <= 0.45`：失败
  - `action_count_sum` 不得相对主线无约束膨胀：失败
  - `bt_sum > 0`：失败

## 3. Analysis
### 成功项
1. `TEN-R` 在 1839 全量上保持了与 Round008 一致的触发稳定区间，没有出现触发爆炸或回退失活。
2. `conflict_k` 与 `BACKTRACK` 链路在全量数据上持续激活，说明时序证据机制具备规模稳定性。
3. `B1/Ours-R` 的全量 raw 已全部补齐，Round009 的三组主对比证据终于闭环。

### 失败项
1. `B1` 虽然没有触发率爆炸，但动作总量达到 `918560`，约为 `TEN-R` 的 `2.99x`，效率不可接受。
2. `B1` 的 `bt_sum=0`、`conflict_k_nonzero_count=0`，说明它本质上只提供了大量 `LOOK_AROUND`，没有形成有效回退链路。
3. `Ours-R` 的 `avg_trigger_rate=0.9631`、`max_trigger_rate=1.0`，几乎退化为“步步触发”，已经明显偏离健康区间。
4. `Ours-R` 虽然 `conflict_k_nonzero_count` 很高，但 `bt_sum=0`，说明冲突证据并未转化为有效回退，反而造成了巨大的扫描成本。
5. 当前推理链路未额外生成统一的官方任务指标文件，因此本轮正式结论主要基于过程门控、安全约束与运行成本。

### 证据对应
- TEN-R 日志：`reports/round_009/logs/01_e3_full_ten_r_v6_1839.log`
- B1 日志：`reports/round_009/logs/02_e3_full_b1_1839.log`
- Ours-R 日志：`reports/round_009/logs/03_e3_full_ours_r_1839.log`
- TEN-R raw：`reports/round_009/raw/e3_full_ten_r_v6_1839/TEN-R/`
- B1 raw：`reports/round_009/raw/e3_full_b1_1839/B1/`
- Ours-R raw：`reports/round_009/raw/e3_full_ours_r_1839/Ours-R/`
- 历史失败/中断：`reports/round_009/logs/archive/`、`reports/round_009/raw/archive/`
- 结构化汇总：`reports/round_009/summary/e3_full_metrics.json`

## 4. 结论
- 这轮 E3 全量对比验证了：
  1. `TEN-R v6` 是当前唯一满足“触发可控 + 回退有效 + 成本可接受”的主线方案；
  2. `B1` 的问题主要不是触发率越界，而是“无回退 + 高动作成本”；
  3. `Ours-R` 的问题是触发失控，无法继续作为后续主线候选。
- 因此，Round009 的主结论是：
  - 后续阶段固定采用 `TEN-R v6` 作为主线方法；
  - `B1` 与 `Ours-R` 保留为对照与失败案例，不继续作为主线推进对象。

## 5. 下一步
1. 按实验设计阶段编号，下一步应进入 `E4`：噪声鲁棒性实验。
2. E4 推荐首先执行 `TEN-R`（必选）与 `B1/Ours-R` 的噪声对照，重点关注：
   - 退化斜率
   - `trigger_rate` 是否继续放大
   - `action_count_sum` 是否进一步失控
3. 若希望在 E4 前补齐任务级指标结论，需要先补一个统一的官方 evaluator 导出流程，再做一次结果对齐。
