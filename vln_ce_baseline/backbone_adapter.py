"""
BackboneAdapter: 封装 CMA 模型并提供统一接口
"""
import torch
import torch.nn as nn
from typing import Dict, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BackboneAdapter(nn.Module):
    """
    适配 VLN-CE CMA 模型的包装器
    - 不修改网络结构
    - 冻结主干模型权重
    - 提供统一的特征提取和动作预测接口
    """
    
    def __init__(self, cma_model: nn.Module, freeze_backbone: bool = True):
        """
        Args:
            cma_model: 预训练的 CMA 模型
            freeze_backbone: 是否冻结主干模型
        """
        super().__init__()
        self.cma_model = cma_model
        self.freeze_backbone = freeze_backbone
        
        if freeze_backbone:
            for param in self.cma_model.parameters():
                param.requires_grad = False
            logger.info("CMA backbone frozen")
        else:
            logger.warning("CMA backbone NOT frozen - be careful with gradients")
    
    def forward(self, observations: Dict[str, torch.Tensor]) -> Tuple[torch.Tensor, Dict[str, Any]]:
        """
        前向传播
        
        Args:
            observations: 包含 RGB/depth/instruction 等的观测字典
            
        Returns:
            action_logits: (batch_size, num_actions) 动作 logits
            features: 中间特征字典，用于后续不确定性计算
        """
        with torch.no_grad() if self.freeze_backbone else torch.enable_grad():
            # 调用 CMA 模型的前向传播
            outputs = self.cma_model(observations)
        
        # 解析模型输出
        if isinstance(outputs, dict):
            action_logits = outputs.get("action_logits", outputs.get("logits"))
            features = {k: v for k, v in outputs.items() if k != "action_logits" and k != "logits"}
        else:
            # 假设输出是 logits
            action_logits = outputs
            features = {}
        
        return action_logits, features
    
    def get_action_space_size(self) -> int:
        """获取动作空间大小（含消歧动作）"""
        # VLN-CE 标准动作数 + 3 个消歧动作 (LA, BT, explicit FOLLOW)
        # 假设 CMA 有 ~8-12 个基本动作
        base_actions = 8
        return base_actions
    
    def get_backbone_params_count(self) -> int:
        """获取主干模型参数数量"""
        return sum(p.numel() for p in self.cma_model.parameters())
