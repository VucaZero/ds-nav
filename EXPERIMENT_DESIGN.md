# ds-nav 实验设计文档（唯一命名源）

最后更新：2026-03-10
版本：`v2.0-active`  
适用范围：`/home/data/czh/ds-nav`

## 0. 文档定位与版本状态
- 本文件是实验执行的唯一术语源（Single Source of Truth）。
- v1 已冻结归档：`docs/archive/2026-03-05_v1/EXPERIMENT_DESIGN.md`。
- v2 草案快照：`docs/proposals/v2_draft/EXPERIMENT_DESIGN_v2.md`。
- 任何参数、阶段、指标口径变化，必须先改本文件，再执行实验。

---

## 1. 方法模式与统一命名

### 1.1 方法模式
- `B0`：纯 CMA，不做消歧覆盖。
- `B1`：基于策略熵的不确定性门控。
- `Ours-R`：规则门控（v1 阈值规则）。
- `Ours-L`：学习门控（v1 预留接口）。
- `TEN-R`：TEN + 趋势规则门控（v2 主线，不训练）。
- `TEN-L`：TEN + 可学习 gating head（v2 扩展）。

### 1.2 关键变量声明（统一字段）
| 变量名 | 含义 | 类型 | 默认值 | 适用 |
|---|---|---|---|---|
| `method` | 推理方法 | str | `TEN-R` | 全阶段 |
| `uncertainty_threshold` | 不确定性阈值 | float | `0.50` | B1/Ours-R/Ours-L |
| `conflict_threshold` | 冲突阈值 | float | `0.30` | Ours-R/TEN-R/TEN-L |
| `ten_window` | TEN 滑窗长度 | int | `20` | TEN-R/TEN-L |
| `theta_hysteresis` | Θ 滞回系数 | float | `0.20` | TEN-R/TEN-L |
| `k_hysteresis` | K 滞回系数 | float | `0.20` | TEN-R/TEN-L |
| `scan_budget` | 单集扫描预算上限 | float | `0.45` | TEN-R/TEN-L |
| `cooldown_steps` | 连续触发冷却步数 | int | `10` | TEN-R/TEN-L |
| `num_environments` | 并行环境数（吞吐配置） | int | `1` | 全阶段 |
| `batch_size` | 批大小（吞吐配置） | int | `5` | 全阶段 |
| `noise_profile` | E4 噪声 profile | str | `none` | E4 |
| `noise_intensity` | E4 噪声强度 | float | `0.0` | E4 |
| `noise_seed` | E4 噪声随机种子 | int | `1234` | E4 |
| `p_scan` | 扫视强度 | float | `-` | TEN 输出 |
| `p_rewind` | 回退倾向 | float | `-` | TEN 输出 |
| `theta_slope` | 不确定性趋势斜率 | float | `0.0` | TEN step 特征 |
| `k_slope` | 冲突趋势斜率 | float | `0.0` | TEN step 特征 |
| `temporal_uncertainty` | 时序融合后的不确定性 | float | `-` | TEN step 特征 |
| `temporal_conflict` | 时序融合后的冲突度 | float | `-` | TEN step 特征 |
| `stagnation_steps` | 连续停滞步数 | int | `0` | TEN 回退触发特征 |
| `scan_steps` | LOOK_AROUND 实际步数 | int | `8` | TEN/Ours-R |
| `backtrack_target_node` | 回退目标拓扑节点 | int/str | `-1` | TEN-R/TEN-L |
| `action_raw` | CMA 原始动作 | int | `-` | 全阶段 |
| `action_final` | 门控后动作 | int | `-` | 全阶段 |
| `action_type` | 高层决策类型 | str | `FOLLOW` | 全阶段 |
| `trigger_rate` | 触发率 | float | `-` | 全阶段 |

### 1.3 指标口径
过程指标：
- `action_count`：episode 总动作步数。
- `disambig_count`：触发步数（`trigger_type != None`）。
- `trigger_rate = disambig_count / action_count`。
- `la_count`：`LOOK_AROUND` 次数。
- `bt_count`：`BACKTRACK` 次数。
- `triggered_episodes`：`trigger_rate > 0` 的 episode 数。

任务指标：
- `SR`、`SPL`、`NE`、`TL`。

v2 安全约束：
1. `max_trigger_rate <= scan_budget`。
2. `avg_trigger_rate in [0.05, 0.45]`（E2/E3 过程门控健康区间）。
3. `bt_sum > 0` 且 `conflict_k` 非全 0（TEN 主线门禁）。
4. `bt_ratio <= 0.08`（防止回退过度导致轨迹爆炸）。
5. `action_count_sum` 不得较主线冻结候选上升超过 `+30%`（Round008 复盘后新增的成本门禁）。

---

## 2. 阶段定义（E0-E9）

