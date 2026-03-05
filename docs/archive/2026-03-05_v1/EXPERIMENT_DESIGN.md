# ds-nav 实验设计文档（唯一命名源）

最后更新：2026-03-05  
适用范围：`/home/data/czh/ds-nav`

## 0. 文档定位与强制规则
- 本文件是后续所有实验与报告的**唯一术语源（Single Source of Truth）**。
- 每次实验前必须先阅读本文件，再执行脚本。
- 任何参数口径、实验阶段、变量命名变化，必须先改本文件，再跑实验。
- 报告中的方法名、实验名、变量名必须与本文件完全一致。

---

## 1. 方法技术规范（当前实现口径）

### 1.1 方法目标
在官方 VLN-CE 推理链路中验证以下主线：
1. 指令地标抽取（文本侧）
2. 图像-地标证据计算（视觉侧）
3. DS 不确定性估计（`uncertainty/conflict/ignorance`）
4. 高层门控（FOLLOW / LOOK_AROUND / BACKTRACK）
5. 动作覆盖与可解释日志输出

### 1.2 方法模式与含义
- `B0`：纯 CMA，不做消歧覆盖。
- `B1`：基于策略熵的不确定性门控。
- `Ours-R`：规则门控（阈值规则 + DS/熵融合不确定性）。
- `Ours-L`：学习门控（保留接口，当前阶段主跑 Ours-R）。

### 1.3 关键变量声明（统一命名）
| 变量名 | 含义 | 类型 | 当前默认 |
|---|---|---|---|
| `method` | 推理方法 | str | `B0/B1/Ours-R/Ours-L` |
| `uncertainty_threshold` | 不确定性触发阈值 | float | `0.5`（扫描） |
| `conflict_threshold` | 冲突触发阈值 | float | `0.3` |
| `uncertainty` | 当前步不确定性 | float | 由 DS+熵校准给出 |
| `conflict` | 当前步冲突度 | float | DS 输出 |
| `ignorance` | 当前步无知度 | float | DS 输出 |
| `action_raw` | CMA 原始动作 | int | 动作空间 ID |
| `action_final` | 门控后最终动作 | int | 动作空间 ID |
| `action_type` | 高层决策类型 | str | `FOLLOW/LOOK_AROUND/BACKTRACK` |
| `trigger_rate` | episode 内触发率 | float | `disambig_count/action_count` |

### 1.4 关键实验参数说明（执行口径）
| 参数 | 说明 | 作用范围 | 推荐取值/约束 |
|---|---|---|---|
| `uncertainty_threshold` | 不确定性触发阈值（常记作 `u_th`） | Ours-R/Ours-L/B1 | E2 扫描；用于控制触发强度 |
| `conflict_threshold` | 冲突触发阈值（常记作 `c_th`） | Ours-R/Ours-L | 当前默认 `0.30` |
| `u` (`uncertainty`) | 当前步不确定性 | step 级 | 当前实现：`u = max(ds_uncertainty, entropy_norm)` |
| `conflict` | 当前步冲突度（可对应 DS 中 `K`） | step 级 | 由 DS 输出，理论范围 `[0,1]` |
| `ignorance` | 当前步无知度 | step 级 | 由 DS 输出，理论范围 `[0,1]` |
| `max_episodes` | 单次实验 episode 上限 | run 级 | E2 常用 `50` |
| `split` | 数据划分 | run 级 | 当前主用 `val_unseen` |
| `method` | 方法类型 | run 级 | `B0/B1/Ours-R/Ours-L` |

参数关系说明：
1. `u > u_th` 时可触发 `LOOK_AROUND`（规则门控下）。
2. `u > u_th` 且 `conflict > c_th` 时才可触发 `BACKTRACK`。
3. `trigger_rate` 与 `u_th` 单调相关（阈值越低通常触发越多）。

### 1.5 Metric 说明（统一统计口径）
过程指标（门控行为）：
| 指标 | 定义 | 说明 |
|---|---|---|
| `action_count` | episode 总动作步数 | 分母口径 |
| `disambig_count` | 触发步数（`trigger_type != None`） | 仅统计触发步，不含非触发 |
| `trigger_rate` | `disambig_count / action_count` | E2 主指标 |
| `la_count` | `LOOK_AROUND` 触发次数 | 过程解释指标 |
| `bt_count` | `BACKTRACK` 触发次数 | 冲突分支健康度指标 |
| `triggered_episodes` | `trigger_rate > 0` 的 episode 数 | 覆盖范围指标 |

任务指标（VLN 常规）：
| 指标 | 含义 | 备注 |
|---|---|---|
| `SR` | Success Rate | 任务完成率 |
| `SPL` | Success weighted by Path Length | 效率与成功综合 |
| `NE` | Navigation Error | 终点误差 |
| `TL` | Trajectory Length | 路径长度 |

E2 判定口径：
1. 主标准：`avg_trigger_rate in [0.05, 0.45]`  
2. 安全建议：`max_trigger_rate <= 0.45`

### 1.6 关键函数与代码位置（当前落地点）
| 功能 | 文件 | 关键函数/类 |
|---|---|---|
| 推理入口（CLI） | `scripts/run_official_vlnce_inference.py` | `main()` |
| 官方推理主循环 | `scripts/run_official_vlnce.py` | `run_official_inference()` |
| 每步门控逻辑 | `vln_ce_baseline/vlnce_integration/inference_hook.py` | `InferenceHook.process_step()` |
| 门控策略规则 | `vln_ce_baseline/disambig_controller.py` | `DisambigController.rule_based_decision()` |
| DS 不确定性 | `vln_ce_baseline/ds_belief_filter.py` | `DSBeliefFilter.forward()` |
| 动作原语与日志 | `vln_ce_baseline/vlnce_integration/action_primitives.py` | `ActionPrimitive`, `ActionSequenceExecutor` |

