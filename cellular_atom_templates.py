#!/usr/bin/env python3
"""
胞元虚拟宇宙的原子模板

模板含义：
- scalar_s：迹方向总强度，近似局域总活跃度
- components(a1..a8)：局域 SU(3) 偏置与耦合坐标

这些不是标准量子化学参数，而是胞元模型中的结构模板。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping

import numpy as np


@dataclass
class AtomTemplate:
    name: str
    scalar_s: float
    components: np.ndarray
    description: str = ""


def component_vector(values: Mapping[str, float] | None = None) -> np.ndarray:
    vec = np.zeros(8, dtype=np.float64)
    if not values:
        return vec
    for key, value in values.items():
        if not key.startswith("a"):
            raise ValueError(f"Unsupported component key '{key}', expected a1..a8")
        index = int(key[1:]) - 1
        if index < 0 or index >= 8:
            raise ValueError(f"Component key '{key}' out of range, expected a1..a8")
        vec[index] = float(value)
    return vec


DEFAULT_ATOM_TEMPLATES: Dict[str, AtomTemplate] = {
    "H": AtomTemplate(
        name="H",
        scalar_s=0.72,
        components=component_vector(
            {
                "a1": 0.03,
                "a3": 0.02,
                "a8": -0.10,
            }
        ),
        description="氢模板：总强度较小，偏置较弱，适合作为外围轻原子。",
    ),
    "C": AtomTemplate(
        name="C",
        scalar_s=0.94,
        components=component_vector(
            {
                "a1": 0.04,
                "a3": -0.05,
                "a4": 0.03,
                "a8": 0.08,
            }
        ),
        description="碳模板：中等总强度，偏置较均衡，适合作为骨架型中心原子。",
    ),
    "O": AtomTemplate(
        name="O",
        scalar_s=1.12,
        components=component_vector(
            {
                "a1": 0.05,
                "a3": -0.22,
                "a4": -0.04,
                "a8": 0.28,
            }
        ),
        description="氧模板：总强度较高，并在 a3/a8 上具较明显偏置，适合作为中心强原子。",
    ),
}
