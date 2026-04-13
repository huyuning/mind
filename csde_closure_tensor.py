#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Callable

import numpy as np

from csde_data_schema import FrameState


def wrap_phase_delta(phase: float, origin: float) -> float:
    return float(math.atan2(math.sin(phase - origin), math.cos(phase - origin)))


def compute_closure_phase_shells(
    node_phases: list[float],
    base_points: np.ndarray,
    closure_phase: float,
    closure_center: np.ndarray,
) -> tuple[list[float], list[float]]:
    phase_shells = [wrap_phase_delta(float(phase), float(closure_phase)) for phase in node_phases]
    radial_shells = [
        float(np.linalg.norm(np.asarray(point, dtype=np.float32) - np.asarray(closure_center, dtype=np.float32)))
        for point in base_points
    ]
    return phase_shells, radial_shells


@dataclass(frozen=True)
class ClosureTensorLayout:
    origin: str = "closure_phase"
    time_bin_size: int = 1
    phase_shell_bin_size: float = 0.125
    radial_shell_bin_size: float = 0.125
    phase_tolerance: float = 0.28
    radial_tolerance: float = 0.22
    connector_strength_threshold: float = 0.5
    min_history_splits: int = 1

    def to_dict(self) -> dict[str, object]:
        return dict(asdict(self))


