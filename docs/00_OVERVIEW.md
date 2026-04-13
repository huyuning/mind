# 项目总览

本页是整个项目的“一页纸说明”。如果你第一次进入仓库，或想快速理解这个项目到底研究什么、理论主线是什么、文档应该怎么读，请先看这里。

当前项目的正式名称统一为：`胞元基底结构动力学研究引擎`，英文名为 `Cellular-Substrate Structural Dynamics Engine`，简称 `CSDE`。

当前若遇到多份文档口径不一致，请先看 [THEORY_CANON.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_CANON.md)；正式定义仍以 [STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md) 为准。

如果你更关心“当前根目录里到底哪些脚本是现行主线、哪些只是专题或辅助脚本”，请先看 [CURRENT_MAINLINE_ROOT_MAP.md](file:///Users/bytedance/TRAEProjects/mind/docs/CURRENT_MAINLINE_ROOT_MAP.md)。
如果你更关心“哪些剩余脚本属于非主线候选、哪些已被进一步归档”，请看 [NON_MAINLINE_CLEANUP_CANDIDATES.md](file:///Users/bytedance/TRAEProjects/mind/docs/NON_MAINLINE_CLEANUP_CANDIDATES.md)。
如果你需要快速了解本项目与标准物理的边界、命名口径与可比性范围，请看 [EFFECTIVE_MODEL_STATEMENT.md](file:///Users/bytedance/TRAEProjects/mind/docs/EFFECTIVE_MODEL_STATEMENT.md)。
如果你需要快速把点、线、面、体、场、谱、态空间等分析视角对应到当前代码结构，请看 [MODEL_ANALYSIS_HIERARCHY.md](file:///Users/bytedance/TRAEProjects/mind/docs/MODEL_ANALYSIS_HIERARCHY.md)。

## 一、项目研究对象

这个项目试图把以下几个问题放进同一套理论与实验框架中：

- 物理对象、生命对象、认知对象和抽象对象，是否都可以被看作某种稳定的动态锁相结构
- 层级究竟是先验几何标签，还是由动态耦合与锁相关系生成
- 抽象概念是否可以理解为跨层级锁相后的高阶稳定模态
- 内存刷新频率、锁相条件与读取频率之间的关系，是否能够解释稳定显现、覆写筛选、意识窗口和相变现象
- 完全图、扫频、闭合共振、层级时间流速等实验，能否为上述理论提供机制验证

因此，本项目不是单一的“物理学文档”或“仿真实验集合”，而是一个同时包含：

- 理论整理
- 数学形式化
- 术语统一
- 机制实验
- 可视化对比

的综合研究仓库。

在当前语境下，更准确地说，项目正在朝一个以胞元、闭合相、轴节点、共轴簇和连续势场为原生对象的 `CSDE` 研究平台收敛，而不是继续停留在零散脚本和切片式分析的组合状态。

## 二、统一主线

当前项目以一条统一主线组织：

`第一性结构 -> 数学展开 -> 计算场 -> 稳定模式 -> 锁相 -> 层级 -> 跨层级锁相 -> 抽象概念 -> 意识/现实显现`

这条主线包含四个关键修正：

### 1. 第一性的重新表述

第一性不再被理解为某个具体粒子、具体对象或单一事件，而被理解为一种可生成、可分化、可锁相、可投影的**数学展开结构**。

这意味着：

- 线性代数主要表达结构展开
- 微积分主要表达过程展开
- 概率论主要表达显态展开后的统计压缩

因此，数学在本项目中不只是描述工具，也被视为第一性结构的展开语言。

### 2. 层级的新定义

层级不再被理解为先验整数层号或纯几何分层，而是由**锁相后的公频等价类**定义。

也就是说：

- 同一层级中的对象共享近似相同的有效主频
- 它们在一定时间窗内保持相位差有界
- 整数层号只是对这些锁相簇排序后的派生标签

当前进一步采用的几何图像是：

- 所有层级都可理解为**锁相球壳的嵌套与交织**
- 越微观，单位尺度内球壳嵌套越密集、壳面间距越小
- 越宏观，球壳之间的交织、闭合、跨层映射和抽象稳定模态越复杂

当前还采用一条对应的时间解释提要：

- 越微观，锁相壳层之间的有效距离更短，因此信息传播路径更短、相位同步更快、锁相频率更高
- 越宏观，更多受跨壳层相位传播与长程闭合耦合影响，因此显现为较低频、较慢的时空展开

因此，层级不是“从微观到宏观的一串离散盒子”，而更像是一组密度和复杂度同时变化的锁相球壳网络。

### 3. 跨层级锁相

不同层级对象并不彼此隔离。只要它们围绕某个更高阶共同主频完成稳定锁相，就能进入同一个更高阶结构。

这意味着：

- 跨层级关系不只是“映射”或“投影”
- 它也可以是动态共振与稳定耦合

### 4. 抽象概念的来源

抽象概念不是脱离具体对象的纯符号，而是跨层级锁相后的**稳定高阶模态**。

这使得“抽象概念”可以被统一放入：

- 物理层
- 生物层
- 神经层
- 语言层
- 社会层

的连续主线中理解。

## 三、理论主轴

项目目前主要围绕三条理论主轴展开。

### A. 计算场与稳定模式

这是最底层的本体框架。

- 计算场被视为更微观的统一动态本体
- 粒子、结构、模式、记忆与概念，都可以被视为稳定模式或稳定耦合态
- 这里的“稳定”不是静止，而是动态锁相和持续自洽

### B. 频率—内存阈值与意识窗口

这是现实显现与认知现象的桥梁。

- 当过程频率高于内存刷新频率时，结构可能被覆写或失稳
- 当过程频率与内存机制进入特定共振窗时，可能形成稳定显现或意识窗口
- RAM 完全图实验与相图实验，目前就是这一主轴的实验入口

### C. 层级、闭合与跨层级抽象

这是当前重构的核心。

- 层级由公频锁相决定
- 闭合锁相决定层级时间流速和导数
- 跨层级锁相形成抽象概念
- 张量漩涡、闭合共振、层级时间流速扫描都属于这一主轴

## 四、文档分层

为避免“同一个概念在不同文档里多次重复定义”，当前文档被分成四层。

### 1. 正式定义层

- [CURRENT_MAINLINE_ROOT_MAP.md](file:///Users/bytedance/TRAEProjects/mind/docs/CURRENT_MAINLINE_ROOT_MAP.md)

作用：

- 汇总当前根目录保留的主线脚本、专题入口、辅助脚本和历史目录
- 用于快速判断哪些文件应优先关注
- [THEORY_CANON.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_CANON.md)

作用：

- 给出当前理论规范、符号裁决顺序和实验解释边界
- 用来分清哪些是现行定义，哪些只是历史或叙事材料
- [STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md)

作用：

- 唯一正式数学定义源
- 公式、符号、锁相条件、层级定义、闭合条件都以此为准

### 2. 术语层

- [GLOSSARY.md](file:///Users/bytedance/TRAEProjects/mind/docs/GLOSSARY.md)
- [STRONG_INTERACTION_TERMINOLOGY_TABLE.md](file:///Users/bytedance/TRAEProjects/mind/docs/STRONG_INTERACTION_TERMINOLOGY_TABLE.md)

作用：

- 唯一统一术语源
- 解释“计算场、层级、公频锁相、跨层级锁相、抽象概念、意识窗口”等术语
- 强相互作用专题术语表用于补充“夸克、强子、色中性、胶子样中间相、强作用闭合度”等专项概念

### 3. 叙事解释层

- [THEORY_FRAMEWORK.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_FRAMEWORK.md)

作用：

- 用较直观的方式解释整体世界观和结构图景
- 适合先理解整体意义，再回到正式定义层
- 仅保留叙事解释职责，不承担正式裁决职责

### 4. 历史来源层

- [SIMULATION_REALITY_DUALITY.md](file:///Users/bytedance/TRAEProjects/mind/docs/SIMULATION_REALITY_DUALITY.md)

作用：

- 保留项目较早阶段的理论版本
- 用于版本对照和概念演化追踪
- 其中的旧符号和旧建模语言不再自动视为现行规范

### 5. 分析映射层

- [MODEL_ANALYSIS_HIERARCHY.md](file:///Users/bytedance/TRAEProjects/mind/docs/MODEL_ANALYSIS_HIERARCHY.md)

作用：

- 把点、线、面、体、场、谱、态空间、信息与层级视角统一映射到当前代码结构
- 用于回答“当前理论层次在代码里落在哪里、成熟度如何、下一步优先补哪一层”

## 五、实验分层

目前实验大致分为四类。

### 1. 理论预测验证

- [testable_predictions.py](file:///Users/bytedance/TRAEProjects/mind/testable_predictions.py)

对应：

- 预测定义与统计量检验
- 文档公式和实验输出的连接层

### 2. RAM 完全图实验

- [current_ram_complete_graph_experiment.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_complete_graph_experiment.py)
- [current_ram_phase_scan.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_phase_scan.py)

对应：

- 读取频率与内存频率代理值之间的竞争
- 双态跳变
- 临界窗口与相图

### 3. 层级/锁相/闭合实验

- [vortex_tensor_animation.py](file:///Users/bytedance/TRAEProjects/mind/vortex_tensor_animation.py)
- [hierarchy_flow_scan.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_flow_scan.py)

对应：

- 张量共振
- 主轴扰动
- 闭合共振
- 层级时间流速
- 参数扫描

### 4. 概念可视化与定义对比

- [hierarchy_definition_comparison.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_definition_comparison.py)

对应：

- 旧层级定义与新层级定义的对比
- 跨层级锁相解释的结构化展示

## 六、CSDE 核心模块待办

围绕 `胞元基底结构动力学研究引擎（CSDE）`，当前最核心的待办模块可整理为以下六组：

这六组模块存在明确依赖链：`状态本体层 -> 事件与持久化层 -> 轴谱与层级层 -> 连续场重建层 -> 观测与可视化层 / 验证与实验编排层`。其中观测层与实验编排层都依赖前四层的统一状态与字段定义，而不是各自独立生长。

### 1. 状态本体层

- `CellNode`：统一胞元位置、相位、频率、振幅、半径、层级、父子关系与激活状态
- `EngineState`：统一保存每一时刻的胞元、闭合事件、轴节点、场变量与观测缓存
- `Snapshot / Replay`：支持状态快照、时间回放与断点续跑

### 2. 事件与持久化层

- `ClosureEvent`：将瞬时闭合相检测结果提升为正式事件对象
- `Closure Persistence Engine`：定义闭合相的强化、衰减、退役和继承规则
- `EventLog`：统一记录出生、合并、共轴、失活与层级跃迁

### 3. 轴谱与层级层

- `AxisNode`：稳定闭合相持久化后的轴心对象
- `CoaxialCluster`：多轴共轴聚类、父子关系与递归生成规则
- `Hierarchy Builder`：把多层级闭合关系整理为可回溯结构树

### 4. 连续场重建层

- `AxisSpectrumField`：从离散轴节点重建连续轴谱密度场
- `MassTensorField`：输出 `M_total / M_parallel / M_perp` 等方向性质量代理
- `GravityPotentialField`：从轴谱密度与相干度生成宏观汇聚势场
- `EMResponseField`：用于后续研究不同波段调制相的轴向耦合与吸收响应

### 5. 观测与可视化层

- 高性能主观察器：替代当前以 Plotly 为主的重型 3D 观察路径
- 事件图与层级树观察器：直接查看闭合相、轴节点和共轴簇的生成链
- 结构视图导出：保留静态图、GIF、HTML 作为导出层，而非主研究层

### 6. 验证与实验编排层

- 参数扫描引擎：围绕闭合阈值、共轴阈值、核尺度等做系统扫描
- 假设验证器：统一跑“质量张量”“引力势”“电子样模态”等命题
- 模型边界报告：明确哪些结论属于 `CSDE` 有效模型语言，哪些可以与标准物理做形式比对

## 七、推荐阅读顺序

如果你是第一次接触项目，建议按下面的统一顺序阅读：

1. [00_OVERVIEW.md](file:///Users/bytedance/TRAEProjects/mind/docs/00_OVERVIEW.md)
2. [INDEX.md](file:///Users/bytedance/TRAEProjects/mind/docs/INDEX.md)
3. [CURRENT_MAINLINE_ROOT_MAP.md](file:///Users/bytedance/TRAEProjects/mind/docs/CURRENT_MAINLINE_ROOT_MAP.md)
4. [THEORY_CANON.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_CANON.md)
5. [EFFECTIVE_MODEL_STATEMENT.md](file:///Users/bytedance/TRAEProjects/mind/docs/EFFECTIVE_MODEL_STATEMENT.md)
6. [GLOSSARY.md](file:///Users/bytedance/TRAEProjects/mind/docs/GLOSSARY.md)
7. [STRONG_INTERACTION_TERMINOLOGY_TABLE.md](file:///Users/bytedance/TRAEProjects/mind/docs/STRONG_INTERACTION_TERMINOLOGY_TABLE.md)
8. [STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md)
9. [THEORY_FRAMEWORK.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_FRAMEWORK.md)
10. 再进入对应实验脚本与输出数据

如果你只想看“层级定义修正”：

1. [GLOSSARY.md](file:///Users/bytedance/TRAEProjects/mind/docs/GLOSSARY.md)
2. [STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md)
3. [SIMULATION_REALITY_DUALITY.md](file:///Users/bytedance/TRAEProjects/mind/docs/SIMULATION_REALITY_DUALITY.md)
4. [hierarchy_definition_comparison.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_definition_comparison.py)

## 八、当前重构状态

当前第一阶段重构已经完成：

- README 已收缩为项目入口页
- INDEX 已升级为项目阅读地图
- CURRENT_MAINLINE_ROOT_MAP 已补充当前根目录主线脚本清单
- THEORY_CANON 已作为当前理论规范页建立
- OVERVIEW 作为一页纸总览建立
- 正式定义层、术语层、叙事层、历史层职责已经分离

后续将继续进行：

- 实验入口页整理
- 目录结构整理
- 历史脚本归档
- 统一实验文档
