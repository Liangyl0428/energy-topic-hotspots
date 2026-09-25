# 如何复算结果

仓库附带固定的数据快照、样本判断和参考结果。复算程序读取这些输入，重新计算指标与实验，再逐项核对输出。

## 安装与运行

在仓库目录执行：

```bash
python -m pip install -e '.[dev]'
energy-hotspots replay --output work/replay
energy-hotspots replay --experiments --output work/experiments
```

第一条复算命令检查文献指标和潜在任务指标；第二条还运行完整实验。每次指定新的空目录，以便区分各次运行。程序成功结束时，会在输出目录写入`REPLAY_VALIDATION.json`。

| 检查内容 | 范围 |
| --- | --- |
| 文献指标、候选与年度轨迹 | 21张表 |
| 潜在任务严格与扩展口径 | 24项指标检查 |
| 完整实验 | 10张实验表，包含1,500次权重扰动和172个情景 |

安装依赖后，这些操作无需联网、GPU、模型权重或完整数据库。结果对照会检查行列顺序和各字段；浮点值按规定容差比较。并列规则见[方法说明](METHOD.md#排名与并列)。

## 输入来自哪里

`assets/snapshot_20260925/hotspots/data/multiyear`包含不同数据范围下的季度、月度论文计数，以及对应的机构和引用汇总。机构并集、引用背景和全库去重信息在数据准备阶段计算。

潜在任务从附带的候选记录、专利申请主体、样本判断及任务政策证据重算。去重文件保留复算所需的记录ID，背景分母使用对应完整来源库的汇总值。

因此，离线复算验证的是这些固定输入下的计算一致性。它不重新聚类、检索完整语料或执行新的专家审阅。

## 重新生成Excel和报告

需要额外安装报告依赖。先完成一次含实验的复算，然后执行：

```bash
python -m pip install -e '.[dev,report]'
ENERGY_HOTSPOTS_RUN=work/experiments python pipelines/hotspots/multiyear_delivery.py
ENERGY_HOTSPOTS_RUN=work/experiments python pipelines/hotspots/multiyear_plots.py
```

输出目录中的CSV用于生成两份Excel和两份报告。CSV保留便于程序读取的字段名；Excel提供中文字段对照和实验情景说明。

## 使用新数据

`energy-hotspots score`可计算文献评分与基本数值资格，输入格式见[数据说明](DATA_SCHEMA.md)。新数据仍需完成数据范围检查和主题样本审阅，才能形成可供专家评估的名单。

`pipelines/hotspots/multiyear_prepare.py`等准备程序需要完整语料、分类标签和元数据。`ENERGY_HOTSPOTS_UPSTREAM`指定这些数据所在目录，`ENERGY_HOTSPOTS_RUN`指定输出目录；附带的精简数据不能替代这些原始输入。

## 验证记录

- [计算与环境验证](../provenance/VALIDATION.md)：测试范围与结果。
- [复算明细](../provenance/REPLAY_VALIDATION.json)：各项结果核对。
- [文件清单](../provenance/FILE_MANIFEST.json)：公开文件的大小和SHA-256校验值。

`python tools/check_release.py`检查发布文件是否符合清单。编辑受校验文件后，需用`tools/build_release.py --output <仓库外的新ZIP路径>`重新生成清单和发行包。
