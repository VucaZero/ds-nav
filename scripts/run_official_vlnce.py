#!/usr/bin/env python3
"""
VLN-CE 官方推理脚本 + DS/CLIP/门控集成

该脚本复用官方 trainer 的 inference 初始化流程，并在每一步策略决策后
调用 InferenceHook 覆盖动作（可选）。输出格式对齐官方 predictions 文件。
"""

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
import tqdm
import numpy as np

# 兼容旧版 habitat-sim 对 numpy 旧别名 (np.float/np.int/np.bool) 的调用
if not hasattr(np, "float"):
    np.float = float  # type: ignore[attr-defined]
if not hasattr(np, "int"):
    np.int = int  # type: ignore[attr-defined]
if not hasattr(np, "bool"):
    np.bool = bool  # type: ignore[attr-defined]


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


DSNAV_ROOT = Path(__file__).resolve().parent.parent
VLNCE_ROOT = DSNAV_ROOT / "programs" / "VLN-CE"
HABITAT_ROOT = DSNAV_ROOT / "programs" / "habitat-lab"

for p in [DSNAV_ROOT, VLNCE_ROOT, HABITAT_ROOT]:
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)


# noqa: F401 - 注册 habitat/vlnce 扩展
import habitat_extensions  # type: ignore
import vlnce_baselines  # type: ignore

from habitat_baselines.common.baseline_registry import baseline_registry
from habitat_baselines.common.environments import get_env_class
from habitat_baselines.common.obs_transformers import apply_obs_transforms_batch
from habitat_baselines.utils.common import batch_obs
from vlnce_baselines.common.env_utils import construct_envs_auto_reset_false
from vlnce_baselines.common.utils import extract_instruction_tokens
from vlnce_baselines.config.default import get_config

from vln_ce_baseline.vlnce_integration.inference_hook import InferenceHook


def _extract_instruction_text(episode: Any) -> str:
    instruction = getattr(episode, "instruction", None)
    if instruction is None:
        return ""

    for key in ["instruction_text", "text"]:
        value = getattr(instruction, key, None)
        if isinstance(value, str):
            return value

    return str(instruction)


def _apply_pause_list(items: List[Any], indices_to_pause: List[int]) -> List[Any]:
    if not indices_to_pause:
        return items

    paused = set(indices_to_pause)
    return [x for i, x in enumerate(items) if i not in paused]


def load_official_config(config_path: str, opts: Optional[List[str]] = None):
    config = get_config(config_path, opts)
    logger.info("配置加载成功: %s", config_path)
    return config


def _setup_inference_config(trainer: Any, split: str, predictions_file: Path):
    checkpoint_path = trainer.config.INFERENCE.CKPT_PATH
    if trainer.config.INFERENCE.USE_CKPT_CONFIG:
        ckpt = trainer.load_checkpoint(checkpoint_path, map_location="cpu")
        config = trainer._setup_eval_config(ckpt["config"])
    else:
        config = trainer.config.clone()

    config.defrost()
    config.TASK_CONFIG.DATASET.SPLIT = split
    config.TASK_CONFIG.DATASET.ROLES = ["guide"]
    config.TASK_CONFIG.DATASET.LANGUAGES = config.INFERENCE.LANGUAGES
    config.TASK_CONFIG.ENVIRONMENT.ITERATOR_OPTIONS.SHUFFLE = False
    config.TASK_CONFIG.ENVIRONMENT.ITERATOR_OPTIONS.MAX_SCENE_REPEAT_STEPS = -1
    config.IL.ckpt_to_load = config.INFERENCE.CKPT_PATH
    config.TASK_CONFIG.TASK.MEASUREMENTS = []
    config.ENV_NAME = "VLNCEInferenceEnv"
    config.INFERENCE.PREDICTIONS_FILE = str(predictions_file)
    config.freeze()
    return config


