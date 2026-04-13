#!/usr/bin/env python3
"""
两层三节点模型的跨层频率比多组扫描

目标
- 对核心层与第二层之间的跨层频率比做多组扫描；
- 比较不同跨层频率配置下的核心闭合、阈值层闭合与跨层锁相；
- 输出 JSON/NPZ/CSV 和热图，便于后续继续定位稳定窗。

扫描结构
- 列方向: `omega_core_ratio`，即核心层相对 `omega_mem` 的频率比例
- 行方向: 多组跨层频率比 profile
- 每个 profile 由 `(low/core, equal/core, high/core)` 三个比值组成

输出
- resonance_data/triad_two_layer_memory_sweep_<timestamp>/
  - sweep_summary_<timestamp>.json
  - sweep_metrics_<timestamp>.csv
  - metrics_volume_<timestamp>.npz
  - cross_locking_heatmap_<timestamp>.png
  - core_closure_heatmap_<timestamp>.png
  - mem_closure_heatmap_<timestamp>.png
  - composite_score_heatmap_<timestamp>.png
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from triad_two_layer_memory_scan import (
    NODE_INDEX,
    build_edge_specs,
    build_node_specs,
    initial_state,
    pair_locking,
    rk4_step,
    triad_closure,
)


@dataclass
class SweepPointSummary:
    group_index: int
    group_label: str
    omega_core_ratio: float
    cross_low_ratio: float
    cross_equal_ratio: float
    cross_high_ratio: float
    omega_mem: float
    omega_core: float
    omega_low: float
    omega_equal: float
    omega_high: float
    low_to_mem_ratio: float
    equal_to_mem_ratio: float
    high_to_mem_ratio: float
    core_closure_mean: float
    mem_closure_mean: float
    cross_locking_mean: float
    strong_core_fraction: float
    strong_mem_fraction: float
    core_pair_locking_mean: float
    mem_pair_locking_mean: float
    cross_pair_locking_mean: float
    composite_score: float


def create_output_dir() -> Path:
    out_dir = Path("./resonance_data")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def parse_float_list(value: str) -> List[float]:
    values = [item.strip() for item in value.split(",") if item.strip()]
    if not values:
        raise argparse.ArgumentTypeError("需要至少一个浮点数")
    try:
        return [float(item) for item in values]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"无法解析浮点数列表: {value}") from exc


def parse_cross_ratio_groups(value: str) -> List[Tuple[float, float, float]]:
    groups: List[Tuple[float, float, float]] = []
    raw_groups = [item.strip() for item in value.split(";") if item.strip()]
    if not raw_groups:
        raise argparse.ArgumentTypeError("需要至少一个跨层频率比组")
    for raw_group in raw_groups:
        parts = [item.strip() for item in raw_group.split(",") if item.strip()]
        if len(parts) != 3:
            raise argparse.ArgumentTypeError(
                "每组跨层频率比必须恰好包含 3 个值: low/core, equal/core, high/core"
            )
        try:
            low, equal, high = (float(parts[0]), float(parts[1]), float(parts[2]))
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"无法解析跨层频率比组: {raw_group}") from exc
        groups.append((low, equal, high))
    return groups


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="两层三节点模型的跨层频率比多组扫描")
    p.add_argument("--duration", type=float, default=40.0, help="每个扫描点的仿真时长")
    p.add_argument("--dt", type=float, default=0.04, help="积分步长")
    p.add_argument("--seed", type=int, default=20260408, help="随机种子")
    p.add_argument("--omega-mem", type=float, default=1.0, help="内存覆写频率 omega_mem")
    p.add_argument(
        "--omega-core-ratios",
        type=parse_float_list,
        default=[1.02, 1.08, 1.15, 1.22, 1.30],
        help="核心层相对 omega_mem 的频率比例列表，用逗号分隔",
    )
    p.add_argument(
        "--cross-ratio-groups",
        type=parse_cross_ratio_groups,
        default=[
            (0.78, 0.87, 0.94),
            (0.82, 0.90, 0.98),
            (0.86, 0.95, 1.03),
            (0.90, 1.00, 1.08),
        ],
        help="多组跨层频率比，用分号分组、组内逗号分隔，例如 0.82,0.90,0.98;0.90,1.00,1.08",
    )
    p.add_argument("--closure-lambda", type=float, default=0.6, help="闭合强度三阶增益项")
    p.add_argument("--core-threshold", type=float, default=2.2, help="核心层强闭合阈值")
    p.add_argument("--mem-threshold", type=float, default=1.2, help="第二层强闭合阈值")
    p.add_argument(
        "--init-noise",
        type=float,
        default=0.0,
        help="初始态幅度微扰标准差，用于避免完全同态扫描；默认 0 表示关闭",
    )
    return p.parse_args()


def build_point_args(
    base_args: argparse.Namespace,
    omega_core_ratio: float,
    cross_group: Tuple[float, float, float],
) -> argparse.Namespace:
    point_args = argparse.Namespace(**vars(base_args))
    point_args.omega_core_ratio = float(omega_core_ratio)
    point_args.low_ratio = float(cross_group[0] * omega_core_ratio)
    point_args.equal_ratio = float(cross_group[1] * omega_core_ratio)
    point_args.high_ratio = float(cross_group[2] * omega_core_ratio)
    return point_args


def build_initial_state(seed: int, init_noise: float) -> np.ndarray:
    x0 = initial_state().copy()
    if init_noise <= 0.0:
        return x0
    rng = np.random.default_rng(seed)
    amp_noise = rng.normal(0.0, init_noise, size=x0.shape[0])
    phase_noise = rng.normal(0.0, init_noise, size=x0.shape[0])
    amplitudes = np.maximum(np.abs(x0) * (1.0 + amp_noise), 1e-6)
    phases = np.angle(x0) + phase_noise
    return amplitudes * np.exp(1j * phases)


def simulate_point(
    point_args: argparse.Namespace,
    seed: int,
    init_noise: float,
) -> Dict[str, object]:
    node_specs = build_node_specs(point_args)
    edge_specs = build_edge_specs(point_args)

    steps = int(np.floor(point_args.duration / point_args.dt))
    if steps <= 0:
        raise ValueError("仿真步数必须大于 0，请检查 duration 和 dt")
    times = np.linspace(0.0, point_args.dt * (steps - 1), steps, dtype=np.float64)
    x = build_initial_state(seed=seed, init_noise=init_noise)

    node_series = np.zeros((steps, 6), dtype=np.complex128)
    core_closure_series = np.zeros(steps, dtype=np.float64)
    mem_closure_series = np.zeros(steps, dtype=np.float64)
    cross_locking_series = np.zeros(steps, dtype=np.float64)

    for step, t in enumerate(times):
        node_series[step] = x
        amp = np.abs(x)
        core_closure_series[step] = triad_closure(amp[:3], point_args.closure_lambda)
        mem_closure_series[step] = triad_closure(amp[3:], point_args.closure_lambda)

        phase_core = np.angle(x[:3])
        phase_mem = np.angle(x[3:])
        cross_locking_series[step] = float(np.abs(np.mean(np.exp(1j * (phase_core - phase_mem)))))

        x = rk4_step(x, float(t), point_args.dt, node_specs, edge_specs)

    omega_mem = float(point_args.omega_mem)
    omega_core = float(point_args.omega_core_ratio * omega_mem)
    omega_low = float(point_args.low_ratio * omega_mem)
    omega_equal = float(point_args.equal_ratio * omega_mem)
    omega_high = float(point_args.high_ratio * omega_mem)

    pair_locking_values = {
        "core_s_w": pair_locking(node_series, NODE_INDEX["s"], NODE_INDEX["w"]),
        "core_w_a": pair_locking(node_series, NODE_INDEX["w"], NODE_INDEX["a"]),
        "core_a_s": pair_locking(node_series, NODE_INDEX["a"], NODE_INDEX["s"]),
        "mem_l_e": pair_locking(node_series, NODE_INDEX["l"], NODE_INDEX["e"]),
        "mem_e_h": pair_locking(node_series, NODE_INDEX["e"], NODE_INDEX["h"]),
        "mem_h_l": pair_locking(node_series, NODE_INDEX["h"], NODE_INDEX["l"]),
        "cross_s_l": pair_locking(node_series, NODE_INDEX["s"], NODE_INDEX["l"]),
        "cross_w_e": pair_locking(node_series, NODE_INDEX["w"], NODE_INDEX["e"]),
        "cross_a_h": pair_locking(node_series, NODE_INDEX["a"], NODE_INDEX["h"]),
    }

    core_pair_locking_mean = float(
        np.mean(
            [
                pair_locking_values["core_s_w"],
                pair_locking_values["core_w_a"],
                pair_locking_values["core_a_s"],
            ]
        )
    )
    mem_pair_locking_mean = float(
        np.mean(
            [
                pair_locking_values["mem_l_e"],
                pair_locking_values["mem_e_h"],
                pair_locking_values["mem_h_l"],
            ]
        )
    )
    cross_pair_locking_mean = float(
        np.mean(
            [
                pair_locking_values["cross_s_l"],
                pair_locking_values["cross_w_e"],
                pair_locking_values["cross_a_h"],
            ]
        )
    )

    summary = {
        "dt": float(point_args.dt),
        "steps": int(steps),
        "duration": float(times[-1]),
        "omega_mem": omega_mem,
        "omega_core": omega_core,
        "omega_low": omega_low,
        "omega_equal": omega_equal,
        "omega_high": omega_high,
        "omega_core_ratio": float(point_args.omega_core_ratio),
        "cross_low_ratio": float(omega_low / omega_core),
        "cross_equal_ratio": float(omega_equal / omega_core),
        "cross_high_ratio": float(omega_high / omega_core),
        "low_to_mem_ratio": float(point_args.low_ratio),
        "equal_to_mem_ratio": float(point_args.equal_ratio),
        "high_to_mem_ratio": float(point_args.high_ratio),
        "core_closure_mean": float(np.mean(core_closure_series)),
        "mem_closure_mean": float(np.mean(mem_closure_series)),
        "cross_locking_mean": float(np.mean(cross_locking_series)),
        "strong_core_fraction": float(np.mean(core_closure_series >= point_args.core_threshold)),
        "strong_mem_fraction": float(np.mean(mem_closure_series >= point_args.mem_threshold)),
        "pair_locking": pair_locking_values,
        "core_pair_locking_mean": core_pair_locking_mean,
        "mem_pair_locking_mean": mem_pair_locking_mean,
        "cross_pair_locking_mean": cross_pair_locking_mean,
    }
    return summary


def composite_score(summary: Dict[str, object]) -> float:
    return float(
        0.34 * float(summary["cross_locking_mean"])
        + 0.22 * float(summary["strong_core_fraction"])
        + 0.16 * float(summary["strong_mem_fraction"])
        + 0.14 * float(summary["core_pair_locking_mean"])
        + 0.14 * float(summary["cross_pair_locking_mean"])
    )


def run_sweep(args: argparse.Namespace) -> Dict[str, object]:
    out_root = create_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = out_root / f"triad_two_layer_memory_sweep_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    omega_core_ratios = [float(x) for x in args.omega_core_ratios]
    cross_ratio_groups = [tuple(float(v) for v in group) for group in args.cross_ratio_groups]
    group_labels = [f"G{i + 1}: {g[0]:.2f}/{g[1]:.2f}/{g[2]:.2f}" for i, g in enumerate(cross_ratio_groups)]

    rows = len(cross_ratio_groups)
    cols = len(omega_core_ratios)
    core_closure_map = np.zeros((rows, cols), dtype=np.float64)
    mem_closure_map = np.zeros((rows, cols), dtype=np.float64)
    cross_locking_map = np.zeros((rows, cols), dtype=np.float64)
    composite_map = np.zeros((rows, cols), dtype=np.float64)

    point_summaries: List[SweepPointSummary] = []

    for row_idx, cross_group in enumerate(cross_ratio_groups):
        for col_idx, omega_core_ratio in enumerate(omega_core_ratios):
            point_args = build_point_args(args, omega_core_ratio=omega_core_ratio, cross_group=cross_group)
            summary = simulate_point(
                point_args,
                seed=args.seed + row_idx * 1000 + col_idx,
                init_noise=float(args.init_noise),
            )
            score = composite_score(summary)

            point = SweepPointSummary(
                group_index=row_idx,
                group_label=group_labels[row_idx],
                omega_core_ratio=float(omega_core_ratio),
                cross_low_ratio=float(summary["cross_low_ratio"]),
                cross_equal_ratio=float(summary["cross_equal_ratio"]),
                cross_high_ratio=float(summary["cross_high_ratio"]),
                omega_mem=float(summary["omega_mem"]),
                omega_core=float(summary["omega_core"]),
                omega_low=float(summary["omega_low"]),
                omega_equal=float(summary["omega_equal"]),
                omega_high=float(summary["omega_high"]),
                low_to_mem_ratio=float(summary["low_to_mem_ratio"]),
                equal_to_mem_ratio=float(summary["equal_to_mem_ratio"]),
                high_to_mem_ratio=float(summary["high_to_mem_ratio"]),
                core_closure_mean=float(summary["core_closure_mean"]),
                mem_closure_mean=float(summary["mem_closure_mean"]),
                cross_locking_mean=float(summary["cross_locking_mean"]),
                strong_core_fraction=float(summary["strong_core_fraction"]),
                strong_mem_fraction=float(summary["strong_mem_fraction"]),
                core_pair_locking_mean=float(summary["core_pair_locking_mean"]),
                mem_pair_locking_mean=float(summary["mem_pair_locking_mean"]),
                cross_pair_locking_mean=float(summary["cross_pair_locking_mean"]),
                composite_score=score,
            )
            point_summaries.append(point)

            core_closure_map[row_idx, col_idx] = point.core_closure_mean
            mem_closure_map[row_idx, col_idx] = point.mem_closure_mean
            cross_locking_map[row_idx, col_idx] = point.cross_locking_mean
            composite_map[row_idx, col_idx] = point.composite_score

    best_point = max(point_summaries, key=lambda item: item.composite_score)

    png_paths = {
        "cross_locking_heatmap": str(
            save_heatmap(
                output_path=run_dir / f"cross_locking_heatmap_{timestamp}.png",
                data=cross_locking_map,
                x_labels=[f"{x:.2f}" for x in omega_core_ratios],
                y_labels=group_labels,
                title="Cross-layer Locking Mean",
                colorbar_label="locking",
            )
        ),
        "core_closure_heatmap": str(
            save_heatmap(
                output_path=run_dir / f"core_closure_heatmap_{timestamp}.png",
                data=core_closure_map,
                x_labels=[f"{x:.2f}" for x in omega_core_ratios],
                y_labels=group_labels,
                title="Core Closure Mean",
                colorbar_label="core closure",
            )
        ),
        "mem_closure_heatmap": str(
            save_heatmap(
                output_path=run_dir / f"mem_closure_heatmap_{timestamp}.png",
                data=mem_closure_map,
                x_labels=[f"{x:.2f}" for x in omega_core_ratios],
                y_labels=group_labels,
                title="Memory Layer Closure Mean",
                colorbar_label="mem closure",
            )
        ),
        "composite_score_heatmap": str(
            save_heatmap(
                output_path=run_dir / f"composite_score_heatmap_{timestamp}.png",
                data=composite_map,
                x_labels=[f"{x:.2f}" for x in omega_core_ratios],
                y_labels=group_labels,
                title="Composite Stability Score",
                colorbar_label="score",
            )
        ),
    }

    npz_path = run_dir / f"metrics_volume_{timestamp}.npz"
    np.savez_compressed(
        npz_path,
        omega_core_ratios=np.array(omega_core_ratios, dtype=np.float64),
        cross_ratio_groups=np.array(cross_ratio_groups, dtype=np.float64),
        core_closure_map=core_closure_map,
        mem_closure_map=mem_closure_map,
        cross_locking_map=cross_locking_map,
        composite_map=composite_map,
    )

    csv_path = run_dir / f"sweep_metrics_{timestamp}.csv"
    save_csv(csv_path, point_summaries)

    result = {
        "model": "triad_two_layer_memory_sweep",
        "timestamp": timestamp,
        "config": {
            "duration": float(args.duration),
            "dt": float(args.dt),
            "seed": int(args.seed),
            "omega_mem": float(args.omega_mem),
            "omega_core_ratios": omega_core_ratios,
            "cross_ratio_groups": [list(group) for group in cross_ratio_groups],
            "closure_lambda": float(args.closure_lambda),
            "core_threshold": float(args.core_threshold),
            "mem_threshold": float(args.mem_threshold),
            "init_noise": float(args.init_noise),
        },
        "group_labels": group_labels,
        "point_summaries": [asdict(item) for item in point_summaries],
        "best_point": asdict(best_point),
        "artifacts": {
            "metrics_npz": str(npz_path),
            "metrics_csv": str(csv_path),
            **png_paths,
        },
    }

    json_path = run_dir / f"sweep_summary_{timestamp}.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    result["run_dir"] = str(run_dir)
    result["summary_json"] = str(json_path)
    return result


def save_csv(output_path: Path, point_summaries: Sequence[SweepPointSummary]) -> None:
    fieldnames = list(asdict(point_summaries[0]).keys()) if point_summaries else []
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in point_summaries:
            writer.writerow(asdict(item))


def save_heatmap(
    output_path: Path,
    data: np.ndarray,
    x_labels: Sequence[str],
    y_labels: Sequence[str],
    title: str,
    colorbar_label: str,
) -> Path:
    fig, ax = plt.subplots(figsize=(1.4 * len(x_labels) + 2.5, 0.9 * len(y_labels) + 2.5))
    im = ax.imshow(data, aspect="auto", cmap="viridis")
    ax.set_title(title)
    ax.set_xlabel("omega_core / omega_mem")
    ax.set_ylabel("cross ratio groups (low/core, equal/core, high/core)")
    ax.set_xticks(np.arange(len(x_labels)))
    ax.set_xticklabels(list(x_labels))
    ax.set_yticks(np.arange(len(y_labels)))
    ax.set_yticklabels(list(y_labels))

    for row in range(data.shape[0]):
        for col in range(data.shape[1]):
            ax.text(col, row, f"{data[row, col]:.3f}", ha="center", va="center", color="white", fontsize=8)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(colorbar_label)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def main() -> None:
    args = parse_args()
    result = run_sweep(args)
    best_point = result["best_point"]
    print(json.dumps(
        {
            "run_dir": result["run_dir"],
            "summary_json": result["summary_json"],
            "best_point": best_point,
        },
        indent=2,
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
