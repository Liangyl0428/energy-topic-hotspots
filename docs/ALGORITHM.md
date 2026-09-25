# 核心算法代码导读

最先看[scoring.py](../src/energy_hotspots/scoring.py)：它包含核心与新兴热点的指标、评分公式和入选条件。潜在热点的统计与门槛在[potential_unified_metrics.py](../pipelines/hotspots/potential_unified_metrics.py)。

本仓库的热点识别由统计指标、规则筛选、数据范围检查和已记录的样本判断共同组成。输入采用固定的750主题目录；离线复算不重新训练分类模型，也不自动完成一次新的专家审阅。

## 核心与新兴：从指标到名单

| 阅读顺序 | 文件和函数 | 作用 |
| --- | --- | --- |
| 1 | [scoring.py](../src/energy_hotspots/scoring.py) → `windows()` | 根据截止季度划分五个不重叠年度 |
| 2 | 同文件 → `score()` | 计算年度份额、增长、趋势、持续性、机构与引用指标，形成核心/新兴分数 |
| 3 | 同文件 → `gates()` | 逐条检查论文规模、活跃性、增长与统计筛查条件 |
| 4 | [multiyear_build.py](../pipelines/hotspots/multiyear_build.py) → `build()` | 比较质量、几何、去重等数据范围，加入最新同月检查，并读取样本范围判断 |
| 5 | 同文件中的 `final_core`、`final_emerging` | 合并数值条件与样本审阅，形成初评名单 |

`score()`接收主题目录`tax`、季度论文计数`q`、机构与引用汇总`context`，返回完整指标表`z`、核心评分成分`cc`和新兴评分成分`ec`。输入格式见[DATA_SCHEMA.md](DATA_SCHEMA.md)。

最终名单的逻辑为：

```text
核心入选 = 核心数值条件通过 AND 核心样本范围审阅通过
新兴入选 = 新兴数值及数据方向检查通过 AND 新兴样本范围审阅通过
```

因此，看分数时也要查看`core_eligible`、`emerging_robust`和样本判断；仅提高分数不会自动获得入选资格。

文献评分权重在`CORE_WEIGHTS`、`EMERGING_WEIGHTS`中，入选阈值在`gates()`中。`ordered_scores()`和`rank_scores()`处理并列排序。流水线使用的[multiyear_scoring.py](../pipelines/hotspots/multiyear_scoring.py)与公开模块内容一致，现有测试会核对两份实现同步。

## 潜在热点：从应用方向到跟踪建议

| 阅读顺序 | 文件和函数 | 作用 |
| --- | --- | --- |
| 1 | [potential_unified.py](../pipelines/hotspots/potential_unified.py) → `UNITS`、`classify()` | 定义4个具体方向，将候选文献判为明确相关、范围待判断或不相关 |
| 2 | [potential_unified_metrics.py](../pipelines/hotspots/potential_unified_metrics.py) → `load_records()`、`selected()` | 应用已记录的样本判断，按严格或扩展范围选择文献 |
| 3 | 同文件 → `calculate()` | 从同一批任务记录统计专利、论文、主体、政策与相对份额，并计算任务内排序分数 |
| 4 | 同文件 → `with_may()`、`qualify()` | 检查1—8月与1—5月两个同期窗口，并判断全部数值条件是否通过 |
| 5 | 同文件 → `build()`中的 `evidence_tier` | 比较严格与扩展计算结果，给出可跟踪、有条件跟踪或保留观察的解释 |

潜在权重在`calculate()`中，为专利数量百分位30%、主体数量百分位20%、政策强度50%；资格门槛在`qualify()`中。分数用于四个方向内部排序，是否达标由门槛判定。

```text
仅明确相关文献达标，加入待判断文献后也达标 → 两种范围均支持，可跟踪
仅明确相关文献达标，加入待判断文献后未达标 → 有条件跟踪，先核实待判断记录
仅明确相关文献尚未达标 → 当前证据不足，保留观察
```

“明确相关”使用题名或局部研究目的中的任务证据；“待判断”表示出现了相关提及，但研究对象或任务范围仍不明确。扩展范围加入待判断记录，明确不相关的记录始终排除。四个方向的具体结果见[METHOD.md](METHOD.md#潜在热点具体应用任务的证据)。

## 实验和复算入口

[multiyear_experiments.py](../pipelines/hotspots/multiyear_experiments.py)运行核心与新兴的消融和灵敏度实验；[potential_experiments.py](../pipelines/hotspots/potential_experiments.py)运行潜在任务实验。

`energy-hotspots replay --experiments --output work/experiments`会重算约定范围的指标与实验，并与参考结果核对。命令调用[src/energy_hotspots/replay.py](../src/energy_hotspots/replay.py)和[replay_snapshot.py](../pipelines/hotspots/replay_snapshot.py)。这些入口组织运行与验证；评分公式和门槛位于上面标出的算法文件。
