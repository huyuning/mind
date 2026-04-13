#!/usr/bin/env python3
"""
胞元虚拟计算宇宙最小原型

模型
- 每个胞元携带一个三维复态 psi_a(t) in C^3
- 每个胞元对应一个 3x3 厄米局域矩阵 M_a(t)
- 胞元之间通过复边 R_ab(t) 相互耦合，实部对应链接强度，虚部对应相位弯曲
- 三角闭合积 R_ab R_bc R_ca 用于提取局域几何闭合和相位曲率

输出
- resonance_data/cellular_virtual_universe_<timestamp>/
  - summary_<timestamp>.json
  - state_series_<timestamp>.npz
  - mean_su3_components_<timestamp>.png
  - closure_series_<timestamp>.png
  - final_a3_heatmap_<timestamp>.png
  - final_field_panels_<timestamp>.png
  - final_network_snapshot_<timestamp>.png
  - final_network_3d_snapshot_<timestamp>.png
  - final_surface_3d_<timestamp>.png
  - interactive_network_3d_<timestamp>.html
  - interactive_surface_3d_<timestamp>.html
  - interactive_network_3d_timeseries_<timestamp>.html
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import yaml

from cellular_atom_templates import DEFAULT_ATOM_TEMPLATES


SQRT3 = math.sqrt(3.0)


@dataclass
class EdgeSpec:
    src: int
    dst: int
    base_strength: float
    base_phase: float


@dataclass
class UniverseSummary:
    width: int
    height: int
    cell_count: int
    edge_count: int
    triangle_count: int
    steps: int
    dt: float
    duration: float
    mean_edge_strength: float
    mean_edge_phase: float
    mean_triangle_closure_real: float
    mean_triangle_closure_phase: float
    peak_triangle_closure_real: float
    final_mean_a3: float
    final_mean_a8: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="胞元虚拟计算宇宙最小原型")
    parser.add_argument("--width", type=int, default=4, help="胞元网格宽度")
    parser.add_argument("--height", type=int, default=4, help="胞元网格高度")
    parser.add_argument("--duration", type=float, default=16.0, help="仿真总时长")
    parser.add_argument("--dt", type=float, default=0.04, help="时间步长")
    parser.add_argument("--seed", type=int, default=20260409, help="随机种子")
    parser.add_argument("--coupling", type=float, default=0.42, help="胞元间传播耦合系数")
    parser.add_argument("--geometry-gain", type=float, default=0.35, help="态重叠对边强度的调制系数")
    parser.add_argument("--curvature-gain", type=float, default=0.70, help="SU(3) 偏置差对边相位的调制系数")
    parser.add_argument("--state-gain", type=float, default=0.65, help="局域态密度矩阵叠加到胞元矩阵的权重")
    parser.add_argument("--periodic", action="store_true", help="是否使用周期边界")
    parser.add_argument(
        "--graph-config",
        type=str,
        default=None,
        help="自定义分子/图结构配置文件（YAML），用于将几何从规则网格解耦",
    )
    parser.add_argument(
        "--projection-z",
        choices=["a3", "a8", "S"],
        default="a3",
        help="三维投影中 z 轴对应的场（默认 a3）",
    )
    parser.add_argument(
        "--z-scale",
        type=float,
        default=1.0,
        help="三维投影 z 轴缩放系数（用于控制起伏高度）",
    )
    parser.add_argument(
        "--target-frames",
        type=int,
        default=80,
        help="时间滑块版 Plotly 动画的目标帧数上限（会按需要降采样）",
    )
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
    matrices[7] = np.array(
        [[1 / SQRT3, 0, 0], [0, 1 / SQRT3, 0], [0, 0, -2 / SQRT3]],
        dtype=np.complex128,
    )
    return matrices


def create_output_dir() -> Path:
    out_dir = Path("resonance_data")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def cell_index(x: int, y: int, width: int) -> int:
    return y * width + x


def build_lattice(width: int, height: int, periodic: bool) -> Tuple[int, List[EdgeSpec], List[Tuple[int, int, int]], np.ndarray]:
    cell_count = width * height
    positions = np.zeros((cell_count, 2), dtype=np.float64)
    for y in range(height):
        for x in range(width):
            positions[cell_index(x, y, width)] = (x, y)

    edge_map: Dict[Tuple[int, int], EdgeSpec] = {}
    triangles: List[Tuple[int, int, int]] = []

    def maybe_neighbor(x: int, y: int) -> Tuple[int, int] | None:
        if periodic:
            return x % width, y % height
        if x < 0 or x >= width or y < 0 or y >= height:
            return None
        return x, y

    def add_undirected_edge(a: int, b: int, strength: float, phase: float) -> None:
        if a == b:
            return
        key = (min(a, b), max(a, b))
        if key in edge_map:
            return
        if a < b:
            edge_map[key] = EdgeSpec(src=a, dst=b, base_strength=strength, base_phase=phase)
        else:
            edge_map[key] = EdgeSpec(src=b, dst=a, base_strength=strength, base_phase=phase)

    for y in range(height):
        for x in range(width):
            a = cell_index(x, y, width)
            right = maybe_neighbor(x + 1, y)
            down = maybe_neighbor(x, y + 1)
            diag = maybe_neighbor(x + 1, y + 1)
            if right is not None:
                b = cell_index(right[0], right[1], width)
                add_undirected_edge(a, b, strength=0.95, phase=0.10)
            if down is not None:
                c = cell_index(down[0], down[1], width)
                add_undirected_edge(a, c, strength=0.90, phase=0.55)
            if diag is not None:
                d = cell_index(diag[0], diag[1], width)
                add_undirected_edge(a, d, strength=0.78, phase=1.00)
            if right is not None and down is not None and diag is not None:
                b = cell_index(right[0], right[1], width)
                c = cell_index(down[0], down[1], width)
                d = cell_index(diag[0], diag[1], width)
                triangles.append((a, b, d))
                triangles.append((a, c, d))

    return cell_count, list(edge_map.values()), triangles, positions


def initialize_states(cell_count: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    psi = (rng.normal(size=(cell_count, 3)) + 1j * rng.normal(size=(cell_count, 3))).astype(np.complex128)
    norms = np.linalg.norm(psi, axis=1, keepdims=True)
    psi /= np.maximum(norms, 1e-12)
    return psi


def build_local_hamiltonians(width: int, height: int, seed: int, lambdas: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed + 17)
    cell_count = width * height
    hamiltonians = np.zeros((cell_count, 3, 3), dtype=np.complex128)
    scalar_s = np.zeros(cell_count, dtype=np.float64)
    static_components = np.zeros((cell_count, 8), dtype=np.float64)

    for y in range(height):
        for x in range(width):
            idx = cell_index(x, y, width)
            fx = 0.0 if width == 1 else x / (width - 1)
            fy = 0.0 if height == 1 else y / (height - 1)
            coeffs = np.array(
                [
                    0.16 * math.cos(2.0 * math.pi * fx),
                    0.12 * math.sin(2.0 * math.pi * fy),
                    0.10 * (fx - fy),
                    0.08 * math.cos(math.pi * (fx + fy)),
                    0.07 * math.sin(2.0 * math.pi * (fx + 0.5 * fy)),
                    0.09 * math.cos(2.0 * math.pi * (fy + 0.25 * fx)),
                    0.06 * math.sin(2.0 * math.pi * (fx - fy)),
                    0.11 * math.cos(2.0 * math.pi * fx) * math.sin(math.pi * fy),
                ],
                dtype=np.float64,
            )
            coeffs += 0.02 * rng.normal(size=8)
            s_value = 0.85 + 0.08 * math.cos(math.pi * (fx + fy)) + 0.02 * rng.normal()
            matrix = (s_value / SQRT3) * np.eye(3, dtype=np.complex128)
            for alpha in range(8):
                matrix += 0.5 * coeffs[alpha] * lambdas[alpha]
            hamiltonians[idx] = 0.5 * (matrix + np.conjugate(matrix.T))
            scalar_s[idx] = s_value
            static_components[idx] = coeffs

    return hamiltonians, scalar_s, static_components


def build_hamiltonians_from_templates(
    node_specs: Sequence[Dict[str, Any]],
    lambdas: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
    cell_count = len(node_specs)
    hamiltonians = np.zeros((cell_count, 3, 3), dtype=np.complex128)
    scalar_s = np.zeros(cell_count, dtype=np.float64)
    static_components = np.zeros((cell_count, 8), dtype=np.float64)
    labels: List[str] = []

    for idx, node in enumerate(node_specs):
        label = str(node.get("id", idx))
        element = str(node.get("element", "H"))
        template = DEFAULT_ATOM_TEMPLATES.get(element)
        labels.append(label)

        if template is None:
            s_value = float(node.get("scalar_s", 0.8))
            coeffs = np.zeros(8, dtype=np.float64)
        else:
            s_value = float(node.get("scalar_s", template.scalar_s))
            coeffs = template.components.copy()

        component_overrides = node.get("components", {})
        if isinstance(component_overrides, dict):
            for key, value in component_overrides.items():
                if key.startswith("a"):
                    comp_idx = int(key[1:]) - 1
                    if 0 <= comp_idx < 8:
                        coeffs[comp_idx] = float(value)

        matrix = (s_value / SQRT3) * np.eye(3, dtype=np.complex128)
        for alpha in range(8):
            matrix += 0.5 * coeffs[alpha] * lambdas[alpha]

        hamiltonians[idx] = 0.5 * (matrix + np.conjugate(matrix.T))
        scalar_s[idx] = s_value
        static_components[idx] = coeffs

    return hamiltonians, scalar_s, static_components, labels


def build_graph_from_yaml(config_path: Path, lambdas: np.ndarray) -> Tuple[int, List[EdgeSpec], List[Tuple[int, int, int]], np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[str], Dict[str, Any]]:
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    nodes = config.get("nodes", [])
    edges_cfg = config.get("edges", [])
    if not nodes:
        raise ValueError("graph-config must define a non-empty 'nodes' list")

    positions = np.zeros((len(nodes), 2), dtype=np.float64)
    for idx, node in enumerate(nodes):
        positions[idx] = (float(node["x"]), float(node["y"]))

    hamiltonians, scalar_s, static_components, labels = build_hamiltonians_from_templates(nodes, lambdas)

    edge_specs: List[EdgeSpec] = []
    adjacency = np.zeros((len(nodes), len(nodes)), dtype=bool)
    label_to_index = {str(node.get("id", idx)): idx for idx, node in enumerate(nodes)}

    for edge in edges_cfg:
        src = edge["src"]
        dst = edge["dst"]
        src_idx = label_to_index[src] if isinstance(src, str) else int(src)
        dst_idx = label_to_index[dst] if isinstance(dst, str) else int(dst)
        edge_specs.append(
            EdgeSpec(
                src=src_idx,
                dst=dst_idx,
                base_strength=float(edge.get("base_strength", 1.0)),
                base_phase=float(edge.get("base_phase", 0.0)),
            )
        )
        adjacency[src_idx, dst_idx] = True
        adjacency[dst_idx, src_idx] = True

    triangles: List[Tuple[int, int, int]] = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if not adjacency[i, j]:
                continue
            for k in range(j + 1, len(nodes)):
                if adjacency[i, k] and adjacency[j, k]:
                    triangles.append((i, j, k))

    simulation_overrides = config.get("simulation", {}) if isinstance(config, dict) else {}
    return len(nodes), edge_specs, triangles, positions, hamiltonians, scalar_s, static_components, labels, simulation_overrides


def density_matrices(psi: np.ndarray) -> np.ndarray:
    return np.einsum("ai,aj->aij", psi, np.conjugate(psi), dtype=np.complex128)


def su3_components_from_matrix(matrices: np.ndarray, lambdas: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    traces = np.trace(matrices, axis1=1, axis2=2).real
    scalar_s = traces / SQRT3
    components = np.zeros((matrices.shape[0], 8), dtype=np.float64)
    for alpha in range(8):
        values = np.einsum("aij,ji->a", matrices, lambdas[alpha]).real
        components[:, alpha] = values
    return scalar_s, components


def build_edge_matrix(
    psi: np.ndarray,
    dynamic_components: np.ndarray,
    edge_specs: Sequence[EdgeSpec],
    geometry_gain: float,
    curvature_gain: float,
) -> np.ndarray:
    cell_count = psi.shape[0]
    edges = np.zeros((cell_count, cell_count), dtype=np.complex128)
    a3 = dynamic_components[:, 2]
    for edge in edge_specs:
        overlap = float(np.abs(np.vdot(psi[edge.src], psi[edge.dst])))
        strength = edge.base_strength * (1.0 + geometry_gain * (overlap - 0.5))
        strength = max(strength, 0.02)
        phase = edge.base_phase + curvature_gain * (a3[edge.dst] - a3[edge.src])
        value = strength * np.exp(1j * phase)
        edges[edge.src, edge.dst] = value
        edges[edge.dst, edge.src] = np.conjugate(value)
    return edges


def compute_triangle_closures(edges: np.ndarray, triangles: Sequence[Tuple[int, int, int]]) -> np.ndarray:
    closure = np.zeros(len(triangles), dtype=np.complex128)
    for idx, (a, b, c) in enumerate(triangles):
        closure[idx] = edges[a, b] * edges[b, c] * edges[c, a]
    return closure


def derivative(
    psi: np.ndarray,
    hamiltonians: np.ndarray,
    edge_specs: Sequence[EdgeSpec],
    lambdas: np.ndarray,
    coupling: float,
    geometry_gain: float,
    curvature_gain: float,
) -> np.ndarray:
    rho = density_matrices(psi)
    _, dynamic_components = su3_components_from_matrix(rho, lambdas)
    edges = build_edge_matrix(psi, dynamic_components, edge_specs, geometry_gain, curvature_gain)
    dpsi = np.zeros_like(psi)
    for idx in range(psi.shape[0]):
        local_term = hamiltonians[idx] @ psi[idx]
        coupling_term = np.sum(edges[idx, :, None] * psi, axis=0)
        dpsi[idx] = -1j * (local_term + coupling * coupling_term)
    return dpsi


def rk4_step(
    psi: np.ndarray,
    dt: float,
    hamiltonians: np.ndarray,
    edge_specs: Sequence[EdgeSpec],
    lambdas: np.ndarray,
    coupling: float,
    geometry_gain: float,
    curvature_gain: float,
) -> np.ndarray:
    k1 = derivative(psi, hamiltonians, edge_specs, lambdas, coupling, geometry_gain, curvature_gain)
    k2 = derivative(psi + 0.5 * dt * k1, hamiltonians, edge_specs, lambdas, coupling, geometry_gain, curvature_gain)
    k3 = derivative(psi + 0.5 * dt * k2, hamiltonians, edge_specs, lambdas, coupling, geometry_gain, curvature_gain)
    k4 = derivative(psi + dt * k3, hamiltonians, edge_specs, lambdas, coupling, geometry_gain, curvature_gain)
    next_psi = psi + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    norms = np.linalg.norm(next_psi, axis=1, keepdims=True)
    next_psi /= np.maximum(norms, 1e-12)
    return next_psi


def plot_mean_components(run_dir: Path, timestamp: str, times: np.ndarray, mean_components: np.ndarray) -> None:
    plt.figure(figsize=(10, 6))
    for idx in range(mean_components.shape[1]):
        plt.plot(times, mean_components[:, idx], linewidth=1.2, label=f"a{idx + 1}")
    plt.xlabel("time")
    plt.ylabel("mean SU(3) component")
    plt.title("Mean SU(3) Components Across Cells")
    plt.grid(alpha=0.3)
    plt.legend(ncol=4, fontsize=8)
    plt.tight_layout()
    plt.savefig(run_dir / f"mean_su3_components_{timestamp}.png", dpi=180)
    plt.close()


def plot_closure_series(run_dir: Path, timestamp: str, times: np.ndarray, closure_real_mean: np.ndarray, closure_phase_mean: np.ndarray) -> None:
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(times, closure_real_mean, color="tab:blue", linewidth=1.4)
    ax1.set_xlabel("time")
    ax1.set_ylabel("mean Re(closure)", color="tab:blue")
    ax1.tick_params(axis="y", labelcolor="tab:blue")
    ax1.grid(alpha=0.3)

    ax2 = ax1.twinx()
    ax2.plot(times, closure_phase_mean, color="tab:orange", linewidth=1.2)
    ax2.set_ylabel("mean arg(closure)", color="tab:orange")
    ax2.tick_params(axis="y", labelcolor="tab:orange")
    plt.title("Triangle Closure Series")
    fig.tight_layout()
    fig.savefig(run_dir / f"closure_series_{timestamp}.png", dpi=180)
    plt.close(fig)


def plot_final_heatmap(run_dir: Path, timestamp: str, final_a3: np.ndarray, width: int, height: int) -> None:
    plt.figure(figsize=(5.5, 4.5))
    grid = final_a3.reshape(height, width)
    image = plt.imshow(grid, cmap="coolwarm", aspect="auto")
    plt.colorbar(image, label="final a3")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.title("Final a3 Bias Field")
    plt.tight_layout()
    plt.savefig(run_dir / f"final_a3_heatmap_{timestamp}.png", dpi=180)
    plt.close()


def plot_field_panels(
    run_dir: Path,
    timestamp: str,
    scalar_s: np.ndarray,
    components: np.ndarray,
    width: int,
    height: int,
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    panels = [
        (scalar_s.reshape(height, width), "Final S Field", "viridis"),
        (components[:, 2].reshape(height, width), "Final a3 Field", "coolwarm"),
        (components[:, 7].reshape(height, width), "Final a8 Field", "PiYG"),
    ]
    for ax, (grid, title, cmap) in zip(axes, panels):
        image = ax.imshow(grid, cmap=cmap, aspect="auto")
        ax.set_title(title)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        fig.colorbar(image, ax=ax, shrink=0.85)
    fig.tight_layout()
    fig.savefig(run_dir / f"final_field_panels_{timestamp}.png", dpi=180)
    plt.close(fig)


def plot_final_field_map_points(
    run_dir: Path,
    timestamp: str,
    positions: np.ndarray,
    values: np.ndarray,
    title: str,
    file_stem: str,
    labels: Sequence[str],
) -> None:
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    scatter = ax.scatter(
        positions[:, 0],
        positions[:, 1],
        c=values,
        cmap="coolwarm",
        s=220,
        edgecolors="black",
        linewidths=0.8,
    )
    for idx, (x, y) in enumerate(positions):
        ax.text(x, y, labels[idx], ha="center", va="center", fontsize=8, color="black")
    ax.set_title(title)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    fig.colorbar(scatter, ax=ax, label=title)
    fig.tight_layout()
    fig.savefig(run_dir / f"{file_stem}_{timestamp}.png", dpi=180)
    plt.close(fig)


def plot_field_panels_points(
    run_dir: Path,
    timestamp: str,
    positions: np.ndarray,
    scalar_s: np.ndarray,
    components: np.ndarray,
    labels: Sequence[str],
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
    panel_defs = [
        (scalar_s, "Final S Field", "viridis"),
        (components[:, 2], "Final a3 Field", "coolwarm"),
        (components[:, 7], "Final a8 Field", "PiYG"),
    ]
    for ax, (values, title, cmap) in zip(axes, panel_defs):
        scatter = ax.scatter(
            positions[:, 0],
            positions[:, 1],
            c=values,
            cmap=cmap,
            s=190,
            edgecolors="black",
            linewidths=0.8,
        )
        for idx, (x, y) in enumerate(positions):
            ax.text(x, y, labels[idx], ha="center", va="center", fontsize=7.5, color="black")
        ax.set_title(title)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_aspect("equal")
        ax.grid(alpha=0.25)
        fig.colorbar(scatter, ax=ax, shrink=0.85)
    fig.tight_layout()
    fig.savefig(run_dir / f"final_field_panels_{timestamp}.png", dpi=180)
    plt.close(fig)


def plot_network_snapshot(
    run_dir: Path,
    timestamp: str,
    positions: np.ndarray,
    edges: np.ndarray,
    final_a3: np.ndarray,
    labels: Sequence[str] | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    if labels is None:
        labels = [str(i) for i in range(len(positions))]

    # Draw only upper-triangle edges to avoid duplicate lines for Hermitian pairs.
    for src in range(edges.shape[0]):
        for dst in range(src + 1, edges.shape[1]):
            value = edges[src, dst]
            strength = float(np.abs(value))
            if strength <= 1e-10:
                continue
            phase = float(np.angle(value))
            x0, y0 = positions[src]
            x1, y1 = positions[dst]
            color = plt.cm.twilight((phase + np.pi) / (2.0 * np.pi))
            linewidth = 0.6 + 3.5 * strength
            ax.plot([x0, x1], [y0, y1], color=color, linewidth=linewidth, alpha=0.72, zorder=1)

    scatter = ax.scatter(
        positions[:, 0],
        positions[:, 1],
        c=final_a3,
        cmap="coolwarm",
        s=170,
        edgecolors="black",
        linewidths=0.8,
        zorder=2,
    )
    for idx, (x, y) in enumerate(positions):
        ax.text(x, y, labels[idx], ha="center", va="center", fontsize=8, color="black", zorder=3)

    ax.set_title("Final Cellular Network Snapshot")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.grid(alpha=0.25)
    fig.colorbar(scatter, ax=ax, label="final a3")
    fig.tight_layout()
    fig.savefig(run_dir / f"final_network_snapshot_{timestamp}.png", dpi=180)
    plt.close(fig)


def plot_network_3d_snapshot(
    run_dir: Path,
    timestamp: str,
    positions: np.ndarray,
    edges: np.ndarray,
    z_display: np.ndarray,
    node_cmap_field: np.ndarray,
    projection_label: str,
    labels: Sequence[str] | None = None,
) -> None:
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (needed for 3D)
    if labels is None:
        labels = [str(i) for i in range(len(positions))]

    fig = plt.figure(figsize=(8.5, 6.8))
    ax = fig.add_subplot(111, projection="3d")
    ax.view_init(elev=28, azim=-60)

    # Draw edges (upper triangle to avoid duplicates)
    for i in range(edges.shape[0]):
        for j in range(i + 1, edges.shape[1]):
            val = edges[i, j]
            strength = float(np.abs(val))
            if strength <= 1e-10:
                continue
            phase = float(np.angle(val))
            x0, y0 = positions[i]
            x1, y1 = positions[j]
            z0, z1 = z_display[i], z_display[j]
            color = plt.cm.twilight((phase + np.pi) / (2.0 * np.pi))
            linewidth = 0.4 + 2.8 * strength
            ax.plot([x0, x1], [y0, y1], [z0, z1], color=color, linewidth=linewidth, alpha=0.75, zorder=1)

    # Draw nodes
    sc = ax.scatter(
        positions[:, 0],
        positions[:, 1],
        z_display,
        c=node_cmap_field,
        cmap="coolwarm",
        s=75,
        edgecolors="black",
        linewidths=0.6,
        depthshade=True,
        zorder=2,
    )
    for idx, (x, y) in enumerate(positions):
        ax.text(x, y, z_display[idx], labels[idx], ha="center", va="center", fontsize=7.5, color="black", zorder=3)

    ax.set_title(f"3D Network Snapshot (z = {projection_label})")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel(f"z ({projection_label}, normalized)")
    fig.colorbar(sc, ax=ax, shrink=0.7, pad=0.1, label="node color (final a3)")
    fig.tight_layout()
    fig.savefig(run_dir / f"final_network_3d_snapshot_{timestamp}.png", dpi=180)
    plt.close(fig)


def plot_surface_3d(
    run_dir: Path,
    timestamp: str,
    z_grid: np.ndarray,
    width: int,
    height: int,
    title: str,
) -> None:
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    X, Y = np.meshgrid(np.arange(width), np.arange(height))
    Z = z_grid.reshape(height, width)
    fig = plt.figure(figsize=(8.0, 6.5))
    ax = fig.add_subplot(111, projection="3d")
    surf = ax.plot_surface(X, Y, Z, cmap="viridis", linewidth=0, antialiased=True, alpha=0.95)
    ax.set_title(title)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    fig.colorbar(surf, ax=ax, shrink=0.65, pad=0.08, label="z value")
    fig.tight_layout()
    fig.savefig(run_dir / f"final_surface_3d_{timestamp}.png", dpi=180)
    plt.close(fig)


def plot_surface_3d_points(
    run_dir: Path,
    timestamp: str,
    positions: np.ndarray,
    z_values: np.ndarray,
    labels: Sequence[str],
    title: str,
) -> None:
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    fig = plt.figure(figsize=(8.0, 6.5))
    ax = fig.add_subplot(111, projection="3d")
    if len(positions) >= 3:
        trisurf = ax.plot_trisurf(
            positions[:, 0],
            positions[:, 1],
            z_values,
            cmap="viridis",
            alpha=0.85,
            linewidth=0.2,
        )
        fig.colorbar(trisurf, ax=ax, shrink=0.65, pad=0.08, label="z value")
    ax.scatter(positions[:, 0], positions[:, 1], z_values, c=z_values, cmap="viridis", s=80, edgecolors="black")
    for idx, (x, y) in enumerate(positions):
        ax.text(x, y, z_values[idx], labels[idx], ha="center", va="center", fontsize=7.5)
    ax.set_title(title)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    fig.tight_layout()
    fig.savefig(run_dir / f"final_surface_3d_{timestamp}.png", dpi=180)
    plt.close(fig)


def normalize_projection_field(z_field: np.ndarray, z_scale: float) -> np.ndarray:
    z = z_field.astype(np.float64)
    max_abs = float(np.max(np.abs(z)))
    if max_abs <= 1e-12:
        max_abs = 1.0
    return z_scale * z / max_abs


def save_plotly_network_3d_html(
    run_dir: Path,
    timestamp: str,
    positions: np.ndarray,
    edges: np.ndarray,
    z_display: np.ndarray,
    node_cmap_field: np.ndarray,
    projection_label: str,
    labels: Sequence[str] | None = None,
) -> None:
    if labels is None:
        labels = [str(i) for i in range(len(z_display))]
    edge_traces: List[Dict[str, object]] = []
    for i in range(edges.shape[0]):
        for j in range(i + 1, edges.shape[1]):
            val = edges[i, j]
            strength = float(np.abs(val))
            if strength <= 1e-10:
                continue
            phase = float(np.angle(val))
            x0, y0 = positions[i]
            x1, y1 = positions[j]
            color_rgba = plt.cm.twilight((phase + np.pi) / (2.0 * np.pi))
            color = "rgba({},{},{},{:.3f})".format(
                int(round(color_rgba[0] * 255)),
                int(round(color_rgba[1] * 255)),
                int(round(color_rgba[2] * 255)),
                0.78,
            )
            edge_traces.append(
                {
                    "type": "scatter3d",
                    "mode": "lines",
                    "x": [float(x0), float(x1)],
                    "y": [float(y0), float(y1)],
                    "z": [float(z_display[i]), float(z_display[j])],
                    "hoverinfo": "text",
                    "text": [f"edge {labels[i]}-{labels[j]}<br>|R|={strength:.3f}<br>arg={phase:.3f}"] * 2,
                    "line": {"color": color, "width": 2.0 + 5.0 * strength},
                    "showlegend": False,
                }
            )

    node_trace = {
        "type": "scatter3d",
        "mode": "markers+text",
        "x": positions[:, 0].astype(float).tolist(),
        "y": positions[:, 1].astype(float).tolist(),
        "z": z_display.astype(float).tolist(),
        "text": list(labels),
        "textposition": "top center",
        "hovertemplate": "cell %{text}<br>x=%{x}<br>y=%{y}<br>z=%{z:.3f}<br>a3=%{marker.color:.3f}<extra></extra>",
        "marker": {
            "size": 7,
            "color": node_cmap_field.astype(float).tolist(),
            "colorscale": "RdBu",
            "reversescale": True,
            "colorbar": {"title": "final a3"},
            "line": {"color": "black", "width": 1},
        },
        "showlegend": False,
    }

    traces = edge_traces + [node_trace]
    layout = {
        "title": {"text": f"Interactive 3D Network Snapshot (z = {projection_label})"},
        "scene": {
            "xaxis": {"title": "x"},
            "yaxis": {"title": "y"},
            "zaxis": {"title": f"z ({projection_label})"},
            "camera": {"eye": {"x": 1.55, "y": -1.55, "z": 1.1}},
        },
        "margin": {"l": 0, "r": 0, "b": 0, "t": 45},
    }
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Interactive 3D Network Snapshot</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body style="margin:0;background:#ffffff;font-family:Arial,sans-serif;">
  <div id="plot" style="width:100vw;height:100vh;"></div>
  <script>
    const traces = {json.dumps(traces, ensure_ascii=False)};
    const layout = {json.dumps(layout, ensure_ascii=False)};
    Plotly.newPlot("plot", traces, layout, {{responsive: true, displaylogo: false}});
  </script>
</body>
</html>
"""
    (run_dir / f"interactive_network_3d_{timestamp}.html").write_text(html, encoding="utf-8")


