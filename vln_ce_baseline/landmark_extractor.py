"""
LandmarkExtractor: 从 VLN 指令中提取地标
"""
import re
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class LandmarkExtractor:
    """
    从自然语言指令中提取地标关键词
    用于后续 CLIP 可见性打分
    """
    
    # 常见的地标词类
    LANDMARK_KEYWORDS = {
        'objects': ['door', 'window', 'chair', 'table', 'bed', 'sofa', 'lamp', 
                   'desk', 'shelf', 'counter', 'cabinet', 'wall', 'floor', 'ceiling',
                   'picture', 'painting', 'poster', 'mirror', 'sign', 'plant', 'vase'],
        'locations': ['kitchen', 'bedroom', 'bathroom', 'living room', 'office', 
                     'hallway', 'corridor', 'stairway', 'entrance', 'exit', 'room',
                     'corner', 'center', 'left', 'right', 'front', 'back'],
        'materials': ['wooden', 'metal', 'glass', 'brick', 'carpet', 'tile', 'marble'],
        'colors': ['red', 'blue', 'green', 'yellow', 'white', 'black', 'gray', 'brown']
    }
    
    def __init__(self):
        pass
    
    def extract_from_instruction(self, instruction: str) -> List[str]:
        """
        从指令文本提取地标
        
        Args:
            instruction: VLN 指令文本
            
        Returns:
            landmarks: 地标关键词列表
        """
        instruction_lower = instruction.lower()
        landmarks = []
        
        # 提取所有匹配的地标词
        for category, words in self.LANDMARK_KEYWORDS.items():
            for word in words:
                # 词边界匹配，避免部分匹配
                pattern = r'\b' + re.escape(word) + r'\b'
                if re.search(pattern, instruction_lower):
                    landmarks.append(word)
        
        # 移除重复
        landmarks = list(set(landmarks))
        
        if not landmarks:
            # 如果没有特定地标词，使用通用地标
            landmarks = ['room', 'door', 'furniture']
        
        logger.debug(f"Extracted landmarks: {landmarks}")
        return landmarks
    
    def extract_batch(self, instructions: List[str]) -> List[List[str]]:
        """
        批量提取地标
        
        Args:
            instructions: 指令列表
            
        Returns:
            batch_landmarks: 地标列表的列表
        """
        return [self.extract_from_instruction(instr) for instr in instructions]
    
    def get_landmark_description(self, landmark: str) -> str:
        """
        为地标生成 CLIP 描述（用于文本编码）
        
        Args:
            landmark: 地标词
            
        Returns:
            description: 描述文本
        """
        descriptions = {
            'door': 'a door in the room',
            'window': 'a window',
            'chair': 'a chair',
            'table': 'a table',
            'bed': 'a bed',
            'sofa': 'a sofa or couch',
            'kitchen': 'a kitchen area',
            'bedroom': 'a bedroom',
            'bathroom': 'a bathroom',
            'living room': 'a living room',
        }
        
        return descriptions.get(landmark.lower(), f'a {landmark}')
