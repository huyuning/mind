# Legacy Scripts

本目录用于归档仓库根目录下不再作为当前主线入口的历史脚本、重复版本和中间试验版本。

归档原则：

- 当前 [README.md](file:///Users/bytedance/TRAEProjects/mind/README.md) 与 [10_EXPERIMENTS.md](file:///Users/bytedance/TRAEProjects/mind/docs/10_EXPERIMENTS.md) 明确列出的主线入口，继续保留在根目录
- 已被更新版本覆盖、仅用于历史对照的脚本，迁移到 `legacy/`
- 迁移后尽量保留原始文件名，方便追踪实验演化路径

当前目录约定：

- `legacy/cartesian/`：旧版笛卡尔积翻转实验
- `legacy/entanglement/`：旧版纠缠翻转实验
- `legacy/exploratory/`：低耦合的探索性旧实验、局部验证脚本与中间版本
- `legacy/graphs/`：旧版图结构变体实验
- `legacy/hamming/`：旧版汉明码与全量轨迹测试脚本
- `legacy/resonance/`：旧版共振翻转、追踪与多次迭代实验

当前仍保留在根目录的相关入口：

- 笛卡尔积当前保留入口：`resonance_cartesian_complete.py`
- 笛卡尔积可视化入口：`resonance_visualize.py`
- 当前共振迭代保留入口：`resonance_iter_v2.py`
- 标准汉明码入口：`hamming_experiment.py`
- 汉明码验证入口：`verify_hamming.py`
- 汉明码纠缠专题入口：`hamming_entanglement.py`
- 汉明码共振校正专题入口：`hamming_resonance_correct.py`
- 当前纠缠翻转保留版本：`entanglement_flip_v4.py`
- 当前图结构对照入口：`multi_graph_test.py`

注意：

- `legacy/` 下脚本不再保证属于当前主线入口
- 它们仍可运行，但不保证与现行文档口径完全一致
- 若需要现行理论与实验入口，请先看 [docs/THEORY_CANON.md](file:///Users/bytedance/TRAEProjects/mind/docs/THEORY_CANON.md) 与 [docs/10_EXPERIMENTS.md](file:///Users/bytedance/TRAEProjects/mind/docs/10_EXPERIMENTS.md)
