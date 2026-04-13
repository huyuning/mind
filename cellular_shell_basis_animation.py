#!/usr/bin/env python3
"""
单胞元锁相球壳动画

目标：
- 为“胞元基底的单个胞元”生成一个 3D 锁相球壳动画
- 内层壳面更密集，外层壳面交织更复杂
- 同时输出 Plotly HTML 和 Matplotlib GIF，避免浏览器交互问题
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import animation


@dataclass
class ShellAnimationSummary:
    shell_count: int
    duration: float
    dt: float
    frame_count: int
    min_radius: float
    max_radius: float
    radial_bias: float
    max_harmonic_order: int
    mean_shell_spacing: float
    min_shell_spacing: float
    max_shell_spacing: float
    radii_profile: str
    radii_source: str
    wave_cells_enabled: bool
    child_cell_count_estimate: int
    dual_cells_enabled: bool
    resonance_cells_enabled: bool
    resonance_cell_count_estimate: int
    third_cells_enabled: bool
    downward_recursion_depth: int
    upward_recursion_depth: int
    macro_cell_count_estimate: int
    cross_hierarchy_resonance_enabled: bool
    cross_hierarchy_cell_count_estimate: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="单胞元锁相球壳动画")
    parser.add_argument("--shell-count", type=int, default=7, help="壳层数量")
    parser.add_argument("--duration", type=float, default=12.0, help="总时长")
    parser.add_argument("--dt", type=float, default=0.12, help="时间步长")
    parser.add_argument("--min-radius", type=float, default=0.35, help="最内层半径")
    parser.add_argument("--max-radius", type=float, default=3.8, help="最外层半径")
    parser.add_argument("--radial-bias", type=float, default=1.85, help="壳层向微观端压缩的幂指数（profile=power），越大内层越密")
    parser.add_argument(
        "--radii-profile",
        type=str,
        choices=["power", "log", "exp", "custom-csv"],
        default="power",
        help="半径压缩/分配的配置：power 幂律、log 对数、exp 指数、custom-csv 来自测量数据",
    )
    parser.add_argument(
        "--radial-log-k",
        type=float,
        default=9.0,
        help="对数压缩参数（profile=log）：normalized=log(1+k*x)/log(1+k)",
    )
    parser.add_argument(
        "--radial-exp-k",
        type=float,
        default=2.0,
        help="指数压缩参数（profile=exp）：normalized=(exp(k*x)-1)/(exp(k)-1)",
    )
    parser.add_argument(
        "--radii-csv",
        type=str,
        default=None,
        help="自定义壳层半径 CSV 文件路径（profile=custom-csv）。支持：单列无表头；或含表头名为 'radius' 的一列。",
    )
    parser.add_argument(
        "--no-normalize-custom",
        action="store_true",
        help="custom-csv 时不把输入数据归一映射到 [min_radius, max_radius]，默认会归一化。",
    )
    parser.add_argument("--max-harmonic-order", type=int, default=6, help="最外层最大角向复杂度")
    parser.add_argument("--theta-count", type=int, default=28, help="极角采样数")
    parser.add_argument("--phi-count", type=int, default=52, help="方位角采样数")
    parser.add_argument("--target-frames", type=int, default=72, help="目标帧数上限")
    parser.add_argument("--gif-fps", type=int, default=12, help="Matplotlib GIF 帧率")
    parser.add_argument("--spawn-wave-cells", action="store_true", help="把每个锁相波作为新的子胞元叠加到父壳层之上")
    parser.add_argument("--wave-cell-multiplier", type=int, default=1, help="每个谐波波峰生成的子胞元倍数")
    parser.add_argument("--child-shell-count", type=int, default=2, help="每个子胞元内部的小壳层数量")
    parser.add_argument("--child-cell-scale", type=float, default=0.18, help="子胞元相对父壳层半径的尺度")
    parser.add_argument("--child-theta-count", type=int, default=10, help="子胞元极角采样数")
    parser.add_argument("--child-phi-count", type=int, default=18, help="子胞元方位角采样数")
    parser.add_argument("--dual-cells", action="store_true", help="引入两个不同父胞元")
    parser.add_argument("--cell-separation", type=float, default=3.2, help="两个父胞元中心的间距")
    parser.add_argument("--cell-phase-offset", type=float, default=0.9, help="第二个胞元相对第一个胞元的相位偏移")
    parser.add_argument("--cell2-radius-scale", type=float, default=0.92, help="第二个胞元的整体尺度因子")
    parser.add_argument("--third-cell", action="store_true", help="引入第三个父胞元，形成三胞元耦合")
    parser.add_argument("--cell3-phase-offset", type=float, default=1.45, help="第三个胞元相对第一个胞元的相位偏移")
    parser.add_argument("--cell3-radius-scale", type=float, default=1.08, help="第三个胞元的整体尺度因子")
    parser.add_argument("--cell-triangle-height", type=float, default=0.0, help="第三胞元在三角排布中的高度；<=0 时自动取等边三角高度")
    parser.add_argument("--spawn-resonance-cells", action="store_true", help="把两个胞元的共振配对生成新的共振胞元")
    parser.add_argument("--resonance-distance-threshold", type=float, default=1.35, help="两个波中心判为共振的最大距离")
    parser.add_argument("--resonance-phase-threshold", type=float, default=0.75, help="两个波中心判为共振的最大相位差")
    parser.add_argument("--resonance-cell-scale", type=float, default=0.13, help="共振胞元相对父壳层半径的尺度")
    parser.add_argument("--resonance-shell-count", type=int, default=2, help="每个共振胞元内部的小壳层数量")
    parser.add_argument("--downward-depth", type=int, default=1, help="向下递归层数；1 表示只生成第一层子胞元")
    parser.add_argument("--downward-scale-decay", type=float, default=0.45, help="向下递归时每深入一层的尺度衰减")
    parser.add_argument("--upward-depth", type=int, default=0, help="向上递归层数；0 表示不生成宏胞元")
    parser.add_argument("--upward-scale-growth", type=float, default=1.7, help="向上递归时每升一层的尺度增长")
    parser.add_argument("--macro-cell-scale", type=float, default=0.22, help="向上递归宏胞元的基础尺度")
    parser.add_argument("--cross-hierarchy-resonance", action="store_true", help="寻找父层与子层递归之间的跨层级共振，并生成新的胞元")
    parser.add_argument("--cross-hierarchy-distance-threshold", type=float, default=0.95, help="跨层级共振的最大距离阈值")
    parser.add_argument("--cross-hierarchy-phase-threshold", type=float, default=1.1, help="跨层级共振的最大相位阈值")
    parser.add_argument("--cross-hierarchy-cell-scale", type=float, default=0.085, help="跨层级共振新胞元的尺度")
    return parser.parse_args()


def create_output_dir() -> Path:
    out_dir = Path("resonance_data")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def shell_radii(shell_count: int, min_radius: float, max_radius: float, radial_bias: float) -> np.ndarray:
    if shell_count == 1:
        return np.array([0.5 * (min_radius + max_radius)], dtype=np.float64)
    normalized = np.linspace(0.0, 1.0, shell_count, dtype=np.float64) ** radial_bias
    return min_radius + (max_radius - min_radius) * normalized


def shell_radii_log(
    shell_count: int, min_radius: float, max_radius: float, k: float
) -> np.ndarray:
    """
    对数压缩：normalized = 1 - log(1 + k * (1 - x)) / log(1 + k), x∈[0,1]
    k 越大，越向内层压缩。
    """
    if shell_count == 1:
        return np.array([0.5 * (min_radius + max_radius)], dtype=np.float64)
    x = np.linspace(0.0, 1.0, shell_count, dtype=np.float64)
    denom = math.log1p(k) if k > 0 else 1.0
    normalized = 1.0 - (np.log1p(k * (1.0 - x)) / denom) if k > 0 else x
    return min_radius + (max_radius - min_radius) * normalized


def shell_radii_exp(
    shell_count: int, min_radius: float, max_radius: float, k: float
) -> np.ndarray:
    """
    指数压缩：normalized = (exp(k * x) - 1) / (exp(k) - 1), x∈[0,1]
    k 越大，越向外层扩张；与对数压缩互补。
    """
    if shell_count == 1:
        return np.array([0.5 * (min_radius + max_radius)], dtype=np.float64)
    x = np.linspace(0.0, 1.0, shell_count, dtype=np.float64)
    denom = math.expm1(k) if k != 0 else 1.0
    normalized = (np.expm1(k * x) / denom) if k != 0 else x
    return min_radius + (max_radius - min_radius) * normalized


def load_custom_radii_csv(
    path: Path,
    shell_count: int,
    min_radius: float,
    max_radius: float,
    normalize: bool = True,
) -> np.ndarray:
    """
    加载自定义测量数据：
    - 支持单列无表头；或 CSV 第一行含 'radius' 表头的单列
    - 若长度与 shell_count 不同，使用线性重采样对齐
    - 若 normalize=True，则把数据线性缩放到 [min_radius, max_radius]
    """
    txt = path.read_text(encoding="utf-8").strip().splitlines()
    values: List[float] = []
    # 尝试表头
    if len(txt) > 0 and ("radius" in txt[0].lower() or "," in txt[0]):
        # 朴素 CSV 解析：用逗号切分，找名为 'radius' 的列
        header = [c.strip().lower() for c in txt[0].split(",")]
        try:
            idx = header.index("radius")
            rows = txt[1:]
            for row in rows:
                if not row.strip():
                    continue
                parts = row.split(",")
                if idx < len(parts):
                    try:
                        values.append(float(parts[idx].strip()))
                    except Exception:
                        continue
        except ValueError:
            # 没找到 radius 列，则尝试把每行第一列当作数值
            for row in txt:
                if not row.strip():
                    continue
                try:
                    values.append(float(row.split(",")[0].strip()))
                except Exception:
                    continue
    else:
        # 单列数字，无表头
        for row in txt:
            if not row.strip():
                continue
            try:
                values.append(float(row.strip()))
            except Exception:
                continue

    if len(values) == 0:
        raise ValueError(f"无法从 CSV 解析到任何半径数据：{path}")

    arr = np.array(values, dtype=np.float64)
    # 重采样到 shell_count
    if len(arr) != shell_count:
        xs_old = np.linspace(0.0, 1.0, len(arr), dtype=np.float64)
        xs_new = np.linspace(0.0, 1.0, shell_count, dtype=np.float64)
        arr = np.interp(xs_new, xs_old, arr)

    # 归一到 [min_radius, max_radius]
    if normalize:
        lo = float(np.min(arr))
        hi = float(np.max(arr))
        if hi - lo > 1e-12:
            arr = (arr - lo) / (hi - lo)
            arr = min_radius + (max_radius - min_radius) * arr
        else:
            # 所有值一样，退化为线性
            arr = np.linspace(min_radius, max_radius, shell_count, dtype=np.float64)
    else:
        # 不归一则直接线性拉伸到单调不减并裁剪到范围
        arr = np.asarray(arr, dtype=np.float64)
        arr = np.clip(arr, min_radius, max_radius)
        # 保证单调非减
        for i in range(1, len(arr)):
            if arr[i] < arr[i - 1]:
                arr[i] = arr[i - 1]
    return arr


def build_shell_radii(
    shell_count: int,
    min_radius: float,
    max_radius: float,
    profile: str,
    radial_bias: float,
    radial_log_k: float,
    radial_exp_k: float,
    radii_csv: str | None,
    normalize_custom: bool,
) -> Tuple[np.ndarray, str, str]:
    """
    返回：radii, profile_used, source
    """
    if profile == "power":
        return shell_radii(shell_count, min_radius, max_radius, radial_bias), "power", "power(bias)"
    if profile == "log":
        return shell_radii_log(shell_count, min_radius, max_radius, radial_log_k), "log", f"log(k={radial_log_k})"
    if profile == "exp":
        return shell_radii_exp(shell_count, min_radius, max_radius, radial_exp_k), "exp", f"exp(k={radial_exp_k})"
    if profile == "custom-csv":
        if not radii_csv:
            raise ValueError("profile=custom-csv 需要提供 --radii-csv 路径")
        path = Path(radii_csv)
        arr = load_custom_radii_csv(path, shell_count, min_radius, max_radius, normalize=(not normalize_custom is True))
        return arr, "custom-csv", str(path)
    # 回退：幂律
    return shell_radii(shell_count, min_radius, max_radius, radial_bias), "power", "power(bias)"


def shell_harmonic_orders(shell_count: int, max_harmonic_order: int) -> np.ndarray:
    if shell_count == 1:
        return np.array([1], dtype=np.int64)
    values = np.linspace(1.0, float(max_harmonic_order), shell_count)
    return np.rint(values).astype(np.int64)


def spherical_grid(theta_count: int, phi_count: int) -> Tuple[np.ndarray, np.ndarray]:
    theta = np.linspace(1e-3, math.pi - 1e-3, theta_count, dtype=np.float64)
    phi = np.linspace(-math.pi, math.pi, phi_count, endpoint=False, dtype=np.float64)
    return np.meshgrid(theta, phi, indexing="ij")


def shell_surface(
    radius: float,
    harmonic_order: int,
    t: float,
    theta_grid: np.ndarray,
    phi_grid: np.ndarray,
    shell_index: int,
    shell_count: int,
    phase_offset: float = 0.0,
    center_offset: np.ndarray | None = None,
    radius_scale: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    # 外层复杂度更高，调制更强；内层更平滑，体现“微观更密但更紧凑”。
    normalized_index = 0.0 if shell_count <= 1 else shell_index / float(shell_count - 1)
    base_breathing = 0.05 + 0.03 * normalized_index
    distortion_gain = 0.04 + 0.10 * normalized_index
    phase = 0.7 * shell_index + phase_offset
    breathing = 1.0 + base_breathing * math.sin(0.9 * t + phase)

    harmonic_a = np.cos(harmonic_order * phi_grid - 0.8 * t + phase)
    harmonic_b = np.sin((harmonic_order + 1) * theta_grid + 0.55 * t - phase)
    harmonic_c = np.cos((harmonic_order + 2) * theta_grid - harmonic_order * phi_grid + 0.35 * t)
    shell_modulation = 0.55 * harmonic_a * harmonic_b + 0.45 * harmonic_c * np.sin(theta_grid)
    r = (radius * radius_scale) * breathing * (1.0 + distortion_gain * shell_modulation)

    x = r * np.sin(theta_grid) * np.cos(phi_grid)
    y = r * np.sin(theta_grid) * np.sin(phi_grid)
    z = r * np.cos(theta_grid)
    if center_offset is not None:
        x = x + float(center_offset[0])
        y = y + float(center_offset[1])
        z = z + float(center_offset[2])
    return x, y, z, shell_modulation


def child_cell_centers(
    radius: float,
    harmonic_order: int,
    t: float,
    shell_index: int,
    shell_count: int,
    multiplier: int,
    center_offset: np.ndarray | None = None,
    phase_offset: float = 0.0,
    radius_scale: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    把每个锁相波峰近似映射为一个子胞元中心。
    """
    count = max(1, int(harmonic_order) * max(1, multiplier))
    normalized_index = 0.0 if shell_count <= 1 else shell_index / float(shell_count - 1)
    phase = 0.55 * t + 0.8 * shell_index + phase_offset
    centers = np.zeros((count, 3), dtype=np.float64)
    phases = np.zeros(count, dtype=np.float64)
    offset = np.zeros(3, dtype=np.float64) if center_offset is None else np.asarray(center_offset, dtype=np.float64)
    for j in range(count):
        u = (j + 0.5) / count
        theta = np.arccos(1.0 - 2.0 * u)
        phi = (2.0 * math.pi * j / count) + phase + 0.22 * harmonic_order
        local_radius = radius * radius_scale * (1.03 + 0.06 * normalized_index + 0.02 * math.sin(t + j))
        centers[j, 0] = offset[0] + local_radius * math.sin(theta) * math.cos(phi)
        centers[j, 1] = offset[1] + local_radius * math.sin(theta) * math.sin(phi)
        centers[j, 2] = offset[2] + local_radius * math.cos(theta)
        phases[j] = phi
    return centers, phases


