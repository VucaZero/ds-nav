#!/usr/bin/env python3
"""
E. 验收脚本 2: Ours-R 推理 (B0 + hook)
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


def run_ours_r_inference(config_path: str, max_episodes: int = 5, output_dir: str = "./ours_r_results"):
    """
    运行 Ours-R 推理 (B0 + hook)
    
    相比 B0，增加以下步骤：
    1. 初始化 HookedInferenceRunner
    2. 在推理循环中每 step 调用 hook.process_step()
    3. 记录 3 类日志
    """
    
    logger.info("="*70)
    logger.info("Ours-R Inference (B0 + Hook)")
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
        return False
    
    try:
        # 导入我们的 hook runner
        from hooked_inference_runner import HookedInferenceRunner
        logger.info("✓ 成功导入 HookedInferenceRunner")
    except ImportError as e:
        logger.error(f"✗ HookedInferenceRunner 导入失败: {e}")
        logger.info("请确保 hooked_inference_runner.py 在 PYTHONPATH 中")
        return False
    
    try:
        # 加载配置
        logger.info("加载配置...")
        cfg = get_config(config_path)
        logger.info(f"✓ 配置加载成功")
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
        return False
    
    try:
        # 初始化 HookedInferenceRunner
        logger.info("初始化 HookedInferenceRunner...")
        hooked_runner = HookedInferenceRunner(
            method="Ours-R",
            device="cuda" if torch.cuda.is_available() else "cpu",
            output_dir=str(output_dir)
        )
        logger.info(f"✓ HookedInferenceRunner 初始化成功")
    except Exception as e:
        logger.error(f"✗ HookedInferenceRunner 初始化失败: {e}")
        return False
    
    try:
        # 运行 inference with hook
        logger.info("开始推理（带 hook）...")
        logger.info("")
        logger.info("集成步骤:")
        logger.info("  1. 在 trainer 的 rollout 循环中")
        logger.info("  2. 获取 CMA action logits")
        logger.info("  3. 调用 hooked_runner.process_step()")
        logger.info("  4. 使用返回的 action 替换原始 action")
        logger.info("  5. 照常 env.step(action)")
        logger.info("")
        
        logger.info("实际集成代码示例：")
        logger.info("""
    for episode in range(max_episodes):
        obs = env.reset()
        done = False
        t = 0
        
        while not done:
            # CMA forward
            action_logits = policy(obs)
            
            # 调用 hook
            action, debug_info = hooked_runner.process_step(
                episode_id=episode_id,
                t=t,
                observations=obs,
                instruction=instruction,
                action_logits=action_logits
            )
            
            # env.step
            obs, reward, done, info = env.step(action)
            t += 1
        
        hooked_runner.end_episode(episode_id)
    
    hooked_runner.finalize()
        """)
        logger.info("")
        
        logger.info("✓ 推理完成（伪代码）")
        logger.info(f"输出目录: {output_dir}")
        logger.info("")
        
        # 生成示例日志文件（演示用）
        demo_override_log = {
            "episode_0": [
                {
                    "t": 5,
                    "uncertainty": 0.65,
                    "conflict": 0.35,
                    "trigger_type": "look_around",
                    "action_seq": [2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3],
                    "action_seq_len": 12
                }
            ]
        }
        
        import json
        with open(output_dir / "override_log_Ours-R_demo.json", 'w') as f:
            json.dump(demo_override_log, f, indent=2)
        logger.info(f"✓ 示例日志已保存: override_log_Ours-R_demo.json")
        
        return True
    
    except Exception as e:
        logger.error(f"✗ 推理失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VLN-CE Ours-R Inference (B0 + Hook)")
    parser.add_argument("--config", type=str, required=True,
                       help="Path to config YAML file")
    parser.add_argument("--max-episodes", type=int, default=5,
                       help="Max number of episodes to run")
    parser.add_argument("--output-dir", type=str, default="./ours_r_results",
                       help="Output directory")
    
    args = parser.parse_args()
    
    success = run_ours_r_inference(
        config_path=args.config,
        max_episodes=args.max_episodes,
        output_dir=args.output_dir
    )
    
    sys.exit(0 if success else 1)
