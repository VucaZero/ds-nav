"""
DSBeliefFilter: Dempster-Shafer 理论用于不确定性表征和时序融合
"""
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class DSBeliefFilter(nn.Module):
    """
    使用 Dempster-Shafer 理论表征 ignorance 和 conflict
    - 将视觉证据转换为基本概率分配 (BPA)
    - 通过 Dempster 规则进行时序融合
    - 计算 uncertainty 和 conflict 度量
    
    核心思想：
    - 对于每个动作，基于地标证据建立信念函数
    - 不确定性 = ignorance + conflict
    - ignorance: 缺乏证据的程度
    - conflict: 相互矛盾的证据的程度
    """
    
    def __init__(self, num_actions: int, fusion_window: int = 5):
        """
        Args:
            num_actions: 动作空间大小
            fusion_window: 时序融合窗口大小
        """
        super().__init__()
        self.num_actions = num_actions
        self.fusion_window = fusion_window
        
        # 融合历史缓冲区
        self.history_buffer: List[Dict] = []
    
    def visibility_to_mass(self, visibility_scores: torch.Tensor) -> torch.Tensor:
        """
        将可见性分数转换为 DS 基本概率分配 (BPA)
        
        Args:
            visibility_scores: (num_landmarks,) 可见性分数 [0, 1]
            
        Returns:
            mass_dict: 支撑集合 -> 质量的映射
                - {'landmark_i'}: 高可见性的直接证据
                - {}: 低可见性的无知表征
        """
        mass_dict = {}
        
        # 每个高可见性的地标作为单独的支撑集合
        threshold = 0.5
        selected_scores = []
        for i, score in enumerate(visibility_scores):
            if score > threshold:
                # 使用分数本身作为质量
                val = float(score.item())
                selected_scores.append((f'landmark_{i}', val))

        # 归一化为合法质量分配（总和 <= 1）
        total_selected = sum(v for _, v in selected_scores)
        norm_factor = max(1.0, total_selected)
        for key, val in selected_scores:
            mass_dict[key] = val / norm_factor
        
        # 剩余质量分配给空集（代表无知）
        total_assigned = sum(mass_dict.values())
        mass_dict['unknown'] = max(0.0, 1.0 - total_assigned)
        
        return mass_dict
    
    def dempster_combine(self, mass1: Dict[str, float], mass2: Dict[str, float]) -> Dict[str, float]:
        """
        Dempster 合并规则：融合两个基本概率分配
        
        M(A) = (sum_{B∩C=A} m1(B)*m2(C)) / (1 - conflict)
        
        其中 conflict = sum_{B∩C=∅} m1(B)*m2(C)
        
        Args:
            mass1, mass2: 两个 BPA 字典
            
        Returns:
            combined_mass: 融合后的 BPA
        """
        combined = {}
        
        # 计算所有可能的交集
        all_elements = set(mass1.keys()) | set(mass2.keys())
        
        conflict = 0.0
        for set1 in mass1:
            for set2 in mass2:
                # 计算两个支撑集合的交集
                if set1 == 'unknown' or set2 == 'unknown':
                    # 与无知集合的交集就是它本身
                    intersection = set1 if set1 != 'unknown' else set2
                    if intersection not in combined:
                        combined[intersection] = 0.0
                    combined[intersection] += mass1[set1] * mass2[set2]
                elif set1 == set2:
                    # 相同支撑集合
                    if set1 not in combined:
                        combined[set1] = 0.0
                    combined[set1] += mass1[set1] * mass2[set2]
                else:
                    # 不同支撑集合的交集为空，产生冲突
                    conflict += mass1[set1] * mass2[set2]
        
        # 归一化
        normalization = 1.0 - conflict
        if normalization > 1e-6:
            combined = {k: v / normalization for k, v in combined.items()}
        else:
            # 全冲突退化：回退到完全无知，避免数值爆炸
            combined = {"unknown": 1.0}
            conflict = 1.0
        
        # 记录冲突度
        combined['_conflict'] = conflict
        
        return combined
    
    def compute_belief_and_uncertainty(self, mass_dict: Dict[str, float]) -> Tuple[float, float, float]:
        """
        从 BPA 计算信念、似然和不确定性
        
        Args:
            mass_dict: 基本概率分配
            
        Returns:
            belief: 信念度量 [0, 1]
            uncertainty: 不确定性度量 [0, 1]
            conflict: 冲突度量 [0, 1]
        """
        # 移除特殊键
        conflict = mass_dict.pop('_conflict', 0.0)
        
        # 无知质量（分配给 'unknown'）
        ignorance = mass_dict.get('unknown', 0.0)
        
        # 信念 = 1 - 无知
        belief = 1.0 - ignorance
        
        # 不确定性 = 无知 + 冲突
        uncertainty = ignorance + conflict
        uncertainty = min(1.0, uncertainty)  # 截断到 [0, 1]
        
        return belief, uncertainty, conflict
    
    def temporal_fusion(self, visibility_sequences: List[torch.Tensor]) -> Dict[str, torch.Tensor]:
        """
        在时序上融合多个观测的不确定性
        使用滑动窗口的 Dempster 融合
        
        Args:
            visibility_sequences: 历史可见性分数序列
                                  [(num_landmarks,), ...]
            
        Returns:
            fusion_results: 包含融合后信念和不确定性的字典
        """
        if not visibility_sequences:
            return {"belief": 0.5, "uncertainty": 1.0}
        
        # 初始化第一个观测的 BPA
        mass = self.visibility_to_mass(visibility_sequences[0])
        
        # 逐步融合后续观测
        for vis_seq in visibility_sequences[1:]:
            new_mass = self.visibility_to_mass(vis_seq)
            mass = self.dempster_combine(mass, new_mass)
        
        # 计算融合后的信念和不确定性
        belief, uncertainty, conflict = self.compute_belief_and_uncertainty(mass.copy())
        
        return {
            "belief": torch.tensor(belief, dtype=torch.float32),
            "uncertainty": torch.tensor(uncertainty, dtype=torch.float32),
            "conflict": torch.tensor(conflict, dtype=torch.float32),
            "mass_dict": mass
        }
    
    def forward(self, visibility_scores: torch.Tensor, 
               historical_visibility: Optional[List[torch.Tensor]] = None) -> Dict[str, torch.Tensor]:
        """
        前向传播：计算当前观测的不确定性度量
        
        Args:
            visibility_scores: (num_landmarks,) 当前可见性
            historical_visibility: 历史可见性序列（可选）
            
        Returns:
            uncertainty_metrics: 包含 uncertainty, ignorance, conflict 的字典
        """
        # 当前观测的 BPA
        mass = self.visibility_to_mass(visibility_scores)
        belief, uncertainty, conflict = self.compute_belief_and_uncertainty(mass.copy())
        
        # 如果有历史观测，执行时序融合
        if historical_visibility is not None:
            sequences = historical_visibility + [visibility_scores]
            fusion_results = self.temporal_fusion(sequences[-self.fusion_window:])
            belief = fusion_results["belief"].item()
            uncertainty = fusion_results["uncertainty"].item()
            conflict = fusion_results["conflict"].item()
        
        return {
            "uncertainty": torch.tensor(uncertainty, dtype=torch.float32),
            "ignorance": torch.tensor(1.0 - belief, dtype=torch.float32),
            "conflict": torch.tensor(conflict, dtype=torch.float32),
            "mass_dict": mass
        }
