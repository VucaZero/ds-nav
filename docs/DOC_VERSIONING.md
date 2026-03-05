# 文档版本治理规范（GitHub + 本地）

最后更新：2026-03-05
适用范围：`/home/data/czh/ds-nav`

## 1. 目标
- 避免根目录出现多份同类文档导致执行口径混乱。
- 明确“激活版 / 草案版 / 归档版”职责。
- 保证 GitHub 与本地仓库的版本切换可追踪、可回滚。

## 2. 四层版本模型
1. 激活版（唯一执行源）
- 位置：仓库根目录
- 文件：
  - `EXPERIMENT_DESIGN.md`
  - `PROJECT_STRUCTURE.md`
  - `METHOD_STRUCTURE.md`
  - `EXPERIMENT_PROCESS_LOG.md`
- 规则：实验执行只认激活版。

2. 草案版（设计讨论源）
- 位置：`docs/proposals/<version>/`
- 规则：可并行多草案，但不能直接作为实验执行口径。

3. 归档版（历史冻结源）
- 位置：`docs/archive/<date>_<version>/`
- 规则：只读，不在主线上继续改写。

4. 分支研究版（方法分析与潜在方向沉淀）
- 位置：`docs/branch/<version>/`
- 规则：
  - 用于沉淀“潜在方法修改、潜在优化方向、论文蓝图、预研分析”。
  - 允许快速迭代与并行记录，不直接作为实验执行口径。
  - 当分支研究成熟后，可抽取稳定内容进入 `docs/proposals/<version>/`，再走“评审 -> 激活”流程。

## 3. GitHub 管理策略
1. `main`：仅保留激活版（根目录四份文档）。
2. 草案开发：使用分支（示例：`proposal/v2.1`）。
3. 升级流程：
- 在 PR 中完成草案评审。
- 合并前先把旧激活版复制到 `docs/archive/`。
- 再将草案内容提升为根目录激活版。
- 合并后打 tag（示例：`docs-v2.0-active`）。

## 4. 本地管理策略
1. 禁止继续在根目录新建 `*_v2.md`、`*_final.md` 等并行文件。
2. 新方案一律放入 `docs/proposals/<version>/`。
3. 方法分析、潜在创新方向、论文草图一律放入 `docs/branch/<version>/`。
4. 版本切换时执行“先归档、后提升、再记录”：
- 归档旧版到 `docs/archive/`。
- 更新根目录激活版。
- 在 `EXPERIMENT_PROCESS_LOG.md` 记录切换证据与原因。

## 5. 当前状态（2026-03-05）
- 当前激活版本：`v2.0-active`
- v1 归档位置：`docs/archive/2026-03-05_v1/`
- v2 草案快照：`docs/proposals/v2_draft/`
- v2.1 分支研究：`docs/branch/v2.1/`

## 6. 升级检查清单
- [ ] `AGENTS.md` 的实验执行规范已同步版本状态
- [ ] `EXPERIMENT_DESIGN.md` 中变量、阶段、评估口径完整
- [ ] `PROJECT_STRUCTURE.md` 与新增模块路径一致
- [ ] `METHOD_STRUCTURE.md` 与实验设计口径一致
- [ ] `EXPERIMENT_PROCESS_LOG.md` 已记录本次切换
- [ ] `reports/round_xxx/summary/` 含 json + md 且 `Analysis` 完整
