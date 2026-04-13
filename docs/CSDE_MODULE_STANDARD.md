# CSDE 模块方案与标准

## 一、定位

`CSDE` 是 `胞元基底结构动力学研究引擎`（`Cellular-Substrate Structural Dynamics Engine`）的简称。

本文件用于定义 `CSDE` 的模块方案、数据标准、接口边界、命名规范和升级路径，确保后续离线查看器、流式 IO、参数扫描、报告系统和实时交互引擎都建立在统一架构之上，而不是继续演变为相互耦合的专题脚本集合。

在当前阶段，`CSDE` 的架构原则是：

- 实验层负责产生状态
- IO 层负责传输状态
- 指标层负责解释状态
- 查看器层负责消费状态
- 报告层负责汇总状态

禁止以下高耦合设计：

- 实验脚本直接依赖 UI 控件对象
- 查看器直接读取实验内部变量
- 报告器直接硬编码某个实验目录结构
- 指标模块直接耦合某个实验的私有实现

---

## 二、总体模块方案

建议按以下目录分层组织 `CSDE`：

```text
csde/
  schema/
    data_schema.py
    metric_schema.py
    schema_version.py
  core/
    state_models.py
    event_models.py
    engine_protocols.py
  io/
    stream_io.py
    snapshot_io.py
    file_loader.py
  metrics/
    frequency_metrics.py
    mass_metrics.py
    alert_rules.py
  registry/
    experiment_registry.py
  orchestration/
    parameter_scan.py
    scan_report.py
  viewer/
    viewer_app.py
    scene_adapter.py
    timeline_panel.py
    structure_tree.py
  experiments/
    hydrogen_coaxial_axis_emergence.py
```

各模块职责如下：

### 1. `schema`

作用：

- 定义统一数据结构
- 定义字段规范
- 定义 schema 版本

约束：

- 只定义结构
- 不包含实验逻辑
- 不包含 UI 逻辑

### 2. `core`

作用：

- 定义核心对象模型
- 定义状态协议和接口协议

约束：

- 不依赖具体存储格式
- 不依赖具体实验脚本
- 不依赖具体查看器实现

### 3. `io`

作用：

- 负责状态快照和流式读写
- 负责离线文件加载和恢复

约束：

- 只处理序列化与反序列化
- 不做指标计算
- 不做 UI 控制

### 4. `metrics`

作用：

- 统一计算时间序列指标、质量代理、频率稳定性等量
- 定义告警规则与阈值解释

约束：

- 指标模块只消费标准化状态对象
- 不直接依赖实验内部变量名

### 5. `registry`

作用：

- 注册实验定义
- 提供默认参数、扫描轴和指标集

约束：

- 不直接负责运行 UI
- 不直接负责写文件格式细节

### 6. `orchestration`

作用：

- 参数扫描
- 批量实验调度
- 报告生成

约束：

- 只调用实验与指标接口
- 不直接关心查看器实现

### 7. `viewer`

作用：

- 负责离线查看器与后续实时交互引擎
- 渲染 3D 视图、时间轴、结构树、事件面板和指标面板

约束：

- 只读取标准化状态流和快照
- 不直接嵌入实验逻辑

### 8. `experiments`

作用：

- 承载具体实验实现
- 负责演化规则和原始状态生成

约束：

- 实验必须能单独运行
- 实验必须能被参数扫描器调用
- 实验输出必须符合标准 schema

---

## 三、核心数据标准

`CSDE` 当前统一要求有以下四类基础对象：

- `FrameState`
- `EventRecord`
- `MetricRecord`
- `RunStatus`

建议最小定义如下：

```python
@dataclass
class FrameState:
    frame_index: int
    time: float
    cells: list[dict]
    axis_nodes: list[dict]
    coaxial_clusters: list[dict]
    metrics: dict[str, float]


@dataclass
class EventRecord:
    event_index: int
    time: float
    event_type: str
    payload: dict[str, object]


@dataclass
class MetricRecord:
    frame_index: int
    time: float
    values: dict[str, float]


@dataclass
class RunStatus:
    run_id: str
    experiment_name: str
    state_schema_version: str
    status: str
    latest_frame_index: int
    latest_time: float
```

### 字段标准

统一字段命名：

- 时间统一用 `time`
- 帧号统一用 `frame_index`
- 事件号统一用 `event_index`
- 对象主键统一用 `id`
- 层级统一用 `level`
- 空间中心统一用 `center`
- 方向统一用 `direction`
- 强度统一用 `strength`
- 持久度统一用 `persistence`

### 命名标准

- 文件名：`snake_case`
- 类名：`PascalCase`
- 指标名：`snake_case`
- 协议/接口：`...Protocol` 或 `...Interface`
- 原型文件：`..._prototype.py`

