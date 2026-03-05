"""
DisambigController: 主动消歧动作策略
实现 FOLLOW / LOOK-AROUND / BACKTRACK 三类高层策略
"""
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple, Optional, Literal
from enum import IntEnum
import logging

logger = logging.getLogger(__name__)


class DisambigActionType(IntEnum):
    """消歧动作类型"""
    FOLLOW = 0         # 跟随 CMA 动作
    LOOK_AROUND = 1    # 四周观察 (LA-90: 15°×6 来回扫描)
    BACKTRACK = 2      # 回退 (180° + 0.25m forward + 180°)


class LAConfiguration:
    """LOOK-AROUND 动作配置"""
    def __init__(self, angle_step: float = 15.0, num_steps: int = 6):
        """
        Args:
            angle_step: 每步旋转角度（度）
            num_steps: 单向步数
        """
        self.angle_step = angle_step
        self.num_steps = num_steps  # 6 步 x 15° = 90°
        self.total_angle = angle_step * num_steps  # 90°
    
    def get_trajectory(self) -> List[Tuple[str, float]]:
        """
        生成 LA-90 轨迹：左扫 -> 回正 -> 右扫 -> 回正
        
        Returns:
            trajectory: [(action_type, value), ...] 列表
        """
        trajectory = []
        
        # 向左扫描
        for i in range(self.num_steps):
            trajectory.append(("TURN", -self.angle_step))
        
        # 回正
        trajectory.append(("TURN", self.total_angle))
        
        # 向右扫描
        for i in range(self.num_steps):
            trajectory.append(("TURN", self.angle_step))
        
        # 回正
        trajectory.append(("TURN", -self.total_angle))
        
        return trajectory


class BTConfiguration:
    """BACKTRACK 动作配置"""
    def __init__(self, forward_distance: float = 0.25):
        """
        Args:
            forward_distance: 回退时的前进距离（米）
        """
        self.forward_distance = forward_distance
    
    def get_trajectory(self) -> List[Tuple[str, float]]:
        """
        生成 BACKTRACK 轨迹：180° + 0.25m + 180°
        
        Returns:
            trajectory: [(action_type, value), ...]
        """
        trajectory = [
            ("TURN", 180.0),
            ("FORWARD", self.forward_distance),
            ("TURN", 180.0)
        ]
        return trajectory


