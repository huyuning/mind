#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

import pygfx as gfx
try:
    # Preferred backend for newer pygfx stacks.
    from rendercanvas.pyside6 import QRenderCanvas as _WgpuCanvas  # type: ignore
except Exception:  # pragma: no cover
    try:
        from rendercanvas.qt import QRenderCanvas as _WgpuCanvas  # type: ignore
    except Exception:
        from rendercanvas.auto import RenderCanvas as _WgpuCanvas  # type: ignore
from csde_data_schema import AxisNodeRecord, CellRecord, EventRecord, FrameState, MetricRecord, RunStatus, TriadCoreState, TriadRecord
from csde_closure_tensor import build_closure_phase_tensor, compute_closure_phase_shells, infer_closure_tensor_layout, query_reconnect_candidates, survey_closure_tensor_statistics
from csde_dimension_generation import build_dimension_frame
from csde_topology_engine import apply_topology_transitions
from csde_triad_dynamics import TRIAD_EDGE_PAIRS, _triad_edge_complex, _triangle_normal, build_triad_core_state_from_cells, circular_mean_phase, minimum_closure_sphere, triad_core_step
from csde_stream_io import CSDEJsonlReader


DIMENSION_STAGE_COLORS = {
    "seed": QtGui.QColor("#64748b"),
    "planar": QtGui.QColor("#f59e0b"),
    "lift": QtGui.QColor("#06b6d4"),
    "closure": QtGui.QColor("#22c55e"),
}
DIMENSION_STAGE_LABELS = {
    "planar": "P",
    "lift": "L",
    "closure": "C",
}
DIMENSION_STAGE_RGB = {
    name: (color.redF(), color.greenF(), color.blueF(), 1.0)
    for name, color in DIMENSION_STAGE_COLORS.items()
}
SHELL_SPECS = [
    ("lat:-45", "latitude", -math.pi / 4.0),
    ("lat:0", "latitude", 0.0),
    ("lat:+45", "latitude", math.pi / 4.0),
    ("lon:0", "longitude", 0.0),
    ("lon:60", "longitude", math.pi / 3.0),
    ("lon:120", "longitude", 2.0 * math.pi / 3.0),
]
SLICE_PLANES = ["XY", "XZ", "YZ"]


def build_demo_frames(frame_count: int = 160) -> List[FrameState]:
    dt = 0.05
    seed_cells = [
        CellRecord(
            id="cell-0",
            center=[1.08, 0.05, 0.10],
            phase=0.0,
            frequency=0.24,
            amplitude=0.82,
            radius=0.24,
            level=0,
            active=True,
            extras={"local_frame": {"n0": [1.0, 0.0, 0.0], "n1": [0.0, 1.0, 0.0], "n2": [0.0, 0.0, 1.0], "scale": 0.24}},
        ),
        CellRecord(
            id="cell-1",
            center=[-0.55, 0.92, -0.08],
            phase=2.1,
            frequency=0.22,
            amplitude=0.76,
            radius=0.22,
            level=0,
            active=True,
            extras={"local_frame": {"n0": [0.0, 1.0, 0.0], "n1": [-1.0, 0.0, 0.0], "n2": [0.0, 0.0, 1.0], "scale": 0.22}},
        ),
        CellRecord(
            id="cell-2",
            center=[-0.48, -0.82, 0.92],
            phase=4.18,
            frequency=0.20,
            amplitude=0.91,
            radius=0.26,
            level=0,
            active=True,
            extras={"local_frame": {"n0": [0.0, 0.0, 1.0], "n1": [1.0, 0.0, 0.0], "n2": [0.0, 1.0, 0.0], "scale": 0.26}},
        ),
    ]
    state = build_triad_core_state_from_cells(seed_cells, triad_id="triad-0", connector_strength=0.62)
    frames: List[FrameState] = []

    initial_positions = np.asarray(state.node_position, dtype=np.float64)
    stable_center = np.mean(initial_positions, axis=0)
    line_direction = initial_positions[1] - initial_positions[0]
    line_direction = line_direction / max(float(np.linalg.norm(line_direction)), 1e-6)
    line_scalars = np.array([-0.72, 0.0, 0.72], dtype=np.float64)

    for i in range(frame_count):
        t = i * dt
        base_positions = np.asarray(state.node_position, dtype=np.float64)
        base_center = np.mean(base_positions, axis=0)

        if 40 <= i < 90:
            split_progress = min(1.0, (i - 40) / 18.0)
            collapsed_positions = np.vstack(
                [
                    stable_center + scalar * line_direction + np.array([0.0, 0.0, 0.015 * idx], dtype=np.float64)
                    for idx, scalar in enumerate(line_scalars)
                ]
            )
            forced_positions = (1.0 - split_progress) * base_positions + split_progress * collapsed_positions
            connector_position = base_center
            connector_strength = 0.16 + 0.06 * math.sin(0.25 * i)
        elif 90 <= i < 126:
            reconnect_progress = min(1.0, (i - 90) / 24.0)
            orbital_positions = initial_positions.copy()
            orbital_positions[0] += np.array([0.24 * math.cos(0.11 * i), 0.18 * math.sin(0.12 * i), 0.08 * math.sin(0.09 * i)], dtype=np.float64)
            orbital_positions[1] += np.array([-0.16 * math.sin(0.1 * i), 0.20 * math.cos(0.08 * i), 0.06 * math.cos(0.13 * i)], dtype=np.float64)
            orbital_positions[2] += np.array([0.14 * math.sin(0.07 * i), -0.22 * math.cos(0.09 * i), 0.18 * math.sin(0.1 * i)], dtype=np.float64)
            forced_positions = (1.0 - reconnect_progress) * base_positions + reconnect_progress * orbital_positions
            forced_center = np.mean(forced_positions, axis=0)
            forced_normal = _triangle_normal(forced_positions)
            connector_position = forced_center + (0.46 + 0.18 * reconnect_progress) * forced_normal
            connector_strength = 0.22 + 0.52 * reconnect_progress
        else:
            orbit_positions = initial_positions.copy()
            orbit_positions[0] += np.array([0.18 * math.cos(0.08 * i), 0.12 * math.sin(0.10 * i), 0.06 * math.sin(0.06 * i)], dtype=np.float64)
            orbit_positions[1] += np.array([-0.11 * math.sin(0.07 * i), 0.17 * math.cos(0.08 * i), 0.05 * math.cos(0.05 * i)], dtype=np.float64)
            orbit_positions[2] += np.array([0.09 * math.sin(0.06 * i), -0.14 * math.cos(0.09 * i), 0.12 * math.sin(0.07 * i)], dtype=np.float64)
            mix = 0.35
            forced_positions = (1.0 - mix) * base_positions + mix * orbit_positions
            forced_center = np.mean(forced_positions, axis=0)
            forced_normal = _triangle_normal(forced_positions)
            connector_position = forced_center + 0.54 * forced_normal
            connector_strength = 0.58 + 0.08 * math.sin(0.04 * i)

        state = TriadCoreState(
            id=state.id,
            node_duty=list(state.node_duty),
            node_freq=list(state.node_freq),
            node_phase=list(state.node_phase),
            node_position=np.asarray(forced_positions, dtype=np.float64).tolist(),
            node_velocity=list(state.node_velocity),
            node_axis=list(state.node_axis),
            edge_state_real=list(state.edge_state_real),
            edge_state_imag=list(state.edge_state_imag),
            connector_position=np.asarray(connector_position, dtype=np.float64).tolist(),
            connector_velocity=[0.0, 0.0, 0.0],
            connector_phase=float(state.connector_phase),
            connector_freq=float(state.connector_freq if state.connector_freq else np.mean(state.node_freq)),
            connector_strength=float(max(0.05, min(connector_strength, 1.2))),
            active=True,
            extras={**state.extras, "lineage_id": "demo-lineage-0", "source_cell_ids": [cell.id for cell in seed_cells]},
        )
        state, diagnostics = triad_core_step(state, dt=dt)

        cells: list[CellRecord] = []
        for idx, point in enumerate(np.asarray(state.node_position, dtype=np.float64)):
            basis = orthonormal_basis_from_hint(np.asarray(state.node_axis[idx], dtype=np.float32))
            radius = float(seed_cells[idx].radius)
            cells.append(
                CellRecord(
                    id=seed_cells[idx].id,
                    center=np.asarray(point, dtype=np.float64).tolist(),
                    phase=float(state.node_phase[idx]),
                    frequency=float(state.node_freq[idx]),
                    amplitude=float(state.node_duty[idx]),
                    radius=radius,
                    level=0,
                    active=True,
                    extras={
                        "local_frame": {
                            "n0": basis[0].tolist(),
                            "n1": basis[1].tolist(),
                            "n2": basis[2].tolist(),
                            "scale": radius,
                            "source": "triad_dynamics_demo",
                        }
                    },
                )
            )

        axis_nodes = [
            AxisNodeRecord(
                id="axis-0",
                level=0,
                center=[0.0, 0.0, 0.0],
                direction=[
                    math.cos(0.35 * t),
                    math.sin(0.35 * t),
                    0.15 * math.sin(0.7 * t),
                ],
                strength=0.85,
                persistence=0.90,
            ),
            AxisNodeRecord(
                id="axis-1",
                level=1,
                center=[0.35 * math.cos(0.45 * t), 0.25 * math.sin(0.45 * t), 0.0],
                direction=[
                    0.2 * math.sin(0.55 * t),
                    1.0,
                    0.2 * math.cos(0.9 * t),
                ],
                strength=0.55,
                persistence=0.72,
            ),
            AxisNodeRecord(
                id="axis-2",
                level=2,
                center=[0.0, 0.0, 0.35 * math.sin(0.38 * t)],
                direction=[
                    0.75,
                    0.15 * math.cos(0.6 * t),
                    0.55,
                ],
                strength=0.40,
                persistence=0.58,
            ),
        ]
        triads = []
        triad_info = build_triad_unit(cells, triad_id="triad-0")
        if triad_info is not None:
            triad_info["triad"].extras["lineage_id"] = "demo-lineage-0"
            triad_info["triad"].extras["connector_phase"] = float(state.connector_phase)
            triad_info["triad"].extras["connector_freq"] = float(state.connector_freq)
            triad_info["triad"].extras["connector_strength"] = float(state.connector_strength)
            triad_info["triad"].extras["demo_stage"] = (
                "split" if 40 <= i < 90 else "reconnect" if 90 <= i < 126 else "stable"
            )
            triads.append(triad_info["triad"])
        frames.append(
            FrameState(
                frame_index=i,
                time=t,
                cells=cells,
                triads=triads,
                axis_nodes=axis_nodes,
                coaxial_clusters=[],
                metrics={
                    "mass_total_proxy": 9.0 + 0.6 * math.sin(0.4 * t),
                    "resonance_frequency_stability_score": 0.55 + 0.25 * float(state.connector_strength),
                    "triad_connector_strength": float(state.connector_strength),
                    "triad_phase_bar": float(diagnostics.get("phase_bar", 0.0)),
                },
                metadata={
                    "source": "triad_dynamics_demo",
                    "demo_stage": "split" if 40 <= i < 90 else "reconnect" if 90 <= i < 126 else "stable",
                },
            )
        )
    return frames


def cell_positions_from_frame(frame: FrameState) -> np.ndarray:
    if not frame.cells:
        return np.zeros((0, 3), dtype=np.float32)
    return np.asarray([cell.center for cell in frame.cells], dtype=np.float32)


def axis_direction_array(node: AxisNodeRecord) -> np.ndarray:
    return np.asarray(node.direction, dtype=np.float32)


def axis_center_array(node: AxisNodeRecord) -> np.ndarray:
    return np.asarray(node.center, dtype=np.float32)


def orthonormal_basis_from_hint(primary: np.ndarray) -> np.ndarray:
    n0 = np.asarray(primary, dtype=np.float32)
    norm = float(np.linalg.norm(n0))
    if norm < 1e-6:
        n0 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    else:
        n0 = n0 / norm
    ref = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    if abs(float(np.dot(n0, ref))) > 0.95:
        ref = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    n1 = np.cross(ref, n0)
    n1_norm = float(np.linalg.norm(n1))
    if n1_norm < 1e-6:
        n1 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    else:
        n1 = n1 / n1_norm
    n2 = np.cross(n0, n1)
    n2 = n2 / max(float(np.linalg.norm(n2)), 1e-6)
    return np.vstack([n0, n1, n2]).astype(np.float32)


def cell_local_frame(cell: CellRecord) -> tuple[np.ndarray, float]:
    local_frame = cell.extras.get("local_frame", {}) if isinstance(cell.extras, dict) else {}
    n0 = np.asarray(local_frame.get("n0", [1.0, 0.0, 0.0]), dtype=np.float32)
    n1 = np.asarray(local_frame.get("n1", [0.0, 1.0, 0.0]), dtype=np.float32)
    n2 = np.asarray(local_frame.get("n2", [0.0, 0.0, 1.0]), dtype=np.float32)
    scale = float(local_frame.get("scale", cell.radius if cell.radius > 0.0 else 0.18))

    # Re-orthogonalize softly to avoid rendering broken local frames.
    n0 = orthonormal_basis_from_hint(n0)[0]
    n1 = n1 - np.dot(n1, n0) * n0
    n1_norm = float(np.linalg.norm(n1))
    if n1_norm < 1e-6:
        basis = orthonormal_basis_from_hint(n0)
        n1 = basis[1]
        n2 = basis[2]
    else:
        n1 = n1 / n1_norm
        n2 = np.cross(n0, n1)
        n2 = n2 / max(float(np.linalg.norm(n2)), 1e-6)
    return np.vstack([n0, n1, n2]).astype(np.float32), scale


def cell_dimension_generation_state(cell: CellRecord) -> tuple[object, float]:
    basis, scale = cell_local_frame(cell)
    extras = cell.extras if isinstance(cell.extras, dict) else {}
    mode_params = extras.get("dimension_generation", {}) if isinstance(extras.get("dimension_generation", {}), dict) else {}
    state = build_dimension_frame(
        basis,
        phase=float(cell.phase),
        sweep_gain=float(mode_params.get("sweep_gain", 0.9)),
        lift_gain=float(mode_params.get("lift_gain", 0.32)),
        torsion_phase=float(mode_params.get("torsion_phase", math.pi / 4.0)),
    )
    return state, scale


def orthonormal_basis_from_axes(primary: np.ndarray, secondary: np.ndarray) -> np.ndarray:
    n0 = np.asarray(primary, dtype=np.float32)
    n0_norm = float(np.linalg.norm(n0))
    if n0_norm < 1e-6:
        return orthonormal_basis_from_hint(np.array([1.0, 0.0, 0.0], dtype=np.float32))
    n0 = n0 / n0_norm
    n1 = np.asarray(secondary, dtype=np.float32) - float(np.dot(secondary, n0)) * n0
    n1_norm = float(np.linalg.norm(n1))
    if n1_norm < 1e-6:
        basis = orthonormal_basis_from_hint(n0)
        return basis
    n1 = n1 / n1_norm
    n2 = np.cross(n0, n1)
    n2 = n2 / max(float(np.linalg.norm(n2)), 1e-6)
    n1 = np.cross(n2, n0)
    n1 = n1 / max(float(np.linalg.norm(n1)), 1e-6)
    return np.vstack([n0, n1, n2]).astype(np.float32)


def build_triad_unit(cells: list[CellRecord], triad_id: str = "triad-0") -> dict[str, object] | None:
    if len(cells) != 3:
        return None

    states = []
    scales = []
    bases = []
    centers = []
    phases = []
    freqs = []
    amps = []
    radii = []
    for cell in cells:
        state, scale = cell_dimension_generation_state(cell)
        basis, _ = cell_local_frame(cell)
        states.append(state)
        scales.append(scale)
        bases.append(basis)
        centers.append(np.asarray(cell.center, dtype=np.float32))
        phases.append(float(cell.phase))
        freqs.append(float(cell.frequency))
        amps.append(float(cell.amplitude))
        radii.append(float(cell.radius if cell.radius > 0.0 else scale))

    closure_center, closure_radius, closure_source = minimum_closure_sphere(centers, radii)
    mean_phase, phase_coherence = circular_mean_phase(phases)
    primary_sum = np.sum([np.asarray(state.n0, dtype=np.float32) for state in states], axis=0)
    secondary_sum = np.sum([np.asarray(state.n1, dtype=np.float32) for state in states], axis=0)
    basis = orthonormal_basis_from_axes(primary_sum, secondary_sum)
    base_center = np.mean(np.asarray(centers, dtype=np.float32), axis=0)
    base_normal = _triangle_normal(np.asarray(centers, dtype=np.float64)).astype(np.float32)
    connector_height = max(0.45 * float(closure_radius), 0.35 * float(np.mean(radii)))
    if float(np.dot(base_normal, basis[2])) < 0.0:
        base_normal = -base_normal
    connector_position = base_center + connector_height * base_normal
    direction_coherence = 0.5 * (
        float(np.linalg.norm(primary_sum)) / 3.0 + float(np.linalg.norm(secondary_sum)) / 3.0
    )
    mean_scale = float(np.mean(scales))
    spread = float(np.mean([np.linalg.norm(point - closure_center) for point in centers]))
    spatial_coherence = 1.0 / (1.0 + spread / max(mean_scale * 4.0, 1e-6))
    coherence_score = 0.45 * phase_coherence + 0.35 * direction_coherence + 0.20 * spatial_coherence
    can_compose = bool(coherence_score >= 0.42)

    composite_radius = float(closure_radius)
    composite_frequency = float(np.mean(freqs))
    composite_amplitude = float(np.mean(amps)) * (0.9 + 0.2 * coherence_score)
    projection_cell = CellRecord(
        id="composite-cell",
        center=closure_center.tolist(),
        phase=mean_phase,
        frequency=composite_frequency,
        amplitude=composite_amplitude,
        radius=composite_radius,
        level=1,
        active=can_compose,
        extras={
            "local_frame": {
                "n0": basis[0].tolist(),
                "n1": basis[1].tolist(),
                "n2": basis[2].tolist(),
                "scale": composite_radius,
            },
            "composite_source_ids": [cell.id for cell in cells],
            "closure_sphere": {
                "center": closure_center.tolist(),
                "radius": composite_radius,
                "source": closure_source,
            },
            "connector": {
                "position": connector_position.tolist(),
                "base_center": base_center.tolist(),
                "base_normal": base_normal.tolist(),
                "height": float(connector_height),
            },
        },
    )
    triad_record = TriadRecord(
        id=triad_id,
        cell_ids=[cell.id for cell in cells],
        center=closure_center.tolist(),
        phase=mean_phase,
        closure_center=closure_center.tolist(),
        closure_radius=float(composite_radius),
        coherence_score=float(coherence_score),
        can_compose=can_compose,
        active=can_compose,
        extras={
            "phase_coherence": float(phase_coherence),
            "direction_coherence": float(direction_coherence),
            "spatial_coherence": float(spatial_coherence),
            "spread": float(spread),
            "closure_source": closure_source,
            "projection_cell": projection_cell.to_dict(),
        },
    )
    return {
        "triad": triad_record,
        "projection_cell": projection_cell,
        "can_compose": can_compose,
        "coherence_score": float(coherence_score),
        "phase_coherence": float(phase_coherence),
        "direction_coherence": float(direction_coherence),
        "spatial_coherence": float(spatial_coherence),
        "spread": float(spread),
        "closure_center": closure_center.tolist(),
        "closure_radius": float(composite_radius),
        "closure_source": closure_source,
        "connector_position": connector_position.tolist(),
        "connector_height": float(connector_height),
        "source_ids": [cell.id for cell in cells],
    }


def build_composite_cell(cells: list[CellRecord]) -> dict[str, object] | None:
    # Compatibility wrapper: the composite wave is now treated as a projection of a triad unit.
    return build_triad_unit(cells)


def resolve_frame_triads(frame: FrameState) -> list[TriadRecord]:
    if frame.triads:
        return list(frame.triads)
    if len(frame.cells) >= 3:
        triad_info = build_triad_unit(frame.cells[:3], triad_id="triad-0")
        if triad_info is not None:
            return [triad_info["triad"]]
    return []


