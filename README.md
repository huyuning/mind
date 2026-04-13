# Mind

分形嵌套宇宙、计算场论、锁相层级与意识/抽象概念实验项目。

本项目当前的正式名称统一为：`胞元基底结构动力学研究引擎`，英文名 `Cellular-Substrate Structural Dynamics Engine`，简称 `CSDE`。
一句话定位：`CSDE` 是一个以胞元、闭合相、轴节点、共轴簇和连续势场为原生对象的结构动力学研究引擎，用于探索多层级涌现、质量代理与宏观汇聚等现象。

本仓库当前定位为一个**理论整理 + 数学重构 + 实验验证**项目：  
用统一的形式化文档和可运行脚本，把“第一性结构 -> 数学展开 -> 计算场 -> 锁相 -> 层级 -> 跨层级抽象概念 -> 意识/现实显现”的主线整理成可追踪、可验证、可扩展的研究结构。

## 核心主张

- 第一性不是某个具体粒子或单一事件，而是可生成、可分化、可锁相、可投影的**数学展开结构**。
- 层级不是先验几何编号，而是由**锁相后的公频等价类**定义。
- 不同层级的对象仍可围绕共同公频完成**跨层级锁相**。
- 抽象概念不是脱离具体对象的纯符号，而是跨层级锁相后形成的**稳定高阶模态**。
- 内存刷新频率、频率阈值和锁相条件共同决定稳定显现、覆写筛选与意识窗口。
- 完全图、扫频、闭合共振与相图实验用于为上述理论提供可执行的机制验证。

## 阅读入口

- 项目总览：[00_OVERVIEW.md](file:///Users/bytedance/TRAEProjects/mind/docs/00_OVERVIEW.md)
- 项目阅读地图：[INDEX.md](file:///Users/bytedance/TRAEProjects/mind/docs/INDEX.md)
- 标准数学重构主文档：[STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md)
- 术语表：[GLOSSARY.md](file:///Users/bytedance/TRAEProjects/mind/docs/GLOSSARY.md)
- 理论叙事框架：[THEORY_FRAMEWORK.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_FRAMEWORK.md)
- 历史理论版本：[SIMULATION_REALITY_DUALITY.md](file:///Users/bytedance/TRAEProjects/mind/docs/SIMULATION_REALITY_DUALITY.md)

## 推荐阅读顺序

1. [00_OVERVIEW.md](file:///Users/bytedance/TRAEProjects/mind/docs/00_OVERVIEW.md)
2. [INDEX.md](file:///Users/bytedance/TRAEProjects/mind/docs/INDEX.md)
3. [GLOSSARY.md](file:///Users/bytedance/TRAEProjects/mind/docs/GLOSSARY.md)
4. [STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md)
5. [THEORY_FRAMEWORK.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_FRAMEWORK.md)
6. 再进入实验脚本与输出数据

## 核心实验入口

- 理论预测验证：`testable_predictions.py`
- RAM 完全图双态实验：`current_ram_complete_graph_experiment.py`
- RAM 临界相图细扫：`current_ram_phase_scan.py`
- 张量漩涡与闭合共振：`vortex_tensor_animation.py`
- 层级时间流速扫描：`hierarchy_flow_scan.py`
- 层级定义对比图：`hierarchy_definition_comparison.py`

## 快速开始

安装依赖：

```bash
pip3 install -r requirements.txt
```

示例运行：

```bash
python3 testable_predictions.py
python3 current_ram_complete_graph_experiment.py
python3 current_ram_phase_scan.py
python3 hierarchy_definition_comparison.py
```

实验输出默认写入 `resonance_data/`、`verification_data/` 等目录。

## 当前重构原则

- 一个正式定义源：以标准数学重构文档为准。
- 一个术语源：以术语表为准。
- 一个项目入口页：README 只保留定位、主张、导航和实验入口。
- 历史理论与当前主线分离：历史文档保留，但不再承担正式定义职责。

## 许可证

本项目采用 `Apache License 2.0`。
