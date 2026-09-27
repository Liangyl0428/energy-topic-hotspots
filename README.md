# 能源热点智能分析

基于500主题的全量论文、专利、政策分类，计算核心、新兴及潜在跨来源候选信号。输入共5,119,004条记录，输出使用F0001–F0500主题编号。

## 当前怎么做

1. 核验分类完成标记、总量与分片哈希。
2. 以2026-06-30为截止日，构造2021Q3—2026Q2完整季度网格，统计论文份额、持续性、机构与引用。
3. 按固定权重评分，并应用规模、活跃、增长和统计诊断门槛。
4. 在共同2026年上半年窗口计算专利／政策关联，输出待审核线索。
5. 执行成分、门槛、权重、时间窗口、文本质量、来源和政策文档留一等消融／灵敏度实验。

当前有287个核心数值候选、119个新兴数值候选；范围审核未完成，不等于已确认热点。潜在关联不等于政策同任务支持或商业成功。

## 核心入口

|内容|入口|
|---|---|
|全量统计与计算|[build.py](pipelines/full_nmf/build.py)|
|评分与门槛|[scoring.py](src/energy_hotspots/scoring.py)|
|消融／灵敏度|[experiments.py](pipelines/full_nmf/experiments.py)|
|当前结果|[hotspot_metrics.csv](assets/full_nmf500/hotspot_metrics.csv)|
|当前实验|[实验报告](assets/full_nmf500/experiments/REPORT.md)|

[方法与公式](docs/METHOD.md) · [字段说明](docs/DATA_SCHEMA.md) · [复现运行](docs/REPRODUCING.md) · [核心文件清单](docs/CORE_FILES.md)。

完整重算需要工作区的逐条分类及论文元数据；Git提供核心源码和紧凑结果。分类总量与具体热点时间窗口的计数分开解释。

## 目录导航

[完整项目结构及每个文件用途](docs/PROJECT_STRUCTURE.md)。当前成果在 `assets/full_nmf500/`；`tests/fixtures/` 只用于回归测试。