def run_official_inference(
    config: Any,
    method: str = "B0",
    split: str = "val_unseen",
    max_episodes: Optional[int] = None,
    output_dir: str = "./eval_results_official",
    uncertainty_threshold: float = 0.5,
    conflict_threshold: float = 0.3,
    ten_window: int = 20,
    theta_hysteresis: float = 0.2,
    k_hysteresis: float = 0.2,
    scan_budget: float = 0.45,
    cooldown_steps: int = 10,
) -> Dict[str, Any]:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("使用设备: %s", device)

    trainer_init = baseline_registry.get_trainer(config.TRAINER_NAME)
    if trainer_init is None:
        raise RuntimeError(f"Trainer {config.TRAINER_NAME} 不支持")

    trainer = trainer_init(config)
    logger.info("Trainer 初始化成功: %s", config.TRAINER_NAME)

    output_path = Path(output_dir) / method
    output_path.mkdir(parents=True, exist_ok=True)

    predictions_file = output_path / ("predictions.jsonl" if config.INFERENCE.FORMAT == "rxr" else "predictions.json")
    episode_logs_file = output_path / "episode_logs.json"

    inference_config = _setup_inference_config(
        trainer=trainer,
        split=split,
        predictions_file=predictions_file,
    )

    envs = construct_envs_auto_reset_false(
        inference_config,
        get_env_class(inference_config.ENV_NAME),
    )

    observation_space, action_space = trainer._get_spaces(inference_config, envs=envs)
    trainer._initialize_policy(
        inference_config,
        load_from_ckpt=True,
        observation_space=observation_space,
        action_space=action_space,
    )
    trainer.policy.eval()

    observations = envs.reset()
    observations = extract_instruction_tokens(
        observations,
        trainer.config.TASK_CONFIG.TASK.INSTRUCTION_SENSOR_UUID,
    )
    batch = batch_obs(observations, trainer.device)
    batch = apply_obs_transforms_batch(batch, trainer.obs_transforms)

    rnn_states = torch.zeros(
        envs.num_envs,
        trainer.policy.net.num_recurrent_layers,
        inference_config.MODEL.STATE_ENCODER.hidden_size,
        device=trainer.device,
    )
    prev_actions = torch.zeros(envs.num_envs, 1, device=trainer.device, dtype=torch.long)
    not_done_masks = torch.zeros(envs.num_envs, 1, dtype=torch.uint8, device=trainer.device)

    hooks: List[Optional[InferenceHook]] = []
    if method == "B0":
        hooks = [None for _ in range(envs.num_envs)]
    else:
        logger.info(
            "门控阈值: uncertainty_threshold=%.3f, conflict_threshold=%.3f; TEN: window=%d, scan_budget=%.3f, cooldown=%d",
            uncertainty_threshold,
            conflict_threshold,
            ten_window,
            scan_budget,
            cooldown_steps,
        )
        hooks = [
            InferenceHook(
                method=method,
                device=device,
                uncertainty_threshold=uncertainty_threshold,
                conflict_threshold=conflict_threshold,
                ten_window=ten_window,
                theta_hysteresis=theta_hysteresis,
                k_hysteresis=k_hysteresis,
                scan_budget=scan_budget,
                cooldown_steps=cooldown_steps,
            )
            for _ in range(envs.num_envs)
        ]

    episode_predictions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    instruction_ids: Dict[str, int] = {}
    episode_logs: List[Dict[str, Any]] = []

    current_episodes = envs.current_episodes()
    for i in range(envs.num_envs):
        ep_id = current_episodes[i].episode_id
        episode_predictions[ep_id].append(envs.call_at(i, "get_info", {"observations": {}}))
        if inference_config.INFERENCE.FORMAT == "rxr":
            k = current_episodes[i].instruction.instruction_id
            instruction_ids[ep_id] = int(k)
        if hooks[i] is not None:
            hooks[i].reset_episode(ep_id)

    completed_episodes = 0
    step_idx = 0

    with tqdm.tqdm(
        total=sum(envs.count_episodes()),
        desc=f"[inference:{split}]",
    ) as pbar:
        while envs.num_envs > 0:
            current_episodes = envs.current_episodes()

            with torch.no_grad():
                features, rnn_states = trainer.policy.net(
                    batch,
                    rnn_states,
                    prev_actions,
                    not_done_masks,
                )
                distribution = trainer.policy.action_distribution(features)
                action_logits = distribution.logits
                if inference_config.INFERENCE.SAMPLE:
                    actions = distribution.sample()
                else:
                    actions = distribution.mode()

            final_actions = actions.clone()
            for i in range(envs.num_envs):
                if hooks[i] is None:
                    continue

                ep = current_episodes[i]
                instruction = _extract_instruction_text(ep)
                action, _ = hooks[i].process_step(
                    observations=observations[i],
                    instruction=instruction,
                    action_logits=action_logits[i : i + 1],
                    t=step_idx,
                    episode_id=ep.episode_id,
                )
                final_actions[i, 0] = int(action)

            prev_actions.copy_(final_actions)

            outputs = envs.step([a[0].item() for a in final_actions])
            observations, _, dones, infos = [list(x) for x in zip(*outputs)]
            step_idx += 1

            not_done_masks = torch.tensor(
                [[0] if done else [1] for done in dones],
                dtype=torch.uint8,
                device=trainer.device,
            )

            hit_max_episodes = False
            for i in range(envs.num_envs):
                ep_id = current_episodes[i].episode_id
                episode_predictions[ep_id].append(infos[i])

                if not dones[i]:
                    continue

                if hooks[i] is not None:
                    episode_logs.append(hooks[i].get_episode_log())

                observations[i] = envs.reset_at(i)[0]
                prev_actions[i] = torch.zeros(1, dtype=torch.long, device=trainer.device)
                completed_episodes += 1
                pbar.update()

                if max_episodes is not None and completed_episodes >= max_episodes:
                    hit_max_episodes = True

            if hit_max_episodes:
                break

            observations = extract_instruction_tokens(
                observations,
                trainer.config.TASK_CONFIG.TASK.INSTRUCTION_SENSOR_UUID,
            )
            batch = batch_obs(observations, trainer.device)
            batch = apply_obs_transforms_batch(batch, trainer.obs_transforms)

            envs_to_pause: List[int] = []
            next_episodes = envs.current_episodes()
            for i in range(envs.num_envs):
                if not dones[i]:
                    continue

                next_ep_id = next_episodes[i].episode_id
                if next_ep_id in episode_predictions:
                    envs_to_pause.append(i)
                else:
                    episode_predictions[next_ep_id].append(
                        envs.call_at(i, "get_info", {"observations": {}})
                    )
                    if inference_config.INFERENCE.FORMAT == "rxr":
                        k = next_episodes[i].instruction.instruction_id
                        instruction_ids[next_ep_id] = int(k)
                    if hooks[i] is not None:
                        hooks[i].reset_episode(next_ep_id)

            hooks = _apply_pause_list(hooks, envs_to_pause)
            observations = _apply_pause_list(observations, envs_to_pause)

            (
                envs,
                rnn_states,
                not_done_masks,
                prev_actions,
                batch,
                _,
            ) = trainer._pause_envs(
                envs_to_pause,
                envs,
                rnn_states,
                not_done_masks,
                prev_actions,
                batch,
            )

    envs.close()

    if inference_config.INFERENCE.FORMAT == "r2r":
        with open(predictions_file, "w") as f:
            json.dump(episode_predictions, f, indent=2)
    else:
        import jsonlines

        predictions_out = []
        for ep_id, infos in episode_predictions.items():
            if not infos:
                continue
            path = [infos[0]["position"]]
            for info in infos[1:]:
                if path[-1] != info["position"]:
                    path.append(info["position"])
            predictions_out.append(
                {
                    "instruction_id": instruction_ids[ep_id],
                    "path": path,
                }
            )

        predictions_out.sort(key=lambda x: x["instruction_id"])
        with jsonlines.open(predictions_file, mode="w") as writer:
            writer.write_all(predictions_out)

    with open(episode_logs_file, "w") as f:
        json.dump(episode_logs, f, indent=2)

    logger.info("推理完成，保存 predictions: %s", predictions_file)
    logger.info("保存 episode logs: %s", episode_logs_file)

    return {
        "method": method,
        "split": split,
        "num_episodes": completed_episodes,
        "uncertainty_threshold": uncertainty_threshold,
        "conflict_threshold": conflict_threshold,
        "ten_window": ten_window,
        "theta_hysteresis": theta_hysteresis,
        "k_hysteresis": k_hysteresis,
        "scan_budget": scan_budget,
        "cooldown_steps": cooldown_steps,
        "predictions_file": str(predictions_file),
        "episode_logs_file": str(episode_logs_file),
        "output_dir": str(output_path),
    }


