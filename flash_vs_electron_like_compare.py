#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="闪现态与 electron-like 基准并排对照")
    parser.add_argument("--flash-metrics", required=True, help="flash_hydrogen_metrics_*.json")
    parser.add_argument("--electron-summary", required=True, help="electron-like summary_*.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    flash_path = Path(args.flash_metrics)
    electron_path = Path(args.electron_summary)
    flash = json.loads(flash_path.read_text(encoding="utf-8"))
    electron = json.loads(electron_path.read_text(encoding="utf-8"))

    flash_freq = float(flash["dominant_frequency"])
    electron_freq = float(electron["probe_dominant_frequency"])
    flash_radius = float(flash["effective_radius"])
    electron_radius = float(electron["effective_radius"])
    freq_ratio = flash_freq / electron_freq if electron_freq else None
    radius_ratio = flash_radius / electron_radius if electron_radius else None

    comparison = {
        "flash_metrics_path": str(flash_path),
        "electron_like_summary_path": str(electron_path),
        "flash_dominant_frequency": flash_freq,
        "electron_like_dominant_frequency": electron_freq,
        "frequency_ratio_flash_to_electron_like": freq_ratio,
        "flash_effective_radius": flash_radius,
        "electron_like_effective_radius": electron_radius,
        "radius_ratio_flash_to_electron_like": radius_ratio,
        "flash_focus_centroid_count": int(flash["focus_centroid_count"]),
        "flash_weight_basis": flash["dominant_frequency_basis"],
        "electron_like_peak_to_mean_ratio": float(electron["final_peak_to_mean_ratio"]),
        "electron_like_angular_node_count": int(electron.get("angular_node_count", 0)),
    }

    out_dir = flash_path.parent
    json_path = out_dir / "flash_vs_electron_like_comparison.json"
    md_path = out_dir / "flash_vs_electron_like_comparison.md"
    json_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")

    lines = [
        "# Flash vs Electron-like Comparison",
        "",
        f"- Flash metrics: `{flash_path}`",
        f"- Electron-like summary: `{electron_path}`",
        "",
        "| metric | flash state | electron-like baseline | ratio |",
        "|---|---:|---:|---:|",
        f"| dominant_frequency | {flash_freq:.6f} | {electron_freq:.6f} | {freq_ratio:.6f} |" if freq_ratio is not None else f"| dominant_frequency | {flash_freq:.6f} | {electron_freq:.6f} | n/a |",
        f"| effective_radius | {flash_radius:.6f} | {electron_radius:.6f} | {radius_ratio:.6f} |" if radius_ratio is not None else f"| effective_radius | {flash_radius:.6f} | {electron_radius:.6f} | n/a |",
        "",
        "## Notes",
        "",
        f"- Flash dominant-frequency basis: `{flash['dominant_frequency_basis']}`",
        f"- Flash focus centroid count: `{flash['focus_centroid_count']}`",
        f"- Electron-like peak/mean ratio: `{electron['final_peak_to_mean_ratio']:.6f}`",
        f"- Electron-like angular node count: `{int(electron.get('angular_node_count', 0))}`",
        "- The flash state is much more compact if the radius ratio is well below 1.",
        "- The flash state stays frequency-comparable if the frequency ratio remains O(1).",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    print(f"dominant_frequency ratio: {freq_ratio:.6f}" if freq_ratio is not None else "dominant_frequency ratio: n/a")
    print(f"effective_radius ratio: {radius_ratio:.6f}" if radius_ratio is not None else "effective_radius ratio: n/a")


if __name__ == "__main__":
    main()
