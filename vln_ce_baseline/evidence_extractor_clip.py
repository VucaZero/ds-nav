"""
EvidenceExtractorCLIP: 使用冻结的 OpenCLIP 从 RGB 和地标计算可见性证据
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional, Union
import logging
import open_clip

logger = logging.getLogger(__name__)


class EvidenceExtractorCLIP(nn.Module):
    """
    使用 OpenCLIP ViT-B/32 计算地标可见性分数
    冻结 CLIP，仅用于特征提取和相似度计算
    """
    
    def __init__(self, model_name: str = "ViT-B-32", pretrained: str = "openai", device: str = "cuda"):
        """
        Args:
            model_name: OpenCLIP 模型名称（推荐轻量级）
            pretrained: 预训练权重来源
            device: 设备
        """
        super().__init__()
        self.device = device
        
        # 加载 OpenCLIP 模型（轻量级 ViT-B/32）
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name=model_name,
            pretrained=pretrained,
            device=device
        )
        self.tokenizer = open_clip.get_tokenizer(model_name)
        
        # 冻结 CLIP 权重
        for param in self.model.parameters():
            param.requires_grad = False
        self.model.eval()
        
        logger.info(f"Loaded OpenCLIP {model_name} (pretrained={pretrained}) - frozen")
    
    @torch.no_grad()
    def encode_image(self, rgb_images: torch.Tensor) -> torch.Tensor:
        """
        编码 RGB 图像为视觉特征
        
        Args:
            rgb_images: (batch_size, 3, H, W) 或 (3, H, W)
            
        Returns:
            image_features: (batch_size, embedding_dim) 归一化特征
        """
        if rgb_images.dim() == 3:
            rgb_images = rgb_images.unsqueeze(0)
        
        # 移至设备
        rgb_images = rgb_images.to(self.device)
        
        # 应用预处理（resize 到 224x224）
        if rgb_images.shape[-2:] != (224, 224):
            rgb_images = F.interpolate(
                rgb_images,
                size=(224, 224),
                mode='bilinear',
                align_corners=False
            )
        
        # 确保 RGB 值在 [0, 1] 范围内
        if rgb_images.max() > 1.0:
            rgb_images = rgb_images / 255.0
        
        # CLIP 编码
        image_features = self.model.encode_image(rgb_images)
        image_features = F.normalize(image_features, dim=-1)
        
        return image_features
    
    @torch.no_grad()
    def encode_text(self, texts: Union[str, List[str]]) -> torch.Tensor:
        """
        编码文本描述为语义特征
        
        Args:
            texts: 单个文本或文本列表
            
        Returns:
            text_features: (num_texts, embedding_dim) 归一化特征
        """
        if isinstance(texts, str):
            texts = [texts]
        
        # 令牌化并编码
        text_tokens = self.tokenizer(texts).to(self.device)
        text_features = self.model.encode_text(text_tokens)
        text_features = F.normalize(text_features, dim=-1)
        
        return text_features
    
    def compute_visibility_evidence(self, 
                                   rgb_image: torch.Tensor, 
                                   landmark: str,
                                   landmark_description: str) -> float:
        """
        计算单个地标在当前观测中的可见性分数
        
        Args:
            rgb_image: (3, H, W) RGB 图像
            landmark: 地标名称
            landmark_description: 地标描述（用于 CLIP 编码）
            
        Returns:
            visibility_score: [0, 1] 可见性分数
        """
        # 编码图像
        image_feat = self.encode_image(rgb_image)  # (1, embedding_dim)
        
        # 编码地标描述
        text_feat = self.encode_text(landmark_description)  # (1, embedding_dim)
        
        # 计算相似度（余弦）
        similarity = (image_feat @ text_feat.t()).item()  # (1, 1) -> scalar
        
        # 映射到 [0, 1]
        visibility_score = max(0.0, min(1.0, (similarity + 1.0) / 2.0))
        
        return visibility_score
    
    def compute_batch_visibility(self, 
                                rgb_images: torch.Tensor,
                                landmarks: List[str],
                                landmark_descriptions: List[str]) -> torch.Tensor:
        """
        批量计算多个地标的可见性
        
        Args:
            rgb_images: (batch_size, 3, H, W) RGB 图像
            landmarks: 地标列表
            landmark_descriptions: 地标描述列表
            
        Returns:
            visibility_matrix: (batch_size, num_landmarks) 可见性矩阵
        """
        batch_size = rgb_images.size(0)
        num_landmarks = len(landmarks)
        
        # 编码所有图像
        image_features = self.encode_image(rgb_images)  # (batch_size, embedding_dim)
        
        # 编码所有地标描述
        text_features = self.encode_text(landmark_descriptions)  # (num_landmarks, embedding_dim)
        
        # 计算相似度矩阵
        similarity_matrix = image_features @ text_features.t()  # (batch_size, num_landmarks)
        
        # 映射到 [0, 1]
        visibility_matrix = torch.clamp((similarity_matrix + 1.0) / 2.0, 0.0, 1.0)
        
        return visibility_matrix
