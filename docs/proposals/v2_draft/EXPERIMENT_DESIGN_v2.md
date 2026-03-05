# ds-nav 实验设计文档（TEN v2 扩展版 / Single Source of Truth）

最后更新：2026-03-05（v2 草案）
适用范围：`/home/data/czh/ds-nav`

## 0. 文档定位与强制规则（继承 v1）
- 本文件仍是后续实验与报告的**唯一术语源**
- 任何参数/阶段/命名变化必须先改本文件再跑实验
- 报告方法名/变量名必须与本文件一致

---

## 1. 方法模式与含义（v2 增补）

### 1.1 v1 保留
- `B0`：纯 CMA
- `B1`：基于策略熵的不确定性门控
- `Ours-R`：规则门控（阈值规则 + DS/熵融合）
- `Ours-L`：学习门控（接口保留）

### 1.2 v2 新增（TEN）
- `TEN-R`：TEN + 规则门控（趋势/滞回/budget/cooldown），不训练
- `TEN-L`：TEN + 可学习 gating head（在 TEN features 上学习 p_scan/p_rewind/budget）
- `TEN-R+Topo`：TEN 绑定 topo 载体（轻量 topo 或 DUET/ETPNav topo）
- `TEN-R+Hist`：TEN 绑定 history 载体（HAMT-style history 或滑窗）

---

## 2. 关键变量声明（v2 增补，保持 v1 表格风格）

| 变量名 | 含义 | 类型 | 默认 | 备注 |
|---|---|---|---|---|
| `method` | 推理方法 | str | `B0/B1/Ours-R/Ours-L/TEN-R/TEN-L` | v2 增补 |
| `uncertainty_threshold` | 不确定性阈值 | float | 0.5 | v1 保留（TEN-R 可不用） |
| `conflict_threshold` | 冲突阈值 | float | 0.3 | v1 保留 |
| `ten_window` | TEN 滑窗长度 | int | 20 | v2 |
| `theta_hysteresis` | Θ 滞回系数 | float | 0.2 | v2 |
| `k_hysteresis` | K 滞回系数 | float | 0.2 | v2 |
| `scan_budget` | episode 扫视预算上限 | float | 0.45 | 对齐 E2 safety 约束 |
| `cooldown_steps` | 连续触发冷却步数 | int | 10 | v2 |
| `p_scan` | 连续扫视强度 | float | — | TEN 输出 |
| `p_rewind` | 连续回退倾向 | float | — | TEN 输出 |
| `scan_steps` | LOOK_AROUND 实际步数 | int | 8 | 可由 p_scan 映射 |
| `backtrack_target_node` | 回退目标 topo node | int/str | -1 | v2 必须可记录 |
| `trigger_rate` | 触发率 | float | — | v1 保留（TEN 同口径） |

---

## 3. 实验阶段定义（v2 扩展 E3-E9）

> v1 阶段 E0-E7 保留。
> v2 在不破坏 v1 的基础上新增更“顶刊口径”的结构化对比与消融。

### 3.1 阶段总览（新增）
| 实验ID | 目标 | 数据 | 方法 | 关键变量 | 通过标准 |
|---|---|---|---|---|---|
| E3 | 主对比（全量） | `val_unseen` 全量 | `B0/B1/Ours-R/TEN-R/TEN-L` | method | TEN 不弱于 B1 且可解释日志完整 |
| E4 | 噪声鲁棒性（先验失配） | 噪声集 | `B0/B1/Ours-R/TEN-R` | profile/intensity | TEN 退化斜率更小 |
| E5 | TEN 消融：无时序 | 同 E3/E4 | `TEN-R w/o temporal` | ten_window=1 | 指标/稳定性显著变差 |
| E6 | TEN 消融：无 topo 绑定 | 同 E3/E4 | `TEN-R w/o topo` | has_topo=false | 回退与纠错质量下降 |
| E7 | TEN 消融：无 budget/cooldown | 同 E3/E4 | `TEN-R w/o budget` | scan_budget=inf | safety/耗时爆炸 |
| E8 | Backbone 正交性 | `val_unseen` 子集/全量 | `CMA vs (DUET/HAMT/ETPNav)+TEN` | backbone | TEN 在强骨干上仍增益 |
| E9 | 校准与可靠性 | 同 E3/E4 | `TEN-R/TEN-L` | calib | uncertainty 的 ECE/Brier 改善 |

---

## 4. E2→E3 迁移规则（防止重复踩坑）
- v1 E2 已证明阈值两极分化问题，且 conflict/BT 不工作；
- v2 进入 E3 前，必须满足：
  1) `bt_sum > 0`（BACKTRACK 至少在少量 ep 中触发执行）
  2) `conflict_k` 在日志中存在非零分布（非全 0）
  3) safety 约束有效：`max_trigger_rate <= scan_budget`

---

## 5. 统一启动入口（保持 v1 CLI 习惯）
统一入口：`scripts/run_official_vlnce_inference.py`

命令模板（v2 示意）：
```bash
/home/data/anaconda3/envs/vlnce38/bin/python \
  /home/data/czh/ds-nav/scripts/run_official_vlnce_inference.py \
  --exp-config vlnce_baselines/config/r2r_baselines/test_set_inference.yaml \
  --method TEN-R \
  --split val_unseen \
  --max-episodes 50 \
  --ten-window 20 \
  --scan-budget 0.45 \
  --cooldown-steps 10 \
  --output-dir /home/data/czh/ds-nav/reports/round_008/raw/e3_ten_r_w20_budget045_cd10