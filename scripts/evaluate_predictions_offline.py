#!/usr/bin/env python3
"""
离线任务级指标评估：从 predictions.json + 数据集 episode 定义计算 SR/SPL/NE/TL。

评估口径：
- `TL`：预测轨迹连续位置的欧氏长度和
- `NE`：轨迹终点到目标点的 geodesic distance
- `SR`：`NE <= goal_radius`
- `SPL`：`SR * geodesic_distance(start, goal) / max(TL, geodesic_distance(start, goal))`
"""

import argparse
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np

if not hasattr(np, "float"):
    np.float = float  # type: ignore[attr-defined]
if not hasattr(np, "int"):
    np.int = int  # type: ignore[attr-defined]
if not hasattr(np, "bool"):
    np.bool = bool  # type: ignore[attr-defined]

import habitat_sim  # type: ignore


def load_dataset_episodes(dataset_file: Path) -> Dict[str, Dict[str, Any]]:
    with gzip.open(dataset_file, "rt") as file_obj:
        dataset = json.load(file_obj)

    episodes = dataset.get("episodes", dataset)
    return {str(episode["episode_id"]): episode for episode in episodes}


def load_predictions(predictions_file: Path) -> Dict[str, List[Dict[str, Any]]]:
    with open(predictions_file, "r") as file_obj:
        predictions = json.load(file_obj)
    return {str(key): value for key, value in predictions.items()}


def build_simulator(scene_file: Path, gpu_device_id: int) -> habitat_sim.Simulator:
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_id = str(scene_file)
    sim_cfg.gpu_device_id = gpu_device_id
    sim_cfg.enable_physics = False

    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = []

    config = habitat_sim.Configuration(sim_cfg, [agent_cfg])
    return habitat_sim.Simulator(config)


def trajectory_length(trajectory: List[Dict[str, Any]]) -> float:
    if len(trajectory) <= 1:
        return 0.0

    points = [np.array(step["position"], dtype=np.float32) for step in trajectory]
    length = 0.0
    for start_point, end_point in zip(points[:-1], points[1:]):
        length += float(np.linalg.norm(end_point - start_point, ord=2))
    return length


def compute_episode_metrics(
    simulator: habitat_sim.Simulator,
    episode: Dict[str, Any],
    trajectory: List[Dict[str, Any]],
) -> Dict[str, Any]:
    goal_position = np.array(episode["goals"][0]["position"], dtype=np.float32)
    goal_radius = float(episode["goals"][0].get("radius", 3.0))
    optimal_distance = float(episode["info"]["geodesic_distance"])
    final_position = np.array(trajectory[-1]["position"], dtype=np.float32)

    shortest_path = habitat_sim.MultiGoalShortestPath()
    shortest_path.requested_start = final_position
    shortest_path.requested_ends = np.array([goal_position], dtype=np.float32)
    simulator.pathfinder.find_path(shortest_path)
    navigation_error = float(shortest_path.geodesic_distance)

    path_length = trajectory_length(trajectory)
    success = 1.0 if navigation_error <= goal_radius else 0.0
    spl = success * optimal_distance / max(path_length, optimal_distance, 1e-8)

    return {
        "episode_id": str(episode["episode_id"]),
        "trajectory_id": int(episode.get("trajectory_id", -1)),
        "scene_id": episode["scene_id"],
        "goal_radius": goal_radius,
        "optimal_distance": optimal_distance,
        "trajectory_length": path_length,
        "navigation_error": navigation_error,
        "success": success,
        "spl": spl,
    }


def aggregate_metrics(per_episode_metrics: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    items = list(per_episode_metrics)
    count = len(items)
    if count == 0:
        return {
            "num_episodes": 0,
            "SR": 0.0,
            "SPL": 0.0,
            "NE": 0.0,
            "TL": 0.0,
        }

    return {
        "num_episodes": count,
        "SR": sum(item["success"] for item in items) / count,
        "SPL": sum(item["spl"] for item in items) / count,
        "NE": sum(item["navigation_error"] for item in items) / count,
        "TL": sum(item["trajectory_length"] for item in items) / count,
        "success_count": int(sum(item["success"] for item in items)),
    }


def evaluate_predictions(
    predictions_file: Path,
    dataset_file: Path,
    scene_datasets_root: Path,
    output_file: Path,
    gpu_device_id: int,
) -> Dict[str, Any]:
    predictions = load_predictions(predictions_file)
    episodes = load_dataset_episodes(dataset_file)

    missing_episode_ids = sorted(set(episodes.keys()) - set(predictions.keys()))
    extra_episode_ids = sorted(set(predictions.keys()) - set(episodes.keys()))

    grouped_ids: Dict[str, List[str]] = defaultdict(list)
    for episode_id in sorted(set(predictions.keys()) & set(episodes.keys()), key=lambda value: int(value)):
        grouped_ids[episodes[episode_id]["scene_id"]].append(episode_id)

    per_episode_metrics: List[Dict[str, Any]] = []
    for scene_id, episode_ids in grouped_ids.items():
        scene_file = scene_datasets_root / scene_id
        simulator = build_simulator(scene_file, gpu_device_id=gpu_device_id)
        try:
            for episode_id in episode_ids:
                trajectory = predictions[episode_id]
                if not trajectory:
                    continue
                metrics = compute_episode_metrics(simulator, episodes[episode_id], trajectory)
                per_episode_metrics.append(metrics)
        finally:
            simulator.close()

    aggregate = aggregate_metrics(per_episode_metrics)
    result = {
        "predictions_file": str(predictions_file),
        "dataset_file": str(dataset_file),
        "scene_datasets_root": str(scene_datasets_root),
        "aggregate_metrics": aggregate,
        "missing_episode_ids": missing_episode_ids,
        "extra_episode_ids": extra_episode_ids,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as file_obj:
        json.dump(result, file_obj, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="离线计算 SR/SPL/NE/TL")
    parser.add_argument("--predictions-file", type=str, required=True)
    parser.add_argument("--dataset-file", type=str, required=True)
    parser.add_argument("--scene-datasets-root", type=str, required=True)
    parser.add_argument("--output-file", type=str, required=True)
    parser.add_argument("--gpu-device-id", type=int, default=0)
    args = parser.parse_args()

    evaluate_predictions(
        predictions_file=Path(args.predictions_file),
        dataset_file=Path(args.dataset_file),
        scene_datasets_root=Path(args.scene_datasets_root),
        output_file=Path(args.output_file),
        gpu_device_id=args.gpu_device_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