### 1.7 当前实现注记（必须在报告中显式声明）
- 为修复 Ours-R 触发率过低，当前实现采用：
  - `uncertainty = max(ds_uncertainty, entropy_norm)`（熵下限校准）
  - Ours-R 在 E2 阶段使用“单步纠偏”（不展开长队列）
  - LOOK_AROUND 动作序列为轻量版本（8-step）
- 上述属于**E2 修复策略**，进入 E3 前必须再次确认是否冻结。

---

## 2. 实验阶段定义（E0-E7）

### 2.1 阶段总览
| 实验ID | 目标 | 数据 | 方法 | 关键变量 | 通过标准 |
|---|---|---|---|---|---|
| E0 | 官方链路冒烟 | `val_unseen`，5 ep | B0 | 无 | 成功产出 predictions/logs |
| E1 | 基线对齐 | `val_unseen` 全量 | B0 | 无 | 全量 1839 ep 可复现 |
| E2 | 门控最小可用 | `val_unseen` 50 ep | Ours-R | `uncertainty_threshold/conflict_threshold` | `avg_trigger_rate` 在 `[0.05,0.45]` |
| E3 | 主对比 | `val_unseen` 全量 | B0/B1/Ours-R/Ours-L | method | Ours-R 鲁棒性不弱于 B1 |
| E4 | 噪声鲁棒性 | 噪声集 | B0/B1/Ours-R | profile/intensity | Ours-R 退化斜率更小 |
| E5 | 消融A | 同 E3/E4 | Ours-R w/o Conflict | has_conflict | 对比退化显著 |
| E6 | 消融B | 同 E4 | Ours-R w/o Re-localize | has_reloc | 失败率上升 |
| E7 | 参数敏感性 | 中强噪声 | Ours-R | tau 网格 | 存在稳定区间 |

### 2.2 各阶段统一启动入口
统一入口脚本：`scripts/run_official_vlnce_inference.py`

标准命令模板：
```bash
/home/data/anaconda3/envs/vlnce38/bin/python \
  /home/data/czh/ds-nav/scripts/run_official_vlnce_inference.py \
  --exp-config vlnce_baselines/config/r2r_baselines/test_set_inference.yaml \
  --method Ours-R \
  --split val_unseen \
  --max-episodes 50 \
  --uncertainty-threshold 0.68 \
  --conflict-threshold 0.30 \
  --output-dir /home/data/czh/ds-nav/reports/round_007/raw/e2_xxx
```

无头服务器推荐：
```bash
xvfb-run -a -s "-screen 0 1280x1024x24" <上面命令>
```

---

## 3. 实验环境与资产规范

### 3.1 虚拟环境（强制）
- 环境名：`vlnce38`
- Python：`/home/data/anaconda3/envs/vlnce38/bin/python`
- 后续实验默认继续使用 `vlnce38`，不切换新环境。

### 3.2 平台与核心代码
- 官方平台：`programs/VLN-CE`
- Habitat：`programs/habitat-lab`
- 方法实现：`vln_ce_baseline/`
- 实验脚本：`scripts/`

### 3.3 Habitat 风格 task/agent/action（简要）
1. Task：
   - 当前主任务是 VLN-CE 导航任务（以指令驱动导航）。
   - 评估主要在 `val_unseen` 划分进行。
2. Agent：
   - 基础策略 agent 为官方 CMA policy（B0）。
   - Ours-R/Ours-L 在 CMA 输出后做高层门控覆盖。
3. Action（离散动作空间）：
   - `0=STOP`
   - `1=MoveForward`
   - `2=TurnLeft`
   - `3=TurnRight`
4. 覆盖语义：
   - `action_raw`：CMA 原始动作
   - `action_final`：门控后最终执行动作
   - `trigger_type`：若发生覆盖，记录 `LOOK_AROUND/BACKTRACK`

### 3.4 数据与模型资产（最低门禁）
- 场景：`programs/VLN-CE/data/scene_datasets/mp3d`
- R2R 预处理：`programs/VLN-CE/data/datasets/R2R_VLNCE_v1-3_preprocessed`
- CMA 权重：`programs/VLN-CE/data/checkpoints/CMA_PM_DA_Aug.pth`
- DDPPO 权重：`programs/VLN-CE/data/ddppo-models/gibson-2plus-resnet50.pth`

---

## 4. 报告与命名规范
- 报告目录：`reports/round_xxx/`
- 每轮至少包含：
  - `01_design_report.md`
  - `02_file_structure_report.md`
  - `03_experiment_result_report.md`
  - `summary/`（含结构化 JSON + 可读分析）
- 每轮结束后还必须更新顶层过程文档：
  - `EXPERIMENT_PROCESS_LOG.md`（证据、归因、bad case、优化方向）
- `raw/` 下每个实验目录名必须体现关键变量，例如：
  - `e2_fix_u068_c030_one_step`

---

## 5. 当前阶段结论（截至 2026-03-05）
- E1 已完成并稳定（B0 全量 1839 ep）。
- E2 仍在参数收敛：
  - 过低阈值导致触发过强与长轨迹；
  - 过高阈值导致触发不足；
  - 已形成可复现修复流程（探针 -> 阈值回填 -> 50ep 验证）。
- 进入 E3 前，必须先在 E2 固化最终阈值组并在报告中声明。

---

## 6. 变更记录要求
- 任何新增参数或日志字段，需在本文件补充“变量声明 + 文件位置 + 默认值”。
- 任何实验结论引用，必须附对应 `raw` 目录和日志文件路径。
- 未在本文件登记的口径，不得进入正式结论。
