#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Sequence

import hydrogen_coaxial_axis_emergence as axis_emergence
from csde_quantum_validation import wrap_runner_with_quantum_post_validation


Runner = Callable[[SimpleNamespace], tuple[Path, Dict[str, Any]]]


@dataclass(frozen=True)
class ScanAxisSpec:
    name: str
    default_values: Sequence[float]
    description: str


@dataclass(frozen=True)
class MetricSpec:
    name: str
    objective: str
    description: str
    unit: str = "arb."


@dataclass(frozen=True)
class ExperimentDefinition:
    name: str
    description: str
    runner: Runner
    default_namespace: Dict[str, Any]
    scan_axes: Sequence[ScanAxisSpec]
    metric_names: Sequence[str]

    def build_namespace(self, overrides: Dict[str, Any] | None = None) -> SimpleNamespace:
        payload = dict(self.default_namespace)
        if overrides:
            payload.update(overrides)
        return SimpleNamespace(**payload)


def load_metric_schema(schema_path: Path | None = None) -> Dict[str, MetricSpec]:
    path = schema_path or Path(__file__).with_name("csde_metric_schema.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    metrics = {}
    for item in payload.get("metrics", []):
        metrics[item["name"]] = MetricSpec(
            name=item["name"],
            objective=item["objective"],
            description=item["description"],
            unit=item.get("unit", "arb."),
        )
    return metrics


def hydrogen_coaxial_default_namespace() -> Dict[str, Any]:
    return {
        "duration": 14.0,
        "dt": 0.04,
        "stream_write": True,
        "stream_every": 1,
        "proton_radius": 1.2,
        "phase_threshold": 1.08,
        "pair_distance_factor": 2.05,
        "merge_angle_threshold": 0.38,
        "merge_center_threshold": 0.82,
        "coaxial_angle_threshold": 0.26,
        "coaxial_phase_threshold": 0.78,
        "coaxial_center_threshold": 1.15,
        "decay_time": 1.4,
        "reinforce_gain": 0.34,
        "retire_threshold": 0.12,
        "max_level": 3,
        "axis_line_scale": 0.9,
    }


def hydrogen_coaxial_scan_axes() -> List[ScanAxisSpec]:
    return [
        ScanAxisSpec(
            name="phase_threshold",
            default_values=[0.96, 1.02, 1.08],
            description="一级闭合相位阈值，决定夸克对闭合相是否可进入轴节点候选。",
        ),
        ScanAxisSpec(
            name="pair_distance_factor",
            default_values=[1.8, 2.05, 2.3],
            description="一级闭合的距离阈值放大系数，控制局域闭合候选的空间容忍度。",
        ),
        ScanAxisSpec(
            name="coaxial_angle_threshold",
            default_values=[0.20, 0.26, 0.32],
            description="活跃轴之间再生成高层共轴节点的角度阈值。",
        ),
        ScanAxisSpec(
            name="merge_center_threshold",
            default_values=[0.6, 0.82],
            description="闭合候选与已有轴节点合并时的中心距离阈值。",
        ),
    ]


def hydrogen_coaxial_runner(case_args: SimpleNamespace) -> tuple[Path, Dict[str, Any]]:
    wrapped_runner = wrap_runner_with_quantum_post_validation(axis_emergence.run)
    return wrapped_runner(case_args)


def default_registry() -> Dict[str, ExperimentDefinition]:
    metric_schema = load_metric_schema()
    experiment = ExperimentDefinition(
        name="hydrogen_coaxial_axis_emergence",
        description="氢玩具原型中的闭合相持久化、多轴并存与共轴递归生成实验。",
        runner=hydrogen_coaxial_runner,
        default_namespace=hydrogen_coaxial_default_namespace(),
        scan_axes=hydrogen_coaxial_scan_axes(),
        metric_names=[
            "axis_node_count_total",
            "axis_node_count_active",
            "max_level",
            "latest_mass_total_proxy",
            "latest_mass_parallel_proxy",
            "latest_absorbed_axis_proxy",
            "coaxial_depth_score",
            "dominant_frequency_std",
            "resonance_frequency_stability_score",
        ],
    )
    registry = {experiment.name: experiment}
    # Ensure referenced metrics exist in schema.
    missing = [name for name in experiment.metric_names if name not in metric_schema]
    if missing:
        raise ValueError(f"Missing metric definitions in csde_metric_schema.json: {missing}")
    return registry


def list_experiments() -> List[str]:
    return sorted(default_registry().keys())


def get_experiment(name: str) -> ExperimentDefinition:
    registry = default_registry()
    if name not in registry:
        available = ", ".join(sorted(registry))
        raise KeyError(f"Unknown CSDE experiment '{name}'. Available: {available}")
    return registry[name]


if __name__ == "__main__":
    registry = default_registry()
    print(json.dumps({"experiments": list(registry.keys())}, indent=2, ensure_ascii=False))
