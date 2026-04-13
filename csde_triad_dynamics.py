#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np

from csde_data_schema import CellRecord, TriadCoreState


TRIAD_EDGE_PAIRS = ((0, 1), (1, 2), (2, 0))


@dataclass(frozen=True)
class TriadDynamicsConfig:
    phase_coupling: float = 0.42
    phase_bar_coupling: float = 0.24
    phase_edge_coupling: float = 0.18
    connector_phase_coupling: float = 0.30
    freq_relaxation: float = 0.36
    freq_coupling: float = 0.28
    freq_bar_coupling: float = 0.18
    freq_edge_coupling: float = 0.12
    connector_freq_coupling: float = 0.26
    duty_relaxation: float = 0.48
    duty_coupling: float = 0.20
    duty_phase_coupling: float = 0.14
    duty_edge_coupling: float = 0.10
    connector_duty_coupling: float = 0.12
    duty_min: float = 0.05
    duty_max: float = 0.95
    position_spring: float = 0.55
    closure_gain: float = 0.72
    phase_position_gain: float = 0.16
    amplitude_position_gain: float = 0.10
    connector_link_gain: float = 0.36
    velocity_damping: float = 0.52
    axis_velocity_blend: float = 0.35
    axis_phase_blend: float = 0.20
    edge_relaxation: float = 0.30
    edge_drive_gain: float = 0.42
    edge_coherence_gain: float = 0.12
    connector_freq_relaxation: float = 0.32
    connector_phase_gain: float = 0.34
    connector_anchor_gain: float = 0.70
    connector_height_gain: float = 0.45
    connector_velocity_damping: float = 0.48
    connector_strength_relaxation: float = 0.42
    connector_strength_gain: float = 0.32
    sigma_freq: float = 0.20
    sigma_duty: float = 0.20
    rest_distance: float = 1.0
    closure_radius_target: float = 0.92
    spatial_scale: float = 1.0

    def to_params(self) -> dict[str, float]:
        return {key: float(value) for key, value in asdict(self).items()}

    @classmethod
    def from_params(cls, params: dict[str, float] | None = None) -> "TriadDynamicsConfig":
        if not params:
            return cls()
        defaults = cls().to_params()
        defaults.update({key: float(value) for key, value in params.items()})
        return cls(**defaults)


def triad_dynamics_default_params() -> dict[str, float]:
    return TriadDynamicsConfig().to_params()


def circular_mean_phase(phases: list[float]) -> tuple[float, float]:
    if not phases:
        return 0.0, 0.0
    vectors = np.exp(1j * np.asarray(phases, dtype=np.float64))
    mean_vec = np.mean(vectors)
    return float(np.angle(mean_vec)), float(abs(mean_vec))


def _triad_edge_complex(state: TriadCoreState) -> np.ndarray:
    real = np.asarray(state.edge_state_real, dtype=np.float64)
    imag = np.asarray(state.edge_state_imag, dtype=np.float64)
    if real.shape != (3,) or imag.shape != (3,):
        raise ValueError("TriadCoreState edge_state_real/imag must both have length 3.")
    return real + 1j * imag


def _triad_edge_lookup(edge_values: np.ndarray) -> dict[tuple[int, int], complex]:
    lookup: dict[tuple[int, int], complex] = {}
    for value, (i, j) in zip(edge_values, TRIAD_EDGE_PAIRS):
        lookup[(i, j)] = complex(value)
        lookup[(j, i)] = complex(np.conjugate(value))
    return lookup


def _triad_default_axis(index: int) -> np.ndarray:
    defaults = [
        np.array([1.0, 0.0, 0.0], dtype=np.float64),
        np.array([0.0, 1.0, 0.0], dtype=np.float64),
        np.array([0.0, 0.0, 1.0], dtype=np.float64),
    ]
    return defaults[index]


def _triangle_normal(points: np.ndarray) -> np.ndarray:
    if points.shape != (3, 3):
        raise ValueError("triangle points must have shape (3, 3)")
    ab = points[1] - points[0]
    ac = points[2] - points[0]
    normal = np.cross(ab, ac)
    norm = float(np.linalg.norm(normal))
    if norm < 1e-8:
        return np.array([0.0, 0.0, 1.0], dtype=np.float64)
    return normal / norm


