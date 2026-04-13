#!/usr/bin/env python3
"""
零先验类氢色荷场原型（有效模型声明见 docs/EFFECTIVE_MODEL_STATEMENT.md）

目标：
- 不依赖任何分子 YAML、原子模板或外部实验数据
- 从随机三分量复场 psi(x, t) in C^3 出发
- 在各向同性扩散 + 自聚焦/排斥平衡 + 局域 SU(3) 旋转下演化
- 支持角动量通道、时频谱分析、2D/3D 扩展和 Plotly 时间滑块可视化

说明：
- 这是一个结构动力学原型（无量纲有效模型），不是标准量子色动力学或量子化学求解器
- “类氢”指：从无先验随机场中涌现单中心局域结构，并呈现近径向衰减
- “类轨道”指：引入角动量通道后，出现带节点或角向分裂的模式
- 脚本中的“电子/中微子/夸克”仅作为“模式家族”占位命名，非标准模型粒子的一一对应
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Sequence, Tuple

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


SQRT3 = math.sqrt(3.0)
EPS = 1e-12


@dataclass
class EmergenceSummary:
    dimensions: int
    width: int
    height: int
    depth: int
    steps: int
    dt: float
    seed: int
    total_mass: float
    final_peak_density: float
    final_mean_density: float
    final_peak_to_mean_ratio: float
    effective_radius: float
    participation_ratio: float
    center_x: float
    center_y: float
    center_z: float
    final_mean_a3: float
    final_mean_a8: float
    probe_dominant_frequency: float
    ridge_frequency_mean: float
    ridge_frequency_std: float
    ridge_energy_share_mean: float
    ridge_energy_share_min: float
    ridge_energy_share_max: float
    center_drift_mean: float
    center_drift_max: float
    angular_momentum: int
    angular_node_count: int
    angular_zero_crossings: int
    dominant_angular_harmonic: int
    angular_contrast: float
    angular_probe_radius: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="零先验类氢色荷场原型")
    parser.add_argument("--dimensions", type=int, choices=[2, 3], default=2, help="空间维度：2 或 3")
    parser.add_argument("--width", type=int, default=41, help="场宽度")
    parser.add_argument("--height", type=int, default=41, help="场高度")
    parser.add_argument("--depth", type=int, default=17, help="三维场深度（仅 dimensions=3 生效）")
    parser.add_argument("--duration", type=float, default=12.0, help="总演化时间")
    parser.add_argument("--dt", type=float, default=0.02, help="时间步长")
    parser.add_argument("--seed", type=int, default=20260409, help="随机种子")
    parser.add_argument("--diffusion", type=float, default=0.18, help="离散拉普拉斯扩散强度")
    parser.add_argument("--attraction", type=float, default=2.6, help="自聚焦强度")
    parser.add_argument("--repulsion", type=float, default=2.2, help="饱和排斥强度")
    parser.add_argument("--su3-spin", type=float, default=0.22, help="局域 SU(3) 旋转强度")
    parser.add_argument("--angular-momentum", type=int, default=0, help="角动量通道量子数 m；0 表示 s-like，1 表示 p-like，2 表示 d-like")
    parser.add_argument("--angular-gain", type=float, default=0.0, help="角动量通道强度；大于 0 时更容易出现带节点的角向模式")
    parser.add_argument("--periodic", action="store_true", help="是否使用周期边界")
    parser.add_argument("--save-stride", type=int, default=5, help="保存时序采样步长")
    parser.add_argument("--probe-radius", type=float, default=2.0, help="中心附近探针区域半径，用于时频谱分析")
    parser.add_argument("--probe-ring-width", type=float, default=0.6, help="窄环带探针宽度，用于多探针时频分析")
    parser.add_argument("--probe-angles", type=int, default=16, help="环带上角向探针数量")
    parser.add_argument("--stft-window", type=int, default=64, help="短时傅里叶窗口长度")
    parser.add_argument("--stft-hop", type=int, default=8, help="短时傅里叶窗口步长")
    parser.add_argument("--ridge-jump-penalty", type=float, default=0.18, help="连续脊线提取的频率跳变惩罚")
    parser.add_argument("--target-frames", type=int, default=80, help="Plotly 时间滑块目标帧数上限")
    return parser.parse_args()


def gell_mann_matrices() -> np.ndarray:
    matrices = np.zeros((8, 3, 3), dtype=np.complex128)
    matrices[0] = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 0]], dtype=np.complex128)
    matrices[1] = np.array([[0, -1j, 0], [1j, 0, 0], [0, 0, 0]], dtype=np.complex128)
    matrices[2] = np.array([[1, 0, 0], [0, -1, 0], [0, 0, 0]], dtype=np.complex128)
    matrices[3] = np.array([[0, 0, 1], [0, 0, 0], [1, 0, 0]], dtype=np.complex128)
    matrices[4] = np.array([[0, 0, -1j], [0, 0, 0], [1j, 0, 0]], dtype=np.complex128)
    matrices[5] = np.array([[0, 0, 0], [0, 0, 1], [0, 1, 0]], dtype=np.complex128)
    matrices[6] = np.array([[0, 0, 0], [0, 0, -1j], [0, 1j, 0]], dtype=np.complex128)
    matrices[7] = np.array([[1 / SQRT3, 0, 0], [0, 1 / SQRT3, 0], [0, 0, -2 / SQRT3]], dtype=np.complex128)
    return matrices


def initialize_field(dimensions: int, height: int, width: int, depth: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    spatial_shape = (height, width) if dimensions == 2 else (depth, height, width)
    psi = (rng.normal(size=spatial_shape + (3,)) + 1j * rng.normal(size=spatial_shape + (3,))).astype(np.complex128)
    psi /= max(np.sqrt(np.sum(np.abs(psi) ** 2)), EPS)
    return psi


def generic_laplacian(field: np.ndarray, periodic: bool) -> np.ndarray:
    spatial_ndim = field.ndim - 1
    if periodic:
        lap = np.zeros_like(field)
        for axis in range(spatial_ndim):
            lap += np.roll(field, 1, axis=axis) + np.roll(field, -1, axis=axis) - 2.0 * field
        return lap

    pad_width = [(1, 1)] * spatial_ndim + [(0, 0)]
    padded = np.pad(field, pad_width, mode="edge")
    center = [slice(1, -1)] * spatial_ndim + [slice(None)]
    center_view = padded[tuple(center)]
    lap = np.zeros_like(field)
    for axis in range(spatial_ndim):
        plus = list(center)
        minus = list(center)
        plus[axis] = slice(2, None)
        minus[axis] = slice(None, -2)
        lap += padded[tuple(plus)] + padded[tuple(minus)] - 2.0 * center_view
    return lap


def density_matrices(psi: np.ndarray) -> np.ndarray:
    return np.einsum("...i,...j->...ij", psi, np.conjugate(psi), dtype=np.complex128)


def su3_components(rho: np.ndarray, lambdas: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    traces = np.trace(rho, axis1=-2, axis2=-1).real
    scalar_s = traces / SQRT3
    comps = np.zeros(rho.shape[:-2] + (8,), dtype=np.float64)
    for alpha in range(8):
        comps[..., alpha] = np.einsum("...ij,ji->...", rho, lambdas[alpha]).real
    return scalar_s, comps


def coordinate_grids(dimensions: int, height: int, width: int, depth: int) -> Tuple[np.ndarray, ...]:
    if dimensions == 2:
        yy, xx = np.mgrid[0:height, 0:width]
        return xx.astype(np.float64), yy.astype(np.float64)
    zz, yy, xx = np.mgrid[0:depth, 0:height, 0:width]
    return xx.astype(np.float64), yy.astype(np.float64), zz.astype(np.float64)


def compute_center(density: np.ndarray, dimensions: int) -> Tuple[float, float, float]:
    mass = float(np.sum(density))
    if dimensions == 2:
        yy, xx = np.mgrid[0 : density.shape[0], 0 : density.shape[1]]
        cx = float(np.sum(xx * density) / max(mass, EPS))
        cy = float(np.sum(yy * density) / max(mass, EPS))
        return cx, cy, 0.0
    zz, yy, xx = np.mgrid[0 : density.shape[0], 0 : density.shape[1], 0 : density.shape[2]]
    cx = float(np.sum(xx * density) / max(mass, EPS))
    cy = float(np.sum(yy * density) / max(mass, EPS))
    cz = float(np.sum(zz * density) / max(mass, EPS))
    return cx, cy, cz


def compute_effective_radius(density: np.ndarray, center: Tuple[float, float, float], dimensions: int) -> float:
    cx, cy, cz = center
    if dimensions == 2:
        yy, xx = np.mgrid[0 : density.shape[0], 0 : density.shape[1]]
        r2 = (xx - cx) ** 2 + (yy - cy) ** 2
    else:
        zz, yy, xx = np.mgrid[0 : density.shape[0], 0 : density.shape[1], 0 : density.shape[2]]
        r2 = (xx - cx) ** 2 + (yy - cy) ** 2 + (zz - cz) ** 2
    return float(np.sqrt(np.sum(r2 * density) / max(np.sum(density), EPS)))


def radial_profile(density: np.ndarray, center: Tuple[float, float, float], dimensions: int, bins: int = 24) -> Tuple[np.ndarray, np.ndarray]:
    cx, cy, cz = center
    if dimensions == 2:
        yy, xx = np.mgrid[0 : density.shape[0], 0 : density.shape[1]]
        rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    else:
        zz, yy, xx = np.mgrid[0 : density.shape[0], 0 : density.shape[1], 0 : density.shape[2]]
        rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2 + (zz - cz) ** 2)
    r_max = float(np.max(rr))
    edges = np.linspace(0.0, r_max, bins + 1)
    values = np.zeros(bins, dtype=np.float64)
    centers = 0.5 * (edges[:-1] + edges[1:])
    for i in range(bins):
        mask = (rr >= edges[i]) & (rr < edges[i + 1])
        if np.any(mask):
            values[i] = float(np.mean(density[mask]))
    return centers, values


def bilinear_sample_2d(field: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    x0 = np.floor(xs).astype(int)
    y0 = np.floor(ys).astype(int)
    x0 = np.clip(x0, 0, field.shape[1] - 1)
    y0 = np.clip(y0, 0, field.shape[0] - 1)
    x1 = np.clip(x0 + 1, 0, field.shape[1] - 1)
    y1 = np.clip(y0 + 1, 0, field.shape[0] - 1)
    tx = xs - x0
    ty = ys - y0

    f00 = field[y0, x0]
    f10 = field[y0, x1]
    f01 = field[y1, x0]
    f11 = field[y1, x1]
    return (1.0 - tx) * (1.0 - ty) * f00 + tx * (1.0 - ty) * f10 + (1.0 - tx) * ty * f01 + tx * ty * f11


def circular_smooth(values: np.ndarray, window: int) -> np.ndarray:
    window = max(3, int(window) | 1)
    pad = window // 2
    kernel = np.ones(window, dtype=np.float64) / float(window)
    extended = np.concatenate([values[-pad:], values, values[:pad]])
    return np.convolve(extended, kernel, mode="valid")


def count_circular_zero_crossings(signal: np.ndarray, threshold: float) -> int:
    signed = np.sign(signal)
    signed[np.abs(signal) < threshold] = 0.0
    if np.all(signed == 0.0):
        return 0

    filled = signed.copy()
    last = 0.0
    for i in range(len(filled)):
        if filled[i] == 0.0:
            filled[i] = last
        else:
            last = filled[i]

    last = 0.0
    for i in range(len(filled) - 1, -1, -1):
        if filled[i] == 0.0:
            filled[i] = last
        else:
            last = filled[i]

    if np.any(filled == 0.0):
        return 0
    return int(np.sum(filled != np.roll(filled, -1)))


def angular_node_signature_2d(
    density: np.ndarray,
    center: Tuple[float, float, float],
    effective_radius: float,
    samples: int = 180,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, int, int, int, float, float]:
    cx, cy, _ = center
    max_radius = float(min(cx, cy, density.shape[1] - 1 - cx, density.shape[0] - 1 - cy))
    if max_radius <= 2.5:
        empty = np.zeros(samples, dtype=np.float64)
        theta = np.linspace(-math.pi, math.pi, samples, endpoint=False, dtype=np.float64)
        return theta, empty, empty, 0, 0, 0, 0.0, 0.0

    probe_radius = float(np.clip(min(max(2.5, 0.55 * effective_radius), max_radius - 1.0), 2.5, max_radius))
    thetas = np.linspace(-math.pi, math.pi, samples, endpoint=False, dtype=np.float64)
    radial_scales = np.array([0.88, 1.0, 1.12], dtype=np.float64)
    sampled_profiles = []
    for scale in radial_scales:
        rr = float(np.clip(probe_radius * scale, 1.5, max_radius))
        xs = cx + rr * np.cos(thetas)
        ys = cy + rr * np.sin(thetas)
        sampled_profiles.append(bilinear_sample_2d(density, xs, ys))

    profile = np.mean(np.stack(sampled_profiles, axis=0), axis=0)
    contrast = profile - float(np.mean(profile))
    smoothed_contrast = circular_smooth(contrast, window= nine_window())
    harmonic_power = np.abs(np.fft.rfft(smoothed_contrast))
    harmonic_power[0] = 0.0
    harmonic_cap = min(12, len(harmonic_power) - 1)
    dominant_harmonic = 0
    if harmonic_cap >= 1 and np.any(harmonic_power[1 : harmonic_cap + 1] > EPS):
        dominant_harmonic = int(np.argmax(harmonic_power[1 : harmonic_cap + 1]) + 1)
    zero_threshold = max(0.08 * float(np.max(np.abs(smoothed_contrast))), 0.15 * float(np.std(smoothed_contrast)), EPS)
    zero_crossings = count_circular_zero_crossings(smoothed_contrast, zero_threshold)
    inferred_node_count = zero_crossings // 2
    angular_contrast = float(np.max(np.abs(smoothed_contrast)) / max(float(np.mean(profile)), EPS))
    if angular_contrast < 0.02:
        dominant_harmonic = 0
        zero_crossings = 0
        inferred_node_count = 0
    return thetas, profile, smoothed_contrast, zero_crossings, inferred_node_count, dominant_harmonic, angular_contrast, probe_radius


def nine_window() -> int:
    return 9


def angular_generator_field(
    dimensions: int,
    density: np.ndarray,
    lambdas: np.ndarray,
    angular_momentum: int,
    angular_gain: float,
) -> np.ndarray:
    if angular_momentum == 0 or angular_gain <= 0.0:
        return np.zeros(density.shape + (3, 3), dtype=np.complex128)

    cx, cy, _ = compute_center(density, dimensions)
    if dimensions == 2:
        yy, xx = np.mgrid[0 : density.shape[0], 0 : density.shape[1]]
        theta = np.arctan2(yy - cy, xx - cx)
        rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    else:
        zz, yy, xx = np.mgrid[0 : density.shape[0], 0 : density.shape[1], 0 : density.shape[2]]
        theta = np.arctan2(yy - cy, xx - cx)
        rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2 + (zz - density.shape[0] / 2.0) ** 2)

    radial_envelope = rr / (1.0 + rr)
    cos_m = np.cos(angular_momentum * theta)
    sin_m = np.sin(angular_momentum * theta)
    generators = np.zeros(density.shape + (3, 3), dtype=np.complex128)
    generators += angular_gain * radial_envelope[..., None, None] * cos_m[..., None, None] * lambdas[0]
    generators += angular_gain * radial_envelope[..., None, None] * sin_m[..., None, None] * lambdas[1]
    generators += 0.5 * angular_gain * radial_envelope[..., None, None] * cos_m[..., None, None] * lambdas[3]
    return generators


def field_derivative(
    psi: np.ndarray,
    lambdas: np.ndarray,
    dimensions: int,
    periodic: bool,
    diffusion: float,
    attraction: float,
    repulsion: float,
    su3_spin: float,
    angular_momentum: int,
    angular_gain: float,
) -> np.ndarray:
    rho = density_matrices(psi)
    scalar_s, comps = su3_components(rho, lambdas)
    density = np.sum(np.abs(psi) ** 2, axis=-1)

    nonlinear_gain = attraction * density - repulsion * density * density
    lap = generic_laplacian(psi, periodic)

    local_generators = np.zeros(psi.shape[:-1] + (3, 3), dtype=np.complex128)
    local_generators += 0.5 * comps[..., 2][..., None, None] * lambdas[2]
    local_generators += 0.5 * comps[..., 7][..., None, None] * lambdas[7]
    local_generators += 0.25 * comps[..., 0][..., None, None] * lambdas[0]
    local_generators += angular_generator_field(dimensions, density, lambdas, angular_momentum, angular_gain)

    su3_term = np.einsum("...ij,...j->...i", local_generators, psi)
    dpsi = diffusion * lap + nonlinear_gain[..., None] * psi - 1j * su3_spin * su3_term
    dpsi -= 0.12 * scalar_s[..., None] * psi
    return dpsi


def rk4_step(
    psi: np.ndarray,
    dt: float,
    lambdas: np.ndarray,
    dimensions: int,
    periodic: bool,
    diffusion: float,
    attraction: float,
    repulsion: float,
    su3_spin: float,
    angular_momentum: int,
    angular_gain: float,
) -> np.ndarray:
    k1 = field_derivative(psi, lambdas, dimensions, periodic, diffusion, attraction, repulsion, su3_spin, angular_momentum, angular_gain)
    k2 = field_derivative(psi + 0.5 * dt * k1, lambdas, dimensions, periodic, diffusion, attraction, repulsion, su3_spin, angular_momentum, angular_gain)
    k3 = field_derivative(psi + 0.5 * dt * k2, lambdas, dimensions, periodic, diffusion, attraction, repulsion, su3_spin, angular_momentum, angular_gain)
    k4 = field_derivative(psi + dt * k3, lambdas, dimensions, periodic, diffusion, attraction, repulsion, su3_spin, angular_momentum, angular_gain)
    next_psi = psi + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    next_psi /= max(np.sqrt(np.sum(np.abs(next_psi) ** 2)), EPS)
    return next_psi


def center_following_ring_probe_signal(
    density: np.ndarray,
    center: Tuple[float, float, float],
    dimensions: int,
    radius: float,
    ring_width: float,
    angles: int,
) -> float:
    cx, cy, cz = center
    if dimensions == 2:
        max_radius = float(min(cx, cy, density.shape[1] - 1 - cx, density.shape[0] - 1 - cy))
        if max_radius <= 1.5:
            return float(np.mean(density))
        inner = max(0.75, radius - 0.5 * ring_width)
        outer = min(max_radius, radius + 0.5 * ring_width)
        sample_radii = np.linspace(inner, max(inner + 1e-6, outer), 3, dtype=np.float64)
        thetas = np.linspace(-math.pi, math.pi, max(8, angles), endpoint=False, dtype=np.float64)
        samples = []
        for rr in sample_radii:
            xs = cx + rr * np.cos(thetas)
            ys = cy + rr * np.sin(thetas)
            samples.append(bilinear_sample_2d(density, xs, ys))
        return float(np.mean(np.stack(samples, axis=0)))

    zz, yy, xx = np.mgrid[0 : density.shape[0], 0 : density.shape[1], 0 : density.shape[2]]
    rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2 + (zz - cz) ** 2)
    inner = max(0.75, radius - 0.5 * ring_width)
    outer = radius + 0.5 * ring_width
    mask = (rr >= inner) & (rr <= outer)
    return float(np.mean(density[mask])) if np.any(mask) else float(np.mean(density))


def stft_spectrogram(signal: np.ndarray, dt: float, window: int, hop: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    window = max(8, min(window, len(signal)))
    hop = max(1, hop)
    if len(signal) < window:
        window = len(signal)
    spec = []
    centers = []
    win = np.hanning(window)
    for start in range(0, max(len(signal) - window + 1, 1), hop):
        segment = signal[start : start + window]
        if len(segment) < window:
            break
        spectrum = np.abs(np.fft.rfft((segment - np.mean(segment)) * win)) ** 2
        spec.append(spectrum)
        centers.append((start + 0.5 * window) * dt)
    if not spec:
        spec = [np.zeros(window // 2 + 1)]
        centers = [0.0]
    freqs = np.fft.rfftfreq(window, d=dt)
    return np.array(centers, dtype=np.float64), freqs, np.array(spec, dtype=np.float64).T


def extract_continuous_frequency_ridge(
    spectrogram: np.ndarray,
    freqs: np.ndarray,
    jump_penalty: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    if spectrogram.size == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float64), np.zeros(0, dtype=np.float64)

    power = np.log(np.maximum(spectrogram, EPS))
    n_freq, n_time = power.shape
    score = np.full((n_freq, n_time), -np.inf, dtype=np.float64)
    back = np.zeros((n_freq, n_time), dtype=np.int64)
    score[:, 0] = power[:, 0]
    norm = max(float(freqs[-1] - freqs[0]), EPS) if len(freqs) > 1 else 1.0

    for t in range(1, n_time):
        for i in range(n_freq):
            freq_jump = np.abs(freqs[i] - freqs) / norm
            candidate = score[:, t - 1] - jump_penalty * freq_jump
            prev = int(np.argmax(candidate))
            score[i, t] = power[i, t] + candidate[prev]
            back[i, t] = prev

    ridge_idx = np.zeros(n_time, dtype=np.int64)
    ridge_idx[-1] = int(np.argmax(score[:, -1]))
    for t in range(n_time - 1, 0, -1):
        ridge_idx[t - 1] = back[ridge_idx[t], t]

    ridge_freqs = freqs[ridge_idx]
    col_sums = np.sum(spectrogram, axis=0)
    ridge_share = spectrogram[ridge_idx, np.arange(n_time)] / np.maximum(col_sums, EPS)
    return ridge_idx, ridge_freqs, ridge_share


def dominant_frequency(signal: np.ndarray, dt: float) -> float:
    if len(signal) < 4:
        return 0.0
    centered = signal - np.mean(signal)
    spectrum = np.abs(np.fft.rfft(centered)) ** 2
    freqs = np.fft.rfftfreq(len(centered), d=dt)
    if len(freqs) <= 1:
        return 0.0
    idx = int(np.argmax(spectrum[1:]) + 1)
    return float(freqs[idx])


def plot_density_map_2d(run_dir: Path, timestamp: str, density: np.ndarray, center: Tuple[float, float, float]) -> None:
    cx, cy, _ = center
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    image = ax.imshow(density, cmap="magma", origin="lower", aspect="auto")
    ax.scatter([cx], [cy], c="cyan", s=55, marker="x", linewidths=1.6)
    ax.set_title("Final Emergent Density Map")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    fig.colorbar(image, ax=ax, label="density")
    fig.tight_layout()
    fig.savefig(run_dir / f"final_density_map_{timestamp}.png", dpi=180)
    plt.close(fig)


def plot_density_slices_3d(run_dir: Path, timestamp: str, density: np.ndarray, center: Tuple[float, float, float]) -> None:
    _, _, cz = center
    z_idx = int(round(np.clip(cz, 0, density.shape[0] - 1)))
    y_idx = density.shape[1] // 2
    x_idx = density.shape[2] // 2
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    slices = [
        (density[z_idx], f"z-slice @ {z_idx}"),
        (density[:, y_idx, :], f"y-slice @ {y_idx}"),
        (density[:, :, x_idx], f"x-slice @ {x_idx}"),
    ]
    for ax, (slc, title) in zip(axes, slices):
        image = ax.imshow(slc, cmap="magma", origin="lower", aspect="auto")
        ax.set_title(title)
        fig.colorbar(image, ax=ax, shrink=0.82)
    fig.tight_layout()
    fig.savefig(run_dir / f"final_density_map_{timestamp}.png", dpi=180)
    plt.close(fig)


def plot_su3_fields_2d(run_dir: Path, timestamp: str, scalar_s: np.ndarray, comps: np.ndarray) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    fields = [(scalar_s, "Final S Field", "viridis"), (comps[..., 2], "Final a3 Field", "coolwarm"), (comps[..., 7], "Final a8 Field", "PiYG")]
    for ax, (field, title, cmap) in zip(axes, fields):
        image = ax.imshow(field, cmap=cmap, origin="lower", aspect="auto")
        ax.set_title(title)
        fig.colorbar(image, ax=ax, shrink=0.84)
    fig.tight_layout()
    fig.savefig(run_dir / f"final_su3_fields_{timestamp}.png", dpi=180)
    plt.close(fig)


def plot_su3_fields_3d(run_dir: Path, timestamp: str, scalar_s: np.ndarray, comps: np.ndarray, center: Tuple[float, float, float]) -> None:
    _, _, cz = center
    z_idx = int(round(np.clip(cz, 0, scalar_s.shape[0] - 1)))
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    fields = [(scalar_s[z_idx], "Final S Field", "viridis"), (comps[z_idx, ..., 2], "Final a3 Field", "coolwarm"), (comps[z_idx, ..., 7], "Final a8 Field", "PiYG")]
    for ax, (field, title, cmap) in zip(axes, fields):
        image = ax.imshow(field, cmap=cmap, origin="lower", aspect="auto")
        ax.set_title(f"{title} (z={z_idx})")
        fig.colorbar(image, ax=ax, shrink=0.84)
    fig.tight_layout()
    fig.savefig(run_dir / f"final_su3_fields_{timestamp}.png", dpi=180)
    plt.close(fig)


def plot_radial_profile(run_dir: Path, timestamp: str, radii: np.ndarray, profile: np.ndarray) -> None:
    plt.figure(figsize=(6.4, 4.2))
    plt.plot(radii, profile, linewidth=1.8)
    plt.xlabel("radius from emergent center")
    plt.ylabel("mean density")
    plt.title("Radial Density Profile")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(run_dir / f"radial_profile_{timestamp}.png", dpi=180)
    plt.close()


def plot_emergence_series(run_dir: Path, timestamp: str, times: np.ndarray, peak_series: np.ndarray, participation_series: np.ndarray) -> None:
    fig, ax1 = plt.subplots(figsize=(8.5, 4.8))
    ax1.plot(times, peak_series, color="tab:red", linewidth=1.5)
    ax1.set_xlabel("time")
    ax1.set_ylabel("peak density", color="tab:red")
    ax1.tick_params(axis="y", labelcolor="tab:red")
    ax1.grid(alpha=0.3)
    ax2 = ax1.twinx()
    ax2.plot(times, participation_series, color="tab:blue", linewidth=1.4)
    ax2.set_ylabel("participation ratio", color="tab:blue")
    ax2.tick_params(axis="y", labelcolor="tab:blue")
    plt.title("Emergence of Hydrogen-like Bound Structure")
    fig.tight_layout()
    fig.savefig(run_dir / f"emergence_series_{timestamp}.png", dpi=180)
    plt.close(fig)


def plot_spectrogram(
    run_dir: Path,
    timestamp: str,
    stft_times: np.ndarray,
    freqs: np.ndarray,
    spectrogram: np.ndarray,
    ridge_freqs: np.ndarray | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    image = ax.pcolormesh(stft_times, freqs, spectrogram, shading="auto", cmap="inferno")
    if ridge_freqs is not None and len(ridge_freqs) == len(stft_times):
        ax.plot(stft_times, ridge_freqs, color="cyan", linewidth=1.6, alpha=0.9, label="continuous ridge")
        ax.legend(loc="upper right")
    ax.set_xlabel("time")
    ax.set_ylabel("frequency")
    ax.set_title("Center Probe Time-Frequency Spectrum")
    fig.colorbar(image, ax=ax, label="power")
    fig.tight_layout()
    fig.savefig(run_dir / f"time_frequency_spectrum_{timestamp}.png", dpi=180)
    plt.close(fig)


def plot_angular_node_profile(
    run_dir: Path,
    timestamp: str,
    thetas: np.ndarray,
    profile: np.ndarray,
    smoothed_contrast: np.ndarray,
    probe_radius: float,
    zero_crossings: int,
    node_count: int,
    dominant_harmonic: int,
) -> None:
    theta_deg = np.degrees(thetas)
    fig, axes = plt.subplots(2, 1, figsize=(8.2, 6.4), sharex=True)
    axes[0].plot(theta_deg, profile, linewidth=1.6, color="tab:blue")
    axes[0].set_ylabel("density")
    axes[0].set_title(f"Angular Density Profile @ r={probe_radius:.2f}")
    axes[0].grid(alpha=0.3)

    axes[1].plot(theta_deg, smoothed_contrast, linewidth=1.6, color="tab:red")
    axes[1].axhline(0.0, color="black", linewidth=1.0, alpha=0.7)
    axes[1].set_xlabel("angle (deg)")
    axes[1].set_ylabel("contrast")
    axes[1].set_title(
        f"Zero Crossings = {zero_crossings}, Dominant Harmonic = {dominant_harmonic}, Inferred Node Count = {node_count}"
    )
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(run_dir / f"angular_node_profile_{timestamp}.png", dpi=180)
    plt.close(fig)


def save_plotly_density_timeseries_2d(run_dir: Path, timestamp: str, density_series: np.ndarray, times: np.ndarray, target_frames: int) -> None:
    steps = density_series.shape[0]
    stride = max(1, int(math.ceil(steps / max(1, target_frames))))
    frame_indices = list(range(0, steps, stride))
    zmin = float(np.min(density_series))
    zmax = float(np.max(density_series))
    initial = density_series[frame_indices[0]]
    traces = [{"type": "heatmap", "z": initial.tolist(), "colorscale": "Inferno", "zmin": zmin, "zmax": zmax, "colorbar": {"title": "density"}}]
    frames = [{"name": str(fi), "data": [{"type": "heatmap", "z": density_series[idx].tolist(), "colorscale": "Inferno", "zmin": zmin, "zmax": zmax}]} for fi, idx in enumerate(frame_indices)]
    slider_steps = [{"label": f"t={times[idx]:.2f}", "method": "animate", "args": [[str(fi)], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}}]} for fi, idx in enumerate(frame_indices)]
    layout = {
        "title": {"text": "Dynamic Density Field"},
        "xaxis": {"title": "x"},
        "yaxis": {"title": "y"},
        "updatemenus": [{
            "type": "buttons",
            "direction": "left",
            "x": 0.0,
            "y": 1.12,
            "showactive": False,
            "buttons": [
                {"label": "Play", "method": "animate", "args": [None, {"fromcurrent": True, "frame": {"duration": 60, "redraw": False}, "transition": {"duration": 0}}]},
                {"label": "Pause", "method": "animate", "args": [[None], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}}]},
                {"label": "Reset", "method": "animate", "args": [[str(0)], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}}]},
            ],
        }],
        "sliders": [{"pad": {"t": 35}, "currentvalue": {"prefix": "Time: "}, "steps": slider_steps}],
        "margin": {"l": 40, "r": 20, "b": 40, "t": 50},
    }
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Dynamic Density Field</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body style="margin:0;background:#ffffff;font-family:Arial,sans-serif;">
  <div id="plot" style="width:100vw;height:100vh;"></div>
  <script>
    const traces = {json.dumps(traces, ensure_ascii=False)};
    const frames = {json.dumps(frames, ensure_ascii=False)};
    const layout = {json.dumps(layout, ensure_ascii=False)};
    Plotly.newPlot("plot", traces, layout, {{responsive: true, displaylogo: false}}).then(function() {{
      Plotly.addFrames("plot", frames);
    }});
  </script>
</body>
</html>
"""
    (run_dir / f"interactive_density_timeseries_{timestamp}.html").write_text(html, encoding="utf-8")


