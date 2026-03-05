按照实验规划直接开始实验，每一轮在当前目录的 `/reports` 下生成：
- 设计报告
- 文件结构报告
- 实验结果报告（包括数据和归因）

## 实验执行规范（强制）

1. 每一次实验前，必须先查看：
   - `EXPERIMENT_DESIGN.md`（实验设计唯一参考源）
2. 如果实验计划、参数、评估口径有任何更新，必须先更新：
   - `EXPERIMENT_DESIGN.md`
3. 下一轮实验开始前，除查看上一轮 `reports/round_xxx` 报告外，也必须核对 `EXPERIMENT_DESIGN.md` 最新版本。
4. 遇到 sandbox 权限、命令允许、常规改动尝试等问题（非重要配置文件变更），默认可直接执行，不用中断询问。
5. 每次实验必须使用同一个虚拟环境：`vlnce38`。

## 文档治理规范（强制）

1. 当前主线维护四类同级文档：
   - `EXPERIMENT_DESIGN.md`
   - `PROJECT_STRUCTURE.md`
   - `METHOD_STRUCTURE.md`（当前内容不改）
   - `EXPERIMENT_PROCESS_LOG.md`（每轮实验过程记录）
2. 每轮实验结束后，必须更新 `EXPERIMENT_PROCESS_LOG.md`，至少包含：
   - 实验证据路径（`raw`/`logs`/`summary`）
   - 结果汇总
   - Bad Case 分析
   - 潜在可行优化方向分析
3. 方法变量名、实验阶段名、结果字段名，统一以 `EXPERIMENT_DESIGN.md` 为准。
4. `PROJECT_STRUCTURE_SPEC.md` 与 `EXPERIMENT_FILE_LAYOUT.md` 仅作为 deprecated 跳转，不再维护内容。

## 报告规范（强制）

1. `reports/round_xxx/summary/` 必须包含结构化汇总（json）和可读总结（md）。
2. 可读总结必须包含 `Analysis` 章节，明确写出：
   - 成功项
   - 失败项
   - 与 `raw/` 与 `logs/` 的证据对应
3. 对中断/失败实验也要留痕，写明中断原因与状态（completed/interrupted/failed）。

## 目录治理规范（强制）

1. `ds-nav` 仅保留当前主线实验相关内容。
2. 历史或无关目录放到上级 `/home/data/czh` 管理（例如：`history`、`LTE_Nav`）。
