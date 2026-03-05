#!/usr/bin/env python3
"""
兼容入口：调用 run_official_vlnce.py 的真实推理实现。
"""

import argparse
import json
import logging
import sys
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_official_vlnce import load_official_config, run_official_inference


def main() -> int:
    parser = argparse.ArgumentParser(description="VLN-CE 官方推理（集成 DS/CLIP/门控）")
    parser.add_argument("--exp-config", type=str, required=True, help="官方 VLN-CE 配置文件路径")
    parser.add_argument("--run-type", type=str, choices=["inference", "eval"], default="inference", help="运行类型")
    parser.add_argument("--method", type=str, default="B0", choices=["B0", "B1", "Ours-R", "Ours-L"], help="推理方法")
    parser.add_argument("--split", type=str, default="val_unseen", choices=["val_unseen", "val_seen", "test"], help="数据集划分")
    parser.add_argument("--max-episodes", type=int, default=None, help="最多运行 episodes 数（默认全量）")
    parser.add_argument("--output-dir", type=str, default="./eval_results_official", help="输出目录")
    parser.add_argument("--uncertainty-threshold", type=float, default=0.5, help="不确定性门控阈值")
    parser.add_argument("--conflict-threshold", type=float, default=0.3, help="冲突门控阈值")
    parser.add_argument("opts", default=None, nargs=argparse.REMAINDER, help="额外配置选项")

    args = parser.parse_args()

    config = load_official_config(args.exp_config, args.opts)
    result = run_official_inference(
        config=config,
        method=args.method,
        split=args.split,
        max_episodes=args.max_episodes,
        output_dir=args.output_dir,
        uncertainty_threshold=args.uncertainty_threshold,
        conflict_threshold=args.conflict_threshold,
    )

    logger.info("完成: %s", json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