def save_plotly_isosurface_timeseries_3d(run_dir: Path, timestamp: str, density_series: np.ndarray, times: np.ndarray, target_frames: int) -> None:
    steps = density_series.shape[0]
    stride = max(1, int(math.ceil(steps / max(1, target_frames))))
    frame_indices = list(range(0, steps, stride))
    nz, ny, nx = density_series.shape[1:]
    zz, yy, xx = np.mgrid[0:nz, 0:ny, 0:nx]
    density_flat = density_series.reshape(steps, -1)
    dmin = float(np.min(density_series))
    dmax = float(np.max(density_series))
    isomin = dmin + 0.58 * (dmax - dmin)
    isomax = dmin + 0.88 * (dmax - dmin)
    initial = density_flat[frame_indices[0]]
    traces = [{
        "type": "isosurface",
        "x": xx.ravel().astype(float).tolist(),
        "y": yy.ravel().astype(float).tolist(),
        "z": zz.ravel().astype(float).tolist(),
        "value": initial.astype(float).tolist(),
        "isomin": isomin,
        "isomax": isomax,
        "surface_count": 3,
        "opacity": 0.65,
        "caps": {"x": {"show": False}, "y": {"show": False}, "z": {"show": False}},
        "colorscale": "Inferno",
        "colorbar": {"title": "density"},
    }]
    frames = []
    for fi, idx in enumerate(frame_indices):
        frames.append({"name": str(fi), "data": [{
            "type": "isosurface",
            "x": xx.ravel().astype(float).tolist(),
            "y": yy.ravel().astype(float).tolist(),
            "z": zz.ravel().astype(float).tolist(),
            "value": density_flat[idx].astype(float).tolist(),
            "isomin": isomin,
            "isomax": isomax,
            "surface_count": 3,
            "opacity": 0.65,
            "caps": {"x": {"show": False}, "y": {"show": False}, "z": {"show": False}},
            "colorscale": "Inferno",
        }]})
    slider_steps = [{"label": f"t={times[idx]:.2f}", "method": "animate", "args": [[str(fi)], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}}]} for fi, idx in enumerate(frame_indices)]
    layout = {
        "title": {"text": "Dynamic Density Isosurface"},
        "scene": {
            "xaxis": {"title": "x"},
            "yaxis": {"title": "y"},
            "zaxis": {"title": "z"},
            "camera": {"eye": {"x": 1.5, "y": -1.4, "z": 1.1}},
        },
        "updatemenus": [{
            "type": "buttons",
            "direction": "left",
            "x": 0.0,
            "y": 1.12,
            "showactive": False,
            "buttons": [
                {"label": "Play", "method": "animate", "args": [None, {"fromcurrent": True, "frame": {"duration": 70, "redraw": False}, "transition": {"duration": 0}}]},
                {"label": "Pause", "method": "animate", "args": [[None], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}}]},
                {"label": "Reset", "method": "animate", "args": [[str(0)], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}}]},
            ],
        }],
        "sliders": [{"pad": {"t": 35}, "currentvalue": {"prefix": "Time: "}, "steps": slider_steps}],
        "margin": {"l": 0, "r": 0, "b": 0, "t": 45},
    }
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Dynamic Density Isosurface</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body style="margin:0;background:#ffffff;font-family:Arial,sans-serif;">
  <div id="plot" style="width:100vw;height:100vh;"></div>
  <script>
    const traces = {json.dumps(traces, ensure_ascii=False)};
    const frames = {json.dumps(frames, ensure_ascii=False)};
    const layout = {json.dumps(layout, ensure_ascii=False)};
    Plotly.newPlot("plot", traces, layout, {{responsive: true, displaylogo: false}}).then(function() {{
      Plotly.addFrames("plot", frames);
    }});
  </script>
