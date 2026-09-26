# Energy Topic Hotspots · 能源热点智能识别

`v0.2.1` 已完成[严格审查与全样本重算](docs/V0.2.1_AUDIT.md)。
[当前CSV、Excel和实验](assets/nmf500/)使用修正后的NMF贡献标签，保留6个核心条件跟踪、
2个新兴条件跟踪及3个潜在应用线索；这些均不是已确认的稳健技术热点。
补充季度完整性、对象关联和审阅版本校验；以下750主题结果为历史基线。

本项目分析750个能源相关主题，结合论文、专利和政策，识别值得专家进一步评估的研究方向。

2026-09-26另新增[OpenAlex关键词NMF500样本版重算](docs/NMF500.md)：基于新主题
统一推断论文标签，重算核心、新兴和潜在跨来源候选信号，结果写入本地
`outputs/nmf500_v021/`。该版覆盖已完成新分类的冻结样本，规模与以下750类历史全量版不同。

| 类型 | 关注的问题 | 结果 |
| --- | --- | --- |
| 核心热点 | 哪些方向在近三年持续活跃，并具有一定研究规模？ | 12个初评候选 |
| 新兴热点 | 哪些方向最近一年的研究关注度明显高于此前多年？ | 22个新兴或持续升温初评候选 |
| 潜在热点 | 哪些具体应用任务同时获得专利活动和政策支持？ | 评估4个应用方向：虚拟电厂、电力大模型可跟踪；空气源热泵需核实范围；知识图谱暂缺充分证据 |

结果用于组织专家评审和应用跟踪。新兴表示研究关注度上升；潜在表示存在应用跟踪依据，均不直接等同于技术首创、技术领先或未来成功。同一主题可能同时满足核心与新兴条件。

## 核心算法在哪里

**从[scoring.py](src/energy_hotspots/scoring.py)开始看：`score()`计算核心与新兴指标和分数，`gates()`定义入选条件。**

| 需要了解的算法 | 核心文件与入口 | 负责什么 |
| --- | --- | --- |
| 核心、新兴的评分公式和门槛 | [scoring.py](src/energy_hotspots/scoring.py)：`score()`、`gates()` | 年度份额、增长、持续性、机构和引用指标，以及加权评分 |
| 核心、新兴最终如何入选 | [multiyear_build.py](pipelines/hotspots/multiyear_build.py)：`build()` | 在数值条件上加入数据范围检查与已记录的样本审阅判断 |
| 潜在方向的指标和门槛 | [potential_unified_metrics.py](pipelines/hotspots/potential_unified_metrics.py)：`calculate()`、`qualify()`、`with_may()` | 同任务论文、专利、主体与政策统计，检查两个同期窗口 |
| 哪些文献属于潜在方向 | [potential_unified.py](pipelines/hotspots/potential_unified.py)：`UNITS`、`classify()` | 定义具体应用方向，将候选记录分为明确相关、待判断、不相关 |

[算法代码导读](docs/ALGORITHM.md)按计算顺序说明这些函数的关系、输入输出和参数位置。

## 查看结果

建议先读报告，再用Excel查看指标和证据。

v0.2.1入口：[500主题报告](assets/nmf500/REPORT.md)、
[审阅结果Excel](assets/nmf500/500主题热点审阅结果.xlsx)、
[新灵敏度实验](assets/nmf500/experiments/REPORT.md)。以下为历史750主题交付。

- [分析报告](assets/snapshot_20260925/hotspots/REPORT.md)：入选方向、判断依据和需要关注的边界。
- [主分析Excel](assets/snapshot_20260925/hotspots/750类核心新兴潜在热点分析.xlsx)：750类结果、候选名单、样本审阅和潜在任务证据。
- [实验报告](assets/snapshot_20260925/hotspots/EXPERIMENT_REPORT.md)：时间窗口、数据范围和参数变化对结果的影响。
- [消融与灵敏度Excel](assets/snapshot_20260925/hotspots/750类热点消融实验与灵敏度分析.xlsx)：1,500次权重试验、172个实验情景及逐项结果。

## 方法概览

核心热点考察2023年7月至2026年6月的三年表现，并要求最近一年持续活跃。新兴热点将2025年7月至2026年6月与此前三个完整年度比较，同时检查五年轨迹。年度论文数先除以同年背景库规模，再比较份额，减少不同年份收录量差异的影响。

潜在热点围绕四个具体任务，按相同任务定义筛选论文和专利。专利规模与申请主体来自同一批专利记录，政策证据也对应同一任务。严格口径只纳入证据明确的记录；扩展口径还纳入范围待判断的记录，用于检查结论是否依赖纳入边界。

详细定义、评分权重和入选条件见[方法说明](docs/METHOD.md)。专家可重点检查主题边界、样本是否具有代表性，以及对数据范围和政策证据的依赖。

## 在本地复算

需要Python 3.10或更高版本。在仓库目录执行：

```bash
python -m pip install -e '.[dev]'
energy-hotspots replay --output work/replay
energy-hotspots replay --experiments --output work/experiments
python -m pytest -q
python tools/check_release.py
```

每次复算使用新的空输出目录。安装依赖后，复算无需联网、GPU或模型权重。程序从仓库附带的汇总数据和候选证据重新计算，再与参考结果逐项核对。

[复现指南](docs/REPRODUCING.md)说明可复算的范围；[输入格式](docs/DATA_SCHEMA.md)说明如何给新数据计算分数。新数据的主题范围和样本判断需要重新评估。

## 文件导航

| 目录 | 内容 |
| --- | --- |
| `src/energy_hotspots` | 评分函数、命令行入口和离线复算 |
| `pipelines/hotspots` | 数据准备、样本审阅、实验和报告生成程序 |
| `assets/snapshot_20260925/hotspots` | Excel、报告、汇总数据和必要证据 |
| `docs` | 方法、输入格式和复现指南 |
| `tests` | 计算规则与结果复算测试 |
| `provenance` | 数据来源说明、验证记录和文件校验值 |

仓库保留固定750主题历史目录，并提供NMF500样本版。二者ID、样本和数值门槛不能混用。
附带数据足以完成约定范围的离线复算，不包含完整论文或专利数据库、向量和模型文件。
