#!/usr/bin/env python3
"""
当前电脑 RAM 相图细扫（ratio = 0.9 ~ 1.3）

说明
- 复用 current_ram_complete_graph_experiment 中的实验类；
- 在给定的 ratio 区间做高分辨率细扫；
- 每个 ratio 下对多组随机初始态做批量试验；
- 汇总 oscillation_fraction / stable_fraction / mean_switch_rate；
- 绘制相图（两态占比与开关速率）并输出 JSON/PNG。
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from current_ram_complete_graph_experiment import (
    CurrentRAMCompleteGraphExperiment,
    TrialResult,
)


def create_output_dir() -> Path:
    out_dir = Path("./resonance_data")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="当前电脑 RAM 相图细扫（ratio=0.9~1.3）")
    # 扫描区间与分辨率
    p.add_argument("--ratio-min", type=float, default=0.9, help="ratio 最小值")
    p.add_argument("--ratio-max", type=float, default=1.3, help="ratio 最大值")
    p.add_argument("--ratio-steps", type=int, default=33, help="ratio 扫描步数（高分辨率）")
    # 批量随机
    p.add_argument("--random-trials", type=int, default=48, help="每个 ratio 下的随机初始态数量")
    p.add_argument("--seed", type=int, default=12345, help="随机种子")
    # 事件与实验类参数
    p.add_argument("--events", type=int, default=1200, help="每个试验的事件数")
    p.add_argument("--nodes", type=int, default=16, help="全连接图节点数")
    p.add_argument("--buffer-mb", type=int, default=64, help="RAM 缓冲区大小（MB）")
    p.add_argument("--stride", type=int, default=64, help="RAM 扫描跨步字节数")
    p.add_argument("--calibration-rounds", type=int, default=9, help="内存频率代理标定轮数")
    p.add_argument("--threshold", type=float, default=3.0, help="读压阈值")
    p.add_argument("--refresh-scale", type=float, default=1.0, help="刷新频率缩放")
    p.add_argument("--read-gain", type=float, default=1.0, help="每次读取增加的读压")
    p.add_argument("--refresh-decay", type=float, default=1.0, help="每次刷新降低的读压")
    return p.parse_args()


def run_phase_scan(args: argparse.Namespace) -> Dict[str, object]:
    out_root = create_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = out_root / f"current_ram_phase_scan_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)

    # 实例化实验
    exp = CurrentRAMCompleteGraphExperiment(
        n_nodes=args.nodes,
        buffer_mb=args.buffer_mb,
        stride_bytes=args.stride,
        calibration_rounds=args.calibration_rounds,
        threshold=args.threshold,
    )
    calib = exp.estimate_mem_proxy_hz()
    f_mem = float(calib["mem_freq_proxy_hz"])

    ratios = np.linspace(args.ratio_min, args.ratio_max, args.ratio_steps, dtype=np.float64)
    random_states = [
        rng.integers(0, 2, size=args.nodes, dtype=np.uint8) for _ in range(args.random_trials)
    ]

    # 汇总容器
    oscillation_frac: List[float] = []
    stable_frac: List[float] = []
    transition_frac: List[float] = []
    mean_switch_rate: List[float] = []
    mean_flips: List[float] = []
    all_trials: List[Dict[str, object]] = []
    per_ratio_summaries: List[Dict[str, object]] = []

    for ratio in ratios:
        trials: List[TrialResult] = []
        for t_idx, init_state in enumerate(random_states):
            trials.append(
                exp.run_trial(
                    trial_index=t_idx,
                    ratio=float(ratio),
                    mem_freq_proxy_hz=f_mem,
                    initial_state=init_state,
                    total_events=args.events,
                    refresh_scale=args.refresh_scale,
                    read_gain=args.read_gain,
                    refresh_decay=args.refresh_decay,
                )
            )
        osc = sum(1 for tr in trials if tr.classification == "two_state_oscillation")
        stb = sum(1 for tr in trials if tr.classification == "stable_single_attractor")
        trn = len(trials) - osc - stb
        oscillation_frac.append(float(osc / max(len(trials), 1)))
        stable_frac.append(float(stb / max(len(trials), 1)))
        transition_frac.append(float(trn / max(len(trials), 1)))
        mean_switch_rate.append(float(np.mean([tr.switch_rate for tr in trials])))
        mean_flips.append(float(np.mean([tr.flips for tr in trials])))
        per_ratio_summaries.append(
            {
                "ratio": float(ratio),
                "trial_count": len(trials),
                "oscillation_fraction": oscillation_frac[-1],
                "stable_fraction": stable_frac[-1],
                "transition_fraction": transition_frac[-1],
                "mean_switch_rate": mean_switch_rate[-1],
                "mean_flips": mean_flips[-1],
            }
        )
        all_trials.extend([asdict(tr) for tr in trials])

    # 作图：上图显示两态占比，下图显示开关速率
    fig, axes = plt.subplots(2, 1, figsize=(9, 8), constrained_layout=True)
    ax0, ax1 = axes

    ax0.plot(ratios, oscillation_frac, color="tab:red", lw=2, label="oscillation fraction")
    ax0.plot(ratios, stable_frac, color="tab:blue", lw=2, label="stable fraction")
    ax0.plot(ratios, transition_frac, color="tab:gray", lw=1.5, label="transition fraction")
    ax0.axvline(1.0, color="k", ls="--", lw=1, alpha=0.7, label="ratio=1.0")
    ax0.set_title("Phase Fractions vs Ratio (RAM Experiment)")
    ax0.set_xlabel("ratio = f_read / f_mem_proxy")
    ax0.set_ylabel("fraction")
    ax0.set_ylim(-0.05, 1.05)
    ax0.grid(alpha=0.3, ls=":")
    ax0.legend(loc="best")

    ax1.plot(ratios, mean_switch_rate, color="tab:green", lw=2, label="mean switch rate")
    ax1.set_title("Mean Switch Rate vs Ratio")
    ax1.set_xlabel("ratio = f_read / f_mem_proxy")
    ax1.set_ylabel("switches per second (approx.)")
    ax1.axvline(1.0, color="k", ls="--", lw=1, alpha=0.7)
    ax1.grid(alpha=0.3, ls=":")
    ax1.legend(loc="best")

    png_path = run_dir / f"phase_scan_{timestamp}.png"
    fig.savefig(png_path, dpi=160)
    plt.close(fig)

    # 保存 JSON
    result = {
        "timestamp": timestamp,
        "calibration": calib,
        "config": {
            "ratio_min": args.ratio_min,
            "ratio_max": args.ratio_max,
            "ratio_steps": args.ratio_steps,
            "random_trials": args.random_trials,
            "seed": args.seed,
            "events": args.events,
            "nodes": args.nodes,
            "buffer_mb": args.buffer_mb,
            "stride": args.stride,
            "calibration_rounds": args.calibration_rounds,
            "threshold": args.threshold,
            "refresh_scale": args.refresh_scale,
            "read_gain": args.read_gain,
            "refresh_decay": args.refresh_decay,
        },
        "ratios": ratios.tolist(),
        "oscillation_fraction": oscillation_frac,
        "stable_fraction": stable_frac,
        "transition_fraction": transition_frac,
        "mean_switch_rate": mean_switch_rate,
        "mean_flips": mean_flips,
        "per_ratio_summaries": per_ratio_summaries,
        "trials": all_trials,
        "artifacts": {"phase_png": str(png_path)},
    }
    json_path = run_dir / f"phase_scan_{timestamp}.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main() -> None:
    args = parse_args()
    result = run_phase_scan(args)
    print("=" * 72)
    print("当前电脑 RAM 相图细扫")
    print("=" * 72)
    print(f"mem_freq_proxy_hz: {result['calibration']['mem_freq_proxy_hz']:.3f}")
    print(f"ratio range:       {result['config']['ratio_min']} ~ {result['config']['ratio_max']}"
          f" ({result['config']['ratio_steps']} steps)")
    print(f"random trials:     {result['config']['random_trials']}")
    print(f"events per trial:  {result['config']['events']}")
    print(f"phase png:         {result['artifacts']['phase_png']}")


if __name__ == "__main__":
    main()

