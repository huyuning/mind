#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import plotly.graph_objects as go


def _as_xyz(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    arr = np.asarray(points, dtype=np.float64)
    if arr.size == 0:
        empty = np.array([], dtype=np.float64)
        return empty, empty, empty
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError("points must be shaped [N, 3]")
    return arr[:, 0], arr[:, 1], arr[:, 2]


def point_trace(
    *,
    points: np.ndarray,
    name: str,
    size: float = 4.0,
    opacity: float = 0.8,
    color: str | None = None,
    color_values: np.ndarray | None = None,
    colorscale: str = "Viridis",
    showscale: bool = False,
    symbol: str = "circle",
) -> go.Scatter3d:
    x, y, z = _as_xyz(points)
    marker: dict = {
        "size": size,
        "opacity": opacity,
        "symbol": symbol,
    }
    if color_values is not None:
        marker["color"] = np.asarray(color_values, dtype=np.float64)
        marker["colorscale"] = colorscale
        marker["showscale"] = showscale
    elif color is not None:
        marker["color"] = color
    return go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode="markers",
        name=name,
        marker=marker,
    )


def line_trace(
    *,
    points: np.ndarray,
    name: str,
    color: str,
    width: float = 4.0,
    opacity: float = 0.7,
) -> go.Scatter3d:
    x, y, z = _as_xyz(points)
    return go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode="lines",
        name=name,
        line={"color": color, "width": width},
        opacity=opacity,
    )


def save_plotly_3d_html(
    *,
    output_path: Path,
    title: str,
    traces: Sequence[go.BaseTraceType],
    axis_span: float | None = None,
    center: Iterable[float] | None = None,
) -> None:
    if center is None:
        center = (0.0, 0.0, 0.0)
    cx, cy, cz = [float(v) for v in center]
    scene: dict = {
        "xaxis": {"title": "x"},
        "yaxis": {"title": "y"},
        "zaxis": {"title": "z"},
        "aspectmode": "cube",
    }
    if axis_span is not None:
        scene["xaxis"]["range"] = [cx - axis_span, cx + axis_span]
        scene["yaxis"]["range"] = [cy - axis_span, cy + axis_span]
        scene["zaxis"]["range"] = [cz - axis_span, cz + axis_span]

    fig = go.Figure(data=list(traces))
    fig.update_layout(
        title=title,
        scene=scene,
        template="plotly_dark",
        legend={"orientation": "h"},
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
    )
    fig.write_html(str(output_path), include_plotlyjs="cdn")

def mesh3d_from_param_grid(
    *,
    X: np.ndarray,
    Y: np.ndarray,
    Z: np.ndarray,
    name: str,
    color: str = "#22c55e",
    opacity: float = 0.85,
) -> go.Mesh3d:
    """
    Build a closed surface Mesh3d from a parameterized grid (theta x phi).
    The grid is expected to be shaped [T, P]; we connect periodic in phi.
    """
    X = np.asarray(X, dtype=np.float64)
    Y = np.asarray(Y, dtype=np.float64)
    Z = np.asarray(Z, dtype=np.float64)
    assert X.shape == Y.shape == Z.shape and X.ndim == 2, "X/Y/Z must be same 2D shape"
    T, P = X.shape
    # Flatten vertices
    x = X.reshape(-1)
    y = Y.reshape(-1)
    z = Z.reshape(-1)
    # Triangulate
    is_list: list[int] = []
    js_list: list[int] = []
    ks_list: list[int] = []
    def vid(i: int, j: int) -> int:
        return i * P + (j % P)
    for i in range(T - 1):
        for j in range(P):
            # two triangles per quad: (i,j)-(i+1,j)-(i+1,j+1) and (i,j)-(i+1,j+1)-(i,j+1)
            a = vid(i, j)
            b = vid(i + 1, j)
            c = vid(i + 1, j + 1)
            d = vid(i, j + 1)
            is_list += [a, a]
            js_list += [b, c]
            ks_list += [c, d]
    mesh = go.Mesh3d(
        x=x, y=y, z=z,
        i=np.asarray(is_list, dtype=np.int32),
        j=np.asarray(js_list, dtype=np.int32),
        k=np.asarray(ks_list, dtype=np.int32),
        color=color,
        opacity=opacity,
        name=name,
        lighting=dict(ambient=0.5, diffuse=0.6, specular=0.3, roughness=0.7, fresnel=0.2),
        flatshading=False,
    )
    return mesh
