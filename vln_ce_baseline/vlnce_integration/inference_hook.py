"""
VLN-CE 推理过程钩子
在官方 trainer 的 step loop 中插入 DS/CLIP/门控
"""

import torch
import logging
from typing import Dict, Optional, Tuple, Any
import numpy as np
import math
import sys
from pathlib import Path

# 处理相对导入
try:
    from ..landmark_extractor import LandmarkExtractor
    from ..evidence_extractor_clip import EvidenceExtractorCLIP
    from ..ds_belief_filter import DSBeliefFilter
    from ..disambig_controller import DisambigController, DisambigActionType
except (ImportError, ValueError):
    # 如果相对导入失败，尝试添加父路径
    parent_dir = str(Path(__file__).parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    try:
        from landmark_extractor import LandmarkExtractor
        from evidence_extractor_clip import EvidenceExtractorCLIP
        from ds_belief_filter import DSBeliefFilter
        from disambig_controller import DisambigController, DisambigActionType
    except ImportError:
        # 如果导入失败，定义 stub 类以允许导入钩子模块本身
        class LandmarkExtractor: pass
        class EvidenceExtractorCLIP: 
            def __init__(self, device="cuda"): pass
        class DSBeliefFilter: 
            def __init__(self, num_actions=8): pass
        class DisambigController: pass
        DisambigActionType = None

from .action_primitives import ActionPrimitive, VLNCEActionType, ActionSequenceExecutor

logger = logging.getLogger(__name__)


class InferenceHook:
    """
    VLN-CE 推理钩子：在每一步注入 DS/CLIP/门控逻辑
    """
    
    _shared_evidence_extractors: Dict[str, Any] = {}

    def __init__(
        self,
        method: str = "B0",
        device: str = "cuda",
        uncertainty_threshold: float = 0.5,
        conflict_threshold: float = 0.3,
    ):
        """
        Args:
            method: "B0"|"B1"|"Ours-R"|"Ours-L"
            device: "cuda" or "cpu"
        """
        self.method = method
        self.device = device
        
        # 初始化模块（按需）
        self.landmark_extractor = LandmarkExtractor()
        
        if method != "B0":
            try:
                if device not in self._shared_evidence_extractors:
                    self._shared_evidence_extractors[device] = EvidenceExtractorCLIP(device=device)
                self.evidence_extractor = self._shared_evidence_extractors[device]
                self.ds_filter = DSBeliefFilter(num_actions=8)
                self.disambig_controller = DisambigController(
                    uncertainty_threshold=uncertainty_threshold,
                    conflict_threshold=conflict_threshold,
                    use_learned_gating=(method == "Ours-L")
                )
                logger.info(f"Initialized {method} modules")
            except Exception as e:
                logger.warning(f"Failed to initialize inference modules: {e}")
                self.evidence_extractor = None
                self.ds_filter = None
                self.disambig_controller = None
        else:
            self.evidence_extractor = None
            self.ds_filter = None
            self.disambig_controller = None
        
        # 状态跟踪
        self.current_episode_id = None
        self.action_executor = None
        self.disambiguation_queue: list = []  # 待执行的消歧动作队列
        self.runtime_config = {
            "uncertainty_threshold": uncertainty_threshold,
            "conflict_threshold": conflict_threshold,
        }
    
    def reset_episode(self, episode_id: str):
        """重置一个 episode 的状态"""
        self.current_episode_id = episode_id
        self.action_executor = ActionSequenceExecutor(episode_id)
        self.disambiguation_queue = []
        logger.debug(f"Reset episode {episode_id}")
    
    def process_step(self,
                    observations: Dict[str, Any],
                    instruction: str,
                    action_logits: torch.Tensor,
                    t: int,
                    episode_id: Optional[str] = None) -> Tuple[int, Dict]:
        """
        推理一步：生成动作并记录信息
        
        Args:
            observations: VLN-CE 环境的观测字典，必含 "rgb"
            instruction: VLN 指令
            action_logits: CMA backbone 输出的动作 logits (1, num_actions)
            t: 当前 timestep
            
        Returns:
            (action_id, debug_info): 最终动作 ID 和调试信息
        """
        # 自动初始化/切换 episode，避免调用方漏掉 reset_episode 导致崩溃
        if episode_id is not None and episode_id != self.current_episode_id:
            self.reset_episode(episode_id)
        elif self.action_executor is None:
            self.reset_episode(self.current_episode_id or "unknown_episode")

        # ============ Step 0: 如果有待执行的消歧动作序列，继续执行 ============
        raw_action = torch.argmax(action_logits).item()
        if self.disambiguation_queue:
            queued = self.disambiguation_queue.pop(0)
            action = int(queued["action"])
            sequence_trigger_type = queued.get("sequence_trigger_type")
            action_type = queued.get("action_type", "FOLLOW")
            self.action_executor.record_action(
                t,
                action,
                source="disambig_queue",
                uncertainty=float(queued.get("uncertainty", 0.0)),
                conflict=float(queued.get("conflict", 0.0)),
                ignorance=float(queued.get("ignorance", 0.0)),
                trigger_type=None,
                action_raw=raw_action,
                action_type=action_type,
                override_reason=f"continue_{(sequence_trigger_type or 'disambig').lower()}_sequence",
                decision_source=queued.get("decision_source", "rule"),
                from_queue=True,
            )
            return action, {
                "source": "disambig_queue",
                "from_queue": True,
                "trigger_type": None,
                "sequence_trigger_type": sequence_trigger_type,
                "action_seq": [action],
                "action_raw": raw_action,
                "action_final": action,
                "action_type": action_type,
            }
        
        # ============ B0: 纯 CMA，无消歧 ============
        if self.method == "B0":
            action = raw_action
            self.action_executor.record_action(
                t,
                action,
                source="cma",
                trigger_type=None,
                action_raw=raw_action,
                action_type="FOLLOW",
                override_reason=None,
                decision_source="none",
            )
            return action, {
                "method": "B0",
                "action": action,
                "trigger_type": None,
                "action_seq": [action],
                "action_raw": raw_action,
                "action_final": action,
                "action_type": "FOLLOW",
            }
        
        # ============ B1+/Ours: 计算不确定性和消歧 ============
        try:
            # 提取地标
            landmarks = self.landmark_extractor.extract_from_instruction(instruction)
            
            # 计算证据（如果有 CLIP）
            if self.evidence_extractor is not None:
                rgb = observations.get("rgb")
                if rgb is not None:
                    if isinstance(rgb, np.ndarray):
                        rgb = torch.from_numpy(rgb)
                    if not isinstance(rgb, torch.Tensor):
                        rgb = torch.tensor(rgb)
                    if rgb.dim() == 3 and rgb.shape[-1] == 3:
                        # HWC -> CHW
                        rgb = rgb.permute(2, 0, 1).contiguous()
                    rgb = rgb.float().to(self.device)

                    landmark_descs = [
                        self.landmark_extractor.get_landmark_description(lm)
                        for lm in landmarks
                    ]
                    
                    # 确保 RGB 形状正确
                    if rgb.dim() == 3:
                        rgb = rgb.unsqueeze(0)
                    
                    visibility_scores = self.evidence_extractor.compute_batch_visibility(
                        rgb, landmarks, landmark_descs
                    )
                    if visibility_scores.dim() == 2:
                        visibility_scores = visibility_scores[0]
                else:
                    visibility_scores = torch.ones(len(landmarks)) * 0.5
                
                # DS 不确定性
                probs = torch.softmax(action_logits, dim=-1)
                entropy = -torch.sum(probs * torch.log(probs + 1e-8))
                entropy_norm = (entropy / math.log(action_logits.size(-1))).item()

                if self.method in ["Ours-R", "Ours-L"]:
                    ds_metrics = self.ds_filter(visibility_scores)
                    ds_uncertainty = ds_metrics["uncertainty"].item()
                    conflict = ds_metrics["conflict"].item()
                    ignorance = ds_metrics["ignorance"].item()
                    # DS uncertainty 在当前数据上量级偏低，使用策略熵作为不确定性下限校准。
                    uncertainty = max(ds_uncertainty, entropy_norm)
                else:
                    # B1: 熵门控
                    uncertainty = entropy_norm
                    conflict = 0.0
                    ignorance = uncertainty
            else:
                visibility_scores = None
                uncertainty = 0.5
                conflict = 0.0
                ignorance = 0.5
            
            # 门控决策
            if self.method in ["Ours-R", "Ours-L"]:
                use_rule = (self.method == "Ours-R")
                action_type, decision_info = self.disambig_controller.decide(
                    torch.tensor(uncertainty),
                    torch.tensor(conflict),
                    torch.tensor(ignorance),
                    action_logits,
                    use_rule=use_rule
                )
                action_type_name = action_type.name if hasattr(action_type, "name") else str(action_type)
                decision_source = "rule" if use_rule else "learned"
                
                # 处理消歧动作
                if action_type == DisambigActionType.FOLLOW:
                    action = raw_action
                    source = "cma"
                    trigger_type = None
                    action_seq = [action]
                    override_reason = None
                else:
                    # 获取消歧动作序列
                    if action_type == DisambigActionType.LOOK_AROUND:
                        action_seq = ActionPrimitive.get_la_trajectory()
                        trigger_type = "LOOK_AROUND"
                    else:  # BACKTRACK
                        action_seq = ActionPrimitive.get_backtrack_trajectory()
                        trigger_type = "BACKTRACK"
                    
                    # 第一个动作立即执行，其余放入队列
                    action = action_seq[0]
                    # Ours-R 在 E2 最小可用阶段采用单步纠偏，避免长队列拖慢推理并稀释触发率统计。
                    if self.method != "Ours-R":
                        self.disambiguation_queue.extend(
                            [
                                {
                                    "action": int(a),
                                    "sequence_trigger_type": trigger_type,
                                    "action_type": action_type_name,
                                    "uncertainty": float(uncertainty),
                                    "conflict": float(conflict),
                                    "ignorance": float(ignorance),
                                    "decision_source": decision_source,
                                }
                                for a in action_seq[1:]
                            ]
                        )
                    source = trigger_type.lower()
                    override_reason = f"gate_{trigger_type.lower()}"
                
                self.action_executor.record_action(
                    t, action, source=source,
                    uncertainty=uncertainty, conflict=conflict,
                    ignorance=ignorance,
                    trigger_type=trigger_type,
                    action_raw=raw_action,
                    action_type=action_type_name,
                    override_reason=override_reason,
                    decision_source=decision_source,
                    from_queue=False,
                )
            else:
                # B1: 简单熵门控
                b1_threshold = self.runtime_config["uncertainty_threshold"]
                if uncertainty > b1_threshold:
                    action_seq = ActionPrimitive.get_la_trajectory()
                    action = action_seq[0]
                    self.disambiguation_queue.extend(
                        [
                            {
                                "action": int(a),
                                "sequence_trigger_type": "LOOK_AROUND",
                                "action_type": "LOOK_AROUND",
                                "uncertainty": float(uncertainty),
                                "conflict": float(conflict),
                                "ignorance": float(ignorance),
                                "decision_source": "entropy_rule",
                            }
                            for a in action_seq[1:]
                        ]
                    )
                    trigger_type = "LOOK_AROUND"
                    action_type_name = "LOOK_AROUND"
                    override_reason = "entropy_gt_threshold"
                else:
                    action = raw_action
                    action_seq = [action]
                    trigger_type = None
                    action_type_name = "FOLLOW"
                    override_reason = None
                
                self.action_executor.record_action(
                    t, action, source="b1_entropy",
                    uncertainty=uncertainty,
                    conflict=conflict,
                    ignorance=ignorance,
                    trigger_type=trigger_type,
                    action_raw=raw_action,
                    action_type=action_type_name,
                    override_reason=override_reason,
                    decision_source="entropy_rule",
                    from_queue=False,
                )
                decision_source = "entropy_rule"
            
            debug_info = {
                "method": self.method,
                "action": action,
                "action_raw": raw_action,
                "action_final": action,
                "uncertainty": uncertainty,
                "conflict": conflict,
                "ignorance": ignorance,
                "landmarks": landmarks,
                "trigger_type": trigger_type,
                "action_type": action_type_name if self.method in ["Ours-R", "Ours-L", "B1"] else "FOLLOW",
                "decision_source": decision_source,
                "action_seq": action_seq,
            }
            
            return action, debug_info
        
        except Exception as e:
            logger.error(f"Error in process_step: {e}")
            action = raw_action
            if self.action_executor is not None:
                self.action_executor.record_action(
                    t,
                    action,
                    source="error_fallback",
                    uncertainty=0.0,
                    conflict=0.0,
                    ignorance=0.0,
                    trigger_type=None,
                    action_raw=raw_action,
                    action_type="FOLLOW",
                    override_reason="exception_fallback_to_cma",
                    decision_source="error_fallback",
                    from_queue=False,
                )
            return action, {
                "error": str(e),
                "fallback_to_cma": True,
                "trigger_type": None,
                "action_seq": [action],
                "action_raw": raw_action,
                "action_final": action,
                "action_type": "FOLLOW",
            }
    
    def get_episode_log(self) -> Dict:
        """获取当前 episode 的完整日志"""
        if self.action_executor is None:
            return {}
        
        override_log = self.action_executor.get_override_log()
        action_history = self.action_executor.action_history
        action_count = len(action_history)
        disambig_count = len(override_log)
        trigger_rate = (disambig_count / action_count) if action_count > 0 else 0.0

        return {
            "episode_id": self.current_episode_id,
            "method": self.method,
            "action_count": action_count,
            "la_count": sum(1 for a in override_log if a["trigger_type"] == "LOOK_AROUND"),
            "bt_count": sum(1 for a in override_log if a["trigger_type"] == "BACKTRACK"),
            "disambig_count": disambig_count,
            "trigger_rate": trigger_rate,
            "runtime_config": self.runtime_config,
            "override_log": override_log,
            "step_log": action_history,
            "action_sequence": self.action_executor.get_action_sequence(),
            "controller_stats": (
                self.disambig_controller.get_statistics()
                if self.disambig_controller is not None
                else {}
            ),
        }
