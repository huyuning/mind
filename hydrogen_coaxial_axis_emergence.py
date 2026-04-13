#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

from cellular_plotly_pointcloud import line_trace, point_trace, save_plotly_3d_html
from csde_data_schema import AxisNodeRecord, CellRecord, EventRecord, FrameState, MetricRecord, RunStatus
from csde_stream_io import CSDEJsonlWriter
import hydrogen_quark_composition_toy as toy


def wrapped_phase_delta(a: float, b: float) -> float:
    delta = (a - b + math.pi) % (2.0 * math.pi) - math.pi
    return abs(delta)


def unit_vector(vec: np.ndarray, fallback: np.ndarray | None = None) -> np.ndarray:
    arr = np.asarray(vec, dtype=np.float64)
    norm = float(np.linalg.norm(arr))
    if norm > 1e-9:
        return arr / norm
    if fallback is None:
        return np.array([1.0, 0.0, 0.0], dtype=np.float64)
    fallback = np.asarray(fallback, dtype=np.float64)
    fallback_norm = float(np.linalg.norm(fallback))
    if fallback_norm > 1e-9:
        return fallback / fallback_norm
    return np.array([1.0, 0.0, 0.0], dtype=np.float64)


def circular_mean(phases: Sequence[float]) -> float:
    if not phases:
        return 0.0
    c = sum(math.cos(value) for value in phases)
    s = sum(math.sin(value) for value in phases)
    return math.atan2(s, c)


def coaxial_angle(direction_a: np.ndarray, direction_b: np.ndarray) -> float:
    dot = float(np.clip(np.dot(unit_vector(direction_a), unit_vector(direction_b)), -1.0, 1.0))
    return math.acos(abs(dot))


def phase_alignment_score(phase_diff: float, threshold: float) -> float:
    return max(0.0, 1.0 - phase_diff / max(threshold, 1e-9))


def distance_alignment_score(dist: float, threshold: float) -> float:
    return max(0.0, 1.0 - dist / max(threshold, 1e-9))