</body>
</html>
"""
    (run_dir / f"interactive_isosurface_timeseries_{timestamp}.html").write_text(html, encoding="utf-8")


def simulate(args: argparse.Namespace) -> Path:
    lambdas = gell_mann_matrices()
    psi = initialize_field(args.dimensions, args.height, args.width, args.depth, args.seed)
    steps = int(math.floor(args.duration / args.dt))
    save_stride = max(1, int(args.save_stride))
    save_steps = list(range(0, steps, save_stride))
    if not save_steps or save_steps[-1] != steps - 1:
        save_steps.append(max(steps - 1, 0))

    peak_series = np.zeros(steps, dtype=np.float64)
    participation_series = np.zeros(steps, dtype=np.float64)
    probe_series = np.zeros(steps, dtype=np.float64)
    center_series = np.zeros((steps, 3), dtype=np.float64)
    saved_density: List[np.ndarray] = []
    saved_scalar: List[np.ndarray] = []
    saved_comps: List[np.ndarray] = []
    saved_times: List[float] = []

    for step in range(steps):
        rho = density_matrices(psi)
        scalar_s, comps = su3_components(rho, lambdas)
        density = np.sum(np.abs(psi) ** 2, axis=-1)
        center = compute_center(density, args.dimensions)
        center_series[step] = np.array(center, dtype=np.float64)
        peak_series[step] = float(np.max(density))
        participation_series[step] = float((np.sum(density) ** 2) / max(np.sum(density**2), EPS))
        probe_series[step] = center_following_ring_probe_signal(
            density=density,
            center=center,
            dimensions=args.dimensions,
            radius=args.probe_radius,
            ring_width=args.probe_ring_width,
            angles=args.probe_angles,
        )

        if step in save_steps:
            saved_density.append(density.copy())
            saved_scalar.append(scalar_s.copy())
            saved_comps.append(comps.copy())
            saved_times.append(step * args.dt)

        psi = rk4_step(
            psi=psi,
            dt=args.dt,
            lambdas=lambdas,
            dimensions=args.dimensions,
            periodic=args.periodic,
            diffusion=args.diffusion,
            attraction=args.attraction,
            repulsion=args.repulsion,
            su3_spin=args.su3_spin,
            angular_momentum=args.angular_momentum,
            angular_gain=args.angular_gain,
        )

    final_rho = density_matrices(psi)
    final_scalar_s, final_comps = su3_components(final_rho, lambdas)
    final_density = np.sum(np.abs(psi) ** 2, axis=-1)
    center = compute_center(final_density, args.dimensions)
    radius = compute_effective_radius(final_density, center, args.dimensions)
    radii, profile = radial_profile(final_density, center, args.dimensions)
    angular_thetas = np.array([], dtype=np.float64)
    angular_profile = np.array([], dtype=np.float64)
    angular_contrast_profile = np.array([], dtype=np.float64)
    angular_zero_crossings = 0
    angular_node_count = 0
    dominant_angular_harmonic = 0
    angular_contrast = 0.0
    angular_probe_radius = 0.0
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path("resonance_data") / f"hydrogen_color_field_emergence_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    if args.dimensions == 2:
        plot_density_map_2d(run_dir, timestamp, final_density, center)
        plot_su3_fields_2d(run_dir, timestamp, final_scalar_s, final_comps)
        (
            angular_thetas,
            angular_profile,
            angular_contrast_profile,
            angular_zero_crossings,
            angular_node_count,
            dominant_angular_harmonic,
            angular_contrast,
            angular_probe_radius,
        ) = angular_node_signature_2d(final_density, center, radius)
        plot_angular_node_profile(
            run_dir,
            timestamp,
            angular_thetas,
            angular_profile,
            angular_contrast_profile,
            angular_probe_radius,
            angular_zero_crossings,
            angular_node_count,
            dominant_angular_harmonic,
        )
    else:
        plot_density_slices_3d(run_dir, timestamp, final_density, center)
        plot_su3_fields_3d(run_dir, timestamp, final_scalar_s, final_comps, center)

    plot_radial_profile(run_dir, timestamp, radii, profile)
    plot_emergence_series(run_dir, timestamp, np.arange(steps) * args.dt, peak_series, participation_series)
    stft_times, freqs, spectrogram = stft_spectrogram(probe_series, args.dt, args.stft_window, args.stft_hop)
    ridge_idx, ridge_freqs, ridge_share = extract_continuous_frequency_ridge(spectrogram, freqs, args.ridge_jump_penalty)
    plot_spectrogram(run_dir, timestamp, stft_times, freqs, spectrogram, ridge_freqs)

    saved_density_array = np.array(saved_density, dtype=np.float64)
    saved_scalar_array = np.array(saved_scalar, dtype=np.float64)
    saved_comps_array = np.array(saved_comps, dtype=np.float64)
    saved_times_array = np.array(saved_times, dtype=np.float64)

    if args.dimensions == 2:
        save_plotly_density_timeseries_2d(run_dir, timestamp, saved_density_array, saved_times_array, args.target_frames)
    else:
        save_plotly_isosurface_timeseries_3d(run_dir, timestamp, saved_density_array, saved_times_array, args.target_frames)

    np.savez_compressed(
        run_dir / f"field_series_{timestamp}.npz",
        saved_times=saved_times_array,
        density=saved_density_array,
        scalar_s=saved_scalar_array,
        su3_components=saved_comps_array,
        final_psi_real=psi.real,
        final_psi_imag=psi.imag,
        final_density=final_density,
        peak_series=peak_series,
        participation_series=participation_series,
        probe_series=probe_series,
        center_series=center_series,
        stft_times=stft_times,
        stft_freqs=freqs,
        spectrogram=spectrogram,
        ridge_indices=ridge_idx,
        ridge_frequencies=ridge_freqs,
        ridge_energy_share=ridge_share,
        radii=radii,
        radial_profile=profile,
        angular_thetas=angular_thetas,
        angular_profile=angular_profile,
        angular_contrast_profile=angular_contrast_profile,
        angular_zero_crossings=np.array([angular_zero_crossings], dtype=np.int64),
        angular_node_count=np.array([angular_node_count], dtype=np.int64),
        dominant_angular_harmonic=np.array([dominant_angular_harmonic], dtype=np.int64),
        angular_contrast=np.array([angular_contrast], dtype=np.float64),
        angular_probe_radius=np.array([angular_probe_radius], dtype=np.float64),
    )

    summary = EmergenceSummary(
        dimensions=args.dimensions,
        width=args.width,
        height=args.height,
        depth=args.depth if args.dimensions == 3 else 1,
        steps=steps,
        dt=float(args.dt),
        seed=int(args.seed),
        total_mass=float(np.sum(final_density)),
        final_peak_density=float(np.max(final_density)),
        final_mean_density=float(np.mean(final_density)),
        final_peak_to_mean_ratio=float(np.max(final_density) / max(np.mean(final_density), EPS)),
        effective_radius=radius,
        participation_ratio=float((np.sum(final_density) ** 2) / max(np.sum(final_density**2), EPS)),
        center_x=float(center[0]),
        center_y=float(center[1]),
        center_z=float(center[2]),
        final_mean_a3=float(np.mean(final_comps[..., 2])),
        final_mean_a8=float(np.mean(final_comps[..., 7])),
        probe_dominant_frequency=dominant_frequency(probe_series, args.dt),
        ridge_frequency_mean=float(np.mean(ridge_freqs)) if len(ridge_freqs) else 0.0,
        ridge_frequency_std=float(np.std(ridge_freqs)) if len(ridge_freqs) else 0.0,
        ridge_energy_share_mean=float(np.mean(ridge_share)) if len(ridge_share) else 0.0,
        ridge_energy_share_min=float(np.min(ridge_share)) if len(ridge_share) else 0.0,
        ridge_energy_share_max=float(np.max(ridge_share)) if len(ridge_share) else 0.0,
        center_drift_mean=float(np.mean(np.linalg.norm(np.diff(center_series, axis=0), axis=1))) if steps > 1 else 0.0,
        center_drift_max=float(np.max(np.linalg.norm(np.diff(center_series, axis=0), axis=1))) if steps > 1 else 0.0,
        angular_momentum=int(args.angular_momentum),
        angular_node_count=int(angular_node_count),
        angular_zero_crossings=int(angular_zero_crossings),
        dominant_angular_harmonic=int(dominant_angular_harmonic),
        angular_contrast=float(angular_contrast),
        angular_probe_radius=float(angular_probe_radius),
    )
    with (run_dir / f"summary_{timestamp}.json").open("w", encoding="utf-8") as f:
        json.dump(asdict(summary), f, indent=2)

    print(f"Run directory: {run_dir}")
    print(f"Peak/mean density ratio: {summary.final_peak_to_mean_ratio:.4f}")
    print(f"Effective radius: {summary.effective_radius:.4f}")
    print(f"Emergent center: ({summary.center_x:.3f}, {summary.center_y:.3f}, {summary.center_z:.3f})")
    print(f"Dominant probe frequency: {summary.probe_dominant_frequency:.4f}")
    print(f"Ridge frequency mean/std: {summary.ridge_frequency_mean:.4f} / {summary.ridge_frequency_std:.4f}")
    print(f"Ridge energy share mean: {summary.ridge_energy_share_mean:.4f}")
    print(f"Center drift mean/max: {summary.center_drift_mean:.4f} / {summary.center_drift_max:.4f}")
    if args.dimensions == 2:
        print(f"Angular node count: {summary.angular_node_count}")
        print(f"Angular zero crossings: {summary.angular_zero_crossings}")
        print(f"Dominant angular harmonic: {summary.dominant_angular_harmonic}")
        print(f"Angular contrast: {summary.angular_contrast:.4f}")
    return run_dir


def main() -> None:
    args = parse_args()
    simulate(args)


if __name__ == "__main__":
    main()
