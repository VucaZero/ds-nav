"""
VLN-CE 官方 evaluator 包装器
调用官方 evaluator 并合并消歧统计
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess

logger = logging.getLogger(__name__)


class OfficialEvaluatorWrapper:
    """
    包装 VLN-CE 官方 evaluator
    - 调用官方评估脚本
    - 读取官方指标
    - 合并新增统计
    """
    
    def __init__(self, 
                 evaluator_script: str,
                 split: str = "val_unseen",
                 method: str = "baseline"):
        """
        Args:
            evaluator_script: 官方 evaluator 脚本路径
            split: 数据集划分 (val_unseen/val_seen/test)
            method: 方法名称
        """
        self.evaluator_script = evaluator_script
        self.split = split
        self.method = method
        
        # 结果缓存
        self.official_metrics: Dict = {}
        self.disambig_stats: Dict = {}
    
    def run_official_evaluation(self, 
                               predictions_file: str,
                               output_dir: str) -> Dict[str, float]:
        """
        调用官方 evaluator
        
        Args:
            predictions_file: predictions.json 路径
            output_dir: 输出目录
            
        Returns:
            official_metrics: 官方指标字典 {sr, spl, ne, tl, ...}
        """
        try:
            logger.info(f"Running official evaluator on {predictions_file}")
            
            # 假设官方 evaluator 脚本接受 --predictions 和 --output_dir 参数
            cmd = [
                "python", self.evaluator_script,
                "--predictions", predictions_file,
                "--output_dir", output_dir,
                "--split", self.split,
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"Evaluator failed: {result.stderr}")
                return {}
            
            logger.info(f"Evaluator output:\n{result.stdout}")
            
            # 尝试从输出解析指标（取决于官方 evaluator 的输出格式）
            # 这里假设官方 evaluator 会输出或保存 JSON 格式的指标
            metrics_file = Path(output_dir) / "metrics.json"
            if metrics_file.exists():
                with open(metrics_file) as f:
                    self.official_metrics = json.load(f)
                logger.info(f"Official metrics: {self.official_metrics}")
            
            return self.official_metrics
        
        except Exception as e:
            logger.error(f"Error running official evaluator: {e}")
            return {}
    
    def aggregate_disambig_statistics(self, 
                                      episode_logs: List[Dict]) -> Dict:
        """
        从 episode 日志聚合消歧统计
        
        Args:
            episode_logs: episode 日志列表（来自 inference_hook）
            
        Returns:
            disambig_stats: 聚合统计字典
        """
        stats = {
            "method": self.method,
            "split": self.split,
            "num_episodes": len(episode_logs),
            "total_steps": sum(log.get("action_count", 0) for log in episode_logs),
            "total_la_count": sum(log.get("la_count", 0) for log in episode_logs),
            "total_bt_count": sum(log.get("bt_count", 0) for log in episode_logs),
            "total_disambig_count": sum(log.get("disambig_count", 0) for log in episode_logs),
            "avg_steps_per_episode": 0,
            "avg_la_per_episode": 0,
            "avg_bt_per_episode": 0,
            "la_trigger_rate": 0.0,
            "bt_trigger_rate": 0.0,
            "disambig_trigger_rate": 0.0,
        }
        
        if stats["num_episodes"] > 0:
            stats["avg_steps_per_episode"] = stats["total_steps"] / stats["num_episodes"]
            stats["avg_la_per_episode"] = stats["total_la_count"] / stats["num_episodes"]
            stats["avg_bt_per_episode"] = stats["total_bt_count"] / stats["num_episodes"]
            stats["disambig_trigger_rate"] = (
                stats["total_disambig_count"] / stats["total_steps"]
                if stats["total_steps"] > 0 else 0.0
            )
        
        self.disambig_stats = stats
        logger.info(f"Disambig statistics:\n{json.dumps(stats, indent=2)}")
        
        return stats
    
    def merge_metrics(self, output_file: str) -> Dict:
        """
        合并官方指标 + 消歧统计，保存为单一 JSON
        
        Args:
            output_file: 输出文件路径
            
        Returns:
            merged: 合并后的指标
        """
        merged = {
            "official_metrics": self.official_metrics,
            "disambig_stats": self.disambig_stats,
        }
        
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(merged, f, indent=2)
        
        logger.info(f"Merged metrics saved to {output_file}")
        return merged
    
    def save_episode_logs(self, episode_logs: List[Dict], output_file: str):
        """
        保存所有 episode 的详细日志
        
        Args:
            episode_logs: episode 日志列表
            output_file: 输出文件路径
        """
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(episode_logs, f, indent=2)
        logger.info(f"Episode logs saved to {output_file}")


class PredictionsFormatter:
    """
    将我们的结果格式化为 VLN-CE 官方 predictions.json
    """
    
    @staticmethod
    def format_predictions(trajectories: Dict[str, List[int]],
                          output_file: str,
                          output_format: str = "r2r"):
        """
        格式化预测为官方格式
        
        Args:
            trajectories: {episode_id: [action_ids...], ...}
            output_file: 输出文件
        """
        if output_format == "r2r":
            # 官方 r2r 推理格式：{episode_id: [info_dict, ...]}
            predictions = {episode_id: traj for episode_id, traj in trajectories.items()}
        elif output_format == "actions":
            # 兼容旧逻辑（动作序列，不用于官方 evaluator）
            predictions = []
            for episode_id, actions in trajectories.items():
                predictions.append({
                    "episode_id": episode_id,
                    "trajectory": actions,
                })
        else:
            raise ValueError(f"Unsupported output_format: {output_format}")

        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(predictions, f, indent=2)
        
        logger.info(f"Predictions saved to {output_file}")
