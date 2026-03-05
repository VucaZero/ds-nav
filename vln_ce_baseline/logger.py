"""
Logger: 综合日志和统计输出
跟踪 SR/SPL/NE/TL 以及消歧相关指标
"""
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import csv
from datetime import datetime


class EpisodeLogger:
    """
    单个 episode 的日志记录
    """
    def __init__(self, episode_id: str):
        self.episode_id = episode_id
        self.data = {
            "episode_id": episode_id,
            "success": False,
            "spl": 0.0,
            "path_length": 0.0,
            "trajectory_length": 0.0,
            "normalized_error": 0.0,
            "la_count": 0,
            "bt_count": 0,
            "follow_count": 0,
            "disambig_triggered": 0,
            "extra_turns": 0,
            "extra_forwards": 0,
            "loop_rate": 0.0,
            "u_reduction": 0.0,
            "c_reduction": 0.0,
            "timestamp": datetime.now().isoformat(),
        }
    
    def update(self, key: str, value: Any):
        """更新字段"""
        if key in self.data:
            self.data[key] = value
    
    def update_batch(self, **kwargs):
        """批量更新"""
        for k, v in kwargs.items():
            if k in self.data:
                self.data[k] = v
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return self.data.copy()


class EvaluationLogger:
    """
    完整评估的日志和统计
    """
    def __init__(self, output_dir: Optional[str] = None, method_name: str = "baseline"):
        """
        Args:
            output_dir: 输出目录
            method_name: 方法名称 (B0/B1/Ours-R/Ours-L)
        """
        self.output_dir = Path(output_dir) if output_dir else Path("./outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.method_name = method_name
        
        # 创建方法特定的子目录
        self.method_dir = self.output_dir / method_name
        self.method_dir.mkdir(exist_ok=True)
        
        self.episodes: List[EpisodeLogger] = []
        
        # 设置日志
        self.logger = logging.getLogger(f"evaluation_{method_name}")
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(self.method_dir / f"{method_name}.log")
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def add_episode(self, episode_logger: EpisodeLogger):
        """添加单个 episode 的日志"""
        self.episodes.append(episode_logger)
    
    def compute_aggregate_metrics(self) -> Dict[str, float]:
        """
        计算汇总指标
        
        Returns:
            metrics: 包含 SR/SPL/NE/TL 等的字典
        """
        if not self.episodes:
            return {}
        
        metrics = {
            "method": self.method_name,
            "num_episodes": len(self.episodes),
        }
        
        # SR: Success Rate
        successes = sum(1 for ep in self.episodes if ep.data["success"])
        metrics["sr"] = successes / len(self.episodes)
        
        # SPL: Success weighted by Path Length
        spl_sum = sum(ep.data["spl"] for ep in self.episodes if ep.data["success"])
        metrics["spl"] = spl_sum / len(self.episodes)
        
        # NE: Normalized Error (path length - optimal length) / optimal length
        ne_sum = sum(ep.data["normalized_error"] for ep in self.episodes)
        metrics["ne"] = ne_sum / len(self.episodes)
        
        # TL: Trajectory Length
        tl_sum = sum(ep.data["trajectory_length"] for ep in self.episodes)
        metrics["tl"] = tl_sum / len(self.episodes)
        
        # 消歧相关指标
        metrics["avg_la_count"] = sum(ep.data["la_count"] for ep in self.episodes) / len(self.episodes)
        metrics["avg_bt_count"] = sum(ep.data["bt_count"] for ep in self.episodes) / len(self.episodes)
        metrics["avg_disambig_triggered"] = sum(ep.data["disambig_triggered"] for ep in self.episodes) / len(self.episodes)
        metrics["total_extra_turns"] = sum(ep.data["extra_turns"] for ep in self.episodes)
        metrics["total_extra_forwards"] = sum(ep.data["extra_forwards"] for ep in self.episodes)
        metrics["avg_loop_rate"] = sum(ep.data["loop_rate"] for ep in self.episodes) / len(self.episodes)
        metrics["avg_u_reduction"] = sum(ep.data["u_reduction"] for ep in self.episodes) / len(self.episodes)
        metrics["avg_c_reduction"] = sum(ep.data["c_reduction"] for ep in self.episodes) / len(self.episodes)
        
        return metrics
    
    def save_results(self, split: str = "val_unseen"):
        """
        保存评估结果到文件
        
        Args:
            split: 数据集划分 (val_unseen/val_seen)
        """
        # 保存详细的 episode 日志
        episodes_json = self.method_dir / f"{split}_episodes.json"
        with open(episodes_json, 'w') as f:
            episodes_data = [ep.to_dict() for ep in self.episodes]
            json.dump(episodes_data, f, indent=2)
        self.logger.info(f"Saved episodes to {episodes_json}")
        
        # 计算汇总指标
        metrics = self.compute_aggregate_metrics()
        
        # 保存汇总指标
        metrics_json = self.method_dir / f"{split}_metrics.json"
        with open(metrics_json, 'w') as f:
            json.dump(metrics, f, indent=2)
        self.logger.info(f"Saved metrics to {metrics_json}")
        
        # 输出到日志
        self._log_metrics(metrics, split)
        
        return metrics
    
    def _log_metrics(self, metrics: Dict, split: str):
        """输出指标到日志"""
        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"Evaluation Results - {split}")
        self.logger.info(f"{'='*50}")
        self.logger.info(f"Method: {metrics.get('method')}")
        self.logger.info(f"Episodes: {metrics.get('num_episodes')}")
        self.logger.info(f"")
        self.logger.info(f"Standard Metrics:")
        self.logger.info(f"  SR (Success Rate):        {metrics.get('sr', 0):.4f}")
        self.logger.info(f"  SPL (Success weighted):   {metrics.get('spl', 0):.4f}")
        self.logger.info(f"  NE (Normalized Error):    {metrics.get('ne', 0):.4f}")
        self.logger.info(f"  TL (Trajectory Length):   {metrics.get('tl', 0):.2f}")
        self.logger.info(f"")
        self.logger.info(f"Disambiguation Metrics:")
        self.logger.info(f"  Avg LA Count:             {metrics.get('avg_la_count', 0):.2f}")
        self.logger.info(f"  Avg BT Count:             {metrics.get('avg_bt_count', 0):.2f}")
        self.logger.info(f"  Avg Disambig Triggered:   {metrics.get('avg_disambig_triggered', 0):.2f}")
        self.logger.info(f"  Total Extra Turns:        {metrics.get('total_extra_turns', 0)}")
        self.logger.info(f"  Total Extra Forwards:     {metrics.get('total_extra_forwards', 0)}")
        self.logger.info(f"  Avg Loop Rate:            {metrics.get('avg_loop_rate', 0):.4f}")
        self.logger.info(f"  Avg U Reduction:          {metrics.get('avg_u_reduction', 0):.4f}")
        self.logger.info(f"  Avg C Reduction:          {metrics.get('avg_c_reduction', 0):.4f}")
        self.logger.info(f"{'='*50}\n")
    
    @staticmethod
    def print_comparison(results_dict: Dict[str, Dict]):
        """
        打印多个方法的对比结果
        
        Args:
            results_dict: {method_name: metrics_dict, ...}
        """
        print("\n" + "="*80)
        print("EVALUATION COMPARISON RESULTS")
        print("="*80)
        
        # 标准指标表
        print("\nStandard Metrics:")
        print("-"*80)
        print(f"{'Method':<15} {'SR':<12} {'SPL':<12} {'NE':<12} {'TL':<12}")
        print("-"*80)
        for method, metrics in results_dict.items():
            print(f"{method:<15} "
                  f"{metrics.get('sr', 0):<12.4f} "
                  f"{metrics.get('spl', 0):<12.4f} "
                  f"{metrics.get('ne', 0):<12.4f} "
                  f"{metrics.get('tl', 0):<12.2f}")
        print("-"*80)
        
        # 消歧指标表
        print("\nDisambiguation Metrics:")
        print("-"*80)
        print(f"{'Method':<15} {'Avg LA':<12} {'Avg BT':<12} {'Disambig Trg':<12} {'U Red':<12}")
        print("-"*80)
        for method, metrics in results_dict.items():
            print(f"{method:<15} "
                  f"{metrics.get('avg_la_count', 0):<12.2f} "
                  f"{metrics.get('avg_bt_count', 0):<12.2f} "
                  f"{metrics.get('avg_disambig_triggered', 0):<12.2f} "
                  f"{metrics.get('avg_u_reduction', 0):<12.4f}")
        print("-"*80)
        print("="*80 + "\n")