def main():
    parser = argparse.ArgumentParser(description="VLN-CE 官方推理 + DS/CLIP/门控")
    parser.add_argument("--exp-config", type=str, required=True, help="官方 VLN-CE 配置文件路径")
    parser.add_argument("--method", type=str, default="B0", choices=["B0", "B1", "Ours-R", "Ours-L", "TEN-R", "TEN-L"], help="推理方法")
    parser.add_argument("--split", type=str, default="val_unseen", choices=["val_unseen", "val_seen", "test"], help="数据集划分")
    parser.add_argument("--episodes", type=int, default=None, help="最多运行 episodes 数（默认全量）")
    parser.add_argument("--output-dir", type=str, default="./eval_results_official", help="输出目录")
    parser.add_argument("--uncertainty-threshold", type=float, default=0.5, help="不确定性门控阈值")
    parser.add_argument("--conflict-threshold", type=float, default=0.3, help="冲突门控阈值")
    parser.add_argument("--ten-window", type=int, default=20, help="TEN 滑窗长度")
    parser.add_argument("--theta-hysteresis", type=float, default=0.2, help="TEN theta 滞回系数")
    parser.add_argument("--k-hysteresis", type=float, default=0.2, help="TEN conflict 滞回系数")
    parser.add_argument("--scan-budget", type=float, default=0.45, help="TEN 扫描预算上限")
    parser.add_argument("--cooldown-steps", type=int, default=10, help="TEN 连续触发冷却步数")
    parser.add_argument("opts", default=None, nargs=argparse.REMAINDER, help="额外配置选项")

    args = parser.parse_args()

    config = load_official_config(args.exp_config, args.opts)
    results = run_official_inference(
        config=config,
        method=args.method,
        split=args.split,
        max_episodes=args.episodes,
        output_dir=args.output_dir,
        uncertainty_threshold=args.uncertainty_threshold,
        conflict_threshold=args.conflict_threshold,
        ten_window=args.ten_window,
        theta_hysteresis=args.theta_hysteresis,
        k_hysteresis=args.k_hysteresis,
        scan_budget=args.scan_budget,
        cooldown_steps=args.cooldown_steps,
    )

    logger.info("推理成功: %s", json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