| 实验ID | 目标 | 数据 | 方法 | 关键变量 | 通过标准 |
|---|---|---|---|---|---|
| E0 | 官方链路冒烟 | `val_unseen` 5ep | B0 | 无 | 产出 predictions/logs |
| E1 | 基线对齐 | `val_unseen` 全量 | B0 | 无 | 可复现 1839ep |
| E2 | v1 门控最小可用 | `val_unseen` 50ep | Ours-R | `u_th/c_th` | 触发可恢复 |
| E3 | v2 主对比 | `val_unseen` 全量 | B0/B1/Ours-R/TEN-R/TEN-L | `method` | TEN 不弱于 B1 且日志完整 |
| E4 | 噪声鲁棒性 | 噪声集 | B0/B1/Ours-R/TEN-R | `profile/intensity` | TEN 退化斜率更小 |
| E5 | TEN 消融A | 同 E3/E4 | TEN-R w/o temporal | `ten_window=1` | 稳定性显著下降 |
| E6 | TEN 消融B | 同 E3/E4 | TEN-R w/o topo | `has_topo=false` | 回退质量下降 |
| E7 | TEN 消融C | 同 E3/E4 | TEN-R w/o budget | `scan_budget=inf` | safety 指标恶化 |
| E8 | 骨干正交性 | 子集/全量 | CMA vs DUET/HAMT/ETPNav + TEN | `backbone` | TEN 在强骨干仍增益 |
| E9 | 校准可靠性 | 同 E3/E4 | TEN-R/TEN-L | `calib` | ECE/Brier 改善 |

---

## 3. v2 实施门禁（E2→E3）

进入 E3 前必须全部满足：
1. `bt_sum > 0`（BACKTRACK 至少在少量 episode 生效）。
2. `conflict_k` 存在非零分布（非全 0）。
3. `max_trigger_rate <= scan_budget`（默认 0.45）。
4. `summary/` 中含结构化 json 和带 `Analysis` 的 md。

---

## 4. Round 008 - v2 具体执行计划（本轮固定）

### 4.1 Plan A：TEN-R 可运行性与日志门禁（50ep）
目标：先证明 TEN 指标可观测，而不是先追最高任务指标。

运行矩阵：
| run_id | method | 关键参数 | 目标 |
|---|---|---|---|
| `e3_ten_r_w20_budget045_cd10` | TEN-R | `ten_window=20, scan_budget=0.45, cooldown=10` | 主线候选 |
| `e3_ten_r_w10_budget045_cd10` | TEN-R | `ten_window=10` | 对比时序窗口 |
| `e3_ten_r_w20_budget035_cd10` | TEN-R | `scan_budget=0.35` | 安全收紧 |
| `e3_ten_r_w20_budget045_cd06` | TEN-R | `cooldown=6` | 连续触发敏感性 |

判定：
- `bt_sum > 0`
- `conflict_k_max > 0`
- `max_trigger_rate <= scan_budget`

### 4.2 Plan B：TEN-L 对照（50ep）
目标：验证可学习门控是否优于趋势规则。

运行矩阵：
| run_id | method | 关键参数 | 目标 |
|---|---|---|---|
| `e3_ten_l_head_w20_budget045_cd10` | TEN-L | `ten_window=20, scan_budget=0.45` | TEN-L 主线 |
| `e3_ten_l_head_w20_budget035_cd10` | TEN-L | `scan_budget=0.35` | 安全约束对照 |

判定：
- 与 `TEN-R` 比较 `SR/SPL/trigger_rate/max_trigger_rate`。
- 若 TEN-L 不稳定，E3 主线先冻结 TEN-R。

### 4.3 Plan C：E3 全量评估（1839ep）
候选：从 Plan A/B 选出 1-2 组主线参数做全量对比。

对比组：
- `B0`
- `B1`
- `Ours-R`
- `TEN-R`（必选）
- `TEN-L`（可选，取决于 Plan B）

### 4.4 Plan D：TEN 时序校准（新增）
目标：解决“单步不敏感”与“时序过激”两端问题，稳定触发结构。

运行矩阵（快速验收）：
| run_id | 说明 | 预期 |
|---|---|---|
| `e3_ten_r_w20_budget045_cd10_temporal_fix_probe10` | 时序增强初版探针（10ep） | 验证 `conflict_k`、`bt_sum` 是否可被激活 |
| `e3_ten_r_w20_budget045_cd10_temporal_fix_probe10_v2` | 冲突饱和校准（10ep） | 降低 conflict 饱和，避免全 BACKTRACK |
| `e3_ten_r_w20_budget045_cd10_temporal_fix_probe3_v5` | 冷却与回退预算收敛验收（3ep） | 触发率回到可控区间 |

判定：
- `conflict_k_nonzero_count > 0`
- `bt_sum > 0`
- `avg_trigger_rate in [0.05, 0.45]`
- `bt_ratio <= 0.08`

### 4.5 Round008 执行结果（2026-03-05）
结论冻结：
- TEN-R 当前冻结候选：`e3_ten_r_w20_budget045_cd10_temporal_fix_50ep_v6`。
- Plan A 结果：`w10` 与 `budget0.35` 两组与冻结候选几乎一致；`cd6` 组触发密度与动作成本显著上升，不作为主线。
- Plan B 结果：TEN-L 两组均出现“低触发 + 高成本”组合，暂不进入后续扩展矩阵。