def _quantile_summary(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0.0, "min": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p90": 0.0, "p95": 0.0, "max": 0.0}
    array = np.asarray(values, dtype=np.float64)
    return {
        "count": float(array.size),
        "min": float(np.min(array)),
        "p25": float(np.quantile(array, 0.25)),
        "p50": float(np.quantile(array, 0.50)),
        "p75": float(np.quantile(array, 0.75)),
        "p90": float(np.quantile(array, 0.90)),
        "p95": float(np.quantile(array, 0.95)),
        "max": float(np.max(array)),
    }


def build_closure_phase_tensor_snapshot(
    frame_index: int,
    time_value: float,
    pyramid_units: list[dict[str, object]],
) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for pyramid in pyramid_units:
        split_cells = list(pyramid.get("split_cells", []))
        entries.append(
            {
                "frame_index": int(frame_index),
                "time": float(time_value),
                "triad_id": str(pyramid["id"]),
                "lineage_id": str(pyramid.get("lineage_id", pyramid["id"])),
                "closure_phase": float(pyramid.get("closure_phase", pyramid["phase"])),
                "closure_center": np.asarray(pyramid["base_center"], dtype=np.float32).tolist(),
                "phase_shells": [float(value) for value in pyramid.get("phase_shells", [])],
                "radial_shells": [float(value) for value in pyramid.get("radial_shells", [])],
                "connector_strength": float(pyramid["connector_strength"]),
                "topology": str(pyramid["geometry"]["topology"]),
                "has_common_apex": bool(pyramid["geometry"]["has_common_apex"]),
                "split_required": bool(split_cells),
                "split_count": len(split_cells),
            }
        )
    return entries


def build_closure_phase_tensor(
    frames: list[FrameState],
    current_index: int,
    frame_to_pyramid_units: Callable[[FrameState], list[dict[str, object]]],
    history_size: int = 48,
) -> dict[str, object]:
    if not frames:
        return {"origin": "closure_phase", "entries": [], "by_lineage": {}}
    start_index = max(0, current_index - history_size + 1)
    entries: list[dict[str, object]] = []
    by_lineage: dict[str, list[dict[str, object]]] = {}
    for frame in frames[start_index : current_index + 1]:
        pyramid_units = frame_to_pyramid_units(frame)
        snapshot = build_closure_phase_tensor_snapshot(frame.frame_index, frame.time, pyramid_units)
        entries.extend(snapshot)
        for entry in snapshot:
            by_lineage.setdefault(str(entry["lineage_id"]), []).append(entry)
    return {
        "origin": "closure_phase",
        "entries": entries,
        "by_lineage": by_lineage,
    }


def survey_closure_tensor_statistics(
    frames: list[FrameState],
    frame_to_pyramid_units: Callable[[FrameState], list[dict[str, object]]],
    history_size: int | None = None,
) -> dict[str, object]:
    if not frames:
        return {
            "origin": "closure_phase",
            "frame_count": 0,
            "entry_count": 0,
            "phase_shell_abs": _quantile_summary([]),
            "radial_shell": _quantile_summary([]),
            "radial_spread": _quantile_summary([]),
            "connector_strength": _quantile_summary([]),
            "time_delta": _quantile_summary([]),
            "split_ratio": 0.0,
            "topology_histogram": {},
        }

    target_frames = frames[-history_size:] if history_size is not None and history_size > 0 else frames
    phase_shell_abs_values: list[float] = []
    radial_shell_values: list[float] = []
    radial_spread_values: list[float] = []
    connector_strength_values: list[float] = []
    split_flags: list[float] = []
    topology_histogram: dict[str, int] = {}
    entries = 0

    time_values = [float(frame.time) for frame in target_frames]
    time_deltas = [time_values[idx + 1] - time_values[idx] for idx in range(len(time_values) - 1)]

    for frame in target_frames:
        pyramid_units = frame_to_pyramid_units(frame)
        for pyramid in pyramid_units:
            phase_shells = [abs(float(value)) for value in pyramid.get("phase_shells", [])]
            radial_shells = [float(value) for value in pyramid.get("radial_shells", [])]
            phase_shell_abs_values.extend(phase_shells)
            radial_shell_values.extend(radial_shells)
            if radial_shells:
                radial_spread_values.append(max(radial_shells) - min(radial_shells))
            connector_strength_values.append(float(pyramid.get("connector_strength", 0.0)))
            split_flags.append(1.0 if pyramid.get("split_cells") else 0.0)
            topology = str(pyramid.get("geometry", {}).get("topology", "unknown"))
            topology_histogram[topology] = topology_histogram.get(topology, 0) + 1
            entries += 1

    return {
        "origin": "closure_phase",
        "frame_count": len(target_frames),
        "entry_count": entries,
        "phase_shell_abs": _quantile_summary(phase_shell_abs_values),
        "radial_shell": _quantile_summary(radial_shell_values),
        "radial_spread": _quantile_summary(radial_spread_values),
        "connector_strength": _quantile_summary(connector_strength_values),
        "time_delta": _quantile_summary(time_deltas),
        "split_ratio": float(np.mean(split_flags)) if split_flags else 0.0,
        "topology_histogram": topology_histogram,
    }


def infer_closure_tensor_layout(
    statistics: dict[str, object],
    *,
    phase_shell_bins: int = 24,
    radial_shell_bins: int = 16,
) -> ClosureTensorLayout:
    phase_stats = statistics.get("phase_shell_abs", {})
    radial_stats = statistics.get("radial_shell", {})
    radial_spread_stats = statistics.get("radial_spread", {})
    connector_stats = statistics.get("connector_strength", {})
    time_stats = statistics.get("time_delta", {})

    phase_p95 = float(phase_stats.get("p95", 0.5))
    radial_p95 = float(radial_stats.get("p95", 0.5))
    radial_spread_p50 = float(radial_spread_stats.get("p50", 0.22))
    connector_p50 = float(connector_stats.get("p50", 0.5))

    phase_bin_size = max(phase_p95 / max(phase_shell_bins - 1, 1), 1e-3)
    radial_bin_size = max(radial_p95 / max(radial_shell_bins - 1, 1), 1e-3)
    phase_tolerance = max(float(phase_stats.get("p25", phase_p95 * 0.35)), phase_bin_size * 2.0)
    radial_tolerance = max(radial_spread_p50, radial_bin_size * 1.5)
    connector_threshold = max(min(connector_p50, 1.0), 0.15)
    time_bin_size = max(1, int(round(float(time_stats.get("p50", 1.0)) / max(float(time_stats.get("min", 1.0)), 1e-6)))) if float(time_stats.get("count", 0.0)) > 0 else 1

    return ClosureTensorLayout(
        origin="closure_phase",
        time_bin_size=time_bin_size,
        phase_shell_bin_size=float(phase_bin_size),
        radial_shell_bin_size=float(radial_bin_size),
        phase_tolerance=float(phase_tolerance),
        radial_tolerance=float(radial_tolerance),
        connector_strength_threshold=float(connector_threshold),
        min_history_splits=1,
    )


def build_bucketized_closure_tensor_index(
    tensor: dict[str, object],
    layout: ClosureTensorLayout,
) -> dict[str, object]:
    buckets: dict[tuple[int, int, int], list[dict[str, object]]] = {}
    for entry in tensor.get("entries", []):
        time_bucket = int(entry["frame_index"]) // max(layout.time_bin_size, 1)
        phase_shells = [abs(float(value)) for value in entry.get("phase_shells", [])]
        radial_shells = [float(value) for value in entry.get("radial_shells", [])]
        for node_index, (phase_shell, radial_shell) in enumerate(zip(phase_shells, radial_shells)):
            phase_bucket = int(math.floor(phase_shell / max(layout.phase_shell_bin_size, 1e-6)))
            radial_bucket = int(math.floor(radial_shell / max(layout.radial_shell_bin_size, 1e-6)))
            bucket_key = (time_bucket, phase_bucket, radial_bucket)
            buckets.setdefault(bucket_key, []).append(
                {
                    "triad_id": entry["triad_id"],
                    "lineage_id": entry["lineage_id"],
                    "frame_index": entry["frame_index"],
                    "node_index": node_index,
                    "phase_shell": float(phase_shell),
                    "radial_shell": float(radial_shell),
                    "connector_strength": float(entry.get("connector_strength", 0.0)),
                    "split_required": bool(entry.get("split_required", False)),
                    "has_common_apex": bool(entry.get("has_common_apex", False)),
                    "topology": entry.get("topology", "unknown"),
                }
            )
    return {
        "origin": layout.origin,
        "layout": layout.to_dict(),
        "bucket_count": len(buckets),
        "buckets": buckets,
    }


def query_reconnect_candidates(
    tensor: dict[str, object],
    pyramid: dict[str, object],
    *,
    phase_tolerance: float = 0.28,
    radial_tolerance: float = 0.22,
    connector_strength_threshold: float = 0.0,
    min_history_splits: int = 1,
) -> dict[str, object]:
    lineage_id = str(pyramid.get("lineage_id", pyramid["id"]))
    lineage_entries = list(tensor.get("by_lineage", {}).get(lineage_id, []))
    if not lineage_entries:
        return {
            "tensor_origin": tensor.get("origin", "closure_phase"),
            "lineage_id": lineage_id,
            "reconnect_ready": False,
            "reconnect_score": 0.0,
            "split_history_count": 0,
            "last_split_frame": None,
        }
    current_frame_index = max(int(entry["frame_index"]) for entry in lineage_entries)
    previous_split_entries = [
        entry
        for entry in lineage_entries
        if bool(entry.get("split_required")) and int(entry["frame_index"]) < current_frame_index
    ]
    current_phase_shells = [abs(float(value)) for value in pyramid.get("phase_shells", [])]
    current_radial_shells = [float(value) for value in pyramid.get("radial_shells", [])]
    radial_spread = (
        max(current_radial_shells) - min(current_radial_shells)
        if current_radial_shells
        else float("inf")
    )
    phase_alignment = 1.0 - min(1.0, max(current_phase_shells, default=math.pi) / max(phase_tolerance, 1e-6))
    radial_alignment = 1.0 - min(1.0, radial_spread / max(radial_tolerance, 1e-6))
    topology_alignment = 1.0 if bool(pyramid["geometry"]["has_common_apex"]) else 0.0
    connector_strength = float(pyramid.get("connector_strength", 0.0))
    connector_alignment = 1.0 if connector_strength >= connector_strength_threshold else 0.0
    reconnect_score = max(0.0, 0.35 * phase_alignment + 0.25 * radial_alignment + 0.20 * topology_alignment + 0.20 * connector_alignment)
    reconnect_ready = bool(
        len(previous_split_entries) >= min_history_splits
        and bool(pyramid["geometry"]["has_common_apex"])
        and max(current_phase_shells, default=math.pi) <= phase_tolerance
        and radial_spread <= radial_tolerance
        and connector_strength >= connector_strength_threshold
    )
    last_split_frame = previous_split_entries[-1]["frame_index"] if previous_split_entries else None
    return {
        "tensor_origin": tensor.get("origin", "closure_phase"),
        "lineage_id": lineage_id,
        "reconnect_ready": reconnect_ready,
        "reconnect_score": float(reconnect_score),
        "split_history_count": len(previous_split_entries),
        "last_split_frame": last_split_frame,
        "phase_shell_max_abs": float(max(current_phase_shells, default=0.0)),
        "radial_shell_spread": float(radial_spread if math.isfinite(radial_spread) else 0.0),
        "connector_strength": connector_strength,
    }
