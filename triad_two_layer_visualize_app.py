#!/usr/bin/env python3
"""
两层三节点实验交互式可视化生成器（纯前端，无需本地JS依赖安装）

用法示例
  python3 triad_two_layer_visualize_app.py --run-dir resonance_data/triad_two_layer_memory_scan_20260408_181621

生成
  <run-dir>/interactive_<timestamp>.html

交互能力
  - 振幅时间序列（6节点，分层着色，可切换）
  - 相位时间序列（6节点，分层着色）
  - 核心/阈值层闭合强度与阈值线
  - 跨层锁相关联度时间序列
  - 成对锁相矩阵热图（6x6）
  - 复平面相位-振幅瞬时散点（时间滑块）
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import numpy as np


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="两层三节点实验交互式可视化生成器")
    p.add_argument(
        "--run-dir",
        type=str,
        required=True,
        help="单次运行目录，例如 resonance_data/triad_two_layer_memory_scan_YYYYMMDD_HHMMSS",
    )
    return p.parse_args()


def load_run(run_dir: Path) -> Dict[str, Any]:
    # 找到 summary_*.json 和 state_series_*.npz
    summaries = list(run_dir.glob("summary_*.json"))
    npzs = list(run_dir.glob("state_series_*.npz"))
    if not summaries or not npzs:
        raise FileNotFoundError("未找到 summary_*.json 或 state_series_*.npz，请确认 run-dir 正确")
    summary_path = summaries[0]
    npz_path = npzs[0]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    npz = np.load(npz_path)
    return {
        "summary": summary,
        "npz": npz,
        "summary_path": summary_path,
        "npz_path": npz_path,
    }


def compute_pair_locking(node_series: np.ndarray) -> np.ndarray:
    # node_series: [T, 6] complex
    phases = np.angle(node_series)
    n = phases.shape[1]
    lock = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(n):
            delta = phases[:, i] - phases[:, j]
            lock[i, j] = float(np.abs(np.mean(np.exp(1j * delta))))
    return lock


def render_html(data: Dict[str, Any]) -> str:
    # 准备数据
    summary = data["summary"]
    npz = data["npz"]
    names = summary["node_order"]
    times = npz["times"].astype(float).tolist() if "times" in npz else (np.arange(npz["node_series"].shape[0]) * 1.0).tolist()
    node_series = npz["node_series"]
    amplitudes = np.abs(node_series)
    phases = np.angle(node_series)
    core_closure = npz.get("core_closure_series", None)
    mem_closure = npz.get("mem_closure_series", None)
    cross_locking = npz.get("cross_locking_series", None)

    lock_mat = compute_pair_locking(node_series)

    # 将数值压缩为普通Python类型
    def as_list(x: np.ndarray) -> list:
        return x.astype(float).tolist()

    payload = {
        "names": names,
        "times": times,
        "amplitudes": as_list(amplitudes),
        "phases": as_list(phases),
        "core_closure": as_list(core_closure) if core_closure is not None else None,
        "mem_closure": as_list(mem_closure) if mem_closure is not None else None,
        "cross_locking": as_list(cross_locking) if cross_locking is not None else None,
        "core_threshold": summary.get("thresholds", {}).get("core_threshold", None),
        "mem_threshold": summary.get("thresholds", {}).get("mem_threshold", None),
        "pair_locking": lock_mat.astype(float).tolist(),
    }
    data_json = json.dumps(payload, ensure_ascii=False)

    # 简单Plotly前端（CDN）
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>两层三节点实验交互式可视化</title>
  <script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji'; margin: 0; padding: 12px; }}
    .row {{ display: flex; flex-wrap: wrap; gap: 16px; }}
    .card {{ flex: 1 1 520px; min-width: 420px; border: 1px solid #e5e5e5; border-radius: 8px; padding: 8px 8px 12px; }}
    .title {{ font-weight: 600; margin: 4px 8px 12px; }}
    #controls {{ display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }}
    input[type="range"] {{ width: 320px; }}
  </style>
</head>
<body>
  <div id="controls">
    <div>时间索引: <span id="timeIdx">0</span></div>
    <input id="slider" type="range" min="0" value="0" />
    <label><input type="checkbox" id="showCore" checked /> 显示核心层</label>
    <label><input type="checkbox" id="showMem" checked /> 显示阈值层</label>
  </div>
  <div class="row">
    <div class="card"><div class="title">振幅时间序列</div><div id="ampChart"></div></div>
    <div class="card"><div class="title">相位时间序列</div><div id="phaseChart"></div></div>
  </div>
  <div class="row">
    <div class="card"><div class="title">闭合与锁相</div><div id="closureChart"></div></div>
    <div class="card"><div class="title">成对锁相矩阵</div><div id="lockHeatmap"></div></div>
  </div>
  <div class="row">
    <div class="card"><div class="title">复平面瞬时相位-振幅</div><div id="phasorChart"></div></div>
  </div>

  <script id="dataset" type="application/json">{data_json}</script>
  <script>
    const data = JSON.parse(document.getElementById('dataset').textContent);
    const names = data.names;
    const times = data.times;
    const amps = data.amplitudes; // [T,6]
    const phs = data.phases;      // [T,6]
    const coreClosure = data.core_closure;
    const memClosure = data.mem_closure;
    const crossLock = data.cross_locking;
    const coreTh = data.core_threshold;
    const memTh = data.mem_threshold;
    const pairLocking = data.pair_locking; // 6x6
    const N = names.length;
    const T = times.length;
    const coreIdx = [0,1,2];
    const memIdx = [3,4,5];

    const slider = document.getElementById('slider');
    const timeIdxSpan = document.getElementById('timeIdx');
    slider.max = Math.max(0, T-1);
    const showCore = document.getElementById('showCore');
    const showMem = document.getElementById('showMem');

    // 振幅图
    function renderAmp() {{
      const traces = [];
      for (let i=0;i<N;i++) {{
        const visibleCore = showCore.checked && coreIdx.includes(i);
        const visibleMem = showMem.checked && memIdx.includes(i);
        const visible = (visibleCore || visibleMem) ? true : 'legendonly';
        traces.push({{
          x: times,
          y: amps.map(row => row[i]),
          type: 'scatter',
          mode: 'lines',
          name: names[i],
          line: {{ width: 1.5 }},
          visible: visible
        }});
      }}
      Plotly.newPlot('ampChart', traces, {{
        margin: {{l:40,r:10,t:10,b:40}},
        xaxis: {{title: 'time'}},
        yaxis: {{title: '|xi|'}},
      }}, {{displayModeBar: false}});
    }}

    // 相位图
    function renderPhase() {{
      const traces = [];
      for (let i=0;i<N;i++) {{
        const visibleCore = showCore.checked && coreIdx.includes(i);
        const visibleMem = showMem.checked && memIdx.includes(i);
        const visible = (visibleCore || visibleMem) ? true : 'legendonly';
        traces.push({{
          x: times,
          y: phs.map(row => row[i]),
          type: 'scatter',
          mode: 'lines',
          name: names[i],
          line: {{ width: 1.2 }},
          visible: visible
        }});
      }}
      Plotly.newPlot('phaseChart', traces, {{
        margin: {{l:40,r:10,t:10,b:40}},
        xaxis: {{title: 'time'}},
        yaxis: {{title: 'phase'}},
      }}, {{displayModeBar: false}});
    }}

    // 闭合与锁相
    function renderClosure() {{
      const traces = [];
      if (coreClosure) {{
        traces.push({{
          x: times, y: coreClosure, type: 'scatter', mode: 'lines',
          name: 'core closure', line: {{color: 'red'}}
        }});
        if (coreTh != null) {{
          traces.push({{
            x: [times[0], times[times.length-1]],
            y: [coreTh, coreTh],
            type: 'scatter', mode: 'lines', name: 'core threshold',
            line: {{color:'red', dash: 'dash'}}, hoverinfo:'skip', showlegend: true
          }});
        }}
      }}
      if (memClosure) {{
        traces.push({{
          x: times, y: memClosure, type: 'scatter', mode: 'lines',
          name: 'mem closure', line: {{color: 'blue'}}
        }});
        if (memTh != null) {{
          traces.push({{
            x: [times[0], times[times.length-1]],
            y: [memTh, memTh],
            type: 'scatter', mode: 'lines', name: 'mem threshold',
            line: {{color:'blue', dash: 'dash'}}, hoverinfo:'skip', showlegend: true
          }});
        }}
      }}
      if (crossLock) {{
        traces.push({{
          x: times, y: crossLock, type: 'scatter', mode: 'lines',
          name: 'cross locking', line: {{color: 'green'}}
        }});
      }}
      Plotly.newPlot('closureChart', traces, {{
        margin: {{l:40,r:10,t:10,b:40}},
        xaxis: {{title: 'time'}},
        yaxis: {{title: 'strength'}},
      }}, {{displayModeBar: false}});
    }}

    // 成对锁相热图
    function renderHeat() {{
      Plotly.newPlot('lockHeatmap', [{{
        z: pairLocking, x: names, y: names, type: 'heatmap', colorscale: 'Viridis'
      }}], {{
        margin: {{l:80,r:20,t:10,b:80}},
      }}, {{displayModeBar: false}});
    }}

    // 复平面瞬时图
    function renderPhasor(tIdx) {{
      const xs = [], ys = [], txt = [], clr = [];
      for (let i=0;i<N;i++) {{
        const r = amps[tIdx][i];
        const p = phs[tIdx][i];
        xs.push(r * Math.cos(p));
        ys.push(r * Math.sin(p));
        txt.push(names[i] + ' |xi|=' + r.toFixed(3));
        clr.push(coreIdx.includes(i) ? 'tomato' : 'steelblue');
      }}
      Plotly.newPlot('phasorChart', [{{
        x: xs, y: ys, mode: 'markers+text', type: 'scatter',
        text: names, textposition: 'top center',
        marker: {{size: 10, color: clr}}
      }}], {{
        margin: {{l:40,r:10,t:10,b:40}},
        xaxis: {{title: 'Re', zeroline: true}},
        yaxis: {{title: 'Im', zeroline: true}},
        showlegend: false,
        shapes: [
          {{type:'circle', xref:'x', yref:'y', x0:-1, y0:-1, x1:1, y1:1, line:{{color:'#ccc'}}}}
        ]
      }}, {{displayModeBar: false}});
      timeIdxSpan.textContent = String(tIdx);
    }}

    function redrawAll() {{
      renderAmp();
      renderPhase();
      renderClosure();
      renderHeat();
      renderPhasor(parseInt(slider.value||'0',10));
    }}

    showCore.addEventListener('change', redrawAll);
    showMem.addEventListener('change', redrawAll);
    slider.addEventListener('input', () => renderPhasor(parseInt(slider.value||'0',10)));

    // 首次渲染
    redrawAll();
  </script>
</body>
</html>
"""
    return html


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir).resolve()
    ctx = load_run(run_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = run_dir / f"interactive_{timestamp}.html"
    html = render_html(ctx)
    out_path.write_text(html, encoding="utf-8")
    print(json.dumps({"interactive_html": str(out_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

