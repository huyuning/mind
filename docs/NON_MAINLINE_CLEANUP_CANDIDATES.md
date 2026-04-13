# 根目录非主线候选清理清单

本页用于整理当前仍保留在根目录、但不属于现行主线白名单的脚本，并区分：

- 哪些是应继续保留的专题入口
- 哪些只是探索性或局部验证脚本
- 哪些已经具备低风险归档条件

本页与 [CURRENT_MAINLINE_ROOT_MAP.md](file:///Users/bytedance/TRAEProjects/mind/docs/CURRENT_MAINLINE_ROOT_MAP.md) 配套使用：

- `CURRENT_MAINLINE_ROOT_MAP.md` 负责说明当前应保留关注的现行入口
- 本文件负责说明哪些文件可视为下一轮清理对象或已执行的非主线归档对象

---

## 一、判断标准

一个脚本被归为“非主线候选”，通常同时满足以下条件中的大部分：

- 未被 [README.md](file:///Users/bytedance/TRAEProjects/mind/README.md) 列为核心实验入口
- 未被 [10_EXPERIMENTS.md](file:///Users/bytedance/TRAEProjects/mind/docs/10_EXPERIMENTS.md) 列为当前推荐入口
- 未被 [CURRENT_MAINLINE_ROOT_MAP.md](file:///Users/bytedance/TRAEProjects/mind/docs/CURRENT_MAINLINE_ROOT_MAP.md) 列为核心主线或保留专题入口
- 没有其他主线脚本对其进行 `import`
- 与历史探索、中间版本、局部验证或一次性参数扫描更接近

---

## 二、仍建议保留在根目录的非主线专题

这些脚本虽然不是 README 第一批核心入口，但仍建议保留在根目录，因为它们代表了独立专题链，而不是简单的旧版本残留。

### 1. 两层三节点与层级专题

- [triad_two_layer_memory_scan.py](file:///Users/bytedance/TRAEProjects/mind/triad_two_layer_memory_scan.py)
- [triad_two_layer_memory_sweep.py](file:///Users/bytedance/TRAEProjects/mind/triad_two_layer_memory_sweep.py)
- [triad_two_layer_visualize_app.py](file:///Users/bytedance/TRAEProjects/mind/triad_two_layer_visualize_app.py)
- [triad_two_layer_cycle_watch.py](file:///Users/bytedance/TRAEProjects/mind/triad_two_layer_cycle_watch.py)
- [triad_complex_core_simulation.py](file:///Users/bytedance/TRAEProjects/mind/triad_complex_core_simulation.py)
- [triad_complex_fractal_simulation.py](file:///Users/bytedance/TRAEProjects/mind/triad_complex_fractal_simulation.py)

### 2. 光子样与 9 位专题

- [triad_photon_experiment.py](file:///Users/bytedance/TRAEProjects/mind/triad_photon_experiment.py)
- [second_layer_nine_positions_test.py](file:///Users/bytedance/TRAEProjects/mind/second_layer_nine_positions_test.py)

### 3. 色荷-味映射与 SU(3) 专题

- [quark_color_flavor_mapping_test.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_test.py)
- [quark_color_flavor_mapping_sweep.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_sweep.py)
- [quark_color_flavor_mapping_boundary_scan.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_boundary_scan.py)
- [quark_color_flavor_matrix_export.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_matrix_export.py)

### 4. 仍建议保留的专题探索

- [consciousness_experiment.py](file:///Users/bytedance/TRAEProjects/mind/consciousness_experiment.py)
- [cosmology_integration.py](file:///Users/bytedance/TRAEProjects/mind/cosmology_integration.py)
- [black_hole_analysis.py](file:///Users/bytedance/TRAEProjects/mind/black_hole_analysis.py)
- [refresh_data_experiment.py](file:///Users/bytedance/TRAEProjects/mind/refresh_data_experiment.py)
- [ring_memory.py](file:///Users/bytedance/TRAEProjects/mind/ring_memory.py)
- [mutual_attractor_experiment.py](file:///Users/bytedance/TRAEProjects/mind/mutual_attractor_experiment.py)
- [universal_attractor_test.py](file:///Users/bytedance/TRAEProjects/mind/universal_attractor_test.py)
- [noise_control_test.py](file:///Users/bytedance/TRAEProjects/mind/noise_control_test.py)
- [stability_test.py](file:///Users/bytedance/TRAEProjects/mind/stability_test.py)
- [long_term_test.py](file:///Users/bytedance/TRAEProjects/mind/long_term_test.py)

这些文件仍建议保留在根目录的原因是：

- 它们代表独立研究方向，而不是简单的旧版覆盖关系
- 其中部分脚本仍与 C/CUDA 或构建链有关
- 贸然归档会降低专题可发现性

---

## 三、低风险归档候选

下列脚本更接近探索期、中间版本或局部验证脚本，且当前未被主线文档和主线脚本直接依赖，已经迁入 `legacy/exploratory/`。

- [determinism_test.py](file:///Users/bytedance/TRAEProjects/mind/legacy/exploratory/determinism_test.py)
- [frequency_variation_test.py](file:///Users/bytedance/TRAEProjects/mind/legacy/exploratory/frequency_variation_test.py)
- [scan_variation_test.py](file:///Users/bytedance/TRAEProjects/mind/legacy/exploratory/scan_variation_test.py)
- [true_time_stability.py](file:///Users/bytedance/TRAEProjects/mind/legacy/exploratory/true_time_stability.py)
- [temp_range_test.py](file:///Users/bytedance/TRAEProjects/mind/legacy/exploratory/temp_range_test.py)
- [spontaneous_flip.py](file:///Users/bytedance/TRAEProjects/mind/legacy/exploratory/spontaneous_flip.py)
- [intrinsic_refresh_freq.py](file:///Users/bytedance/TRAEProjects/mind/legacy/exploratory/intrinsic_refresh_freq.py)
- [multi_address_oscillation.py](file:///Users/bytedance/TRAEProjects/mind/legacy/exploratory/multi_address_oscillation.py)
- [different_memory.py](file:///Users/bytedance/TRAEProjects/mind/legacy/exploratory/different_memory.py)
- [improved_experiment.py](file:///Users/bytedance/TRAEProjects/mind/legacy/exploratory/improved_experiment.py)
- [entanglement_resonance.py](file:///Users/bytedance/TRAEProjects/mind/legacy/exploratory/entanglement_resonance.py)
- [cyclic_pattern_mapping.py](file:///Users/bytedance/TRAEProjects/mind/legacy/exploratory/cyclic_pattern_mapping.py)

这些文件的共同特征：

- 仓库文档中未作为现行入口收录
- 没有被当前保留的主线脚本反向导入
- 更接近局部对照、参数扰动、一次性扫描或历史改进尝试

---

## 四、已执行的本轮收尾归档

为完成当前建议，本轮已将上面的低风险候选统一迁入：

- `legacy/exploratory/`

迁移后的目标是：

- 根目录更聚焦于现行主线和保留专题
- 探索期脚本仍可追溯，但不再干扰当前入口判断

---

## 五、清理后的使用建议

如果你现在要继续使用仓库，建议遵循：

1. 先看 [CURRENT_MAINLINE_ROOT_MAP.md](file:///Users/bytedance/TRAEProjects/mind/docs/CURRENT_MAINLINE_ROOT_MAP.md)
2. 如果只是跑主线，不要从本页列出的低风险归档候选开始
3. 如果要做历史对照或参数回溯，再去 `legacy/` 查找旧脚本

---

## 六、后续原则

后续若继续做目录清理，建议坚持两个原则：

- 先把“当前保留入口白名单”写清楚，再做迁移
- 凡是仍代表独立专题链的脚本，即使不是主线，也先保留在根目录

这样可以避免把“历史重复版本”和“仍在生长的专题链”混为一类。
