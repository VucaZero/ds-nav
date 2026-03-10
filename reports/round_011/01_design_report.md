# Round 011 设计报告（backtrack_target_selector v1 方法优化）

## 1. 本轮目标
1. 将 `backtrack_target_node` 从常量占位升级为可解释、非常量的规则选择器。
2. 完成 `selector v1` 的主线接线规划与最小验证计划。
3. 为后续 `TEN-R` clean 回归与噪声回测建立方法优化入口。

## 2. 执行矩阵（计划）
- `r11_selector_v1_demo`
  - 目标：验证 selector 对手写候选输入输出稳定且非常量
- `r11_selector_v1_clean_probe10`
  - 目标：接入主线后验证 `backtrack_target_node` 不再恒定
- `r11_selector_v1_clean_probe50`
  - 目标：验证 selector 接入后 `bt_sum > 0` 且日志完整
- `r11_selector_v1_clean_full1839`
  - 目标：与当前 `TEN-R v6` 做 clean 全量回归比较

## 3. 通过标准
- `backtrack_target_node` 非常量
- `backtrack_ranked_candidates` 成功落盘
- `bt_sum > 0`
- `conflict_k_nonzero_count > 0`
- `summary/` 中包含 json + md
