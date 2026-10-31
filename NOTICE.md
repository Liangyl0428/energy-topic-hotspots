# 数据与第三方组件

本仓库包含：代码、技术词条词典（`config/technology_terms/`）、判定配置（`config/*.json`）、
以及可复算的紧凑计数与判定产物（`outputs/terms/*.csv`、`run_meta.json`）。

`outputs/terms/` 随仓库提供，是为了让 `report` / `find` 克隆后即可运行；其中不含原始语料、
不含逐篇导出。子方向聚合与电网瓶颈分析已迁至 `grid-bottleneck-report` 仓库，本仓库不再产出
`subtopic_report.csv`。

**不包含**：论文库、专利库、政策全文等原始语料，也不包含任何主题模型或模型权重。
语料通过环境变量指向外部目录（见 README 的「数据位置」），因此 `rebuild` 需要外部数据才能运行；
`report` 只需要 `outputs/` 下的计数产物。

未指定开源许可证；公开访问本身不等同于授予任意使用许可。第三方 Python 库按各自许可使用，未复制到仓库内。