def save_plotly_surface_3d_html(
    run_dir: Path,
    timestamp: str,
    z_grid: np.ndarray,
    width: int,
    height: int,
    projection_label: str,
) -> None:
    x = list(range(width))
    y = list(range(height))
    z = z_grid.reshape(height, width).astype(float)
    trace = {
        "type": "surface",
        "x": x,
        "y": y,
        "z": z.tolist(),
        "colorscale": "Viridis",
        "colorbar": {"title": projection_label},
        "hovertemplate": "x=%{x}<br>y=%{y}<br>z=%{z:.3f}<extra></extra>",
    }
    layout = {
        "title": {"text": f"Interactive 3D Surface (z = {projection_label})"},
        "scene": {
            "xaxis": {"title": "x"},
            "yaxis": {"title": "y"},
            "zaxis": {"title": projection_label},
            "camera": {"eye": {"x": 1.45, "y": -1.35, "z": 1.0}},
        },
        "margin": {"l": 0, "r": 0, "b": 0, "t": 45},
    }
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Interactive 3D Surface</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body style="margin:0;background:#ffffff;font-family:Arial,sans-serif;">
  <div id="plot" style="width:100vw;height:100vh;"></div>
  <script>
    const traces = [{json.dumps(trace, ensure_ascii=False)}];
    const layout = {json.dumps(layout, ensure_ascii=False)};
    Plotly.newPlot("plot", traces, layout, {{responsive: true, displaylogo: false}});
  </script>
