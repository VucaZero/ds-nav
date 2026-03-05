"""
VLN-CE 推理过程钩子
在官方 trainer 的 step loop 中插入 DS/CLIP/门控
"""

import torch
import logging
from typing import Dict, Optional, Tuple, Any, List
import numpy as np
import math
import sys
from pathlib import Path
from collections import deque

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
        ten_window: int = 20,
        theta_hysteresis: float = 0.2,
        k_hysteresis: float = 0.2,
        scan_budget: float = 0.45,
        cooldown_steps: int = 10,
    ):
        """
        Args:
            method: "B0"|"B1"|"Ours-R"|"Ours-L"|"TEN-R"|"TEN-L"
            device: "cuda" or "cpu"
        """
        self.method = method
        self.device = device
        self.is_ten_method = method in ["TEN-R", "TEN-L"]
        self.is_ours_method = method in ["Ours-R", "Ours-L", "TEN-R", "TEN-L"]
        
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
                    use_learned_gating=(method in ["Ours-L", "TEN-L"])
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
            "ten_window": ten_window,
            "theta_hysteresis": theta_hysteresis,
            "k_hysteresis": k_hysteresis,
            "scan_budget": scan_budget,
            "cooldown_steps": cooldown_steps,
        }
        self._history_window = max(3, int(ten_window))
        self.visibility_history: deque = deque(maxlen=self._history_window)
        self.theta_history: deque = deque(maxlen=self._history_window)
        self.conflict_history: deque = deque(maxlen=self._history_window)
        self.cooldown_left = 0
        self.trigger_count = 0
        self.stagnation_steps = 0
    
    def reset_episode(self, episode_id: str):
        """重置一个 episode 的状态"""
        self.current_episode_id = episode_id
        self.action_executor = ActionSequenceExecutor(episode_id)
        self.disambiguation_queue = []
        self.visibility_history.clear()
        self.theta_history.clear()
        self.conflict_history.clear()
        self.cooldown_left = 0
        self.trigger_count = 0
        self.stagnation_steps = 0
        logger.debug(f"Reset episode {episode_id}")

    @staticmethod
    def _clip01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _compute_slope(history: deque, current_value: float, tail: int = 5) -> float:
        if not history:
            return 0.0
        arr = list(history)[-min(tail, len(history)) :]
        baseline = float(np.mean(arr))
        return float(current_value - baseline)
    
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
                p_scan=float(queued.get("p_scan", 0.0)),
                p_rewind=float(queued.get("p_rewind", 0.0)),
                budget_left=float(queued.get("budget_left", 1.0)),
                cooldown_left=int(queued.get("cooldown_left", 0)),
                backtrack_target_node=int(queued.get("backtrack_target_node", -1)),
                theta=float(queued.get("theta", 0.0)),
                conflict_k=float(queued.get("conflict_k", 0.0)),
                bel_h=float(queued.get("bel_h", 0.0)),
                bel_not_h=float(queued.get("bel_not_h", 0.0)),
                theta_slope=float(queued.get("theta_slope", 0.0)),
                k_slope=float(queued.get("k_slope", 0.0)),
                ds_uncertainty_raw=float(queued.get("ds_uncertainty_raw", 0.0)),
                conflict_raw=float(queued.get("conflict_raw", 0.0)),
                entropy_norm=float(queued.get("entropy_norm", 0.0)),
                temporal_uncertainty=float(queued.get("temporal_uncertainty", 0.0)),
                temporal_conflict=float(queued.get("temporal_conflict", 0.0)),
                stagnation_steps=int(queued.get("stagnation_steps", 0)),
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
            ds_uncertainty_raw = 0.0
            conflict_raw = 0.0
            ignorance_raw = 0.5
            entropy_norm = 0.0
            theta_slope = 0.0
            k_slope = 0.0
            temporal_uncertainty = 0.0
            temporal_conflict = 0.0
            
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
                
                # DS + 策略熵：TEN 采用时序特征融合，缓解单步硬阈值的不敏感
                probs = torch.softmax(action_logits, dim=-1)
                entropy = -torch.sum(probs * torch.log(probs + 1e-8))
                entropy_norm = (entropy / math.log(action_logits.size(-1))).item()

                if self.is_ours_method:
                    hist_visibility: List[torch.Tensor] = list(self.visibility_history)[-6:]
                    ds_metrics = self.ds_filter(
                        visibility_scores,
                        historical_visibility=hist_visibility if hist_visibility else None,
                    )
                    ds_uncertainty_raw = float(ds_metrics["uncertainty"].item())
                    conflict_raw = float(ds_metrics["conflict"].item())
                    ignorance_raw = float(ds_metrics["ignorance"].item())

                    # 滞回平滑：降低 step-to-step 抖动，让 TEN 对趋势更敏感
                    prev_theta = float(self.theta_history[-1]) if self.theta_history else ds_uncertainty_raw
                    prev_conflict = float(self.conflict_history[-1]) if self.conflict_history else conflict_raw
                    theta_h = float(self.runtime_config["theta_hysteresis"])
                    k_h = float(self.runtime_config["k_hysteresis"])
                    ds_uncertainty = (1.0 - theta_h) * ds_uncertainty_raw + theta_h * prev_theta
                    conflict = (1.0 - k_h) * conflict_raw + k_h * prev_conflict
                    ignorance = ignorance_raw
                    # 冲突校准：抑制 DS 合并后的饱和尖峰，保留可触发区分度
                    conflict = self._clip01(math.sqrt(max(0.0, conflict)) * 0.25)

                    # Ours 系列继续沿用熵下限校准；TEN 在此基础上叠加时序趋势特征
                    uncertainty = max(ds_uncertainty, entropy_norm)
                    if self.is_ten_method:
                        theta_slope = self._compute_slope(self.theta_history, uncertainty)
                        k_slope = self._compute_slope(self.conflict_history, conflict)
                        temporal_uncertainty = self._clip01(
                            uncertainty + 0.12 * max(0.0, theta_slope) + 0.05 * max(0.0, k_slope)
                        )
                        temporal_conflict = self._clip01(
                            conflict + 0.10 * max(0.0, k_slope)
                        )
                        uncertainty = temporal_uncertainty
                        conflict = temporal_conflict
                    else:
                        temporal_uncertainty = uncertainty
                        temporal_conflict = conflict

                    self.visibility_history.append(visibility_scores.detach().cpu())
                    self.theta_history.append(float(uncertainty))
                    self.conflict_history.append(float(conflict))
                else:
                    # B1: 熵门控
                    uncertainty = entropy_norm
                    conflict = 0.0
                    ignorance = uncertainty
                    temporal_uncertainty = uncertainty
                    temporal_conflict = conflict
            else:
                visibility_scores = None
                uncertainty = 0.5
                conflict = 0.0
                ignorance = 0.5
                temporal_uncertainty = uncertainty
                temporal_conflict = conflict
            
            # 门控决策
            if self.is_ours_method:
                use_rule = (self.method in ["Ours-R", "TEN-R"])
                action_type, decision_info = self.disambig_controller.decide(
                    torch.tensor(uncertainty),
                    torch.tensor(conflict),
                    torch.tensor(ignorance),
                    action_logits,
                    use_rule=use_rule
                )
                action_type_name = action_type.name if hasattr(action_type, "name") else str(action_type)
                decision_source = "rule" if use_rule else "learned"

                theta = float(uncertainty)
                conflict_k = float(conflict)
                u_th = float(self.runtime_config["uncertainty_threshold"])
                c_th = float(self.runtime_config["conflict_threshold"])

                if self.is_ten_method:
                    if theta > (u_th + 0.08) and abs(theta_slope) < 0.02:
                        self.stagnation_steps += 1
                    else:
                        self.stagnation_steps = max(0, self.stagnation_steps - 1)

                    temporal_backtrack = (
                        (self.stagnation_steps >= 3 and theta > (u_th + 0.12) and self.trigger_count >= 3 and conflict_k > 0.12)
                        or (conflict_k > (c_th + 0.08))
                    )
                    if temporal_backtrack and action_type != DisambigActionType.BACKTRACK:
                        action_type = DisambigActionType.BACKTRACK
                        action_type_name = "BACKTRACK"
                        decision_source = "ten_temporal_backtrack"

                # TEN 预算与冷却约束
                action_count = len(self.action_executor.action_history)
                current_trigger_rate = (self.trigger_count / action_count) if action_count > 0 else 0.0
                scan_budget = float(self.runtime_config["scan_budget"])
                budget_left = max(0.0, scan_budget - current_trigger_rate)
                in_cooldown = self.is_ten_method and self.cooldown_left > 0
                budget_exhausted = self.is_ten_method and budget_left <= 0.0
                if in_cooldown or budget_exhausted:
                    action_type = DisambigActionType.FOLLOW
                    action_type_name = "FOLLOW"
                    decision_source = "ten_cooldown" if in_cooldown else "ten_budget"
                    if in_cooldown:
                        self.cooldown_left = max(0, self.cooldown_left - 1)

                p_scan = self._clip01(theta + 0.25 * max(0.0, theta_slope))
                p_rewind = self._clip01(conflict_k + 0.35 * max(0.0, k_slope))
                backtrack_target_node = -1
                bel_h = max(0.0, 1.0 - float(uncertainty))
                bel_not_h = min(1.0, float(conflict))

                # BACKTRACK 预算：避免时序规则过度触发导致轨迹爆炸
                if self.is_ten_method and action_type == DisambigActionType.BACKTRACK:
                    bt_count = sum(
                        1 for a in self.action_executor.action_history if a.get("trigger_type") == "BACKTRACK"
                    )
                    bt_rate = (bt_count / action_count) if action_count > 0 else 0.0
                    bt_budget = 0.08
                    if bt_rate >= bt_budget:
                        if theta > u_th:
                            action_type = DisambigActionType.LOOK_AROUND
                            action_type_name = "LOOK_AROUND"
                            decision_source = "ten_bt_budget_to_la"
                        else:
                            action_type = DisambigActionType.FOLLOW
                            action_type_name = "FOLLOW"
                            decision_source = "ten_bt_budget_to_follow"

                # 处理消歧动作
                if action_type == DisambigActionType.FOLLOW:
                    action = raw_action
                    source = "cma"
                    trigger_type = None
                    action_seq = [action]
                    override_reason = None
                    if theta <= u_th:
                        self.stagnation_steps = 0
                else:
                    if action_type == DisambigActionType.LOOK_AROUND:
                        action_seq = ActionPrimitive.get_la_trajectory()
                        trigger_type = "LOOK_AROUND"
                        p_scan = max(p_scan, self._clip01(float(uncertainty)))
                    else:  # BACKTRACK
                        action_seq = ActionPrimitive.get_backtrack_trajectory()
                        trigger_type = "BACKTRACK"
                        p_scan = max(p_scan, self._clip01(float(uncertainty)))
                        p_rewind = max(p_rewind, self._clip01(float(conflict)))

                    action = action_seq[0]
                    # Ours-R / TEN-R 采用单步纠偏，避免长队列导致推理拖慢。
                    if self.method not in ["Ours-R", "TEN-R"]:
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
                                    "p_scan": float(p_scan),
                                    "p_rewind": float(p_rewind),
                                    "budget_left": float(budget_left),
                                    "cooldown_left": int(self.cooldown_left),
                                    "backtrack_target_node": int(backtrack_target_node),
                                    "theta": float(theta),
                                    "conflict_k": float(conflict_k),
                                    "bel_h": float(bel_h),
                                    "bel_not_h": float(bel_not_h),
                                    "theta_slope": float(theta_slope),
                                    "k_slope": float(k_slope),
                                    "ds_uncertainty_raw": float(ds_uncertainty_raw),
                                    "conflict_raw": float(conflict_raw),
                                    "entropy_norm": float(entropy_norm),
                                    "temporal_uncertainty": float(temporal_uncertainty),
                                    "temporal_conflict": float(temporal_conflict),
                                    "stagnation_steps": int(self.stagnation_steps),
                                }
                                for a in action_seq[1:]
                            ]
                        )

                    self.trigger_count += 1
                    if self.is_ten_method:
                        self.cooldown_left = int(self.runtime_config["cooldown_steps"])
                    source = trigger_type.lower()
                    override_reason = f"gate_{trigger_type.lower()}"
                    if trigger_type == "BACKTRACK":
                        backtrack_target_node = 0
                        self.stagnation_steps = 0

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
                    p_scan=p_scan,
                    p_rewind=p_rewind,
                    budget_left=budget_left,
                    cooldown_left=self.cooldown_left,
                    backtrack_target_node=backtrack_target_node,
                    theta=theta,
                    conflict_k=conflict_k,
                    bel_h=bel_h,
                    bel_not_h=bel_not_h,
                    theta_slope=theta_slope,
                    k_slope=k_slope,
                    ds_uncertainty_raw=ds_uncertainty_raw,
                    conflict_raw=conflict_raw,
                    entropy_norm=entropy_norm,
                    temporal_uncertainty=temporal_uncertainty,
                    temporal_conflict=temporal_conflict,
                    stagnation_steps=self.stagnation_steps,
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
                "entropy_norm": entropy_norm,
                "ds_uncertainty_raw": ds_uncertainty_raw,
                "conflict_raw": conflict_raw,
                "temporal_uncertainty": temporal_uncertainty,
                "temporal_conflict": temporal_conflict,
                "theta_slope": theta_slope,
                "k_slope": k_slope,
                "stagnation_steps": self.stagnation_steps,
                "landmarks": landmarks,
                "trigger_type": trigger_type,
                "action_type": action_type_name if self.method in ["Ours-R", "Ours-L", "TEN-R", "TEN-L", "B1"] else "FOLLOW",
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
