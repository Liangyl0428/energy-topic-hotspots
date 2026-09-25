# Energy Topic Hotspots — 750主题多年热点识别

当前版本 `0.3.0 / 750-multiyear-v1`。核心采用近三年持续表现并检查最近一年；新兴采用最近一年相对此前三年背景，并检查五年轨迹；潜在保持统一任务集合。

**当前结果：12个核心、22个新兴/持续升温初评候选。** 潜在4任务单元中2项双口径支持、1项条件性跟踪、1项观察。结果供专家评审，不证明技术首创、领先或未来成功。

## 结果

- [主分析Excel](assets/snapshot_20260925/hotspots/750类核心新兴潜在热点分析.xlsx)
- [消融与灵敏度Excel](assets/snapshot_20260925/hotspots/750类热点消融实验与灵敏度分析.xlsx)
- [分析报告](assets/snapshot_20260925/hotspots/REPORT.md)
- [实验报告](assets/snapshot_20260925/hotspots/EXPERIMENT_REPORT.md)
- [五年年度轨迹](assets/snapshot_20260925/hotspots/results/multiyear_annual_trajectories.csv)
- [旧新结果变化](assets/snapshot_20260925/hotspots/results/multiyear_before_after.csv)

原15核心、16新兴在仅改变数值方法时仍通过。跨年补审后，4个原核心因任务范围混杂转入观察，新增1个核心；新兴新增6个。不能把这些变化都归因于时间窗，也不能把退出解释为技术不重要。

## 独立离线复现

Python 3.10+，从本目录可编辑安装：

```bash
python -m pip install -e '.[dev]'
energy-hotspots replay --output work/replay
energy-hotspots replay --experiments --output work/experiments
python -m pytest -q
python tools/check_release.py
```

每次使用新的空输出目录。安装依赖后无需网络、GPU、模型权重或原项目数据库。回放重算21张多年指标/候选/轨迹表、潜在严格/扩展指标；实验模式另重跑1,500次权重扰动、172个场景（核心/新兴101个，潜在71个），与交付快照对照。

评分输入是冻结季度计数、各情景机构并集和引用汇总；质量/几何/去重/标签压力输入已在原全库重新统计。潜在从候选记录与同源主体重算。回放不重新扫描完整语料、检索全库或进行新的专家审阅；历史截止点是回顾性敏感性，不是预测回测。

## 仓库内容

| 目录 | 内容 |
| --- | --- |
| `src/energy_hotspots` | 多年纯评分函数、CLI、离线复现 |
| `pipelines/hotspots` | 多年输入适配、候选、冻结样本决定、实验、交付与潜在算法 |
| `assets/snapshot_20260925/hotspots` | 当前Excel、报告、必要汇总、跨年样本、潜在候选子集 |
| `tests` | 窗口不重叠、基线隔离、缺失历史、来源隔离与快照回归 |
| `provenance` | 验证结果、迁移说明与文件哈希 |

固定750标签；没有重新聚类。无全量文献/专利库、向量或模型权重。少量已读摘录和潜在候选文本用于证据追溯与复算。旧一年主窗版本已在原工作区备份，不混入当前结果。

`energy-hotspots score --help` 支持新数据的数值评分；输入契约见[DATA_SCHEMA.md](docs/DATA_SCHEMA.md)。该命令只生成数值资格，不自动进行跨过滤稳健确认、语义审阅或输出正式推荐。方法见[METHOD.md](docs/METHOD.md)，复现边界见[REPRODUCING.md](docs/REPRODUCING.md)。
