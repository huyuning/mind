# 胞元虚拟计算宇宙可视化说明

## 目标

本文件用于解释 [cellular_virtual_universe.py](file:///Users/bytedance/TRAEProjects/mind/cellular_virtual_universe.py) 生成的各类可视化结果分别表示什么、应该如何阅读、它们和“胞元虚拟计算宇宙”这一最小原型之间的关系是什么。

当前推荐把 `Plotly` 3D 页面作为三维结构解释的主版本，把静态 `Matplotlib` 3D 图当作快速快照和报告图使用。

这份文档只解释当前原型的图像含义，不把这些图解释成标准物理中的直接观测图。
若涉及理论边界，请仍以 [THEORY_CANON.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_CANON.md) 为准。

---

## 一、原型对应什么

当前原型把“胞元虚拟计算宇宙”压成了三层对象：

- 胞元：每个胞元携带一个局域三维复态 `\psi_a(t) \in \mathbb{C}^3`
- 局域内部结构：每个胞元对应一个 `3x3` 厄米矩阵 `M_a(t)`
- 胞元间几何：胞元之间通过动态复边 `R_{ab}(t)` 相互耦合

其中：

- `M_a(t)` 的实质是一个 `U(1)+SU(3)` 风格的局域内部状态表示
- `R_{ab}(t)` 的模长表示链接强度
- `R_{ab}(t)` 的相位表示方向弯曲或几何扭转
- 三角闭合积 `R_{ab}R_{bc}R_{ca}` 用来测量局部闭合和相位曲率

---

## 二、输出目录

运行脚本后，会生成：

- `resonance_data/cellular_virtual_universe_<timestamp>/`

典型样例目录：

- [cellular_virtual_universe_20260409_192914](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914)

其中当前可视化文件包括：

- [mean_su3_components_20260409_192914.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/mean_su3_components_20260409_192914.png)
- [closure_series_20260409_192914.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/closure_series_20260409_192914.png)
- [final_a3_heatmap_20260409_192914.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/final_a3_heatmap_20260409_192914.png)
- [final_field_panels_20260409_192914.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/final_field_panels_20260409_192914.png)
- [final_network_snapshot_20260409_192914.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/final_network_snapshot_20260409_192914.png)
- [final_network_3d_snapshot_20260409_192914.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/final_network_3d_snapshot_20260409_192914.png)
- [final_surface_3d_20260409_192914.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/final_surface_3d_20260409_192914.png)
- [interactive_network_3d_20260409_192914.html](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/interactive_network_3d_20260409_192914.html)
- [interactive_surface_3d_20260409_192914.html](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/interactive_surface_3d_20260409_192914.html)

同时还会输出：

- [summary_20260409_192914.json](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/summary_20260409_192914.json)
- [state_series_20260409_192914.npz](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/state_series_20260409_192914.npz)

---

## 三、每张图表示什么

### 1. `mean_su3_components_*.png`

对应文件：

- [mean_su3_components_20260409_191650.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_191650/mean_su3_components_20260409_191650.png)

含义：

- 横轴是时间
- 纵轴是全体胞元上 `a1...a8` 的平均值
- 每条线表示一个 `SU(3)` 分量在整个胞元网络上的总体演化趋势

它回答的问题：

- 哪些内部自由度在整个宇宙中被持续激发
- 某些偏置位、桥接位或流向位是否长期保持非零
- 胞元宇宙的内部状态是否会自发偏向某些方向

推荐读法：

- 若某条曲线长期偏离 `0`，说明对应结构分量在全局上形成稳定偏置
- 若多条曲线同步振荡，说明不同内部自由度之间可能形成耦合共振

---

### 2. `closure_series_*.png`

对应文件：

- [closure_series_20260409_191650.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_191650/closure_series_20260409_191650.png)

含义：

- 蓝线表示所有三角闭合积实部的平均值 `mean Re(closure)`
- 橙线表示所有三角闭合积相位的平均角 `mean arg(closure)`

其中：

```math
\mathrm{closure}_{abc} = R_{ab}R_{bc}R_{ca}
```

它回答的问题：

- 局部几何环是否在整体上维持闭合
- 胞元网络是否形成稳定的相位曲率
- 闭合的“强度”与“方向”是否随时间漂移

推荐读法：

- 实部越高，表示局部闭合环越强
- 平均相位若稳定在某个固定值附近，说明网络整体存在稳定几何扭转方向
- 若两条曲线同时平稳，说明胞元几何较稳定；若剧烈波动，说明局部几何正在重排

---

### 3. `final_a3_heatmap_*.png`

对应文件：

- [final_a3_heatmap_20260409_191650.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_191650/final_a3_heatmap_20260409_191650.png)

含义：

- 这是最终时刻每个胞元的 `a3` 分量二维热图
- 横纵坐标是胞元网格坐标
- 颜色表示 `a3` 的正负和大小

这里的 `a3` 对应的是一个对角偏置方向，可理解为：

- 第 1、2 内部通道的相对占据偏置
- 局域内部结构的一个主偏置轴

它回答的问题：

- 哪些区域更偏向正偏置，哪些区域更偏向负偏置
- 胞元宇宙是否形成大尺度偏置团块或条纹

推荐读法：

- 若图像出现平滑渐变，说明偏置场较连续
- 若出现强烈块状分区，说明不同胞元区已分化成不同局域态簇

---

### 4. `final_field_panels_*.png`

对应文件：

- [final_field_panels_20260409_191650.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_191650/final_field_panels_20260409_191650.png)

含义：

这是一个三联图，分别显示最终时刻的：

- `S` 场
- `a3` 场
- `a8` 场

三者含义分别是：

- `S`：胞元矩阵的迹方向强度，表示局域总标量强度
- `a3`：第一组对角偏置方向
- `a8`：第二组对角偏置方向

它回答的问题：

- 总强度场和内部偏置场是否同步
- 某些区域是“强但不偏置”，还是“弱但强偏置”
- `a3` 与 `a8` 两个偏置方向是否形成不同空间结构

推荐读法：

- 先看 `S` 场判断哪里是总体“活跃区”
- 再看 `a3`、`a8` 判断活跃区内部是均匀的还是发生了结构分裂

这张图比单独的 `a3` 热图更完整，因为它把“强度”和“偏置”拆开看了。

---

### 5. `final_network_snapshot_*.png`

对应文件：

- [final_network_snapshot_20260409_191650.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_191650/final_network_snapshot_20260409_191650.png)

含义：

- 节点位置是胞元在网格中的位置
- 节点颜色表示最终 `a3`
- 连线粗细表示边强度 `|R_{ab}|`
- 连线颜色表示边相位 `arg(R_{ab})`

它回答的问题：

- 最终几何连接是否更集中在某些区域
- 强边与弱边如何分布
- 相位扭转是否在不同区域形成不同色带
- 胞元内部偏置与胞元间连接是否出现空间对齐

推荐读法：

- 先看哪些边最粗，判断强耦合骨架在哪里
- 再看边颜色，判断这些强耦合是否共享相近相位方向
- 最后看节点颜色与边颜色是否配合，判断“内部态偏置”和“外部几何连接”是否协同

这张图是最接近“胞元虚拟时空快照”的一张图。

---

### 6. `final_network_3d_snapshot_*.png`

对应文件：

- [final_network_3d_snapshot_20260409_192914.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/final_network_3d_snapshot_20260409_192914.png)

含义：

- 这是把二维胞元网络抬升到三维后的静态快照
- `x, y` 保持胞元网格位置
- `z` 由你选择的投影场决定，当前样例使用 `a8`
- 节点颜色仍默认用最终 `a3` 表示
- 连线粗细表示边强度
- 连线颜色表示边相位

它回答的问题：

- 若把某个内部场当作“高度”，整个胞元宇宙会形成什么几何起伏
- 哪些强边跨越了高度差，哪些强边只存在于同一高度层
- 偏置场与几何连接之间是否存在立体上的协同

推荐读法：

- 把它看成“带有内部场起伏的胞元骨架”
- 节点高度看内部场，边的颜色和粗细看外部几何
- 这张图适合做静态报告，但旋转理解仍受限

---

### 7. `final_surface_3d_*.png`

对应文件：

- [final_surface_3d_20260409_192914.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/final_surface_3d_20260409_192914.png)

含义：

- 这是把选定投影场直接当成离散表面高度后的静态曲面图
- 该图不强调边结构，而强调“整体场的地形”

它回答的问题：

- 某个内部场在空间上是形成山谷、脊线还是盆地区
- 胞元宇宙更像一个单峰场、双峰场还是分块台阶场

推荐读法：

- 把它看成“胞元宇宙的场形地形图”
- 它最适合观察大尺度结构，不适合分析具体哪条边最强

---

### 8. `interactive_network_3d_*.html`

对应文件：

- [interactive_network_3d_20260409_192914.html](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/interactive_network_3d_20260409_192914.html)

含义：

- 这是推荐优先使用的三维解释版本
- 它与静态 `final_network_3d_snapshot_*.png` 对应同一类信息，但允许你旋转、缩放和平移

为什么推荐它替代静态 3D 图作为主解释：

- 静态视角会遮挡部分边结构
- 高度、边相位和节点颜色三种信息叠在一起时，需要旋转才能看清
- 交互版更适合判断立体骨架是否真的形成扭转、分层和局部团簇

推荐读法：

- 先整体旋转一圈，看是否存在主脊线或主凹谷
- 再放大局部强边区域，看强耦合是否集中在同一高度层
- 最后观察不同高度区域的边相位颜色是否连续

---

### 9. `interactive_surface_3d_*.html`

对应文件：

- [interactive_surface_3d_20260409_192914.html](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/interactive_surface_3d_20260409_192914.html)

含义：

- 这是推荐优先使用的三维场形解释版本
- 它与静态 `final_surface_3d_*.png` 对应，但允许从不同角度观察整个场面

为什么推荐它：

- 某些峰谷在静态视角下会重叠
- 旋转后更容易分辨“连续曲面起伏”和“离散台阶结构”

推荐读法：

- 如果你关心“宇宙整体像什么形状”，先看这个
- 如果你关心“具体几何边是怎么连的”，再切回交互网络图

---

## 四、`a3`、`a8` 和 `S` 在三维投影中的区别

脚本通过：

```bash
--projection-z a3
--projection-z a8
--projection-z S
```

来决定三维投影中的 `z` 轴到底代表什么。

### 1. `a3`

`a3` 是第一组对角偏置方向。

在三维投影里，把 `a3` 作为高度，等于在看：

- “第 1、2 内部通道相对占据差”如何在空间上抬升成地形

它更适合回答：

- 哪些区域在第一主偏置轴上发生了分化
- 网络中是否形成沿某一主偏置方向的脊线或团块

直觉上：

- `a3` 更像“第一主偏置山脊”

### 2. `a8`

`a8` 是第二组对角偏置方向。

在三维投影里，把 `a8` 作为高度，等于在看：

- “前两个通道整体相对于第三通道的偏置差”如何在空间上展开

它更适合回答：

- 胞元内部是否存在另一种独立于 `a3` 的大尺度分层
- 网络是否在第二主偏置轴上形成不同形态的几何分区

直觉上：

- `a8` 更像“第二主偏置坡面”

### 3. `S`

`S` 是迹方向上的总标量强度。

在三维投影里，把 `S` 作为高度，等于在看：

- 哪些胞元总体更活跃、更强，哪些胞元总体更弱

它更适合回答：

- 宇宙整体活跃区在哪里
- 强度场是否和偏置场重合，还是彼此错位

直觉上：

- `S` 更像“总能量地形”或“活跃度地形”

### 4. 三者怎么区分使用

- 如果你关心“哪里更活跃”，优先投影 `S`
- 如果你关心“第一主偏置方向的结构分裂”，优先投影 `a3`
- 如果你关心“第二主偏置方向的独立分层”，优先投影 `a8`

最有信息量的做法不是三选一，而是：

1. 先看 `S`，找总体活跃区
2. 再看 `a3`，看活跃区内部是否沿第一主偏置轴分裂
3. 最后看 `a8`，看是否还存在另一组独立分层

---

## 五、如何把这些图连起来看

建议按下面顺序阅读：

1. 先看 [closure_series_20260409_192914.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/closure_series_20260409_192914.png)
   - 判断这个宇宙整体是否进入稳定闭合状态
2. 再看 [mean_su3_components_20260409_192914.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/mean_su3_components_20260409_192914.png)
   - 看内部态的全局平均是否形成稳定偏置
3. 然后看 [final_field_panels_20260409_192914.png](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/final_field_panels_20260409_192914.png)
   - 看这种偏置在空间上如何展开
4. 再看 [interactive_surface_3d_20260409_192914.html](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/interactive_surface_3d_20260409_192914.html)
   - 看选定投影场在三维中的整体地形
5. 最后看 [interactive_network_3d_20260409_192914.html](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/interactive_network_3d_20260409_192914.html)
   - 看胞元几何连接与内部态分布在三维中是否对齐

这五步分别对应：

- 时间稳定性
- 全局态方向
- 空间分布
- 场形地形
- 立体几何结构

---

## 六、当前样例结果怎么理解

当前样例摘要见：

- [summary_20260409_192914.json](file:///Users/bytedance/TRAEProjects/mind/resonance_data/cellular_virtual_universe_20260409_192914/summary_20260409_192914.json)

当前样例的几个关键量是：

- `cell_count = 16`
- `edge_count = 33`
- `triangle_count = 18`
- `mean_triangle_closure_real ≈ 0.6745`
- `mean_triangle_closure_phase ≈ -0.22`
- `final_mean_a3 ≈ -0.1016`
- `final_mean_a8 ≈ -0.0338`

这意味着：

- 该 `4x4` 胞元网格已经形成了稳定的平均闭合
- 平均闭合相位不是 `0`，说明局部几何存在一个整体扭转方向
- 当前样例使用 `a8` 作为三维投影高度，因此更适合观察第二主偏置方向的空间分层
- 全局 `a3` 和 `a8` 都略偏负，说明最终内部偏置方向没有完全对称抵消

当前样例更像一个“已形成稳定闭合、但仍保留轻微方向偏置”的最小虚拟胞元宇宙。

---

## 七、运行方式

最小运行：

```bash
python3 cellular_virtual_universe.py
```

更小的快速预览：

```bash
python3 cellular_virtual_universe.py --width 3 --height 3 --duration 3 --dt 0.05
```

更大的胞元宇宙：

```bash
python3 cellular_virtual_universe.py --width 6 --height 6 --duration 20 --dt 0.03
```

打开周期边界：

```bash
python3 cellular_virtual_universe.py --width 5 --height 5 --periodic
```

使用 `a8` 做三维投影并放大起伏：

```bash
python3 cellular_virtual_universe.py --width 4 --height 4 --duration 3 --dt 0.05 --projection-z a8 --z-scale 1.4
```

使用 `S` 做三维投影：

```bash
python3 cellular_virtual_universe.py --projection-z S --z-scale 1.8
```

---

## 八、解释边界

当前这些图像的理论地位是：

- 它们是“胞元虚拟计算宇宙”最小结构模型的状态图
- 它们说明局域 `SU(3)` 态、复边几何和三角闭合可以被统一可视化
- 它们可以用于比较不同参数下的稳定窗、偏置场和闭合几何

但它们不是：

- 标准物理中的直接天体图像
- 真实宇宙时空曲率的实验测量图
- 粒子物理标准模型的实测结果

它们的价值在于：

- 作为结构模型的可视化证据
- 帮助判断胞元网络是否涌现出稳定几何与偏置场
- 为后续更复杂的胞元时空仿真提供可比较的图像基线
