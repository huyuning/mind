# 色荷-味映射实验（专题）

## 1. 原理概述

- 假设映射：
  - 三种色荷 ↔ 三个本征位（对角位 `v11, v22, v33`）
  - 六种味 ↔ 六个有向推理位（非对角位 `v12, v21, v13, v31, v23, v32`）
- 结构意图：第二层 `9` 位应在动力学上自然分裂为“3 个自保持本征核 + 6 个有向通道”，而非仅为命名上的区分。
- 失稳判据：当六个味位过度贴近本征位（或失去方向性差异）时，`3+6` 分层塌缩，`mapping_supported` 从 `True` 掉到 `False`。

## 2. 脚本入口

- 单点实验（基线与特征分离）  
  [quark_color_flavor_mapping_test.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_test.py)
- 常规扫描（稳定窗与热图）  
  [quark_color_flavor_mapping_sweep.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_sweep.py)
- 边界扫描（失稳区与边界带）  
  [quark_color_flavor_mapping_boundary_scan.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_boundary_scan.py)

## 3. 参数物理意义

| 参数 | 计算角色 | 物理/结构含义 | 增大后的主要效果 | 失稳含义 |
|---|---|---|---|---|
| `blend` | 控制非对角位中“派生味位”和“源/目标混合参考项”的权重比例 | 味位对本征位的贴附度、继承度、混合深度 | 味位越来越像源位和目标位的强混合体，`6` 个味通道逐步贴近 `3` 个本征位 | 当 `blend` 过高时，`3+6` 分层塌缩，味位失去独立通道身份，`mapping_supported` 容易掉到 `False` |
| `phase_push` | 控制非对角位相对于目标位的定向相位推进量 | 味位的方向性、流向性、手性可分辨度 | `i -> j` 与 `j -> i` 的相位骨架差异被拉开，味位的有向推理特征更明显 | 它通常不单独主导失稳，而是塑造边界形状；在某些窗口内过强或过弱都会削弱方向分离，也可能出现再入稳定区 |

使用建议：

- 低到中等 `blend` 更容易保持 `3` 个本征位与 `6` 个味位的清晰分层
- `phase_push` 更适合用来调方向性和边界形状，而不是单独追求“大就是强”
- 若要先找失稳边界，优先扩大 `blend` 范围；若要细看再入稳定区，再局部细扫 `phase_push`

## 4. 指标与判据

- 自保持/闭合：
  - `self_score`、`closure_score`
- 方向不对称：
  - `asymmetry_vs_reverse = 1 - xcorr(v_ij, v_ji)`
- 手性敏感性：
  - `chirality_sensitivity = 1 - xcorr(v_ij^{(+1)}, v_ij^{(-1)})`
- 聚合分离度：
  - `cluster_separation_score = 0.5 * ((eigen_self_mean - flavor_self_mean) + (flavor_asym_mean - eigen_asym_mean))`
- 支持判据：
  - `eigen_self_mean > flavor_self_mean + 0.05`
  - `flavor_asym_mean > eigen_asym_mean + 0.05`
  - `flavor_chirality_sensitivity_mean > eigen_chirality_sensitivity_mean + 0.03`

## 5. 数据与边界分析（样例）

- 常规扫描（中低 `blend`、低 `phase_push`）：
  - `mapping_supported` 全为 `True`
  - 最优点（样例）：`chirality = -1, blend = 0.22, phase_push = 0.04`
  - `cluster_separation_score ≈ 0.691`（强分离）
- 边界扫描（扩大至高 `blend`）：
  - 出现失稳区与边界带
  - 失稳优先在高 `blend` 区出现，`phase_push` 主要塑造边界形状
- 手性差异（样例）：
  - `chirality = -1`：先丢“方向性”（`directionality_gap` 先掉线）
  - `chirality = +1`：先丢“本征-味位稳定性分层”（`stability_gap` 先掉线）
- 再入稳定区（样例）：
  - 在固定 `blend` 的某些窗口，`phase_push` 增大后先失稳，继续增大又恢复稳定
  - 表明 `phase_push` 可在局部重新拉开方向性差异

对应输出示例：

- 常规扫描：[sweep_summary.json](file:///Users/bytedance/TRAEProjects/mind/resonance_data/quark_color_flavor_mapping_sweep_20260409_154917/sweep_summary.json)
- 边界扫描：[boundary_summary.json](file:///Users/bytedance/TRAEProjects/mind/resonance_data/quark_color_flavor_mapping_boundary_scan_20260409_160103/boundary_summary.json)

## 6. 运行入口

单点实验（基线与特征分离）：

```bash
python3 quark_color_flavor_mapping_test.py
```

常规扫描（稳定窗与热图）：

```bash
python3 quark_color_flavor_mapping_sweep.py
```

边界扫描（失稳区与边界带）：

```bash
python3 quark_color_flavor_mapping_boundary_scan.py
```

局部高分辨率边界扫描（建议针对再入稳定区放大）：

```bash
python3 quark_color_flavor_mapping_boundary_scan.py \
  --blend-min 0.78 --blend-max 0.92 --blend-count 29 \
  --phase-push-min 0.20 --phase-push-max 0.45 --phase-push-count 26
```

## 7. 小结

- `3` 个本征位与 `6` 个味位的动力学分层在中低 `blend` 区稳定成立
- 高 `blend` 是主要失稳源，`phase_push` 调制边界并可能产生再入稳定现象
- 两种手性对应不同的失稳通道：`-1` 先丢方向性，`+1` 先丢自保持分层
- 实验提供了“映射假设”的数据支持与失稳边界定位方法，可用于进一步的理论对接与参数优化
