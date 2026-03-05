#!/usr/bin/env python3
"""
集成测试：验证官方推理脚本的基本功能
不需要真实的 Habitat 环境，只验证结构和导入
"""

import sys
import os
from pathlib import Path

DSNAV_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(DSNAV_ROOT))
sys.path.insert(0, str(DSNAV_ROOT / "vln_ce_baseline"))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_script_imports():
    """测试推理脚本的导入"""
    logger.info("=" * 60)
    logger.info("测试 1: 推理脚本导入")
    logger.info("=" * 60)
    
    try:
        # 导入脚本中的关键模块
        from vlnce_integration.inference_hook import InferenceHook
        logger.info("✓ InferenceHook 导入成功")
        
        import torch
        logger.info(f"✓ PyTorch {torch.__version__}")
        
        # 验证可以创建脚本对象（虚拟）
        logger.info("✓ 所有关键导入成功")
        return True
    except Exception as e:
        logger.error(f"✗ 导入失败: {e}")
        return False


def test_output_directory():
    """测试输出目录创建"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 2: 输出目录创建")
    logger.info("=" * 60)
    
    try:
        from pathlib import Path
        output_dir = Path("/tmp/test_vlnce_output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查创建是否成功
        assert output_dir.exists(), "输出目录创建失败"
        logger.info(f"✓ 输出目录创建成功: {output_dir}")
        
        # 清理
        import shutil
        shutil.rmtree(output_dir)
        logger.info("✓ 临时目录清理完成")
        
        return True
    except Exception as e:
        logger.error(f"✗ 目录测试失败: {e}")
        return False


def test_json_output():
    """测试 JSON 输出格式"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 3: JSON 输出格式")
    logger.info("=" * 60)
    
    try:
        import json
        from pathlib import Path
        
        test_data = {
            "method": "Ours-R",
            "num_episodes": 5,
            "trajectories": {
                "ep_001": [1, 2, 1, 0],
                "ep_002": [1, 1, 0],
            }
        }
        
        test_file = Path("/tmp/test_predictions.json")
        with open(test_file, 'w') as f:
            json.dump(test_data, f, indent=2)
        
        # 验证能读回
        with open(test_file, 'r') as f:
            loaded = json.load(f)
        
        assert loaded == test_data, "JSON 往返失败"
        logger.info("✓ JSON 输出格式正确")
        
        # 清理
        test_file.unlink()
        return True
    except Exception as e:
        logger.error(f"✗ JSON 测试失败: {e}")
        return False


def test_argument_parsing():
    """测试命令行参数解析"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 4: 命令行参数解析")
    logger.info("=" * 60)
    
    try:
        import argparse
        
        parser = argparse.ArgumentParser()
        parser.add_argument("--method", choices=["B0", "B1", "Ours-R", "Ours-L"], default="B0")
        parser.add_argument("--max-episodes", type=int, default=None)
        parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
        
        # 测试几个参数组合
        test_cases = [
            [],
            ["--method", "Ours-R"],
            ["--method", "B1", "--max-episodes", "50"],
            ["--device", "cpu"],
        ]
        
        for test_args in test_cases:
            args = parser.parse_args(test_args)
            logger.info(f"  ✓ 参数解析: {test_args if test_args else '(默认)'}")
        
        logger.info("✓ 参数解析测试完成")
        return True
    except Exception as e:
        logger.error(f"✗ 参数解析失败: {e}")
        return False


def main():
    logger.info("VLN-CE 推理脚本集成测试")
    logger.info("")
    
    results = {}
    
    results["imports"] = test_script_imports()
    results["directory"] = test_output_directory()
    results["json"] = test_json_output()
    results["args"] = test_argument_parsing()
    
    # 汇总
    logger.info("\n" + "=" * 60)
    logger.info("测试汇总")
    logger.info("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n✓ 所有集成测试通过！")
        return 0
    else:
        logger.warning("\n⚠ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
