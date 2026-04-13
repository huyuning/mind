# 当前理论规范

## 目标

本文件用于给出当前项目的统一理论规范，解决不同文档之间的角色重叠、符号漂移和解释层混用问题。

它不替代正式数学定义源，也不替代术语表，而是回答三个更基础的问题：

- 当前项目里，哪份文档是正式定义，哪份只是叙事解释，哪份只是历史来源
- 当不同文档出现口径差异时，应以什么顺序裁决
- 当前哪些理论主张已经进入“规范层”，哪些仍属于探索层或类比层

---

## 一、裁决顺序

当前项目内所有理论口径的优先级，统一按下面顺序裁决：

1. [STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md)
2. [GLOSSARY.md](file:///Users/bytedance/TRAEProjects/mind/docs/GLOSSARY.md)
3. 本文件
4. [HIERARCHICAL_RECURSION_DEFINITION.md](file:///Users/bytedance/TRAEProjects/mind/docs/HIERARCHICAL_RECURSION_DEFINITION.md)
5. 专题文档，例如 [STRONG_INTERACTION_TERMINOLOGY_TABLE.md](file:///Users/bytedance/TRAEProjects/mind/docs/STRONG_INTERACTION_TERMINOLOGY_TABLE.md) 与 [COLOR_FLAVOR_MAPPING_EXPERIMENT.md](file:///Users/bytedance/TRAEProjects/mind/docs/COLOR_FLAVOR_MAPPING_EXPERIMENT.md)
6. [THEORY_FRAMEWORK.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_FRAMEWORK.md)
7. [SIMULATION_REALITY_DUALITY.md](file:///Users/bytedance/TRAEProjects/mind/docs/SIMULATION_REALITY_DUALITY.md)

若低优先级文档与高优先级文档冲突，以高优先级文档为准。

---

## 二、当前有效主线

当前项目的有效理论主线统一为：

`第一性结构 -> 数学展开 -> 计算场 -> 稳定模式 -> 锁相 -> 层级 -> 跨层级锁相 -> 抽象概念 -> 显态世界`

它包含以下规范性判断：

- 第一性不是某个具体粒子或单一对象，而是可展开、可锁相、可投影的数学结构
- 线性代数、微积分、概率论分别承担结构展开、过程展开和显态统计压缩三条主线
- 层级首先由锁相后的公频等价类定义，整数层号只是派生标签
- 层级的当前规范性几何图像可表述为“锁相球壳嵌套交织”：同一层级不是单点薄层，而是围绕共同锁相条件形成的一组球壳状稳定区域
- 更微观方向并不意味着“壳层更简单”，而意味着单位尺度内的壳层嵌套更致密、锁相壳面间距更小
- 更宏观方向并不意味着“壳层更稀少”，而意味着壳层之间的交织、回返、跨层耦合和抽象稳定模态更复杂
- 时间流速在当前规范中应理解为有效信息传播与相位调整完成的速率，而不是先验绝对时钟速度
- 微观方向由于锁相壳层间有效距离更短，因此局域信息传播路径更短、相位同步更快、锁相频率更高
- 宏观方向则更多受跨壳层相位传播、闭合耦合和长程交织影响，因而显现为较低频、较慢的时空展开
- 跨层级关系不只是一对一映射，也可以是围绕共同高阶主频形成的稳定锁相
- 抽象概念被理解为跨层级稳定模态，而不是脱离结构的纯标签

---

## 三、符号规范

### 1. 潜状态与观测

当前项目不再把“模拟空间 / 现实空间”作为现行正式定义。

规范写法为：

- 潜状态空间：`\mathcal{X}`
- 观测空间：`\mathcal{Y}`
- 观测映射：`h:\mathcal{X}\to\mathcal{Y}`

旧的“模拟-现实对偶”表述仅作为历史来源保留，不再作为当前正式建模主语言。

### 2. 层级索引

层级索引 `n` 统一视为尺度标签，而不是先验本体标签。

当前规范中只保留一种直接约定：

- 若用 `d_{n,n+1} = d_0 \lambda^n` 表示相邻层级间距，且 `\lambda > 1`
- 则 `n \to +\infty` 表示更宏观方向，相邻层距增大
- `n \to -\infty` 表示更微观方向，相邻层距减小

在当前规范中，上述“相邻层距”可进一步解释为锁相球壳之间的有效间距，因此：

- `n \to -\infty` 时，壳层嵌套更密集，单位尺度内可容纳更多锁相壳面与更细的回返结构
- `n \to +\infty` 时，壳层间距变大，但跨壳层交织、闭合和抽象稳定模态更复杂
- 因而“微观更密 / 宏观更复杂”是当前层级解释的规范口径

进一步地，当前规范允许把时间尺度也放进同一解释链：

- 微观层中的时间流速，解释为单位结构尺度内信息传播与相位同步完成得更快
- 宏观层中的时间展开，解释为跨壳层相位传播、长程闭合和显态重组的结果
- 因而可用“微观高频锁相 / 宏观低频展开”概括当前时间解释口径

任何与此冲突的“宏观趋零 / 微观趋无限”说法，均视为旧版本遗留叙事，不再作为现行符号解释。

### 3. 尺度倍率 `\lambda`

当前规范中：

- `\lambda > 1` 仅表示尺度倍率
- `\lambda` 不再兼作动力学状态变量

若历史文档中需要讨论模式态、矛盾态或膨胀/收缩态，应使用其他专门符号，而不应继续复用当前规范中的 `\lambda`。

---

## 四、层级与有效投影位

关于有效投影位、回映冗余位和层级递推，当前统一采用以下分工：

- [HIERARCHICAL_RECURSION_DEFINITION.md](file:///Users/bytedance/TRAEProjects/mind/docs/HIERARCHICAL_RECURSION_DEFINITION.md) 是主文档
- [EFFECTIVE_PROJECTION_COUNT_DEFINITION.md](file:///Users/bytedance/TRAEProjects/mind/docs/EFFECTIVE_PROJECTION_COUNT_DEFINITION.md) 是计数定义的抽取版

当前规范保留以下核心对象：

- `V^{(k)}_{raw}`：原始展开节点集合
- `V^{(k)}_{return}`：回映冗余位集合
- `V^{(k)}_{eff}`：有效投影位集合
- `N^{(k)}_{eff} = N^{(k)}_{raw} - R^{(k)}`：有效投影位计数

对层级复杂度、去冗余自由度和质数规律的讨论，优先作用于 `N^{(k)}_{eff}`，而不是 `N^{(k)}_{raw}`。

---

## 五、9 位模型与 SU(3) 口径

当前关于第二层 `9` 位结构的规范口径如下：

- `v11, v22, v33` 对应对角本征位
- `v12, v21, v13, v31, v23, v32` 对应非对角有向关系位
- 这是一个结构动力学模型，不是标准粒子物理的直接等价物

为便于形式化，可把 `9` 位模型改写为 `3x3` 厄米复矩阵：

```math
M=
\begin{pmatrix}
v_{11} & B_{12}-iF_{12} & B_{13}-iF_{13} \\
B_{12}+iF_{12} & v_{22} & B_{23}-iF_{23} \\
B_{13}+iF_{13} & B_{23}+iF_{23} & v_{33}
\end{pmatrix}
```

其中：

- `B_{ij} = (v_{ij}+v_{ji})/2`
- `F_{ij} = (v_{ji}-v_{ij})/2`

这一步的意义是把原本的 `3 + 6` 结构，改写成一个带 `U(1)+SU(3)` 分解的局域内部状态表示。

但当前规范同时明确：

- 这是一种形式上的结构对齐
- 不是对标准模型中 `SU(3)_C` 的直接物理证明
- 相关实验结果应解释为“结构类比与动力学分层证据”，而不是高能物理实测结果

---

## 六、实验解释边界

当前项目的实验统一分成三类：

- 真实机器上的 RAM / 频率 / 读写行为实验
- 抽象动力学仿真
- 理论结构映射与可视化实验

因此，实验输出的解释边界统一为：

- 可以用来检验理论结构是否自洽、是否出现稳定窗、边界带、再入稳定区和分层模式
- 不可以直接宣称为标准物理中的粒子、场、引力或量子态的实验观测结果
- 若与标准物理建立联系，默认只能使用“结构类比”“形式对齐”“低维有效模型”这类表述

---

## 七、文档状态定义

当前文档状态统一分为四类：

- `canonical`：现行规范文档
- `supporting`：补充定义或专题文档
- `narrative`：叙事解释文档
- `legacy`：历史来源文档

建议对应如下：

- `canonical`：
  - [STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md)
  - [GLOSSARY.md](file:///Users/bytedance/TRAEProjects/mind/docs/GLOSSARY.md)
  - 本文件
- `supporting`：
  - [HIERARCHICAL_RECURSION_DEFINITION.md](file:///Users/bytedance/TRAEProjects/mind/docs/HIERARCHICAL_RECURSION_DEFINITION.md)
  - [EFFECTIVE_PROJECTION_COUNT_DEFINITION.md](file:///Users/bytedance/TRAEProjects/mind/docs/EFFECTIVE_PROJECTION_COUNT_DEFINITION.md)
  - [STRONG_INTERACTION_TERMINOLOGY_TABLE.md](file:///Users/bytedance/TRAEProjects/mind/docs/STRONG_INTERACTION_TERMINOLOGY_TABLE.md)
  - [COLOR_FLAVOR_MAPPING_EXPERIMENT.md](file:///Users/bytedance/TRAEProjects/mind/docs/COLOR_FLAVOR_MAPPING_EXPERIMENT.md)
- `narrative`：
  - [THEORY_FRAMEWORK.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_FRAMEWORK.md)
- `legacy`：
  - [SIMULATION_REALITY_DUALITY.md](file:///Users/bytedance/TRAEProjects/mind/docs/SIMULATION_REALITY_DUALITY.md)

---

## 八、整合后的最短阅读路径

如果只想读当前有效主线，建议按下面顺序：

1. [00_OVERVIEW.md](file:///Users/bytedance/TRAEProjects/mind/docs/00_OVERVIEW.md)
2. [INDEX.md](file:///Users/bytedance/TRAEProjects/mind/docs/INDEX.md)
3. [THEORY_CANON.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_CANON.md)
4. [GLOSSARY.md](file:///Users/bytedance/TRAEProjects/mind/docs/GLOSSARY.md)
5. [STANDARD_MATHEMATICAL_RECONSTRUCTION.md](file:///Users/bytedance/TRAEProjects/mind/docs/STANDARD_MATHEMATICAL_RECONSTRUCTION.md)
6. 再进入专题文档和实验入口

---

## 九、当前提纯结论

当前项目在整合后，应坚持以下最短结论：

- 理论以“数学展开结构”而非具体粒子叙事为第一性
- 正式定义与叙事解释必须分层，不再混写
- 旧版“模拟-现实对偶”“黑洞广播宇宙”一类表述可保留为历史或叙事材料，但不再作为现行正式定义
- 层级、投影位、`9` 位模型、`SU(3)` 改写都可以保留，但必须放在“结构模型”口径下解释
- 实验的价值在于结构验证、稳定窗定位和模型比较，不在于替代标准物理实验