---

## 四、版本标准

所有 `CSDE` 输出和 schema 均应包含以下基础字段：

- `engine_name`
- `schema_name`
- `schema_version`

建议每个实验输出目录至少包含：

- `summary.json`
- `schema.json`
- `status.json`

### schema 升级规则

- 增加字段且保持兼容：次版本递增
- 删除字段或改变字段语义：主版本递增

---

## 五、IO 标准

第一阶段统一采用以下轻量流格式：

- `state_stream.jsonl`
- `event_stream.jsonl`
- `metric_stream.csv`
- `status.json`

### 流式写入要求

- 单条记录一次写完整一行
- 每条记录写入后应 `flush`
- 查看器允许按字节偏移量增量读取

### 快照要求

可选导出：

- `snapshot_000123.json`

用于：

- 断点恢复
- 随机跳转
- 调试某个关键帧

---

## 六、接口标准

### Writer 接口

```python
class CSDEWriter(Protocol):
    def write_state(self, frame: FrameState) -> None: ...
    def write_event(self, event: EventRecord) -> None: ...
    def write_metric(self, metric: MetricRecord) -> None: ...
    def update_status(self, status: RunStatus) -> None: ...
    def close(self) -> None: ...
```

### Reader 接口

```python
class CSDEReader(Protocol):
    def poll_states(self) -> list[FrameState]: ...
    def poll_events(self) -> list[EventRecord]: ...
    def poll_metrics(self) -> list[MetricRecord]: ...
    def read_status(self) -> RunStatus | None: ...
```

### Viewer Adapter 接口

```python
class ViewerAdapter(Protocol):
    def load_frame(self, frame: FrameState) -> None: ...
    def apply_events(self, events: list[EventRecord]) -> None: ...
    def update_metrics(self, metrics: list[MetricRecord]) -> None: ...
```

这些接口的核心要求是：

- 实验层不直接知道查看器细节
- 查看器不直接知道实验内部实现
- 存储介质可替换而不影响实验和 UI

---

## 七、指标系统标准

指标系统分三层：

- 指标计算逻辑
- 指标 schema 定义
- 告警规则

### 指标 schema 要求

每个指标至少应包含：

- `name`
- `objective`
- `unit`
- `description`
- `default_thresholds`
- `alert_rule`

示例：

```json
{
  "name": "dominant_frequency_std",
  "objective": "min",
  "unit": "hz_proxy",
  "description": "主导频率标准差",
  "default_thresholds": {
    "warning_upper": 0.03,
    "critical_upper": 0.08
  },
  "alert_rule": {
    "mode": "upper_bound"
  }
}
```

### 告警标准

统一使用三级状态：

- `ok`
- `warning`
- `critical`

判定逻辑建议放在：

- `metrics/alert_rules.py`

配置源建议统一放在：

- `metric_schema`

---

## 八、实验注册标准

每个实验必须在注册表中声明：

- `name`
- `description`
- `runner`
- `default_namespace`
- `scan_axes`
- `metric_names`

实验本体必须满足：

- 可单独运行
- 可被参数扫描器调用
- 输出符合标准 schema

---

## 九、查看器标准

第一版查看器至少应支持以下面板：

- 时间轴面板
- 3D 主视图
- 结构树面板
- 指标面板
- 事件面板

查看器不得：

- 直接调用实验函数获取内部状态
- 依赖某个实验的私有字段名

查看器只允许：

- 读取标准化状态流
- 读取标准化快照
- 读取标准化指标流

---

## 十、实施顺序

当前建议的实施顺序如下：

1. 定义 `schema`
2. 定义 `core protocols`
3. 实现 `io`
4. 让一个实验接入标准写入
5. 让查看器接入标准读取
6. 再接参数扫描和报告系统

---

## 十一、当前冻结的第一批标准

为避免后续频繁推翻，当前建议先冻结以下标准：

- 数据对象：
  - `FrameState`
  - `EventRecord`
  - `MetricRecord`
  - `RunStatus`
- 流格式：
  - `JSONL + CSV + status.json`
- 模块边界：
  - `experiment -> writer -> reader -> viewer`
- 指标来源：
  - 实验 summary 与 metric stream
- 命名规则：
  - 统一 `snake_case`

---

## 十二、最短结论

`CSDE` 后续所有模块建设必须围绕“状态标准化、接口解耦、观察器独立、指标可复用”四个原则展开。

最重要的不是优先堆功能，而是优先建立稳定的：

- 数据契约
- 接口边界
- 模块职责
- 升级路径

只有在这些标准稳定后，离线查看器、流式读写、实时交互引擎和更高层物理实验模块才能持续演进而不互相拖垮。
