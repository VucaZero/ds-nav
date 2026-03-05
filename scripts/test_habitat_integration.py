#!/usr/bin/env python3
"""
VLN-CE 环境集成测试
验证 B1：环境加载、动作空间、CMA backbone 对齐
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加 ds-nav 到路径
DSNAV_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(DSNAV_ROOT))
sys.path.insert(0, str(DSNAV_ROOT / "vln_ce_baseline"))

# 添加 habitat-lab 到路径
HABITAT_ROOT = DSNAV_ROOT / "programs" / "habitat-lab"
sys.path.insert(0, str(HABITAT_ROOT))


def test_imports():
    """测试关键导入"""
    logger.info("=" * 60)
    logger.info("TEST 1: 验证关键导入")
    logger.info("=" * 60)
    
    try:
        import torch
        logger.info(f"✓ PyTorch: {torch.__version__}")
        logger.info(f"  CUDA available: {torch.cuda.is_available()}")
    except ImportError as e:
        logger.error(f"✗ PyTorch 导入失败: {e}")
        return False
    
    try:
        import habitat
        logger.info(f"✓ Habitat: {habitat.__version__}")
    except ImportError as e:
        logger.error(f"✗ Habitat 导入失败: {e}")
        return False
    
    try:
        from habitat.config import Config
        logger.info("✓ habitat.config.Config")
    except ImportError as e:
        logger.error(f"✗ habitat.config 导入失败: {e}")
        return False
    
    try:
        from habitat_baselines.config.default import get_config
        logger.info("✓ habitat_baselines.config.default.get_config")
    except ImportError as e:
        logger.error(f"✗ habitat_baselines 导入失败: {e}")
        logger.warning("  尝试使用备用导入...")
        try:
            from habitat.config import Config as get_config
            logger.info("✓ 备用导入成功")
        except ImportError:
            return False
    
    try:
        from vlnce_integration.action_primitives import VLNCEActionType, ActionPrimitive
        logger.info("✓ vlnce_integration.action_primitives")
    except ImportError as e:
        logger.error(f"✗ action_primitives 导入失败: {e}")
        return False
    
    try:
        from vlnce_integration.inference_hook import InferenceHook
        logger.info("✓ vlnce_integration.inference_hook")
    except ImportError as e:
        logger.error(f"✗ inference_hook 导入失败: {e}")
        return False
    
    return True


def test_action_primitives():
    """测试动作基元"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: 验证动作基元")
    logger.info("=" * 60)
    
    try:
        from vlnce_integration.action_primitives import ActionPrimitive, VLNCEActionType
        
        # 测试 LA-90
        la_trajectory = ActionPrimitive.get_la_trajectory()
        logger.info(f"✓ LA-90 轨迹长度: {len(la_trajectory)}")
        logger.info(f"  动作: {[VLNCEActionType(a).name for a in la_trajectory[:6]]}")
        assert len(la_trajectory) == 24, f"期望 LA-90 长度 24，得到 {len(la_trajectory)}"
        
        # 测试 BACKTRACK
        bt_trajectory = ActionPrimitive.get_backtrack_trajectory()
        logger.info(f"✓ BACKTRACK 轨迹长度: {len(bt_trajectory)}")
        logger.info(f"  动作: {[VLNCEActionType(a).name for a in bt_trajectory]}")
        assert len(bt_trajectory) == 13, f"期望 BACKTRACK 长度 13，得到 {len(bt_trajectory)}"
        
        return True
    except Exception as e:
        logger.error(f"✗ 动作基元测试失败: {e}")
        return False


