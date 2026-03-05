# ds-nav 实验主线总览

更新时间：2026-03-04

## 1. 根目录保留文档（指导性）
- `AGENTS.md`：协作与执行规范（核心，不动）
- `EXPERIMENT_DESIGN.md`：实验设计唯一来源（核心，不动）
- `METHOD_STRUCTURE.md`：方法路径与验证逻辑
- `PROJECT_STRUCTURE_SPEC.md`：项目结构规范与边界
- `EXPERIMENT_FILE_LAYOUT.md`：实验代码/数据/权重落位规则
- `README.md`：本总览

历史说明文档已迁移到：`history/docs/legacy_guides/`

## 2. 主线目录
- `programs/VLN-CE/`：官方 VLN-CE 运行底座
- `vln_ce_baseline/`：方法模块与注入实现
- `scripts/experiments/`：资产规整与 E0/E1 运行入口
- `experiment_workspace/`：后续实验专用空间（code/data/models/outputs/reports/configs）
- `reports/round_xxx/`：轮次证据与结论

## 3. 当前资产状态（可开跑）
- MP3D scene：`programs/VLN-CE/data/scene_datasets/mp3d/`（90 个场景）
- R2R preprocessed：`programs/VLN-CE/data/datasets/R2R_VLNCE_v1-3_preprocessed/`
- CMA checkpoint：`programs/VLN-CE/data/checkpoints/CMA_PM_DA_Aug.pth`

## 4. 历史/参考区
- `history/`：历史文档、旧下载、旧运行产物
- `LTE_Nav/`：参考平台（非本轮 E0/E1 主线执行目录）

## 5. 实验前固定检查
```bash
cd /home/data/czh/ds-nav
bash scripts/experiments/check_and_layout_assets.sh
bash dsnav.sh data-verify
```

## 6. E0/E1 启动
```bash
bash /home/data/czh/ds-nav/scripts/experiments/run_e0_e1.sh
```
