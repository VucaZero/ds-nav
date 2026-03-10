# Round 010 实验结果报告（E4 第一轮矩阵完成）

## 1. 执行状态
- `plan_version`：`v2.0-active`
- 轮次状态：`completed`
- 已完成 run：
  - `e4_noise_visual_gaussian_p010_ten_r_v6_probe50`
  - `e4_noise_visual_gaussian_p020_ten_r_v6_probe50`
  - `e4_noise_visual_gaussian_p030_ten_r_v6_probe50`
  - `e4_noise_visual_gaussian_p010_b1_probe50`
  - `e4_noise_visual_gaussian_p010_ours_r_probe50`

## 2. 结果汇总
### 2.1 `TEN-R` 主线强度探针
- `p010`: `SR=0.3585`, `SPL=0.2888`, `NE=6.1752`, `TL=11.5263`
- `p020`: `SR=0.3208`, `SPL=0.2722`, `NE=5.7160`, `TL=11.2224`
- `p030`: `SR=0.2264`, `SPL=0.1745`, `NE=6.7390`, `TL=13.1291`
- 结论：噪声强度提升后，`TEN-R` 任务级性能逐步退化，但过程门控保持稳定。

### 2.2 `B1 p010` 对照
- 任务级：`SR=0.0192`, `SPL=0.0192`, `NE=8.6636`, `TL=1.8927`
- 过程级：`avg_trigger_rate=0.1223`, `bt_sum=0`, `action_count_sum=26000`
- 相对 clean subset：`delta_SR=+0.0000`, `delta_SPL=+0.0000`, `delta_NE=-0.3104`, `delta_TL=+0.2177`

### 2.3 `Ours-R p010` 对照
- 任务级：`SR=0.0577`, `SPL=0.0536`, `NE=9.7951`, `TL=1.0639`
- 过程级：`avg_trigger_rate=0.9647`, `bt_sum=0`, `action_count_sum=26000`
- 相对 clean subset：`delta_SR=-0.0192`, `delta_SPL=-0.0174`, `delta_NE=+0.1681`, `delta_TL=-0.0337`

## 3. Analysis
### 成功项
1. `E4` 第一轮矩阵已经闭环：`TEN-R` 三个强度点 + `B1 p010` + `Ours-R p010` 全部完成。
2. `TEN-R` 在 `p010/p020/p030` 上形成清晰的渐进退化曲线，同时过程门控保持稳定，说明它是“鲁棒但会逐步退化”的主线方案。
3. `B1` 和 `Ours-R` 两个对照都没有显示出优于 `TEN-R` 的噪声鲁棒性证据，反而进一步证明它们在当前设置下都不是可用主线。

### 失败项
1. `B1 p010` 的任务级表现极差，且与 clean subset 几乎没有差异，说明其本身已接近失效基线。
2. `Ours-R p010` 的 `avg_trigger_rate=0.9647`、`max_trigger_rate=1.0`，说明其在轻度噪声下依旧维持极端触发行为。
3. `Ours-R p010` 的任务级表现同样很弱：`SR=0.0577`、`SPL=0.0536`，并且噪声下继续轻度退化。
4. 当前矩阵样本量仍以 `~50 episode` 为主，适合阶段性结论，不足以替代大样本正式鲁棒性结论。

### 证据对应
- `TEN-R p010`：`reports/round_010/logs/01_e4_noise_visual_gaussian_p010_ten_r_v6_probe50.log`
- `TEN-R p020`：`reports/round_010/logs/02_e4_noise_visual_gaussian_p020_ten_r_v6_probe50.log`
- `TEN-R p030`：`reports/round_010/logs/03_e4_noise_visual_gaussian_p030_ten_r_v6_probe50.log`
- `B1 p010`：`reports/round_010/logs/04_e4_noise_visual_gaussian_p010_b1_probe50.log`
- `Ours-R p010`：`reports/round_010/logs/05_e4_noise_visual_gaussian_p010_ours_r_probe50.log`
- 汇总：`reports/round_010/summary/task_metrics_round010.json`

## 4. 结论
- `TEN-R`：当前唯一具备“主线可用性 + 渐进退化曲线”的方案；
- `B1`：在 clean 与 noise 下都接近失效基线，缺乏作为有效鲁棒性对照的价值；
- `Ours-R`：在轻度噪声下依旧维持高触发、低任务性能，说明它不仅在 clean setting 下失稳，在噪声 setting 下同样没有竞争力；
- 因此，`E4` 第一轮矩阵已经足以支持阶段性结论：`TEN-R` 的退化斜率明显优于 `B1/Ours-R`，后者不宜再作为主线候选推进。

## 5. 下一步
1. 若追求更稳的 E4 结论，可扩大 `TEN-R` 的样本量或切换其他噪声 profile（如指令扰动、观测延迟）。
2. 若追求实验效率，当前可以冻结 `E4` 第一轮结论，并开始准备下一阶段。
