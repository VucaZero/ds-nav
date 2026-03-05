"""
VLN-CE 动作空间与原语映射
将消歧动作（LA-90, BACKTRACK）映射到官方 VLN-CE 环境的 action IDs
"""

from enum import IntEnum
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)


class VLNCEActionType(IntEnum):
    """
    VLN-CE 官方动作类型（来自 habitat.tasks.vln.vln）
    标准 agent action space: 0=STOP, 1=MoveForward, 2=TurnLeft, 3=TurnRight
    """
    STOP = 0
    MOVE_FORWARD = 1
    TURN_LEFT = 2
    TURN_RIGHT = 3


class ActionPrimitive:
    """
    高层消歧动作到低层 VLN-CE 动作序列的映射
    """
    
    # 轻量 LOOK-AROUND：小范围左扫/右扫并回正，避免过长队列拖慢推理。
    # 每个转身对应 TURN_LEFT 或 TURN_RIGHT（1 次 step = 1 个动作）
    LA_90_TRAJECTORY = [
        # 向左扫 (2 步)
        VLNCEActionType.TURN_LEFT,
        VLNCEActionType.TURN_LEFT,
        # 右扫并跨过中点 (4 步)
        VLNCEActionType.TURN_RIGHT,
        VLNCEActionType.TURN_RIGHT,
        VLNCEActionType.TURN_RIGHT,
        VLNCEActionType.TURN_RIGHT,
        # 回正 (2 步)
        VLNCEActionType.TURN_LEFT,
        VLNCEActionType.TURN_LEFT,
    ]
    
    # BACKTRACK: 转身180° (6步) + 前进0.25m (1步) + 转身180° (6步)
    # 注：VLN-CE 中转身角度由环境参数控制，这里假设 1 step = ~30° 转身
    BACKTRACK_TRAJECTORY = [
        # 转身 180° (6 步左转)
        VLNCEActionType.TURN_LEFT,
        VLNCEActionType.TURN_LEFT,
        VLNCEActionType.TURN_LEFT,
        VLNCEActionType.TURN_LEFT,
        VLNCEActionType.TURN_LEFT,
        VLNCEActionType.TURN_LEFT,
        # 前进 0.25m (1 步)
        VLNCEActionType.MOVE_FORWARD,
        # 转身 180° (6 步右转)
        VLNCEActionType.TURN_RIGHT,
        VLNCEActionType.TURN_RIGHT,
        VLNCEActionType.TURN_RIGHT,
        VLNCEActionType.TURN_RIGHT,
        VLNCEActionType.TURN_RIGHT,
        VLNCEActionType.TURN_RIGHT,
    ]
    
    @staticmethod
    def get_la_trajectory() -> List[int]:
        """获取 LOOK-AROUND-90 动作序列"""
        return list(ActionPrimitive.LA_90_TRAJECTORY)
    
    @staticmethod
    def get_backtrack_trajectory() -> List[int]:
        """获取 BACKTRACK 动作序列"""
        return list(ActionPrimitive.BACKTRACK_TRAJECTORY)
    
    @staticmethod
    def get_action_name(action_id: int) -> str:
        """获取动作名称"""
        try:
            return VLNCEActionType(action_id).name
        except ValueError:
            return f"UNKNOWN({action_id})"


class ActionSequenceExecutor:
    """
    管理动作序列的执行和日志记录
    """
    
    def __init__(self, episode_id: str):
        """
        Args:
            episode_id: 当前 episode ID
        """
        self.episode_id = episode_id
        self.action_history: List[Dict] = []
    
    def record_action(
        self,
        t: int,
        action: int,
        source: str = "cma",
        uncertainty: float = 0.0,
        conflict: float = 0.0,
        ignorance: float = 0.0,
        trigger_type: str = None,
        action_raw: int = None,
        action_type: str = "FOLLOW",
        override_reason: str = None,
        decision_source: str = "rule",
        from_queue: bool = False,
        p_scan: float = 0.0,
        p_rewind: float = 0.0,
        budget_left: float = 1.0,
        cooldown_left: int = 0,
        backtrack_target_node: int = -1,
        theta: float = 0.0,
        conflict_k: float = 0.0,
        bel_h: float = 0.0,
        bel_not_h: float = 0.0,
        theta_slope: float = 0.0,
        k_slope: float = 0.0,
        ds_uncertainty_raw: float = 0.0,
        conflict_raw: float = 0.0,
        entropy_norm: float = 0.0,
        temporal_uncertainty: float = 0.0,
        temporal_conflict: float = 0.0,
        stagnation_steps: int = 0,
        topo_node_id: int = -1,
        frontier_count: int = 0,
        visited_count: int = 0,
    ):
        """
        记录一个动作执行
        
        Args:
            t: timestep
            action: 最终动作 ID
            source: 动作来源 ("cma", "la", "bt")
            uncertainty: 不确定性度量（用于消歧触发的动作）
            conflict: 冲突度量
            ignorance: 无知度量
            trigger_type: 消歧触发类型 ("LOOK_AROUND", "BACKTRACK")
            action_raw: CMA 原始动作 ID，默认与最终动作相同
            action_type: 门控动作类型 ("FOLLOW"/"LOOK_AROUND"/"BACKTRACK")
            override_reason: 覆盖原因
            decision_source: 决策来源
            from_queue: 是否来自已入队消歧序列
        """
        raw_action = action if action_raw is None else action_raw
        override = (raw_action != action) or from_queue or (trigger_type is not None)

        self.action_history.append({
            "t": t,
            "episode_id": self.episode_id,
            "action_id": action,  # backward-compatible alias (final action)
            "action_name": ActionPrimitive.get_action_name(action),  # final action name
            "action_raw_id": raw_action,
            "action_raw_name": ActionPrimitive.get_action_name(raw_action),
            "action_final_id": action,
            "action_final_name": ActionPrimitive.get_action_name(action),
            "override": override,
            "override_reason": override_reason,
            "source": source,
            "uncertainty": uncertainty,
            "conflict": conflict,
            "ignorance": ignorance,
            "action_type": action_type,
            "decision_source": decision_source,
            "from_queue": from_queue,
            "trigger_type": trigger_type,
            "p_scan": float(p_scan),
            "p_rewind": float(p_rewind),
            "budget_left": float(budget_left),
            "cooldown_left": int(cooldown_left),
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
            "stagnation_steps": int(stagnation_steps),
            "topo_node_id": int(topo_node_id),
            "frontier_count": int(frontier_count),
            "visited_count": int(visited_count),
        })
    
    def get_override_log(self) -> List[Dict]:
        """
        获取动作覆盖日志（只含消歧触发的动作）
        
        Returns:
            List[Dict]: 消歧动作列表
        """
        return [a for a in self.action_history if a["trigger_type"] is not None]
    
    def get_action_sequence(self) -> List[int]:
        """获取完整动作序列"""
        return [a["action_id"] for a in self.action_history]


# 全局映射表
ACTION_ID_TO_NAME = {
    VLNCEActionType.STOP: "STOP",
    VLNCEActionType.MOVE_FORWARD: "MoveForward",
    VLNCEActionType.TURN_LEFT: "TurnLeft",
    VLNCEActionType.TURN_RIGHT: "TurnRight",
}

ACTION_NAME_TO_ID = {v: k for k, v in ACTION_ID_TO_NAME.items()}
