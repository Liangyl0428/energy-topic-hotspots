# 当前数据字段

当前紧凑输出位于assets/full_nmf500，使用F0001–F0500。

|文件|内容|
|---|---|
|topic_catalog.csv|主题、关键词、各来源数量及审核状态|
|quarter_counts.csv|category_id、period及论文计数，完整主题×季度网格|
|institution_citation_context.csv|机构去重、引用年份队列与时间窗口|
|hotspot_metrics.csv|核心／新兴分数、门槛、数值候选及审核状态|
|core_components.csv、emerging_components.csv|评分分量|
|cross_source_signals.csv|共同日期窗口的份额及潜在线索|
|transfer_source_summary.csv|跨来源覆盖|
|SUMMARY.json|截止日期、计数及分类摘要哈希|
|experiments/|情景、权重扰动、过滤结果、排名区间及完成清单|

数值候选不是人工确认热点。机构和引用与季度计数必须采用同一数据范围；逐条分类和元数据在共享工作区。
