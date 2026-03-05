"""
IntegratedPipeline: 集成所有模块的推理管道
支持 4 种方法：B0 (CMA), B1 (Entropy), Ours-R (DS+Rule), Ours-L (DS+Learn)
"""
import torch
import torch.nn as nn
from typing import Dict, List, Optional, Tuple, Literal
import logging
import math
from enum import Enum

from .backbone_adapter import BackboneAdapter
from .landmark_extractor import LandmarkExtractor
from .evidence_extractor_clip import EvidenceExtractorCLIP
from .ds_belief_filter import DSBeliefFilter
from .disambig_controller import DisambigController, DisambigActionType
from .logger import EpisodeLogger, EvaluationLogger

logger = logging.getLogger(__name__)


class MethodType(str, Enum):
    """评估方法类型"""
    B0 = "B0"           # CMA 原始
    B1 = "B1"           # Entropy gating (非 DS)
    OURS_R = "Ours-R"   # DS + 规则门控
    OURS_L = "Ours-L"   # DS + 学习门控


class IntegratedPipeline(nn.Module):
    """
    完整推理管道
    """
    
    def __init__(self, 
                 cma_model: nn.Module,
                 method_type: MethodType = MethodType.OURS_R,
                 device: str = "cuda" if torch.cuda.is_available() else "cpu",
                 **kwargs):
        """
        Args:
            cma_model: 预训练的 CMA 模型
            method_type: 评估方法 (B0/B1/Ours-R/Ours-L)
            device: 设备
            **kwargs: 其他配置参数
        """
        super().__init__()
        self.device = device
        self.method_type = method_type
        
        # 1. Backbone 适配器
        self.backbone = BackboneAdapter(cma_model, freeze_backbone=True)
        
        # 2. 地标提取器
        self.landmark_extractor = LandmarkExtractor()
        
        # 3. CLIP 证据提取器（仅用于非 B0 方法）
        if method_type != MethodType.B0:
            try:
                self.evidence_extractor = EvidenceExtractorCLIP(device=device)
            except Exception as e:
                logger.warning(f"Failed to load EvidenceExtractorCLIP: {e}. Using dummy.")
                self.evidence_extractor = None
        else:
            self.evidence_extractor = None
        
        # 4. DS 信念滤波器（仅用于 Ours-R/L）
        if method_type in [MethodType.OURS_R, MethodType.OURS_L]:
            self.ds_filter = DSBeliefFilter(num_actions=8)
        else:
            self.ds_filter = None
        
        # 5. 消歧控制器（仅用于 Ours-R/L）
        if method_type in [MethodType.OURS_R, MethodType.OURS_L]:
            use_learn = (method_type == MethodType.OURS_L)
            self.disambig_controller = DisambigController(
                uncertainty_threshold=0.5,
                conflict_threshold=0.3,
                use_learned_gating=use_learn
            )
        else:
            self.disambig_controller = None
        
        # 6. 日志记录器
        self.logger = None
        
        logger.info(f"IntegratedPipeline initialized with method: {method_type}")
    
    def forward(self, 
               observations: Dict[str, torch.Tensor],
               instruction: str,
               episode_id: Optional[str] = None) -> Dict:
        """
        前向推理
        
        Args:
            observations: 观测字典（RGB, depth, etc.)
            instruction: VLN 指令文本
            episode_id: 可选的 episode ID（用于日志）
            
        Returns:
            result: 包含动作决策和调试信息的字典
        """
        # ============ Step 1: CMA 骨干推理 ============
        action_logits, features = self.backbone(observations)
        
        if self.method_type == MethodType.B0:
            # B0: 直接使用 CMA 输出
            action = torch.argmax(action_logits, dim=-1)
            result = {
                "method": "B0",
                "action": action.item(),
                "action_logits": action_logits,
                "confidence": torch.max(torch.softmax(action_logits, dim=-1)).item(),
                "disambig_action": None,
            }
            return result
        
        # ============ Step 2: 地标和证据提取（B1, Ours-R/L） ============
        landmarks = self.landmark_extractor.extract_from_instruction(instruction)
        
        if self.evidence_extractor is None:
            # 无 CLIP，使用虚拟证据
            visibility_scores = torch.ones(len(landmarks), device=self.device) * 0.5
            uncertainty = torch.tensor(0.5, device=self.device)
            conflict = torch.tensor(0.0, device=self.device)
            ignorance = torch.tensor(0.5, device=self.device)
        else:
            # ============ Step 3: CLIP 可见性计算 ============
            rgb_image = observations.get("rgb", observations.get("image"))
            if rgb_image is not None:
                # 提取地标描述
                landmark_descs = [
                    self.landmark_extractor.get_landmark_description(lm) 
                    for lm in landmarks
                ]
                
                # 计算可见性
                visibility_scores = self.evidence_extractor.compute_batch_visibility(
                    rgb_image.unsqueeze(0) if rgb_image.dim() == 3 else rgb_image,
                    landmarks,
                    landmark_descs
                )
                
                if visibility_scores.dim() == 2:
                    visibility_scores = visibility_scores[0]
            else:
                visibility_scores = torch.ones(len(landmarks), device=self.device) * 0.5
            
            # ============ Step 4: DS 不确定性计算（Ours-R/L） ============
            if self.method_type in [MethodType.OURS_R, MethodType.OURS_L]:
                ds_metrics = self.ds_filter(visibility_scores)
                uncertainty = ds_metrics["uncertainty"]
                conflict = ds_metrics["conflict"]
                ignorance = ds_metrics["ignorance"]
            else:
                # B1: 使用熵作为不确定性度量
                probs = torch.softmax(action_logits, dim=-1)
                entropy = -torch.sum(probs * torch.log(probs + 1e-8))
                uncertainty = entropy / math.log(action_logits.size(-1))
                conflict = torch.tensor(0.0, device=action_logits.device)
                ignorance = uncertainty
        
        # ============ Step 5: 消歧决策（Ours-R/L）============
        if self.method_type in [MethodType.OURS_R, MethodType.OURS_L]:
            use_rule = (self.method_type == MethodType.OURS_R)
            disambig_action_type, decision_info = self.disambig_controller.decide(
                uncertainty=uncertainty,
                conflict=conflict,
                ignorance=ignorance,
                action_logits=action_logits,
                use_rule=use_rule
            )
            
            # 如果决定消歧，获取轨迹（这里简化为返回标记）
            if disambig_action_type != DisambigActionType.FOLLOW:
                trajectory = self.disambig_controller.get_trajectory(disambig_action_type)
                action = -int(disambig_action_type)  # 负数表示消歧动作
                disambig_info = {
                    "type": disambig_action_type.name,
                    "trajectory": trajectory,
                }
            else:
                action = torch.argmax(action_logits, dim=-1).item()
                disambig_info = None
        else:
            # B1: 如果熵过高，触发消歧（简化）
            if uncertainty > 0.5:
                action = -1  # 标记为 LOOK_AROUND
                disambig_info = {"type": "LOOK_AROUND"}
            else:
                action = torch.argmax(action_logits, dim=-1).item()
                disambig_info = None
        
        # ============ 组织输出 ============
        result = {
            "method": self.method_type.value,
            "action": action,
            "action_logits": action_logits,
            "confidence": torch.max(torch.softmax(action_logits, dim=-1)).item(),
            "uncertainty": uncertainty.item() if isinstance(uncertainty, torch.Tensor) else uncertainty,
            "conflict": conflict.item() if isinstance(conflict, torch.Tensor) else conflict,
            "ignorance": ignorance.item() if isinstance(ignorance, torch.Tensor) else ignorance,
            "visibility_scores": visibility_scores.cpu().numpy() if isinstance(visibility_scores, torch.Tensor) else visibility_scores,
            "landmarks": landmarks,
            "disambig_action": disambig_info,
            "decision_info": decision_info if self.method_type in [MethodType.OURS_R, MethodType.OURS_L] else None,
        }
        
        return result
    
    def reset_statistics(self):
        """重置统计信息"""
        if self.disambig_controller is not None:
            self.disambig_controller.stats = {
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
    
    def get_statistics(self) -> Dict:
        """获取当前统计信息"""
        if self.disambig_controller is not None:
            return self.disambig_controller.get_statistics()
        return {}
