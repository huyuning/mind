# 假设验证记录

## H1-1A

- 假设：H1 稳定模式是真实吸引子，而不是数值假象
- 实验编号：H1-1A 初值鲁棒性
- 日期：2026-04-09
- 脚本：[hydrogen_color_field_emergence.py](file:///Users/bytedance/TRAEProjects/mind/hydrogen_color_field_emergence.py)
- 命令模板：

```bash
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --seed <seed>
```

### 运行结果

| seed | run_dir | peak/mean | effective_radius | participation_ratio | dominant_frequency | center |
|------|---------|-----------|------------------|---------------------|--------------------|--------|
| 20260409 | [hydrogen_color_field_emergence_20260409_222238](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hydrogen_color_field_emergence_20260409_222238) | 4.1192 | 17.2078 | 1208.8256 | 0.1667 | (20.566, 19.355) |
| 20260410 | [hydrogen_color_field_emergence_20260409_222240](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hydrogen_color_field_emergence_20260409_222240) | 5.0609 | 17.6167 | 1211.9992 | 0.1667 | (20.278, 19.650) |
| 20260411 | [hydrogen_color_field_emergence_20260409_222242](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hydrogen_color_field_emergence_20260409_222242) | 4.0509 | 17.0865 | 1233.9103 | 0.3333 | (21.157, 20.034) |

### 观察

- 三组种子都形成了单中心局域结构，没有出现“模式完全消失”或明显的拓扑崩塌。
- `effective_radius` 保持在 `17.09 ~ 17.62`，说明空间尺度基本稳定。
- `final_peak_to_mean_ratio` 保持在 `4.05 ~ 5.06`，说明三次运行都维持了局域化。
- `probe_dominant_frequency` 在两次运行中为 `0.1667`，一次上升到 `0.3333`，表明时间谱对初值仍有一定敏感性。

### 初步判断

- 结果：`部分通过`

理由：

- 通过项：
  - 三次运行都出现同类单中心局域模式
  - 有效半径和峰均比处于相近量级
  - 没有因更换种子而失去模式
- 保留项：
  - 主频在第三次运行发生明显偏移
  - 需要继续做 H1-1B 与 H1-1C，判断这种频率变化是正常模式分支，还是稳定性不足

### 下一步建议

- 继续执行 H1-1B 时间步长鲁棒性实验
- 继续执行 H1-1C 角向节点鲁棒性实验
- 若后续仍出现主频双分支，考虑把“单中心空间稳定”与“时间谱稳定”拆成两个子判据

## H1-1B

- 假设：H1 稳定模式是真实吸引子，而不是数值假象
- 实验编号：H1-1B 时间步长鲁棒性
- 日期：2026-04-09
- 脚本：[hydrogen_color_field_emergence.py](file:///Users/bytedance/TRAEProjects/mind/hydrogen_color_field_emergence.py)
- 命令模板：

```bash
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt <dt>
```

### 运行结果

| dt | run_dir | peak/mean | effective_radius | participation_ratio | dominant_frequency | center |
|----|---------|-----------|------------------|---------------------|--------------------|--------|
| 0.01 | [hydrogen_color_field_emergence_20260409_222436](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hydrogen_color_field_emergence_20260409_222436) | 4.1194 | 17.2078 | 1208.8051 | 0.1667 | (20.566, 19.355) |
| 0.02 | [hydrogen_color_field_emergence_20260409_222438](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hydrogen_color_field_emergence_20260409_222438) | 4.1192 | 17.2078 | 1208.8256 | 0.1667 | (20.566, 19.355) |
| 0.04 | [hydrogen_color_field_emergence_20260409_222440](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hydrogen_color_field_emergence_20260409_222440) | 4.1188 | 17.2077 | 1208.8666 | 0.1667 | (20.565, 19.355) |

### 观察

- 三组 `dt` 都得到同一类单中心局域结构。
- `final_peak_to_mean_ratio` 仅在 `4.1188 ~ 4.1194` 之间波动，几乎不变。
- `effective_radius` 保持在 `17.2077 ~ 17.2078`，空间尺度高度稳定。
- `probe_dominant_frequency` 三次都保持 `0.1667`，说明在当前参数下时间谱对步长不敏感。

### 初步判断

- 结果：`通过`

理由：

- 通过项：
  - 改变 `dt` 后主模式类别完全不变
  - 峰均比、有效半径、参与比和主频都高度一致
  - 没有出现数值爆炸、失稳或拓扑跳变
- 保留项：
  - 目前只验证了单组默认种子，后续仍可考虑把“多种子 + 多步长”联合验证作为更严格版本

### 下一步建议

- 继续执行 H1-1C 角向节点鲁棒性实验
- 若 H1-1C 也稳定，则 H1 可以从“部分通过”提升到更强支持状态

## H1-1C

- 假设：H1 稳定模式是真实吸引子，而不是数值假象
- 实验编号：H1-1C 角向节点鲁棒性
- 日期：2026-04-09
- 脚本：[hydrogen_color_field_emergence.py](file:///Users/bytedance/TRAEProjects/mind/hydrogen_color_field_emergence.py)
- 命令模板：

```bash
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --angular-momentum <m> --angular-gain <gain>
```

### 运行结果

| m | angular_gain | run_dir | peak/mean | effective_radius | participation_ratio | dominant_frequency | angular_node_count | angular_zero_crossings | dominant_angular_harmonic |
|---|--------------|---------|-----------|------------------|---------------------|--------------------|--------------------|------------------------|---------------------------|
| 1 | 0.28 | [hydrogen_color_field_emergence_20260409_223259](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hydrogen_color_field_emergence_20260409_223259) | 4.1203 | 17.2148 | 1208.6492 | 0.1667 | 3 | 6 | 1 |
| 2 | 0.22 | [hydrogen_color_field_emergence_20260409_223301](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hydrogen_color_field_emergence_20260409_223301) | 4.1127 | 17.2009 | 1209.6747 | 0.1667 | 4 | 8 | 1 |

### 产物

- `final_density_map_*.png`
- `final_su3_fields_*.png`
- `time_frequency_spectrum_*.png`
- `interactive_density_timeseries_*.html`
- `angular_node_profile_*.png`

对应目录：

- [hydrogen_color_field_emergence_20260409_223259](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hydrogen_color_field_emergence_20260409_223259)
- [hydrogen_color_field_emergence_20260409_223301](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hydrogen_color_field_emergence_20260409_223301)

### 观察

- `m=1` 与 `m=2` 两组运行都稳定结束，没有数值失稳。
- 两组的 `peak/mean`、`effective_radius`、`participation_ratio` 都保持在与默认稳定模式相近的量级。
- 两组的 `probe_dominant_frequency` 都为 `0.1667`，说明主频并未因为角向模式选择而明显分叉。
- 当前脚本已自动输出 `angular_node_count`、`angular_zero_crossings` 和 `angular_node_profile_*.png`，不再完全依赖人工目视判图。
- 自动零点提取把两组模式稳定区分为：
  - `m=1` -> `6` 个角向零交叉，对应 `3` 个节点计数
  - `m=2` -> `8` 个角向零交叉，对应 `4` 个节点计数
- `dominant_angular_harmonic` 当前两组都为 `1`，说明在现阶段它更像辅助诊断量，而不是可靠的主判据。

### 初步判断

- 结果：`通过`

理由：

- 通过项：
  - 角向通道 `m=1` 与 `m=2` 都能稳定运行
  - 没有因引入角动量通道而破坏单中心局域结构
  - 自动零点提取已经给出可重复的角向区分结果
  - 输出图像、动态 HTML 和 `angular_node_profile_*.png` 可相互交叉验证
- 保留项：
  - 当前的“节点计数”是几何启发式指标，数值上能稳定区分模式，但暂不应直接解释为严格的量子角动量本征值
  - 主频没有明显分叉，说明“角向区分”主要仍体现在空间形态，而不是时间谱

### 下一步建议

- 把自动节点计数应用到更多 `m` 和 `angular_gain` 参数扫描，检查区分是否持续成立
- 若要进一步提升可信度，可增加“节点寿命”统计，而不只看终态切片
- 从当前结果看，H1 总体已获得更完整支持：空间稳定性明确，且角向模式现在已有自动定量化入口

## H2-1

- 假设：H2 锁相层级可以被统一判据定义
- 实验编号：H2-1 RAM 相图稳定窗扫描
- 日期：2026-04-10
- 脚本：[current_ram_phase_scan.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_phase_scan.py)
- 命令：

```bash
python3 current_ram_phase_scan.py --ratio-min 0.9 --ratio-max 1.3 --ratio-steps 21 --random-trials 24
```

### 运行结果

- 输出目录：[current_ram_phase_scan_20260410_101856](file:///Users/bytedance/TRAEProjects/mind/resonance_data/current_ram_phase_scan_20260410_101856)
- 图像：[phase_scan_20260410_101856.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/current_ram_phase_scan_20260410_101856/phase_scan_20260410_101856.png)

### 关键指标

- 稳定窗口：
  - `ratio ∈ [0.90, 1.00]`
  - `stable_fraction = 1.0`
  - `oscillation_fraction = 0.0`
  - `mean_switch_rate = 0.0`
- 振荡窗口：
  - `ratio ∈ [1.02, 1.30]`
  - `stable_fraction = 0.0`
  - `oscillation_fraction = 1.0`
  - `mean_switch_rate` 从 `9.4858` 单调上升到 `168.4219`
- 过渡窗口：
  - 本次未出现显著 `transition_fraction > 0` 的混合带

### 观察

- 该相图给出了非常清晰的二分结构：
  - `ratio <= 1.00` 为稳定单吸引子区
  - `ratio >= 1.02` 为双态振荡区
- `mean_switch_rate` 作为辅助判据与振荡区严格同向变化，可作为“强切换区”的强度指标。
- 因此，仅靠一组简单判据就能把该实验切成：
  - 稳定区
  - 振荡区
  - 切换强度

### 初步判断

- 结果：`通过`

理由：

- `stable_fraction / oscillation_fraction / mean_switch_rate` 足以构成统一的最小判据组
- 稳定区与振荡区边界清楚，不依赖人工主观解释

### 下一步建议

- 将这组判据与层级流扫描中的 `stable_island_fraction / smooth_score / split_score / closure_error_normalized_mean` 对照，验证跨实验可共用性

## H2-2

- 假设：H2 锁相层级可以被统一判据定义
- 实验编号：H2-2 层级流扫描
- 日期：2026-04-10
- 脚本：[hierarchy_flow_scan.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_flow_scan.py)
- 参考报告目录：[hierarchy_flow_scan_20260407_210156](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hierarchy_flow_scan_20260407_210156)
- 参考摘要：[report_20260407_210156.md](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hierarchy_flow_scan_20260407_210156/report_20260407_210156.md)
- 参考数据：[report_20260407_210156.json](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hierarchy_flow_scan_20260407_210156/report_20260407_210156.json)

### 运行结果

- 最平滑区域：
  - `detuning_scale = 1.0000`
  - `shell_drift_scale = 0.0000`
  - `resonance_gain = 0.0000`
  - `smooth_score = 0.933114`
  - `chi_temporal_std = 0.000000`
  - `closure_error_normalized_mean = 0.282518`
  - `stable_island_fraction = 1.000000`
- 最分裂区域：
  - `detuning_scale = 0.5000`
  - `shell_drift_scale = 0.3250`
  - `resonance_gain = 1.2000`
  - `split_score = 0.329935`
  - `chi_temporal_std = 0.005343`
  - `closure_error_normalized_mean = 0.708636`
  - `stable_island_fraction = 0.000000`

### 判据映射

- H2-1 中的“稳定区”可映射为：
  - `stable_fraction ↑`
  - `mean_switch_rate ↓`
- H2-2 中对应为：
  - `stable_island_fraction ↑`
  - `smooth_score ↑`
  - `chi_temporal_std ↓`
  - `closure_error_normalized_mean ↓`

- H2-1 中的“振荡 / 切换区”可映射为：
  - `oscillation_fraction ↑`
  - `mean_switch_rate ↑`
- H2-2 中对应为：
  - `split_score ↑`
  - `chi_temporal_std ↑`
  - `closure_error_normalized_mean ↑`
  - `stable_island_fraction ↓`

### 观察

- 两个实验虽然系统不同，但都能被同一套语言描述：
  - 稳定区
  - 分裂 / 振荡区
  - 切换或波动强度
  - 闭合误差
- 在 H2-2 里，“稳定岛比例高 + 闭合误差低 + 时间波动低”与 H2-1 里的“stable_fraction 高 + switch_rate 低”是相同类型的对象。
- 在 H2-2 里，“stable_island_fraction = 0` 且 `closure_error_normalized_mean` 高、`chi_temporal_std` 高”的区域，与 H2-1 中“oscillation_fraction = 1.0` 且 `mean_switch_rate` 持续上升”的区域在判据逻辑上是一致的。

### 初步判断

- 结果：`通过`

理由：

- 跨实验已经可以共用“稳定 / 分裂 / 切换强度 / 闭合误差”这套语言
- 不同实验的具体量不同，但可稳定映射到同一类判据角色

### 当前 H2 总结

- H2-1：`通过`
- H2-2：`通过`

当前结论：

- H2 已获得较强支持
- “锁相层级可统一判定”这一命题，目前至少在 RAM 相图扫描与层级流扫描这两类实验中成立

### 下一步建议

- 若继续加强 H2，应补做连续场原型的时频锁相实验，把 `probe_dominant_frequency / stft ridge / 模式切换` 也纳入同一判据映射

## H2-3

- 假设：H2 锁相层级可以被统一判据定义
- 实验编号：H2-3 连续场时频锁相分析
- 日期：2026-04-10
- 脚本：[hydrogen_color_field_emergence.py](file:///Users/bytedance/TRAEProjects/mind/hydrogen_color_field_emergence.py)
- 命令：

```bash
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --probe-radius 2.0 --stft-window 64 --stft-hop 8
```

### 运行结果

- 输出目录：[hydrogen_color_field_emergence_20260410_103757](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hydrogen_color_field_emergence_20260410_103757)
- 终态摘要：[summary_20260410_103757.json](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hydrogen_color_field_emergence_20260410_103757/summary_20260410_103757.json)
- 时频图：[time_frequency_spectrum_20260410_103757.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hydrogen_color_field_emergence_20260410_103757/time_frequency_spectrum_20260410_103757.png)
- 脊线摘要：[h2_3_frequency_ridge_summary.json](file:///Users/bytedance/TRAEProjects/mind/resonance_data/hydrogen_color_field_emergence_20260410_103757/h2_3_frequency_ridge_summary.json)

### 关键指标

- `probe_dominant_frequency = 0.1667`
- `ridge_frequency_mean = 0.7552`
- `ridge_frequency_std = 0.1402`
- `ridge_energy_share_mean = 0.6490`
- `ridge_energy_share_min = 0.3032`
- `ridge_energy_share_max = 0.9354`
- `stft_time_count = 30`

### 观察

- 连续场原型存在可提取的主频对象，不再只是“看动态图”。
- STFT 脊线平均占据约 `64.9%` 的列能量，说明能量确实集中在主导频带，而不是完全弥散噪声。
- 但 `ridge_frequency_std = 0.1402` 仍然不小，说明主频脊线会随时间漂移，不是完全刚性的窄带锁相。
- 因此该实验更像是：
  - 存在主导锁相带
  - 但锁相强度有限，仍伴随明显频带漂移

### 初步判断

- 结果：`部分通过`

理由：

- 通过项：
  - 已存在稳定可提取的主频对象
  - 时频脊线能量占比明显高于弥散背景
  - 可以与 H2-1 / H2-2 的稳定性判据对接
- 保留项：
  - 主频脊线仍有可观漂移
  - 当前尚未定义“连续场锁相充分稳定”的阈值

## H2 统一判据对照表

| 判据角色 | H2-1 RAM 相图 | H2-2 层级流扫描 | H2-3 连续场时频 |
|---|---|---|---|
| 稳定区 | `stable_fraction ↑` | `stable_island_fraction ↑`, `smooth_score ↑` | `ridge_energy_share_mean ↑`, `ridge_frequency_std ↓` |
| 振荡/分裂区 | `oscillation_fraction ↑` | `split_score ↑` | 主频脊线漂移增大，能量分散 |
| 切换强度 | `mean_switch_rate ↑` | `chi_temporal_std ↑` | `ridge_frequency_std ↑` |
| 闭合/一致性 | 稳定窗边界清晰 | `closure_error_normalized_mean ↓` 表示更一致 | 主频脊线持续集中表示更一致 |
| 稳定对象 | 单吸引子 vs 双态振荡 | 稳定岛 vs 分裂区 | 主频带 vs 漂移带 |

### 统一解释

- 三个实验虽然系统层次不同，但都可以压缩为同一套判据语言：
  - 是否存在稳定主导结构
  - 该结构是否随时间显著切换或漂移
  - 是否存在更高的一致性 / 闭合性
- 其中：
  - `H2-1` 最适合给出离散的“稳定区 / 振荡区”边界
  - `H2-2` 最适合给出“闭合误差 / 稳定岛比例”的中观结构定义
  - `H2-3` 最适合补上“连续场中的主频锁相带是否存在”

### 当前 H2 总结（更新）

- H2-1：`通过`
- H2-2：`通过`
- H2-3：`部分通过`

当前结论：

- H2 整体仍为 `通过`
- 原因是跨实验的统一判据已经成立：
  - RAM 相图给出清晰边界
  - 层级流扫描给出稳定岛与闭合误差
  - 连续场原型给出主频锁相带
- 当前剩余工作主要不是“是否存在统一语言”，而是：
  - 如何把连续场中的锁相阈值进一步定量化