def _validate_triad_node_positions(state: TriadCoreState) -> np.ndarray:
    raw_node_position = state.node_position
    try:
        base_points = np.asarray(raw_node_position, dtype=np.float32)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"TriadCoreState '{state.id}' has invalid node_position: "
            f"expected 3 node coordinates with 3 floats each, got {raw_node_position!r}"
        ) from exc
    if base_points.ndim != 2:
        raise ValueError(
            f"TriadCoreState '{state.id}' node_position must be a 2D array with shape (3, 3), "
            f"got ndim={base_points.ndim}, shape={base_points.shape}"
        )
    if base_points.shape != (3, 3):
        node_count = len(raw_node_position) if isinstance(raw_node_position, (list, tuple)) else "unknown"
        raise ValueError(
            f"TriadCoreState '{state.id}' node_position must have shape (3, 3), "
            f"got shape={base_points.shape}, node_count={node_count}, value={raw_node_position!r}"
        )
    if not np.isfinite(base_points).all():
        raise ValueError(
            f"TriadCoreState '{state.id}' node_position contains NaN or inf: {base_points.tolist()}"
        )
    return base_points


def analyze_pyramid_geometry(
    base_points: np.ndarray,
    apex: np.ndarray,
    *,
    triad_id: str,
) -> dict[str, object]:
    ab = base_points[1] - base_points[0]
    ac = base_points[2] - base_points[0]
    base_normal = np.cross(ab, ac)
    normal_norm = float(np.linalg.norm(base_normal))
    area = 0.5 * normal_norm
    centroid = np.mean(base_points, axis=0)
    height_vector = apex - centroid
    if normal_norm > 1e-8:
        normal_unit = base_normal / normal_norm
        signed_height = float(np.dot(height_vector, normal_unit))
    else:
        normal_unit = np.zeros(3, dtype=np.float32)
        signed_height = 0.0
    edge_lengths = [float(np.linalg.norm(apex - base_points[idx])) for idx in range(3)]
    min_edge_length = min(edge_lengths) if edge_lengths else 0.0
    issues: list[str] = []
    topology = "pyramid"
    if area < 1e-6:
        issues.append("degenerate_base")
        topology = "line_fan"
    if abs(signed_height) < 1e-5:
        issues.append("apex_coplanar")
        if topology == "pyramid":
            topology = "coplanar_fan"
    if min_edge_length < 1e-5:
        issues.append("collapsed_side_edge")
        if topology == "pyramid":
            topology = "collapsed_pyramid"
    if not np.isfinite(apex).all():
        issues.append("invalid_apex")
        topology = "invalid"
    return {
        "triad_id": triad_id,
        "topology": topology,
        "issues": issues,
        "base_area": float(area),
        "signed_height": float(signed_height),
        "min_side_edge_length": float(min_edge_length),
        "base_normal": normal_unit.astype(np.float32).tolist(),
        "centroid": centroid.astype(np.float32).tolist(),
        "has_common_apex": topology == "pyramid",
    }

def project_triad_core_state_to_pyramid(
    state: TriadCoreState,
    diagnostics: dict[str, object] | None = None,
) -> dict[str, object]:
    base_points = _validate_triad_node_positions(state)
    base_center = np.mean(base_points, axis=0).astype(np.float32)
    base_normal = _triangle_normal(base_points.astype(np.float64)).astype(np.float32)
    basis = orthonormal_basis_from_axes(
        base_points[1] - base_points[0],
        base_points[2] - base_points[0],
    ).astype(np.float32)
    if len(state.connector_position) == 3:
        apex = np.asarray(state.connector_position, dtype=np.float32)
    elif diagnostics is not None and len(diagnostics.get("connector_target_position", [])) == 3:
        apex = np.asarray(diagnostics["connector_target_position"], dtype=np.float32)
    else:
        apex = base_center + 0.1 * base_normal
    geometry = analyze_pyramid_geometry(base_points, apex, triad_id=state.id)
    closure_phase = float(state.connector_phase if abs(state.connector_phase) > 1e-8 else np.mean(state.node_phase))
    phase_shells, radial_shells = compute_closure_phase_shells(
        [float(value) for value in state.node_phase],
        base_points,
        closure_phase,
        base_center,
    )
    return {
        "id": state.id,
        "lineage_id": str(state.extras.get("lineage_id", state.id)),
        "source_cell_ids": [str(value) for value in state.extras.get("source_cell_ids", [f"{state.id}:node:{idx}" for idx in range(3)])],
        "base_points": base_points.astype(np.float32),
        "apex": apex.astype(np.float32),
        "base_center": base_center,
        "base_normal": np.asarray(geometry["base_normal"], dtype=np.float32),
        "basis": basis,
        "phase": float(np.mean(state.node_phase)),
        "closure_phase": closure_phase,
        "phase_shells": phase_shells,
        "radial_shells": radial_shells,
        "node_phases": [float(value) for value in state.node_phase],
        "node_freqs": [float(value) for value in state.node_freq],
        "node_amplitudes": [float(value) for value in state.node_duty],
        "connector_phase": float(state.connector_phase),
        "connector_freq": float(state.connector_freq),
        "connector_strength": float(state.connector_strength),
        "edge_complex": _triad_edge_complex(state),
        "geometry": geometry,
        "summary": {
            "can_compose": bool(geometry["topology"] == "pyramid"),
            "coherence_score": float(state.connector_strength),
            "phase_coherence": 0.0,
            "direction_coherence": 0.0,
            "spatial_coherence": 0.0,
            "spread": float(np.mean([np.linalg.norm(point - base_center) for point in base_points])),
            "closure_center": base_center.astype(np.float32).tolist(),
            "closure_radius": float(max(np.linalg.norm(point - base_center) for point in base_points)),
            "closure_source": geometry["topology"],
            "closure_phase": closure_phase,
            "phase_shells": list(phase_shells),
            "radial_shells": list(radial_shells),
            "connector_position": apex.astype(np.float32).tolist(),
            "topology": geometry["topology"],
            "topology_issues": list(geometry["issues"]),
            "has_common_apex": bool(geometry["has_common_apex"]),
        },
        "source": "triad_core_state",
    }


def project_triad_record_to_pyramid(
    triad: TriadRecord,
    cell_lookup: dict[str, CellRecord],
) -> dict[str, object] | None:
    cells = [cell_lookup.get(cell_id) for cell_id in triad.cell_ids]
    if any(cell is None for cell in cells):
        return None
    base_points = np.asarray([cell.center for cell in cells if cell is not None], dtype=np.float32)
    if base_points.shape != (3, 3):
        return None
    projection = triad.extras.get("projection_cell", {}) if isinstance(triad.extras, dict) else {}
    projection_extras = projection.get("extras", {}) if isinstance(projection, dict) else {}
    connector = projection_extras.get("connector", {}) if isinstance(projection_extras, dict) else {}
    base_center = np.mean(base_points, axis=0).astype(np.float32)
    basis = orthonormal_basis_from_axes(
        base_points[1] - base_points[0],
        base_points[2] - base_points[0],
    ).astype(np.float32)
    if len(connector.get("position", [])) == 3:
        apex = np.asarray(connector["position"], dtype=np.float32)
    else:
        height = float(connector.get("height", max(0.45 * float(triad.closure_radius), 0.12)))
        base_normal = _triangle_normal(base_points.astype(np.float64)).astype(np.float32)
        apex = base_center + height * base_normal
    geometry = analyze_pyramid_geometry(base_points, apex, triad_id=triad.id)
    node_phases = [float(cell.phase) for cell in cells if cell is not None]
    closure_phase = float(triad.phase if abs(triad.phase) > 1e-8 else np.mean(node_phases))
    phase_shells, radial_shells = compute_closure_phase_shells(
        node_phases,
        base_points,
        closure_phase,
        base_center,
    )
    summary = {
        "can_compose": bool(triad.can_compose),
        "coherence_score": float(triad.coherence_score),
        "phase_coherence": float(triad.extras.get("phase_coherence", 0.0)) if isinstance(triad.extras, dict) else 0.0,
        "direction_coherence": float(triad.extras.get("direction_coherence", 0.0)) if isinstance(triad.extras, dict) else 0.0,
        "spatial_coherence": float(triad.extras.get("spatial_coherence", 0.0)) if isinstance(triad.extras, dict) else 0.0,
        "spread": float(triad.extras.get("spread", 0.0)) if isinstance(triad.extras, dict) else 0.0,
        "closure_center": list(triad.closure_center),
        "closure_radius": float(triad.closure_radius),
        "closure_source": triad.extras.get("closure_source", geometry["topology"]) if isinstance(triad.extras, dict) else geometry["topology"],
        "closure_phase": closure_phase,
        "phase_shells": list(phase_shells),
        "radial_shells": list(radial_shells),
        "connector_position": apex.astype(np.float32).tolist(),
        "topology": geometry["topology"],
        "topology_issues": list(geometry["issues"]),
        "has_common_apex": bool(geometry["has_common_apex"]),
    }
    return {
        "id": triad.id,
        "lineage_id": str(triad.extras.get("lineage_id", triad.id)) if isinstance(triad.extras, dict) else triad.id,
        "source_cell_ids": [str(cell.id) for cell in cells if cell is not None],
        "base_points": base_points.astype(np.float32),
        "apex": apex.astype(np.float32),
        "base_center": base_center,
        "base_normal": np.asarray(geometry["base_normal"], dtype=np.float32),
        "basis": basis,
        "phase": float(triad.phase),
        "closure_phase": closure_phase,
        "phase_shells": phase_shells,
        "radial_shells": radial_shells,
        "node_phases": node_phases,
        "node_freqs": [float(cell.frequency) for cell in cells if cell is not None],
        "node_amplitudes": [float(cell.amplitude) for cell in cells if cell is not None],
        "connector_phase": float(triad.phase),
        "connector_freq": 0.0,
        "connector_strength": float(triad.coherence_score),
        "edge_complex": None,
        "geometry": geometry,
        "summary": summary,
        "source": "triad_record",
    }


