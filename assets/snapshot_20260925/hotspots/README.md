# 750主题多年热点分析

- [主分析Excel](750类核心新兴潜在热点分析.xlsx)
- [实验Excel](750类热点消融实验与灵敏度分析.xlsx)
- [报告](REPORT.md) / [实验报告](EXPERIMENT_REPORT.md)

当前方法见data/MULTIYEAR_METHOD.json。核心近三年加最近一年；新兴最近一年对比此前三年非重叠背景并检查五年轨迹。潜在保持四个统一任务单元。

复现顺序：multiyear_prepare.py → multiyear_build.py → multiyear_review_samples.py（展示样本后另写明确判断）→ multiyear_build.py → multiyear_experiments.py → multiyear_finalize.py → multiyear_delivery.py → multiyear_validate.py。复算使用已冻结的语义决定不等于完成新的专家审核。独立仓库提供不依赖全量数据库的汇总回放。

旧一年主窗版在audit/MULTIYEAR_BASELINE.json所指备份中；旧年度脚本不再是当前默认入口。历史截止点为回顾性窗口诊断，不是预测回测。
