#!/usr/bin/env python3
"""
层级定义对比图

左图：旧定义
- 层级被视为先验整数索引或尺度压缩方向
- 跨层级关系主要解释为几何距离、缩放或树状映射

右图：新定义
- 层级由锁相后的公频等价类决定
- 跨层级对象可围绕共同公频锁相
- 抽象概念来自跨层级锁相后的稳定模态
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch


def add_box(ax, x, y, w, h, text, fc, ec="black", fontsize=10, weight="normal"):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        facecolor=fc,
        edgecolor=ec,
        linewidth=1.4,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, weight=weight)


def add_node(ax, x, y, text, fc, radius=0.048, fontsize=10, ec="black"):
    circ = Circle((x, y), radius=radius, facecolor=fc, edgecolor=ec, linewidth=1.4)
    ax.add_patch(circ)
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize)


def add_arrow(ax, p1, p2, text=None, color="black", style="-|>", lw=1.5, rad=0.0, text_offset=(0, 0)):
    arrow = FancyArrowPatch(
        p1,
        p2,
        arrowstyle=style,
        mutation_scale=12,
        linewidth=lw,
        color=color,
        connectionstyle=f"arc3,rad={rad}",
    )
    ax.add_patch(arrow)
    if text:
        mx = (p1[0] + p2[0]) / 2 + text_offset[0]
        my = (p1[1] + p2[1]) / 2 + text_offset[1]
        ax.text(mx, my, text, color=color, fontsize=9, ha="center", va="center")


def draw_old_definition(ax):
    ax.set_title("旧定义：层级 = 先验索引/几何压缩", fontsize=14, weight="bold")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    add_box(ax, 0.08, 0.86, 0.84, 0.08, "层级先由整数索引 n 与尺度压缩 λ 给定", fc="#f8d7da", fontsize=11, weight="bold")

    ys = [0.72, 0.54, 0.36]
    labels = ["L+1 宏观层", "L0 观察层", "L-1 微观层"]
    colors = ["#fee2e2", "#fef3c7", "#dbeafe"]
    for y, label, color in zip(ys, labels, colors):
        add_box(ax, 0.14, y, 0.26, 0.08, label, fc=color, fontsize=10)

    add_arrow(ax, (0.27, 0.70), (0.27, 0.62), text="λ 缩放", color="#9b1c1c")
    add_arrow(ax, (0.27, 0.52), (0.27, 0.44), text="λ 缩放", color="#9b1c1c")

    add_node(ax, 0.66, 0.74, "宏观对象", "#fecaca")
    add_node(ax, 0.66, 0.54, "语言对象", "#fde68a")
    add_node(ax, 0.66, 0.34, "微观对象", "#bfdbfe")

    add_arrow(ax, (0.70, 0.70), (0.70, 0.58), text="跨层级映射", color="#374151")
    add_arrow(ax, (0.70, 0.50), (0.70, 0.38), text="跨层级映射", color="#374151")

    add_box(ax, 0.50, 0.11, 0.35, 0.13, "解释重点：\n1. 层号先验给定\n2. 跨层级多解释为投影/映射\n3. 抽象概念像高层标签", fc="#f3f4f6", fontsize=10)
    ax.text(0.50, 0.28, "难点：跨层级锁相只能被视作附加耦合", fontsize=10, color="#7f1d1d")


def draw_new_definition(ax):
    ax.set_title("新定义：层级 = 锁相公频簇", fontsize=14, weight="bold")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    add_box(ax, 0.08, 0.86, 0.84, 0.08, "层级先由公频 Ω* 与相位锁相定义，层号只是派生索引", fc="#d1fae5", fontsize=11, weight="bold")

    add_box(ax, 0.08, 0.65, 0.24, 0.09, "锁相簇 A\nΩ* ≈ Ω₁*", fc="#e0f2fe", fontsize=10)
    add_box(ax, 0.08, 0.45, 0.24, 0.09, "锁相簇 B\nΩ* ≈ Ω₂*", fc="#ede9fe", fontsize=10)
    add_box(ax, 0.08, 0.25, 0.24, 0.09, "锁相簇 C\nΩ* ≈ Ω₃*", fc="#fce7f3", fontsize=10)

    add_node(ax, 0.48, 0.70, "恒星", "#fecaca")
    add_node(ax, 0.62, 0.58, "神经元", "#fde68a")
    add_node(ax, 0.52, 0.46, "语言", "#bfdbfe")
    add_node(ax, 0.66, 0.34, "制度", "#ddd6fe")

    add_arrow(ax, (0.30, 0.69), (0.43, 0.70), text="同频锁相", color="#0369a1")
    add_arrow(ax, (0.30, 0.49), (0.47, 0.46), text="同频锁相", color="#6d28d9")
    add_arrow(ax, (0.30, 0.29), (0.61, 0.34), text="同频锁相", color="#be185d")

    add_box(ax, 0.58, 0.73, 0.24, 0.08, "抽象概念模态\nC_abs", fc="#bbf7d0", fontsize=10, weight="bold")
    add_arrow(ax, (0.49, 0.72), (0.60, 0.75), text="跨层级锁相", color="#047857", rad=0.15, text_offset=(0.0, 0.03))
    add_arrow(ax, (0.62, 0.60), (0.66, 0.73), color="#047857", rad=-0.15)
    add_arrow(ax, (0.53, 0.48), (0.63, 0.73), color="#047857", rad=0.05)
    add_arrow(ax, (0.67, 0.37), (0.69, 0.73), color="#047857", rad=-0.05)

    add_box(ax, 0.46, 0.11, 0.42, 0.15, "解释重点：\n1. 层级是公频等价类\n2. 跨层级可围绕共同 Ω* 锁相\n3. 抽象概念是稳定跨层级模态", fc="#ecfccb", fontsize=10)
    ax.text(0.46, 0.30, "优势：抽象概念可被解释为锁相后的高阶稳定结构", fontsize=10, color="#065f46")


def create_figure(output_dir: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(15, 7), constrained_layout=True)
    draw_old_definition(axes[0])
    draw_new_definition(axes[1])
    fig.suptitle("层级定义对比：旧定义 vs 新定义（跨层级锁相解释）", fontsize=16, weight="bold")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"hierarchy_definition_comparison_{timestamp}.png"
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def main() -> None:
    out_dir = Path("resonance_data")
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = create_figure(out_dir)
    print("=" * 72)
    print("层级定义对比图已生成")
    print("=" * 72)
    print(f"输出文件: {output_path}")


if __name__ == "__main__":
    main()
