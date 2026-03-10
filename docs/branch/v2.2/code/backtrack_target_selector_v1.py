"""第一版 BACKTRACK 目标节点规则选择器原型。

该文件只放在 docs/branch/v2.2 下做原型验证，不接入主线。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class SelectorWeights:
    info_gain: float = 0.32
    recovery_rate: float = 0.22
    conflict_support: float = 0.16
    progress_gain: float = 0.12
    anchor_bonus: float = 0.10
    distance_penalty: float = 0.16
    revisit_penalty: float = 0.12
    staleness_penalty: float = 0.08
    loop_penalty: float = 0.14


@dataclass(frozen=True)
class SelectorConfig:
    max_backtrack_distance: float = 6.0
    min_step_gap: int = 2
    low_budget_threshold: float = 0.08
    high_conflict_threshold: float = 0.18
    high_stagnation_threshold: int = 3
    max_ranked_candidates: int = 5
    weights: SelectorWeights = field(default_factory=SelectorWeights)


@dataclass(frozen=True)
class SelectionContext:
    current_node_id: int
    theta: float
    conflict_k: float
    stagnation_steps: int
    budget_left: float
    cooldown_left: int
    steps_since_last_rewind: int
    visited_count: int
    frontier_count: int


@dataclass(frozen=True)
class BacktrackCandidate:
    node_id: int
    topo_distance: float
    graph_hops: int
    visit_count: int
    last_seen_step_gap: int
    historical_recovery_rate: float
    progress_gain: float
    expected_info_gain: float
    conflict_support: float
    uncertainty_support: float
    is_frontier_parent: bool = False
    is_recent_anchor: bool = False
    reachable: bool = True


@dataclass(frozen=True)
class RankedCandidate:
    node_id: int
    total_score: float
    reward_score: float
    penalty_score: float
    score_breakdown: Dict[str, float]


@dataclass(frozen=True)
class SelectionResult:
    should_backtrack: bool
    selected_node_id: int
    selected_score: float
    reason: str
    score_breakdown: Dict[str, float]
    ranked_candidates: List[RankedCandidate]

    def to_dict(self) -> Dict[str, object]:
        return {
            "should_backtrack": self.should_backtrack,
            "selected_node_id": self.selected_node_id,
            "selected_score": self.selected_score,
            "reason": self.reason,
            "score_breakdown": self.score_breakdown,
            "ranked_candidates": [asdict(item) for item in self.ranked_candidates],
        }


class BacktrackTargetSelectorV1:
    """基于规则打分的回退目标节点选择器。"""

    def __init__(self, config: Optional[SelectorConfig] = None):
        self.config = config or SelectorConfig()

    def select(
        self,
        context: SelectionContext,
        candidates: List[BacktrackCandidate],
    ) -> SelectionResult:
        if context.cooldown_left > 0:
            return self._empty_result("cooldown_active")

        filtered = [candidate for candidate in candidates if self._is_valid_candidate(context, candidate)]
        if not filtered:
            return self._empty_result("no_valid_candidate")

        ranked = [self._score_candidate(context, candidate) for candidate in filtered]
        ranked.sort(key=lambda item: item.total_score, reverse=True)
        best = ranked[0]

        should_backtrack = best.total_score > 0.0
        reason = self._build_reason(context, best, should_backtrack)
        if not should_backtrack:
            return SelectionResult(
                should_backtrack=False,
                selected_node_id=-1,
                selected_score=best.total_score,
                reason=reason,
                score_breakdown=best.score_breakdown,
                ranked_candidates=ranked[: self.config.max_ranked_candidates],
            )

        return SelectionResult(
            should_backtrack=True,
            selected_node_id=best.node_id,
            selected_score=best.total_score,
            reason=reason,
            score_breakdown=best.score_breakdown,
            ranked_candidates=ranked[: self.config.max_ranked_candidates],
        )

    def _is_valid_candidate(self, context: SelectionContext, candidate: BacktrackCandidate) -> bool:
        if not candidate.reachable:
            return False
        if candidate.node_id == context.current_node_id:
            return False
        if candidate.topo_distance > self.config.max_backtrack_distance:
            return False
        if candidate.last_seen_step_gap < self.config.min_step_gap:
            return False
        return True

    def _score_candidate(
        self,
        context: SelectionContext,
        candidate: BacktrackCandidate,
    ) -> RankedCandidate:
        weights = self.config.weights

        dynamic_distance_penalty = weights.distance_penalty
        if context.budget_left < self.config.low_budget_threshold:
            dynamic_distance_penalty *= 1.35

        dynamic_info_gain = weights.info_gain
        if (
            context.conflict_k >= self.config.high_conflict_threshold
            and context.stagnation_steps >= self.config.high_stagnation_threshold
        ):
            dynamic_info_gain *= 1.15

        anchor_bonus = 0.0
        if candidate.is_frontier_parent:
            anchor_bonus += 0.55
        if candidate.is_recent_anchor:
            anchor_bonus += 0.45

        loop_risk = self._clip01(candidate.visit_count / 6.0)
        distance_norm = self._clip01(candidate.topo_distance / self.config.max_backtrack_distance)
        staleness = self._clip01(max(candidate.last_seen_step_gap - 12, 0) / 20.0)
        revisit_risk = self._clip01(max(candidate.visit_count - 1, 0) / 5.0)

        reward_terms = {
            "info_gain": dynamic_info_gain * self._clip01(candidate.expected_info_gain),
            "recovery_rate": weights.recovery_rate * self._clip01(candidate.historical_recovery_rate),
            "conflict_support": weights.conflict_support * self._clip01(candidate.conflict_support),
            "progress_gain": weights.progress_gain * self._clip01(candidate.progress_gain),
            "anchor_bonus": weights.anchor_bonus * self._clip01(anchor_bonus),
        }
        penalty_terms = {
            "distance_penalty": dynamic_distance_penalty * distance_norm,
            "revisit_penalty": weights.revisit_penalty * revisit_risk,
            "staleness_penalty": weights.staleness_penalty * staleness,
            "loop_penalty": weights.loop_penalty * loop_risk,
        }

        reward_score = sum(reward_terms.values())
        penalty_score = sum(penalty_terms.values())
        total_score = reward_score - penalty_score
        breakdown = {
            "reward_score": reward_score,
            "penalty_score": penalty_score,
            **reward_terms,
            **penalty_terms,
            "topo_distance": candidate.topo_distance,
            "graph_hops": float(candidate.graph_hops),
            "visit_count": float(candidate.visit_count),
            "last_seen_step_gap": float(candidate.last_seen_step_gap),
        }
        return RankedCandidate(
            node_id=candidate.node_id,
            total_score=round(total_score, 6),
            reward_score=round(reward_score, 6),
            penalty_score=round(penalty_score, 6),
            score_breakdown={key: round(value, 6) for key, value in breakdown.items()},
        )

    def _build_reason(
        self,
        context: SelectionContext,
        best: RankedCandidate,
        should_backtrack: bool,
    ) -> str:
        if not should_backtrack:
            return "best_candidate_score_non_positive"
        if context.conflict_k >= self.config.high_conflict_threshold:
            return "high_conflict_best_recovery_anchor"
        if context.stagnation_steps >= self.config.high_stagnation_threshold:
            return "stagnation_driven_best_information_gain"
        return "best_tradeoff_information_gain_vs_cost"

    def _empty_result(self, reason: str) -> SelectionResult:
        return SelectionResult(
            should_backtrack=False,
            selected_node_id=-1,
            selected_score=0.0,
            reason=reason,
            score_breakdown={},
            ranked_candidates=[],
        )

    @staticmethod
    def _clip01(value: float) -> float:
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return value


def build_demo_case() -> Tuple[SelectionContext, List[BacktrackCandidate]]:
    context = SelectionContext(
        current_node_id=7,
        theta=0.71,
        conflict_k=0.22,
        stagnation_steps=4,
        budget_left=0.19,
        cooldown_left=0,
        steps_since_last_rewind=11,
        visited_count=9,
        frontier_count=3,
    )
    candidates = [
        BacktrackCandidate(
            node_id=3,
            topo_distance=1.5,
            graph_hops=1,
            visit_count=1,
            last_seen_step_gap=6,
            historical_recovery_rate=0.82,
            progress_gain=0.55,
            expected_info_gain=0.74,
            conflict_support=0.69,
            uncertainty_support=0.61,
            is_frontier_parent=True,
            is_recent_anchor=True,
        ),
        BacktrackCandidate(
            node_id=4,
            topo_distance=3.8,
            graph_hops=2,
            visit_count=3,
            last_seen_step_gap=10,
            historical_recovery_rate=0.64,
            progress_gain=0.48,
            expected_info_gain=0.58,
            conflict_support=0.54,
            uncertainty_support=0.57,
            is_frontier_parent=False,
            is_recent_anchor=True,
        ),
        BacktrackCandidate(
            node_id=1,
            topo_distance=5.2,
            graph_hops=4,
            visit_count=4,
            last_seen_step_gap=20,
            historical_recovery_rate=0.71,
            progress_gain=0.66,
            expected_info_gain=0.62,
            conflict_support=0.43,
            uncertainty_support=0.51,
            is_frontier_parent=False,
            is_recent_anchor=False,
        ),
    ]
    return context, candidates


if __name__ == "__main__":
    selector = BacktrackTargetSelectorV1()
    demo_context, demo_candidates = build_demo_case()
    result = selector.select(demo_context, demo_candidates)
    print(result.to_dict())