@dataclass
class AxisNode:
    id: int
    center: np.ndarray
    direction: np.ndarray
    phase: float
    strength: float
    level: int
    parent_ids: List[int]
    source_labels: List[str]
    birth_time: float
    last_update_time: float
    lifetime: float
    persistence: float
    closure_count: int
    active: bool = True

    def to_json(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["center"] = np.asarray(self.center, dtype=np.float64).round(8).tolist()
        payload["direction"] = np.asarray(self.direction, dtype=np.float64).round(8).tolist()
        return payload


@dataclass
class ClosureCandidate:
    center: np.ndarray
    direction: np.ndarray
    phase: float
    strength: float
    level: int
    parent_ids: List[int]
    source_labels: List[str]
    closure_kind: str


@dataclass
class IntegrationAction:
    action_type: str
    axis_id: int
    closure_kind: str
    level: int
    parent_ids: List[int]
    source_labels: List[str]
    strength: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prototype for persistent coaxial-axis emergence in the hydrogen toy")
    parser.add_argument("--duration", type=float, default=14.0, help="simulation duration")
    parser.add_argument("--dt", type=float, default=0.04, help="simulation timestep")
    parser.add_argument("--proton-radius", type=float, default=1.2, help="proton core scale")
    parser.add_argument("--phase-threshold", type=float, default=1.08, help="pair closure phase threshold in radians")
    parser.add_argument("--pair-distance-factor", type=float, default=2.05, help="pair closure distance threshold relative to mean pair radius")
    parser.add_argument("--merge-angle-threshold", type=float, default=0.38, help="axis merge threshold in radians")
    parser.add_argument("--merge-center-threshold", type=float, default=0.82, help="axis merge center distance threshold")
    parser.add_argument("--coaxial-angle-threshold", type=float, default=0.26, help="active-axis coaxial spawn angle threshold in radians")
    parser.add_argument("--coaxial-phase-threshold", type=float, default=0.78, help="active-axis coaxial spawn phase threshold in radians")
    parser.add_argument("--coaxial-center-threshold", type=float, default=1.15, help="active-axis coaxial spawn center threshold")
    parser.add_argument("--decay-time", type=float, default=1.4, help="axis persistence decay time")
    parser.add_argument("--reinforce-gain", type=float, default=0.34, help="persistence reinforcement on matched closure")
    parser.add_argument("--retire-threshold", type=float, default=0.12, help="retire axis node below this persistence")
    parser.add_argument("--max-level", type=int, default=3, help="maximum coaxial recursion level")
    parser.add_argument("--axis-line-scale", type=float, default=0.9, help="3D line length scale for active axes")
    parser.add_argument("--stream-write", action="store_true", help="write CSDE state/event/metric streams during the run")
    parser.add_argument("--stream-every", type=int, default=1, help="write one streamed frame every N simulation steps")
    return parser.parse_args()


def create_output_dir() -> Path:
    root = Path("resonance_data")
    root.mkdir(parents=True, exist_ok=True)
    out_dir = root / f"hydrogen_coaxial_axis_emergence_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def instantaneous_quark_phase(spec: toy.QuarkSpec, t: float) -> float:
    base_freq, _ = toy.FLAVOR_TO_FREQ_AMP[spec.flavor]
    return 2.0 * math.pi * (0.55 * base_freq) * t + spec.phase


def closure_candidates_from_quarks(specs: Sequence[toy.QuarkSpec], positions: np.ndarray, t: float, args: argparse.Namespace) -> List[ClosureCandidate]:
    candidates: List[ClosureCandidate] = []
    for i in range(len(specs)):
        for j in range(i + 1, len(specs)):
            rel = positions[j] - positions[i]
            dist = float(np.linalg.norm(rel))
            mean_scale = 0.5 * (float(specs[i].base_radius) + float(specs[j].base_radius))
            dist_threshold = float(args.pair_distance_factor) * mean_scale
            if dist > dist_threshold:
                continue
            phase_i = instantaneous_quark_phase(specs[i], t)
            phase_j = instantaneous_quark_phase(specs[j], t)
            phase_diff = wrapped_phase_delta(phase_i, phase_j)
            if phase_diff > args.phase_threshold:
                continue
            strength = 0.5 * (
                distance_alignment_score(dist, dist_threshold)
                + phase_alignment_score(phase_diff, args.phase_threshold)
            )
            if strength <= 0.0:
                continue
            direction = unit_vector(rel)
            center = 0.5 * (positions[i] + positions[j])
            candidates.append(
                ClosureCandidate(
                    center=center,
                    direction=direction,
                    phase=circular_mean([phase_i, phase_j]),
                    strength=strength,
                    level=0,
                    parent_ids=[],
                    source_labels=[specs[i].label, specs[j].label],
                    closure_kind="pair",
                )
            )
    return candidates


def axis_match_score(candidate: ClosureCandidate, node: AxisNode, args: argparse.Namespace) -> float:
    if not node.active or node.level != candidate.level:
        return -1.0
    if candidate.level == 0 and set(candidate.source_labels) != set(node.source_labels):
        return -1.0
    if candidate.level > 0 and candidate.parent_ids and node.parent_ids and set(candidate.parent_ids) != set(node.parent_ids):
        return -1.0
    angle = coaxial_angle(candidate.direction, node.direction)
    if angle > args.merge_angle_threshold:
        return -1.0
    center_dist = float(np.linalg.norm(candidate.center - node.center))
    if center_dist > args.merge_center_threshold:
        return -1.0
    phase_diff = wrapped_phase_delta(candidate.phase, node.phase)
    if phase_diff > args.phase_threshold:
        return -1.0
    source_overlap = len(set(candidate.source_labels) & set(node.source_labels))
    overlap_bonus = 0.08 * float(source_overlap)
    return (
        0.45 * phase_alignment_score(phase_diff, args.phase_threshold)
        + 0.35 * distance_alignment_score(center_dist, args.merge_center_threshold)
        + 0.20 * distance_alignment_score(angle, args.merge_angle_threshold)
        + overlap_bonus
    )


def update_axis_node(node: AxisNode, candidate: ClosureCandidate, t: float, dt: float, args: argparse.Namespace) -> None:
    blend = 0.34
    node.center = (1.0 - blend) * node.center + blend * candidate.center
    combined_dir = (1.0 - blend) * node.direction + blend * candidate.direction
    node.direction = unit_vector(combined_dir, fallback=node.direction)
    node.phase = circular_mean([node.phase, candidate.phase])
    node.strength = (1.0 - blend) * node.strength + blend * candidate.strength
    node.last_update_time = float(t)
    node.lifetime = max(node.lifetime, node.last_update_time - node.birth_time)
    node.persistence = min(1.0, node.persistence + float(args.reinforce_gain))
    node.closure_count += 1
    node.active = True
    node.parent_ids = sorted(set(node.parent_ids) | set(candidate.parent_ids))
    node.source_labels = sorted(set(node.source_labels) | set(candidate.source_labels))


def create_axis_node(next_id: int, candidate: ClosureCandidate, t: float) -> AxisNode:
    return AxisNode(
        id=next_id,
        center=np.asarray(candidate.center, dtype=np.float64),
        direction=unit_vector(candidate.direction),
        phase=float(candidate.phase),
        strength=float(candidate.strength),
        level=int(candidate.level),
        parent_ids=list(candidate.parent_ids),
        source_labels=list(candidate.source_labels),
        birth_time=float(t),
        last_update_time=float(t),
        lifetime=0.0,
        persistence=min(1.0, 0.45 + 0.55 * float(candidate.strength)),
        closure_count=1,
        active=True,
    )


def decay_axis_nodes(nodes: List[AxisNode], updated_ids: set[int], t: float, dt: float, args: argparse.Namespace) -> None:
    for node in nodes:
        if node.id in updated_ids:
            continue
        node.persistence *= math.exp(-dt / max(args.decay_time, 1e-6))
        node.strength *= 0.995
        node.lifetime = max(node.lifetime, float(t) - node.birth_time)
        if node.persistence < args.retire_threshold:
            node.active = False


def spawn_coaxial_candidates(active_nodes: Sequence[AxisNode], args: argparse.Namespace) -> List[ClosureCandidate]:
    candidates: List[ClosureCandidate] = []
    for i in range(len(active_nodes)):
        for j in range(i + 1, len(active_nodes)):
            node_a = active_nodes[i]
            node_b = active_nodes[j]
            if not node_a.active or not node_b.active:
                continue
            level = max(node_a.level, node_b.level) + 1
            if level > args.max_level:
                continue
            angle = coaxial_angle(node_a.direction, node_b.direction)
            if angle > args.coaxial_angle_threshold:
                continue
            phase_diff = wrapped_phase_delta(node_a.phase, node_b.phase)
            if phase_diff > args.coaxial_phase_threshold:
                continue
            center_dist = float(np.linalg.norm(node_a.center - node_b.center))
            if center_dist > args.coaxial_center_threshold:
                continue
            combined_dir = unit_vector(node_a.strength * node_a.direction + node_b.strength * node_b.direction, fallback=node_a.direction)
            combined_center = 0.5 * (node_a.center + node_b.center)
            combined_strength = min(
                1.0,
                0.55 * (node_a.strength + node_b.strength)
                + 0.25 * phase_alignment_score(phase_diff, args.coaxial_phase_threshold)
                + 0.20 * distance_alignment_score(angle, args.coaxial_angle_threshold),
            )
            source_labels = sorted(set(node_a.source_labels) | set(node_b.source_labels))
            parent_ids = sorted({node_a.id, node_b.id})
            candidates.append(
                ClosureCandidate(
                    center=combined_center,
                    direction=combined_dir,
                    phase=circular_mean([node_a.phase, node_b.phase]),
                    strength=combined_strength,
                    level=level,
                    parent_ids=parent_ids,
                    source_labels=source_labels,
                    closure_kind="coaxial",
                )
            )
    return candidates


def integrate_candidates(
    nodes: List[AxisNode],
    candidates: Sequence[ClosureCandidate],
    t: float,
    dt: float,
    args: argparse.Namespace,
    next_id_ref: List[int],
) -> Tuple[set[int], List[IntegrationAction]]:
    updated_ids: set[int] = set()
    actions: List[IntegrationAction] = []
    for candidate in candidates:
        best_node: AxisNode | None = None
        best_score = -1.0
        for node in nodes:
            score = axis_match_score(candidate, node, args)
            if score > best_score:
                best_score = score
                best_node = node
        if best_node is not None and best_score >= 0.22:
            update_axis_node(best_node, candidate, t, dt, args)
            updated_ids.add(best_node.id)
            actions.append(
                IntegrationAction(
                    action_type="merge",
                    axis_id=best_node.id,
                    closure_kind=candidate.closure_kind,
                    level=candidate.level,
                    parent_ids=list(candidate.parent_ids),
                    source_labels=list(candidate.source_labels),
                    strength=float(candidate.strength),
                )
            )
            continue
        new_node = create_axis_node(next_id_ref[0], candidate, t)
        nodes.append(new_node)
        updated_ids.add(new_node.id)
        actions.append(
            IntegrationAction(
                action_type="create",
                axis_id=new_node.id,
                closure_kind=candidate.closure_kind,
                level=candidate.level,
                parent_ids=list(candidate.parent_ids),
                source_labels=list(candidate.source_labels),
                strength=float(candidate.strength),
            )
        )
        next_id_ref[0] += 1
    return updated_ids, actions


def mass_proxies(active_nodes: Sequence[AxisNode]) -> Tuple[float, float, float]:
    if not active_nodes:
        return 0.0, 0.0, 0.0
    total = sum(node.persistence * node.strength * (1.0 + 0.25 * node.level) for node in active_nodes)
    max_strength = max(node.persistence * node.strength for node in active_nodes)
    mean_level = sum(node.level for node in active_nodes) / max(len(active_nodes), 1)
    parallel = total / (1.0 + 0.65 * max_strength)
    absorbed_axes = sum(node.persistence for node in active_nodes) * (1.0 + 0.15 * mean_level)
    return float(total), float(parallel), float(absorbed_axes)


def dominant_frequency(signal: np.ndarray, dt: float) -> Tuple[float, float]:
    if signal.size < 4 or dt <= 0.0:
        return 0.0, 0.0
    centered = np.asarray(signal, dtype=np.float64) - float(np.mean(signal))
    if float(np.std(centered)) < 1e-9:
        return 0.0, 0.0
    window = np.hanning(centered.size)
    spectrum = np.fft.rfft(centered * window)
    freqs = np.fft.rfftfreq(centered.size, d=dt)
    if freqs.size <= 1:
        return 0.0, 0.0
    amplitudes = np.abs(spectrum)
    amplitudes[0] = 0.0
    idx = int(np.argmax(amplitudes))
    return float(freqs[idx]), float(amplitudes[idx])


def resonance_frequency_metrics(time_rows: Sequence[Dict[str, object]], dt: float) -> Dict[str, float]:
    if not time_rows:
        return {
            "dominant_frequency_mean": 0.0,
            "dominant_frequency_std": 0.0,
            "frequency_lock_ratio": 0.0,
            "resonance_frequency_stability_score": 0.0,
        }

    signal = np.asarray(
        [
            float(row["mass_total_proxy"])
            + 0.35 * float(row["active_axis_count"])
            + 0.20 * float(row["coaxial_candidate_count"])
            + 0.10 * float(row["pair_candidate_count"])
            for row in time_rows
        ],
        dtype=np.float64,
    )
    sample_count = signal.size
    if sample_count < 8 or dt <= 0.0:
        freq, _ = dominant_frequency(signal, dt)
        return {
            "dominant_frequency_mean": float(freq),
            "dominant_frequency_std": 0.0,
            "frequency_lock_ratio": 1.0 if freq > 0.0 else 0.0,
            "resonance_frequency_stability_score": 1.0 if freq > 0.0 else 0.0,
        }

    window_size = max(16, min(sample_count, int(round(sample_count * 0.22))))
    if window_size >= sample_count:
        window_size = sample_count
    step = max(4, window_size // 2)
    window_freqs: List[float] = []
    resolutions: List[float] = []
    for start in range(0, sample_count - window_size + 1, step):
        segment = signal[start : start + window_size]
        freq, amp = dominant_frequency(segment, dt)
        if amp <= 1e-9:
            continue
        window_freqs.append(freq)
        resolutions.append(1.0 / max(window_size * dt, 1e-9))

    if not window_freqs:
        freq, _ = dominant_frequency(signal, dt)
        return {
            "dominant_frequency_mean": float(freq),
            "dominant_frequency_std": 0.0,
            "frequency_lock_ratio": 1.0 if freq > 0.0 else 0.0,
            "resonance_frequency_stability_score": 1.0 if freq > 0.0 else 0.0,
        }

    freq_array = np.asarray(window_freqs, dtype=np.float64)
    dominant_mean = float(np.mean(freq_array))
    dominant_std = float(np.std(freq_array))
    central_freq = float(np.median(freq_array))
    resolution = float(np.mean(resolutions)) if resolutions else 0.0
    tolerance = max(0.10 * max(central_freq, 1e-9), resolution)
    lock_ratio = float(np.mean(np.abs(freq_array - central_freq) <= tolerance))
    relative_jitter = dominant_std / max(central_freq, resolution, 1e-9)
    stability_score = float(np.clip(lock_ratio * math.exp(-relative_jitter), 0.0, 1.0))
    return {
        "dominant_frequency_mean": dominant_mean,
        "dominant_frequency_std": dominant_std,
        "frequency_lock_ratio": lock_ratio,
        "resonance_frequency_stability_score": stability_score,
    }


def save_axis_nodes(path: Path, nodes: Sequence[AxisNode]) -> None:
    payload = [node.to_json() for node in nodes]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_time_series(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def axis_node_record(node: AxisNode) -> AxisNodeRecord:
    return AxisNodeRecord(
        id=str(node.id),
        center=np.asarray(node.center, dtype=np.float64).tolist(),
        direction=np.asarray(node.direction, dtype=np.float64).tolist(),
        level=int(node.level),
        strength=float(node.strength),
        persistence=float(node.persistence),
        parent_ids=[str(item) for item in node.parent_ids],
        phase=float(node.phase),
        active=bool(node.active),
        extras={
            "source_labels": list(node.source_labels),
            "birth_time": float(node.birth_time),
            "last_update_time": float(node.last_update_time),
            "lifetime": float(node.lifetime),
            "closure_count": int(node.closure_count),
        },
    )


def orthonormal_cell_frame(
    spec: toy.QuarkSpec,
    quark_series: np.ndarray,
    frame_index: int,
    quark_index: int,
) -> tuple[list[float], list[float], list[float], float]:
    n0 = unit_vector(toy.COLOR_TO_AXIS[spec.color], fallback=np.array([1.0, 0.0, 0.0], dtype=np.float64))

    prev_index = max(0, frame_index - 1)
    next_index = min(quark_series.shape[0] - 1, frame_index + 1)
    tangent = quark_series[next_index, quark_index] - quark_series[prev_index, quark_index]
    if float(np.linalg.norm(tangent)) < 1e-9:
        core_center = np.mean(quark_series[frame_index], axis=0)
        tangent = quark_series[frame_index, quark_index] - core_center
    tangent = tangent - np.dot(tangent, n0) * n0
    tangent_norm = float(np.linalg.norm(tangent))
    if tangent_norm < 1e-9:
        ref = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        if abs(float(np.dot(n0, ref))) > 0.95:
            ref = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        tangent = np.cross(ref, n0)
        tangent_norm = float(np.linalg.norm(tangent))
    n1 = tangent / max(tangent_norm, 1e-9)
    n2 = np.cross(n0, n1)
    n2 = n2 / max(float(np.linalg.norm(n2)), 1e-9)
    scale = 0.35 * float(spec.base_radius)
    return n0.tolist(), n1.tolist(), n2.tolist(), scale


def frame_state_from_step(
    frame_index: int,
    t: float,
    positions: np.ndarray,
    specs: Sequence[toy.QuarkSpec],
    quark_series: np.ndarray,
    active_nodes: Sequence[AxisNode],
    metrics: Dict[str, object],
) -> FrameState:
    cells: List[CellRecord] = []
    for idx, spec in enumerate(specs):
        n0, n1, n2, scale = orthonormal_cell_frame(spec, quark_series, frame_index, idx)
        cells.append(
            CellRecord(
                id=str(spec.label),
                center=np.asarray(positions[idx], dtype=np.float64).tolist(),
                phase=float(instantaneous_quark_phase(spec, t)),
                frequency=float(toy.FLAVOR_TO_FREQ_AMP[spec.flavor][0]),
                amplitude=float(toy.FLAVOR_TO_FREQ_AMP[spec.flavor][1]),
                radius=float(spec.base_radius),
                level=0,
                parent_id=None,
                active=True,
                extras={
                    "flavor": spec.flavor,
                    "color": spec.color,
                    "local_frame": {
                        "n0": n0,
                        "n1": n1,
                        "n2": n2,
                        "scale": scale,
                        "source": "color_axis+tangent",
                    },
                },
            )
        )
    axis_nodes = [axis_node_record(node) for node in active_nodes]
    numeric_metrics = {
        str(key): float(value)
        for key, value in metrics.items()
        if key != "time" and isinstance(value, (int, float))
    }
    return FrameState(
        frame_index=frame_index,
        time=float(t),
        cells=cells,
        axis_nodes=axis_nodes,
        coaxial_clusters=[],
        metrics=numeric_metrics,
        metadata={"experiment_name": "hydrogen_coaxial_axis_emergence"},
    )


def status_record(run_id: str, latest_frame_index: int, latest_time: float, status: str, message: str = "") -> RunStatus:
    return RunStatus(
        run_id=run_id,
        experiment_name="hydrogen_coaxial_axis_emergence",
        status=status,
        latest_frame_index=int(latest_frame_index),
        latest_time=float(latest_time),
        message=message,
    )


def active_axis_traces(nodes: Sequence[AxisNode], axis_line_scale: float) -> List[object]:
    if not nodes:
        return []
    level_colors = {
        0: "#f59e0b",
        1: "#22d3ee",
        2: "#a78bfa",
        3: "#f472b6",
    }
    traces: List[object] = []
    for level in sorted({node.level for node in nodes}):
        level_nodes = [node for node in nodes if node.level == level]
        centers = np.asarray([node.center for node in level_nodes], dtype=np.float64)
        strengths = np.asarray([node.persistence * node.strength for node in level_nodes], dtype=np.float64)
        traces.append(
            point_trace(
                points=centers,
                name=f"axis level {level}",
                size=5.0 + 1.4 * level,
                opacity=0.9,
                color=level_colors.get(level, "#e5e7eb"),
                color_values=strengths,
                colorscale="Viridis",
                showscale=(level == max(node.level for node in nodes)),
            )
        )
        for node in level_nodes:
            half_length = axis_line_scale * (0.35 + 0.65 * node.persistence) * (1.0 + 0.22 * node.level)
            segment = np.vstack(
                [
                    node.center - half_length * node.direction,
                    node.center + half_length * node.direction,
                ]
            )
            traces.append(
                line_trace(
                    points=segment,
                    name=f"axis {node.id}",
                    color=level_colors.get(level, "#e5e7eb"),
                    width=3.0 + level,
                    opacity=0.58,
                )
            )
    return traces


def run(args: argparse.Namespace) -> Tuple[Path, Dict[str, object]]:
    out_dir = create_output_dir()
    stream_writer = CSDEJsonlWriter(out_dir) if getattr(args, "stream_write", False) else None
    run_id = out_dir.name
    specs = toy.build_quark_specs(args.proton_radius)
    times = np.arange(0.0, args.duration + 0.5 * args.dt, args.dt, dtype=np.float64)
    quark_series = np.zeros((len(times), len(specs), 3), dtype=np.float64)
    for ti, t in enumerate(times):
        for qi, spec in enumerate(specs):
            quark_series[ti, qi] = toy.quark_position(spec, float(t))

    nodes: List[AxisNode] = []
    time_rows: List[Dict[str, object]] = []
    next_id_ref = [1]
    event_index = 0
    if stream_writer is not None:
        stream_writer.update_status(status_record(run_id, latest_frame_index=-1, latest_time=0.0, status="running", message="stream initialized"))

    for ti, t in enumerate(times):
        positions = quark_series[ti]
        previous_node_ids = {node.id for node in nodes}
        previous_active_ids = {node.id for node in nodes if node.active}
        pair_candidates = closure_candidates_from_quarks(specs, positions, float(t), args)
        pair_updated_ids, pair_actions = integrate_candidates(nodes, pair_candidates, float(t), float(args.dt), args, next_id_ref)
        active_leaf_nodes = [node for node in nodes if node.active]
        coaxial_candidates = spawn_coaxial_candidates(active_leaf_nodes, args)
        coaxial_updated_ids, coaxial_actions = integrate_candidates(nodes, coaxial_candidates, float(t), float(args.dt), args, next_id_ref)
        updated_ids = pair_updated_ids | coaxial_updated_ids
        decay_axis_nodes(nodes, updated_ids, float(t), float(args.dt), args)

        active_nodes = [node for node in nodes if node.active]
        mass_total, mass_parallel, absorbed_axes = mass_proxies(active_nodes)
        level_counts = {level: sum(1 for node in active_nodes if node.level == level) for level in range(args.max_level + 1)}
        row: Dict[str, object] = {
            "time": float(t),
            "pair_candidate_count": len(pair_candidates),
            "coaxial_candidate_count": len(coaxial_candidates),
            "active_axis_count": len(active_nodes),
            "mass_total_proxy": mass_total,
            "mass_parallel_proxy": mass_parallel,
            "absorbed_axis_proxy": absorbed_axes,
        }
        for level, count in level_counts.items():
            row[f"level_{level}_count"] = int(count)
        time_rows.append(row)

        if stream_writer is not None:
            current_node_map = {node.id: node for node in nodes}
            current_active_ids = {node.id for node in active_nodes}
            retired_ids = previous_active_ids - current_active_ids
            for candidate in pair_candidates:
                event_index += 1
                stream_writer.write_event(
                    EventRecord(
                        event_index=event_index,
                        time=float(t),
                        event_type="pair_closure_birth",
                        payload={
                            "closure_kind": candidate.closure_kind,
                            "level": int(candidate.level),
                            "center": np.asarray(candidate.center, dtype=np.float64).round(8).tolist(),
                            "direction": np.asarray(candidate.direction, dtype=np.float64).round(8).tolist(),
                            "strength": float(candidate.strength),
                            "source_labels": list(candidate.source_labels),
                        },
                    )
                )

            for action in pair_actions + coaxial_actions:
                node = current_node_map.get(action.axis_id)
                if node is None:
                    continue
                event_index += 1
                event_type = "axis_birth" if action.action_type == "create" else "axis_merge"
                stream_writer.write_event(
                    EventRecord(
                        event_index=event_index,
                        time=float(t),
                        event_type=event_type,
                        payload={
                            "axis_id": str(node.id),
                            "level": int(node.level),
                            "closure_kind": action.closure_kind,
                            "parent_ids": [str(item) for item in action.parent_ids],
                            "source_labels": list(action.source_labels),
                            "strength": float(node.strength),
                            "persistence": float(node.persistence),
                            "center": np.asarray(node.center, dtype=np.float64).round(8).tolist(),
                            "direction": np.asarray(node.direction, dtype=np.float64).round(8).tolist(),
                        },
                    )
                )
            for node_id in sorted(retired_ids):
                node = current_node_map.get(node_id)
                if node is None:
                    continue
                event_index += 1
                stream_writer.write_event(
                    EventRecord(
                        event_index=event_index,
                        time=float(t),
                        event_type="axis_retire",
                        payload={
                            "axis_id": str(node.id),
                            "level": int(node.level),
                        },
                    )
                )

            if ti % max(int(args.stream_every), 1) == 0:
                stream_writer.write_state(frame_state_from_step(ti, float(t), positions, specs, quark_series, active_nodes, row))
                stream_writer.write_metric(
                    MetricRecord(
                        frame_index=ti,
                        time=float(t),
                        values={str(key): float(value) for key, value in row.items() if key != "time"},
                    )
                )
            stream_writer.update_status(
                status_record(
                    run_id,
                    latest_frame_index=ti,
                    latest_time=float(t),
                    status="running",
                    message=f"streaming frame {ti}",
                )
            )

    active_nodes = [node for node in nodes if node.active]
    latest_positions = quark_series[-1]
    quark_traces = [
        line_trace(points=quark_series[:, idx, :], name=f"{spec.label} trajectory", color=toy.COLOR_TO_PLOT[spec.color], width=4.0, opacity=0.35)
        for idx, spec in enumerate(specs)
    ]
    quark_points = [
        point_trace(points=np.asarray([latest_positions[idx]]), name=spec.label, size=7.0, opacity=0.95, color=toy.COLOR_TO_PLOT[spec.color])
        for idx, spec in enumerate(specs)
    ]
    axis_traces = active_axis_traces(active_nodes, args.axis_line_scale)
    axis_span = max(1.2, float(np.max(np.abs(quark_series))) * 1.35)
    save_plotly_3d_html(
        output_path=out_dir / "3d_plotly_axes.html",
        title="Hydrogen Coaxial Axis Emergence",
        traces=[*quark_traces, *quark_points, *axis_traces],
        axis_span=axis_span,
    )
    save_axis_nodes(out_dir / "axis_nodes.json", nodes)
    save_time_series(out_dir / "mass_tensor_series.csv", time_rows)
    frequency_metrics = resonance_frequency_metrics(time_rows, float(args.dt))

    summary = {
        "duration": float(args.duration),
        "dt": float(args.dt),
        "sample_count": int(len(times)),
        "axis_node_count_total": int(len(nodes)),
        "axis_node_count_active": int(len(active_nodes)),
        "max_level": int(max((node.level for node in nodes), default=0)),
        "active_level_histogram": {
            str(level): int(sum(1 for node in active_nodes if node.level == level))
            for level in range(args.max_level + 1)
        },
        "latest_mass_total_proxy": float(time_rows[-1]["mass_total_proxy"]) if time_rows else 0.0,
        "latest_mass_parallel_proxy": float(time_rows[-1]["mass_parallel_proxy"]) if time_rows else 0.0,
        "latest_absorbed_axis_proxy": float(time_rows[-1]["absorbed_axis_proxy"]) if time_rows else 0.0,
        "dominant_frequency_mean": float(frequency_metrics["dominant_frequency_mean"]),
        "dominant_frequency_std": float(frequency_metrics["dominant_frequency_std"]),
        "frequency_lock_ratio": float(frequency_metrics["frequency_lock_ratio"]),
        "resonance_frequency_stability_score": float(frequency_metrics["resonance_frequency_stability_score"]),
        "output_axis_nodes": str(out_dir / "axis_nodes.json"),
        "output_mass_series": str(out_dir / "mass_tensor_series.csv"),
        "output_plotly_html": str(out_dir / "3d_plotly_axes.html"),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if stream_writer is not None:
        stream_writer.update_status(
            status_record(
                run_id,
                latest_frame_index=len(times) - 1,
                latest_time=float(times[-1] if len(times) else 0.0),
                status="finished",
                message="stream completed",
            )
        )
        stream_writer.close()
    return out_dir, summary


def main() -> None:
    args = parse_args()
    out_dir, summary = run(args)
    print(f"Run directory: {out_dir}")
    print(f"Axis nodes total/active: {summary['axis_node_count_total']} / {summary['axis_node_count_active']}")
    print(f"Latest mass total proxy: {summary['latest_mass_total_proxy']:.6f}")
    print(f"Latest mass parallel proxy: {summary['latest_mass_parallel_proxy']:.6f}")


if __name__ == "__main__":
    main()
