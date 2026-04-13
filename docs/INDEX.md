# 项目阅读地图

本页不只是文档索引，而是当前项目的**阅读地图**：说明核心理论主线是什么、每份文档负责什么、先看什么、遇到什么问题去哪里找。

当前项目的正式名称统一为：`胞元基底结构动力学研究引擎`，英文名 `Cellular-Substrate Structural Dynamics Engine`，简称 `CSDE`。
一句话定位：`CSDE` 是一个以胞元、闭合相、轴节点、共轴簇和连续势场为原生对象的结构动力学研究引擎，用于探索多层级涌现、质量代理与宏观汇聚等现象。

## 一、项目主线

当前项目以一条统一主线组织：

`第一性结构 -> 数学展开 -> 计算场 -> 稳定模式 -> 锁相 -> 层级 -> 跨层级锁相 -> 抽象概念 -> 意识/现实显现`

其中最重要的修正是：

- 第一性不再被理解为某个具体粒子、具体对象或单一事件，而是可生成、可分化、可锁相、可投影的**数学展开结构**。
- 线性代数、微积分、概率论分别对应结构展开、过程展开与显态统计压缩。
- 层级不是先验整数编号，而是由**锁相后的公频等价类**定义。
- 不同层级对象仍可围绕共同公频完成**跨层级锁相**。
- 抽象概念不是脱离对象的标签，而是跨层级锁相后形成的**稳定高阶模态**。

## 二、阅读入口