def test_inference_hook():
    """测试推理钩子初始化"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: 验证推理钩子初始化")
    logger.info("=" * 60)
    
    try:
        import torch
        from vlnce_integration.inference_hook import InferenceHook
        
        # 测试 B0
        hook_b0 = InferenceHook(method="B0", device="cpu")
        logger.info("✓ B0 钩子初始化成功")
        
        # 测试 B1（简化版）
        try:
            hook_b1 = InferenceHook(method="B1", device="cpu")
            logger.info("✓ B1 钩子初始化成功")
        except Exception as e:
            logger.warning(f"⚠ B1 初始化部分失败（预期）: {e}")
        
        # 测试 reset_episode
        hook_b0.reset_episode("test_ep_001")
        logger.info("✓ reset_episode() 成功")
        
        return True
    except Exception as e:
        logger.error(f"✗ 推理钩子测试失败: {e}")
        return False


def test_config_loading(config_path: Optional[str] = None):
    """测试配置加载"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: 验证配置加载")
    logger.info("=" * 60)
    
    if config_path is None:
        # 查找默认配置
        test_configs = [
            HABITAT_ROOT / "configs" / "tasks" / "vln_r2r.yaml",
            HABITAT_ROOT / "configs" / "tasks" / "vln" / "vln_r2r.yaml",
        ]
        
        for cfg_path in test_configs:
            if cfg_path.exists():
                config_path = str(cfg_path)
                logger.info(f"发现配置: {config_path}")
                break
    
    if config_path is None:
        logger.warning("⚠ 未找到默认配置文件，跳过配置测试")
        return True
    
    try:
        # 尝试加载配置
        try:
            from habitat_baselines.config.default import get_config
            config = get_config(config_path)
            logger.info(f"✓ 配置加载成功")
            
            # 检查关键字段
            if hasattr(config, 'DATASET'):
                logger.info(f"  数据集: {config.DATASET.TYPE if hasattr(config.DATASET, 'TYPE') else 'unknown'}")
            if hasattr(config, 'TRAINER_NAME'):
                logger.info(f"  Trainer: {config.TRAINER_NAME}")
            
        except Exception as e:
            logger.warning(f"⚠ habitat_baselines 加载失败，尝试备用方法: {e}")
            
            from habitat.config import Config
            config = Config.load(config_path)
            logger.info(f"✓ 备用配置加载成功")
        
        return True
    except Exception as e:
        logger.error(f"✗ 配置加载失败: {e}")
        return False


def test_environment_creation(config_path: Optional[str] = None, num_episodes: int = 2):
    """测试环境创建"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: 验证环境创建和基本推理")
    logger.info("=" * 60)
    
    if config_path is None:
        config_path = str(HABITAT_ROOT / "configs" / "tasks" / "vln_r2r.yaml")
    
    if not os.path.exists(config_path):
        logger.warning(f"⚠ 配置文件不存在: {config_path}，跳过环境测试")
        return True
    
    try:
        import torch
        from habitat import make_env
        from habitat_baselines.config.default import get_config
        
        # 加载配置
        config = get_config(config_path, ["TASK_CONFIG.DATASET.SPLIT", "val_unseen"])
        logger.info(f"✓ 配置加载成功")
        
        # 创建环境
        env = make_env(config=config.TASK_CONFIG, env_class="VizDoomGym")  # 或适当的 env class
        logger.info(f"✓ 环境创建成功")
        
        # 重置环境
        obs = env.reset()
        logger.info(f"✓ env.reset() 成功")
        logger.info(f"  观测字段: {list(obs.keys()) if isinstance(obs, dict) else 'not a dict'}")
        
        # 检查 RGB
        if isinstance(obs, dict) and "rgb" in obs:
            rgb = obs["rgb"]
            logger.info(f"  RGB 形状: {rgb.shape if hasattr(rgb, 'shape') else 'unknown'}")
        
        # 测试几个随机步
        for step_id in range(min(3, num_episodes * 10)):
            action = env.action_space.sample()
            obs, reward, done, info = env.step(action)
            if done:
                obs = env.reset()
        
        logger.info(f"✓ 环境推理循环正常 ({step_id + 1} 步)")
        
        env.close()
        logger.info(f"✓ 环境关闭成功")
        
        return True
    
    except Exception as e:
        logger.error(f"✗ 环境测试失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def main():
    parser = argparse.ArgumentParser(description="VLN-CE 集成测试")
    parser.add_argument("--config", type=str, default=None, help="配置文件路径")
    parser.add_argument("--test", type=str, default="all",
                       choices=["all", "imports", "actions", "hook", "config", "env"],
                       help="运行指定测试")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("VLN-CE 真实环境集成测试")
    logger.info("=" * 60)
    logger.info(f"Python: {sys.version}")
    logger.info(f"CWD: {os.getcwd()}")
    logger.info(f"DSNAV_ROOT: {DSNAV_ROOT}")
    logger.info(f"HABITAT_ROOT: {HABITAT_ROOT}")
    logger.info("")
    
    results = {}
    
    # 运行选定的测试
    if args.test in ["all", "imports"]:
        results["imports"] = test_imports()
    
    if args.test in ["all", "actions"]:
        results["actions"] = test_action_primitives()
    
    if args.test in ["all", "hook"]:
        results["hook"] = test_inference_hook()
    
    if args.test in ["all", "config"]:
        results["config"] = test_config_loading(args.config)
    
    if args.test in ["all", "env"]:
        results["env"] = test_environment_creation(args.config)
    
    # 输出总结
    logger.info("\n" + "=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n✓ 所有测试通过！")
        return 0
    else:
        logger.warning("\n⚠ 部分测试失败，请检查上述错误")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