</body>
</html>
"""
    (run_dir / f"interactive_surface_3d_{timestamp}.html").write_text(html, encoding="utf-8")


def save_plotly_surface_3d_points_html(
    run_dir: Path,
    timestamp: str,
    positions: np.ndarray,
    z_values: np.ndarray,
    labels: Sequence[str],
    projection_label: str,
) -> None:
    trace = {
        "type": "mesh3d",
        "x": positions[:, 0].astype(float).tolist(),
        "y": positions[:, 1].astype(float).tolist(),
        "z": z_values.astype(float).tolist(),
        "intensity": z_values.astype(float).tolist(),
        "colorscale": "Viridis",
        "opacity": 0.80,
        "hovertemplate": "x=%{x}<br>y=%{y}<br>z=%{z:.3f}<extra></extra>",
    }
    labels_trace = {
        "type": "scatter3d",
        "mode": "markers+text",
        "x": positions[:, 0].astype(float).tolist(),
        "y": positions[:, 1].astype(float).tolist(),
        "z": z_values.astype(float).tolist(),
        "text": list(labels),
        "textposition": "top center",
        "marker": {"size": 5, "color": z_values.astype(float).tolist(), "colorscale": "Viridis", "showscale": False},
        "showlegend": False,
    }
    layout = {
        "title": {"text": f"Interactive 3D Surface (z = {projection_label})"},
        "scene": {
            "xaxis": {"title": "x"},
            "yaxis": {"title": "y"},
            "zaxis": {"title": projection_label},
            "camera": {"eye": {"x": 1.45, "y": -1.35, "z": 1.0}},
        },
        "margin": {"l": 0, "r": 0, "b": 0, "t": 45},
    }
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Interactive 3D Surface</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body style="margin:0;background:#ffffff;font-family:Arial,sans-serif;">
  <div id="plot" style="width:100vw;height:100vh;"></div>
  <script>
    const traces = [{json.dumps(trace, ensure_ascii=False)}, {json.dumps(labels_trace, ensure_ascii=False)}];
    const layout = {json.dumps(layout, ensure_ascii=False)};
    Plotly.newPlot("plot", traces, layout, {{responsive: true, displaylogo: false}});
  </script>
</body>
</html>
"""
    (run_dir / f"interactive_surface_3d_{timestamp}.html").write_text(html, encoding="utf-8")


