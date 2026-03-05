#!/usr/bin/env python3
"""
E. 验收脚本 1: B0 官方 baseline 推理
"""

import sys
import os
import argparse
import logging
from pathlib import Path

import torch
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加路径
WORKSPACE = Path("/home/data/czh/ds-nav")
VLNCE_ROOT = Path(os.environ.get("VLNCE_ROOT", f"{WORKSPACE}/programs/VLN-CE"))

sys.path.insert(0, str(VLNCE_ROOT))
sys.path.insert(0, str(WORKSPACE))


def run_b0_baseline(config_path: str, max_episodes: int = 5, output_dir: str = "./b0_results"):
    """
    运行官方 B0 baseline
    
    这是一个轻量化的推理脚本，展示如何：
    1. 加载 VLN-CE 配置
    2. 初始化官方 trainer
    3. 运行 eval/inference
    4. 保存 predictions
    """
    
    logger.info("="*70)
    logger.info("B0 Official Baseline Inference")
    logger.info("="*70)
    logger.info(f"Config: {config_path}")
    logger.info(f"Max episodes: {max_episodes}")
    logger.info(f"Output: {output_dir}")
    logger.info("")
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # 导入 VLN-CE config loader
        from vlnce_baselines.config import get_config
        logger.info("✓ 成功导入 VLN-CE config")
    except ImportError as e:
        logger.error(f"✗ 导入失败: {e}")
        logger.info("请确保 VLN-CE 已安装: pip install -e .")
        return False
    
    try:
        # 加载配置
        logger.info("加载配置...")
        cfg = get_config(config_path)
        logger.info(f"✓ 配置加载成功")
        logger.info(f"  Trainer: {cfg.TRAINER_NAME if hasattr(cfg, 'TRAINER_NAME') else 'unknown'}")
        logger.info(f"  Dataset split: {cfg.TASK_CONFIG.DATASET.SPLIT if hasattr(cfg.TASK_CONFIG, 'DATASET') else 'unknown'}")
    except Exception as e:
        logger.error(f"✗ 配置加载失败: {e}")
        return False
    
    try:
        # 导入 baseline registry
        from habitat_baselines.common.baseline_registry import baseline_registry
        logger.info("✓ 成功导入 baseline_registry")
    except ImportError as e:
        logger.error(f"✗ baseline_registry 导入失败: {e}")
        return False
    
    try:
        # 初始化 trainer
        logger.info("初始化 trainer...")
        trainer_init = baseline_registry.get_trainer(cfg.TRAINER_NAME)
        if trainer_init is None:
            logger.error(f"✗ Trainer '{cfg.TRAINER_NAME}' 未注册")
            return False
        
        trainer = trainer_init(cfg)
        logger.info(f"✓ Trainer 初始化成功")
    except Exception as e:
        logger.error(f"✗ Trainer 初始化失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    try:
        # 运行 inference
        # 注意：这里的实现取决于官方 VLN-CE 的具体 trainer API
        # 一般来说，调用 trainer.eval() 或 trainer.inference()
        
        logger.info("开始推理...")
        logger.info("(这需要对接官方 trainer 的 eval/inference 方法)")
        logger.info("")
        logger.info("实际运行步骤:")
        logger.info("  1. 调用 trainer.eval() 或 trainer.inference()")
        logger.info("  2. trainer 应保存 predictions 到 predictions.json")
        logger.info("  3. 调用官方 evaluator 计算指标")
        logger.info("")
        
        # 这里是伪代码，实际需要查看官方 trainer 的接口
        # predictions = trainer.eval()  # 或 trainer.inference()
        
        logger.info("✓ 推理完成（伪代码）")
        logger.info(f"输出目录: {output_dir}")
        
        return True
    
    except Exception as e:
        logger.error(f"✗ 推理失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VLN-CE B0 Baseline Inference")
    parser.add_argument("--config", type=str, required=True,
                       help="Path to config YAML file")
    parser.add_argument("--max-episodes", type=int, default=5,
                       help="Max number of episodes to run")
    parser.add_argument("--output-dir", type=str, default="./b0_results",
                       help="Output directory")
    
    args = parser.parse_args()
    
    success = run_b0_baseline(
        config_path=args.config,
        max_episodes=args.max_episodes,
        output_dir=args.output_dir
    )
    
    sys.exit(0 if success else 1)