进入 E4-E9 的主线方法：
- `TEN-R`（必选，固定采用 v6 配置）
- `TEN-L`（可选，需先完成时序稀疏化改造后再重启）

### 4.6 Round009 执行补充（吞吐配置）
- 为缩短全量运行时长，Round009 的 E3 全量对比（TEN-R/B1/Ours-R）统一使用：
  - `NUM_ENVIRONMENTS=4`
- 为保持全量对比执行吞吐一致，Round009 的 E3 全量对比统一额外设置：
  - `IL.batch_size=4`
- 该配置属于执行吞吐参数，不改变方法口径；三组全量 run 必须保持一致。

### 4.7 Round010 执行计划（E4 首轮）
- 目标：先建立 E4 的统一噪声链路与任务级 evaluator 闭环，再扩展完整噪声矩阵。
- 首轮主线仅启动 `TEN-R v6`，采用视觉高斯噪声探针：
  - `run_id=e4_noise_visual_gaussian_p010_ten_r_v6_probe50`
  - `method=TEN-R`
  - `noise_profile=visual_gaussian`
  - `noise_intensity=0.10`
  - `noise_seed=20260310`
  - `max_episodes=50`
  - `NUM_ENVIRONMENTS=4`
  - `IL.batch_size=4`
- 首轮判定：
  - 成功产出 `predictions.json`、`episode_logs.json`、`task_metrics.json`
  - `summary/` 中补齐 json + md
  - 对比 Round009 的 `TEN-R` 基线，确认 `SR/SPL/NE/TL` 与 `trigger_rate` 已出现可解释退化

---

### 4.8 Round011 执行计划（方法优化：backtrack_target_selector v1）
- 决策依据：
  - `Round009` 已证明 `TEN-R v6` 是唯一 clean setting 下可用主线；
  - `Round010` 已证明在视觉高斯噪声下，`TEN-R` 呈现“渐进退化但门控稳定”，而 `B1/Ours-R` 都不是有效主线竞争者；
  - 因此后续重点不再是继续扩弱基线矩阵，而是增强 `TEN-R` 的核心纠错能力。
- 分支研究重点来源：
  - `docs/branch/v2.1/01_method_diagnosis_and_optimization_report.md`
  - `docs/branch/v2.1/02_ten_v2.1_paper_blueprint.md`
  - `docs/branch/v2.2/04_backtrack_target_selector_design.md`
  - `docs/branch/v2.2/05_backtrack_selector_code_integration_map.md`
- 本轮目标：
  - 让 `backtrack_target_node` 不再是常量；
  - 让 `BACKTRACK(target_node)` 成为可解释、可排序、可分析的目标选择过程；
  - 用最小 patch 验证 selector 接入后 `bt_sum > 0` 且日志字段完整。
- 计划矩阵：
  - `r11_selector_v1_demo`
  - `r11_selector_v1_clean_probe10`
  - `r11_selector_v1_clean_probe50`
  - `r11_selector_v1_clean_full1839`
- 首轮通过标准：
  - `backtrack_target_node` 非常量
  - `backtrack_ranked_candidates` 成功落盘
  - `bt_sum > 0`
  - `summary/` 中补齐 json + md

## 5. 统一入口与命令模板

统一入口：`scripts/run_official_vlnce_inference.py`
统一任务级 evaluator：`scripts/evaluate_predictions_offline.py`

TEN-R 模板：
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
```

无头模式：
```bash
xvfb-run -a -s "-screen 0 1280x1024x24" <上面命令>
```

TEN-R E4 模板：
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
  --noise-profile visual_gaussian \
  --noise-intensity 0.10 \
  --noise-seed 20260310 \
  --output-dir /home/data/czh/ds-nav/reports/round_010/raw/e4_noise_visual_gaussian_p010_ten_r_v6_probe50
```

---

## 6. 环境与资产（强制）
- 虚拟环境：`vlnce38`
- Python：`/home/data/anaconda3/envs/vlnce38/bin/python`
- 官方平台：`programs/VLN-CE`
- 方法实现：`vln_ce_baseline/`
- 脚本目录：`scripts/`

最低门禁资产：
- `programs/VLN-CE/data/scene_datasets/mp3d`
- `programs/VLN-CE/data/datasets/R2R_VLNCE_v1-3_preprocessed`
- `programs/VLN-CE/data/checkpoints/CMA_PM_DA_Aug.pth`
- `programs/VLN-CE/data/ddppo-models/gibson-2plus-resnet50.pth`

---

## 7. 报告与命名规范
- 报告目录：`reports/round_xxx/`
- 每轮至少包含：
  - `01_design_report.md`
  - `02_file_structure_report.md`
  - `03_experiment_result_report.md`
  - `summary/`（json + md）
- `raw/` 命名规则：`e<stage>_<method>_<key_params>`。

---

## 8. 变更记录要求
- 新增参数或日志字段必须登记在本文件变量表。
- 任何实验结论必须指向 `raw/` 与 `logs/` 证据路径。
- 未在本文件登记的口径不得进入正式结论。