def save_plotly_network_3d_timeseries_html(
    run_dir: Path,
    timestamp: str,
    positions: np.ndarray,
    labels: Sequence[str],
    z_series: np.ndarray,  # shape: (steps, N)
    node_color_series: np.ndarray,  # shape: (steps, N)
    edge_complex_series: np.ndarray,  # shape: (steps, N, N) complex
    times: np.ndarray,
    projection_label: str,
    target_frames: int,
) -> None:
    steps, cell_count = z_series.shape
    # 计算降采样步长，控制帧数不超过 target_frames
    stride = max(1, int(math.ceil(steps / max(1, target_frames))))
    frame_indices = list(range(0, steps, stride))
    active_pairs = [
        (i, j)
        for i in range(cell_count)
        for j in range(i + 1, cell_count)
        if float(np.max(np.abs(edge_complex_series[:, i, j]))) > 1e-10
    ]
    # 基础布局
    layout = {
        "title": {"text": f"Dynamic 3D Network (z = {projection_label})"},
        "scene": {
            "xaxis": {"title": "x"},
            "yaxis": {"title": "y"},
            "zaxis": {"title": f"z ({projection_label})"},
            "camera": {"eye": {"x": 1.55, "y": -1.55, "z": 1.1}},
        },
        "margin": {"l": 0, "r": 0, "b": 0, "t": 45},
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
                        "args": [
                            None,
                            {
                                "fromcurrent": True,
                                "frame": {"duration": 60, "redraw": False},
                                "transition": {"duration": 0},
                            },
                        ],
                    },
                    {
                        "label": "Pause",
                        "method": "animate",
                        "args": [
                            [None],
                            {
                                "mode": "immediate",
                                "frame": {"duration": 0, "redraw": False},
                                "transition": {"duration": 0},
                            },
                        ],
                    },
                    {
                        "label": "Reset",
                        "method": "animate",
                        "args": [
                            [0],
                            {
                                "mode": "immediate",
                                "frame": {"duration": 0, "redraw": False},
                                "transition": {"duration": 0},
                            },
                        ],
                    },
                ],
            }
        ],
    }
    # 初始帧 traces（使用第一个索引）
    i0 = frame_indices[0]
    traces = []
    # 边 traces
    for i, j in active_pairs:
        val = edge_complex_series[i0, i, j]
        strength = float(np.abs(val))
        if strength <= 1e-10:
            strength = 0.0
        phase = float(np.angle(val))
        x0, y0 = positions[i]
        x1, y1 = positions[j]
        color_rgba = plt.cm.twilight((phase + np.pi) / (2.0 * np.pi))
        color = "rgba({},{},{},{:.3f})".format(
            int(round(color_rgba[0] * 255)),
            int(round(color_rgba[1] * 255)),
            int(round(color_rgba[2] * 255)),
            0.78,
        )
        traces.append(
            {
                "type": "scatter3d",
                "mode": "lines",
                "x": [float(x0), float(x1)],
                "y": [float(y0), float(y1)],
                "z": [float(z_series[i0, i]), float(z_series[i0, j])],
                "line": {"color": color, "width": 2.0 + 5.0 * strength},
                "hoverinfo": "text",
                "text": [f"edge {labels[i]}-{labels[j]}"] * 2,
                "showlegend": False,
            }
        )
    # 节点 trace
    traces.append(
        {
            "type": "scatter3d",
            "mode": "markers+text",
            "x": positions[:, 0].astype(float).tolist(),
            "y": positions[:, 1].astype(float).tolist(),
            "z": z_series[i0, :].astype(float).tolist(),
            "text": list(labels),
            "textposition": "top center",
            "hovertemplate": "cell %{text}<br>x=%{x}<br>y=%{y}<br>z=%{z:.3f}<br>a3=%{marker.color:.3f}<extra></extra>",
            "marker": {
                "size": 7,
                "color": node_color_series[i0, :].astype(float).tolist(),
                "colorscale": "RdBu",
                "reversescale": True,
                "colorbar": {"title": "a3 (per-step)"},
                "line": {"color": "black", "width": 1},
            },
            "showlegend": False,
        }
    )
    # 构建 frames
    frames = []
    for fi, step in enumerate(frame_indices):
        frame_data = []
        # 更新每一条边
        for i, j in active_pairs:
            val = edge_complex_series[step, i, j]
            strength = float(np.abs(val))
            phase = float(np.angle(val))
            x0, y0 = positions[i]
            x1, y1 = positions[j]
            color_rgba = plt.cm.twilight((phase + np.pi) / (2.0 * np.pi))
            color = "rgba({},{},{},{:.3f})".format(
                int(round(color_rgba[0] * 255)),
                int(round(color_rgba[1] * 255)),
                int(round(color_rgba[2] * 255)),
                0.78,
            )
            frame_data.append(
                {
                    "type": "scatter3d",
                    "mode": "lines",
                    "x": [float(x0), float(x1)],
                    "y": [float(y0), float(y1)],
                    "z": [float(z_series[step, i]), float(z_series[step, j])],
                    "line": {"color": color, "width": 2.0 + 5.0 * strength},
                    "hoverinfo": "text",
                    "text": [f"edge {labels[i]}-{labels[j]}"] * 2,
                    "showlegend": False,
                }
            )
        # 节点
        frame_data.append(
            {
                "type": "scatter3d",
                "mode": "markers+text",
                "x": positions[:, 0].astype(float).tolist(),
                "y": positions[:, 1].astype(float).tolist(),
                "z": z_series[step, :].astype(float).tolist(),
                "text": list(labels),
                "textposition": "top center",
                "hovertemplate": "cell %{text}<br>x=%{x}<br>y=%{y}<br>z=%{z:.3f}<br>a3=%{marker.color:.3f}<extra></extra>",
                "marker": {
                    "size": 7,
                    "color": node_color_series[step, :].astype(float).tolist(),
                    "colorscale": "RdBu",
                    "reversescale": True,
                    "colorbar": {"title": "a3 (per-step)"},
                    "line": {"color": "black", "width": 1},
                },
                "showlegend": False,
            }
        )
        frames.append({"name": str(fi), "data": frame_data})
    # slider 配置
    slider_steps = [{"label": f"t={times[idx]:.2f}", "method": "animate", "args": [[str(si)], {"mode": "immediate", "frame": {"duration": 0, "redraw": False}, "transition": {"duration": 0}}]} for si, idx in enumerate(frame_indices)]
    sliders = [{"pad": {"t": 35}, "currentvalue": {"prefix": "Time: "}, "steps": slider_steps}]
    layout["sliders"] = sliders
    # 生成 HTML
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Dynamic 3D Network (z = {projection_label})</title>
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
    (run_dir / f"interactive_network_3d_timeseries_{timestamp}.html").write_text(html, encoding="utf-8")


