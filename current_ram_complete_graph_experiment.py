#!/usr/bin/env python3
"""
当前电脑 RAM 中的全连接图双态跳变实验

实验目的
- 在当前机器的用户态 RAM 中常驻一块内存；
- 用一小段 RAM 表示 K_N 全连接图的节点状态；
- 用“大块 RAM 扫描”的耗时估计一个内存服务频率代理值 f_mem_proxy；
- 当读取频率 f_read 高于该代理频率时，观察全连接图是否在两种全局状态之间循环跳变。

说明
- 这是“当前电脑内存中的用户态实验”，不是直接修改 DRAM 控制器或硬件刷新寄存器；
- 实验依赖真实 RAM 访问耗时，但“主控频率”采用可重复测量的代理量；
- 全连接图采用最小双吸引子模型：A=全0，B=全1，任一次全局翻转都会把 A/B 互换。
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np


@dataclass
class TrialResult:
    trial_index: int
    ratio: float
    initial_state: str
    read_freq_hz: float
    mem_freq_proxy_hz: float
    refresh_period_ns: int
    read_period_ns: int
    total_events: int
    read_events: int
    refresh_events: int
    flips: int
    unique_states: int
    loop_length: int
    switch_rate: float
    mean_dwell_events: float
    synchronized_jump_fraction: float
    states_seen: List[str]
    classification: str


class CurrentRAMCompleteGraphExperiment:
    def __init__(
        self,
        n_nodes: int = 16,
        buffer_mb: int = 64,
        stride_bytes: int = 64,
        calibration_rounds: int = 9,
        threshold: float = 3.0,
    ) -> None:
        self.n_nodes = n_nodes
        self.buffer_bytes = buffer_mb * 1024 * 1024
        self.stride_bytes = max(1, stride_bytes)
        self.calibration_rounds = calibration_rounds
        self.threshold = threshold

        self.ram_buffer = np.zeros(self.buffer_bytes, dtype=np.uint8)
        # 强制触页，确保缓冲区真正驻留在当前进程的 RAM 使用中
        self.ram_buffer[:] = 1
        self.state_view = self.ram_buffer[: self.n_nodes]

    def _touch_ram(self) -> int:
        """
        读取大块 RAM 的跨步样本并回写极小扰动，逼近一次“真实内存服务”。
        返回值仅用于防止解释器优化掉该访问。
        """
        sample = self.ram_buffer[:: self.stride_bytes]
        # 先将求和结果转换为 Python int，再进行按位与，避免某些 NumPy 版本的 dtype 运算限制
        checksum_val = int(sample.sum(dtype=np.uint64))
        checksum = checksum_val & 0xFFFFFFFF
        # 在尾部写入一个极小变化，维持“读+写”访问模式
        tail_index = self.buffer_bytes - 1
        self.ram_buffer[tail_index] ^= checksum & 0x1
        return checksum

    def estimate_mem_proxy_hz(self) -> Dict[str, float]:
        durations_ns: List[int] = []
        checksums: List[int] = []

        for _ in range(self.calibration_rounds):
            t0 = time.perf_counter_ns()
            checksums.append(self._touch_ram())
            t1 = time.perf_counter_ns()
            durations_ns.append(max(1, t1 - t0))

        median_ns = int(statistics.median(durations_ns))
        mean_ns = float(statistics.mean(durations_ns))
        proxy_hz = 1e9 / max(median_ns, 1)
        return {
            "touch_ns_median": float(median_ns),
            "touch_ns_mean": mean_ns,
            "mem_freq_proxy_hz": float(proxy_hz),
            "checksum_anchor": float(checksums[-1]) if checksums else 0.0,
        }

    def _state_string(self) -> str:
        return "".join("1" if int(x) else "0" for x in self.state_view.tolist())

    def _set_state(self, value: int) -> None:
        self.state_view[:] = value

    def _set_state_array(self, values: np.ndarray) -> None:
        self.state_view[:] = values.astype(np.uint8, copy=False)

    def _flip_state(self) -> None:
        # K_N 全连接图的最小模型：任意一次全局共振翻转会把全体节点同时切换
        self.state_view[:] ^= 1

    def _detect_loop_length(self, history: List[str]) -> int:
        seen: Dict[str, int] = {}
        for idx, state in enumerate(history):
            if state in seen:
                return idx - seen[state]
            seen[state] = idx
        return 0

    def _compress_history(self, history: List[str]) -> List[str]:
        if not history:
            return []
        compressed = [history[0]]
        for state in history[1:]:
            if state != compressed[-1]:
                compressed.append(state)
        return compressed

    def run_trial(
        self,
        trial_index: int,
        ratio: float,
        mem_freq_proxy_hz: float,
        initial_state: np.ndarray,
        total_events: int = 2000,
        refresh_scale: float = 1.0,
        read_gain: float = 1.0,
        refresh_decay: float = 1.0,
    ) -> TrialResult:
        refresh_freq_hz = max(1e-9, mem_freq_proxy_hz * refresh_scale)
        read_freq_hz = max(1e-9, refresh_freq_hz * ratio)
        refresh_period_ns = max(1, int(round(1e9 / refresh_freq_hz)))
        read_period_ns = max(1, int(round(1e9 / read_freq_hz)))

        initial_state_arr = np.array(initial_state, dtype=np.uint8).reshape(self.n_nodes)
        self._set_state_array(initial_state_arr)
        pressure = 0.0
        flips = 0
        read_events = 0
        refresh_events = 0
        last_flip_event = -1
        dwell_lengths: List[int] = []
        synchronized_jump_fraction = 0.0

        history: List[str] = [self._state_string()]
        current_time_ns = 0
        next_read_ns = read_period_ns
        next_refresh_ns = refresh_period_ns

        for event_idx in range(total_events):
            if next_read_ns <= next_refresh_ns:
                current_time_ns = next_read_ns
                next_read_ns += read_period_ns
                read_events += 1
                self._touch_ram()
                pressure += read_gain

                if pressure >= self.threshold:
                    self._flip_state()
                    pressure -= self.threshold
                    flips += 1
                    if last_flip_event >= 0:
                        dwell_lengths.append(event_idx - last_flip_event)
                    last_flip_event = event_idx
                    # 全连接图模型里一次翻转即全体同步，因此同步率为1
                    synchronized_jump_fraction = 1.0
            else:
                current_time_ns = next_refresh_ns
                next_refresh_ns += refresh_period_ns
                refresh_events += 1
                self._touch_ram()
                pressure = max(0.0, pressure - refresh_decay)

            history.append(self._state_string())

        unique_states = len(set(history))
        compressed_history = self._compress_history(history)
        loop_length = self._detect_loop_length(compressed_history)
        mean_dwell = float(np.mean(dwell_lengths)) if dwell_lengths else float("inf")
        total_time_s = current_time_ns / 1e9 if current_time_ns > 0 else 1e-9
        switch_rate = flips / total_time_s
        alternating = (
            len(compressed_history) >= 6
            and len(set(compressed_history)) == 2
            and all(
                compressed_history[idx] != compressed_history[idx - 1]
                for idx in range(1, len(compressed_history))
            )
        )

        if flips == 0:
            classification = "stable_single_attractor"
        elif unique_states == 2 and alternating:
            classification = "two_state_oscillation"
        else:
            classification = "transitioning"

        return TrialResult(
            trial_index=int(trial_index),
            ratio=float(ratio),
            initial_state="".join(str(int(x)) for x in initial_state_arr.tolist()),
            read_freq_hz=float(read_freq_hz),
            mem_freq_proxy_hz=float(mem_freq_proxy_hz),
            refresh_period_ns=int(refresh_period_ns),
            read_period_ns=int(read_period_ns),
            total_events=int(total_events),
            read_events=int(read_events),
            refresh_events=int(refresh_events),
            flips=int(flips),
            unique_states=int(unique_states),
            loop_length=int(loop_length),
            switch_rate=float(switch_rate),
            mean_dwell_events=float(mean_dwell),
            synchronized_jump_fraction=float(synchronized_jump_fraction),
            states_seen=sorted(set(history)),
            classification=classification,
        )


def create_output_dir() -> Path:
    out_dir = Path("./resonance_data")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def run_experiment(args: argparse.Namespace) -> Dict[str, object]:
    experiment = CurrentRAMCompleteGraphExperiment(
        n_nodes=args.nodes,
        buffer_mb=args.buffer_mb,
        stride_bytes=args.stride,
        calibration_rounds=args.calibration_rounds,
        threshold=args.threshold,
    )
    calibration = experiment.estimate_mem_proxy_hz()
    mem_freq_proxy_hz = float(calibration["mem_freq_proxy_hz"])
    rng = np.random.default_rng(args.seed)

    ratios = np.linspace(args.ratio_min, args.ratio_max, args.ratio_steps, dtype=np.float64)
    random_states = [
        rng.integers(0, 2, size=args.nodes, dtype=np.uint8)
        for _ in range(args.random_trials)
    ]
    trials: List[TrialResult] = []
    ratio_summaries: List[Dict[str, object]] = []

    for ratio in ratios:
        ratio_trials = [
            experiment.run_trial(
                trial_index=trial_idx,
                ratio=float(ratio),
                mem_freq_proxy_hz=mem_freq_proxy_hz,
                initial_state=initial_state,
                total_events=args.events,
                refresh_scale=args.refresh_scale,
                read_gain=args.read_gain,
                refresh_decay=args.refresh_decay,
            )
            for trial_idx, initial_state in enumerate(random_states)
        ]
        trials.extend(ratio_trials)

        oscillation_count = sum(
            1 for trial in ratio_trials if trial.classification == "two_state_oscillation"
        )
        stable_count = sum(
            1 for trial in ratio_trials if trial.classification == "stable_single_attractor"
        )
        transition_count = len(ratio_trials) - oscillation_count - stable_count
        mean_switch_rate = float(np.mean([trial.switch_rate for trial in ratio_trials]))
        mean_flips = float(np.mean([trial.flips for trial in ratio_trials]))
        ratio_summaries.append(
            {
                "ratio": float(ratio),
                "trial_count": len(ratio_trials),
                "oscillation_fraction": float(oscillation_count / max(len(ratio_trials), 1)),
                "stable_fraction": float(stable_count / max(len(ratio_trials), 1)),
                "transition_fraction": float(transition_count / max(len(ratio_trials), 1)),
                "mean_switch_rate": mean_switch_rate,
                "mean_flips": mean_flips,
                "representative_states": sorted(
                    {
                        tuple(trial.states_seen)
                        for trial in ratio_trials
                        if trial.states_seen
                    }
                )[:4],
            }
        )

    best_oscillation = max(
        trials,
        key=lambda t: (
            t.classification == "two_state_oscillation",
            t.switch_rate,
            -abs(t.ratio - 1.5),
        ),
    )

    out_root = create_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_root / f"current_ram_complete_graph_{timestamp}.json"
    result = {
        "timestamp": timestamp,
        "host_experiment": "current_ram_complete_graph",
        "calibration": calibration,
        "config": {
            "nodes": args.nodes,
            "buffer_mb": args.buffer_mb,
            "stride_bytes": args.stride,
            "events": args.events,
            "threshold": args.threshold,
            "refresh_scale": args.refresh_scale,
            "read_gain": args.read_gain,
            "refresh_decay": args.refresh_decay,
            "ratio_min": args.ratio_min,
            "ratio_max": args.ratio_max,
            "ratio_steps": args.ratio_steps,
            "random_trials": args.random_trials,
            "seed": args.seed,
        },
        "best_oscillation": asdict(best_oscillation),
        "ratio_summaries": ratio_summaries,
        "trials": [asdict(trial) for trial in trials],
    }
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    result["output_path"] = str(out_path)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="当前电脑 RAM 全连接图双态跳变实验")
    parser.add_argument("--nodes", type=int, default=16, help="全连接图节点数")
    parser.add_argument("--buffer-mb", type=int, default=64, help="RAM 缓冲区大小（MB）")
    parser.add_argument("--stride", type=int, default=64, help="RAM 扫描跨步字节数")
    parser.add_argument("--calibration-rounds", type=int, default=9, help="内存频率代理标定轮数")
    parser.add_argument("--events", type=int, default=2400, help="每个频率比的事件数")
    parser.add_argument("--threshold", type=float, default=3.0, help="读压累积触发全局翻转阈值")
    parser.add_argument("--refresh-scale", type=float, default=1.0, help="相对内存代理频率的刷新缩放")
    parser.add_argument("--read-gain", type=float, default=1.0, help="每次读取增加的读压")
    parser.add_argument("--refresh-decay", type=float, default=1.0, help="每次刷新降低的读压")
    parser.add_argument("--ratio-min", type=float, default=0.5, help="读取/刷新频率比最小值")
    parser.add_argument("--ratio-max", type=float, default=2.5, help="读取/刷新频率比最大值")
    parser.add_argument("--ratio-steps", type=int, default=9, help="读取/刷新频率比扫描步数")
    parser.add_argument("--random-trials", type=int, default=32, help="每个频率比测试的随机初始数据数量")
    parser.add_argument("--seed", type=int, default=42, help="随机初始数据种子")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_experiment(args)
    best = result["best_oscillation"]

    print("=" * 72)
    print("当前电脑 RAM 全连接图双态跳变实验")
    print("=" * 72)
    print(f"内存代理频率: {result['calibration']['mem_freq_proxy_hz']:.3f} Hz")
    print(f"缓冲区大小:   {result['config']['buffer_mb']} MB")
    print(f"随机数据数:   {result['config']['random_trials']}")
    print(f"最佳跃迁比:   ratio={best['ratio']:.3f}")
    print(f"分类结果:     {best['classification']}")
    print(f"翻转次数:     {best['flips']}")
    print(f"唯一状态数:   {best['unique_states']}")
    print(f"循环长度:     {best['loop_length']}")
    print(f"同步翻转率:   {best['synchronized_jump_fraction']:.3f}")
    print(f"输出文件:     {result['output_path']}")


if __name__ == "__main__":
    main()