- 项目总览：[00_OVERVIEW.md](file:///Users/bytedance/TRAEProjects/mind/docs/00_OVERVIEW.md)
- 项目入口页：[README.md](file:///Users/bytedance/TRAEProjects/mind/README.md)
- 根目录现行主线清单：[CURRENT_MAINLINE_ROOT_MAP.md](file:///Users/bytedance/TRAEProjects/mind/docs/CURRENT_MAINLINE_ROOT_MAP.md)
- 根目录非主线候选清单：[NON_MAINLINE_CLEANUP_CANDIDATES.md](file:///Users/bytedance/TRAEProjects/mind/docs/NON_MAINLINE_CLEANUP_CANDIDATES.md)
- 当前理论规范：[THEORY_CANON.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_CANON.md)
- 有效模型声明：[EFFECTIVE_MODEL_STATEMENT.md](file:///Users/bytedance/TRAEProjects/mind/docs/EFFECTIVE_MODEL_STATEMENT.md)
- 理论统一路线图：[THEORY_UNIFICATION_ROADMAP.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_UNIFICATION_ROADMAP.md)
- 优先科学假设：[PRIORITY_SCIENTIFIC_HYPOTHESES.md](file:///Users/bytedance/TRAEProjects/mind/docs/PRIORITY_SCIENTIFIC_HYPOTHESES.md)
- 假设验证执行清单：[HYPOTHESIS_VALIDATION_CHECKLIST.md](file:///Users/bytedance/TRAEProjects/mind/docs/HYPOTHESIS_VALIDATION_CHECKLIST.md)
- 正式数学定义源：[STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md)
- 模型分析层级图：[MODEL_ANALYSIS_HIERARCHY.md](file:///Users/bytedance/TRAEProjects/mind/docs/MODEL_ANALYSIS_HIERARCHY.md)
- 统一术语源：[GLOSSARY.md](file:///Users/bytedance/TRAEProjects/mind/docs/GLOSSARY.md)
- 强相互作用术语表：[STRONG_INTERACTION_TERMINOLOGY_TABLE.md](file:///Users/bytedance/TRAEProjects/mind/docs/STRONG_INTERACTION_TERMINOLOGY_TABLE.md)
- 胞元宇宙可视化说明：[CELLULAR_VIRTUAL_UNIVERSE_VISUALIZATION.md](file:///Users/bytedance/TRAEProjects/mind/docs/CELLULAR_VIRTUAL_UNIVERSE_VISUALIZATION.md)
- 理论叙事版：[THEORY_FRAMEWORK.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_FRAMEWORK.md)
- 历史理论版本：[SIMULATION_REALITY_DUALITY.md](file:///Users/bytedance/TRAEProjects/mind/docs/SIMULATION_REALITY_DUALITY.md)

## 三、文档分工

### 1. 正式定义层

- [CURRENT_MAINLINE_ROOT_MAP.md](file:///Users/bytedance/TRAEProjects/mind/docs/CURRENT_MAINLINE_ROOT_MAP.md)
  - 作用：整理当前根目录仍保留的主线脚本、专题入口、辅助工具与历史目录
  - 适合阅读：想快速判断“现在应该从哪个脚本入手、哪些文件已经迁入 legacy”时
- [NON_MAINLINE_CLEANUP_CANDIDATES.md](file:///Users/bytedance/TRAEProjects/mind/docs/NON_MAINLINE_CLEANUP_CANDIDATES.md)
  - 作用：列出当前非主线专题、低风险归档候选与已执行的收尾归档对象
  - 适合阅读：想继续做目录收敛、判断哪些脚本属于探索期残留时
- [THEORY_CANON.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_CANON.md)
  - 作用：当前项目的理论裁决顺序、符号规范与解释边界
  - 适合阅读：需要先判断哪份文档是现行规范、哪些内容只是叙事或历史时
  - 原则：当多个文档口径冲突时，先看本文件给出的裁决顺序
- [EFFECTIVE_MODEL_STATEMENT.md](file:///Users/bytedance/TRAEProjects/mind/docs/EFFECTIVE_MODEL_STATEMENT.md)
  - 作用：明确当前结构动力学原型与标准模型、QFT、GR 的边界，以及“模式家族”命名口径
  - 适合阅读：需要判断某个脚本是否属于物理等价求解器、还是低维有效模型时
- [THEORY_UNIFICATION_ROADMAP.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_UNIFICATION_ROADMAP.md)
  - 作用：给出从公理层、有效模型层到科学接口层的理论完善顺序
  - 适合阅读：想知道“下一步如何系统完善理论，而不是继续增加叙事”时
- [PRIORITY_SCIENTIFIC_HYPOTHESES.md](file:///Users/bytedance/TRAEProjects/mind/docs/PRIORITY_SCIENTIFIC_HYPOTHESES.md)
  - 作用：列出当前最优先验证的三个科学假设，并给出最小实验、指标、证伪条件与脚本入口
  - 适合阅读：准备从理论整理进入实验验证阶段时
- [HYPOTHESIS_VALIDATION_CHECKLIST.md](file:///Users/bytedance/TRAEProjects/mind/docs/HYPOTHESIS_VALIDATION_CHECKLIST.md)
  - 作用：把优先科学假设转成可直接执行的实验清单，统一命令、输出规范与通过/失败判据
  - 适合阅读：准备正式开始逐条跑验证实验时
- [STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md)
  - 作用：全项目唯一正式数学定义源
  - 适合阅读：需要确认公式、符号、层级、公频锁相、跨层级抽象概念、时间流速、闭合条件时
  - 重点章节：
    - 多图层与锁相层级：[STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md#L692-L872)
    - 计算场论与粒子显态：[STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md#L799-L861)
    - 学习—内存—连续意识：[STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md#L862-L901)
    - 频率—内存阈值与宏观—量子差异：[STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md#L902-L944)
- [MODEL_ANALYSIS_HIERARCHY.md](file:///Users/bytedance/TRAEProjects/mind/docs/MODEL_ANALYSIS_HIERARCHY.md)
  - 作用：把点、线、面、体、场、谱、态空间、信息与层级视角统一映射到当前代码结构
  - 适合阅读：需要同时理解“理论分析层次”和“当前代码落点”时

### 2. 术语层

- [GLOSSARY.md](file:///Users/bytedance/TRAEProjects/mind/docs/GLOSSARY.md)
  - 作用：统一术语源
  - 适合阅读：看到“计算场、层级、公频锁相、跨层级锁相、抽象概念、意识窗口”等词时
  - 原则：其他文档若与术语表冲突，以术语表和正式数学定义为准
- [STRONG_INTERACTION_TERMINOLOGY_TABLE.md](file:///Users/bytedance/TRAEProjects/mind/docs/STRONG_INTERACTION_TERMINOLOGY_TABLE.md)
  - 作用：强相互作用相关概念的专项术语表与结构判据表
  - 适合阅读：需要查看“夸克、强子、色中性、胶子样中间相、强作用闭合度”等概念的本理论重解释时
  - 原则：它是强相互作用专题文档；若遇到全局术语冲突，仍以 `GLOSSARY.md` 和正式数学定义源为准

### 3. 叙事解释层

- [THEORY_FRAMEWORK.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_FRAMEWORK.md)
  - 作用：理论的叙事版和宏观图景版
  - 适合阅读：想先理解整体世界观、结构图景和跨域耦合意义时
  - 注意：它只承担叙事解释职责，不承担最终正式定义职责

### 4. 历史来源层

- [SIMULATION_REALITY_DUALITY.md](file:///Users/bytedance/TRAEProjects/mind/docs/SIMULATION_REALITY_DUALITY.md)
  - 作用：保存项目较早阶段的理论版本与历史推导
  - 适合阅读：做版本对照、追踪概念演化、比较旧定义和新定义时
  - 注意：它是历史来源，不是当前唯一标准，也不应作为现行符号约定的直接来源

## 四、实验地图

### 1. 理论验证类

- [testable_predictions.py](file:///Users/bytedance/TRAEProjects/mind/testable_predictions.py)
  - 对应：标准化预测验证、统计量与理论定义映射

### 2. RAM 完全图实验类

- [current_ram_complete_graph_experiment.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_complete_graph_experiment.py)
  - 对应：当前电脑 RAM 上的全连接图双态跳变实验
- [current_ram_phase_scan.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_phase_scan.py)
  - 对应：`ratio = f_read / f_mem_proxy` 的临界窗口细扫与相图

### 3. 层级/锁相/闭合实验类

- [vortex_tensor_animation.py](file:///Users/bytedance/TRAEProjects/mind/vortex_tensor_animation.py)
  - 对应：张量漩涡、主轴扰动、壳层、闭合共振、层级时间流速
- [hierarchy_flow_scan.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_flow_scan.py)
  - 对应：层级时间流速扫描、平滑/分裂区域搜索

### 4. 概念可视化类

- [hierarchy_definition_comparison.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_definition_comparison.py)
  - 对应：旧层级定义 vs 新层级定义的对比图

## 五、推荐阅读路径

### 路线 A：先把理论主线读明白

1. [00_OVERVIEW.md](file:///Users/bytedance/TRAEProjects/mind/docs/00_OVERVIEW.md)
2. [INDEX.md](file:///Users/bytedance/TRAEProjects/mind/docs/INDEX.md)
3. [CURRENT_MAINLINE_ROOT_MAP.md](file:///Users/bytedance/TRAEProjects/mind/docs/CURRENT_MAINLINE_ROOT_MAP.md)
4. [THEORY_CANON.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_CANON.md)
5. [EFFECTIVE_MODEL_STATEMENT.md](file:///Users/bytedance/TRAEProjects/mind/docs/EFFECTIVE_MODEL_STATEMENT.md)
6. [GLOSSARY.md](file:///Users/bytedance/TRAEProjects/mind/docs/GLOSSARY.md)
7. [STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md)
8. [MODEL_ANALYSIS_HIERARCHY.md](file:///Users/bytedance/TRAEProjects/mind/docs/MODEL_ANALYSIS_HIERARCHY.md)
9. [THEORY_FRAMEWORK.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_FRAMEWORK.md)

### 路线 B：先看层级定义修正

1. [GLOSSARY.md](file:///Users/bytedance/TRAEProjects/mind/docs/GLOSSARY.md)
2. [STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md#L692-L872)
3. [SIMULATION_REALITY_DUALITY.md](file:///Users/bytedance/TRAEProjects/mind/docs/SIMULATION_REALITY_DUALITY.md)
4. [hierarchy_definition_comparison.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_definition_comparison.py)

### 路线 C：先看实验如何落地

1. [README.md](file:///Users/bytedance/TRAEProjects/mind/README.md)
2. [current_ram_complete_graph_experiment.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_complete_graph_experiment.py)
3. [current_ram_phase_scan.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_phase_scan.py)
4. [vortex_tensor_animation.py](file:///Users/bytedance/TRAEProjects/mind/vortex_tensor_animation.py)
5. [hierarchy_flow_scan.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_flow_scan.py)

## 六、遇到问题时看哪里

- 不知道一个概念是什么意思：看 [GLOSSARY.md](file:///Users/bytedance/TRAEProjects/mind/docs/GLOSSARY.md)
- 不知道一个定义是否正式：看 [STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md)
- 不知道某个结果属于物理等价解释还是有效模型边界：看 [EFFECTIVE_MODEL_STATEMENT.md](file:///Users/bytedance/TRAEProjects/mind/docs/EFFECTIVE_MODEL_STATEMENT.md)
- 想知道理论整体想表达什么：看 [THEORY_FRAMEWORK.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_FRAMEWORK.md)
- 想知道早期版本怎么说：看 [SIMULATION_REALITY_DUALITY.md](file:///Users/bytedance/TRAEProjects/mind/docs/SIMULATION_REALITY_DUALITY.md)
- 想知道实验怎么跑：先看 [README.md](file:///Users/bytedance/TRAEProjects/mind/README.md)，再看对应脚本

## 七、当前重构状态

- README 已收缩为项目入口页
- INDEX 正在作为阅读地图使用
- 当前理论规范已单独抽出为 [THEORY_CANON.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_CANON.md)
- 正式定义、术语表、叙事版、历史版四类文档职责已经明确分离
- 后续将继续重构实验入口页和目录结构