def build_frame_pyramid_units(
    frame: FrameState,
    triads: list[TriadRecord] | None = None,
    triad_core_states: dict[str, TriadCoreState] | None = None,
    triad_diagnostics: dict[str, dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    triad_items = triads if triads is not None else resolve_frame_triads(frame)
    state_map = triad_core_states or {}
    diagnostics_map = triad_diagnostics or {}
    cell_lookup = {cell.id: cell for cell in frame.cells}
    units: list[dict[str, object]] = []
    for triad in triad_items:
        unit: dict[str, object] | None
        state = state_map.get(triad.id)
        if state is not None:
            try:
                unit = project_triad_core_state_to_pyramid(state, diagnostics=diagnostics_map.get(triad.id))
            except ValueError:
                unit = None
        else:
            unit = project_triad_record_to_pyramid(triad, cell_lookup)
        if unit is not None:
            split_cells = build_split_cells_from_pyramid(unit)
            unit["split_cells"] = split_cells
            if "summary" in unit and isinstance(unit["summary"], dict):
                unit["summary"]["split_required"] = bool(split_cells)
                unit["summary"]["split_count"] = len(split_cells)
            units.append(unit)
    return units


def build_pyramid_edge_segments(
    pyramid: dict[str, object],
    *,
    selected: bool = False,
) -> list[tuple[str, np.ndarray, tuple[float, float, float, float], float]]:
    base_points = np.asarray(pyramid["base_points"], dtype=np.float32)
    apex = np.asarray(pyramid["apex"], dtype=np.float32)
    alpha = 0.92 if selected else 0.50
    thickness = 2.8 if selected else 1.6
    connector_phase = float(pyramid["connector_phase"])
    edge_complex = pyramid.get("edge_complex")
    segments: list[tuple[str, np.ndarray, tuple[float, float, float, float], float]] = []
    for edge_idx, (i, j) in enumerate(TRIAD_EDGE_PAIRS):
        segment = np.vstack([base_points[i], base_points[j]]).astype(np.float32)
        if edge_complex is not None:
            edge_phase = float(np.angle(edge_complex[edge_idx]))
        else:
            edge_phase = float(pyramid["phase"])
        segments.append((f"base:{edge_idx}", segment, phase_band_color(edge_phase, alpha=alpha), thickness))
    for node_idx in range(3):
        segment = np.vstack([base_points[node_idx], apex]).astype(np.float32)
        segments.append(
            (
                f"side:{node_idx}",
                segment,
                phase_band_color(connector_phase, alpha=min(1.0, alpha + 0.06)),
                thickness + 0.2,
            )
        )
    return segments


def build_pyramid_face_segments(
    pyramid: dict[str, object],
    *,
    selected: bool = False,
) -> list[tuple[str, np.ndarray, tuple[float, float, float, float], float]]:
    base_points = np.asarray(pyramid["base_points"], dtype=np.float32)
    apex = np.asarray(pyramid["apex"], dtype=np.float32)
    alpha = 0.34 if selected else 0.20
    thickness = 2.0 if selected else 1.1
    phase = float(pyramid["phase"])
    connector_phase = float(pyramid["connector_phase"])
    face_specs = [
        ("base", [base_points[0], base_points[1], base_points[2], base_points[0]], phase),
        ("side:0", [base_points[0], base_points[1], apex, base_points[0]], connector_phase),
        ("side:1", [base_points[1], base_points[2], apex, base_points[1]], connector_phase),
        ("side:2", [base_points[2], base_points[0], apex, base_points[2]], connector_phase),
    ]
    return [
        (
            face_id,
            np.asarray(points, dtype=np.float32),
            phase_band_color(face_phase, alpha=alpha),
            thickness,
        )
        for face_id, points, face_phase in face_specs
    ]


def build_split_cells_from_pyramid(pyramid: dict[str, object]) -> list[CellRecord]:
    geometry = pyramid.get("geometry", {})
    if bool(geometry.get("has_common_apex", True)):
        return []

    base_points = np.asarray(pyramid["base_points"], dtype=np.float32)
    apex = np.asarray(pyramid["apex"], dtype=np.float32)
    base_center = np.asarray(pyramid["base_center"], dtype=np.float32)
    base_normal = np.asarray(pyramid["base_normal"], dtype=np.float32)
    basis = np.asarray(pyramid["basis"], dtype=np.float32)
    node_phases = list(pyramid.get("node_phases", [float(pyramid["phase"])] * 3))
    node_freqs = list(pyramid.get("node_freqs", [float(pyramid["connector_freq"])] * 3))
    node_amplitudes = list(pyramid.get("node_amplitudes", [float(pyramid["connector_strength"])] * 3))

    split_direction = apex - base_center
    split_norm = float(np.linalg.norm(split_direction))
    if split_norm < 1e-6:
        split_direction = base_normal
        split_norm = float(np.linalg.norm(split_direction))
    if split_norm < 1e-6:
        split_direction = basis[2]
        split_norm = max(float(np.linalg.norm(split_direction)), 1e-6)
    split_direction = split_direction / split_norm

    base_radius = float(np.mean([np.linalg.norm(point - base_center) for point in base_points]))
    split_offset = max(0.16, 0.35 * base_radius)
    daughter_radius = max(0.08, 0.58 * max(base_radius, 0.12))

    split_cells: list[CellRecord] = []
    for idx in range(3):
        point = base_points[idx]
        radial = point - base_center
        daughter_center = point + split_offset * split_direction + 0.22 * radial
        local_basis = orthonormal_basis_from_axes(
            radial if float(np.linalg.norm(radial)) > 1e-6 else basis[0],
            split_direction,
        ).astype(np.float32)
        split_cells.append(
            CellRecord(
                id=f"{pyramid['id']}:split:{idx}",
                center=daughter_center.astype(np.float32).tolist(),
                phase=float(node_phases[idx]),
                frequency=float(node_freqs[idx]),
                amplitude=float(node_amplitudes[idx]),
                radius=float(daughter_radius),
                level=1,
                parent_id=str(pyramid["id"]),
                active=True,
                extras={
                    "local_frame": {
                        "n0": local_basis[0].tolist(),
                        "n1": local_basis[1].tolist(),
                        "n2": local_basis[2].tolist(),
                        "scale": float(daughter_radius),
                    },
                    "split_origin": {
                        "triad_id": str(pyramid["id"]),
                        "node_index": idx,
                        "node_position": point.astype(np.float32).tolist(),
                        "lineage_id": str(pyramid.get("lineage_id", pyramid["id"])),
                        "closure_phase": float(pyramid.get("closure_phase", pyramid["phase"])),
                        "phase_shell": float(pyramid.get("phase_shells", [0.0, 0.0, 0.0])[idx]),
                        "radial_shell": float(pyramid.get("radial_shells", [0.0, 0.0, 0.0])[idx]),
                        "connector_phase": float(pyramid["connector_phase"]),
                        "connector_freq": float(pyramid["connector_freq"]),
                        "connector_strength": float(pyramid["connector_strength"]),
                        "topology": geometry.get("topology", "unknown"),
                        "topology_issues": list(geometry.get("issues", [])),
                    },
                },
            )
        )
    return split_cells


def build_pyramid_field_sources(pyramid_units: list[dict[str, object]]) -> list[dict[str, object]]:
    sources: list[dict[str, object]] = []
    for pyramid in pyramid_units:
        split_cells = list(pyramid.get("active_split_cells", pyramid.get("split_cells", [])))
        if split_cells:
            for cell in split_cells:
                state, _ = cell_dimension_generation_state(cell)
                dynamic_basis = np.vstack(
                    [
                        np.asarray(state.n0, dtype=np.float32),
                        np.asarray(state.n1, dtype=np.float32),
                        np.asarray(state.n2, dtype=np.float32),
                    ]
                ).astype(np.float32)
                sources.append(
                    {
                        "center": np.asarray(cell.center, dtype=np.float32),
                        "dynamic_basis": dynamic_basis,
                        "phase": float(cell.phase),
                        "state": state,
                    }
                )
            continue
        basis = np.asarray(pyramid["basis"], dtype=np.float32)
        phase = float(pyramid["phase"])
        connector_phase = float(pyramid["connector_phase"])
        base_state = build_dimension_frame(basis, phase)
        sources.append(
            {
                "center": np.asarray(pyramid["base_center"], dtype=np.float32),
                "dynamic_basis": basis,
                "phase": phase,
                "state": base_state,
            }
        )
        apex_basis = np.vstack([basis[2], basis[0], basis[1]]).astype(np.float32)
        apex_state = build_dimension_frame(apex_basis, connector_phase)
        sources.append(
            {
                "center": np.asarray(pyramid["apex"], dtype=np.float32),
                "dynamic_basis": apex_basis,
                "phase": connector_phase,
                "state": apex_state,
            }
        )
    return sources


def build_dimension_history(
    frames: List[FrameState],
    current_index: int,
    cell_id: str,
    history_size: int = 72,
) -> list[dict[str, object]]:
    if not frames:
        return []
    start_index = max(0, current_index - history_size + 1)
    history: list[dict[str, object]] = []
    for frame in frames[start_index : current_index + 1]:
        cell = next((item for item in frame.cells if item.id == cell_id), None)
        if cell is None:
            continue
        state, scale = cell_dimension_generation_state(cell)
        history.append(
            {
                "frame_index": frame.frame_index,
                "time": frame.time,
                "center": np.asarray(cell.center, dtype=np.float32),
                "state": state,
                "scale": float(scale),
            }
        )
    return history


def build_wave_shell_history(
    frames: List[FrameState],
    current_index: int,
    cell_id: str,
    history_size: int = 5,
) -> list[dict[str, object]]:
    if not frames:
        return []
    start_index = max(0, current_index - history_size + 1)
    history: list[dict[str, object]] = []
    for frame in frames[start_index : current_index + 1]:
        cell = next((item for item in frame.cells if item.id == cell_id), None)
        if cell is None:
            continue
        basis, scale = cell_local_frame(cell)
        state, _ = cell_dimension_generation_state(cell)
        dynamic_basis = np.vstack(
            [
                np.asarray(state.n0, dtype=np.float32),
                np.asarray(state.n1, dtype=np.float32),
                np.asarray(state.n2, dtype=np.float32),
            ]
        ).astype(np.float32)
        history.append(
            {
                "cell_id": cell.id,
                "center": np.asarray(cell.center, dtype=np.float32),
                "basis": basis,
                "dynamic_basis": dynamic_basis,
                "scale": float(scale),
                "phase": float(cell.phase),
                "state": state,
            }
        )
    return history


def build_slice_grid_history(
    frames: List[FrameState],
    current_index: int,
    cell_ids: list[str],
    history_size: int = 5,
) -> list[dict[str, object]]:
    if not frames:
        return []
    start_index = max(0, current_index - history_size + 1)
    history: list[dict[str, object]] = []
    visible_ids = {cell_id for cell_id in cell_ids if cell_id}
    for frame in frames[start_index : current_index + 1]:
        cell_entries = []
        for cell in frame.cells:
            if visible_ids and cell.id not in visible_ids:
                continue
            state, _ = cell_dimension_generation_state(cell)
            dynamic_basis = np.vstack(
                [
                    np.asarray(state.n0, dtype=np.float32),
                    np.asarray(state.n1, dtype=np.float32),
                    np.asarray(state.n2, dtype=np.float32),
                ]
            ).astype(np.float32)
            cell_entries.append(
                {
                    "cell_id": cell.id,
                    "center": np.asarray(cell.center, dtype=np.float32),
                    "dynamic_basis": dynamic_basis,
                    "phase": float(cell.phase),
                    "state": state,
                }
            )
        if cell_entries:
            history.append({"cells": cell_entries})
    return history


def lerp_color(color_a: tuple[float, float, float, float], color_b: tuple[float, float, float, float], t: float) -> tuple[float, float, float, float]:
    ratio = float(np.clip(t, 0.0, 1.0))
    return tuple((1.0 - ratio) * a + ratio * b for a, b in zip(color_a, color_b))


def dimension_state_color(state: object) -> tuple[float, float, float, float]:
    n1_strength = float(getattr(state, "n1_strength"))
    n2_strength = float(getattr(state, "n2_strength"))
    if n1_strength < 0.25:
        return lerp_color(DIMENSION_STAGE_RGB["seed"], DIMENSION_STAGE_RGB["planar"], n1_strength / 0.25)
    if n2_strength < 0.25:
        return lerp_color(DIMENSION_STAGE_RGB["planar"], DIMENSION_STAGE_RGB["lift"], n2_strength / 0.25)
    if n2_strength < 0.65:
        return lerp_color(DIMENSION_STAGE_RGB["lift"], DIMENSION_STAGE_RGB["closure"], (n2_strength - 0.25) / 0.40)
    return DIMENSION_STAGE_RGB["closure"]


def sphere_ring_points(
    center: np.ndarray,
    basis: np.ndarray,
    radius: float,
    mode: str,
    parameter: float,
    sample_count: int = 72,
) -> np.ndarray:
    center = np.asarray(center, dtype=np.float32)
    basis = np.asarray(basis, dtype=np.float32)
    theta_values = np.linspace(0.0, 2.0 * math.pi, sample_count, endpoint=True, dtype=np.float32)
    points = []
    if mode == "latitude":
        z = math.sin(parameter)
        ring_radius = math.cos(parameter)
        for theta in theta_values:
            direction = (
                ring_radius * math.cos(float(theta)) * basis[0]
                + ring_radius * math.sin(float(theta)) * basis[1]
                + z * basis[2]
            )
            points.append(center + float(radius) * direction)
    else:
        for theta in theta_values:
            direction = (
                math.cos(float(theta)) * math.cos(parameter) * basis[0]
                + math.cos(float(theta)) * math.sin(parameter) * basis[1]
                + math.sin(float(theta)) * basis[2]
            )
            points.append(center + float(radius) * direction)
    return np.asarray(points, dtype=np.float32)


def phase_band_color(local_phase: float, alpha: float = 1.0) -> tuple[float, float, float, float]:
    return (
        0.30 + 0.70 * (0.5 + 0.5 * math.sin(local_phase)),
        0.25 + 0.75 * (0.5 + 0.5 * math.sin(local_phase + 2.0 * math.pi / 3.0)),
        0.30 + 0.70 * (0.5 + 0.5 * math.sin(local_phase + 4.0 * math.pi / 3.0)),
        alpha,
    )


def distorted_shell_sample(
    center: np.ndarray,
    basis: np.ndarray,
    radius: float,
    theta: float,
    phi: float,
    phase: float,
    state: object,
) -> tuple[np.ndarray, float]:
    basis = np.asarray(basis, dtype=np.float32)
    center = np.asarray(center, dtype=np.float32)
    n1_strength = float(getattr(state, "n1_strength"))
    n2_strength = float(getattr(state, "n2_strength"))
    phase_value = float(phase)

    theta_twisted = float(theta) + 0.28 * n1_strength * math.sin(float(phi) + phase_value)
    phi_twisted = float(phi) + 0.22 * n2_strength * math.cos(2.0 * float(theta) - phase_value)
    direction = (
        math.cos(theta_twisted) * math.cos(phi_twisted) * basis[0]
        + math.sin(theta_twisted) * math.cos(phi_twisted) * basis[1]
        + math.sin(phi_twisted) * basis[2]
    )
    direction = direction / max(float(np.linalg.norm(direction)), 1e-6)
    radial_gain = distorted_shell_radial_gain(theta_twisted, phi_twisted, phase_value, state)
    point = center + float(radius) * float(radial_gain) * direction
    local_phase = (
        phase_value
        + 2.0 * theta_twisted
        + 3.0 * phi_twisted
        + 1.5 * n2_strength * math.sin(theta_twisted - phi_twisted)
    )
    return point.astype(np.float32), float(local_phase)


def distorted_shell_radial_gain(theta_twisted: float, phi_twisted: float, phase_value: float, state: object) -> float:
    n1_strength = float(getattr(state, "n1_strength"))
    n2_strength = float(getattr(state, "n2_strength"))
    return (
        1.0
        + 0.10 * math.sin(2.0 * theta_twisted - phase_value)
        + 0.08 * n1_strength * math.cos(3.0 * phi_twisted + 0.7 * phase_value)
        + 0.12 * n2_strength * math.sin(theta_twisted + phi_twisted + 1.3 * phase_value)
    )


def shell_layer_radii(
    base_radius: float,
    phase: float,
    state: object,
    layer_count: int = 3,
    baseline_amplitude: float = 0.12,
    base_gap_ratio: float = 0.22,
    amplitude_gap_gain: float = 1.75,
) -> list[float]:
    theta_values = np.linspace(0.0, 2.0 * math.pi, 12, endpoint=False, dtype=np.float32)
    phi_values = np.linspace(-0.75 * math.pi / 2.0, 0.75 * math.pi / 2.0, 6, dtype=np.float32)
    max_amplitude = 0.0
    phase_value = float(phase)
    n1_strength = float(getattr(state, "n1_strength"))
    n2_strength = float(getattr(state, "n2_strength"))
    for theta in theta_values:
        for phi in phi_values:
            theta_twisted = float(theta) + 0.28 * n1_strength * math.sin(float(phi) + phase_value)
            phi_twisted = float(phi) + 0.22 * n2_strength * math.cos(2.0 * float(theta) - phase_value)
            radial_gain = distorted_shell_radial_gain(theta_twisted, phi_twisted, phase_value, state)
            max_amplitude = max(max_amplitude, abs(float(radial_gain) - 1.0))
    extra_ratio = 0.0
    if max_amplitude > baseline_amplitude:
        extra_ratio = amplitude_gap_gain * ((max_amplitude - baseline_amplitude) / max(baseline_amplitude, 1e-6))
    gap_ratio = base_gap_ratio * (1.0 + extra_ratio)
    return [float(base_radius) * (1.0 + gap_ratio * layer_idx) for layer_idx in range(layer_count)]


def distorted_shell_ring_segments(
    center: np.ndarray,
    basis: np.ndarray,
    radius: float,
    mode: str,
    parameter: float,
    phase: float,
    state: object,
    sample_count: int = 56,
) -> list[tuple[np.ndarray, float]]:
    segments: list[tuple[np.ndarray, float]] = []
    if mode == "latitude":
        theta_values = np.linspace(0.0, 2.0 * math.pi, sample_count, endpoint=True, dtype=np.float32)
        samples = [
            distorted_shell_sample(center, basis, radius, float(theta), float(parameter), phase, state)
            for theta in theta_values
        ]
    else:
        phi_values = np.linspace(-math.pi, math.pi, sample_count, endpoint=True, dtype=np.float32)
        samples = [
            distorted_shell_sample(center, basis, radius, float(parameter), float(phi), phase, state)
            for phi in phi_values
        ]
    for idx in range(len(samples) - 1):
        p0, phase0 = samples[idx]
        p1, phase1 = samples[idx + 1]
        segment = np.vstack([p0, p1]).astype(np.float32)
        segments.append((segment, 0.5 * (phase0 + phase1)))
    return segments


def build_shell_network_segments(
    center: np.ndarray,
    basis: np.ndarray,
    radius: float,
    phase: float,
    state: object,
    theta_count: int = 10,
    phi_count: int = 6,
) -> list[tuple[np.ndarray, float]]:
    theta_values = np.linspace(0.0, 2.0 * math.pi, theta_count, endpoint=False, dtype=np.float32)
    phi_values = np.linspace(-0.75 * math.pi / 2.0, 0.75 * math.pi / 2.0, phi_count, dtype=np.float32)
    points: list[list[tuple[np.ndarray, float]]] = []
    for phi in phi_values:
        row: list[tuple[np.ndarray, float]] = []
        for theta in theta_values:
            row.append(distorted_shell_sample(center, basis, radius, float(theta), float(phi), phase, state))
        points.append(row)

    segments: list[tuple[np.ndarray, float]] = []
    for phi_idx, row in enumerate(points):
        for theta_idx in range(len(row)):
            p0, phase0 = row[theta_idx]
            p1, phase1 = row[(theta_idx + 1) % len(row)]
            segments.append((np.vstack([p0, p1]).astype(np.float32), 0.5 * (phase0 + phase1)))
            if phi_idx + 1 < len(points):
                p2, phase2 = points[phi_idx + 1][theta_idx]
                segments.append((np.vstack([p0, p2]).astype(np.float32), 0.5 * (phase0 + phase2)))
    return segments


def strain_band_color(strain_value: float, alpha: float = 1.0) -> tuple[float, float, float, float]:
    value = float(np.clip(strain_value, 0.0, 1.0))
    if value < 0.5:
        local = value / 0.5
        return (
            0.15 + 0.35 * local,
            0.45 + 0.45 * local,
            1.0 - 0.45 * local,
            alpha,
        )
    local = (value - 0.5) / 0.5
    return (
        0.50 + 0.50 * local,
        0.90 - 0.55 * local,
        0.55 - 0.45 * local,
        alpha,
    )


def space_grid_displacement(
    point: np.ndarray,
    center: np.ndarray,
    basis: np.ndarray,
    phase: float,
    state: object,
) -> tuple[np.ndarray, float, float]:
    point = np.asarray(point, dtype=np.float32)
    center = np.asarray(center, dtype=np.float32)
    basis = np.asarray(basis, dtype=np.float32)
    rel = point - center
    coord0 = float(np.dot(rel, basis[0]))
    coord1 = float(np.dot(rel, basis[1]))
    coord2 = float(np.dot(rel, basis[2]))
    n1_strength = float(getattr(state, "n1_strength"))
    n2_strength = float(getattr(state, "n2_strength"))
    phase_value = float(phase)

    disp0 = 0.18 * math.sin(1.35 * coord0 - 1.2 * phase_value)
    disp1 = 0.14 * n1_strength * math.sin(1.8 * coord1 + 0.8 * coord0 - phase_value)
    disp2 = 0.16 * n2_strength * math.cos(1.7 * coord2 - 0.9 * phase_value + 0.5 * coord1)
    displacement = disp0 * basis[0] + disp1 * basis[1] + disp2 * basis[2]

    local_phase = phase_value + 1.6 * coord0 + 1.2 * coord1 + 1.4 * coord2
    strain = min(1.0, float(np.linalg.norm(displacement)) / 0.32)
    return (point + displacement).astype(np.float32), float(local_phase), strain


def slice_plane_point(plane: str, u: float, v: float) -> np.ndarray:
    if plane == "XY":
        return np.array([u, v, 0.0], dtype=np.float32)
    if plane == "XZ":
        return np.array([u, 0.0, v], dtype=np.float32)
    return np.array([0.0, u, v], dtype=np.float32)


def build_slice_grid_segments(
    plane: str,
    center: np.ndarray,
    basis: np.ndarray,
    phase: float,
    state: object,
    span: float = 3.2,
    line_count: int = 7,
    sample_count: int = 24,
) -> list[tuple[np.ndarray, float, float]]:
    segments: list[tuple[np.ndarray, float, float]] = []
    fixed_values = np.linspace(-span, span, line_count, dtype=np.float32)
    varying_values = np.linspace(-span, span, sample_count, dtype=np.float32)

    def add_line(points: list[np.ndarray], phases: list[float], strains: list[float]) -> None:
        for idx in range(len(points) - 1):
            segment = np.vstack([points[idx], points[idx + 1]]).astype(np.float32)
            segments.append((segment, 0.5 * (phases[idx] + phases[idx + 1]), 0.5 * (strains[idx] + strains[idx + 1])))

    for fixed in fixed_values:
        line_points = []
        line_phases = []
        line_strains = []
        for value in varying_values:
            if plane == "XY":
                point = slice_plane_point(plane, float(fixed), float(value))
            elif plane == "XZ":
                point = slice_plane_point(plane, float(fixed), float(value))
            else:
                point = slice_plane_point(plane, float(fixed), float(value))
            displaced, local_phase, strain = space_grid_displacement(point, center, basis, phase, state)
            line_points.append(displaced)
            line_phases.append(local_phase)
            line_strains.append(strain)
        add_line(line_points, line_phases, line_strains)

    for fixed in fixed_values:
        line_points = []
        line_phases = []
        line_strains = []
        for value in varying_values:
            if plane == "XY":
                point = slice_plane_point(plane, float(value), float(fixed))
            elif plane == "XZ":
                point = slice_plane_point(plane, float(value), float(fixed))
            else:
                point = slice_plane_point(plane, float(value), float(fixed))
            displaced, local_phase, strain = space_grid_displacement(point, center, basis, phase, state)
            line_points.append(displaced)
            line_phases.append(local_phase)
            line_strains.append(strain)
        add_line(line_points, line_phases, line_strains)
    return segments


def build_space_point_cloud(
    cell_entries: list[dict[str, object]],
    color_mode: str,
    span: float = 3.2,
    samples_per_axis: int = 7,
) -> tuple[np.ndarray, np.ndarray]:
    if not cell_entries:
        return np.zeros((0, 3), dtype=np.float32), np.zeros((0, 4), dtype=np.float32)
    axis_values = np.linspace(-span, span, samples_per_axis, dtype=np.float32)
    base_points: list[np.ndarray] = []
    seen_points: set[tuple[int, int, int]] = set()
    positions: list[np.ndarray] = []
    colors: list[tuple[float, float, float, float]] = []

    def append_point(point: np.ndarray) -> None:
        key = tuple(int(round(float(value) * 1000.0)) for value in point)
        if key in seen_points:
            return
        seen_points.add(key)
        base_points.append(np.asarray(point, dtype=np.float32))

    for x in axis_values:
        for y in axis_values:
            for z in axis_values:
                append_point(np.array([x, y, z], dtype=np.float32))

    # Add a denser local cloud around each cell. The denser region follows the cell motion:
    # higher tangential speed / stronger n1-n2 excitation => higher local point density.
    for item in cell_entries:
        center = np.asarray(item["center"], dtype=np.float32)
        state = item["state"]
        tangential_speed = float(getattr(state, "tangential_speed", 0.0))
        n1_strength = float(getattr(state, "n1_strength", 0.0))
        n2_strength = float(getattr(state, "n2_strength", 0.0))
        motion_score = float(
            np.clip(
                0.55 * min(1.0, tangential_speed / 0.55)
                + 0.20 * n1_strength
                + 0.25 * n2_strength,
                0.0,
                1.0,
            )
        )

        local_span = 0.72 + 0.55 * motion_score
        local_samples = 5 if motion_score < 0.28 else 7 if motion_score < 0.62 else 9
        local_values = np.linspace(-local_span, local_span, local_samples, dtype=np.float32)
        for dx in local_values:
            for dy in local_values:
                for dz in local_values:
                    offset = np.array([dx, dy, dz], dtype=np.float32)
                    radius = float(np.linalg.norm(offset))
                    if radius > local_span:
                        continue
                    # Keep low-motion regions sparse by only retaining the core neighborhood.
                    if motion_score < 0.28 and radius > 0.58 * local_span:
                        continue
                    point = center + offset
                    if np.max(np.abs(point)) > span:
                        continue
                    append_point(point.astype(np.float32))

    for base_point in base_points:
        accum_disp = np.zeros(3, dtype=np.float32)
        accum_phase = 0.0
        accum_strain = 0.0
        total_weight = 0.0
        for item in cell_entries:
            center = np.asarray(item["center"], dtype=np.float32)
            basis = np.asarray(item["dynamic_basis"], dtype=np.float32)
            phase = float(item["phase"])
            state = item["state"]
            displaced, local_phase, strain = space_grid_displacement(base_point, center, basis, phase, state)
            displacement = displaced - base_point
            distance = float(np.linalg.norm(base_point - center))
            weight = 1.0 / (1.0 + 0.35 * distance * distance)
            accum_disp += weight * displacement
            accum_phase += weight * local_phase
            accum_strain += weight * strain
            total_weight += weight
        if total_weight <= 1e-6:
            total_weight = 1.0
        final_point = base_point + accum_disp / total_weight
        final_phase = accum_phase / total_weight
        final_strain = min(1.0, accum_strain / total_weight)
        positions.append(final_point.astype(np.float32))
        if color_mode == "strain":
            colors.append(strain_band_color(final_strain, alpha=0.68))
        else:
            colors.append(phase_band_color(final_phase, alpha=0.68))
    return np.asarray(positions, dtype=np.float32), np.asarray(colors, dtype=np.float32)


class Viewer3D(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.canvas = _WgpuCanvas()
        layout.addWidget(self.canvas)

        self.renderer = gfx.renderers.WgpuRenderer(
            self.canvas,
            pixel_ratio=1.0,
            pixel_filter="linear",
            show_fps=False,
            sort_objects=True,
        )
        self.scene = gfx.Scene()
        self.scene.add(gfx.Background(None, gfx.BackgroundMaterial((0.05, 0.07, 0.12))))

        self.camera = gfx.PerspectiveCamera(55, 16 / 9)
        self.camera.local.position = (0.0, 0.0, 6.5)
        self.camera.show_pos((0.0, 0.0, 0.0), up=(0.0, 1.0, 0.0), depth=6.5)
        self.controller = gfx.OrbitController(self.camera, register_events=self.renderer)

        self.scene.add(gfx.AxesHelper(size=1.4))
        self.scene.add(gfx.GridHelper(size=10.0, divisions=10, color1=(0.25, 0.28, 0.35, 1.0), color2=(0.15, 0.18, 0.22, 1.0)))

        self.cell_positions = gfx.Buffer(np.zeros((1, 3), dtype=np.float32))
        self.cell_geometry = gfx.Geometry(positions=self.cell_positions)
        # pygfx 0.16 uses SizeMode {uniform, vertex}. "uniform" is good enough for the prototype.
        self.cell_material = gfx.PointsMaterial(color=(0.95, 0.6, 0.2, 1.0), size=0.06, size_mode="uniform")
        self.cell_points = gfx.Points(self.cell_geometry, self.cell_material)
        self.scene.add(self.cell_points)

        self.space_field_positions = gfx.Buffer(np.zeros((1, 3), dtype=np.float32))
        self.space_field_colors = gfx.Buffer(np.zeros((1, 4), dtype=np.float32))
        self.space_field_geometry = gfx.Geometry(positions=self.space_field_positions, colors=self.space_field_colors)
        self.space_field_material = gfx.PointsMaterial(
            size=0.035,
            size_mode="uniform",
            color_mode="vertex",
            aa=False,
        )
        self.space_field_points = gfx.Points(self.space_field_geometry, self.space_field_material)
        self.scene.add(self.space_field_points)

        self.axis_objects: Dict[str, gfx.Line] = {}
        self.cell_axis_objects: Dict[str, gfx.Line] = {}
        self.dimension_axis_objects: Dict[str, gfx.Line] = {}
        self.pyramid_edge_objects: Dict[str, gfx.Line] = {}
        self.pyramid_face_objects: Dict[str, gfx.Line] = {}
        self.pyramid_axis_objects: Dict[str, gfx.Line] = {}
        self.dimension_shell_objects: Dict[str, gfx.Line] = {}
        self.dimension_shell_network_objects: Dict[str, gfx.Line] = {}
        self.closure_sphere_objects: Dict[str, gfx.Line] = {}
        self.dimension_plane_objects: Dict[str, gfx.Line] = {}
        self.dimension_traj_objects: Dict[str, gfx.Line] = {}
        self.dimension_stage_marker_objects: Dict[str, gfx.Points] = {}
        self.dimension_stage_label_objects: Dict[str, gfx.Text] = {}
        self.dimension_slice_objects: Dict[str, gfx.Line] = {}
        self.dimension_slice_trail_objects: Dict[str, gfx.Line] = {}
        self.dimension_shell_trail_objects: Dict[str, gfx.Line] = {}
        self.dimension_mode_enabled = False
        self.selected_cell_id: str | None = None
        self.selected_triad_id: str | None = None
        self.visible_shell_cell_ids: set[str] = set()
        self.visible_slice_planes: set[str] = set(SLICE_PLANES)
        self.slice_color_mode = "phase"
        self.wave_shell_trails_enabled = False
        self.slice_grid_trails_enabled = False
        self.shell_network_enabled = True
        self.shell_layer_count = 3
        self.shell_base_gap_ratio = 0.22
        self.shell_baseline_amplitude = 0.12
        self.shell_amplitude_gap_gain = 1.75
        self.composite_wave_only = False
        self.closure_sphere_enabled = True
        self.last_triad_info: dict[str, object] | None = None
        self.last_composite_info: dict[str, object] | None = None
        self.last_pyramid_units: list[dict[str, object]] = []
        self.wave_shell_history: list[dict[str, object]] = []
        self.slice_grid_history: list[dict[str, object]] = []
        self.space_point_cloud_enabled = True

        self.canvas.request_draw(self.draw_frame)
        self.animation_timer = QtCore.QTimer(self)
        self.animation_timer.timeout.connect(self.request_render)
        self.animation_timer.start(16)

    def draw_frame(self) -> None:
        self.renderer.render(self.scene, self.camera)

    def request_render(self) -> None:
        self.canvas.request_draw()

    def set_dimension_mode(self, enabled: bool) -> None:
        self.dimension_mode_enabled = enabled

    def set_selected_cell(self, cell_id: str | None) -> None:
        self.selected_cell_id = cell_id

    def set_selected_triad(self, triad_id: str | None) -> None:
        self.selected_triad_id = triad_id

    def set_visible_shell_cell_ids(self, cell_ids: set[str]) -> None:
        self.visible_shell_cell_ids = set(cell_ids)

    def set_visible_slice_planes(self, plane_names: set[str]) -> None:
        self.visible_slice_planes = set(plane_names)

    def set_slice_color_mode(self, mode: str) -> None:
        self.slice_color_mode = mode

    def set_wave_shell_trails_enabled(self, enabled: bool) -> None:
        self.wave_shell_trails_enabled = enabled

    def set_slice_grid_trails_enabled(self, enabled: bool) -> None:
        self.slice_grid_trails_enabled = enabled

    def set_shell_network_enabled(self, enabled: bool) -> None:
        self.shell_network_enabled = enabled

    def set_shell_layer_parameters(
        self,
        layer_count: int,
        base_gap_ratio: float,
        baseline_amplitude: float,
        amplitude_gap_gain: float,
    ) -> None:
        self.shell_layer_count = max(1, int(layer_count))
        self.shell_base_gap_ratio = max(0.01, float(base_gap_ratio))
        self.shell_baseline_amplitude = max(0.001, float(baseline_amplitude))
        self.shell_amplitude_gap_gain = max(0.0, float(amplitude_gap_gain))

    def set_composite_wave_only(self, enabled: bool) -> None:
        self.composite_wave_only = enabled

    def set_closure_sphere_enabled(self, enabled: bool) -> None:
        self.closure_sphere_enabled = enabled

    def set_wave_shell_history(self, history: list[dict[str, object]]) -> None:
        self.wave_shell_history = history

    def set_slice_grid_history(self, history: list[dict[str, object]]) -> None:
        self.slice_grid_history = history

    def set_space_point_cloud_enabled(self, enabled: bool) -> None:
        self.space_point_cloud_enabled = enabled

    def set_dimension_history(self, history: list[dict[str, object]]) -> None:
        if not history:
            for obj in self.dimension_traj_objects.values():
                obj.visible = False
            for obj in self.dimension_stage_marker_objects.values():
                obj.visible = False
            for obj in self.dimension_stage_label_objects.values():
                obj.visible = False
            return
        current_center = np.asarray(history[-1]["center"], dtype=np.float32)
        points = []
        stage_marker_points: Dict[str, list[np.ndarray]] = {name: [] for name in DIMENSION_STAGE_COLORS}
        stage_label_items: list[tuple[str, np.ndarray, np.ndarray]] = []
        previous_stage: str | None = None
        for item in history:
            state = item["state"]
            scale = float(item["scale"])
            point = current_center + scale * np.asarray(state.n0, dtype=np.float32)
            points.append(point)
            stage = str(state.stage)
            if previous_stage is not None and stage != previous_stage:
                stage_marker_points.setdefault(stage, []).append(point)
                if stage in DIMENSION_STAGE_LABELS:
                    stage_label_items.append((stage, point, np.asarray(state.n2, dtype=np.float32)))
            previous_stage = stage
        active_traj_ids = set()
        for idx in range(len(points) - 1):
            segment = np.vstack([points[idx], points[idx + 1]]).astype(np.float32)
            start_color = dimension_state_color(history[idx]["state"])
            end_color = dimension_state_color(history[idx + 1]["state"])
            segment_color = lerp_color(start_color, end_color, 0.5)
            object_id = f"traj:{idx}"
            if object_id not in self.dimension_traj_objects:
                geometry = gfx.Geometry(positions=gfx.Buffer(segment))
                material = gfx.LineMaterial(color=segment_color, thickness=3)
                obj = gfx.Line(geometry, material)
                self.dimension_traj_objects[object_id] = obj
                self.scene.add(obj)
            else:
                obj = self.dimension_traj_objects[object_id]
                if obj.geometry.positions.data.shape != segment.shape:
                    obj.geometry.positions = gfx.Buffer(segment)
                else:
                    obj.geometry.positions.data[:] = segment
                    obj.geometry.positions.update_range()
                obj.material.color = segment_color
            obj.visible = True
            active_traj_ids.add(object_id)
        for object_id, obj in self.dimension_traj_objects.items():
            obj.visible = object_id in active_traj_ids

        for stage_name, color in DIMENSION_STAGE_COLORS.items():
            marker_points = np.asarray(stage_marker_points.get(stage_name, []), dtype=np.float32)
            if marker_points.size == 0:
                marker_points = np.zeros((1, 3), dtype=np.float32)
                visible = False
            else:
                visible = True
            if stage_name not in self.dimension_stage_marker_objects:
                geometry = gfx.Geometry(positions=gfx.Buffer(marker_points))
                material = gfx.PointsMaterial(
                    color=(color.redF(), color.greenF(), color.blueF(), 1.0),
                    size=0.08,
                    size_mode="uniform",
                )
                obj = gfx.Points(geometry, material)
                self.dimension_stage_marker_objects[stage_name] = obj
                self.scene.add(obj)
            else:
                obj = self.dimension_stage_marker_objects[stage_name]
                if obj.geometry.positions.data.shape != marker_points.shape:
                    obj.geometry.positions = gfx.Buffer(marker_points)
                else:
                    obj.geometry.positions.data[:] = marker_points
                    obj.geometry.positions.update_range()
            obj.visible = visible

        active_label_ids = set()
        for idx, (stage_name, point, offset_axis) in enumerate(stage_label_items):
            object_id = f"label:{idx}:{stage_name}"
            label_pos = np.asarray(point, dtype=np.float32) + 0.06 * np.asarray(offset_axis, dtype=np.float32)
            if object_id not in self.dimension_stage_label_objects:
                obj = gfx.Text(
                    text=DIMENSION_STAGE_LABELS[stage_name],
                    font_size=14,
                    screen_space=True,
                    anchor="middle-center",
                    material=gfx.TextMaterial(color=DIMENSION_STAGE_RGB[stage_name]),
                )
                self.dimension_stage_label_objects[object_id] = obj
                self.scene.add(obj)
            else:
                obj = self.dimension_stage_label_objects[object_id]
                obj.text = DIMENSION_STAGE_LABELS[stage_name]
                obj.material.color = DIMENSION_STAGE_RGB[stage_name]
            obj.local.position = tuple(float(v) for v in label_pos)
            obj.visible = True
            active_label_ids.add(object_id)
        for object_id, obj in self.dimension_stage_label_objects.items():
            obj.visible = object_id in active_label_ids

    def update_frame(
        self,
        frame: FrameState,
        triads: list[TriadRecord] | None = None,
        triad_core_states: dict[str, TriadCoreState] | None = None,
        triad_diagnostics: dict[str, dict[str, object]] | None = None,
        pyramid_units: list[dict[str, object]] | None = None,
    ) -> None:
        if pyramid_units is None:
            triad_items = triads if triads is not None else resolve_frame_triads(frame)
            pyramid_units = build_frame_pyramid_units(
                frame,
                triads=triad_items,
                triad_core_states=triad_core_states,
                triad_diagnostics=triad_diagnostics,
            )
        self.last_pyramid_units = pyramid_units
        self.last_triad_info = pyramid_units[0] if pyramid_units else None
        self.last_composite_info = pyramid_units[0]["summary"] if pyramid_units else None
        split_cells = [
            cell
            for pyramid in pyramid_units
            for cell in pyramid.get("active_split_cells", pyramid.get("split_cells", []))
        ]
        display_cells = [*frame.cells, *split_cells]
        render_cells = display_cells
        if self.composite_wave_only:
            render_cells = []

        if display_cells:
            positions = np.asarray([cell.center for cell in display_cells], dtype=np.float32)
        else:
            positions = np.zeros((0, 3), dtype=np.float32)
        if positions.shape != self.cell_positions.data.shape:
            self.cell_positions = gfx.Buffer(positions.copy())
            self.cell_geometry.positions = self.cell_positions
        else:
            self.cell_positions.data[:] = positions
        self.cell_positions.update_range()
        self.cell_points.visible = not self.composite_wave_only

        active_ids = set()
        level_colors = {
            0: (0.95, 0.45, 0.15, 1.0),
            1: (0.15, 0.8, 0.9, 1.0),
            2: (0.7, 0.5, 0.95, 1.0),
            3: (0.95, 0.35, 0.7, 1.0),
        }

        for node in frame.axis_nodes:
            direction = axis_direction_array(node)
            norm = float(np.linalg.norm(direction))
            if norm < 1e-6:
                direction = np.array([1.0, 0.0, 0.0], dtype=np.float32)
            else:
                direction = direction / norm

            half_length = 0.5 + 1.2 * node.strength + 0.15 * node.level
            center = axis_center_array(node)
            segment = np.vstack(
                [
                    center - half_length * direction,
                    center + half_length * direction,
                ]
            ).astype(np.float32)

            if node.id not in self.axis_objects:
                geometry = gfx.Geometry(positions=gfx.Buffer(segment))
                material = gfx.LineMaterial(color=level_colors.get(node.level, (0.9, 0.9, 0.9, 1.0)), thickness=4)
                line = gfx.Line(geometry, material)
                self.axis_objects[node.id] = line
                self.scene.add(line)
            else:
                line = self.axis_objects[node.id]
                line.geometry.positions.data[:] = segment
                line.geometry.positions.update_range()
                line.material.color = level_colors.get(node.level, (0.9, 0.9, 0.9, 1.0))
            active_ids.add(node.id)

        for node_id, obj in self.axis_objects.items():
            obj.visible = node_id in active_ids

        active_cell_axis_ids = set()
        cell_axis_colors = {
            "n0": (0.95, 0.25, 0.25, 1.0),
            "n1": (0.25, 0.95, 0.35, 1.0),
            "n2": (0.25, 0.55, 0.98, 1.0),
        }
        for cell in render_cells:
            center = np.asarray(cell.center, dtype=np.float32)
            basis, scale = cell_local_frame(cell)
            for idx, axis_name in enumerate(["n0", "n1", "n2"]):
                direction = basis[idx]
                segment = np.vstack(
                    [
                        center,
                        center + scale * direction,
                    ]
                ).astype(np.float32)
                object_id = f"{cell.id}:{axis_name}"
                if object_id not in self.cell_axis_objects:
                    geometry = gfx.Geometry(positions=gfx.Buffer(segment))
                    material = gfx.LineMaterial(color=cell_axis_colors[axis_name], thickness=3)
                    line = gfx.Line(geometry, material)
                    self.cell_axis_objects[object_id] = line
                    self.scene.add(line)
                else:
                    line = self.cell_axis_objects[object_id]
                    line.geometry.positions.data[:] = segment
                    line.geometry.positions.update_range()
                active_cell_axis_ids.add(object_id)

        for object_id, obj in self.cell_axis_objects.items():
            obj.visible = (object_id in active_cell_axis_ids) and (not self.composite_wave_only)

        point_cloud_cells = build_pyramid_field_sources(pyramid_units)
        if not point_cloud_cells:
            for cell in render_cells:
                state, _ = cell_dimension_generation_state(cell)
                dynamic_basis = np.vstack(
                    [
                        np.asarray(state.n0, dtype=np.float32),
                        np.asarray(state.n1, dtype=np.float32),
                        np.asarray(state.n2, dtype=np.float32),
                    ]
                ).astype(np.float32)
                point_cloud_cells.append(
                    {
                        "center": np.asarray(cell.center, dtype=np.float32),
                        "dynamic_basis": dynamic_basis,
                        "phase": float(cell.phase),
                        "state": state,
                    }
                )
        if self.space_point_cloud_enabled and point_cloud_cells:
            cloud_positions, cloud_colors = build_space_point_cloud(point_cloud_cells, self.slice_color_mode)
            if cloud_positions.shape != self.space_field_positions.data.shape:
                self.space_field_positions = gfx.Buffer(cloud_positions)
                self.space_field_geometry.positions = self.space_field_positions
            else:
                self.space_field_positions.data[:] = cloud_positions
                self.space_field_positions.update_range()
            if cloud_colors.shape != self.space_field_colors.data.shape:
                self.space_field_colors = gfx.Buffer(cloud_colors)
                self.space_field_geometry.colors = self.space_field_colors
            else:
                self.space_field_colors.data[:] = cloud_colors
                self.space_field_colors.update_range()
            self.space_field_points.visible = True
        else:
            self.space_field_points.visible = False

        active_dimension_ids = set()
        active_shell_ids = set()
        active_shell_network_ids = set()
        active_closure_sphere_ids = set()
        active_shell_trail_ids = set()
        active_plane_ids = set()
        active_slice_ids = set()
        active_slice_trail_ids = set()
        active_pyramid_edge_ids = set()
        active_pyramid_face_ids = set()
        active_pyramid_axis_ids = set()

        for pyramid in pyramid_units:
            triad_id = str(pyramid["id"])
            is_selected_triad = triad_id == self.selected_triad_id
            for segment_id, points, color, thickness in build_pyramid_edge_segments(pyramid, selected=is_selected_triad):
                object_id = f"pyramid_edge:{triad_id}:{segment_id}"
                if object_id not in self.pyramid_edge_objects:
                    geometry = gfx.Geometry(positions=gfx.Buffer(points))
                    material = gfx.LineMaterial(color=color, thickness=thickness)
                    line = gfx.Line(geometry, material)
                    self.pyramid_edge_objects[object_id] = line
                    self.scene.add(line)
                else:
                    line = self.pyramid_edge_objects[object_id]
                    if line.geometry.positions.data.shape != points.shape:
                        line.geometry.positions = gfx.Buffer(points)
                    else:
                        line.geometry.positions.data[:] = points
                        line.geometry.positions.update_range()
                    line.material.color = color
                    line.material.thickness = thickness
                active_pyramid_edge_ids.add(object_id)
            for segment_id, points, color, thickness in build_pyramid_face_segments(pyramid, selected=is_selected_triad):
                object_id = f"pyramid_face:{triad_id}:{segment_id}"
                if object_id not in self.pyramid_face_objects:
                    geometry = gfx.Geometry(positions=gfx.Buffer(points))
                    material = gfx.LineMaterial(color=color, thickness=thickness)
                    line = gfx.Line(geometry, material)
                    self.pyramid_face_objects[object_id] = line
                    self.scene.add(line)
                else:
                    line = self.pyramid_face_objects[object_id]
                    if line.geometry.positions.data.shape != points.shape:
                        line.geometry.positions = gfx.Buffer(points)
                    else:
                        line.geometry.positions.data[:] = points
                        line.geometry.positions.update_range()
                    line.material.color = color
                    line.material.thickness = thickness
                active_pyramid_face_ids.add(object_id)
            axis_points = np.vstack(
                [
                    np.asarray(pyramid["base_center"], dtype=np.float32),
                    np.asarray(pyramid["apex"], dtype=np.float32),
                ]
            ).astype(np.float32)
            axis_object_id = f"pyramid_axis:{triad_id}:connector"
            axis_color = (1.0, 0.95, 0.35, 0.95) if is_selected_triad else (0.9, 0.9, 0.55, 0.55)
            axis_thickness = 3.0 if is_selected_triad else 1.8
            if axis_object_id not in self.pyramid_axis_objects:
                geometry = gfx.Geometry(positions=gfx.Buffer(axis_points))
                material = gfx.LineMaterial(color=axis_color, thickness=axis_thickness)
                line = gfx.Line(geometry, material)
                self.pyramid_axis_objects[axis_object_id] = line
                self.scene.add(line)
            else:
                line = self.pyramid_axis_objects[axis_object_id]
                line.geometry.positions.data[:] = axis_points
                line.geometry.positions.update_range()
                line.material.color = axis_color
                line.material.thickness = axis_thickness
            active_pyramid_axis_ids.add(axis_object_id)

        for cell in render_cells:
            center = np.asarray(cell.center, dtype=np.float32)
            basis, shell_scale = cell_local_frame(cell)
            shell_state, _ = cell_dimension_generation_state(cell)
            dynamic_basis = np.vstack(
                [
                    np.asarray(shell_state.n0, dtype=np.float32),
                    np.asarray(shell_state.n1, dtype=np.float32),
                    np.asarray(shell_state.n2, dtype=np.float32),
                ]
            ).astype(np.float32)
            shell_alpha = 0.70 if cell.id == self.selected_cell_id else 0.32
            shell_thickness = 2.2 if cell.id == self.selected_cell_id else 1.2
            layer_radii = shell_layer_radii(
                float(shell_scale),
                float(cell.phase),
                shell_state,
                layer_count=self.shell_layer_count,
                baseline_amplitude=self.shell_baseline_amplitude,
                base_gap_ratio=self.shell_base_gap_ratio,
                amplitude_gap_gain=self.shell_amplitude_gap_gain,
            )
            layer_count = len(layer_radii)
            for layer_idx, layer_radius in enumerate(layer_radii):
                layer_ratio = layer_idx / max(layer_count - 1, 1)
                layer_alpha = shell_alpha * (0.86 - 0.28 * layer_ratio)
                layer_thickness = max(0.7, shell_thickness * (1.0 - 0.22 * layer_ratio))
                for shell_id, shell_mode, parameter in SHELL_SPECS:
                    segments = distorted_shell_ring_segments(
                        center=center,
                        basis=dynamic_basis,
                        radius=layer_radius,
                        mode=shell_mode,
                        parameter=float(parameter),
                        phase=float(cell.phase),
                        state=shell_state,
                    )
                    for segment_idx, (shell_segment, shell_phase) in enumerate(segments):
                        object_id = f"shell:{cell.id}:{layer_idx}:{shell_id}:{segment_idx}"
                        shell_color = phase_band_color(shell_phase, alpha=layer_alpha)
                        if object_id not in self.dimension_shell_objects:
                            geometry = gfx.Geometry(positions=gfx.Buffer(shell_segment))
                            material = gfx.LineMaterial(color=shell_color, thickness=layer_thickness)
                            line = gfx.Line(geometry, material)
                            self.dimension_shell_objects[object_id] = line
                            self.scene.add(line)
                        else:
                            line = self.dimension_shell_objects[object_id]
                            if line.geometry.positions.data.shape != shell_segment.shape:
                                line.geometry.positions = gfx.Buffer(shell_segment)
                            else:
                                line.geometry.positions.data[:] = shell_segment
                                line.geometry.positions.update_range()
                            line.material.color = shell_color
                            line.material.thickness = layer_thickness
                        active_shell_ids.add(object_id)
            if self.shell_network_enabled:
                network_alpha = 0.55 if cell.id == self.selected_cell_id else 0.24
                network_thickness = 1.2 if cell.id == self.selected_cell_id else 0.8
                for layer_idx, layer_radius in enumerate(layer_radii):
                    layer_ratio = layer_idx / max(layer_count - 1, 1)
                    layer_alpha = network_alpha * (0.90 - 0.30 * layer_ratio)
                    layer_thickness = max(0.45, network_thickness * (1.0 - 0.25 * layer_ratio))
                    network_segments = build_shell_network_segments(
                        center=center,
                        basis=dynamic_basis,
                        radius=layer_radius,
                        phase=float(cell.phase),
                        state=shell_state,
                    )
                    for segment_idx, (network_segment, network_phase) in enumerate(network_segments):
                        object_id = f"shellnet:{cell.id}:{layer_idx}:{segment_idx}"
                        network_color = phase_band_color(network_phase, alpha=layer_alpha)
                        if object_id not in self.dimension_shell_network_objects:
                            geometry = gfx.Geometry(positions=gfx.Buffer(network_segment))
                            material = gfx.LineMaterial(color=network_color, thickness=layer_thickness)
                            line = gfx.Line(geometry, material)
                            self.dimension_shell_network_objects[object_id] = line
                            self.scene.add(line)
                        else:
                            line = self.dimension_shell_network_objects[object_id]
                            if line.geometry.positions.data.shape != network_segment.shape:
                                line.geometry.positions = gfx.Buffer(network_segment)
                            else:
                                line.geometry.positions.data[:] = network_segment
                                line.geometry.positions.update_range()
                            line.material.color = network_color
                            line.material.thickness = layer_thickness
                        active_shell_network_ids.add(object_id)

        if self.closure_sphere_enabled and self.last_composite_info is not None and bool(self.last_composite_info["can_compose"]):
            closure_center = np.asarray(self.last_composite_info["closure_center"], dtype=np.float32)
            closure_radius = float(self.last_composite_info["closure_radius"])
            closure_basis = orthonormal_basis_from_hint(np.array([1.0, 0.0, 0.0], dtype=np.float32))
            closure_specs = [
                ("lat:-45", "latitude", -math.pi / 4.0),
                ("lat:0", "latitude", 0.0),
                ("lat:+45", "latitude", math.pi / 4.0),
                ("lon:0", "longitude", 0.0),
                ("lon:60", "longitude", math.pi / 3.0),
                ("lon:120", "longitude", 2.0 * math.pi / 3.0),
            ]
            closure_phase = 0.0
            if pyramid_units:
                closure_phase = float(pyramid_units[0]["phase"])
            for shell_id, shell_mode, parameter in closure_specs:
                segments = distorted_shell_ring_segments(
                    center=closure_center,
                    basis=closure_basis,
                    radius=closure_radius,
                    mode=shell_mode,
                    parameter=float(parameter),
                    phase=closure_phase,
                    state=build_dimension_frame(closure_basis, closure_phase),
                )
                for segment_idx, (segment, segment_phase) in enumerate(segments):
                    object_id = f"closure_sphere:{shell_id}:{segment_idx}"
                    color = phase_band_color(segment_phase, alpha=0.88)
                    if object_id not in self.closure_sphere_objects:
                        geometry = gfx.Geometry(positions=gfx.Buffer(segment))
                        material = gfx.LineMaterial(color=color, thickness=2.8)
                        line = gfx.Line(geometry, material)
                        self.closure_sphere_objects[object_id] = line
                        self.scene.add(line)
                    else:
                        line = self.closure_sphere_objects[object_id]
                        if line.geometry.positions.data.shape != segment.shape:
                            line.geometry.positions = gfx.Buffer(segment)
                        else:
                            line.geometry.positions.data[:] = segment
                            line.geometry.positions.update_range()
                        line.material.color = color
                        line.material.thickness = 2.8
                    active_closure_sphere_ids.add(object_id)

        if self.dimension_mode_enabled and self.selected_cell_id is not None and self.wave_shell_trails_enabled and self.wave_shell_history:
            trail_count = len(self.wave_shell_history)
            for trail_index, item in enumerate(self.wave_shell_history[:-1]):
                center = np.asarray(item["center"], dtype=np.float32)
                dynamic_basis = np.asarray(item["dynamic_basis"], dtype=np.float32)
                shell_scale = float(item["scale"])
                shell_phase = float(item["phase"])
                shell_state = item["state"]
                age = (trail_count - 1) - trail_index
                age_ratio = age / max(trail_count - 1, 1)
                trail_alpha = 0.10 + 0.22 * (1.0 - age_ratio)
                trail_thickness = 0.6 + 0.7 * (1.0 - age_ratio)
                for shell_id, shell_mode, parameter in SHELL_SPECS:
                    segments = distorted_shell_ring_segments(
                        center=center,
                        basis=dynamic_basis,
                        radius=shell_scale,
                        mode=shell_mode,
                        parameter=float(parameter),
                        phase=shell_phase,
                        state=shell_state,
                    )
                    for segment_idx, (shell_segment, shell_local_phase) in enumerate(segments):
                        object_id = f"trail:{trail_index}:{shell_id}:{segment_idx}"
                        shell_color = phase_band_color(shell_local_phase, alpha=trail_alpha)
                        if object_id not in self.dimension_shell_trail_objects:
                            geometry = gfx.Geometry(positions=gfx.Buffer(shell_segment))
                            material = gfx.LineMaterial(color=shell_color, thickness=trail_thickness)
                            line = gfx.Line(geometry, material)
                            self.dimension_shell_trail_objects[object_id] = line
                            self.scene.add(line)
                        else:
                            line = self.dimension_shell_trail_objects[object_id]
                            if line.geometry.positions.data.shape != shell_segment.shape:
                                line.geometry.positions = gfx.Buffer(shell_segment)
                            else:
                                line.geometry.positions.data[:] = shell_segment
                                line.geometry.positions.update_range()
                            line.material.color = shell_color
                            line.material.thickness = trail_thickness
                        active_shell_trail_ids.add(object_id)

        if self.dimension_mode_enabled and self.selected_cell_id is not None and self.slice_grid_trails_enabled and self.slice_grid_history:
            trail_count = len(self.slice_grid_history)
            for trail_index, item in enumerate(self.slice_grid_history[:-1]):
                age = (trail_count - 1) - trail_index
                age_ratio = age / max(trail_count - 1, 1)
                trail_alpha = 0.05 + 0.14 * (1.0 - age_ratio)
                trail_thickness = 0.45 + 0.45 * (1.0 - age_ratio)
                frame_cells = item.get("cells", [])
                for cell_idx, cell_item in enumerate(frame_cells):
                    center = np.asarray(cell_item["center"], dtype=np.float32)
                    dynamic_basis = np.asarray(cell_item["dynamic_basis"], dtype=np.float32)
                    slice_phase = float(cell_item["phase"])
                    slice_state = cell_item["state"]
                    for plane_name in SLICE_PLANES:
                        if plane_name not in self.visible_slice_planes:
                            continue
                        slice_segments = build_slice_grid_segments(
                            plane=plane_name,
                            center=center,
                            basis=dynamic_basis,
                            phase=slice_phase,
                            state=slice_state,
                        )
                        for segment_idx, (segment, local_phase, strain) in enumerate(slice_segments):
                            object_id = f"slice_trail:{trail_index}:{cell_idx}:{plane_name}:{segment_idx}"
                            if self.slice_color_mode == "strain":
                                color = strain_band_color(strain, alpha=trail_alpha)
                            else:
                                color = phase_band_color(local_phase, alpha=trail_alpha)
                            if object_id not in self.dimension_slice_trail_objects:
                                geometry = gfx.Geometry(positions=gfx.Buffer(segment))
                                material = gfx.LineMaterial(color=color, thickness=trail_thickness)
                                line = gfx.Line(geometry, material)
                                self.dimension_slice_trail_objects[object_id] = line
                                self.scene.add(line)
                            else:
                                line = self.dimension_slice_trail_objects[object_id]
                                if line.geometry.positions.data.shape != segment.shape:
                                    line.geometry.positions = gfx.Buffer(segment)
                                else:
                                    line.geometry.positions.data[:] = segment
                                    line.geometry.positions.update_range()
                                line.material.color = color
                                line.material.thickness = trail_thickness
                            active_slice_trail_ids.add(object_id)

        if self.dimension_mode_enabled and self.selected_cell_id is not None:
            selected_cell = next((cell for cell in frame.cells if cell.id == self.selected_cell_id), None)
            if selected_cell is not None:
                center = np.asarray(selected_cell.center, dtype=np.float32)
                basis, shell_scale = cell_local_frame(selected_cell)
                state, scale = cell_dimension_generation_state(selected_cell)
                dynamic_basis = np.vstack(
                    [
                        np.asarray(state.n0, dtype=np.float32),
                        np.asarray(state.n1, dtype=np.float32),
                        np.asarray(state.n2, dtype=np.float32),
                    ]
                ).astype(np.float32)
                dimension_colors = {
                    "n0": (1.0, 0.95, 0.35, 1.0),
                    "n1": (0.35, 1.0, 0.8, 1.0),
                    "n2": (0.45, 0.75, 1.0, 1.0),
                }
                for plane_name in SLICE_PLANES:
                    if plane_name not in self.visible_slice_planes:
                        continue
                    slice_segments = build_slice_grid_segments(
                        plane=plane_name,
                        center=center,
                        basis=dynamic_basis,
                        phase=float(selected_cell.phase),
                        state=state,
                    )
                    for segment_idx, (segment, local_phase, strain) in enumerate(slice_segments):
                        object_id = f"slice:{selected_cell.id}:{plane_name}:{segment_idx}"
                        if self.slice_color_mode == "strain":
                            color = strain_band_color(strain, alpha=0.34)
                        else:
                            color = phase_band_color(local_phase, alpha=0.34)
                        if object_id not in self.dimension_slice_objects:
                            geometry = gfx.Geometry(positions=gfx.Buffer(segment))
                            material = gfx.LineMaterial(color=color, thickness=1.2)
                            line = gfx.Line(geometry, material)
                            self.dimension_slice_objects[object_id] = line
                            self.scene.add(line)
                        else:
                            line = self.dimension_slice_objects[object_id]
                            if line.geometry.positions.data.shape != segment.shape:
                                line.geometry.positions = gfx.Buffer(segment)
                            else:
                                line.geometry.positions.data[:] = segment
                                line.geometry.positions.update_range()
                            line.material.color = color
                        active_slice_ids.add(object_id)

                tangent_origin = center + float(shell_scale) * np.asarray(state.n0, dtype=np.float32)
                plane_half_extent = 0.36 * float(shell_scale)
                corner_a = tangent_origin + plane_half_extent * (np.asarray(state.n1, dtype=np.float32) + np.asarray(state.n2, dtype=np.float32))
                corner_b = tangent_origin + plane_half_extent * (np.asarray(state.n1, dtype=np.float32) - np.asarray(state.n2, dtype=np.float32))
                corner_c = tangent_origin + plane_half_extent * (-np.asarray(state.n1, dtype=np.float32) - np.asarray(state.n2, dtype=np.float32))
                corner_d = tangent_origin + plane_half_extent * (-np.asarray(state.n1, dtype=np.float32) + np.asarray(state.n2, dtype=np.float32))
                plane_outline = np.vstack([corner_a, corner_b, corner_c, corner_d, corner_a]).astype(np.float32)
                plane_cross_n1 = np.vstack(
                    [
                        tangent_origin - plane_half_extent * np.asarray(state.n1, dtype=np.float32),
                        tangent_origin + plane_half_extent * np.asarray(state.n1, dtype=np.float32),
                    ]
                ).astype(np.float32)
                plane_cross_n2 = np.vstack(
                    [
                        tangent_origin - plane_half_extent * np.asarray(state.n2, dtype=np.float32),
                        tangent_origin + plane_half_extent * np.asarray(state.n2, dtype=np.float32),
                    ]
                ).astype(np.float32)
                normal_link = np.vstack([center, tangent_origin]).astype(np.float32)
                plane_geometries = {
                    f"plane:{selected_cell.id}:outline": (plane_outline, (0.95, 0.95, 1.0, 0.36), 2.0),
                    f"plane:{selected_cell.id}:n1": (plane_cross_n1, (0.35, 1.0, 0.8, 0.72), 2.5),
                    f"plane:{selected_cell.id}:n2": (plane_cross_n2, (0.45, 0.75, 1.0, 0.72), 2.5),
                    f"plane:{selected_cell.id}:normal": (normal_link, (1.0, 0.95, 0.35, 0.45), 1.5),
                }
                for object_id, (points, color, thickness) in plane_geometries.items():
                    if object_id not in self.dimension_plane_objects:
                        geometry = gfx.Geometry(positions=gfx.Buffer(points))
                        material = gfx.LineMaterial(color=color, thickness=thickness)
                        line = gfx.Line(geometry, material)
                        self.dimension_plane_objects[object_id] = line
                        self.scene.add(line)
                    else:
                        line = self.dimension_plane_objects[object_id]
                        if line.geometry.positions.data.shape != points.shape:
                            line.geometry.positions = gfx.Buffer(points)
                        else:
                            line.geometry.positions.data[:] = points
                            line.geometry.positions.update_range()
                    active_plane_ids.add(object_id)
                for axis_name, direction, strength in [
                    ("n0", state.n0, state.n0_strength),
                    ("n1", state.n1, state.n1_strength),
                    ("n2", state.n2, state.n2_strength),
                ]:
                    segment = np.vstack(
                        [
                            center,
                            center + float(scale) * float(strength) * np.asarray(direction, dtype=np.float32),
                        ]
                    ).astype(np.float32)
                    object_id = f"dimension:{selected_cell.id}:{axis_name}"
                    if object_id not in self.dimension_axis_objects:
                        geometry = gfx.Geometry(positions=gfx.Buffer(segment))
                        material = gfx.LineMaterial(color=dimension_colors[axis_name], thickness=6)
                        line = gfx.Line(geometry, material)
                        self.dimension_axis_objects[object_id] = line
                        self.scene.add(line)
                    else:
                        line = self.dimension_axis_objects[object_id]
                        line.geometry.positions.data[:] = segment
                        line.geometry.positions.update_range()
                    active_dimension_ids.add(object_id)

        for object_id, obj in self.dimension_axis_objects.items():
            obj.visible = object_id in active_dimension_ids
        for object_id, obj in self.pyramid_edge_objects.items():
            obj.visible = object_id in active_pyramid_edge_ids
        for object_id, obj in self.pyramid_face_objects.items():
            obj.visible = object_id in active_pyramid_face_ids
        for object_id, obj in self.pyramid_axis_objects.items():
            obj.visible = object_id in active_pyramid_axis_ids
        for object_id, obj in self.dimension_shell_objects.items():
            obj.visible = object_id in active_shell_ids
        for object_id, obj in self.dimension_shell_network_objects.items():
            obj.visible = object_id in active_shell_network_ids
        for object_id, obj in self.closure_sphere_objects.items():
            obj.visible = object_id in active_closure_sphere_ids
        for object_id, obj in self.dimension_shell_trail_objects.items():
            obj.visible = object_id in active_shell_trail_ids
        for object_id, obj in self.dimension_plane_objects.items():
            obj.visible = object_id in active_plane_ids
        for object_id, obj in self.dimension_slice_trail_objects.items():
            obj.visible = object_id in active_slice_trail_ids
        for object_id, obj in self.dimension_slice_objects.items():
            obj.visible = object_id in active_slice_ids


class TimelineWidget(QtWidgets.QWidget):
    frame_changed = QtCore.Signal(int)
    play_toggled = QtCore.Signal(bool)
    follow_latest_changed = QtCore.Signal(bool)

    def __init__(self, frame_count: int, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._playing = False

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self.play_button = QtWidgets.QPushButton("Play")
        self.play_button.clicked.connect(self._toggle_play)
        layout.addWidget(self.play_button)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setRange(0, max(frame_count - 1, 0))
        self.slider.valueChanged.connect(self.frame_changed.emit)
        layout.addWidget(self.slider, 1)

        self.follow_latest_check = QtWidgets.QCheckBox("Follow Latest")
        self.follow_latest_check.toggled.connect(self.follow_latest_changed.emit)
        layout.addWidget(self.follow_latest_check)

        self.mode_label = QtWidgets.QLabel("mode=manual")
        layout.addWidget(self.mode_label)

        self.frame_label = QtWidgets.QLabel("frame=0")
        layout.addWidget(self.frame_label)

    def set_frame(self, frame_index: int, time_value: float) -> None:
        blocker = QtCore.QSignalBlocker(self.slider)
        self.slider.setValue(frame_index)
        del blocker
        self.frame_label.setText(f"frame={frame_index}  t={time_value:.2f}")

    def set_frame_count(self, frame_count: int) -> None:
        blocker = QtCore.QSignalBlocker(self.slider)
        self.slider.setRange(0, max(frame_count - 1, 0))
        del blocker

    def set_follow_latest(self, enabled: bool) -> None:
        blocker = QtCore.QSignalBlocker(self.follow_latest_check)
        self.follow_latest_check.setChecked(enabled)
        del blocker
        self.mode_label.setText("mode=follow" if enabled else "mode=manual")

    def _toggle_play(self) -> None:
        self._playing = not self._playing
        self.play_button.setText("Pause" if self._playing else "Play")
        self.play_toggled.emit(self._playing)


class MetricPlotWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.metric_history: List[MetricRecord] = []
        self.metric_names = ["mass_total_proxy", "resonance_frequency_stability_score"]
        self.metric_colors = {
            "mass_total_proxy": QtGui.QColor("#22c55e"),
            "resonance_frequency_stability_score": QtGui.QColor("#a78bfa"),
        }
        self.setMinimumHeight(180)

    def set_history(self, metric_history: List[MetricRecord], up_to_frame: int | None = None) -> None:
        if up_to_frame is None:
            self.metric_history = list(metric_history)
        else:
            self.metric_history = [item for item in metric_history if item.frame_index <= up_to_frame]
        self.update()

    def paintEvent(self, _event: QtGui.QPaintEvent) -> None:  # noqa: N802
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor("#111827"))
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        margin_left = 42
        margin_right = 14
        margin_top = 18
        margin_bottom = 24
        plot_rect = QtCore.QRectF(
            margin_left,
            margin_top,
            max(10.0, self.width() - margin_left - margin_right),
            max(10.0, self.height() - margin_top - margin_bottom),
        )

        painter.setPen(QtGui.QPen(QtGui.QColor("#334155"), 1))
        painter.drawRect(plot_rect)
        painter.setPen(QtGui.QPen(QtGui.QColor("#cbd5e1"), 1))
        painter.drawText(10, 14, "Metrics")

        if not self.metric_history:
            painter.drawText(int(plot_rect.left()) + 12, int(plot_rect.center().y()), "No metric data")
            painter.end()
            return

        values_by_metric: Dict[str, List[float]] = {name: [] for name in self.metric_names}
        for record in self.metric_history:
            for name in self.metric_names:
                if name in record.values:
                    values_by_metric[name].append(float(record.values[name]))

        flat_values = [value for values in values_by_metric.values() for value in values]
        if not flat_values:
            painter.drawText(int(plot_rect.left()) + 12, int(plot_rect.center().y()), "No tracked metrics available")
            painter.end()
            return

        min_value = min(flat_values)
        max_value = max(flat_values)
        if abs(max_value - min_value) < 1e-9:
            max_value = min_value + 1.0

        painter.setPen(QtGui.QPen(QtGui.QColor("#94a3b8"), 1))
        painter.drawText(6, int(plot_rect.top()) + 4, f"{max_value:.3f}")
        painter.drawText(6, int(plot_rect.bottom()), f"{min_value:.3f}")

        frame_count = max(len(self.metric_history) - 1, 1)
        for metric_name in self.metric_names:
            series = [record.values.get(metric_name) for record in self.metric_history]
            if all(value is None for value in series):
                continue
            path = QtGui.QPainterPath()
            started = False
            for idx, value in enumerate(series):
                if value is None:
                    continue
                x = plot_rect.left() + plot_rect.width() * idx / frame_count
                norm = (float(value) - min_value) / (max_value - min_value)
                y = plot_rect.bottom() - plot_rect.height() * norm
                point = QtCore.QPointF(x, y)
                if not started:
                    path.moveTo(point)
                    started = True
                else:
                    path.lineTo(point)
            painter.setPen(QtGui.QPen(self.metric_colors.get(metric_name, QtGui.QColor("#e5e7eb")), 2))
            painter.drawPath(path)

        legend_y = int(plot_rect.bottom()) + 16
        legend_x = int(plot_rect.left())
        for metric_name in self.metric_names:
            painter.setPen(QtGui.QPen(self.metric_colors.get(metric_name, QtGui.QColor("#e5e7eb")), 2))
            painter.drawLine(legend_x, legend_y, legend_x + 18, legend_y)
            painter.setPen(QtGui.QPen(QtGui.QColor("#e5e7eb"), 1))
            painter.drawText(legend_x + 24, legend_y + 4, metric_name)
            legend_x += 200

        painter.end()


class DimensionPhasePlotWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.history: list[dict[str, object]] = []
        self.current_stage = "seed"
        self.selected_cell_id = ""
        self.setMinimumHeight(220)

    def set_history(self, history: list[dict[str, object]], selected_cell_id: str | None = None) -> None:
        self.history = history
        self.selected_cell_id = selected_cell_id or ""
        if history:
            self.current_stage = str(history[-1]["state"].stage)
        else:
            self.current_stage = "seed"
        self.update()

    def paintEvent(self, _event: QtGui.QPaintEvent) -> None:  # noqa: N802
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor("#0b1220"))
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        margin_left = 42
        margin_right = 16
        margin_top = 22
        margin_bottom = 28
        plot_rect = QtCore.QRectF(
            margin_left,
            margin_top,
            max(10.0, self.width() - margin_left - margin_right),
            max(10.0, self.height() - margin_top - margin_bottom),
        )
        painter.setPen(QtGui.QPen(QtGui.QColor("#334155"), 1))
        painter.drawRect(plot_rect)
        title = "Dimension Expansion"
        if self.selected_cell_id:
            title += f" | {self.selected_cell_id} | stage={self.current_stage}"
        painter.setPen(QtGui.QPen(QtGui.QColor("#e2e8f0"), 1))
        painter.drawText(10, 16, title)

        if not self.history:
            painter.drawText(int(plot_rect.left()) + 12, int(plot_rect.center().y()), "Select a cell to inspect n1/n2 expansion")
            painter.end()
            return

        sample_count = len(self.history)
        if sample_count == 1:
            sample_count = 2

        for idx, item in enumerate(self.history):
            stage = str(item["state"].stage)
            color = DIMENSION_STAGE_COLORS.get(stage, QtGui.QColor("#475569"))
            alpha_color = QtGui.QColor(color)
            alpha_color.setAlpha(52)
            x0 = plot_rect.left() + plot_rect.width() * idx / sample_count
            x1 = plot_rect.left() + plot_rect.width() * (idx + 1) / sample_count
            painter.fillRect(QtCore.QRectF(x0, plot_rect.top(), max(1.0, x1 - x0), plot_rect.height()), alpha_color)

        painter.setPen(QtGui.QPen(QtGui.QColor("#475569"), 1, QtCore.Qt.PenStyle.DashLine))
        for y_value in [0.25, 0.5, 0.75]:
            y = plot_rect.bottom() - plot_rect.height() * y_value
            painter.drawLine(QtCore.QPointF(plot_rect.left(), y), QtCore.QPointF(plot_rect.right(), y))

        def draw_series(name: str, color: QtGui.QColor) -> None:
            path = QtGui.QPainterPath()
            started = False
            for idx, item in enumerate(self.history):
                state = item["state"]
                value = float(getattr(state, name))
                x = plot_rect.left() + plot_rect.width() * idx / max(len(self.history) - 1, 1)
                y = plot_rect.bottom() - plot_rect.height() * float(np.clip(value, 0.0, 1.0))
                point = QtCore.QPointF(x, y)
                if not started:
                    path.moveTo(point)
                    started = True
                else:
                    path.lineTo(point)
            painter.setPen(QtGui.QPen(color, 2))
            painter.drawPath(path)

        draw_series("n1_strength", QtGui.QColor("#34d399"))
        draw_series("n2_strength", QtGui.QColor("#60a5fa"))

        current_x = plot_rect.right()
        painter.setPen(QtGui.QPen(QtGui.QColor("#f8fafc"), 1))
        painter.drawLine(QtCore.QPointF(current_x, plot_rect.top()), QtCore.QPointF(current_x, plot_rect.bottom()))
        painter.drawText(8, int(plot_rect.top()) + 5, "1.0")
        painter.drawText(12, int(plot_rect.bottom()), "0.0")

        legend_y = int(plot_rect.bottom()) + 16
        legend_x = int(plot_rect.left())
        for label, color in [("n1", QtGui.QColor("#34d399")), ("n2", QtGui.QColor("#60a5fa"))]:
            painter.setPen(QtGui.QPen(color, 2))
            painter.drawLine(legend_x, legend_y, legend_x + 18, legend_y)
            painter.setPen(QtGui.QPen(QtGui.QColor("#e5e7eb"), 1))
            painter.drawText(legend_x + 24, legend_y + 4, label)
            legend_x += 72

        stage_x = legend_x + 12
        for stage_name in ["seed", "planar", "lift", "closure"]:
            color = DIMENSION_STAGE_COLORS[stage_name]
            painter.fillRect(stage_x, legend_y - 8, 14, 10, color)
            painter.setPen(QtGui.QPen(QtGui.QColor("#e5e7eb"), 1))
            painter.drawText(stage_x + 20, legend_y + 4, stage_name)
            stage_x += 92

        painter.end()


class StructureTree(QtWidgets.QTreeWidget):
    node_selected = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHeaderLabels(["Object", "Value"])
        self.itemSelectionChanged.connect(self._emit_selection)

    def load_frame(self, frame: FrameState, selected_id: str | None = None, triads: list[TriadRecord] | None = None) -> None:
        self.clear()
        selected_item: QtWidgets.QTreeWidgetItem | None = None

        cells_root = QtWidgets.QTreeWidgetItem(["Cells", str(len(frame.cells))])
        for idx, cell in enumerate(frame.cells):
            item = QtWidgets.QTreeWidgetItem(
                [cell.id or f"cell-{idx}", f"({cell.center[0]:.2f}, {cell.center[1]:.2f}, {cell.center[2]:.2f})"]
            )
            object_id = f"cell:{cell.id or f'cell-{idx}'}"
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, object_id)
            item.addChild(QtWidgets.QTreeWidgetItem(["phase", f"{cell.phase:.3f}"]))
            item.addChild(QtWidgets.QTreeWidgetItem(["frequency", f"{cell.frequency:.3f}"]))
            item.addChild(QtWidgets.QTreeWidgetItem(["radius", f"{cell.radius:.3f}"]))
            if selected_id == object_id:
                selected_item = item
            cells_root.addChild(item)
        self.addTopLevelItem(cells_root)

        triad_items = triads if triads is not None else frame.triads
        triad_root = QtWidgets.QTreeWidgetItem(["Triads", str(len(triad_items))])
        for triad in triad_items:
            item = QtWidgets.QTreeWidgetItem([triad.id, f"compose={triad.can_compose}, c={triad.coherence_score:.2f}"])
            object_id = f"triad:{triad.id}"
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, object_id)
            item.addChild(QtWidgets.QTreeWidgetItem(["cell_ids", ", ".join(triad.cell_ids)]))
            item.addChild(QtWidgets.QTreeWidgetItem(["closure_radius", f"{triad.closure_radius:.3f}"]))
            item.addChild(QtWidgets.QTreeWidgetItem(["phase", f"{triad.phase:.3f}"]))
            if selected_id == object_id:
                selected_item = item
            triad_root.addChild(item)
        self.addTopLevelItem(triad_root)

        axis_root = QtWidgets.QTreeWidgetItem(["Axis Nodes", str(len(frame.axis_nodes))])
        for node in frame.axis_nodes:
            item = QtWidgets.QTreeWidgetItem([node.id, f"level={node.level}, s={node.strength:.2f}"])
            object_id = f"axis:{node.id}"
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, object_id)
            item.addChild(QtWidgets.QTreeWidgetItem(["center", f"{tuple(float(v) for v in node.center)}"]))
            item.addChild(QtWidgets.QTreeWidgetItem(["direction", f"{tuple(float(v) for v in node.direction)}"]))
            if selected_id == object_id:
                selected_item = item
            axis_root.addChild(item)
        self.addTopLevelItem(axis_root)

        metrics_root = QtWidgets.QTreeWidgetItem(["Metrics", str(len(frame.metrics))])
        for key, value in frame.metrics.items():
            metrics_root.addChild(QtWidgets.QTreeWidgetItem([key, f"{value:.6f}"]))
        self.addTopLevelItem(metrics_root)
        self.expandAll()
        if selected_item is not None:
            self.setCurrentItem(selected_item)

    def _emit_selection(self) -> None:
        items = self.selectedItems()
        if not items:
            return
        node_id = items[0].data(0, QtCore.Qt.ItemDataRole.UserRole)
        if node_id:
            self.node_selected.emit(str(node_id))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, frames: List[FrameState], reader: CSDEJsonlReader | None = None) -> None:
        super().__init__()
        self.frames = frames
        self.reader = reader
        self.source_dir: Path | None = Path(reader.paths.root_dir) if reader is not None else None
        self.current_index = 0
        self.follow_latest = reader is not None
        self.latest_metrics: List[MetricRecord] = []
        self.latest_events: List[EventRecord] = []
        self.latest_status: RunStatus | None = None
        self.selected_object_id: str | None = None
        self.current_triads: list[TriadRecord] = resolve_frame_triads(frames[0]) if frames else []
        self.current_closure_tensor: dict[str, object] = {"origin": "closure_phase", "entries": [], "by_lineage": {}}
        self.current_closure_stats: dict[str, object] = {}
        self.current_closure_layout: dict[str, object] = {}
        self.current_reconnect_reports: dict[str, dict[str, object]] = {}
        self.current_quantum_report: dict[str, object] = {}
        self.current_quantum_frames: dict[int, dict[str, object]] = {}
        self.current_quantum_error: str | None = None
        self.dimension_mode_enabled = True
        self.runs_root = (Path(__file__).resolve().parent / "resonance_data").resolve()
        self.shell_toggle_cell_ids: list[str] = []
        self.wave_shell_trails_enabled = False
        self.slice_grid_trails_enabled = False
        self.shell_layer_count = 3
        self.shell_base_gap_ratio = 0.22
        self.shell_baseline_amplitude = 0.12
        self.shell_amplitude_gap_gain = 1.75
        self.composite_wave_only = False

        self.setWindowTitle("CSDE Experiment Viewer Prototype")
        self.resize(1520, 900)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        outer_layout = QtWidgets.QVBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.mode_bar = QtWidgets.QWidget()
        mode_bar_layout = QtWidgets.QHBoxLayout(self.mode_bar)
        mode_bar_layout.setContentsMargins(10, 6, 10, 6)
        self.open_run_button = QtWidgets.QPushButton("Open Run Directory")
        mode_bar_layout.addWidget(self.open_run_button)
        self.refresh_browser_button = QtWidgets.QPushButton("Refresh Browser")
        mode_bar_layout.addWidget(self.refresh_browser_button)
        self.reset_quantum_button = QtWidgets.QPushButton("Reset Quantum")
        mode_bar_layout.addWidget(self.reset_quantum_button)
        self.dimension_mode_check = QtWidgets.QCheckBox("Dimension Generation Mode")
        self.dimension_mode_check.setChecked(True)
        mode_bar_layout.addWidget(self.dimension_mode_check)
        self.shells_label = QtWidgets.QLabel("Shells:")
        mode_bar_layout.addWidget(self.shells_label)
        self.shell_checkboxes: list[QtWidgets.QCheckBox] = []
        for idx in range(3):
            checkbox = QtWidgets.QCheckBox(f"cell-{idx}")
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._on_shell_visibility_changed)
            self.shell_checkboxes.append(checkbox)
            mode_bar_layout.addWidget(checkbox)
        self.slice_label = QtWidgets.QLabel("Slices:")
        mode_bar_layout.addWidget(self.slice_label)
        self.slice_checkboxes: dict[str, QtWidgets.QCheckBox] = {}
        for plane_name in SLICE_PLANES:
            checkbox = QtWidgets.QCheckBox(plane_name)
            checkbox.setChecked(False)
            checkbox.toggled.connect(self._on_slice_visibility_changed)
            self.slice_checkboxes[plane_name] = checkbox
            mode_bar_layout.addWidget(checkbox)
        self.point_cloud_check = QtWidgets.QCheckBox("XYZ Point Cloud")
        self.point_cloud_check.setChecked(True)
        mode_bar_layout.addWidget(self.point_cloud_check)
        self.composite_wave_check = QtWidgets.QCheckBox("Composite Wave Only")
        self.composite_wave_check.setChecked(False)
        mode_bar_layout.addWidget(self.composite_wave_check)
        self.slice_color_label = QtWidgets.QLabel("Slice Color:")
        mode_bar_layout.addWidget(self.slice_color_label)
        self.slice_color_combo = QtWidgets.QComboBox()
        self.slice_color_combo.addItems(["phase", "strain"])
        mode_bar_layout.addWidget(self.slice_color_combo)
        self.shell_trails_check = QtWidgets.QCheckBox("Shell Trails")
        self.shell_trails_check.setChecked(False)
        mode_bar_layout.addWidget(self.shell_trails_check)
        self.shell_network_check = QtWidgets.QCheckBox("Shell Network")
        self.shell_network_check.setChecked(True)
        mode_bar_layout.addWidget(self.shell_network_check)
        self.closure_sphere_check = QtWidgets.QCheckBox("Closure Sphere")
        self.closure_sphere_check.setChecked(True)
        mode_bar_layout.addWidget(self.closure_sphere_check)
        self.layer_count_label = QtWidgets.QLabel("Layer Count:")
        mode_bar_layout.addWidget(self.layer_count_label)
        self.layer_count_spin = QtWidgets.QSpinBox()
        self.layer_count_spin.setRange(1, 8)
        self.layer_count_spin.setValue(self.shell_layer_count)
        mode_bar_layout.addWidget(self.layer_count_spin)
        self.base_gap_label = QtWidgets.QLabel("Base Gap:")
        mode_bar_layout.addWidget(self.base_gap_label)
        self.base_gap_spin = QtWidgets.QDoubleSpinBox()
        self.base_gap_spin.setRange(0.05, 1.50)
        self.base_gap_spin.setSingleStep(0.02)
        self.base_gap_spin.setDecimals(2)
        self.base_gap_spin.setValue(self.shell_base_gap_ratio)
        mode_bar_layout.addWidget(self.base_gap_spin)
        self.baseline_amp_label = QtWidgets.QLabel("Baseline Amp:")
        mode_bar_layout.addWidget(self.baseline_amp_label)
        self.baseline_amp_spin = QtWidgets.QDoubleSpinBox()
        self.baseline_amp_spin.setRange(0.01, 1.00)
        self.baseline_amp_spin.setSingleStep(0.01)
        self.baseline_amp_spin.setDecimals(2)
        self.baseline_amp_spin.setValue(self.shell_baseline_amplitude)
        mode_bar_layout.addWidget(self.baseline_amp_spin)
        self.amplitude_gain_label = QtWidgets.QLabel("Amplitude Gain:")
        mode_bar_layout.addWidget(self.amplitude_gain_label)
        self.amplitude_gain_spin = QtWidgets.QDoubleSpinBox()
        self.amplitude_gain_spin.setRange(0.0, 5.0)
        self.amplitude_gain_spin.setSingleStep(0.05)
        self.amplitude_gain_spin.setDecimals(2)
        self.amplitude_gain_spin.setValue(self.shell_amplitude_gap_gain)
        mode_bar_layout.addWidget(self.amplitude_gain_spin)
        self.slice_trails_check = QtWidgets.QCheckBox("Slice Trails")
        self.slice_trails_check.setChecked(False)
        mode_bar_layout.addWidget(self.slice_trails_check)
        self.gpu_label = QtWidgets.QLabel("Renderer=wgpu")
        mode_bar_layout.addWidget(self.gpu_label)
        self.current_source_label = QtWidgets.QLabel("source=demo")
        mode_bar_layout.addWidget(self.current_source_label)
        self.dimension_mode_label = QtWidgets.QLabel("selected_cell=none")
        mode_bar_layout.addWidget(self.dimension_mode_label)
        mode_bar_layout.addStretch(1)
        outer_layout.addWidget(self.mode_bar)

        self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        outer_layout.addWidget(self.main_splitter, 1)

        self.left_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.left_splitter.setMinimumWidth(340)
        self.main_splitter.addWidget(self.left_splitter)

        self.file_browser_container = QtWidgets.QWidget()
        browser_layout = QtWidgets.QVBoxLayout(self.file_browser_container)
        browser_layout.setContentsMargins(0, 0, 0, 0)
        browser_layout.setSpacing(4)
        self.browser_root_label = QtWidgets.QLabel(f"Runs Root: {self.runs_root}")
        browser_layout.addWidget(self.browser_root_label)
        self.file_model = QtWidgets.QFileSystemModel(self)
        self.file_model.setFilter(QtCore.QDir.Filter.AllDirs | QtCore.QDir.Filter.NoDotAndDotDot)
        self.file_model.setRootPath(str(self.runs_root))
        self.file_tree = QtWidgets.QTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(self.file_model.index(str(self.runs_root)))
        self.file_tree.setHeaderHidden(True)
        for column in range(1, self.file_model.columnCount()):
            self.file_tree.hideColumn(column)
        browser_layout.addWidget(self.file_tree, 1)
        self.left_splitter.addWidget(self.file_browser_container)

        self.structure_tree = StructureTree()
        self.left_splitter.addWidget(self.structure_tree)
        self.left_splitter.setSizes([300, 520])

        self.viewer = Viewer3D()
        self.main_splitter.addWidget(self.viewer)

        self.right_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.right_splitter.setMinimumWidth(320)
        self.main_splitter.addWidget(self.right_splitter)

        self.detail_panel = QtWidgets.QTextEdit()
        self.detail_panel.setReadOnly(True)
        self.right_splitter.addWidget(self.detail_panel)

        self.quantum_tabs = QtWidgets.QTabWidget()

        self.quantum_summary_tab = QtWidgets.QWidget()
        self.quantum_summary_tab_layout = QtWidgets.QVBoxLayout(self.quantum_summary_tab)
        self.quantum_summary_tab_layout.setContentsMargins(0, 0, 0, 0)
        self.quantum_summary_tab_layout.setSpacing(4)
        self.quantum_summary_panel = QtWidgets.QTextEdit()
        self.quantum_summary_panel.setReadOnly(True)
        self.quantum_summary_tab_layout.addWidget(self.quantum_summary_panel)
        self.quantum_tabs.addTab(self.quantum_summary_tab, "Σ Summary")

        self.quantum_frame_tab = QtWidgets.QWidget()
        self.quantum_frame_tab_layout = QtWidgets.QVBoxLayout(self.quantum_frame_tab)
        self.quantum_frame_tab_layout.setContentsMargins(0, 0, 0, 0)
        self.quantum_frame_tab_layout.setSpacing(4)
        self.quantum_frame_panel = QtWidgets.QTextEdit()
        self.quantum_frame_panel.setReadOnly(True)
        self.quantum_frame_tab_layout.addWidget(self.quantum_frame_panel)
        self.quantum_tabs.addTab(self.quantum_frame_tab, "◫ Frame")

        self.quantum_triad_tab = QtWidgets.QWidget()
        self.quantum_triad_tab_layout = QtWidgets.QVBoxLayout(self.quantum_triad_tab)
        self.quantum_triad_tab_layout.setContentsMargins(0, 0, 0, 0)
        self.quantum_triad_tab_layout.setSpacing(4)
        self.quantum_triad_status_label = QtWidgets.QLabel("Selected Triad: none")
        self.quantum_triad_status_label.setStyleSheet("font-weight: 600; padding: 6px 8px; background: #1f2430; color: #f0f3f8; border-radius: 4px;")
        self.quantum_triad_tab_layout.addWidget(self.quantum_triad_status_label)
        self.quantum_triad_panel = QtWidgets.QTextEdit()
        self.quantum_triad_panel.setReadOnly(True)
        self.quantum_triad_tab_layout.addWidget(self.quantum_triad_panel)
        self.quantum_tabs.addTab(self.quantum_triad_tab, "△ Triad")
        self.right_splitter.addWidget(self.quantum_tabs)

        self.event_list = QtWidgets.QListWidget()
        self.right_splitter.addWidget(self.event_list)

        self.metric_plot = MetricPlotWidget()
        self.right_splitter.addWidget(self.metric_plot)
        self.dimension_plot = DimensionPhasePlotWidget()
        self.right_splitter.addWidget(self.dimension_plot)
        self.right_splitter.setSizes([220, 180, 150, 180, 210])
        self.main_splitter.setSizes([360, 780, 380])

        self.timeline = TimelineWidget(frame_count=len(frames))
        outer_layout.addWidget(self.timeline)

        self.play_timer = QtCore.QTimer(self)
        self.play_timer.timeout.connect(self._advance_frame)
        self.play_timer.setInterval(40)

        self.stream_timer = QtCore.QTimer(self)
        self.stream_timer.timeout.connect(self._poll_stream)
        if self.reader is not None:
            self.stream_timer.start(250)

        if self.reader is None:
            self.latest_metrics = [
                MetricRecord(frame_index=frame.frame_index, time=frame.time, values=dict(frame.metrics))
                for frame in self.frames
            ]
        self.timeline.set_follow_latest(self.follow_latest)

        self.timeline.frame_changed.connect(self._on_timeline_frame_changed)
        self.timeline.play_toggled.connect(self._on_play_toggled)
        self.timeline.follow_latest_changed.connect(self._on_follow_latest_changed)
        self.structure_tree.node_selected.connect(self._show_node_details)
        self.dimension_mode_check.toggled.connect(self._on_dimension_mode_changed)
        self.slice_color_combo.currentTextChanged.connect(self._on_slice_color_mode_changed)
        self.shell_trails_check.toggled.connect(self._on_shell_trails_toggled)
        self.shell_network_check.toggled.connect(self._on_shell_network_toggled)
        self.closure_sphere_check.toggled.connect(self._on_closure_sphere_toggled)
        self.layer_count_spin.valueChanged.connect(self._on_shell_parameter_changed)
        self.base_gap_spin.valueChanged.connect(self._on_shell_parameter_changed)
        self.baseline_amp_spin.valueChanged.connect(self._on_shell_parameter_changed)
        self.amplitude_gain_spin.valueChanged.connect(self._on_shell_parameter_changed)
        self.slice_trails_check.toggled.connect(self._on_slice_trails_toggled)
        self.point_cloud_check.toggled.connect(self._on_point_cloud_toggled)
        self.composite_wave_check.toggled.connect(self._on_composite_wave_toggled)
        self.open_run_button.clicked.connect(self._browse_for_run_directory)
        self.refresh_browser_button.clicked.connect(self._refresh_file_browser)
        self.reset_quantum_button.clicked.connect(self._reset_quantum_panel)
        self.file_tree.doubleClicked.connect(self._load_run_directory_from_index)
        self.viewer.set_dimension_mode(self.dimension_mode_enabled)
        self.viewer.set_visible_slice_planes(set())
        self.viewer.set_slice_color_mode(self.slice_color_combo.currentText())
        self.viewer.set_wave_shell_trails_enabled(self.wave_shell_trails_enabled)
        self.viewer.set_slice_grid_trails_enabled(self.slice_grid_trails_enabled)
        self.viewer.set_shell_network_enabled(self.shell_network_check.isChecked())
        self.viewer.set_shell_layer_parameters(
            self.shell_layer_count,
            self.shell_base_gap_ratio,
            self.shell_baseline_amplitude,
            self.shell_amplitude_gap_gain,
        )
        self.viewer.set_space_point_cloud_enabled(True)
        self.viewer.set_composite_wave_only(self.composite_wave_only)
        self.viewer.set_closure_sphere_enabled(self.closure_sphere_check.isChecked())
        if self.reader is not None:
            self._apply_data_source(
                frames=self.frames,
                reader=self.reader,
                metrics=self.reader.poll_metrics(),
                events=self.reader.poll_events(),
                status=self.reader.read_status(),
                source_dir=self.source_dir,
            )
        else:
            self._refresh_file_browser()
            self._update_source_label()
            self._update_shell_visibility_controls(self.frames[0] if self.frames else None)
            if self.frames:
                self.set_frame(0)

    def _on_play_toggled(self, playing: bool) -> None:
        if playing:
            self.play_timer.start()
        else:
            self.play_timer.stop()

    def _on_follow_latest_changed(self, enabled: bool) -> None:
        self.follow_latest = enabled
        self.timeline.set_follow_latest(enabled)
        if enabled:
            if self.timeline._playing:
                self.timeline._toggle_play()
            if self.frames:
                self.set_frame(len(self.frames) - 1)

    def _on_timeline_frame_changed(self, index: int) -> None:
        if self.reader is not None and self.follow_latest and self.frames and index != len(self.frames) - 1:
            self.follow_latest = False
            self.timeline.set_follow_latest(False)
        self.set_frame(index)

    def _on_dimension_mode_changed(self, enabled: bool) -> None:
        self.dimension_mode_enabled = enabled
        self.viewer.set_dimension_mode(enabled)
        self.set_frame(self.current_index)

    def _on_shell_visibility_changed(self, _checked: bool) -> None:
        visible_ids = {
            cell_id
            for checkbox, cell_id in zip(self.shell_checkboxes, self.shell_toggle_cell_ids)
            if checkbox.isEnabled() and checkbox.isChecked()
        }
        self.viewer.set_visible_shell_cell_ids(visible_ids)
        if self.frames:
            self.set_frame(self.current_index)

    def _on_slice_visibility_changed(self, _checked: bool) -> None:
        visible_planes = {
            plane_name
            for plane_name, checkbox in self.slice_checkboxes.items()
            if checkbox.isChecked()
        }
        self.viewer.set_visible_slice_planes(visible_planes)
        if self.frames:
            self.set_frame(self.current_index)

    def _on_slice_color_mode_changed(self, mode: str) -> None:
        self.viewer.set_slice_color_mode(mode)
        if self.frames:
            self.set_frame(self.current_index)

    def _on_point_cloud_toggled(self, enabled: bool) -> None:
        self.viewer.set_space_point_cloud_enabled(enabled)
        if self.frames:
            self.set_frame(self.current_index)

    def _on_composite_wave_toggled(self, enabled: bool) -> None:
        self.composite_wave_only = enabled
        self.viewer.set_composite_wave_only(enabled)
        if self.frames:
            self.set_frame(self.current_index)

    def _on_shell_trails_toggled(self, enabled: bool) -> None:
        self.wave_shell_trails_enabled = enabled
        self.viewer.set_wave_shell_trails_enabled(enabled)
        if self.frames:
            self.set_frame(self.current_index)

    def _on_shell_network_toggled(self, enabled: bool) -> None:
        self.viewer.set_shell_network_enabled(enabled)
        if self.frames:
            self.set_frame(self.current_index)

    def _on_closure_sphere_toggled(self, enabled: bool) -> None:
        self.viewer.set_closure_sphere_enabled(enabled)
        if self.frames:
            self.set_frame(self.current_index)

    def _on_shell_parameter_changed(self, _value: object) -> None:
        self.shell_layer_count = int(self.layer_count_spin.value())
        self.shell_base_gap_ratio = float(self.base_gap_spin.value())
        self.shell_baseline_amplitude = float(self.baseline_amp_spin.value())
        self.shell_amplitude_gap_gain = float(self.amplitude_gain_spin.value())
        self.viewer.set_shell_layer_parameters(
            self.shell_layer_count,
            self.shell_base_gap_ratio,
            self.shell_baseline_amplitude,
            self.shell_amplitude_gap_gain,
        )
        if self.frames:
            self.set_frame(self.current_index)

    def _on_slice_trails_toggled(self, enabled: bool) -> None:
        self.slice_grid_trails_enabled = enabled
        self.viewer.set_slice_grid_trails_enabled(enabled)
        if self.frames:
            self.set_frame(self.current_index)

    def _update_shell_visibility_controls(self, frame: FrameState | None) -> None:
        cell_ids = [cell.id for cell in frame.cells[:3]] if frame is not None else []
        self.shell_toggle_cell_ids = cell_ids
        for idx, checkbox in enumerate(self.shell_checkboxes):
            blocker = QtCore.QSignalBlocker(checkbox)
            if idx < len(cell_ids):
                checkbox.setText(cell_ids[idx])
                checkbox.setEnabled(True)
                checkbox.setChecked(True)
            else:
                checkbox.setText(f"cell-{idx}")
                checkbox.setEnabled(False)
                checkbox.setChecked(False)
            del blocker
        self.viewer.set_visible_shell_cell_ids(set(cell_ids))

    def _refresh_file_browser(self) -> None:
        self.runs_root.mkdir(parents=True, exist_ok=True)
        self.file_model.setRootPath(str(self.runs_root))
        self.file_tree.setRootIndex(self.file_model.index(str(self.runs_root)))
        self.browser_root_label.setText(f"Runs Root: {self.runs_root}")

    def _update_source_label(self) -> None:
        if self.source_dir is None:
            self.current_source_label.setText("source=demo")
        else:
            self.current_source_label.setText(f"source={self.source_dir.name}")

    def _browse_for_run_directory(self) -> None:
        start_dir = str(self.source_dir or self.runs_root)
        selected = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Open CSDE Run Directory",
            start_dir,
        )
        if not selected:
            return
        self._load_run_directory(Path(selected))

    def _load_run_directory_from_index(self, index: QtCore.QModelIndex) -> None:
        path = Path(self.file_model.filePath(index))
        self._load_run_directory(path)

    def _load_run_directory(self, path: Path) -> None:
        candidate = path if path.is_dir() else path.parent
        if not candidate.exists():
            QtWidgets.QMessageBox.warning(self, "Open Run Directory", f"Directory does not exist:\n{candidate}")
            return
        required_files = ["state_stream.jsonl", "metric_stream.csv", "status.json"]
        if not any((candidate / name).exists() for name in required_files):
            QtWidgets.QMessageBox.information(
                self,
                "Open Run Directory",
                f"Selected directory does not look like a CSDE run:\n{candidate}",
            )
            return
        reader = CSDEJsonlReader(candidate)
        frames = reader.poll_states()
        events = reader.poll_events()
        metrics = reader.poll_metrics()
        status = reader.read_status()
        self._apply_data_source(
            frames=frames,
            reader=reader,
            metrics=metrics,
            events=events,
            status=status,
            source_dir=candidate,
        )

    def _set_quantum_status_message(self, message: str, timeout_ms: int = 6000) -> None:
        self.statusBar().showMessage(message, timeout_ms)

    def _reset_quantum_panel(self) -> None:
        self.current_quantum_report = {}
        self.current_quantum_frames = {}
        self.current_quantum_error = "reset by user"
        placeholder = "Quantum consistency report cache cleared. Awaiting reload."
        self.quantum_summary_panel.setPlainText(placeholder)
        self.quantum_frame_panel.setPlainText(placeholder)
        self.quantum_triad_panel.setPlainText(placeholder)
        self.quantum_triad_status_label.setText("Selected Triad: none")
        self._set_quantum_status_message("Quantum panel cache reset.")

    def _load_quantum_report(self, source_dir: Path | None) -> tuple[dict[str, object], dict[int, dict[str, object]], str | None]:
        if source_dir is None:
            return {}, {}, None
        report_path = source_dir / "quantum_consistency_report.json"
        if not report_path.exists():
            return {}, {}, None
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return {}, {}, f"invalid JSON: {exc.msg}"
        except OSError as exc:
            return {}, {}, f"file locked or unreadable: {exc.strerror or exc.__class__.__name__}"
        except Exception as exc:
            return {}, {}, f"report load failed: {exc.__class__.__name__}"
        if not isinstance(report, dict):
            return {}, {}, "invalid report root: expected object"
        if "frames" not in report:
            return {}, {}, "frames field missing"
        frames_payload = report.get("frames", [])
        if not isinstance(frames_payload, list):
            return report, {}, "frames field is not a list"
        frame_map = {
            int(item.get("frame_index", -1)): item
            for item in frames_payload
            if isinstance(item, dict) and "frame_index" in item
        }
        return report, frame_map, None

    def _apply_data_source(
        self,
        frames: List[FrameState],
        reader: CSDEJsonlReader | None,
        metrics: List[MetricRecord],
        events: List[EventRecord],
        status: RunStatus | None,
        source_dir: Path | None,
    ) -> None:
        self.reader = reader
        self.source_dir = source_dir
        self.current_quantum_report, self.current_quantum_frames, self.current_quantum_error = self._load_quantum_report(source_dir)
        if self.current_quantum_error:
            self._set_quantum_status_message(f"Quantum report unavailable: {self.current_quantum_error}")
        self.frames = frames if frames else build_demo_frames()
        self.latest_metrics = metrics if metrics else [
            MetricRecord(frame_index=frame.frame_index, time=frame.time, values=dict(frame.metrics))
            for frame in self.frames
        ]
        self.latest_events = list(events)
        self.latest_status = status
        self.current_index = 0
        self.selected_object_id = None
        self.follow_latest = bool(reader is not None and status is not None and status.status == "running")
        self.timeline.set_follow_latest(self.follow_latest)
        self.timeline.set_frame_count(len(self.frames))
        self.viewer.set_selected_cell(None)
        self.viewer.set_selected_triad(None)
        self.viewer.set_dimension_history([])
        self.dimension_plot.set_history([], None)
        placeholder = "No quantum consistency report loaded."
        self.quantum_summary_panel.setPlainText(placeholder)
        self.quantum_frame_panel.setPlainText(placeholder)
        self.quantum_triad_panel.setPlainText(placeholder)
        self.quantum_triad_status_label.setText("Selected Triad: none")
        self._update_source_label()
        self._update_shell_visibility_controls(self.frames[0] if self.frames else None)
        if reader is not None:
            self.stream_timer.start(250)
        else:
            self.stream_timer.stop()
        self.set_frame(0)

    def _advance_frame(self) -> None:
        if not self.frames:
            return
        if self.reader is not None and self.follow_latest:
            self.set_frame(len(self.frames) - 1)
            return
        if self.current_index + 1 < len(self.frames):
            self.set_frame(self.current_index + 1)
            return
        if self.reader is None:
            self.set_frame(0)

    def _poll_stream(self) -> None:
        if self.reader is None:
            return
        new_frames = self.reader.poll_states()
        new_events = self.reader.poll_events()
        new_metrics = self.reader.poll_metrics()
        status = self.reader.read_status()
        quantum_report_updated = False

        appended = False
        if new_frames:
            self.frames.extend(new_frames)
            self.timeline.set_frame_count(len(self.frames))
            appended = True
        if new_events:
            self.latest_events.extend(new_events)
            self._refresh_event_panel(frame_time_limit=self.frames[self.current_index].time if self.frames else None)
        if new_metrics:
            self.latest_metrics.extend(new_metrics)
            current_frame_index = self.frames[self.current_index].frame_index if self.frames else None
            self.metric_plot.set_history(self.latest_metrics, up_to_frame=current_frame_index)
        if status is not None:
            self.latest_status = status
        if self.source_dir is not None and (self.source_dir / "quantum_consistency_report.json").exists():
            loaded_report, loaded_frames, load_error = self._load_quantum_report(self.source_dir)
            if load_error:
                self.current_quantum_error = load_error
                self._set_quantum_status_message(f"Quantum report unavailable: {load_error}")
            elif loaded_report != self.current_quantum_report or loaded_frames != self.current_quantum_frames:
                self.current_quantum_report = loaded_report
                self.current_quantum_frames = loaded_frames
                self.current_quantum_error = None
                quantum_report_updated = True

        if appended and self.follow_latest:
            self.set_frame(len(self.frames) - 1)
        elif appended and len(self.frames) == len(new_frames):
            self.set_frame(0)
        elif quantum_report_updated:
            self._refresh_quantum_panel()

    def set_frame(self, index: int) -> None:
        if not self.frames:
            return
        self.current_index = int(index)
        frame = self.frames[self.current_index]
        self.current_triads = resolve_frame_triads(frame)
        self._refresh_dimension_visuals()
        frame_to_pyramid_units = lambda tensor_frame: build_frame_pyramid_units(
            tensor_frame,
            triads=resolve_frame_triads(tensor_frame),
        )
        raw_pyramid_units = frame_to_pyramid_units(frame)
        self.current_closure_stats = survey_closure_tensor_statistics(
            self.frames,
            frame_to_pyramid_units=frame_to_pyramid_units,
            history_size=48,
        )
        self.current_closure_layout = infer_closure_tensor_layout(self.current_closure_stats).to_dict()
        self.current_closure_tensor = build_closure_phase_tensor(
            self.frames,
            self.current_index,
            frame_to_pyramid_units=frame_to_pyramid_units,
            history_size=48,
        )
        raw_reconnect_reports: dict[str, dict[str, object]] = {}
        for pyramid in raw_pyramid_units:
            report = query_reconnect_candidates(
                self.current_closure_tensor,
                pyramid,
                phase_tolerance=float(self.current_closure_layout.get("phase_tolerance", 0.28)),
                radial_tolerance=float(self.current_closure_layout.get("radial_tolerance", 0.22)),
                connector_strength_threshold=float(self.current_closure_layout.get("connector_strength_threshold", 0.0)),
                min_history_splits=int(self.current_closure_layout.get("min_history_splits", 1)),
            )
            report["phase_shell_bin_size"] = float(self.current_closure_layout.get("phase_shell_bin_size", 0.0))
            report["radial_shell_bin_size"] = float(self.current_closure_layout.get("radial_shell_bin_size", 0.0))
            report["connector_strength_threshold"] = float(self.current_closure_layout.get("connector_strength_threshold", 0.0))
            raw_reconnect_reports[str(pyramid["id"])] = report
        transitioned_units, transitioned_reports = apply_topology_transitions(raw_pyramid_units, raw_reconnect_reports)
        self.current_reconnect_reports = transitioned_reports
        self.viewer.update_frame(frame, triads=self.current_triads, pyramid_units=transitioned_units)
        if self.viewer.last_composite_info is not None and self.viewer.last_pyramid_units:
            first_triad_id = str(self.viewer.last_pyramid_units[0]["id"])
            self.viewer.last_composite_info.update(self.current_reconnect_reports.get(first_triad_id, {}))
        self.structure_tree.load_frame(frame, selected_id=self.selected_object_id, triads=self.current_triads)
        self.timeline.set_frame(self.current_index, frame.time)
        self._refresh_detail_panel()
        self._refresh_quantum_panel()
        self._refresh_event_panel(frame_time_limit=frame.time)
        self.metric_plot.set_history(self.latest_metrics, up_to_frame=frame.frame_index)
        self.viewer.request_render()

    def _refresh_dimension_visuals(self) -> None:
        frame = self.frames[self.current_index]
        if self.composite_wave_only:
            self.viewer.set_selected_cell(None)
            self.viewer.set_selected_triad(None if not (self.selected_object_id and self.selected_object_id.startswith("triad:")) else self.selected_object_id.split(":", 1)[1])
            self.viewer.set_dimension_history([])
            self.viewer.set_wave_shell_history([])
            self.viewer.set_slice_grid_history([])
            self.dimension_plot.set_history([], None)
            return
        if not self.dimension_mode_enabled or not self.selected_object_id or not self.selected_object_id.startswith("cell:"):
            self.viewer.set_selected_cell(None)
            self.viewer.set_selected_triad(None if not (self.selected_object_id and self.selected_object_id.startswith("triad:")) else self.selected_object_id.split(":", 1)[1])
            self.viewer.set_dimension_history([])
            self.viewer.set_wave_shell_history([])
            self.viewer.set_slice_grid_history([])
            self.dimension_plot.set_history([], None)
            return
        cell_id = self.selected_object_id.split(":", 1)[1]
        if not any(cell.id == cell_id for cell in frame.cells):
            self.viewer.set_selected_cell(None)
            self.viewer.set_selected_triad(None)
            self.viewer.set_dimension_history([])
            self.viewer.set_wave_shell_history([])
            self.viewer.set_slice_grid_history([])
            self.dimension_plot.set_history([], None)
            return
        history = build_dimension_history(self.frames, self.current_index, cell_id)
        wave_shell_history = []
        if self.wave_shell_trails_enabled:
            wave_shell_history = build_wave_shell_history(self.frames, self.current_index, cell_id, history_size=5)
        slice_grid_history = []
        if self.slice_grid_trails_enabled:
            slice_grid_history = build_slice_grid_history(
                self.frames,
                self.current_index,
                sorted(self.viewer.visible_shell_cell_ids),
                history_size=5,
            )
        self.viewer.set_selected_cell(cell_id)
        self.viewer.set_selected_triad(None)
        self.viewer.set_dimension_history(history)
        self.viewer.set_wave_shell_history(wave_shell_history)
        self.viewer.set_slice_grid_history(slice_grid_history)
        self.dimension_plot.set_history(history, cell_id)

    def _refresh_detail_panel(self) -> None:
        frame = self.frames[self.current_index]
        if self.selected_object_id and self.selected_object_id.startswith("cell:"):
            cell_id = self.selected_object_id.split(":", 1)[1]
            cell = next((item for item in frame.cells if item.id == cell_id), None)
            if cell is not None:
                self._show_cell_details(cell)
                return
        if self.selected_object_id and self.selected_object_id.startswith("triad:"):
            triad_id = self.selected_object_id.split(":", 1)[1]
            triad = next((item for item in self.current_triads if item.id == triad_id), None)
            if triad is not None:
                self._show_triad_details(triad)
                return
        if self.selected_object_id and self.selected_object_id.startswith("axis:"):
            axis_id = self.selected_object_id.split(":", 1)[1]
            node = next((item for item in frame.axis_nodes if item.id == axis_id), None)
            if node is not None:
                self._show_axis_details(node)
                return
        self._show_summary_details(frame)

    def _refresh_quantum_panel(self) -> None:
        if not self.current_quantum_report:
            if self.current_quantum_error:
                placeholder = f"Quantum consistency report is not available for this run.\nreason = {self.current_quantum_error}"
            else:
                placeholder = "Quantum consistency report is not available for this run."
            self.quantum_summary_panel.setPlainText(placeholder)
            self.quantum_frame_panel.setPlainText(placeholder)
            self.quantum_triad_panel.setPlainText(placeholder)
            self.quantum_triad_status_label.setText("Selected Triad: none")
            return

        summary = self.current_quantum_report.get("summary", {})
        frame_report = self.current_quantum_frames.get(self.frames[self.current_index].frame_index, {})
        triad_report = None
        selected_triad_id: str | None = None
        if self.selected_object_id and self.selected_object_id.startswith("triad:"):
            triad_id = self.selected_object_id.split(":", 1)[1]
            selected_triad_id = triad_id
            triad_report = next(
                (
                    item
                    for item in frame_report.get("triads", [])
                    if str(item.get("state_id")) == triad_id or str(item.get("state_id")) == f"frame-{self.frames[self.current_index].frame_index}-triad-0"
                ),
                None,
            )
        elif frame_report.get("triads"):
            triad_report = frame_report["triads"][0]

        summary_lines = [
            f"run_id = {self.current_quantum_report.get('run_id', 'unknown')}",
            f"experiment_name = {self.current_quantum_report.get('experiment_name', 'unknown')}",
            f"frame_count = {self.current_quantum_report.get('frame_count', 0)}",
            f"processed_triad_count = {self.current_quantum_report.get('processed_triad_count', 0)}",
            f"dt = {float(self.current_quantum_report.get('dt', 0.0)):.6f}",
            f"  continuity_residual_rms_mean = {float(summary.get('continuity_residual_rms_mean', 0.0)):.6e}",
            f"  continuity_residual_max_abs = {float(summary.get('continuity_residual_max_abs', 0.0)):.6e}",
            f"  hermitian_error_max = {float(summary.get('hermitian_error_max', 0.0)):.6e}",
            f"  eigen_residual_max_abs = {float(summary.get('eigen_residual_max_abs', 0.0)):.6e}",
        ]
        self.quantum_summary_panel.setPlainText("\n".join(summary_lines))

        frame_lines: list[str]
        if frame_report:
            frame_lines = [
                f"frame_index = {frame_report.get('frame_index', self.frames[self.current_index].frame_index)}",
                f"time = {float(frame_report.get('time', self.frames[self.current_index].time)):.6f}",
                f"triad_count = {frame_report.get('triad_count', 0)}",
            ]
            for triad_entry in frame_report.get("triads", []):
                continuity = triad_entry.get("continuity", {})
                spectrum = triad_entry.get("spectrum", {})
                triad_state_id = str(triad_entry.get("state_id", "unknown"))
                frame_lines.extend(
                    [
                        "",
                        "=" * 56,
                        f"Triad: {triad_state_id}",
                        f"  continuity_residual_rms   = {float(continuity.get('residual_rms', 0.0)):.6e}",
                        f"  continuity_residual_max   = {float(continuity.get('residual_max_abs', 0.0)):.6e}",
                        f"  probability_drift_max     = {float(continuity.get('probability_drift_max_abs', 0.0)):.6e}",
                        f"  hermitian_error           = {float(spectrum.get('hermitian_error', 0.0)):.6e}",
                        f"  eigen_residual_max_abs    = {float(spectrum.get('eigen_residual_max_abs', 0.0)):.6e}",
                        f"  eigenvalues               = {spectrum.get('eigenvalues', [])}",
                    ]
                )
        else:
            frame_lines = ["No frame-level quantum data available."]
        self.quantum_frame_panel.setPlainText("\n".join(frame_lines))

        triad_lines: list[str]
        if triad_report is not None:
            continuity = triad_report.get("continuity", {})
            spectrum = triad_report.get("spectrum", {})
            basis_probabilities = triad_report.get("basis_probabilities", {})
            triad_state_id = str(triad_report.get("state_id", "unknown"))
            self.quantum_triad_status_label.setText(f"Selected Triad: {selected_triad_id or triad_state_id}")
            triad_lines = [
                f"state_id = {triad_state_id}",
                f"continuity_residual_rms = {float(continuity.get('residual_rms', 0.0)):.6e}",
                f"continuity_residual_max_abs = {float(continuity.get('residual_max_abs', 0.0)):.6e}",
                f"probability_drift_max_abs = {float(continuity.get('probability_drift_max_abs', 0.0)):.6e}",
                f"hermitian_error = {float(spectrum.get('hermitian_error', 0.0)):.6e}",
                f"orthonormality_error = {float(spectrum.get('orthonormality_error', 0.0)):.6e}",
                f"eigen_residual_max_abs = {float(spectrum.get('eigen_residual_max_abs', 0.0)):.6e}",
                f"eigenvalues = {spectrum.get('eigenvalues', [])}",
                f"basis_probabilities = {basis_probabilities}",
            ]
        else:
            self.quantum_triad_status_label.setText("Selected Triad: none")
            triad_lines = ["No triad is selected for quantum details."]
        self.quantum_triad_panel.setPlainText("\n".join(triad_lines))

    def _show_summary_details(self, frame: FrameState) -> None:
        latest_metric = next((item for item in reversed(self.latest_metrics) if item.frame_index == frame.frame_index), None)
        latest_event_count = len([event for event in self.latest_events if event.time <= frame.time])
        status_line = "status = demo"
        if self.latest_status is not None:
            status_line = f"status = {self.latest_status.status}"
        source_line = f"source = {self.source_dir}" if self.source_dir is not None else "source = demo"
        mode_line = "mode = follow_latest" if self.follow_latest else "mode = manual_review"
        composite_lines: list[str] = []
        if self.viewer.last_composite_info is not None:
            composite_lines = [
                f"composite_can_compose = {self.viewer.last_composite_info['can_compose']}",
                f"composite_coherence = {self.viewer.last_composite_info['coherence_score']:.4f}",
                f"composite_phase_coherence = {self.viewer.last_composite_info['phase_coherence']:.4f}",
                f"composite_spatial_spread = {self.viewer.last_composite_info['spread']:.4f}",
                f"closure_radius = {self.viewer.last_composite_info['closure_radius']:.4f}",
                f"closure_center = {tuple(round(float(v), 4) for v in self.viewer.last_composite_info['closure_center'])}",
                f"closure_source = {self.viewer.last_composite_info['closure_source']}",
                f"closure_phase = {self.viewer.last_composite_info.get('closure_phase', 0.0):.4f}",
                f"topology = {self.viewer.last_composite_info.get('topology', 'unknown')}",
                f"has_common_apex = {self.viewer.last_composite_info.get('has_common_apex', False)}",
                f"split_required = {self.viewer.last_composite_info.get('split_required', False)}",
                f"split_count = {self.viewer.last_composite_info.get('split_count', 0)}",
                f"active_split_count = {self.viewer.last_composite_info.get('active_split_count', 0)}",
                f"topology_state = {self.viewer.last_composite_info.get('topology_state', 'unknown')}",
                f"tensor_origin = {self.viewer.last_composite_info.get('tensor_origin', 'closure_phase')}",
                f"reconnect_ready = {self.viewer.last_composite_info.get('reconnect_ready', False)}",
                f"reconnect_applied = {self.viewer.last_composite_info.get('reconnect_applied', False)}",
                f"reconnect_score = {self.viewer.last_composite_info.get('reconnect_score', 0.0):.4f}",
                f"split_history_count = {self.viewer.last_composite_info.get('split_history_count', 0)}",
                f"phase_shell_bin_size = {self.viewer.last_composite_info.get('phase_shell_bin_size', 0.0):.4f}",
                f"radial_shell_bin_size = {self.viewer.last_composite_info.get('radial_shell_bin_size', 0.0):.4f}",
            ]
        self.detail_panel.setPlainText(
            "\n".join(
                [
                    status_line,
                    source_line,
                    mode_line,
                    f"time = {frame.time:.3f}",
                    f"frame_index = {frame.frame_index}",
                    f"cells = {len(frame.cells)}",
                    f"axis_nodes = {len(frame.axis_nodes)}",
                    f"events_seen = {latest_event_count}",
                    "",
                    f"metrics = {frame.metrics}",
                    f"stream_metrics = {latest_metric.values if latest_metric else {}}",
                    *composite_lines,
                    "",
                    "Select a cell to inspect dimension generation, or an axis node to inspect persistence.",
                ]
            )
        )

    def _show_axis_details(self, node: AxisNodeRecord) -> None:
        self.detail_panel.setPlainText(
            "\n".join(
                [
                    f"id = {node.id}",
                    f"level = {node.level}",
                    f"strength = {node.strength:.3f}",
                    f"persistence = {node.persistence:.3f}",
                    f"center = ({node.center[0]:.3f}, {node.center[1]:.3f}, {node.center[2]:.3f})",
                    f"direction = ({node.direction[0]:.3f}, {node.direction[1]:.3f}, {node.direction[2]:.3f})",
                ]
            )
        )

    def _show_cell_details(self, cell: CellRecord) -> None:
        self.viewer.set_selected_cell(cell.id if self.dimension_mode_enabled else None)
        self.viewer.set_selected_triad(None)
        self.dimension_mode_label.setText(f"selected_cell={cell.id}")
        state, scale = cell_dimension_generation_state(cell)
        tangent_origin = np.asarray(cell.center, dtype=np.float64) + float(scale) * np.asarray(state.n0, dtype=np.float64)
        self.detail_panel.setPlainText(
            "\n".join(
                [
                    f"id = {cell.id}",
                    f"composite_wave_only = {self.composite_wave_only}",
                    f"phase = {cell.phase:.4f}",
                    f"frequency = {cell.frequency:.4f}",
                    f"radius = {cell.radius:.4f}",
                    f"center = ({cell.center[0]:.3f}, {cell.center[1]:.3f}, {cell.center[2]:.3f})",
                    "",
                    "dimension_generation",
                    f"  stage = {state.stage}",
                    f"  alpha = {state.alpha:.4f}",
                    f"  beta = {state.beta:.4f}",
                    f"  tangential_speed = {state.tangential_speed:.4f}",
                    f"  n0_strength = {state.n0_strength:.4f}",
                    f"  n1_strength = {state.n1_strength:.4f}",
                    f"  n2_strength = {state.n2_strength:.4f}",
                    f"  scale = {scale:.4f}",
                    f"  tangent_plane_origin = ({tangent_origin[0]:.4f}, {tangent_origin[1]:.4f}, {tangent_origin[2]:.4f})",
                    "  tangent_plane_normal = n0",
                    "",
                    f"n0 = ({state.n0[0]:.4f}, {state.n0[1]:.4f}, {state.n0[2]:.4f})",
                    f"n1 = ({state.n1[0]:.4f}, {state.n1[1]:.4f}, {state.n1[2]:.4f})",
                    f"n2 = ({state.n2[0]:.4f}, {state.n2[1]:.4f}, {state.n2[2]:.4f})",
                    *(
                        [
                            "",
                            f"composite_can_compose = {self.viewer.last_composite_info['can_compose']}",
                            f"composite_coherence = {self.viewer.last_composite_info['coherence_score']:.4f}",
                            f"closure_radius = {self.viewer.last_composite_info['closure_radius']:.4f}",
                            f"closure_source = {self.viewer.last_composite_info['closure_source']}",
                        ]
                        if self.viewer.last_composite_info is not None
                        else []
                    ),
                ]
            )
        )

    def _show_triad_details(self, triad: TriadRecord) -> None:
        projection = triad.extras.get("projection_cell", {})
        reconnect_report = self.current_reconnect_reports.get(triad.id, {})
        pyramid_summary = next(
            (
                dict(item.get("summary", {}))
                for item in self.viewer.last_pyramid_units
                if str(item.get("id")) == triad.id
            ),
            {},
        )
        geometry_lines: list[str] = []
        if pyramid_summary:
            geometry_lines = [
                f"topology = {pyramid_summary.get('topology', 'unknown')}",
                f"has_common_apex = {pyramid_summary.get('has_common_apex', False)}",
                f"topology_issues = {pyramid_summary.get('topology_issues', [])}",
                f"split_required = {pyramid_summary.get('split_required', False)}",
                f"split_count = {pyramid_summary.get('split_count', 0)}",
                f"active_split_count = {pyramid_summary.get('active_split_count', 0)}",
                f"topology_state = {pyramid_summary.get('topology_state', 'unknown')}",
                f"closure_phase = {pyramid_summary.get('closure_phase', 0.0):.4f}",
            ]
        if reconnect_report:
            geometry_lines.extend(
                [
                    f"tensor_origin = {reconnect_report.get('tensor_origin', 'closure_phase')}",
                    f"lineage_id = {reconnect_report.get('lineage_id', triad.id)}",
                    f"reconnect_ready = {reconnect_report.get('reconnect_ready', False)}",
                    f"reconnect_applied = {reconnect_report.get('reconnect_applied', False)}",
                    f"reconnect_score = {reconnect_report.get('reconnect_score', 0.0):.4f}",
                    f"split_history_count = {reconnect_report.get('split_history_count', 0)}",
                    f"last_split_frame = {reconnect_report.get('last_split_frame', None)}",
                    f"phase_shell_max_abs = {reconnect_report.get('phase_shell_max_abs', 0.0):.4f}",
                    f"radial_shell_spread = {reconnect_report.get('radial_shell_spread', 0.0):.4f}",
                    f"phase_shell_bin_size = {reconnect_report.get('phase_shell_bin_size', 0.0):.4f}",
                    f"radial_shell_bin_size = {reconnect_report.get('radial_shell_bin_size', 0.0):.4f}",
                    f"connector_strength = {reconnect_report.get('connector_strength', 0.0):.4f}",
                    f"connector_strength_threshold = {reconnect_report.get('connector_strength_threshold', 0.0):.4f}",
                ]
            )
        self.detail_panel.setPlainText(
            "\n".join(
                [
                    f"id = {triad.id}",
                    f"cell_ids = {', '.join(triad.cell_ids)}",
                    f"can_compose = {triad.can_compose}",
                    f"coherence_score = {triad.coherence_score:.4f}",
                    f"phase = {triad.phase:.4f}",
                    f"center = ({triad.center[0]:.4f}, {triad.center[1]:.4f}, {triad.center[2]:.4f})",
                    f"closure_center = ({triad.closure_center[0]:.4f}, {triad.closure_center[1]:.4f}, {triad.closure_center[2]:.4f})",
                    f"closure_radius = {triad.closure_radius:.4f}",
                    f"closure_source = {triad.extras.get('closure_source', 'unknown')}",
                    f"phase_coherence = {float(triad.extras.get('phase_coherence', 0.0)):.4f}",
                    f"direction_coherence = {float(triad.extras.get('direction_coherence', 0.0)):.4f}",
                    f"spatial_coherence = {float(triad.extras.get('spatial_coherence', 0.0)):.4f}",
                    f"spread = {float(triad.extras.get('spread', 0.0)):.4f}",
                    "",
                    f"projection_id = {projection.get('id', 'composite-cell')}",
                    f"projection_radius = {float(projection.get('radius', 0.0)):.4f}",
                    f"projection_frequency = {float(projection.get('frequency', 0.0)):.4f}",
                    f"projection_amplitude = {float(projection.get('amplitude', 0.0)):.4f}",
                    *geometry_lines,
                ]
            )
        )

    def _show_node_details(self, object_id: str) -> None:
        self.selected_object_id = object_id
        if object_id.startswith("cell:"):
            cell_id = object_id.split(":", 1)[1]
            self.viewer.set_selected_cell(cell_id if self.dimension_mode_enabled else None)
            self.viewer.set_selected_triad(None)
            self.dimension_mode_label.setText(f"selected_cell={cell_id}")
        elif object_id.startswith("triad:"):
            triad_id = object_id.split(":", 1)[1]
            self.viewer.set_selected_cell(None)
            self.viewer.set_selected_triad(triad_id)
            self.dimension_mode_label.setText(f"selected_triad={triad_id}")
        else:
            self.viewer.set_selected_cell(None)
            self.viewer.set_selected_triad(None)
            self.dimension_mode_label.setText("selected_cell=none")
        self._refresh_detail_panel()
        self._refresh_quantum_panel()
        self._refresh_dimension_visuals()

    def _refresh_event_panel(self, frame_time_limit: float | None = None) -> None:
        self.event_list.clear()
        filtered = self.latest_events
        if frame_time_limit is not None:
            filtered = [event for event in self.latest_events if event.time <= frame_time_limit]
        for event in filtered[-120:]:
            item = QtWidgets.QListWidgetItem(
                f"[t={event.time:.2f}] {event.event_type} | {event.payload}"
            )
            self.event_list.addItem(item)
        if self.event_list.count() > 0:
            self.event_list.scrollToBottom()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CSDE experiment viewer prototype with optional JSONL stream reader")
    parser.add_argument("--stream-dir", type=str, default="", help="read CSDE JSONL/CSV stream from this directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = QtWidgets.QApplication(sys.argv)
    reader = CSDEJsonlReader(args.stream_dir) if args.stream_dir else None
    frames = build_demo_frames() if reader is None else []
    window = MainWindow(frames, reader=reader)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