def child_cell_points(
    radii: np.ndarray,
    harmonic_orders: np.ndarray,
    t: float,
    child_shell_count: int,
    child_cell_scale: float,
    child_theta_grid: np.ndarray,
    child_phi_grid: np.ndarray,
    wave_cell_multiplier: int,
    center_offset: np.ndarray | None = None,
    phase_offset: float = 0.0,
    radius_scale: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    """
    生成所有子胞元的散点点云，作为叠加层。
    """
    xs: List[np.ndarray] = []
    ys: List[np.ndarray] = []
    zs: List[np.ndarray] = []
    cs: List[np.ndarray] = []
    total_cells = 0
    shell_count = len(radii)
    unit_x = np.sin(child_theta_grid) * np.cos(child_phi_grid)
    unit_y = np.sin(child_theta_grid) * np.sin(child_phi_grid)
    unit_z = np.cos(child_theta_grid)

    for shell_idx, (radius, harmonic_order) in enumerate(zip(radii, harmonic_orders)):
        centers, _ = child_cell_centers(
            radius=float(radius),
            harmonic_order=int(harmonic_order),
            t=float(t),
            shell_index=shell_idx,
            shell_count=shell_count,
            multiplier=wave_cell_multiplier,
            center_offset=center_offset,
            phase_offset=phase_offset,
            radius_scale=radius_scale,
        )
        total_cells += len(centers)
        normalized_index = 0.0 if shell_count <= 1 else shell_idx / float(shell_count - 1)
        for center_idx, center in enumerate(centers):
            for child_shell_idx in range(max(1, child_shell_count)):
                child_phase = 0.9 * t + 0.7 * center_idx + 0.35 * child_shell_idx
                base_child_radius = float(radius) * child_cell_scale * (0.72 + 0.22 * child_shell_idx)
                local_mod = (
                    0.55 * np.cos((child_shell_idx + 1) * child_phi_grid - child_phase)
                    + 0.45 * np.sin((child_shell_idx + 2) * child_theta_grid + child_phase)
                )
                local_r = base_child_radius * (1.0 + (0.10 + 0.06 * normalized_index) * local_mod)
                xs.append(center[0] + local_r * unit_x)
                ys.append(center[1] + local_r * unit_y)
                zs.append(center[2] + local_r * unit_z)
                cs.append(local_mod + 0.2 * normalized_index)

    if not xs:
        empty = np.array([], dtype=np.float64)
        return empty, empty, empty, empty, 0
    return (
        np.concatenate([x.reshape(-1) for x in xs]),
        np.concatenate([y.reshape(-1) for y in ys]),
        np.concatenate([z.reshape(-1) for z in zs]),
        np.concatenate([c.reshape(-1) for c in cs]),
        total_cells,
    )


def wrapped_phase_delta(a: float, b: float) -> float:
    delta = abs(a - b)
    return min(delta, 2.0 * math.pi - delta)


def resonance_cell_points(
    radii: np.ndarray,
    harmonic_orders: np.ndarray,
    t: float,
    resonance_shell_count: int,
    resonance_cell_scale: float,
    child_theta_grid: np.ndarray,
    child_phi_grid: np.ndarray,
    wave_cell_multiplier: int,
    cell_a_offset: np.ndarray,
    cell_b_offset: np.ndarray,
    cell_b_phase_offset: float,
    cell_b_radius_scale: float,
    distance_threshold: float,
    phase_threshold: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    xs: List[np.ndarray] = []
    ys: List[np.ndarray] = []
    zs: List[np.ndarray] = []
    cs: List[np.ndarray] = []
    total_cells = 0
    unit_x = np.sin(child_theta_grid) * np.cos(child_phi_grid)
    unit_y = np.sin(child_theta_grid) * np.sin(child_phi_grid)
    unit_z = np.cos(child_theta_grid)

    for shell_idx, (radius, harmonic_order) in enumerate(zip(radii, harmonic_orders)):
        centers_a, phases_a = child_cell_centers(
            radius=float(radius),
            harmonic_order=int(harmonic_order),
            t=float(t),
            shell_index=shell_idx,
            shell_count=len(radii),
            multiplier=wave_cell_multiplier,
            center_offset=cell_a_offset,
            phase_offset=0.0,
            radius_scale=1.0,
        )
        centers_b, phases_b = child_cell_centers(
            radius=float(radius),
            harmonic_order=int(harmonic_order),
            t=float(t),
            shell_index=shell_idx,
            shell_count=len(radii),
            multiplier=wave_cell_multiplier,
            center_offset=cell_b_offset,
            phase_offset=cell_b_phase_offset,
            radius_scale=cell_b_radius_scale,
        )
        pair_count = min(len(centers_a), len(centers_b))
        for idx in range(pair_count):
            center_a = centers_a[idx]
            center_b = centers_b[idx]
            dist = float(np.linalg.norm(center_a - center_b))
            phase_diff = wrapped_phase_delta(float(phases_a[idx]), float(phases_b[idx]))
            if dist > distance_threshold or phase_diff > phase_threshold:
                continue
            total_cells += 1
            midpoint = 0.5 * (center_a + center_b)
            resonance_strength = max(0.0, 1.0 - dist / max(distance_threshold, 1e-6))
            phase_strength = max(0.0, 1.0 - phase_diff / max(phase_threshold, 1e-6))
            coupling = 0.5 * (resonance_strength + phase_strength)
            for child_shell_idx in range(max(1, resonance_shell_count)):
                local_phase = 1.1 * t + 0.65 * idx + 0.4 * child_shell_idx
                base_radius = float(radius) * resonance_cell_scale * (0.70 + 0.24 * child_shell_idx)
                local_mod = (
                    0.60 * np.cos((child_shell_idx + 1) * child_phi_grid - local_phase)
                    + 0.40 * np.sin((child_shell_idx + 2) * child_theta_grid + local_phase)
                )
                local_r = base_radius * (1.0 + (0.08 + 0.10 * coupling) * local_mod)
                xs.append(midpoint[0] + local_r * unit_x)
                ys.append(midpoint[1] + local_r * unit_y)
                zs.append(midpoint[2] + local_r * unit_z)
                cs.append(local_mod + 0.8 * coupling)

    if not xs:
        empty = np.array([], dtype=np.float64)
        return empty, empty, empty, empty, 0
    return (
        np.concatenate([x.reshape(-1) for x in xs]),
        np.concatenate([y.reshape(-1) for y in ys]),
        np.concatenate([z.reshape(-1) for z in zs]),
        np.concatenate([c.reshape(-1) for c in cs]),
        total_cells,
    )


def collect_wave_centers(
    radii: np.ndarray,
    harmonic_orders: np.ndarray,
    t: float,
    wave_cell_multiplier: int,
    center_offset: np.ndarray | None = None,
    phase_offset: float = 0.0,
    radius_scale: float = 1.0,
) -> np.ndarray:
    centers_all: List[np.ndarray] = []
    for shell_idx, (radius, harmonic_order) in enumerate(zip(radii, harmonic_orders)):
        centers, _ = child_cell_centers(
            radius=float(radius),
            harmonic_order=int(harmonic_order),
            t=float(t),
            shell_index=shell_idx,
            shell_count=len(radii),
            multiplier=wave_cell_multiplier,
            center_offset=center_offset,
            phase_offset=phase_offset,
            radius_scale=radius_scale,
        )
        if len(centers) > 0:
            centers_all.append(centers)
    if not centers_all:
        return np.zeros((0, 3), dtype=np.float64)
    return np.concatenate(centers_all, axis=0)


def pair_resonance_centroids(
    radii: np.ndarray,
    harmonic_orders: np.ndarray,
    t: float,
    wave_cell_multiplier: int,
    cell_a_offset: np.ndarray,
    cell_b_offset: np.ndarray,
    cell_b_phase_offset: float,
    cell_b_radius_scale: float,
    distance_threshold: float,
    phase_threshold: float,
) -> Tuple[np.ndarray, np.ndarray]:
    centroids: List[np.ndarray] = []
    couplings: List[float] = []
    for shell_idx, (radius, harmonic_order) in enumerate(zip(radii, harmonic_orders)):
        centers_a, phases_a = child_cell_centers(
            radius=float(radius),
            harmonic_order=int(harmonic_order),
            t=float(t),
            shell_index=shell_idx,
            shell_count=len(radii),
            multiplier=wave_cell_multiplier,
            center_offset=cell_a_offset,
        )
        centers_b, phases_b = child_cell_centers(
            radius=float(radius),
            harmonic_order=int(harmonic_order),
            t=float(t),
            shell_index=shell_idx,
            shell_count=len(radii),
            multiplier=wave_cell_multiplier,
            center_offset=cell_b_offset,
            phase_offset=cell_b_phase_offset,
            radius_scale=cell_b_radius_scale,
        )
        pair_count = min(len(centers_a), len(centers_b))
        for idx in range(pair_count):
            dist = float(np.linalg.norm(centers_a[idx] - centers_b[idx]))
            phase_diff = wrapped_phase_delta(float(phases_a[idx]), float(phases_b[idx]))
            if dist > distance_threshold or phase_diff > phase_threshold:
                continue
            resonance_strength = max(0.0, 1.0 - dist / max(distance_threshold, 1e-6))
            phase_strength = max(0.0, 1.0 - phase_diff / max(phase_threshold, 1e-6))
            centroids.append(0.5 * (centers_a[idx] + centers_b[idx]))
            couplings.append(0.5 * (resonance_strength + phase_strength))
    if not centroids:
        return np.zeros((0, 3), dtype=np.float64), np.zeros(0, dtype=np.float64)
    return np.vstack(centroids), np.asarray(couplings, dtype=np.float64)


def triple_resonance_centroids(
    radii: np.ndarray,
    harmonic_orders: np.ndarray,
    t: float,
    wave_cell_multiplier: int,
    cell_a_offset: np.ndarray,
    cell_b_offset: np.ndarray,
    cell_c_offset: np.ndarray,
    cell_b_phase_offset: float,
    cell_c_phase_offset: float,
    cell_b_radius_scale: float,
    cell_c_radius_scale: float,
    distance_threshold: float,
    phase_threshold: float,
) -> Tuple[np.ndarray, np.ndarray]:
    centroids: List[np.ndarray] = []
    couplings: List[float] = []
    for shell_idx, (radius, harmonic_order) in enumerate(zip(radii, harmonic_orders)):
        centers_a, phases_a = child_cell_centers(
            radius=float(radius),
            harmonic_order=int(harmonic_order),
            t=float(t),
            shell_index=shell_idx,
            shell_count=len(radii),
            multiplier=wave_cell_multiplier,
            center_offset=cell_a_offset,
        )
        centers_b, phases_b = child_cell_centers(
            radius=float(radius),
            harmonic_order=int(harmonic_order),
            t=float(t),
            shell_index=shell_idx,
            shell_count=len(radii),
            multiplier=wave_cell_multiplier,
            center_offset=cell_b_offset,
            phase_offset=cell_b_phase_offset,
            radius_scale=cell_b_radius_scale,
        )
        centers_c, phases_c = child_cell_centers(
            radius=float(radius),
            harmonic_order=int(harmonic_order),
            t=float(t),
            shell_index=shell_idx,
            shell_count=len(radii),
            multiplier=wave_cell_multiplier,
            center_offset=cell_c_offset,
            phase_offset=cell_c_phase_offset,
            radius_scale=cell_c_radius_scale,
        )
        count = min(len(centers_a), len(centers_b), len(centers_c))
        for idx in range(count):
            dist_ab = float(np.linalg.norm(centers_a[idx] - centers_b[idx]))
            dist_ac = float(np.linalg.norm(centers_a[idx] - centers_c[idx]))
            dist_bc = float(np.linalg.norm(centers_b[idx] - centers_c[idx]))
            phase_ab = wrapped_phase_delta(float(phases_a[idx]), float(phases_b[idx]))
            phase_ac = wrapped_phase_delta(float(phases_a[idx]), float(phases_c[idx]))
            phase_bc = wrapped_phase_delta(float(phases_b[idx]), float(phases_c[idx]))
            if max(dist_ab, dist_ac, dist_bc) > distance_threshold:
                continue
            if max(phase_ab, phase_ac, phase_bc) > phase_threshold:
                continue
            dist_strength = 1.0 - (dist_ab + dist_ac + dist_bc) / (3.0 * max(distance_threshold, 1e-6))
            phase_strength = 1.0 - (phase_ab + phase_ac + phase_bc) / (3.0 * max(phase_threshold, 1e-6))
            centroids.append((centers_a[idx] + centers_b[idx] + centers_c[idx]) / 3.0)
            couplings.append(max(0.0, 0.5 * (dist_strength + phase_strength)))
    if not centroids:
        return np.zeros((0, 3), dtype=np.float64), np.zeros(0, dtype=np.float64)
    return np.vstack(centroids), np.asarray(couplings, dtype=np.float64)


def downward_recursive_points(
    seed_centers: np.ndarray,
    t: float,
    depth: int,
    base_scale: float,
    scale_decay: float,
    theta_grid: np.ndarray,
    phi_grid: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    if depth <= 1 or len(seed_centers) == 0:
        empty = np.array([], dtype=np.float64)
        return empty, empty, empty, empty, 0
    xs: List[np.ndarray] = []
    ys: List[np.ndarray] = []
    zs: List[np.ndarray] = []
    cs: List[np.ndarray] = []
    unit_x = np.sin(theta_grid) * np.cos(phi_grid)
    unit_y = np.sin(theta_grid) * np.sin(phi_grid)
    unit_z = np.cos(theta_grid)
    current = np.asarray(seed_centers, dtype=np.float64)
    total = 0
    for level in range(2, depth + 1):
        local_scale = base_scale * (scale_decay ** (level - 2))
        next_centers: List[np.ndarray] = []
        for idx, center in enumerate(current):
            local_phase = 0.8 * t + 0.45 * idx + 0.25 * level
            local_mod = 0.58 * np.cos(level * phi_grid - local_phase) + 0.42 * np.sin((level + 1) * theta_grid + local_phase)
            local_r = local_scale * (1.0 + 0.10 * local_mod)
            xs.append(center[0] + local_r * unit_x)
            ys.append(center[1] + local_r * unit_y)
            zs.append(center[2] + local_r * unit_z)
            cs.append(local_mod - 0.15 * level)
            total += 1
            if level < depth:
                for branch in range(3):
                    angle = (2.0 * math.pi * branch / 3.0) + local_phase
                    direction = np.array(
                        [
                            math.cos(angle),
                            math.sin(angle),
                            0.25 * math.sin(local_phase + branch),
                        ],
                        dtype=np.float64,
                    )
                    next_centers.append(center + (1.9 * local_scale) * direction)
        current = np.asarray(next_centers, dtype=np.float64) if next_centers else np.zeros((0, 3), dtype=np.float64)
        if len(current) == 0:
            break
    if not xs:
        empty = np.array([], dtype=np.float64)
        return empty, empty, empty, empty, 0
    return (
        np.concatenate([x.reshape(-1) for x in xs]),
        np.concatenate([y.reshape(-1) for y in ys]),
        np.concatenate([z.reshape(-1) for z in zs]),
        np.concatenate([c.reshape(-1) for c in cs]),
        total,
    )


def estimate_center_phases(centers: np.ndarray) -> np.ndarray:
    if len(centers) == 0:
        return np.zeros(0, dtype=np.float64)
    return np.arctan2(centers[:, 1], centers[:, 0]).astype(np.float64)


def downward_recursive_centers(
    seed_centers: np.ndarray,
    t: float,
    depth: int,
    base_scale: float,
    scale_decay: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    返回向下递归过程中所有新增中心及其层级编号。
    """
    if depth <= 1 or len(seed_centers) == 0:
        return np.zeros((0, 3), dtype=np.float64), np.zeros(0, dtype=np.int64)
    current = np.asarray(seed_centers, dtype=np.float64)
    centers_all: List[np.ndarray] = []
    levels_all: List[np.ndarray] = []
    for level in range(2, depth + 1):
        local_scale = base_scale * (scale_decay ** (level - 2))
        next_centers: List[np.ndarray] = []
        for idx, center in enumerate(current):
            local_phase = 0.8 * t + 0.45 * idx + 0.25 * level
            for branch in range(3):
                angle = (2.0 * math.pi * branch / 3.0) + local_phase
                direction = np.array(
                    [
                        math.cos(angle),
                        math.sin(angle),
                        0.25 * math.sin(local_phase + branch),
                    ],
                    dtype=np.float64,
                )
                next_centers.append(center + (1.9 * local_scale) * direction)
        if not next_centers:
            break
        current = np.asarray(next_centers, dtype=np.float64)
        centers_all.append(current)
        levels_all.append(np.full(len(current), level, dtype=np.int64))
    if not centers_all:
        return np.zeros((0, 3), dtype=np.float64), np.zeros(0, dtype=np.int64)
    return np.concatenate(centers_all, axis=0), np.concatenate(levels_all, axis=0)


def cross_hierarchy_resonance_centroids(
    parent_centers: np.ndarray,
    parent_phases: np.ndarray,
    descendant_centers: np.ndarray,
    descendant_levels: np.ndarray,
    distance_threshold: float,
    phase_threshold: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    父层中心与更深层中心之间的跨层级共振中点。
    """
    if len(parent_centers) == 0 or len(descendant_centers) == 0:
        return np.zeros((0, 3), dtype=np.float64), np.zeros(0, dtype=np.float64)
    descendant_phases = estimate_center_phases(descendant_centers)
    centroids: List[np.ndarray] = []
    couplings: List[float] = []
    for p_idx, p_center in enumerate(parent_centers):
        phase_p = float(parent_phases[p_idx]) if p_idx < len(parent_phases) else float(math.atan2(p_center[1], p_center[0]))
        distances = np.linalg.norm(descendant_centers - p_center[None, :], axis=1)
        close_indices = np.where(distances <= distance_threshold)[0]
        for d_idx in close_indices:
            phase_d = float(descendant_phases[d_idx])
            phase_diff = wrapped_phase_delta(phase_p, phase_d)
            if phase_diff > phase_threshold:
                continue
            level = int(descendant_levels[d_idx]) if d_idx < len(descendant_levels) else 2
            dist_strength = max(0.0, 1.0 - float(distances[d_idx]) / max(distance_threshold, 1e-6))
            phase_strength = max(0.0, 1.0 - phase_diff / max(phase_threshold, 1e-6))
            level_weight = 1.0 / max(1.0, float(level - 1))
            coupling = (0.45 * dist_strength) + (0.35 * phase_strength) + (0.20 * level_weight)
            centroids.append(0.5 * (p_center + descendant_centers[d_idx]))
            couplings.append(float(coupling))
    if not centroids:
        return np.zeros((0, 3), dtype=np.float64), np.zeros(0, dtype=np.float64)
    return np.vstack(centroids), np.asarray(couplings, dtype=np.float64)


def upward_recursive_points(
    seed_centers: np.ndarray,
    seed_weights: np.ndarray,
    t: float,
    depth: int,
    base_scale: float,
    scale_growth: float,
    theta_grid: np.ndarray,
    phi_grid: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    if depth <= 0 or len(seed_centers) == 0:
        empty = np.array([], dtype=np.float64)
        return empty, empty, empty, empty, 0
    xs: List[np.ndarray] = []
    ys: List[np.ndarray] = []
    zs: List[np.ndarray] = []
    cs: List[np.ndarray] = []
    unit_x = np.sin(theta_grid) * np.cos(phi_grid)
    unit_y = np.sin(theta_grid) * np.sin(phi_grid)
    unit_z = np.cos(theta_grid)
    weights = seed_weights if len(seed_weights) == len(seed_centers) else np.ones(len(seed_centers), dtype=np.float64)
    total = 0
    for level in range(1, depth + 1):
        centroid = np.average(seed_centers, axis=0, weights=np.maximum(weights, 1e-6))
        local_scale = base_scale * (scale_growth ** (level - 1))
        local_phase = 0.55 * t + 0.4 * level
        local_mod = 0.52 * np.cos(level * phi_grid - local_phase) + 0.48 * np.sin((level + 2) * theta_grid + local_phase)
        local_r = local_scale * (1.0 + 0.12 * local_mod)
        xs.append(centroid[0] + local_r * unit_x)
        ys.append(centroid[1] + local_r * unit_y)
        zs.append(centroid[2] + local_r * unit_z)
        cs.append(local_mod + 0.35 * level)
        total += 1
        seed_centers = np.asarray([centroid], dtype=np.float64)
        weights = np.asarray([float(np.mean(weights)) + 0.1 * level], dtype=np.float64)
    return (
        np.concatenate([x.reshape(-1) for x in xs]),
        np.concatenate([y.reshape(-1) for y in ys]),
        np.concatenate([z.reshape(-1) for z in zs]),
        np.concatenate([c.reshape(-1) for c in cs]),
        total,
    )


def make_shell_trace(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    modulation: np.ndarray,
    shell_index: int,
    harmonic_order: int,
    radius: float,
) -> Dict[str, object]:
    normalized_color = modulation.astype(np.float64)
    return {
        "type": "scatter3d",
        "mode": "markers",
        "x": x.reshape(-1).astype(float).tolist(),
        "y": y.reshape(-1).astype(float).tolist(),
        "z": z.reshape(-1).astype(float).tolist(),
        "hovertemplate": (
            f"shell={shell_index}<br>harmonic={harmonic_order}"
            f"<br>base radius={radius:.3f}<br>mod=%{{marker.color:.3f}}<extra></extra>"
        ),
        "marker": {
            "size": 2.2,
            "color": normalized_color.reshape(-1).astype(float).tolist(),
            "colorscale": "Plasma",
            "cmin": -1.0,
            "cmax": 1.0,
            "opacity": 0.74,
            "showscale": False,
        },
        "name": f"shell {shell_index}",
        "showlegend": False,
    }


def build_animation_frames(
    times: np.ndarray,
    radii: np.ndarray,
    harmonic_orders: np.ndarray,
    theta_grid: np.ndarray,
    phi_grid: np.ndarray,
    spawn_wave_cells: bool,
    wave_cell_multiplier: int,
    child_shell_count: int,
    child_cell_scale: float,
    child_theta_grid: np.ndarray,
    child_phi_grid: np.ndarray,
    dual_cells: bool,
    third_cell: bool,
    cell_separation: float,
    cell_phase_offset: float,
    cell2_radius_scale: float,
    cell3_phase_offset: float,
    cell3_radius_scale: float,
    cell_triangle_height: float,
    spawn_resonance_cells: bool,
    resonance_distance_threshold: float,
    resonance_phase_threshold: float,
    resonance_cell_scale: float,
    resonance_shell_count: int,
    downward_depth: int,
    downward_scale_decay: float,
    upward_depth: int,
    upward_scale_growth: float,
    macro_cell_scale: float,
    cross_hierarchy_resonance: bool,
    cross_hierarchy_distance_threshold: float,
    cross_hierarchy_phase_threshold: float,
    cross_hierarchy_cell_scale: float,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    frames: List[Dict[str, object]] = []
    first_traces: List[Dict[str, object]] = []
    use_multi = dual_cells or third_cell
    cell_a_offset = np.array([-0.5 * cell_separation, 0.0, 0.0], dtype=np.float64)
    cell_b_offset = np.array([0.5 * cell_separation, 0.0, 0.0], dtype=np.float64)
    triangle_height = cell_triangle_height if cell_triangle_height > 0.0 else (math.sqrt(3.0) * 0.5 * cell_separation)
    cell_c_offset = np.array([0.0, triangle_height, 0.0], dtype=np.float64)
    for frame_idx, t in enumerate(times):
        frame_traces: List[Dict[str, object]] = []
        for shell_idx, (radius, harmonic_order) in enumerate(zip(radii, harmonic_orders), start=1):
            x, y, z, modulation = shell_surface(
                radius=radius,
                harmonic_order=int(harmonic_order),
                t=float(t),
                theta_grid=theta_grid,
                phi_grid=phi_grid,
                shell_index=shell_idx - 1,
                shell_count=len(radii),
                center_offset=cell_a_offset if use_multi else np.zeros(3, dtype=np.float64),
            )
            frame_traces.append(
                make_shell_trace(
                    x=x,
                    y=y,
                    z=z,
                    modulation=modulation,
                    shell_index=shell_idx,
                    harmonic_order=int(harmonic_order),
                    radius=float(radius),
                )
            )
            if use_multi:
                x2, y2, z2, modulation2 = shell_surface(
                    radius=radius,
                    harmonic_order=int(harmonic_order),
                    t=float(t),
                    theta_grid=theta_grid,
                    phi_grid=phi_grid,
                    shell_index=shell_idx - 1,
                    shell_count=len(radii),
                    phase_offset=cell_phase_offset,
                    center_offset=cell_b_offset,
                    radius_scale=cell2_radius_scale,
                )
                frame_traces.append(
                    {
                        **make_shell_trace(
                            x=x2,
                            y=y2,
                            z=z2,
                            modulation=modulation2,
                            shell_index=shell_idx,
                            harmonic_order=int(harmonic_order),
                            radius=float(radius) * cell2_radius_scale,
                        ),
                        "marker": {
                            "size": 2.1,
                            "color": modulation2.reshape(-1).astype(float).tolist(),
                            "colorscale": "Viridis",
                            "cmin": -1.0,
                            "cmax": 1.0,
                            "opacity": 0.62,
                            "showscale": False,
                        },
                        "name": f"shell B {shell_idx}",
                    }
                )
            if third_cell:
                x3, y3, z3, modulation3 = shell_surface(
                    radius=radius,
                    harmonic_order=int(harmonic_order),
                    t=float(t),
                    theta_grid=theta_grid,
                    phi_grid=phi_grid,
                    shell_index=shell_idx - 1,
                    shell_count=len(radii),
                    phase_offset=cell3_phase_offset,
                    center_offset=cell_c_offset,
                    radius_scale=cell3_radius_scale,
                )
                frame_traces.append(
                    {
                        **make_shell_trace(
                            x=x3,
                            y=y3,
                            z=z3,
                            modulation=modulation3,
                            shell_index=shell_idx,
                            harmonic_order=int(harmonic_order),
                            radius=float(radius) * cell3_radius_scale,
                        ),
                        "marker": {
                            "size": 2.0,
                            "color": modulation3.reshape(-1).astype(float).tolist(),
                            "colorscale": "Inferno",
                            "cmin": -1.0,
                            "cmax": 1.0,
                            "opacity": 0.58,
                            "showscale": False,
                        },
                        "name": f"shell C {shell_idx}",
                    }
                )
        if spawn_wave_cells:
            child_x, child_y, child_z, child_c, _ = child_cell_points(
                radii=radii,
                harmonic_orders=harmonic_orders,
                t=float(t),
                child_shell_count=child_shell_count,
                child_cell_scale=child_cell_scale,
                child_theta_grid=child_theta_grid,
                child_phi_grid=child_phi_grid,
                wave_cell_multiplier=wave_cell_multiplier,
                center_offset=cell_a_offset if use_multi else np.zeros(3, dtype=np.float64),
            )
            frame_traces.append(
                {
                    "type": "scatter3d",
                    "mode": "markers",
                    "x": child_x.astype(float).tolist(),
                    "y": child_y.astype(float).tolist(),
                    "z": child_z.astype(float).tolist(),
                    "marker": {
                        "size": 1.6,
                        "color": child_c.astype(float).tolist(),
                        "colorscale": "Turbo",
                        "cmin": -1.4,
                        "cmax": 1.4,
                        "opacity": 0.42,
                        "showscale": False,
                    },
                    "name": "wave cells",
                    "showlegend": False,
                    "hovertemplate": "child cell cloud<br>mod=%{marker.color:.3f}<extra></extra>",
                }
            )
            if use_multi:
                child_x2, child_y2, child_z2, child_c2, _ = child_cell_points(
                    radii=radii,
                    harmonic_orders=harmonic_orders,
                    t=float(t),
                    child_shell_count=child_shell_count,
                    child_cell_scale=child_cell_scale,
                    child_theta_grid=child_theta_grid,
                    child_phi_grid=child_phi_grid,
                    wave_cell_multiplier=wave_cell_multiplier,
                    center_offset=cell_b_offset,
                    phase_offset=cell_phase_offset,
                    radius_scale=cell2_radius_scale,
                )
                frame_traces.append(
                    {
                        "type": "scatter3d",
                        "mode": "markers",
                        "x": child_x2.astype(float).tolist(),
                        "y": child_y2.astype(float).tolist(),
                        "z": child_z2.astype(float).tolist(),
                        "marker": {
                            "size": 1.5,
                            "color": child_c2.astype(float).tolist(),
                            "colorscale": "Cividis",
                            "cmin": -1.4,
                            "cmax": 1.4,
                            "opacity": 0.32,
                            "showscale": False,
                        },
                        "name": "wave cells B",
                        "showlegend": False,
                        "hovertemplate": "child cell cloud B<br>mod=%{marker.color:.3f}<extra></extra>",
                    }
                )
            if third_cell:
                child_x3, child_y3, child_z3, child_c3, _ = child_cell_points(
                    radii=radii,
                    harmonic_orders=harmonic_orders,
                    t=float(t),
                    child_shell_count=child_shell_count,
                    child_cell_scale=child_cell_scale,
                    child_theta_grid=child_theta_grid,
                    child_phi_grid=child_phi_grid,
                    wave_cell_multiplier=wave_cell_multiplier,
                    center_offset=cell_c_offset,
                    phase_offset=cell3_phase_offset,
                    radius_scale=cell3_radius_scale,
                )
                frame_traces.append(
                    {
                        "type": "scatter3d",
                        "mode": "markers",
                        "x": child_x3.astype(float).tolist(),
                        "y": child_y3.astype(float).tolist(),
                        "z": child_z3.astype(float).tolist(),
                        "marker": {
                            "size": 1.5,
                            "color": child_c3.astype(float).tolist(),
                            "colorscale": "Portland",
                            "cmin": -1.4,
                            "cmax": 1.4,
                            "opacity": 0.28,
                            "showscale": False,
                        },
                        "name": "wave cells C",
                        "showlegend": False,
                        "hovertemplate": "child cell cloud C<br>mod=%{marker.color:.3f}<extra></extra>",
                    }
                )
        pair_seed_centers: List[np.ndarray] = []
        pair_seed_weights: List[np.ndarray] = []
        if use_multi and spawn_resonance_cells:
            res_x, res_y, res_z, res_c, _ = resonance_cell_points(
                radii=radii,
                harmonic_orders=harmonic_orders,
                t=float(t),
                resonance_shell_count=resonance_shell_count,
                resonance_cell_scale=resonance_cell_scale,
                child_theta_grid=child_theta_grid,
                child_phi_grid=child_phi_grid,
                wave_cell_multiplier=wave_cell_multiplier,
                cell_a_offset=cell_a_offset,
                cell_b_offset=cell_b_offset,
                cell_b_phase_offset=cell_phase_offset,
                cell_b_radius_scale=cell2_radius_scale,
                distance_threshold=resonance_distance_threshold,
                phase_threshold=resonance_phase_threshold,
            )
            frame_traces.append(
                {
                    "type": "scatter3d",
                    "mode": "markers",
                    "x": res_x.astype(float).tolist(),
                    "y": res_y.astype(float).tolist(),
                    "z": res_z.astype(float).tolist(),
                    "marker": {
                        "size": 2.2,
                        "color": res_c.astype(float).tolist(),
                        "colorscale": "Magma",
                        "cmin": -1.4,
                        "cmax": 1.8,
                        "opacity": 0.70,
                        "showscale": False,
                    },
                    "name": "resonance cells",
                    "showlegend": False,
                    "hovertemplate": "resonance cell<br>coupling=%{marker.color:.3f}<extra></extra>",
                }
            )
            ab_centers, ab_weights = pair_resonance_centroids(
                radii=radii,
                harmonic_orders=harmonic_orders,
                t=float(t),
                wave_cell_multiplier=wave_cell_multiplier,
                cell_a_offset=cell_a_offset,
                cell_b_offset=cell_b_offset,
                cell_b_phase_offset=cell_phase_offset,
                cell_b_radius_scale=cell2_radius_scale,
                distance_threshold=resonance_distance_threshold,
                phase_threshold=resonance_phase_threshold,
            )
            if len(ab_centers) > 0:
                pair_seed_centers.append(ab_centers)
                pair_seed_weights.append(ab_weights)
            if third_cell:
                ac_centers, ac_weights = pair_resonance_centroids(
                    radii=radii,
                    harmonic_orders=harmonic_orders,
                    t=float(t),
                    wave_cell_multiplier=wave_cell_multiplier,
                    cell_a_offset=cell_a_offset,
                    cell_b_offset=cell_c_offset,
                    cell_b_phase_offset=cell3_phase_offset,
                    cell_b_radius_scale=cell3_radius_scale,
                    distance_threshold=resonance_distance_threshold,
                    phase_threshold=resonance_phase_threshold,
                )
                bc_centers, bc_weights = pair_resonance_centroids(
                    radii=radii,
                    harmonic_orders=harmonic_orders,
                    t=float(t),
                    wave_cell_multiplier=wave_cell_multiplier,
                    cell_a_offset=cell_b_offset,
                    cell_b_offset=cell_c_offset,
                    cell_b_phase_offset=cell3_phase_offset - cell_phase_offset,
                    cell_b_radius_scale=cell3_radius_scale / max(cell2_radius_scale, 1e-6),
                    distance_threshold=resonance_distance_threshold,
                    phase_threshold=resonance_phase_threshold,
                )
                for centers, weights, name, colorscale, opacity in [
                    (ac_centers, ac_weights, "resonance AC", "Sunset", 0.54),
                    (bc_centers, bc_weights, "resonance BC", "Temps", 0.50),
                ]:
                    if len(centers) == 0:
                        continue
                    pair_seed_centers.append(centers)
                    pair_seed_weights.append(weights)
                    frame_traces.append(
                        {
                            "type": "scatter3d",
                            "mode": "markers",
                            "x": centers[:, 0].astype(float).tolist(),
                            "y": centers[:, 1].astype(float).tolist(),
                            "z": centers[:, 2].astype(float).tolist(),
                            "marker": {
                                "size": 2.3,
                                "color": weights.astype(float).tolist(),
                                "colorscale": colorscale,
                                "cmin": 0.0,
                                "cmax": 1.0,
                                "opacity": opacity,
                                "showscale": False,
                            },
                            "name": name,
                            "showlegend": False,
                            "hovertemplate": f"{name}<br>coupling=%{{marker.color:.3f}}<extra></extra>",
                        }
                    )
                triple_centers, triple_weights = triple_resonance_centroids(
                    radii=radii,
                    harmonic_orders=harmonic_orders,
                    t=float(t),
                    wave_cell_multiplier=wave_cell_multiplier,
                    cell_a_offset=cell_a_offset,
                    cell_b_offset=cell_b_offset,
                    cell_c_offset=cell_c_offset,
                    cell_b_phase_offset=cell_phase_offset,
                    cell_c_phase_offset=cell3_phase_offset,
                    cell_b_radius_scale=cell2_radius_scale,
                    cell_c_radius_scale=cell3_radius_scale,
                    distance_threshold=resonance_distance_threshold,
                    phase_threshold=resonance_phase_threshold,
                )
                if len(triple_centers) > 0:
                    pair_seed_centers.append(triple_centers)
                    pair_seed_weights.append(triple_weights)
                    frame_traces.append(
                        {
                            "type": "scatter3d",
                            "mode": "markers",
                            "x": triple_centers[:, 0].astype(float).tolist(),
                            "y": triple_centers[:, 1].astype(float).tolist(),
                            "z": triple_centers[:, 2].astype(float).tolist(),
                            "marker": {
                                "size": 2.8,
                                "color": triple_weights.astype(float).tolist(),
                                "colorscale": "Electric",
                                "cmin": 0.0,
                                "cmax": 1.0,
                                "opacity": 0.82,
                                "showscale": False,
                            },
                            "name": "triple resonance",
                            "showlegend": False,
                            "hovertemplate": "triple resonance<br>coupling=%{marker.color:.3f}<extra></extra>",
                        }
                    )
        if spawn_wave_cells and downward_depth > 1:
            seed_centers = [collect_wave_centers(
                radii=radii,
                harmonic_orders=harmonic_orders,
                t=float(t),
                wave_cell_multiplier=wave_cell_multiplier,
                center_offset=cell_a_offset if use_multi else np.zeros(3, dtype=np.float64),
            )]
            if use_multi:
                seed_centers.append(
                    collect_wave_centers(
                        radii=radii,
                        harmonic_orders=harmonic_orders,
                        t=float(t),
                        wave_cell_multiplier=wave_cell_multiplier,
                        center_offset=cell_b_offset,
                        phase_offset=cell_phase_offset,
                        radius_scale=cell2_radius_scale,
                    )
                )
            if third_cell:
                seed_centers.append(
                    collect_wave_centers(
                        radii=radii,
                        harmonic_orders=harmonic_orders,
                        t=float(t),
                        wave_cell_multiplier=wave_cell_multiplier,
                        center_offset=cell_c_offset,
                        phase_offset=cell3_phase_offset,
                        radius_scale=cell3_radius_scale,
                    )
                )
            merged_seed = np.concatenate([s for s in seed_centers if len(s) > 0], axis=0) if any(len(s) > 0 for s in seed_centers) else np.zeros((0, 3), dtype=np.float64)
            micro_x, micro_y, micro_z, micro_c, _ = downward_recursive_points(
                seed_centers=merged_seed,
                t=float(t),
                depth=downward_depth,
                base_scale=float(np.min(radii)) * child_cell_scale * 0.55,
                scale_decay=downward_scale_decay,
                theta_grid=child_theta_grid,
                phi_grid=child_phi_grid,
            )
            frame_traces.append(
                {
                    "type": "scatter3d",
                    "mode": "markers",
                    "x": micro_x.astype(float).tolist(),
                    "y": micro_y.astype(float).tolist(),
                    "z": micro_z.astype(float).tolist(),
                    "marker": {
                        "size": 1.2,
                        "color": micro_c.astype(float).tolist(),
                        "colorscale": "IceFire",
                        "cmin": -2.0,
                        "cmax": 1.0,
                        "opacity": 0.24,
                        "showscale": False,
                    },
                    "name": "downward recursion",
                    "showlegend": False,
                    "hovertemplate": "downward recursive cell<br>level=%{marker.color:.3f}<extra></extra>",
                }
            )
            if cross_hierarchy_resonance and len(merged_seed) > 0:
                descendant_centers, descendant_levels = downward_recursive_centers(
                    seed_centers=merged_seed,
                    t=float(t),
                    depth=downward_depth,
                    base_scale=float(np.min(radii)) * child_cell_scale * 0.55,
                    scale_decay=downward_scale_decay,
                )
                cross_centers, cross_weights = cross_hierarchy_resonance_centroids(
                    parent_centers=merged_seed,
                    parent_phases=estimate_center_phases(merged_seed),
                    descendant_centers=descendant_centers,
                    descendant_levels=descendant_levels,
                    distance_threshold=cross_hierarchy_distance_threshold,
                    phase_threshold=cross_hierarchy_phase_threshold,
                )
                if len(cross_centers) > 0:
                    pair_seed_centers.append(cross_centers)
                    pair_seed_weights.append(cross_weights)
                    cross_mod = cross_weights[:, None, None] + (
                        0.55 * np.cos(child_phi_grid - 0.9 * float(t))
                        + 0.45 * np.sin(2.0 * child_theta_grid + 0.6 * float(t))
                    )[None, :, :]
                    cross_r = float(np.min(radii)) * cross_hierarchy_cell_scale * (1.0 + 0.08 * cross_mod)
                    cross_x = (cross_centers[:, 0][:, None, None] + cross_r * np.sin(child_theta_grid)[None, :, :] * np.cos(child_phi_grid)[None, :, :]).reshape(-1)
                    cross_y = (cross_centers[:, 1][:, None, None] + cross_r * np.sin(child_theta_grid)[None, :, :] * np.sin(child_phi_grid)[None, :, :]).reshape(-1)
                    cross_z = (cross_centers[:, 2][:, None, None] + cross_r * np.cos(child_theta_grid)[None, :, :]).reshape(-1)
                    frame_traces.append(
                        {
                            "type": "scatter3d",
                            "mode": "markers",
                            "x": cross_x.astype(float).tolist(),
                            "y": cross_y.astype(float).tolist(),
                            "z": cross_z.astype(float).tolist(),
                            "marker": {
                                "size": 1.8,
                                "color": np.repeat(cross_weights, child_theta_grid.size).astype(float).tolist(),
                                "colorscale": "YlGnBu",
                                "cmin": 0.0,
                                "cmax": 1.2,
                                "opacity": 0.52,
                                "showscale": False,
                            },
                            "name": "cross hierarchy resonance",
                            "showlegend": False,
                            "hovertemplate": "cross-hierarchy cell<br>coupling=%{marker.color:.3f}<extra></extra>",
                        }
                    )
        if upward_depth > 0 and pair_seed_centers:
            macro_seed_centers = np.concatenate(pair_seed_centers, axis=0)
            macro_seed_weights = np.concatenate(pair_seed_weights, axis=0)
            macro_x, macro_y, macro_z, macro_c, _ = upward_recursive_points(
                seed_centers=macro_seed_centers,
                seed_weights=macro_seed_weights,
                t=float(t),
                depth=upward_depth,
                base_scale=float(np.max(radii)) * macro_cell_scale,
                scale_growth=upward_scale_growth,
                theta_grid=theta_grid,
                phi_grid=phi_grid,
            )
            frame_traces.append(
                {
                    "type": "scatter3d",
                    "mode": "markers",
                    "x": macro_x.astype(float).tolist(),
                    "y": macro_y.astype(float).tolist(),
                    "z": macro_z.astype(float).tolist(),
                    "marker": {
                        "size": 2.6,
                        "color": macro_c.astype(float).tolist(),
                        "colorscale": "Bluered",
                        "cmin": -1.0,
                        "cmax": 2.0,
                        "opacity": 0.46,
                        "showscale": False,
                    },
                    "name": "upward recursion",
                    "showlegend": False,
                    "hovertemplate": "macro recursive cell<br>level=%{marker.color:.3f}<extra></extra>",
                }
            )
        if frame_idx == 0:
            first_traces = frame_traces
        frames.append({"name": str(frame_idx), "data": frame_traces})
    return first_traces, frames


def save_plotly_shell_animation_html(
    run_dir: Path,
    timestamp: str,
    traces: List[Dict[str, object]],
    frames: List[Dict[str, object]],
    times: np.ndarray,
) -> None:
    slider_steps = []
    for idx, t in enumerate(times):
        slider_steps.append(
            {
                "label": f"t={t:.2f}",
                "method": "animate",
                "args": [[str(idx)], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}}],
            }
        )

    layout = {
        "title": {"text": "Cellular Shell Basis and Resonance Animation"},
        "scene": {
            "xaxis": {"title": "x", "range": [-4.6, 4.6]},
            "yaxis": {"title": "y", "range": [-4.6, 4.6]},
            "zaxis": {"title": "z", "range": [-4.6, 4.6]},
            "aspectmode": "cube",
            "camera": {"eye": {"x": 1.55, "y": -1.45, "z": 1.15}},
        },
        "paper_bgcolor": "#0b1020",
        "plot_bgcolor": "#0b1020",
        "font": {"color": "#e5e7eb"},
        "updatemenus": [
            {
                "type": "buttons",
                "direction": "left",
                "x": 0.0,
                "y": 1.12,
                "showactive": False,
                "buttons": [
                    {
                        "label": "Play",
                        "method": "animate",
                        "args": [None, {"fromcurrent": True, "frame": {"duration": 80, "redraw": False}, "transition": {"duration": 0}}],
                    },
                    {
                        "label": "Pause",
                        "method": "animate",
                        "args": [[None], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}}],
                    },
                    {
                        "label": "Reset",
                        "method": "animate",
                        "args": [["0"], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}}],
                    },
                ],
            }
        ],
        "sliders": [{"pad": {"t": 35}, "currentvalue": {"prefix": "Time: "}, "steps": slider_steps}],
        "margin": {"l": 0, "r": 0, "t": 55, "b": 0},
    }

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>Single Cellular Shell Basis Animation</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body style="margin:0;background:#0b1020;">
  <div id="plot" style="width:100vw;height:100vh;"></div>
  <script>
    const data = {json.dumps(traces, ensure_ascii=False)};
    const layout = {json.dumps(layout, ensure_ascii=False)};
    const frames = {json.dumps(frames, ensure_ascii=False)};
    Plotly.newPlot("plot", data, layout, {{responsive: true}}).then(function() {{
      Plotly.addFrames("plot", frames);
    }});
  </script>