def circumcenter_3d(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray | None:
    ab = b - a
    ac = c - a
    normal = np.cross(ab, ac)
    normal_norm_sq = float(np.dot(normal, normal))
    if normal_norm_sq < 1e-8:
        return None
    term1 = np.cross(normal, ab) * float(np.dot(ac, ac))
    term2 = np.cross(ac, normal) * float(np.dot(ab, ab))
    center = a + (term1 + term2) / (2.0 * normal_norm_sq)
    return center.astype(np.float32)


def pair_enclosing_sphere_center(c0: np.ndarray, r0: float, c1: np.ndarray, r1: float) -> np.ndarray:
    delta = c1 - c0
    distance = float(np.linalg.norm(delta))
    if distance < 1e-8:
        return c0.astype(np.float32)
    if r0 >= distance + r1:
        return c0.astype(np.float32)
    if r1 >= distance + r0:
        return c1.astype(np.float32)
    radius = 0.5 * (distance + r0 + r1)
    t = (radius - r0) / distance
    return (c0 + t * delta).astype(np.float32)


def closure_radius_for_center(center: np.ndarray, centers: list[np.ndarray], radii: list[float]) -> float:
    return max(float(np.linalg.norm(center - point)) + float(radius) for point, radius in zip(centers, radii))


def minimum_closure_sphere(centers: list[np.ndarray], radii: list[float]) -> tuple[np.ndarray, float, str]:
    candidates: list[tuple[np.ndarray, str]] = []
    for idx, center in enumerate(centers):
        candidates.append((center.astype(np.float32), f"single:{idx}"))
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            pair_center = pair_enclosing_sphere_center(centers[i], radii[i], centers[j], radii[j])
            candidates.append((pair_center, f"pair:{i}-{j}"))
    if len(centers) == 3:
        circumcenter = circumcenter_3d(centers[0], centers[1], centers[2])
        if circumcenter is not None:
            candidates.append((circumcenter, "circumcenter"))
    mean_center = np.mean(np.asarray(centers, dtype=np.float32), axis=0)
    candidates.append((mean_center.astype(np.float32), "mean"))

    best_center = candidates[0][0]
    best_radius = closure_radius_for_center(best_center, centers, radii)
    best_source = candidates[0][1]
    for center, source in candidates[1:]:
        radius = closure_radius_for_center(center, centers, radii)
        if radius < best_radius:
            best_center = center
            best_radius = radius
            best_source = source
    return best_center.astype(np.float32), float(best_radius), best_source


def _cell_primary_axis(cell: CellRecord) -> np.ndarray:
    local_frame = cell.extras.get("local_frame", {}) if isinstance(cell.extras, dict) else {}
    axis = np.asarray(local_frame.get("n0", [1.0, 0.0, 0.0]), dtype=np.float64)
    norm = float(np.linalg.norm(axis))
    if norm < 1e-8:
        return np.array([1.0, 0.0, 0.0], dtype=np.float64)
    return axis / norm


def build_triad_core_state_from_cells(
    cells: list[CellRecord],
    triad_id: str = "triad-0",
    *,
    connector_strength: float | None = None,
) -> TriadCoreState:
    if len(cells) != 3:
        raise ValueError("build_triad_core_state_from_cells requires exactly 3 cells.")

    node_position = [list(np.asarray(cell.center, dtype=np.float64)) for cell in cells]
    node_phase = [float(cell.phase) for cell in cells]
    node_freq = [float(cell.frequency) for cell in cells]
    node_duty = [float(np.clip(cell.amplitude, 0.0, 1.0)) for cell in cells]
    node_axis = [_cell_primary_axis(cell).tolist() for cell in cells]
    node_velocity = [list(np.zeros(3, dtype=np.float64)) for _ in cells]

    centers = [np.asarray(cell.center, dtype=np.float32) for cell in cells]
    closure_center, closure_radius, closure_source = minimum_closure_sphere(centers, [0.0, 0.0, 0.0])
    base_points = np.asarray(node_position, dtype=np.float64)
    base_normal = _triangle_normal(base_points)
    connector_height = max(0.45 * float(closure_radius), 0.12)
    connector_position = (np.mean(base_points, axis=0) + connector_height * base_normal).astype(np.float64)
    connector_phase, phase_coherence = circular_mean_phase(node_phase)

    base_edge_strength = float(np.mean(node_duty))
    edge_values = []
    for i, j in TRIAD_EDGE_PAIRS:
        phase_alignment = np.exp(1j * (node_phase[j] - node_phase[i]))
        edge_values.append(base_edge_strength * phase_alignment)
    edge_values_np = np.asarray(edge_values, dtype=np.complex128)

    return TriadCoreState(
        id=triad_id,
        node_duty=node_duty,
        node_freq=node_freq,
        node_phase=node_phase,
        node_position=node_position,
        node_velocity=node_velocity,
        node_axis=node_axis,
        edge_state_real=np.real(edge_values_np).astype(np.float64).tolist(),
        edge_state_imag=np.imag(edge_values_np).astype(np.float64).tolist(),
        connector_position=connector_position.astype(np.float64).tolist(),
        connector_velocity=np.zeros(3, dtype=np.float64).tolist(),
        connector_phase=float(connector_phase),
        connector_freq=float(np.mean(node_freq)),
        connector_strength=float(connector_strength if connector_strength is not None else phase_coherence),
        active=all(cell.active for cell in cells),
        extras={
            "base_freq": node_freq,
            "base_duty": node_duty,
            "closure_center": closure_center.astype(np.float64).tolist(),
            "closure_radius": float(closure_radius),
            "closure_source": closure_source,
            "source_cell_ids": [cell.id for cell in cells],
        },
    )


def summarize_triad_core_state(
    state: TriadCoreState,
    diagnostics: dict[str, object] | None = None,
) -> dict[str, object]:
    edge_values = _triad_edge_complex(state)
    closure_center, closure_radius, closure_source = minimum_closure_sphere(
        [np.asarray(point, dtype=np.float32) for point in state.node_position],
        [0.0, 0.0, 0.0],
    )
    phi_bar, phase_coherence = circular_mean_phase([float(value) for value in state.node_phase])
    return {
        "triad_id": state.id,
        "phase_bar": float(diagnostics["phase_bar"]) if diagnostics and "phase_bar" in diagnostics else float(phi_bar),
        "phase_coherence": float(diagnostics["phase_coherence"]) if diagnostics and "phase_coherence" in diagnostics else float(phase_coherence),
        "connector_phase": float(state.connector_phase),
        "connector_freq": float(state.connector_freq),
        "connector_strength": float(state.connector_strength),
        "closure_center": closure_center.astype(np.float64).tolist(),
        "closure_radius": float(closure_radius),
        "closure_source": closure_source,
        "edge_magnitude_mean": float(np.mean(np.abs(edge_values))),
        "duty_mean": float(np.mean(np.asarray(state.node_duty, dtype=np.float64))),
        "freq_mean": float(np.mean(np.asarray(state.node_freq, dtype=np.float64))),
    }


def simulate_triad_core(
    initial_state: TriadCoreState,
    step_count: int,
    dt: float,
    params: dict[str, float] | TriadDynamicsConfig | None = None,
) -> tuple[list[TriadCoreState], list[dict[str, object]]]:
    if step_count < 0:
        raise ValueError("step_count must be non-negative.")
    if isinstance(params, TriadDynamicsConfig):
        param_dict = params.to_params()
    else:
        param_dict = TriadDynamicsConfig.from_params(params).to_params()

    states = [initial_state]
    diagnostics_history: list[dict[str, object]] = []
    current_state = initial_state
    for _ in range(step_count):
        current_state, diagnostics = triad_core_step(current_state, dt, params=param_dict)
        states.append(current_state)
        diagnostics_history.append(diagnostics)
    return states, diagnostics_history


def triad_core_step(
    state: TriadCoreState,
    dt: float,
    params: dict[str, float] | None = None,
) -> tuple[TriadCoreState, dict[str, object]]:
    if dt <= 0.0:
        raise ValueError("dt must be positive.")
    if not (
        len(state.node_duty) == len(state.node_freq) == len(state.node_phase) == 3
        and len(state.node_position) == len(state.node_velocity) == len(state.node_axis) == 3
    ):
        raise ValueError("TriadCoreState must contain exactly three node states.")

    cfg = TriadDynamicsConfig.from_params(params).to_params()

    duty = np.asarray(state.node_duty, dtype=np.float64)
    freq = np.asarray(state.node_freq, dtype=np.float64)
    phase = np.asarray(state.node_phase, dtype=np.float64)
    position = np.asarray(state.node_position, dtype=np.float64)
    velocity = np.asarray(state.node_velocity, dtype=np.float64)
    axis = np.asarray(state.node_axis, dtype=np.float64)
    for idx in range(3):
        norm = float(np.linalg.norm(axis[idx]))
        axis[idx] = _triad_default_axis(idx) if norm < 1e-8 else axis[idx] / norm

    base_freq = np.asarray(state.extras.get("base_freq", state.node_freq), dtype=np.float64)
    base_duty = np.asarray(state.extras.get("base_duty", state.node_duty), dtype=np.float64)
    if base_freq.shape != (3,):
        base_freq = freq.copy()
    if base_duty.shape != (3,):
        base_duty = duty.copy()

    edge_values = _triad_edge_complex(state)
    edge_lookup = _triad_edge_lookup(edge_values)

    phi_bar, phase_coherence = circular_mean_phase(phase.tolist())
    omega_bar = float(np.mean(freq))
    duty_bar = float(np.mean(duty))
    edge_strength = np.abs(edge_values)
    edge_coherence = float(np.mean(edge_strength / (1.0 + edge_strength)))

    closure_center, closure_radius, closure_source = minimum_closure_sphere(
        [position[i].astype(np.float32) for i in range(3)],
        [0.0, 0.0, 0.0],
    )
    spread = float(np.mean([np.linalg.norm(position[i] - closure_center) for i in range(3)]))
    spatial_coherence = 1.0 / (1.0 + spread / max(cfg["spatial_scale"], 1e-6))
    coherence_score = 0.50 * phase_coherence + 0.30 * edge_coherence + 0.20 * spatial_coherence

    base_center = np.mean(position, axis=0)
    base_normal = _triangle_normal(position)
    mean_axis = np.mean(axis, axis=0)
    mean_axis_norm = float(np.linalg.norm(mean_axis))
    if mean_axis_norm > 1e-8 and float(np.dot(base_normal, mean_axis)) < 0.0:
        base_normal = -base_normal
    elif mean_axis_norm < 1e-8:
        mean_axis = base_normal
    connector_target_height = max(cfg["closure_radius_target"], 0.45 * closure_radius)
    if len(state.connector_position) == 3:
        connector_position = np.asarray(state.connector_position, dtype=np.float64)
    else:
        connector_position = base_center + connector_target_height * base_normal
    if len(state.connector_velocity) == 3:
        connector_velocity = np.asarray(state.connector_velocity, dtype=np.float64)
    else:
        connector_velocity = np.zeros(3, dtype=np.float64)
    connector_phase = float(state.connector_phase if state.connector_phase else phi_bar)
    connector_freq = float(state.connector_freq if state.connector_freq else omega_bar)
    connector_strength = float(state.connector_strength if state.connector_strength else coherence_score)

    dphi = np.zeros(3, dtype=np.float64)
    domega = np.zeros(3, dtype=np.float64)
    dduty = np.zeros(3, dtype=np.float64)
    dvel = np.zeros((3, 3), dtype=np.float64)
    new_axis = axis.copy()

    for i in range(3):
        j, k = [idx for idx in range(3) if idx != i]
        edge_sum = (
            edge_lookup[(i, j)] * np.exp(1j * (phase[j] - phase[i]))
            + edge_lookup[(i, k)] * np.exp(1j * (phase[k] - phase[i]))
        )
        pair_phase_sum = math.sin(phase[j] - phase[i]) + math.sin(phase[k] - phase[i])
        pair_cos_sum = math.cos(phase[j] - phase[i]) + math.cos(phase[k] - phase[i])

        dphi[i] = (
            freq[i]
            + cfg["phase_coupling"] * pair_phase_sum
            + cfg["phase_bar_coupling"] * math.sin(phi_bar - phase[i])
            + cfg["phase_edge_coupling"] * float(np.imag(edge_sum))
            + cfg["connector_phase_coupling"] * connector_strength * math.sin(connector_phase - phase[i])
        )

        domega[i] = (
            -cfg["freq_relaxation"] * (freq[i] - base_freq[i])
            + cfg["freq_coupling"] * ((freq[j] - freq[i]) + (freq[k] - freq[i]))
            + cfg["freq_bar_coupling"] * (omega_bar - freq[i])
            + cfg["freq_edge_coupling"] * float(np.real(edge_sum))
            + cfg["connector_freq_coupling"] * connector_strength * (connector_freq - freq[i])
        )

        dduty[i] = (
            cfg["duty_relaxation"] * (base_duty[i] - duty[i])
            + cfg["duty_coupling"] * ((duty[j] - duty[i]) + (duty[k] - duty[i]))
            + cfg["duty_phase_coupling"] * pair_cos_sum
            + cfg["duty_edge_coupling"] * float(np.real(edge_sum))
            + 0.08 * coherence_score * (duty_bar - duty[i])
            + cfg["connector_duty_coupling"] * connector_strength * (duty_bar - duty[i])
        )

        for neighbor in (j, k):
            delta = position[neighbor] - position[i]
            distance = float(np.linalg.norm(delta))
            if distance < 1e-8:
                continue
            direction = delta / distance
            dvel[i] += cfg["position_spring"] * (distance - cfg["rest_distance"]) * direction
            dvel[i] += cfg["phase_position_gain"] * math.sin(phase[neighbor] - phase[i]) * direction
            dvel[i] += cfg["amplitude_position_gain"] * (duty[neighbor] - duty[i]) * direction

        radial = position[i] - closure_center
        radial_norm = float(np.linalg.norm(radial))
        if radial_norm < 1e-8:
            radial = axis[i]
            radial_norm = max(float(np.linalg.norm(radial)), 1e-8)
        radial_dir = radial / radial_norm
        dvel[i] += -cfg["closure_gain"] * (radial_norm - cfg["closure_radius_target"]) * radial_dir
        connector_delta = connector_position - position[i]
        connector_distance = float(np.linalg.norm(connector_delta))
        if connector_distance > 1e-8:
            connector_dir = connector_delta / connector_distance
            dvel[i] += cfg["connector_link_gain"] * connector_strength * connector_dir
        dvel[i] += -cfg["velocity_damping"] * velocity[i]

        velocity_hint = velocity[i] + dt * dvel[i]
        if float(np.linalg.norm(velocity_hint)) > 1e-6:
            velocity_axis = velocity_hint / max(float(np.linalg.norm(velocity_hint)), 1e-8)
        else:
            velocity_axis = axis[i]
        phase_axis = (
            math.cos(phase[i]) * axis[i]
            + math.sin(phase[i]) * np.cross(radial_dir, axis[i])
        )
        axis_mix = (
            (1.0 - cfg["axis_velocity_blend"] - cfg["axis_phase_blend"]) * axis[i]
            + cfg["axis_velocity_blend"] * velocity_axis
            + cfg["axis_phase_blend"] * phase_axis
        )
        axis_norm = float(np.linalg.norm(axis_mix))
        new_axis[i] = axis[i] if axis_norm < 1e-8 else axis_mix / axis_norm

    connector_target_position = base_center + connector_target_height * base_normal
    dconnector_phase = (
        connector_freq
        + cfg["connector_phase_gain"] * sum(math.sin(phase[i] - connector_phase) for i in range(3))
    )
    dconnector_freq = (
        -cfg["connector_freq_relaxation"] * (connector_freq - omega_bar)
        + cfg["connector_freq_coupling"] * sum(freq[i] - connector_freq for i in range(3)) / 3.0
    )
    dconnector_strength = (
        -cfg["connector_strength_relaxation"] * (connector_strength - coherence_score)
        + cfg["connector_strength_gain"] * (phase_coherence + edge_coherence + spatial_coherence - 3.0 * connector_strength / max(connector_strength + 1e-8, 1.0))
    )
    dconnector_velocity = (
        cfg["connector_anchor_gain"] * (connector_target_position - connector_position)
        + cfg["connector_height_gain"] * connector_strength * base_normal
        - cfg["connector_velocity_damping"] * connector_velocity
    )

    new_phase = phase + dt * dphi
    new_freq = np.clip(freq + dt * domega, 0.01, None)
    new_duty = np.clip(duty + dt * dduty, cfg["duty_min"], cfg["duty_max"])
    new_velocity = velocity + dt * dvel
    new_position = position + dt * new_velocity
    new_connector_phase = connector_phase + dt * dconnector_phase
    new_connector_freq = max(0.01, connector_freq + dt * dconnector_freq)
    new_connector_strength = float(np.clip(connector_strength + dt * dconnector_strength, 0.0, 1.5))
    new_connector_velocity = connector_velocity + dt * dconnector_velocity
    new_connector_position = connector_position + dt * new_connector_velocity

    new_edge_values = edge_values.astype(np.complex128).copy()
    for edge_idx, (i, j) in enumerate(TRIAD_EDGE_PAIRS):
        freq_match = math.exp(-abs(new_freq[i] - new_freq[j]) / max(cfg["sigma_freq"], 1e-6))
        duty_match = math.exp(-abs(new_duty[i] - new_duty[j]) / max(cfg["sigma_duty"], 1e-6))
        phase_alignment = np.exp(1j * (new_phase[j] - new_phase[i]))
        rest_edge = complex(edge_values[edge_idx])
        target_edge = (cfg["edge_drive_gain"] * freq_match * duty_match + cfg["edge_coherence_gain"] * coherence_score) * phase_alignment
        dz = -cfg["edge_relaxation"] * (new_edge_values[edge_idx] - rest_edge) + target_edge
        new_edge_values[edge_idx] = new_edge_values[edge_idx] + dt * dz

    next_state = TriadCoreState(
        id=state.id,
        node_duty=new_duty.astype(np.float64).tolist(),
        node_freq=new_freq.astype(np.float64).tolist(),
        node_phase=new_phase.astype(np.float64).tolist(),
        node_position=new_position.astype(np.float64).tolist(),
        node_velocity=new_velocity.astype(np.float64).tolist(),
        node_axis=new_axis.astype(np.float64).tolist(),
        edge_state_real=np.real(new_edge_values).astype(np.float64).tolist(),
        edge_state_imag=np.imag(new_edge_values).astype(np.float64).tolist(),
        connector_position=new_connector_position.astype(np.float64).tolist(),
        connector_velocity=new_connector_velocity.astype(np.float64).tolist(),
        connector_phase=float(new_connector_phase),
        connector_freq=float(new_connector_freq),
        connector_strength=float(new_connector_strength),
        active=state.active,
        extras={
            **(state.extras if isinstance(state.extras, dict) else {}),
            "base_freq": base_freq.astype(np.float64).tolist(),
            "base_duty": base_duty.astype(np.float64).tolist(),
        },
    )

    diagnostics = {
        "phase_bar": float(phi_bar),
        "omega_bar": float(omega_bar),
        "duty_bar": float(duty_bar),
        "phase_coherence": float(phase_coherence),
        "edge_coherence": float(edge_coherence),
        "spatial_coherence": float(spatial_coherence),
        "coherence_score": float(coherence_score),
        "closure_center": closure_center.astype(np.float64).tolist(),
        "closure_radius": float(closure_radius),
        "closure_source": closure_source,
        "connector_target_position": connector_target_position.astype(np.float64).tolist(),
        "connector_position": new_connector_position.astype(np.float64).tolist(),
        "connector_phase": float(new_connector_phase),
        "connector_freq": float(new_connector_freq),
        "connector_strength": float(new_connector_strength),
        "edge_complex": [complex(value) for value in new_edge_values],
    }
    return next_state, diagnostics
