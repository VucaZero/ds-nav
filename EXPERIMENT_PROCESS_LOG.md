# ds-nav 实验过程记录（第4类文档）

最后更新：2026-03-05
范围：`/home/data/czh/ds-nav`

## 1. 文档定位
- 本文档用于记录**每一轮实验结束后的证据闭环**：
  - 运行事实（跑了什么、成功/失败/中断）
  - 结果汇总（关键指标）
  - 归因分析（成功原因、失败原因、bad case）
  - 可行优化方向（短期可执行与中期设计修正）
- 与三类同级文档关系：
  - `EXPERIMENT_DESIGN.md`：方法命名与实验口径规范
  - `PROJECT_STRUCTURE.md`：静态结构规范
  - `METHOD_STRUCTURE.md`：方法路径描述
  - `EXPERIMENT_PROCESS_LOG.md`（本文）：轮次证据与归因

## 2. 维护规则（强制）
1. 每轮实验结束后必须更新本文档。
2. 记录必须包含证据路径（`reports/round_xxx/raw`、`logs`、`summary`）。
3. 每轮必须有 `Bad Case` 与 `Optimization` 两节。
4. 结论必须明确回答：
   - 当前问题是“框架执行问题”还是“方法设计问题”。

## 3. Round 007 Review（暂停实验后复盘）

### 3.1 轮次目标
- 对 E1/E2 全部结果做证据化复盘。
- 回答：`Ours-R` 效果差是“框架不动优化策略可解”，还是“方法设计本身存在关键缺陷”。

### 3.2 证据清单
- 结果报告：`reports/round_007/03_experiment_result_report.md`
- 汇总 JSON：`reports/round_007/summary/round_status.json`
- 指标明细：`reports/round_007/summary/e2_metrics.json`
- 关键运行日志：
  - `reports/round_007/logs/05_e2_ours_r_50.log`
  - `reports/round_007/logs/12_e2_probe_u110_c030.log`
  - `reports/round_007/logs/13_e2_fix_u068_c030_one_step.log`
  - `reports/round_007/logs/14_e2_fix_u085_c030_one_step.log`
- 原始输出目录：
  - `reports/round_007/raw/e2_ours_r`
  - `reports/round_007/raw/e2_probe_u110_c030`
  - `reports/round_007/raw/e2_fix_u068_c030_one_step`
  - `reports/round_007/raw/e2_fix_u085_c030_one_step`

### 3.3 结果汇总（E2 关键 run）
| run | avg_trigger_rate | max_trigger_rate | 结论 |
|---|---:|---:|---|
| `e2_ours_r` | 0.0000 | 0.0000 | 完全无触发 |
| `e2_fix_u045_c030` | 0.0000 | 0.0000 | DS-only 阈值下仍无触发 |
| `e2_probe_u110_c030` | 0.0000 | 0.0000 | 采样不确定性分布用 |
| `e2_fix_u068_c030_one_step` | 0.2773 | 0.5940 | 主标准通过，安全上限超出 |
| `e2_fix_u085_c030_one_step` | 0.0119 | 0.2240 | 安全通过，主标准不达标 |

### 3.4 框架健康度判断
- 框架侧基本健康（可跑、可复现、可产出）：
  - E1 全量 1839 ep 完成；
  - E2 多组能稳定执行并产生 episode/step 日志；
  - 无头模式与环境口径已统一。
- 因此“完全框架失效”结论不成立。

### 3.5 方法归因（核心）
结论：**主要是方法设计问题，不只是策略阈值问题。**

关键证据：
1. `conflict` 全程接近 0（均值/分位/最大均为 0），`BACKTRACK` 从未触发。  
   说明 Conflict 分支在当前实现下几乎“结构性失活”。
2. Ours-R 触发几乎全部来自 `LOOK_AROUND`，且受 `uncertainty_threshold` 单一控制。  
   当阈值降低时触发过强并拉长轨迹；升高又触发不足。
3. 当前 `uncertainty` 采用 `max(ds_uncertainty, entropy_norm)`。  
   使 Ours-R 在实践上退化为“熵阈值门控主导”，DS 的区分贡献不足。

### 3.6 Bad Case（Round007）
- `e2_fix_u068_c030_one_step` 中高触发样本：
  - episode `165`: `trigger_rate=0.594`, `action_count=500`, `disambig_count=297`
  - episode `1`: `trigger_rate=0.572`, `action_count=500`, `disambig_count=286`
  - episode `147`: `trigger_rate=0.548`, `action_count=500`, `disambig_count=274`
- 现象：
  - 高频触发导致 episode 接近上限步数；
  - 触发率通过主标准，但轨迹质量和效率明显劣化。

### 3.7 优化方向（可执行）

#### A. 框架不动的策略优化（短期）
1. 增加 episode 触发预算（例如上限 0.45）和冷却窗口。
2. 将固定阈值改为分位阈值（在线估计近期不确定性分位）。
3. 对 `LOOK_AROUND` 触发加“连续触发抑制”。

#### B. 方法设计修正（优先级更高）
1. 重构 DS 证据映射：显式支持 `H / ¬H / Θ`，避免冲突项长期为 0。
2. 引入时序历史融合（非单步独立）使 `K` 有真实动态。
3. 恢复并验证 `BACKTRACK` 触发链路（Conflict 分支可观测可触发）。
4. 将 “DS 指标” 与 “策略熵” 由 `max` 改为可解释融合（如加权或门控网络）。

### 3.8 本轮最终判定
- 判定：`Ours-R` 当前瓶颈以**方法设计缺陷**为主，策略调参只能做局部修补。
- 建议：下一轮先做方法设计修正（B），再做阈值收敛与 E3 对比。

## 4. 下一轮记录模板
复制以下模板创建下一轮条目：

```md
## Round XXX Review
### 目标
### 证据清单
### 结果汇总
### Bad Case
### 归因判断（框架 vs 方法）
### 优化方向
### 结论与下一步
```
