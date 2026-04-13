# 优先科学假设

## 目标

本文件根据当前理论缺口，列出接下来最优先验证的三个科学假设。

这里的“优先”不是指它们已经最接近被证明，而是指：

- 它们最直接决定当前理论是否还能继续推进
- 它们最能把“叙事性理论”推进到“可检验理论”
- 它们最能连接当前已有脚本与下一阶段统一路线

若要直接开始执行实验而不是继续阅读理论说明，请转到：

- [HYPOTHESIS_VALIDATION_CHECKLIST.md](file:///Users/bytedance/TRAEProjects/mind/docs/HYPOTHESIS_VALIDATION_CHECKLIST.md)

本文件与以下文档配套阅读：

- [THEORY_UNIFICATION_ROADMAP.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_UNIFICATION_ROADMAP.md)
- [EFFECTIVE_MODEL_STATEMENT.md](file:///Users/bytedance/TRAEProjects/mind/docs/EFFECTIVE_MODEL_STATEMENT.md)
- [THEORY_CANON.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_CANON.md)
- [HYPOTHESIS_VALIDATION_CHECKLIST.md](file:///Users/bytedance/TRAEProjects/mind/docs/HYPOTHESIS_VALIDATION_CHECKLIST.md)

---

## 一、假设 1：稳定模式是真实吸引子，而不是数值假象

### 假设内容

在当前连续场与离散图原型中出现的局域稳定模式，不只是由数值归一化、初值偶然性或积分器误差制造出来的伪稳态，而是同一母动力学中的真实吸引子族。

如果这个假设不成立，那么：

- “类氢单中心”
- “类轨道节点”
- “模式家族”
- “粒子样稳定结构”

这些说法都失去基础。

### 为什么优先

这是所有后续理论主张的地基。

在当前项目中，我们已经能观察到：

- 单中心局域结构
- 带节点的角向模式
- 局部时间频谱
- 参数变化下的模式切换

但目前仍不能排除这些现象只是：

- 强归一化步骤造成的人工稳定
- 特定网格和步长下的离散假象
- 极窄参数点的偶然现象

### 最小实验

使用 [hydrogen_color_field_emergence.py](file:///Users/bytedance/TRAEProjects/mind/hydrogen_color_field_emergence.py) 做三组对照实验。

实验 A：初值鲁棒性

```bash
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --seed 20260409
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --seed 20260410
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --seed 20260411
```

实验 B：积分分辨率鲁棒性

```bash
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.01
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.04
```

实验 C：角向模式鲁棒性

```bash
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --angular-momentum 1 --angular-gain 0.28
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --angular-momentum 2 --angular-gain 0.22
```

### 核心指标

建议优先跟踪：

- `final_peak_to_mean_ratio`
- `effective_radius`
- `participation_ratio`
- `probe_dominant_frequency`
- 模式是否保持单中心
- 节点数是否稳定
- 模式寿命是否超过最小时间窗

其中：

- `final_peak_to_mean_ratio` 过低，说明没有真正局域化
- `effective_radius` 大幅漂移，说明模式不稳
- 节点数不稳定，说明角向模式不是稳态结构

### 证伪条件

若出现以下任一情况，则该假设被削弱或暂时失败：

1. 仅更换随机种子，最终模式类别就完全消失或乱跳
2. 仅改变 `dt`，模式拓扑结构就大幅改变
3. 角动量通道产生的节点结构不能维持最小稳定时间窗
4. 所谓“稳定模式”只在极窄参数点出现，无法形成稳定参数窗

### 脚本入口

- [hydrogen_color_field_emergence.py](file:///Users/bytedance/TRAEProjects/mind/hydrogen_color_field_emergence.py)
- [particle_family_suite.py](file:///Users/bytedance/TRAEProjects/mind/particle_family_suite.py)

---

## 二、假设 2：锁相层级可以被统一判据定义

### 假设内容

层级、闭合、跨层级耦合等概念，可以被压缩成一套统一、可测、可重复的锁相判据，而不是每个实验都各说各话。

当前最小目标不是一次性统一所有理论叙事，而是先验证：

> 是否存在一组跨实验可复用的锁相判据，
> 使得连续场、图实验、RAM 相图和层级扫描都能落入同一语言。

### 为什么优先

当前项目把“层级”定义为锁相后的公频等价类，但这个定义若不能转成标准可测判据，那么：

- 层级仍然只是解释性术语
- 抽象概念、跨层级锁相也难以落地
- 理论统一会停在叙事层

### 最小实验

用三个现有入口交叉验证。

实验 A：RAM 相图中的稳定窗与双态窗

```bash
python3 current_ram_phase_scan.py --ratio-min 0.9 --ratio-max 1.3 --ratio-steps 21 --random-trials 24
```

实验 B：层级时间流速参数扫描

```bash
python3 hierarchy_flow_scan.py
```

实验 C：中心探针的时间频谱

```bash
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --probe-radius 2.0 --stft-window 64 --stft-hop 8
```

### 核心指标

建议统一用以下判据组描述“锁相”：

1. 主频差是否低于阈值
2. 相位差是否在时间窗内有界
3. 稳定时间窗是否超过最小长度
4. 模式切换是否低于阈值
5. 闭合误差是否处于低误差区

可对应到现有脚本里的指标包括：

- `stable_fraction`
- `oscillation_fraction`
- `mean_switch_rate`
- `closure_error_mean`
- `closure_error_normalized_mean`
- `probe_dominant_frequency`
- `chi_temporal_std`

### 证伪条件

若出现以下任一情况，则该假设被削弱：

1. 每个实验都必须使用一套完全不同的“锁相”定义
2. 没有任何跨脚本可复用阈值
3. 一个脚本中的稳定区，在另一个脚本中对应不到任何可比较对象
4. 所谓“层级”不能被主频、相位稳定窗或闭合误差统一表达

### 脚本入口

- [current_ram_phase_scan.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_phase_scan.py)
- [hierarchy_flow_scan.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_flow_scan.py)
- [hydrogen_color_field_emergence.py](file:///Users/bytedance/TRAEProjects/mind/hydrogen_color_field_emergence.py)

---

## 三、假设 3：当前理论可以进入标准统计比较，而不只是图像类比

### 假设内容

当前原型产生的结构现象，不只能通过“看图感觉像”来描述，而可以被转写成标准统计对象，并与基线模型进行比较。

换句话说，要验证的是：

> 当前理论是否不仅能产出图像，
> 还能产出足够强的统计证据来支撑“这不是普通扩散或普通振荡的平凡版本”。

### 为什么优先

如果没有标准统计比较，那么：

- 理论只能停留在图像、类比和直觉层
- 很难和主流科学理论建立正式接口
- 也无法判断哪些现象是本模型特有，哪些只是通用动力学现象

### 最小实验

实验 A：运行标准数学模型验证脚本

```bash
python3 testable_predictions.py
```

实验 B：对连续场原型补做统计总结

```bash
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --angular-momentum 1 --angular-gain 0.28
```

实验 C：对模式家族扫描做结果表汇总

```bash
python3 particle_family_suite.py --dimensions 2 --mode fast --max-runs-per-particle 4
```

### 核心指标

当前建议至少建立以下统计对象：

- 两点相关函数
- 功率谱
- 模式寿命分布
- 模式切换转移矩阵
- 稳定窗口宽度
- 参数鲁棒性评分

在现有脚本中已可直接使用或近似使用的指标包括：

- `confidence`
- `deviation`
- `self_consistency_history`
- `final_peak_to_mean_ratio`
- `effective_radius`
- `probe_dominant_frequency`
- `stable_fraction`

### 证伪条件

若出现以下情况，则该假设被削弱：

1. 新增统计量无法比图像肉眼判断提供更多信息
2. 与纯扩散或简单反应扩散模型比较时，没有可区分优势
3. 所谓“模式家族”在统计上无法稳定区分
4. 不同实验重复后，统计量不可复现或高度漂移

### 脚本入口

- [testable_predictions.py](file:///Users/bytedance/TRAEProjects/mind/testable_predictions.py)
- [hydrogen_color_field_emergence.py](file:///Users/bytedance/TRAEProjects/mind/hydrogen_color_field_emergence.py)
- [particle_family_suite.py](file:///Users/bytedance/TRAEProjects/mind/particle_family_suite.py)

---

## 四、建议验证顺序

建议按以下顺序推进：

1. 先验证“稳定模式是否真实存在”
2. 再验证“锁相层级是否可统一判定”
3. 最后验证“统计接口是否足够强，能与基线模型比较”

原因是：

- 若没有真实稳定模式，就没有后续理论对象
- 若没有锁相统一判据，层级与抽象概念无法标准化
- 若没有统计接口，理论无法进入科学比较

---

## 五、最短结论

当前最值得优先验证的，不是“宇宙终极叙事是否为真”，而是下面三件更基础的事：

1. 稳定模式是否是真实吸引子
2. 锁相层级是否可以统一定义
3. 理论结果是否可以进入标准统计比较

如果这三件事中的前两件无法成立，那么当前理论需要回退到“结构探索框架”。
如果三件事都能逐步成立，那么当前项目才有资格继续推进“统一理论”的下一阶段。
