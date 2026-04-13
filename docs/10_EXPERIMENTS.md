# 实验入口页

本页用于承接当前项目的三层入口结构，把“应该跑哪个实验脚本、结果会写到哪里、不同实验分别回答什么问题”整理成一张实验导航图。

当前若需要判断实验结果可以被解释到什么程度，请同时参考 [THEORY_CANON.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_CANON.md) 中的“实验解释边界”一节。本页负责导航，不负责扩大实验结论的物理解释范围。

如果你还没有读过项目入口文档，建议先按下面顺序进入：

1. [00_OVERVIEW.md](file:///Users/bytedance/TRAEProjects/mind/docs/00_OVERVIEW.md)
2. [INDEX.md](file:///Users/bytedance/TRAEProjects/mind/docs/INDEX.md)
3. [GLOSSARY.md](file:///Users/bytedance/TRAEProjects/mind/docs/GLOSSARY.md)
4. [STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md)
5. [THEORY_FRAMEWORK.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_FRAMEWORK.md)
6. 再进入本页和对应实验脚本

## 一、与三层入口的关系

当前项目的入口层级可以理解为：

- [README.md](file:///Users/bytedance/TRAEProjects/mind/README.md)：项目入口页，只负责定位、主张、总导航
- [00_OVERVIEW.md](file:///Users/bytedance/TRAEProjects/mind/docs/00_OVERVIEW.md)：项目总览，用一页纸说明研究对象、统一主线、文档分层、实验分层
- [INDEX.md](file:///Users/bytedance/TRAEProjects/mind/docs/INDEX.md)：项目阅读地图，说明“先看什么、遇到什么问题去哪里找”
- [10_EXPERIMENTS.md](file:///Users/bytedance/TRAEProjects/mind/docs/10_EXPERIMENTS.md)：实验入口页，说明“具体跑什么、产出什么、结果去哪里看”

也就是说：

- 前三层入口负责理解项目
- 本页负责进入实验

## 二、当前核心实验主线

当前项目不把所有历史脚本都视为同等重要的入口，而是优先收束到五条核心实验主线。

### 1. 理论预测验证

目标：

- 把文档中的标准化预测转成统计量和可执行检验

主入口：

- [testable_predictions.py](file:///Users/bytedance/TRAEProjects/mind/testable_predictions.py)

主要回答：

- 理论文档中的预测是否被当前脚本显式实现
- 统计量、谱、相关性、窗口效应是否有统一输出

主要输出目录：

- `verification_data/`

常见输出文件：

- `verification_results_*.json`

### 2. RAM 完全图与临界窗口实验

目标：

- 在当前电脑 RAM 中构造完全图双态跳变实验
- 观察 `ratio = f_read / f_mem_proxy` 附近的临界窗口、相变和双态循环

主入口：

- [current_ram_complete_graph_experiment.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_complete_graph_experiment.py)
- [current_ram_phase_scan.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_phase_scan.py)

主要回答：

- 高于内存频率代理值读取时，是否出现双态循环跳变
- 临界窗口是否狭窄
- 参数改变后相图如何变化

主要输出目录：

- `resonance_data/`

常见输出文件和目录：

- `current_ram_complete_graph_*.json`
- `current_ram_phase_scan_*/phase_scan_*.json`
- `current_ram_phase_scan_*/phase_scan_*.png`

### 3. 层级、锁相、闭合共振实验

目标：

- 用张量漩涡和参数扫描，把“层级由公频锁相决定”落实到可视化和扫描报告中

主入口：

- [vortex_tensor_animation.py](file:///Users/bytedance/TRAEProjects/mind/vortex_tensor_animation.py)
- [hierarchy_flow_scan.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_flow_scan.py)

主要回答：

- 主轴扰动、壳层和闭合共振如何影响层级时间流速
- 哪些参数区域更平滑，哪些更分裂
- 稳定岛是否出现，以及如何随参数变化

主要输出目录：

- `resonance_data/`

常见输出文件和目录：

- `vortex_tensor_*/frame_*.png`
- `vortex_tensor_*/vortex_tensor_*.gif`
- `vortex_tensor_*/vortex_volume_*.npy`
- `vortex_tensor_*/meta_*.json`
- `vortex_tensor_*/hierarchy_metrics_*.npz`
- `hierarchy_flow_scan_*/report_*.json`
- `hierarchy_flow_scan_*/report_*.md`
- `hierarchy_flow_scan_*/smoothness_heatmap_*.png`
- `hierarchy_flow_scan_*/splitness_heatmap_*.png`
- `hierarchy_flow_scan_*/stable_fraction_heatmap_*.png`

### 4. 两层三节点内存阈值实验

目标：

- 用两层三节点全连接模型，把“核心同频核 + 内存阈值层 + 跨层一一对应耦合”落实到可运行仿真
- 观察核心层闭合、阈值层闭合与跨层锁相是否能够同时维持高值

主入口：

- [triad_two_layer_memory_scan.py](file:///Users/bytedance/TRAEProjects/mind/triad_two_layer_memory_scan.py)

主要回答：

- 第一层同频核心三角是否能稳定维持高闭合强度
- 第二层低于/等于/高于内存频率的三节点在跨层耦合下是否进入同一锁相窗口
- 哪些闭合和锁相统计量可以作为后续参数扫描的基线指标

主要输出目录：

- `resonance_data/`

常见输出文件和目录：

- `triad_two_layer_memory_scan_*/summary_*.json`
- `triad_two_layer_memory_scan_*/state_series_*.npz`
- `triad_two_layer_memory_scan_*/amplitudes_*.png`
- `triad_two_layer_memory_scan_*/phases_*.png`
- `triad_two_layer_memory_scan_*/closure_*.png`
- `triad_two_layer_memory_scan_*/locking_*.png`

当前最小验证结果：

- 结果样本见 [summary_20260408_181621.json](file:///Users/bytedance/TRAEProjects/mind/resonance_data/triad_two_layer_memory_scan_20260408_181621/summary_20260408_181621.json)
- 本次最小运行采用 `omega_core = 1.15`、`omega_mem = 1.00`、`omega_low = 0.92`、`omega_equal = 1.00`、`omega_high = 1.08`
- 核心层平均闭合强度 `core_closure_mean ≈ 72.21`，阈值层平均闭合强度 `mem_closure_mean ≈ 40.92`
- 跨层平均锁相强度 `cross_locking_mean ≈ 0.9204`
- 核心层强闭合占比 `strong_core_fraction = 1.0`，阈值层强闭合占比 `strong_mem_fraction ≈ 0.9467`
- 三组跨层对应锁相 `cross_s_l`、`cross_w_e`、`cross_a_h` 分别约为 `0.9934`、`0.9951`、`0.9985`，可作为后续 sweep 的基线参考

### 5. 概念可视化与定义对比

目标：

- 用最直接的图像方式，对比旧层级定义和新层级定义

主入口：

- [hierarchy_definition_comparison.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_definition_comparison.py)

主要回答：

- 旧定义为什么难以解释跨层级锁相
- 新定义如何把公频锁相和抽象概念放进同一结构

主要输出目录：

- `resonance_data/`

常见输出文件：

- `hierarchy_definition_comparison_*.png`

### 6+. 胞元虚拟计算宇宙（原型）

目标：

- 用“胞元 = 局域三维复态 + 局域 3x3 厄米矩阵 + 复边几何”实现最小虚拟宇宙原型
- 观察 `SU(3)` 分量、复边相位与三角闭合如何联动

主入口：

- [cellular_virtual_universe.py](file:///Users/bytedance/TRAEProjects/mind/cellular_virtual_universe.py)

常见输出与可视化说明：

- 可视化解释见 [CELLULAR_VIRTUAL_UNIVERSE_VISUALIZATION.md](file:///Users/bytedance/TRAEProjects/mind/docs/CELLULAR_VIRTUAL_UNIVERSE_VISUALIZATION.md)
- 三维结构优先阅读 `interactive_network_3d_*.html` 与 `interactive_surface_3d_*.html`，它们是对静态 3D 图的可旋转替代版本
- 典型图：
  - `mean_su3_components_*.png`：全体胞元的 `a1...a8` 平均演化
  - `closure_series_*.png`：三角闭合实部与相位的时间曲线
  - `final_a3_heatmap_*.png`：最终 `a3` 偏置场热图
  - `final_field_panels_*.png`：最终 `S/a3/a8` 三联图
  - `final_network_snapshot_*.png`：最终网络快照（边强度/相位 + 节点偏置）
  - `interactive_network_3d_*.html`：可旋转的 3D 胞元网络几何
  - `interactive_surface_3d_*.html`：可旋转的 3D 场形曲面
### 6. 色荷-味映射实验

目标：

- 用第二层 `9` 位结构验证“`3` 个对角位对应 `3` 个本征色荷，`6` 个非对角位对应 `6` 个有向味通道”的映射假设
- 观察该 `3+6` 分层在不同混合度和相位推进条件下是否稳定存在
- 扫描并定位 `mapping_supported` 从 `True` 掉到 `False` 的失稳区与边界带

主入口：

- [quark_color_flavor_mapping_test.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_test.py)
- [quark_color_flavor_mapping_sweep.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_sweep.py)
- [quark_color_flavor_mapping_boundary_scan.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_boundary_scan.py)

主要回答：

- `v11, v22, v33` 是否在动力学上自然形成 `3` 个本征稳定位
- `v12, v21, v13, v31, v23, v32` 是否在动力学上自然形成 `6` 个有向推理位
- `blend` 和 `phase_push` 如何共同决定 `3+6` 映射的稳定窗、边界带和失稳区

主要输出目录：

- `resonance_data/`

常见输出文件和目录：

- `quark_color_flavor_mapping_test_*/summary.json`
- `quark_color_flavor_mapping_test_*/nine_positions_metrics.csv`
- `quark_color_flavor_mapping_test_*/self_similarity_heatmap.png`
- `quark_color_flavor_mapping_test_*/asymmetry_heatmap.png`
- `quark_color_flavor_mapping_test_*/chirality_sensitivity_heatmap.png`
- `quark_color_flavor_mapping_test_*/feature_scatter.png`
- `quark_color_flavor_mapping_sweep_*/sweep_summary.json`
- `quark_color_flavor_mapping_sweep_*/sweep_points.csv`
- `quark_color_flavor_mapping_sweep_*/mapping_supported_chirality_*.png`
- `quark_color_flavor_mapping_boundary_scan_*/boundary_summary.json`
- `quark_color_flavor_mapping_boundary_scan_*/boundary_points.csv`
- `quark_color_flavor_mapping_boundary_scan_*/unstable_points.csv`
- `quark_color_flavor_mapping_boundary_scan_*/boundary_mask_chirality_*.png`
- `quark_color_flavor_mapping_boundary_scan_*/unstable_mask_chirality_*.png`

参数物理意义表：

| 参数 | 计算角色 | 物理/结构含义 | 增大后的主要效果 | 失稳含义 |
|---|---|---|---|---|
| `blend` | 控制非对角位中“派生味位”和“源/目标混合参考项”的权重比例 | 味位对本征位的贴附度、继承度、混合深度 | 味位越来越像源位和目标位的强混合体，`6` 个味通道逐步贴近 `3` 个本征位 | 当 `blend` 过高时，`3+6` 分层塌缩，味位失去独立通道身份，`mapping_supported` 容易掉到 `False` |
| `phase_push` | 控制非对角位相对于目标位的定向相位推进量 | 味位的方向性、流向性、手性可分辨度 | `i -> j` 与 `j -> i` 的相位骨架差异被拉开，味位的有向推理特征更明显 | 它通常不单独主导失稳，而是塑造边界形状；在某些窗口内过强或过弱都会削弱方向分离，也可能出现再入稳定区 |

使用建议：

- 低到中等 `blend` 更容易保持 `3` 个本征位与 `6` 个味位的清晰分层
- `phase_push` 更适合用来调方向性和边界形状，而不是单独追求“大就是强”
- 若要先找失稳边界，优先扩大 `blend` 范围；若要细看再入稳定区，再局部细扫 `phase_push`

当前样例结果：

- 单点实验样例见 [summary.json](file:///Users/bytedance/TRAEProjects/mind/resonance_data/quark_color_flavor_mapping_test_20260409_154257/summary.json)
- 常规扫描样例见 [sweep_summary.json](file:///Users/bytedance/TRAEProjects/mind/resonance_data/quark_color_flavor_mapping_sweep_20260409_154917/sweep_summary.json)
- 边界扫描样例见 [boundary_summary.json](file:///Users/bytedance/TRAEProjects/mind/resonance_data/quark_color_flavor_mapping_boundary_scan_20260409_160103/boundary_summary.json)
- 目前观察到高 `blend` 是主要失稳来源，`phase_push` 更像边界形状调节量，并在部分手性窗口中出现再入稳定现象

## 三、实验脚本优先级

当前仓库根目录下有大量历史实验和中间脚本。为了避免入口过多，建议按下面优先级使用：

### 第一优先级：当前主线入口

- [testable_predictions.py](file:///Users/bytedance/TRAEProjects/mind/testable_predictions.py)
- [current_ram_complete_graph_experiment.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_complete_graph_experiment.py)
- [current_ram_phase_scan.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_phase_scan.py)
- [vortex_tensor_animation.py](file:///Users/bytedance/TRAEProjects/mind/vortex_tensor_animation.py)
- [hierarchy_flow_scan.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_flow_scan.py)
- [triad_two_layer_memory_scan.py](file:///Users/bytedance/TRAEProjects/mind/triad_two_layer_memory_scan.py)
- [hierarchy_definition_comparison.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_definition_comparison.py)

### 第二优先级：专题实验

- [consciousness_filter_simulation.py](file:///Users/bytedance/TRAEProjects/mind/consciousness_filter_simulation.py)
- [quark_color_flavor_mapping_test.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_test.py)
- [quark_color_flavor_mapping_sweep.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_sweep.py)
- [quark_color_flavor_mapping_boundary_scan.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_boundary_scan.py)

说明：

- 该脚本对应“意识选择滤波”专题
- 当前是独立专题实验，还没有并入主入口实验链
- 输出主要写入 `verification_data/`
- 色荷-味映射脚本对应“强相互作用结构重解释”专题
- 当前也是独立专题实验，主要输出写入 `resonance_data/`

### 第三优先级：历史脚本与探索性脚本

说明：

- 根目录中其余大量 `hamming_*`、`resonance_*`、`entanglement_*`、`*_test.py`、`*_experiment.py` 文件，更多属于历史探索、中间版本或局部问题验证
- 它们目前不作为项目的首选入口
- 已确认的重复版本正逐步迁移到 [legacy/README.md](file:///Users/bytedance/TRAEProjects/mind/legacy/README.md) 所说明的历史目录
- 已迁移的第二批包括旧版 `resonance_cartesian*.py` 变体和 `multi_graph_fixed_freq.py`
- 已迁移的第三批包括 `resonance_experiment.py`、`resonance_multi_iter.py`、`resonance_trace.py`、`resonance_trace_v2.py`
- 已迁移的第四批包括 `hamming_correct.py`、`hamming_double_*.py`、`hamming_entanglement_fix*.py`、`hamming_std_1k.py`
- 已迁移的第五批包括 `resonance_stable.py`
- 已迁移的第六批包括若干低耦合探索脚本，它们现统一位于 `legacy/exploratory/`
- 若你只需要标准汉明码入口，优先使用 [hamming_experiment.py](file:///Users/bytedance/TRAEProjects/mind/hamming_experiment.py)
- 若你需要汉明码验证入口，请使用 [verify_hamming.py](file:///Users/bytedance/TRAEProjects/mind/verify_hamming.py)
- 若你需要保留在根目录的汉明码专题脚本，请使用 [hamming_entanglement.py](file:///Users/bytedance/TRAEProjects/mind/hamming_entanglement.py) 与 [hamming_resonance_correct.py](file:///Users/bytedance/TRAEProjects/mind/hamming_resonance_correct.py)
- 若你需要查看旧版纠缠翻转和旧版汉明码变体，请到 `legacy/entanglement/` 与 `legacy/hamming/` 中查找
- 若你需要查看旧版笛卡尔积翻转实验或旧版图结构变体，请到 `legacy/cartesian/` 与 `legacy/graphs/` 中查找
- 若你需要查看旧版共振翻转、追踪与稳定性脚本，请到 `legacy/resonance/` 中查找；当前这一组保留入口为 [resonance_iter_v2.py](file:///Users/bytedance/TRAEProjects/mind/resonance_iter_v2.py)
- 若你需要查看低耦合的探索期参数扫描与局部验证脚本，请到 `legacy/exploratory/` 中查找

## 四、输出目录地图

### 1. `verification_data/`

定位：

- 偏向标准化验证、统计结果、意识选择滤波等结果输出

当前典型内容：

- `verification_results_*.json`
- `consciousness_filter_simulation_*.json`

适合查看：

- 预测检验结果
- 概率分布和验证型 JSON 结果

### 2. `resonance_data/`

定位：

- 当前最主要的实验输出目录

当前典型内容：

- RAM 完全图实验结果
- 临界窗口相图
- 张量漩涡动画帧、GIF、体数据
- 层级扫描热图与报告
- 两层三节点核心层/阈值层闭合与跨层锁相结果
- 层级定义对比图

适合查看：

- 图像结果
- 扫描报告
- 动画与体数据
- 当前主线实验的大多数输出

### 3. `improved_data/`

定位：

- 较早阶段的改进实验结果和中间结果

说明：

- 该目录暂时保留
- 当前不作为主线实验入口目录
- 更适合作为历史结果或辅助对照使用

## 五、按问题找实验

- 想看理论预测怎么落地：先看 [testable_predictions.py](file:///Users/bytedance/TRAEProjects/mind/testable_predictions.py)
- 想看内存频率阈值、双态跳变和临界窗口：先看 [current_ram_complete_graph_experiment.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_complete_graph_experiment.py) 和 [current_ram_phase_scan.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_phase_scan.py)
- 想看层级、公频锁相、闭合共振和稳定岛：先看 [vortex_tensor_animation.py](file:///Users/bytedance/TRAEProjects/mind/vortex_tensor_animation.py) 和 [hierarchy_flow_scan.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_flow_scan.py)
- 想看三节点主体核如何与低于/等于/高于内存阈值层耦合：先看 [triad_two_layer_memory_scan.py](file:///Users/bytedance/TRAEProjects/mind/triad_two_layer_memory_scan.py)
- 想快速理解新旧层级定义差异：先看 [hierarchy_definition_comparison.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_definition_comparison.py)
- 想看意识选择滤波的概率分布演示：先看 [consciousness_filter_simulation.py](file:///Users/bytedance/TRAEProjects/mind/consciousness_filter_simulation.py)
- 想看 `3` 个色荷样本征位与 `6` 个味样推理位如何随参数稳定或失稳：先看 [quark_color_flavor_mapping_test.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_test.py)、[quark_color_flavor_mapping_sweep.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_sweep.py) 和 [quark_color_flavor_mapping_boundary_scan.py](file:///Users/bytedance/TRAEProjects/mind/quark_color_flavor_mapping_boundary_scan.py)

## 六、最小运行入口

如果你只想快速进入当前主线实验，可优先运行下面几条命令：

```bash
python3 testable_predictions.py
python3 current_ram_complete_graph_experiment.py
python3 current_ram_phase_scan.py
python3 triad_two_layer_memory_scan.py --duration 12 --dt 0.04
python3 hierarchy_definition_comparison.py
```

如果你要进入层级/闭合实验主线，再运行：

```bash
python3 vortex_tensor_animation.py
python3 hierarchy_flow_scan.py
```

## 七、当前整理原则

- 一个实验入口页：本页只保留当前主线实验和输出目录地图
- 一个主输出目录：当前主线实验优先写入 `resonance_data/` 和 `verification_data/`
- 历史脚本不删除，但不继续作为默认入口
- 后续会继续补充实验参数说明、输出文件格式说明和历史实验归档说明