def simulate(args: argparse.Namespace) -> Path:
    lambdas = gell_mann_matrices()
    labels: List[str]
    if args.graph_config:
        (
            cell_count,
            edge_specs,
            triangles,
            positions,
            hamiltonians,
            static_s,
            static_components,
            labels,
            simulation_overrides,
        ) = build_graph_from_yaml(Path(args.graph_config), lambdas)
        args.duration = float(simulation_overrides.get("duration", args.duration))
        args.dt = float(simulation_overrides.get("dt", args.dt))
        args.coupling = float(simulation_overrides.get("coupling", args.coupling))
        args.geometry_gain = float(simulation_overrides.get("geometry_gain", args.geometry_gain))
        args.curvature_gain = float(simulation_overrides.get("curvature_gain", args.curvature_gain))
        args.state_gain = float(simulation_overrides.get("state_gain", args.state_gain))
        args.projection_z = str(simulation_overrides.get("projection_z", args.projection_z))
        args.z_scale = float(simulation_overrides.get("z_scale", args.z_scale))
    else:
        cell_count, edge_specs, triangles, positions = build_lattice(args.width, args.height, args.periodic)
        hamiltonians, static_s, static_components = build_local_hamiltonians(args.width, args.height, args.seed, lambdas)
        labels = [str(i) for i in range(cell_count)]
    psi = initialize_states(cell_count, args.seed)

    steps = int(math.floor(args.duration / args.dt))
    times = np.arange(steps, dtype=np.float64) * args.dt

    psi_series = np.zeros((steps, cell_count, 3), dtype=np.complex128)
    matrix_series = np.zeros((steps, cell_count, 3, 3), dtype=np.complex128)
    scalar_series = np.zeros((steps, cell_count), dtype=np.float64)
    component_series = np.zeros((steps, cell_count, 8), dtype=np.float64)
    edge_strength_series = np.zeros((steps, cell_count, cell_count), dtype=np.float64)
    edge_phase_series = np.zeros((steps, cell_count, cell_count), dtype=np.float64)
    closure_series = np.zeros((steps, len(triangles)), dtype=np.complex128)

    for step in range(steps):
        rho = density_matrices(psi)
        matrices = hamiltonians + args.state_gain * rho
        scalar_s, components = su3_components_from_matrix(matrices, lambdas)
        edges = build_edge_matrix(psi, components, edge_specs, args.geometry_gain, args.curvature_gain)
        closures = compute_triangle_closures(edges, triangles)

        psi_series[step] = psi
        matrix_series[step] = matrices
        scalar_series[step] = scalar_s
        component_series[step] = components
        edge_strength_series[step] = np.abs(edges)
        edge_phase_series[step] = np.angle(edges)
        closure_series[step] = closures

        psi = rk4_step(
            psi=psi,
            dt=args.dt,
            hamiltonians=hamiltonians,
            edge_specs=edge_specs,
            lambdas=lambdas,
            coupling=args.coupling,
            geometry_gain=args.geometry_gain,
            curvature_gain=args.curvature_gain,
        )

    mean_components = np.mean(component_series, axis=1)
    closure_real_mean = np.mean(closure_series.real, axis=1) if len(triangles) else np.zeros(steps, dtype=np.float64)
    closure_phase_mean = np.angle(np.mean(closure_series, axis=1)) if len(triangles) else np.zeros(steps, dtype=np.float64)

    summary = UniverseSummary(
        width=args.width,
        height=args.height,
        cell_count=cell_count,
        edge_count=len(edge_specs),
        triangle_count=len(triangles),
        steps=steps,
        dt=float(args.dt),
        duration=float(times[-1]) if len(times) else 0.0,
        mean_edge_strength=float(np.mean(edge_strength_series)),
        mean_edge_phase=float(np.angle(np.mean(np.exp(1j * edge_phase_series)))),
        mean_triangle_closure_real=float(np.mean(closure_series.real)) if len(triangles) else 0.0,
        mean_triangle_closure_phase=float(np.angle(np.mean(closure_series))) if len(triangles) else 0.0,
        peak_triangle_closure_real=float(np.max(closure_series.real)) if len(triangles) else 0.0,
        final_mean_a3=float(np.mean(component_series[-1, :, 2])) if steps else 0.0,
        final_mean_a8=float(np.mean(component_series[-1, :, 7])) if steps else 0.0,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = create_output_dir() / f"cellular_virtual_universe_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        run_dir / f"state_series_{timestamp}.npz",
        times=times,
        psi_real=psi_series.real,
        psi_imag=psi_series.imag,
        matrix_real=matrix_series.real,
        matrix_imag=matrix_series.imag,
        scalar_s=scalar_series,
        su3_components=component_series,
        edge_strength_series=edge_strength_series,
        edge_phase_series=edge_phase_series,
        closure_real=closure_series.real,
        closure_imag=closure_series.imag,
        static_scalar_s=static_s,
        static_components=static_components,
        positions=positions,
        triangles=np.array(triangles, dtype=np.int32),
        labels=np.array(labels, dtype=object),
    )

    with (run_dir / f"summary_{timestamp}.json").open("w", encoding="utf-8") as f:
        json.dump(asdict(summary), f, indent=2)

    plot_mean_components(run_dir, timestamp, times, mean_components)
    plot_closure_series(run_dir, timestamp, times, closure_real_mean, closure_phase_mean)
    # Choose z field for 3D projection
    if args.projection_z == "a3":
        z_field = component_series[-1, :, 2]
    elif args.projection_z == "a8":
        z_field = component_series[-1, :, 7]
    else:  # "S"
        z_field = scalar_series[-1]
    z_display = normalize_projection_field(z_field, args.z_scale)

    if args.graph_config:
        plot_final_field_map_points(
            run_dir,
            timestamp,
            positions,
            component_series[-1, :, 2],
            title="Final a3 Bias Field",
            file_stem="final_a3_heatmap",
            labels=labels,
        )
        plot_field_panels_points(run_dir, timestamp, positions, scalar_series[-1], component_series[-1], labels)
    else:
        plot_final_heatmap(run_dir, timestamp, component_series[-1, :, 2], args.width, args.height)
        plot_field_panels(run_dir, timestamp, scalar_series[-1], component_series[-1], args.width, args.height)
    plot_network_snapshot(
        run_dir,
        timestamp,
        positions,
        edge_strength_series[-1] * np.exp(1j * edge_phase_series[-1]),
        component_series[-1, :, 2],
        labels=labels,
    )
    # 3D projections
    plot_network_3d_snapshot(
        run_dir,
        timestamp,
        positions,
        edge_strength_series[-1] * np.exp(1j * edge_phase_series[-1]),
        z_display,
        component_series[-1, :, 2],
        args.projection_z,
        labels=labels,
    )
    if args.graph_config:
        plot_surface_3d_points(
            run_dir,
            timestamp,
            positions,
            z_display,
            labels,
            title=f"Final Surface (z = {args.projection_z}, scaled)",
        )
    else:
        plot_surface_3d(
            run_dir,
            timestamp,
            z_display,
            args.width,
            args.height,
            title=f"Final Surface (z = {args.projection_z}, scaled)",
        )
    save_plotly_network_3d_html(
        run_dir,
        timestamp,
        positions,
        edge_strength_series[-1] * np.exp(1j * edge_phase_series[-1]),
        z_display,
        component_series[-1, :, 2],
        args.projection_z,
        labels=labels,
    )
    save_plotly_network_3d_timeseries_html(
        run_dir,
        timestamp,
        positions,
        labels,
        np.array([normalize_projection_field(v, args.z_scale) for v in (component_series[:, :, 2] if args.projection_z == "a3" else component_series[:, :, 7] if args.projection_z == "a8" else scalar_series)]),
        component_series[:, :, 2],
        edge_strength_series * np.exp(1j * edge_phase_series),
        times,
        args.projection_z,
        args.target_frames,
    )
    if args.graph_config:
        save_plotly_surface_3d_points_html(
            run_dir,
            timestamp,
            positions,
            z_display,
            labels,
            args.projection_z,
        )
    else:
        save_plotly_surface_3d_html(
            run_dir,
            timestamp,
            z_display,
            args.width,
            args.height,
            args.projection_z,
        )

    print(f"Run directory: {run_dir}")
    print(f"Cells: {cell_count}, edges: {len(edge_specs)}, triangles: {len(triangles)}")
    print(f"Mean closure real: {summary.mean_triangle_closure_real:.6f}")
    print(f"Final mean a3: {summary.final_mean_a3:.6f}")
    return run_dir


def main() -> None:
    args = parse_args()
    simulate(args)


if __name__ == "__main__":
    main()