class DisambigController(nn.Module):
    """
    高层消歧动作控制器
    
    策略：
    - 基于不确定性度量和证据冲突决定是否触发消歧
    - 三类动作：FOLLOW (CMA决策) / LOOK-AROUND (探索) / BACKTRACK (退避)
    """
    
    def __init__(self, 
                 uncertainty_threshold: float = 0.5,
                 conflict_threshold: float = 0.3,
                 use_learned_gating: bool = False,
                 hidden_dim: int = 128):
        """
        Args:
            uncertainty_threshold: 触发消歧的不确定性阈值
            conflict_threshold: 触发消歧的冲突阈值
            use_learned_gating: 是否使用学习的门控网络（Ours-L）
            hidden_dim: 学习网络的隐层维度
        """
        super().__init__()
        self.uncertainty_threshold = uncertainty_threshold
        self.conflict_threshold = conflict_threshold
        self.use_learned_gating = use_learned_gating
        
        # 配置
        self.la_config = LAConfiguration(angle_step=15.0, num_steps=6)
        self.bt_config = BTConfiguration(forward_distance=0.25)
        
        # 学习门控网络（可选，参数 < 1M）
        if use_learned_gating:
            # 输入：不确定性度量 (3) + 动作子集 (3) = 6 维
            # 输出：3 类消歧动作的概率
            self.gating_net = nn.Sequential(
                nn.Linear(6, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, 3),  # [FOLLOW, LA, BT]
            )
        else:
            self.gating_net = None
        
        # 统计信息
        self.stats = {
            "follow_count": 0,
            "la_count": 0,
            "bt_count": 0,
            "total_steps": 0,
            "disambig_triggered": 0,
            "u_before_list": [],
            "u_after_list": [],
            "c_before_list": [],
            "c_after_list": [],
        }
    
    def rule_based_decision(self, 
                           uncertainty: torch.Tensor,
                           conflict: torch.Tensor,
                           ignorance: torch.Tensor) -> DisambigActionType:
        """
        规则门控决策：基于阈值的规则
        
        Args:
            uncertainty: 不确定性度量
            conflict: 证据冲突度量
            ignorance: 无知度量
            
        Returns:
            action_type: 消歧动作类型
        """
        u = uncertainty.item() if isinstance(uncertainty, torch.Tensor) else uncertainty
        c = conflict.item() if isinstance(conflict, torch.Tensor) else conflict
        
        # 规则：high uncertainty or high conflict -> 消歧
        if u > self.uncertainty_threshold and c > self.conflict_threshold:
            # 冲突情况：倾向 BACKTRACK
            return DisambigActionType.BACKTRACK
        elif u > self.uncertainty_threshold:
            # 单纯不确定：倾向 LOOK-AROUND
            return DisambigActionType.LOOK_AROUND
        else:
            # 低不确定性：跟随 CMA
            return DisambigActionType.FOLLOW
    
    def learned_decision(self, 
                        uncertainty: torch.Tensor,
                        conflict: torch.Tensor,
                        ignorance: torch.Tensor,
                        action_logits: torch.Tensor,
                        temperature: float = 1.0) -> DisambigActionType:
        """
        学习门控决策：通过小网络学习
        
        Args:
            uncertainty: 不确定性
            conflict: 冲突
            ignorance: 无知
            action_logits: CMA 的动作 logits
            temperature: 温度参数
            
        Returns:
            action_type: 消歧动作类型
        """
        # 组合特征
        if action_logits.dim() > 1:
            action_logits = action_logits.squeeze(0)
        
        # 确保所有张量在同一设备上
        device = action_logits.device
        u_val = uncertainty.unsqueeze(0) if uncertainty.dim() == 0 else uncertainty
        u_val = u_val.to(device)
        c_val = conflict.unsqueeze(0) if conflict.dim() == 0 else conflict
        c_val = c_val.to(device)
        ig_val = ignorance.unsqueeze(0) if ignorance.dim() == 0 else ignorance
        ig_val = ig_val.to(device)
        
        # 只取前 3 个动作 logits（以保证总维度为 6）
        action_subset = action_logits[:3]
        
        features = torch.cat([
            u_val,
            c_val,
            ig_val,
            action_subset  # 3 个动作 logits
        ])
        
        # 确保网络在同一设备上
        if self.gating_net is not None:
            self.gating_net = self.gating_net.to(device)
        
        # 通过学习网络
        logits = self.gating_net(features.unsqueeze(0) if features.dim() == 1 else features)
        if logits.dim() > 1:
            logits = logits.squeeze(0)
        probs = torch.softmax(logits / temperature, dim=-1)
        
        # 采样或取最大值
        action_type = torch.argmax(probs).item()
        return DisambigActionType(action_type)
    
    def decide(self, 
               uncertainty: torch.Tensor,
               conflict: torch.Tensor,
               ignorance: torch.Tensor,
               action_logits: Optional[torch.Tensor] = None,
               use_rule: bool = True) -> Tuple[DisambigActionType, Dict]:
        """
        决策主入口
        
        Args:
            uncertainty: 不确定性度量
            conflict: 冲突度量
            ignorance: 无知度量
            action_logits: CMA 动作 logits（用于学习门控）
            use_rule: 是否使用规则门控（否则用学习门控）
            
        Returns:
            action_type: 消歧动作类型
            decision_info: 决策信息字典
        """
        # 记录触发前的 U/C
        u = uncertainty.item() if isinstance(uncertainty, torch.Tensor) else uncertainty
        c = conflict.item() if isinstance(conflict, torch.Tensor) else conflict
        self.stats["u_before_list"].append(u)
        self.stats["c_before_list"].append(c)
        
        # 决策
        if use_rule or not self.use_learned_gating:
            action_type = self.rule_based_decision(uncertainty, conflict, ignorance)
        else:
            action_type = self.learned_decision(uncertainty, conflict, ignorance, action_logits)
        
        # 更新统计
        self.stats["total_steps"] += 1
        if action_type != DisambigActionType.FOLLOW:
            self.stats["disambig_triggered"] += 1
        
        decision_info = {
            "action_type": action_type,
            "uncertainty": u,
            "conflict": c,
            "ignorance": ignorance.item() if isinstance(ignorance, torch.Tensor) else ignorance,
        }
        
        return action_type, decision_info
    
    def get_trajectory(self, action_type: DisambigActionType) -> List[Tuple[str, float]]:
        """
        根据动作类型获取执行轨迹
        
        Args:
            action_type: 消歧动作类型
            
        Returns:
            trajectory: [(action_name, value), ...]
        """
        if action_type == DisambigActionType.LOOK_AROUND:
            self.stats["la_count"] += 1
            return self.la_config.get_trajectory()
        elif action_type == DisambigActionType.BACKTRACK:
            self.stats["bt_count"] += 1
            return self.bt_config.get_trajectory()
        else:  # FOLLOW
            self.stats["follow_count"] += 1
            return [("FOLLOW", 1.0)]
    
    def get_statistics(self) -> Dict:
        """获取运行统计信息"""
        stats_copy = self.stats.copy()
        
        # 计算平均值
        if stats_copy["u_before_list"]:
            stats_copy["avg_u_before"] = np.mean(stats_copy["u_before_list"])
            stats_copy["avg_u_after"] = np.mean(stats_copy["u_after_list"]) if stats_copy["u_after_list"] else 0.0
        
        if stats_copy["c_before_list"]:
            stats_copy["avg_c_before"] = np.mean(stats_copy["c_before_list"])
            stats_copy["avg_c_after"] = np.mean(stats_copy["c_after_list"]) if stats_copy["c_after_list"] else 0.0
        
        stats_copy["disambig_rate"] = (
            stats_copy["disambig_triggered"] / stats_copy["total_steps"] 
            if stats_copy["total_steps"] > 0 else 0.0
        )
        
        return stats_copy
