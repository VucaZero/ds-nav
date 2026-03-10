# Round 010 设计报告（E4 首轮启动）

## 1. 本轮目标
1. 启动 E4 噪声鲁棒性首轮实验。
2. 先验证 `TEN-R v6` 在轻度视觉高斯噪声下的任务级与过程级退化行为。
3. 验证统一 task evaluator 是否可直接复用于 E4。

## 2. 执行矩阵（首轮）
- `e4_noise_visual_gaussian_p010_ten_r_v6_probe50`
  - method: `TEN-R`
  - noise_profile: `visual_gaussian`
  - noise_intensity: `0.10`
  - noise_seed: `20260310`
  - episodes: `50`
  - `NUM_ENVIRONMENTS=4`
  - `IL.batch_size=4`
  - status: `completed`
- `e4_noise_visual_gaussian_p020_ten_r_v6_probe50`
  - method: `TEN-R`
  - noise_profile: `visual_gaussian`
  - noise_intensity: `0.20`
  - noise_seed: `20260310`
  - episodes: `50`
  - `NUM_ENVIRONMENTS=4`
  - `IL.batch_size=4`
  - status: `running`

## 3. 通过标准
- 成功产出 `predictions.json`、`episode_logs.json`、`task_metrics.json`
- `summary/` 中生成 `json + md`
- 相对 Round009 `TEN-R` 基线出现可解释退化，而非直接失稳

- `e4_noise_visual_gaussian_p030_ten_r_v6_probe50`
  - method: `TEN-R`
  - noise_profile: `visual_gaussian`
  - noise_intensity: `0.30`
  - noise_seed: `20260310`
  - episodes: `50`
  - `NUM_ENVIRONMENTS=4`
  - `IL.batch_size=4`
  - status: `running`

- `e4_noise_visual_gaussian_p010_b1_probe50`
  - method: `B1`
  - noise_profile: `visual_gaussian`
  - noise_intensity: `0.10`
  - noise_seed: `20260310`
  - episodes: `50`
  - `NUM_ENVIRONMENTS=4`
  - `IL.batch_size=4`
  - status: `running`

- `e4_noise_visual_gaussian_p010_ours_r_probe50`
  - method: `Ours-R`
  - noise_profile: `visual_gaussian`
  - noise_intensity: `0.10`
  - noise_seed: `20260310`
  - episodes: `50`
  - `NUM_ENVIRONMENTS=4`
  - `IL.batch_size=4`
  - status: `running`
