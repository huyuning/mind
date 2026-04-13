# 根目录现行主线脚本清单

本页用于回答一个实际问题：

- 当前仓库根目录里，哪些文件属于现行主线
- 哪些是理论文档入口
- 哪些是实验入口
- 哪些虽然还保留在根目录，但属于专题、辅助或工具脚本

本页只描述当前整理后的有效入口结构，不替代理论规范页，也不替代实验导航页。

若你还想继续追踪“哪些剩余脚本不属于主线、哪些已被收尾归档”，请配合阅读 [NON_MAINLINE_CLEANUP_CANDIDATES.md](file:///Users/bytedance/TRAEProjects/mind/docs/NON_MAINLINE_CLEANUP_CANDIDATES.md)。

---

## 一、总原则

当前根目录文件按四类理解：

- 核心主线：README 中明确列出的当前主线入口
- 理论文档：`docs/` 下承担现行定义、术语和阅读导航职责的文档
- 实验入口：用于直接运行当前实验主线的脚本
- 专题/辅助脚本：仍保留在根目录，但不属于第一优先级主线入口

历史脚本、重复版本和旧实验链已逐步迁入 [legacy/README.md](file:///Users/bytedance/TRAEProjects/mind/legacy/README.md) 所说明的目录结构中。

---

## 二、核心主线

这些文件构成当前项目最核心的阅读与运行路径。

### 1. 项目入口

- [README.md](file:///Users/bytedance/TRAEProjects/mind/README.md)
  - 作用：项目总入口、核心主张、主线实验入口

### 2. 核心实验主线

- [testable_predictions.py](file:///Users/bytedance/TRAEProjects/mind/testable_predictions.py)
  - 作用：理论预测验证主入口
- [current_ram_complete_graph_experiment.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_complete_graph_experiment.py)
  - 作用：RAM 完全图双态实验
- [current_ram_phase_scan.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_phase_scan.py)
  - 作用：RAM 临界窗口相图细扫
- [vortex_tensor_animation.py](file:///Users/bytedance/TRAEProjects/mind/vortex_tensor_animation.py)
  - 作用：张量漩涡、闭合共振与壳层结构演示
- [hierarchy_flow_scan.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_flow_scan.py)
  - 作用：层级时间流速扫描
- [hierarchy_definition_comparison.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_definition_comparison.py)
  - 作用：旧层级定义与新层级定义对比图

---

## 三、理论文档

这些文件不在根目录脚本区，但构成当前项目的现行理论主线。

### 1. 规范与定义层

- [THEORY_CANON.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_CANON.md)
  - 当前理论规范、裁决顺序与解释边界
- [STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md)
  - 全项目唯一正式数学定义源
- [GLOSSARY.md](file:///Users/bytedance/TRAEProjects/mind/docs/GLOSSARY.md)
  - 统一术语源

### 2. 导航层

- [00_OVERVIEW.md](file:///Users/bytedance/TRAEProjects/mind/docs/00_OVERVIEW.md)
  - 一页纸总览
- [INDEX.md](file:///Users/bytedance/TRAEProjects/mind/docs/INDEX.md)
  - 阅读地图
- [10_EXPERIMENTS.md](file:///Users/bytedance/TRAEProjects/mind/docs/10_EXPERIMENTS.md)
  - 实验入口导航

### 3. 补充定义与专题层

- [HIERARCHICAL_RECURSION_DEFINITION.md](file:///Users/bytedance/TRAEProjects/mind/docs/HIERARCHICAL_RECURSION_DEFINITION.md)
  - 层级与有效投影位递推主文档
- [EFFECTIVE_PROJECTION_COUNT_DEFINITION.md](file:///Users/bytedance/TRAEProjects/mind/docs/EFFECTIVE_PROJECTION_COUNT_DEFINITION.md)
  - 有效投影位计数抽取版
- [STRONG_INTERACTION_TERMINOLOGY_TABLE.md](file:///Users/bytedance/TRAEProjects/mind/docs/STRONG_INTERACTION_TERMINOLOGY_TABLE.md)
  - 强相互作用相关专题术语表
- [COLOR_FLAVOR_MAPPING_EXPERIMENT.md](file:///Users/bytedance/TRAEProjects/mind/docs/COLOR_FLAVOR_MAPPING_EXPERIMENT.md)
  - 色荷-味映射实验专题

### 4. 叙事与历史层

- [THEORY_FRAMEWORK.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_FRAMEWORK.md)
  - 当前仅承担叙事解释职责
- [SIMULATION_REALITY_DUALITY.md](file:///Users/bytedance/TRAEProjects/mind/docs/SIMULATION_REALITY_DUALITY.md)
  - 当前仅作为历史来源保留

---

## 四、现行实验入口

这部分脚本仍在根目录，且具有明确入口意义。

### 1. 主线实验入口

- [testable_predictions.py](file:///Users/bytedance/TRAEProjects/mind/testable_predictions.py)
- [current_ram_complete_graph_experiment.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_complete_graph_experiment.py)
- [current_ram_phase_scan.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_phase_scan.py)
- [vortex_tensor_animation.py](file:///Users/bytedance/TRAEProjects/mind/vortex_tensor_animation.py)
- [hierarchy_flow_scan.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_flow_scan.py)
- [hierarchy_definition_comparison.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_definition_comparison.py)

### 2. 当前保留的共振入口

- [resonance_iter_v2.py](file:///Users/bytedance/TRAEProjects/mind/resonance_iter_v2.py)
  - 当前共振翻转/迭代这一组的保留入口
- [resonance_cartesian_complete.py](file:///Users/bytedance/TRAEProjects/mind/resonance_cartesian_complete.py)
  - 当前笛卡尔积翻转实验保留入口
- [resonance_visualize.py](file:///Users/bytedance/TRAEProjects/mind/resonance_visualize.py)
  - 与 `resonance_cartesian_complete.py` 配套的可视化入口

### 3. 当前保留的汉明码入口

- [hamming_experiment.py](file:///Users/bytedance/TRAEProjects/mind/hamming_experiment.py)
  - 标准汉明码实验入口
- [verify_hamming.py](file:///Users/bytedance/TRAEProjects/mind/verify_hamming.py)
  - 汉明码验证入口
- [hamming_entanglement.py](file:///Users/bytedance/TRAEProjects/mind/hamming_entanglement.py)
  - 汉明码纠缠专题入口
- [hamming_resonance_correct.py](file:///Users/bytedance/TRAEProjects/mind/hamming_resonance_correct.py)
  - 汉明码共振校正专题入口

### 4. 当前保留的图结构入口

- [multi_graph_test.py](file:///Users/bytedance/TRAEProjects/mind/multi_graph_test.py)
  - 当前图结构主线与对照组测试入口

### 5. 当前保留的纠缠翻转入口

- [entanglement_flip_v4.py](file:///Users/bytedance/TRAEProjects/mind/entanglement_flip_v4.py)
  - 纠缠翻转系列当前保留版本

---

## 五、专题实验脚本

这些脚本仍保留在根目录，通常用于专题验证、结构映射或附加可视化，不属于 README 中最核心的第一批主线入口。

### 1. 两层三节点与层级专题

- [triad_two_layer_memory_scan.py](file:///Users/bytedance/TRAEProjects/mind/triad_two_layer_memory_scan.py)
- [triad_two_layer_memory_sweep.py](file:///Users/bytedance/TRAEProjects/mind/triad_two_layer_memory_sweep.py)
- [triad_two_layer_visualize_app.py](file:///Users/bytedance/TRAEProjects/mind/triad_two_layer_visualize_app.py)
- [triad_two_layer_cycle_watch.py](file:///Users/bytedance/TRAEProjects/mind/triad_two_layer_cycle_watch.py)
- [triad_complex_core_simulation.py](file:///Users/bytedance/TRAEProjects/mind/triad_complex_core_simulation.py)
- [triad_complex_fractal_simulation.py](file:///Users/bytedance/TRAEProjects/mind/triad_complex_fractal_simulation.py)

### 2. 光子样三元核与 9 位结构专题

- [triad_photon_experiment.py](file:///Users/bytedance/TRAEProjects/mind/triad_photon_experiment.py)
- [second_layer_nine_positions_test.py](file:///Users/bytedance/TRAEProjects/mind/second_layer_nine_positions_test.py)

### 3. 色荷-味映射、SU(3) 与胞元宇宙专题

- [quark_color_flavor_mapping_test.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_test.py)
- [quark_color_flavor_mapping_sweep.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_sweep.py)
- [quark_color_flavor_mapping_boundary_scan.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_boundary_scan.py)
- [quark_color_flavor_matrix_export.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_matrix_export.py)
- [cellular_virtual_universe.py](file:///Users/bytedance/TRAEProjects/mind/cellular_virtual_universe.py)
- [CELLULAR_VIRTUAL_UNIVERSE_VISUALIZATION.md](file:///Users/bytedance/TRAEProjects/mind/docs/CELLULAR_VIRTUAL_UNIVERSE_VISUALIZATION.md)

---

## 六、辅助与工具脚本

这些文件目前仍在根目录，但主要承担采集、分析、绘图、设备侧支持或局部验证功能，不建议作为项目第一入口。

### 1. 采集与硬件侧

- [hardware_collector.py](file:///Users/bytedance/TRAEProjects/mind/hardware_collector.py)
- [cuda_memory_monitor.py](file:///Users/bytedance/TRAEProjects/mind/cuda_memory_monitor.py)
- [memory_bit_flip_test.cu](file:///Users/bytedance/TRAEProjects/mind/memory_bit_flip_test.cu)
- [bit_ops.c](file:///Users/bytedance/TRAEProjects/mind/bit_ops.c)
- [bit_ops.h](file:///Users/bytedance/TRAEProjects/mind/bit_ops.h)
- [flip_level.c](file:///Users/bytedance/TRAEProjects/mind/flip_level.c)
- [flip_level.h](file:///Users/bytedance/TRAEProjects/mind/flip_level.h)
- [build.sh](file:///Users/bytedance/TRAEProjects/mind/build.sh)

### 2. 结构验证与局部对照

- [complete_graph_robustness.py](file:///Users/bytedance/TRAEProjects/mind/complete_graph_robustness.py)
- [ascii_complete_graph.py](file:///Users/bytedance/TRAEProjects/mind/ascii_complete_graph.py)
- [graph_string_derivation.py](file:///Users/bytedance/TRAEProjects/mind/graph_string_derivation.py)
- [constant_verification.py](file:///Users/bytedance/TRAEProjects/mind/constant_verification.py)
- [analyze_lost.py](file:///Users/bytedance/TRAEProjects/mind/analyze_lost.py)

### 3. 其他仍在根目录的探索脚本

- 诸如 `consciousness_*`、`cosmology_*`、`refresh_*`、`ring_memory.py`、`mutual_attractor_experiment.py`、`universal_attractor_test.py`、`noise_control_test.py`、`stability_test.py`、`long_term_test.py` 等脚本，当前更接近探索性或局部问题验证，不建议视为项目主线入口。

---

## 七、历史目录

已经归档的旧脚本主要位于：

- [legacy/README.md](file:///Users/bytedance/TRAEProjects/mind/legacy/README.md)
- `legacy/entanglement/`
- `legacy/exploratory/`
- `legacy/hamming/`
- `legacy/cartesian/`
- `legacy/graphs/`
- `legacy/resonance/`

如果你需要追踪版本演化、比较旧实验与新入口，优先从 `legacy/README.md` 开始。

---

## 八、最短使用建议

如果你只想抓住当前项目最重要的入口，建议按下面顺序：

1. 先读 [README.md](file:///Users/bytedance/TRAEProjects/mind/README.md)
2. 再看 [00_OVERVIEW.md](file:///Users/bytedance/TRAEProjects/mind/docs/00_OVERVIEW.md) 与 [INDEX.md](file:///Users/bytedance/TRAEProjects/mind/docs/INDEX.md)
3. 若要确认理论标准，读 [THEORY_CANON.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_CANON.md) 与 [STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md)
4. 若要直接跑主线实验，从下面 6 个脚本开始：
   - [testable_predictions.py](file:///Users/bytedance/TRAEProjects/mind/testable_predictions.py)
   - [current_ram_complete_graph_experiment.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_complete_graph_experiment.py)
   - [current_ram_phase_scan.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_phase_scan.py)
   - [vortex_tensor_animation.py](file:///Users/bytedance/TRAEProjects/mind/vortex_tensor_animation.py)
   - [hierarchy_flow_scan.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_flow_scan.py)
   - [hierarchy_definition_comparison.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_definition_comparison.py)