</body>
</html>
"""
    (run_dir / f"interactive_shell_basis_{timestamp}.html").write_text(html, encoding="utf-8")


def save_matplotlib_shell_animation_gif(
    run_dir: Path,
    timestamp: str,
    times: np.ndarray,
    radii: np.ndarray,
    harmonic_orders: np.ndarray,
    theta_grid: np.ndarray,
    phi_grid: np.ndarray,
    fps: int,
    spawn_wave_cells: bool,
    wave_cell_multiplier: int,
    child_shell_count: int,
    child_cell_scale: float,
    child_theta_grid: np.ndarray,
    child_phi_grid: np.ndarray,
    dual_cells: bool,
    third_cell: bool,
    cell_separation: float,
    cell_phase_offset: float,
    cell2_radius_scale: float,
    cell3_phase_offset: float,
    cell3_radius_scale: float,
    cell_triangle_height: float,
    spawn_resonance_cells: bool,
    resonance_distance_threshold: float,
    resonance_phase_threshold: float,
    resonance_cell_scale: float,
    resonance_shell_count: int,
    downward_depth: int,
    downward_scale_decay: float,
    upward_depth: int,
    upward_scale_growth: float,
    macro_cell_scale: float,
    cross_hierarchy_resonance: bool,
    cross_hierarchy_distance_threshold: float,
    cross_hierarchy_phase_threshold: float,
    cross_hierarchy_cell_scale: float,
) -> None:
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    fig = plt.figure(figsize=(8.2, 7.4))
    ax = fig.add_subplot(111, projection="3d")
    fig.patch.set_facecolor("#0b1020")
    ax.set_facecolor("#0b1020")
    use_multi = dual_cells or third_cell
    cell_a_offset = np.array([-0.5 * cell_separation, 0.0, 0.0], dtype=np.float64)
    cell_b_offset = np.array([0.5 * cell_separation, 0.0, 0.0], dtype=np.float64)
    triangle_height = cell_triangle_height if cell_triangle_height > 0.0 else (math.sqrt(3.0) * 0.5 * cell_separation)
    cell_c_offset = np.array([0.0, triangle_height, 0.0], dtype=np.float64)

    def style_axes(current_time: float) -> None:
        span = max(4.8, 0.85 * cell_separation + 4.4)
        ax.set_xlim(-span, span)
        ax.set_ylim(-span, span)
        ax.set_zlim(-4.8, 4.8)
        ax.set_xlabel("x", color="#e5e7eb")
        ax.set_ylabel("y", color="#e5e7eb")
        ax.set_zlabel("z", color="#e5e7eb")
        ax.set_title(f"Cellular Resonance Basis\nTime = {current_time:.2f}", color="#e5e7eb")
        ax.tick_params(colors="#cbd5e1")
        ax.xaxis.pane.set_alpha(0.08)
        ax.yaxis.pane.set_alpha(0.08)
        ax.zaxis.pane.set_alpha(0.08)
        ax.grid(alpha=0.15)
        ax.view_init(elev=26, azim=-58)

    def update(frame_idx: int):
        ax.cla()
        current_time = float(times[frame_idx])
        for shell_idx, (radius, harmonic_order) in enumerate(zip(radii, harmonic_orders), start=1):
            x, y, z, modulation = shell_surface(
                radius=float(radius),
                harmonic_order=int(harmonic_order),
                t=current_time,
                theta_grid=theta_grid,
                phi_grid=phi_grid,
                shell_index=shell_idx - 1,
                shell_count=len(radii),
                center_offset=cell_a_offset if use_multi else np.zeros(3, dtype=np.float64),
            )
            ax.scatter(
                x.reshape(-1),
                y.reshape(-1),
                z.reshape(-1),
                c=modulation.reshape(-1),
                cmap="plasma",
                vmin=-1.0,
                vmax=1.0,
                s=7.0,
                alpha=0.70,
                linewidths=0.0,
            )
            if use_multi:
                x2, y2, z2, modulation2 = shell_surface(
                    radius=float(radius),
                    harmonic_order=int(harmonic_order),
                    t=current_time,
                    theta_grid=theta_grid,
                    phi_grid=phi_grid,
                    shell_index=shell_idx - 1,
                    shell_count=len(radii),
                    phase_offset=cell_phase_offset,
                    center_offset=cell_b_offset,
                    radius_scale=cell2_radius_scale,
                )
                ax.scatter(
                    x2.reshape(-1),
                    y2.reshape(-1),
                    z2.reshape(-1),
                    c=modulation2.reshape(-1),
                    cmap="viridis",
                    vmin=-1.0,
                    vmax=1.0,
                    s=6.0,
                    alpha=0.54,
                    linewidths=0.0,
                )
            if third_cell:
                x3, y3, z3, modulation3 = shell_surface(
                    radius=float(radius),
                    harmonic_order=int(harmonic_order),
                    t=current_time,
                    theta_grid=theta_grid,
                    phi_grid=phi_grid,
                    shell_index=shell_idx - 1,
                    shell_count=len(radii),
                    phase_offset=cell3_phase_offset,
                    center_offset=cell_c_offset,
                    radius_scale=cell3_radius_scale,
                )
                ax.scatter(
                    x3.reshape(-1),
                    y3.reshape(-1),
                    z3.reshape(-1),
                    c=modulation3.reshape(-1),
                    cmap="inferno",
                    vmin=-1.0,
                    vmax=1.0,
                    s=5.5,
                    alpha=0.48,
                    linewidths=0.0,
                )
        if spawn_wave_cells:
            child_x, child_y, child_z, child_c, _ = child_cell_points(
                radii=radii,
                harmonic_orders=harmonic_orders,
                t=current_time,
                child_shell_count=child_shell_count,
                child_cell_scale=child_cell_scale,
                child_theta_grid=child_theta_grid,
                child_phi_grid=child_phi_grid,
                wave_cell_multiplier=wave_cell_multiplier,
                center_offset=cell_a_offset if use_multi else np.zeros(3, dtype=np.float64),
            )
            ax.scatter(
                child_x,
                child_y,
                child_z,
                c=child_c,
                cmap="turbo",
                vmin=-1.4,
                vmax=1.4,
                s=3.0,
                alpha=0.30,
                linewidths=0.0,
            )
            if use_multi:
                child_x2, child_y2, child_z2, child_c2, _ = child_cell_points(
                    radii=radii,
                    harmonic_orders=harmonic_orders,
                    t=current_time,
                    child_shell_count=child_shell_count,
                    child_cell_scale=child_cell_scale,
                    child_theta_grid=child_theta_grid,
                    child_phi_grid=child_phi_grid,
                    wave_cell_multiplier=wave_cell_multiplier,
                    center_offset=cell_b_offset,
                    phase_offset=cell_phase_offset,
                    radius_scale=cell2_radius_scale,
                )
                ax.scatter(
                    child_x2,
                    child_y2,
                    child_z2,
                    c=child_c2,
                    cmap="cividis",
                    vmin=-1.4,
                    vmax=1.4,
                    s=2.5,
                    alpha=0.24,
                    linewidths=0.0,
                )
            if third_cell:
                child_x3, child_y3, child_z3, child_c3, _ = child_cell_points(
                    radii=radii,
                    harmonic_orders=harmonic_orders,
                    t=current_time,
                    child_shell_count=child_shell_count,
                    child_cell_scale=child_cell_scale,
                    child_theta_grid=child_theta_grid,
                    child_phi_grid=child_phi_grid,
                    wave_cell_multiplier=wave_cell_multiplier,
                    center_offset=cell_c_offset,
                    phase_offset=cell3_phase_offset,
                    radius_scale=cell3_radius_scale,
                )
                ax.scatter(
                    child_x3,
                    child_y3,
                    child_z3,
                    c=child_c3,
                    cmap="plasma",
                    vmin=-1.4,
                    vmax=1.4,
                    s=2.2,
                    alpha=0.20,
                    linewidths=0.0,
                )
        pair_seed_centers: List[np.ndarray] = []
        pair_seed_weights: List[np.ndarray] = []
        if use_multi and spawn_resonance_cells:
            res_x, res_y, res_z, res_c, _ = resonance_cell_points(
                radii=radii,
                harmonic_orders=harmonic_orders,
                t=current_time,
                resonance_shell_count=resonance_shell_count,
                resonance_cell_scale=resonance_cell_scale,
                child_theta_grid=child_theta_grid,
                child_phi_grid=child_phi_grid,
                wave_cell_multiplier=wave_cell_multiplier,
                cell_a_offset=cell_a_offset,
                cell_b_offset=cell_b_offset,
                cell_b_phase_offset=cell_phase_offset,
                cell_b_radius_scale=cell2_radius_scale,
                distance_threshold=resonance_distance_threshold,
                phase_threshold=resonance_phase_threshold,
            )
            ax.scatter(
                res_x,
                res_y,
                res_z,
                c=res_c,
                cmap="magma",
                vmin=-1.4,
                vmax=1.8,
                s=4.0,
                alpha=0.62,
                linewidths=0.0,
            )
            ab_centers, ab_weights = pair_resonance_centroids(
                radii=radii,
                harmonic_orders=harmonic_orders,
                t=current_time,
                wave_cell_multiplier=wave_cell_multiplier,
                cell_a_offset=cell_a_offset,
                cell_b_offset=cell_b_offset,
                cell_b_phase_offset=cell_phase_offset,
                cell_b_radius_scale=cell2_radius_scale,
                distance_threshold=resonance_distance_threshold,
                phase_threshold=resonance_phase_threshold,
            )
            if len(ab_centers) > 0:
                pair_seed_centers.append(ab_centers)
                pair_seed_weights.append(ab_weights)
            if third_cell:
                ac_centers, ac_weights = pair_resonance_centroids(
                    radii=radii,
                    harmonic_orders=harmonic_orders,
                    t=current_time,
                    wave_cell_multiplier=wave_cell_multiplier,
                    cell_a_offset=cell_a_offset,
                    cell_b_offset=cell_c_offset,
                    cell_b_phase_offset=cell3_phase_offset,
                    cell_b_radius_scale=cell3_radius_scale,
                    distance_threshold=resonance_distance_threshold,
                    phase_threshold=resonance_phase_threshold,
                )
                bc_centers, bc_weights = pair_resonance_centroids(
                    radii=radii,
                    harmonic_orders=harmonic_orders,
                    t=current_time,
                    wave_cell_multiplier=wave_cell_multiplier,
                    cell_a_offset=cell_b_offset,
                    cell_b_offset=cell_c_offset,
                    cell_b_phase_offset=cell3_phase_offset - cell_phase_offset,
                    cell_b_radius_scale=cell3_radius_scale / max(cell2_radius_scale, 1e-6),
                    distance_threshold=resonance_distance_threshold,
                    phase_threshold=resonance_phase_threshold,
                )
                triple_centers, triple_weights = triple_resonance_centroids(
                    radii=radii,
                    harmonic_orders=harmonic_orders,
                    t=current_time,
                    wave_cell_multiplier=wave_cell_multiplier,
                    cell_a_offset=cell_a_offset,
                    cell_b_offset=cell_b_offset,
                    cell_c_offset=cell_c_offset,
                    cell_b_phase_offset=cell_phase_offset,
                    cell_c_phase_offset=cell3_phase_offset,
                    cell_b_radius_scale=cell2_radius_scale,
                    cell_c_radius_scale=cell3_radius_scale,
                    distance_threshold=resonance_distance_threshold,
                    phase_threshold=resonance_phase_threshold,
                )
                for centers, weights, cmap, size, alpha in [
                    (ac_centers, ac_weights, "spring", 2.6, 0.36),
                    (bc_centers, bc_weights, "winter", 2.6, 0.36),
                    (triple_centers, triple_weights, "cool", 3.4, 0.68),
                ]:
                    if len(centers) == 0:
                        continue
                    pair_seed_centers.append(centers)
                    pair_seed_weights.append(weights)
                    ax.scatter(
                        centers[:, 0],
                        centers[:, 1],
                        centers[:, 2],
                        c=weights,
                        cmap=cmap,
                        vmin=0.0,
                        vmax=1.0,
                        s=size,
                        alpha=alpha,
                        linewidths=0.0,
                    )
        if spawn_wave_cells and downward_depth > 1:
            seed_sets = [collect_wave_centers(
                radii=radii,
                harmonic_orders=harmonic_orders,
                t=current_time,
                wave_cell_multiplier=wave_cell_multiplier,
                center_offset=cell_a_offset if use_multi else np.zeros(3, dtype=np.float64),
            )]
            if use_multi:
                seed_sets.append(
                    collect_wave_centers(
                        radii=radii,
                        harmonic_orders=harmonic_orders,
                        t=current_time,
                        wave_cell_multiplier=wave_cell_multiplier,
                        center_offset=cell_b_offset,
                        phase_offset=cell_phase_offset,
                        radius_scale=cell2_radius_scale,
                    )
                )
            if third_cell:
                seed_sets.append(
                    collect_wave_centers(
                        radii=radii,
                        harmonic_orders=harmonic_orders,
                        t=current_time,
                        wave_cell_multiplier=wave_cell_multiplier,
                        center_offset=cell_c_offset,
                        phase_offset=cell3_phase_offset,
                        radius_scale=cell3_radius_scale,
                    )
                )
            merged_seed = np.concatenate([s for s in seed_sets if len(s) > 0], axis=0) if any(len(s) > 0 for s in seed_sets) else np.zeros((0, 3), dtype=np.float64)
            micro_x, micro_y, micro_z, micro_c, _ = downward_recursive_points(
                seed_centers=merged_seed,
                t=current_time,
                depth=downward_depth,
                base_scale=float(np.min(radii)) * child_cell_scale * 0.55,
                scale_decay=downward_scale_decay,
                theta_grid=child_theta_grid,
                phi_grid=child_phi_grid,
            )
            ax.scatter(
                micro_x,
                micro_y,
                micro_z,
                c=micro_c,
                cmap="afmhot",
                vmin=-2.0,
                vmax=1.0,
                s=1.8,
                alpha=0.18,
                linewidths=0.0,
            )
            if cross_hierarchy_resonance and len(merged_seed) > 0:
                descendant_centers, descendant_levels = downward_recursive_centers(
                    seed_centers=merged_seed,
                    t=current_time,
                    depth=downward_depth,
                    base_scale=float(np.min(radii)) * child_cell_scale * 0.55,
                    scale_decay=downward_scale_decay,
                )
                cross_centers, cross_weights = cross_hierarchy_resonance_centroids(
                    parent_centers=merged_seed,
                    parent_phases=estimate_center_phases(merged_seed),
                    descendant_centers=descendant_centers,
                    descendant_levels=descendant_levels,
                    distance_threshold=cross_hierarchy_distance_threshold,
                    phase_threshold=cross_hierarchy_phase_threshold,
                )
                if len(cross_centers) > 0:
                    pair_seed_centers.append(cross_centers)
                    pair_seed_weights.append(cross_weights)
                    ax.scatter(
                        cross_centers[:, 0],
                        cross_centers[:, 1],
                        cross_centers[:, 2],
                        c=cross_weights,
                        cmap="YlGnBu",
                        vmin=0.0,
                        vmax=1.2,
                        s=3.2,
                        alpha=0.58,
                        linewidths=0.0,
                    )
        if upward_depth > 0 and pair_seed_centers:
            macro_seed_centers = np.concatenate(pair_seed_centers, axis=0)
            macro_seed_weights = np.concatenate(pair_seed_weights, axis=0)
            macro_x, macro_y, macro_z, macro_c, _ = upward_recursive_points(
                seed_centers=macro_seed_centers,
                seed_weights=macro_seed_weights,
                t=current_time,
                depth=upward_depth,
                base_scale=float(np.max(radii)) * macro_cell_scale,
                scale_growth=upward_scale_growth,
                theta_grid=theta_grid,
                phi_grid=phi_grid,
            )
            ax.scatter(
                macro_x,
                macro_y,
                macro_z,
                c=macro_c,
                cmap="bwr",
                vmin=-1.0,
                vmax=2.0,
                s=4.4,
                alpha=0.34,
                linewidths=0.0,
            )
        style_axes(current_time)
        return []

    ani = animation.FuncAnimation(fig, update, frames=len(times), interval=max(40, int(round(1000 / max(1, fps)))), blit=False)
    out_path = run_dir / f"shell_basis_{timestamp}.gif"
    writer = animation.PillowWriter(fps=max(1, fps))
    ani.save(out_path, writer=writer)
    plt.close(fig)


def save_summary(run_dir: Path, timestamp: str, summary: ShellAnimationSummary, radii: np.ndarray, harmonic_orders: np.ndarray) -> None:
    payload = asdict(summary)
    payload["shell_radii"] = radii.astype(float).tolist()
    payload["harmonic_orders"] = harmonic_orders.astype(int).tolist()
    (run_dir / f"summary_{timestamp}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    args = parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = create_output_dir() / f"cellular_shell_basis_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    all_times = np.arange(0.0, args.duration + 0.5 * args.dt, args.dt, dtype=np.float64)
    stride = max(1, int(math.ceil(len(all_times) / max(1, args.target_frames))))
    times = all_times[::stride]

    radii, radii_profile, radii_source = build_shell_radii(
        shell_count=args.shell_count,
        min_radius=args.min_radius,
        max_radius=args.max_radius,
        profile=args.radii_profile,
        radial_bias=args.radial_bias,
        radial_log_k=args.radial_log_k,
        radial_exp_k=args.radial_exp_k,
        radii_csv=args.radii_csv,
        normalize_custom=args.no_normalize_custom,
    )
    harmonic_orders = shell_harmonic_orders(args.shell_count, args.max_harmonic_order)
    theta_grid, phi_grid = spherical_grid(args.theta_count, args.phi_count)
    child_theta_grid, child_phi_grid = spherical_grid(args.child_theta_count, args.child_phi_count)

    traces, frames = build_animation_frames(
        times,
        radii,
        harmonic_orders,
        theta_grid,
        phi_grid,
        spawn_wave_cells=args.spawn_wave_cells,
        wave_cell_multiplier=args.wave_cell_multiplier,
        child_shell_count=args.child_shell_count,
        child_cell_scale=args.child_cell_scale,
        child_theta_grid=child_theta_grid,
        child_phi_grid=child_phi_grid,
        dual_cells=args.dual_cells,
        third_cell=args.third_cell,
        cell_separation=args.cell_separation,
        cell_phase_offset=args.cell_phase_offset,
        cell2_radius_scale=args.cell2_radius_scale,
        cell3_phase_offset=args.cell3_phase_offset,
        cell3_radius_scale=args.cell3_radius_scale,
        cell_triangle_height=args.cell_triangle_height,
        spawn_resonance_cells=args.spawn_resonance_cells,
        resonance_distance_threshold=args.resonance_distance_threshold,
        resonance_phase_threshold=args.resonance_phase_threshold,
        resonance_cell_scale=args.resonance_cell_scale,
        resonance_shell_count=args.resonance_shell_count,
        downward_depth=args.downward_depth,
        downward_scale_decay=args.downward_scale_decay,
        upward_depth=args.upward_depth,
        upward_scale_growth=args.upward_scale_growth,
        macro_cell_scale=args.macro_cell_scale,
        cross_hierarchy_resonance=args.cross_hierarchy_resonance,
        cross_hierarchy_distance_threshold=args.cross_hierarchy_distance_threshold,
        cross_hierarchy_phase_threshold=args.cross_hierarchy_phase_threshold,
        cross_hierarchy_cell_scale=args.cross_hierarchy_cell_scale,
    )
    save_plotly_shell_animation_html(run_dir, timestamp, traces, frames, times)
    save_matplotlib_shell_animation_gif(
        run_dir=run_dir,
        timestamp=timestamp,
        times=times,
        radii=radii,
        harmonic_orders=harmonic_orders,
        theta_grid=theta_grid,
        phi_grid=phi_grid,
        fps=args.gif_fps,
        spawn_wave_cells=args.spawn_wave_cells,
        wave_cell_multiplier=args.wave_cell_multiplier,
        child_shell_count=args.child_shell_count,
        child_cell_scale=args.child_cell_scale,
        child_theta_grid=child_theta_grid,
        child_phi_grid=child_phi_grid,
        dual_cells=args.dual_cells,
        third_cell=args.third_cell,
        cell_separation=args.cell_separation,
        cell_phase_offset=args.cell_phase_offset,
        cell2_radius_scale=args.cell2_radius_scale,
        cell3_phase_offset=args.cell3_phase_offset,
        cell3_radius_scale=args.cell3_radius_scale,
        cell_triangle_height=args.cell_triangle_height,
        spawn_resonance_cells=args.spawn_resonance_cells,
        resonance_distance_threshold=args.resonance_distance_threshold,
        resonance_phase_threshold=args.resonance_phase_threshold,
        resonance_cell_scale=args.resonance_cell_scale,
        resonance_shell_count=args.resonance_shell_count,
        downward_depth=args.downward_depth,
        downward_scale_decay=args.downward_scale_decay,
        upward_depth=args.upward_depth,
        upward_scale_growth=args.upward_scale_growth,
        macro_cell_scale=args.macro_cell_scale,
        cross_hierarchy_resonance=args.cross_hierarchy_resonance,
        cross_hierarchy_distance_threshold=args.cross_hierarchy_distance_threshold,
        cross_hierarchy_phase_threshold=args.cross_hierarchy_phase_threshold,
        cross_hierarchy_cell_scale=args.cross_hierarchy_cell_scale,
    )

    spacings = np.diff(radii) if len(radii) > 1 else np.array([0.0], dtype=np.float64)
    effective_multi_cells = 1 + int(args.dual_cells or args.third_cell) + int(args.third_cell)
    child_cell_count_estimate = 0
    if args.spawn_wave_cells:
        child_cell_count_estimate = int(np.sum(np.maximum(1, harmonic_orders * max(1, args.wave_cell_multiplier))))
        child_cell_count_estimate *= effective_multi_cells
    resonance_cell_count_estimate = 0
    if (args.dual_cells or args.third_cell) and args.spawn_resonance_cells:
        pair_count = 1 if not args.third_cell else 4
        resonance_cell_count_estimate = int(pair_count * np.sum(np.maximum(1, harmonic_orders * max(1, args.wave_cell_multiplier))))
    cross_hierarchy_cell_count_estimate = 0
    if args.cross_hierarchy_resonance and args.spawn_wave_cells and args.downward_depth > 1:
        cross_hierarchy_cell_count_estimate = int(
            effective_multi_cells
            * np.sum(np.maximum(1, harmonic_orders * max(1, args.wave_cell_multiplier)))
            * max(1, args.downward_depth - 1)
        )
    macro_cell_count_estimate = int(max(0, args.upward_depth))
    summary = ShellAnimationSummary(
        shell_count=int(args.shell_count),
        duration=float(args.duration),
        dt=float(args.dt),
        frame_count=int(len(times)),
        min_radius=float(args.min_radius),
        max_radius=float(args.max_radius),
        radial_bias=float(args.radial_bias),
        max_harmonic_order=int(args.max_harmonic_order),
        mean_shell_spacing=float(np.mean(spacings)),
        min_shell_spacing=float(np.min(spacings)),
        max_shell_spacing=float(np.max(spacings)),
        radii_profile=radii_profile,
        radii_source=radii_source,
        wave_cells_enabled=bool(args.spawn_wave_cells),
        child_cell_count_estimate=child_cell_count_estimate,
        dual_cells_enabled=bool(args.dual_cells or args.third_cell),
        resonance_cells_enabled=bool((args.dual_cells or args.third_cell) and args.spawn_resonance_cells),
        resonance_cell_count_estimate=resonance_cell_count_estimate,
        third_cells_enabled=bool(args.third_cell),
        downward_recursion_depth=int(args.downward_depth),
        upward_recursion_depth=int(args.upward_depth),
        macro_cell_count_estimate=macro_cell_count_estimate,
        cross_hierarchy_resonance_enabled=bool(args.cross_hierarchy_resonance),
        cross_hierarchy_cell_count_estimate=cross_hierarchy_cell_count_estimate,
    )
    save_summary(run_dir, timestamp, summary, radii, harmonic_orders)

    print(f"Run directory: {run_dir}")
    print(f"Frames: {len(times)}")
    print(f"Shell count: {args.shell_count}")
    print(f"Radii profile: {radii_profile}")
    print(f"Radii source: {radii_source}")
    print(f"Dual cells: {args.dual_cells or args.third_cell}")
    print(f"Third cell: {args.third_cell}")
    print(f"Resonance cells: {(args.dual_cells or args.third_cell) and args.spawn_resonance_cells}")
    print(f"Cross-hierarchy resonance: {args.cross_hierarchy_resonance}")
    print(f"Downward depth: {args.downward_depth}")
    print(f"Upward depth: {args.upward_depth}")
    print(f"Mean shell spacing: {summary.mean_shell_spacing:.4f}")


if __name__ == "__main__":
    main()
