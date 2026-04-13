# 假设验证执行清单

## 目标

本文件把 [PRIORITY_SCIENTIFIC_HYPOTHESES.md](file:///Users/bytedance/TRAEProjects/mind/docs/PRIORITY_SCIENTIFIC_HYPOTHESES.md) 中的三条优先科学假设，转写为一份可直接执行的实验清单。

它的目标不是补充新的理论叙事，而是统一：

- 实验执行顺序
- 命令模板
- 输出目录命名规范
- 通过 / 失败判据
- 实验记录格式

建议与以下文档配套阅读：

- [PRIORITY_SCIENTIFIC_HYPOTHESES.md](file:///Users/bytedance/TRAEProjects/mind/docs/PRIORITY_SCIENTIFIC_HYPOTHESES.md)
- [THEORY_UNIFICATION_ROADMAP.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_UNIFICATION_ROADMAP.md)
- [EFFECTIVE_MODEL_STATEMENT.md](file:///Users/bytedance/TRAEProjects/mind/docs/EFFECTIVE_MODEL_STATEMENT.md)

---

## 一、总执行顺序

严格按以下顺序推进：

1. 假设 1：稳定模式是真实吸引子，而不是数值假象
2. 假设 2：锁相层级可以被统一判据定义
3. 假设 3：当前理论可以进入标准统计比较，而不只是图像类比

原因：

- 如果稳定模式不成立，后面的“层级”“模式家族”“粒子样结构”都没有基础
- 如果锁相不能被统一判定，层级理论无法标准化
- 如果没有标准统计比较，理论无法进入科学接口层

---

## 二、统一输出规范

### A. 输出目录

所有实验都默认输出到：

- `resonance_data/`
- `verification_data/`

若脚本本身会自动生成时间戳目录，则直接保留其默认行为。

若脚本支持自定义输出目录，建议使用如下命名：

- 假设 1：`validation_h1_YYYYMMDD_HHMMSS`
- 假设 2：`validation_h2_YYYYMMDD_HHMMSS`
- 假设 3：`validation_h3_YYYYMMDD_HHMMSS`

### B. 结果归档建议

每完成一次实验批次，至少保留：

- 原始 `json / npz`
- 汇总 `md`
- 关键 `png / html`

不建议只保留截图而不保留结构化数据。

### C. 最低记录项

每次实验都应记录：

- 脚本名
- 命令
- 时间
- 输出目录
- 核心参数
- 核心指标
- 初步判断：通过 / 部分通过 / 失败

---

## 三、假设 1 执行清单

## 假设 1

稳定模式是真实吸引子，而不是数值假象。

### 目标

验证当前连续场原型中的局域模式、单中心结构和角向节点，是否对初值、步长和角动量参数具有鲁棒性。

### 使用脚本

- [hydrogen_color_field_emergence.py](file:///Users/bytedance/TRAEProjects/mind/hydrogen_color_field_emergence.py)
- [particle_family_suite.py](file:///Users/bytedance/TRAEProjects/mind/particle_family_suite.py)

### 执行顺序

1. 初值鲁棒性
2. 时间步长鲁棒性
3. 角向节点鲁棒性
4. 模式家族批量复查

### 实验 1A：初值鲁棒性

```bash
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --seed 20260409
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --seed 20260410
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --seed 20260411
```

记录指标：

- `final_peak_to_mean_ratio`
- `effective_radius`
- `participation_ratio`
- `probe_dominant_frequency`
- 单中心是否保留

通过判据：

- 三次运行都形成同类局域结构
- 峰均比和有效半径只出现温和波动
- 不因随机种子变化而完全失去模式

失败判据：

- 三次运行出现完全不同拓扑
- 两次以上无法形成局域模式
- 指标漂移幅度过大且无稳定窗口

### 实验 1B：时间步长鲁棒性

```bash
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.01
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.04
```

记录指标：

- 最终模式类型
- `final_peak_to_mean_ratio`
- `effective_radius`
- 主频是否保持同一量级

通过判据：

- 改变 `dt` 后主模式仍属于同一结构类别
- 不出现明显数值爆炸或完全失稳

失败判据：

- 仅因 `dt` 变化就导致模式完全消失
- 结论依赖某个单独 `dt`

### 实验 1C：角向节点鲁棒性

```bash
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --angular-momentum 1 --angular-gain 0.28
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --angular-momentum 2 --angular-gain 0.22
```

记录指标：

- 节点数
- 节点是否持续存在
- `probe_dominant_frequency`
- `time_frequency_spectrum`

通过判据：

- `m=1` 与 `m=2` 产生可区分的角向模式
- 节点不是瞬时噪声，而能维持到输出末段

失败判据：

- 所有角动量通道都回落为同一无节点模式
- 节点只在单帧短暂出现

### 实验 1D：模式家族复查

```bash
python3 particle_family_suite.py --dimensions 2 --mode fast --max-runs-per-particle 4
```

记录指标：

- 各模式家族最优样例的 `freq / radius / peak_mean`
- 家族间是否可分离

通过判据：

- 至少出现两类可稳定区分的模式家族

失败判据：

- 所有家族退化到同一模式

### 假设 1 结论规则

- `通过`：1A、1B、1C 中至少两项通过，且无核心失败信号
- `部分通过`：出现稳定模式，但参数窗较窄或节点稳定性不足
- `失败`：稳定模式高度依赖单一数值设置

---

## 四、假设 2 执行清单

## 假设 2

锁相层级可以被统一判据定义。

### 目标

验证不同实验中的“稳定窗、双态窗、闭合区、时间频谱稳定区”是否能用同一组锁相判据描述。

### 使用脚本

- [current_ram_phase_scan.py](file:///Users/bytedance/TRAEProjects/mind/current_ram_phase_scan.py)
- [hierarchy_flow_scan.py](file:///Users/bytedance/TRAEProjects/mind/hierarchy_flow_scan.py)
- [hydrogen_color_field_emergence.py](file:///Users/bytedance/TRAEProjects/mind/hydrogen_color_field_emergence.py)

### 建议统一判据组

建议至少记录以下五项：

1. 主频差
2. 相位差是否有界
3. 最小稳定时间窗
4. 模式切换率
5. 闭合误差

### 实验 2A：RAM 相图稳定窗

```bash
python3 current_ram_phase_scan.py --ratio-min 0.9 --ratio-max 1.3 --ratio-steps 21 --random-trials 24
```

记录指标：

- `stable_fraction`
- `oscillation_fraction`
- `transition_fraction`
- `mean_switch_rate`

通过判据：

- 存在清晰稳定窗或双态窗
- 稳定区与切换区可区分

失败判据：

- 全区间表现混乱，没有可识别窗口

### 实验 2B：层级流扫描

```bash
python3 hierarchy_flow_scan.py
```

记录指标：

- `smooth_score`
- `split_score`
- `chi_temporal_std`
- `closure_error_mean`
- `stable_island_fraction`

通过判据：

- 能找到低闭合误差且高稳定岛比例区域
- 平滑区与分裂区可分离

失败判据：

- 参数图无明显结构，所有区域同质化

### 实验 2C：连续场时频锁相

```bash
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --probe-radius 2.0 --stft-window 64 --stft-hop 8
```

记录指标：

- `probe_dominant_frequency`
- 主频是否稳定
- 模式切换是否出现
- 时频谱是否出现集中脊线

通过判据：

- 时频谱存在清晰主频带
- 主频变化可以和稳定区或切换区对应

失败判据：

- 谱完全弥散，无法提取有效主频

### 假设 2 结论规则

- `通过`：三个实验都能提取可比较的稳定性对象，且至少能构造一组共享判据
- `部分通过`：能提取稳定区，但跨实验阈值尚未统一
- `失败`：不同脚本完全无法共用锁相语言

---

## 五、假设 3 执行清单

## 假设 3

当前理论可以进入标准统计比较，而不只是图像类比。

### 目标

验证当前原型是否能稳定地产出标准统计对象，并与更简单的基线模型进行比较。

### 使用脚本

- [testable_predictions.py](file:///Users/bytedance/TRAEProjects/mind/testable_predictions.py)
- [hydrogen_color_field_emergence.py](file:///Users/bytedance/TRAEProjects/mind/hydrogen_color_field_emergence.py)
- [particle_family_suite.py](file:///Users/bytedance/TRAEProjects/mind/particle_family_suite.py)

### 实验 3A：标准预测验证

```bash
python3 testable_predictions.py
```

记录指标：

- `passed`
- `confidence`
- `measured_value`
- `expected_value`
- `deviation`

通过判据：

- 多条预测可重复通过
- 偏差与置信度处于可接受范围

失败判据：

- 大多数预测不通过
- 输出只能作为叙事展示，不能作为统计证据

### 实验 3B：连续场统计总结

```bash
python3 hydrogen_color_field_emergence.py --dimensions 2 --width 41 --height 41 --duration 6 --dt 0.02 --angular-momentum 1 --angular-gain 0.28
```

记录指标：

- `final_peak_to_mean_ratio`
- `effective_radius`
- `probe_dominant_frequency`
- `time_frequency_spectrum`
- 输出目录中的 `field_series_*.npz`

通过判据：

- 能提取稳定统计量，而不只是输出图片
- 同一设置重复运行时，统计量波动可控

失败判据：

- 指标高度不稳定
- 无法从结果中抽出统一统计对象

### 实验 3C：模式家族统计区分

```bash
python3 particle_family_suite.py --dimensions 2 --mode fast --max-runs-per-particle 4
```

记录指标：

- `particle_family_results.csv`
- 家族间 `freq / radius / peak_mean` 的分布差异
- 最优样例是否退化

通过判据：

- 至少出现部分家族可在统计上区分

失败判据：

- 所有家族的统计分布高度重合

### 假设 3 结论规则

- `通过`：至少已有一组稳定统计量，可以支持与基线模型比较
- `部分通过`：统计量已存在，但区分力不足
- `失败`：仍然只能靠图像类比进行解释

---

## 六、统一实验记录模板

每跑完一个实验批次，建议补一条记录，格式如下：

```md
## 实验记录

- 假设：H1 / H2 / H3
- 实验编号：1A / 2B / 3C
- 日期：
- 脚本：
- 命令：
- 输出目录：
- 核心参数：
- 核心指标：
- 初步结果：通过 / 部分通过 / 失败
- 异常情况：
- 下一步建议：
```

---

## 七、最终汇总规则

当三条假设都执行完后，建议最终汇总为三种状态之一：

- `继续推进`
  - H1 通过
  - H2 至少部分通过
  - H3 至少部分通过

- `回到模型整理`
  - H1 部分通过
  - H2 与 H3 区分力不足

- `暂停宏大理论外推`
  - H1 失败
  - 或 H2 失败且 H3 失败

---

## 八、最短结论

这份清单的核心作用只有一个：

> 把“理论是否值得继续推进”从感觉判断，变成有顺序、有命令、有指标、有证伪条件的执行过程。

只要严格按这份清单推进，当前项目就能逐步从：

`理论叙事 + 原型图像`

推进到：

`假设 -> 实验 -> 指标 -> 结论`
