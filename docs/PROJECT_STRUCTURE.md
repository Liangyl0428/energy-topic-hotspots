# 项目结构与逐文件用途

## 从哪里开始

当前计算入口是 `pipelines/full_nmf/`，当前成果仅在 `assets/full_nmf500/`。`tests/fixtures/` 是固定回归输入，不是另一套待选用成果。共享模块和兼容实现因当前调用或测试需要而保留，不应直接替代全量入口。

阅读 [当前报告](../assets/full_nmf500/experiments/REPORT.md)、[方法](METHOD.md) 和 [复现步骤](REPRODUCING.md)。下面逐项列出全部 Git 管理的文件及目录，不用省略号隐藏文件。

## 完整结构图

```text
energy-topic-hotspots/  # 当前发布源码与紧凑成果
├── .github/  # 远端自动化配置
│   └── workflows/  # 持续集成工作流
│       └── tests.yml  # 自动安装依赖并运行测试和校验
├── assets/  # 发布用的紧凑结果；不是原始语料
│   └── full_nmf500/  # 当前全量 500 主题流程或成果
│       ├── experiments/  # 已完成消融与灵敏度实验的表格、报告和校验记录
│       │   ├── COMPLETE.json  # 完成标记、输入绑定和输出指纹
│       │   ├── PROTOCOL.json  # 实验参数、范围、限制与输入指纹
│       │   ├── REPORT.md  # 面向读者的结果报告
│       │   ├── baseline_context.csv  # 实验各条件的机构/引用背景数据
│       │   ├── baseline_quarter_counts.csv  # 实验各条件的季度计数数据
│       │   ├── data_filter_counts.csv  # 文本过滤后的实际记录数量
│       │   ├── exclude_title_only_context.csv  # 实验各条件的机构/引用背景数据
│       │   ├── exclude_title_only_quarter_counts.csv  # 实验各条件的季度计数数据
│       │   ├── paper_margin_0025_context.csv  # 实验各条件的机构/引用背景数据
│       │   ├── paper_margin_0025_quarter_counts.csv  # 实验各条件的季度计数数据
│       │   ├── paper_margin_005_context.csv  # 实验各条件的机构/引用背景数据
│       │   ├── paper_margin_005_quarter_counts.csv  # 实验各条件的季度计数数据
│       │   ├── paper_margin_010_context.csv  # 实验各条件的机构/引用背景数据
│       │   ├── paper_margin_010_quarter_counts.csv  # 实验各条件的季度计数数据
│       │   ├── policy_document_loo.csv  # 逐篇撤回政策后的候选资格
│       │   ├── potential_association_baseline.csv  # 跨来源潜在关联基准指标
│       │   ├── rank_intervals.csv  # 逐主题扰动排名范围
│       │   ├── scenario_memberships.csv  # 逐情景候选成员名单
│       │   ├── scenarios.csv  # 逐消融与门槛情景的候选和排序变化
│       │   ├── weight_draws.csv  # 随机权重扰动结果
│       │   └── weight_summary.csv  # 各类随机权重扰动的汇总统计
│       ├── MANIFEST.json  # 当前发布结果的 SHA-256 指纹
│       ├── POSTPROCESS_DELIVERY.json  # 三仓库交付及实验绑定记录
│       ├── REPORT.md  # 面向读者的结果报告
│       ├── SUMMARY.json  # 机器可读统计摘要
│       ├── core_components.csv  # 核心热点评分分量
│       ├── coverage.csv  # 按来源统计输入、已分类与未分类数量
│       ├── cross_source_signals.csv  # 论文、专利和政策共同窗口信号
│       ├── emerging_components.csv  # 新兴热点评分分量
│       ├── hotspot_metrics.csv  # 各主题热点得分、门槛和数值候选资格
│       ├── institution_citation_context.csv  # 机构广度与引用背景
│       ├── quarter_counts.csv  # 各主题季度论文数量
│       ├── topic_catalog.csv  # 主题编号、关键词与规模
│       └── transfer_source_summary.csv  # 专利政策匹配统计
├── docs/  # 方法、数据、复现与目录说明
│   ├── ALGORITHM.md  # 评分算法说明
│   ├── CORE_FILES.md  # 核心文件与外部大文件边界
│   ├── DATA_SCHEMA.md  # 数据字段约定
│   ├── FULL_EXPERIMENTS.md  # 实验设计和解释限制
│   ├── FULL_NMF.md  # 全量主题流程说明
│   ├── METHOD.md  # 当前算法与适用边界
│   ├── PROJECT_STRUCTURE.md  # 本文件：全部受版本管理文件的用途索引
│   └── REPRODUCING.md  # 环境、输入和复现步骤
├── pipelines/  # 计算与复现入口
│   ├── full_nmf/  # 当前全量主流程
│   │   ├── build.py  # 构建本阶段计算结果
│   │   ├── experiments.py  # 执行消融及灵敏度实验
│   │   └── report.py  # 生成人类可读结果报告
│   ├── hotspots/  # 多年份和潜在关联兼容回归实现
│   │   ├── common.py  # 公共路径、配置和辅助函数
│   │   ├── multiyear_build.py  # 兼容回归的多年季度计数与背景数据构建
│   │   ├── multiyear_delivery.py  # 兼容回归表格和交付产物生成
│   │   ├── multiyear_experiments.py  # 兼容回归的多年热点消融及敏感性计算
│   │   ├── multiyear_finalize.py  # 兼容回归结果整理和最终输出
│   │   ├── multiyear_plots.py  # 兼容回归的热点趋势和实验图表
│   │   ├── multiyear_scoring.py  # 兼容回归的多年热点评分
│   │   ├── multiyear_validate.py  # 兼容回归结果约束与完整性检查
│   │   ├── potential_delivery.py  # 兼容回归的潜在关联表格输出
│   │   ├── potential_experiments.py  # 兼容回归的潜在关联消融实验
│   │   ├── potential_unified.py  # 兼容回归的跨来源潜在关联计算
│   │   ├── potential_unified_metrics.py  # 兼容回归的跨来源指标与过滤条件
│   │   └── replay_snapshot.py  # 兼容快照回放编排
│   └── nmf500/  # 共享计算模块或固定回归流程；当前入口见 full_nmf
│       ├── build.py  # 构建本阶段计算结果
│       ├── experiments.py  # 执行消融及灵敏度实验
│       ├── review.py  # 候选主题范围及语义审核应用
│       ├── review_contract.py  # 审核决定的输入绑定和有效性约束
│       ├── review_decisions.json  # 固定回归审核决定；不得继承为当前主题审核结论
│       ├── review_decisions_v021.json  # 固定回归审核决定；不得继承为当前主题审核结论
│       └── validate.py  # 固定回归输出的数据约束检查
├── provenance/  # 文件指纹与审计元数据
│   ├── CORE_FILES.json  # 当前核心文件完整性清单
│   ├── DOCUMENTATION_VALIDATION.json  # 发布或回归审计记录：DOCUMENTATION / VALIDATION
│   ├── EXTRACTION.json  # 发布或回归审计记录：EXTRACTION
│   ├── FILE_MANIFEST.json  # 发布或回归审计记录：FILE / MANIFEST
│   ├── ISOLATED_RELEASE_VALIDATION.json  # 发布或回归审计记录：ISOLATED / RELEASE / VALIDATION
│   ├── RANKING_PORTABILITY.json  # 发布或回归审计记录：RANKING / PORTABILITY
│   └── REPLAY_VALIDATION.json  # 发布或回归审计记录：REPLAY / VALIDATION
├── src/  # 可导入的算法模块
│   └── energy_hotspots/  # 热点评分、命令行及离线回放包
│       ├── __init__.py  # Python 包初始化
│       ├── __main__.py  # 模块命令行入口
│       ├── cli.py  # 命令行参数与入口
│       ├── replay.py  # 固定输入的离线兼容回放
│       └── scoring.py  # 核心与新兴热点评分、门槛和确定性排序
├── tests/  # 自动化测试及固定输入
│   ├── fixtures/  # 仅用于兼容回归，不代表当前成果
│   │   ├── nmf500/  # 固定回归目录；不作为当前结果使用
│   │   │   ├── experiments/  # 固定回归目录；不作为当前结果使用
│   │   │   │   ├── PROTOCOL.json  # 固定回归输入/期望值；不作为当前结果使用：实验参数、范围、限制与输入指纹
│   │   │   │   ├── policy_family_loo.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   │   ├── rank_intervals.csv  # 固定回归输入/期望值；不作为当前结果使用：逐主题扰动排名范围
│   │   │   │   ├── scenario_memberships.csv  # 固定回归输入/期望值；不作为当前结果使用：逐情景候选成员名单
│   │   │   │   ├── scenarios.csv  # 固定回归输入/期望值；不作为当前结果使用：逐消融与门槛情景的候选和排序变化
│   │   │   │   ├── weight_draws.csv  # 固定回归输入/期望值；不作为当前结果使用：随机权重扰动结果
│   │   │   │   └── weight_summary.csv  # 固定回归输入/期望值；不作为当前结果使用：各类随机权重扰动的汇总统计
│   │   │   ├── 500主题核心新兴潜在热点.xlsx  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── 500主题热点审阅结果.xlsx  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── MANIFEST.json  # 固定回归输入/期望值；不作为当前结果使用：当前发布结果的 SHA-256 指纹
│   │   │   ├── METHOD.json  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── PAPER_INPUTS.json  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── REVIEW_SUMMARY.json  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── SUMMARY.json  # 固定回归输入/期望值；不作为当前结果使用：机器可读统计摘要
│   │   │   ├── VALIDATION.json  # 固定回归输入/期望值；不作为当前结果使用：数据完整性检查结果
│   │   │   ├── candidate_evidence.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── confidence_thresholds.json  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── core_candidates.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── core_components.csv  # 固定回归输入/期望值；不作为当前结果使用：核心热点评分分量
│   │   │   ├── core_followup.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── coverage_audit.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── emerging_candidates.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── emerging_components.csv  # 固定回归输入/期望值；不作为当前结果使用：新兴热点评分分量
│   │   │   ├── emerging_followup.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── hotspot_metrics.csv  # 固定回归输入/期望值；不作为当前结果使用：各主题热点得分、门槛和数值候选资格
│   │   │   ├── institution_citation_context.csv  # 固定回归输入/期望值；不作为当前结果使用：机构广度与引用背景
│   │   │   ├── policy_evidence_review.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── potential_candidates.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── potential_followup.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── potential_metrics.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── quarter_counts.csv  # 固定回归输入/期望值；不作为当前结果使用：各主题季度论文数量
│   │   │   ├── reviewed_hotspot_metrics.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── reviewed_potential_metrics.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── scope_review.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── sensitivity.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── topic_catalog.csv  # 固定回归输入/期望值；不作为当前结果使用：主题编号、关键词与规模
│   │   │   ├── transfer_recalibration_audit.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   ├── transfer_scores.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   │   └── uniform_inference_changes.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │   └── snapshot_20260925/  # 固定回归目录；不作为当前结果使用
│   │       └── hotspots/  # 固定回归目录；不作为当前结果使用
│   │           ├── data/  # 固定回归目录；不作为当前结果使用
│   │           │   ├── multiyear/  # 固定回归目录；不作为当前结果使用
│   │           │   │   ├── INPUT_METHOD.json  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── dedup_2026Q2_context.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── dedup_months.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── dedup_quarters.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── exclude_needs_review_2026Q2_context.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── exclude_needs_review_months.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── exclude_needs_review_quarters.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── geometry_2026Q2_context.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── geometry_months.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── geometry_quarters.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── main_2025Q2_context.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── main_2025Q4_context.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── main_2026Q1_context.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── main_2026Q2_context.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── main_months.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── main_quarters.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── quality_2026Q2_context.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── quality_months.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── quality_quarters.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── supported_only_2026Q2_context.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   ├── supported_only_months.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   │   └── supported_only_quarters.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── FINAL_METHOD.json  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── MULTIYEAR_METHOD.json  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── MULTIYEAR_REVIEW_DESIGN.json  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── MULTIYEAR_VALIDATION.json  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── MULTIYEAR_WORKBOOK_TABLES.json  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── POTENTIAL_UNIFIED_METHOD.json  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── POTENTIAL_UNIFIED_VALIDATION.json  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── VALIDATION.json  # 固定回归输入/期望值；不作为当前结果使用：数据完整性检查结果
│   │           │   ├── patent_metadata.parquet  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   └── potential_unified_global_dedup.parquet  # 固定回归输入/期望值；不作为当前结果使用
│   │           ├── evidence/  # 固定回归目录；不作为当前结果使用
│   │           │   └── potential_unified_candidates.parquet  # 固定回归输入/期望值；不作为当前结果使用
│   │           ├── figures/  # 固定回归目录；不作为当前结果使用
│   │           │   ├── multiyear_data_stress.pdf  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_data_stress.png  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_windows.pdf  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   └── multiyear_windows.png  # 固定回归输入/期望值；不作为当前结果使用
│   │           ├── reliability/  # 固定回归目录；不作为当前结果使用
│   │           │   ├── EXPERIMENT_METHOD.json  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── POTENTIAL_UNIFIED_EXPERIMENT_METHOD.json  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── data_sensitivity_topic_details.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── gate_and_data_sensitivity.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── policy_publisher_sensitivity.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── potential_score_components.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── potential_unified_sensitivity_details.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── potential_unified_sensitivity_summary.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── score_ablation_ranks.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── score_ablation_summary.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── weight_rank_stability.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   └── weight_trials.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           ├── results/  # 固定回归目录；不作为当前结果使用
│   │           │   ├── category_catalog.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── core_hotspots.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── emerging_hotspots.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── field_dictionary.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── hotspot_summary_all750.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── literature_metrics_all750.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_annual_trajectories.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_baseline_2y.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_baseline_4y.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_before_after.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_core_1y.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_core_5y.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_core_candidates.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_core_components.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_coverage_audit.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_cutoff_2025Q2.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_cutoff_2025Q4.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_cutoff_2026Q1.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_dedup.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_emerging_candidates.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_emerging_components.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_exclude_needs_review.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_geometry.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_metrics_all750.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_omit_baseline_1.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_omit_baseline_2.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_omit_baseline_3.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_quality.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_robustness_grades.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_semantic_review.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── multiyear_supported_only.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── paper_metadata_quality.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── potential_priority.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── potential_reading_guide.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── potential_unified_applicant_evidence.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── potential_unified_before_after.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── potential_unified_decision_counts.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── potential_unified_dedup_denominators.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── potential_unified_denominators.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── potential_unified_document_reviews.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── potential_unified_metrics.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── potential_unified_policy_reviews.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── potential_unified_record_ledger.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── potential_unified_scope.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── potential_unified_watch.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   ├── semantic_review_decisions.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   └── watch_and_downgraded.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           ├── review/  # 固定回归目录；不作为当前结果使用
│   │           │   ├── multiyear_displayed_samples.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │           │   └── multiyear_semantic_decisions.json  # 固定回归输入/期望值；不作为当前结果使用
│   │           ├── 750类核心新兴潜在热点分析.xlsx  # 固定回归输入/期望值；不作为当前结果使用
│   │           ├── 750类热点消融实验与灵敏度分析.xlsx  # 固定回归输入/期望值；不作为当前结果使用
│   │           └── METHOD.json  # 固定回归输入/期望值；不作为当前结果使用
│   ├── conftest.py  # 测试共享配置
│   ├── test_current_release.py  # 回归测试：current / release
│   ├── test_full_experiments.py  # 回归测试：full / experiments
│   ├── test_full_nmf.py  # 回归测试：full / nmf
│   ├── test_multiyear.py  # 回归测试：multiyear
│   ├── test_nmf500_diagnostics.py  # 回归测试：nmf500 / diagnostics
│   ├── test_ranking.py  # 回归测试：ranking
│   ├── test_readable_report.py  # 回归测试：readable / report
│   └── test_review_lineage.py  # 回归测试：review / lineage
├── tools/  # 发布校验、清单及维护工具
│   ├── build_release.py  # 源码发布包构建工具
│   ├── check_current_release.py  # 校验核心代码、成果指纹和文档链接
│   ├── check_release.py  # 检查发布文件、二进制白名单及数据约束
│   ├── project_structure.py  # 重建本结构图及逐文件用途
│   └── update_release_manifest.py  # 更新发布文件指纹
├── .gitattributes  # Git 文本与二进制属性
├── .gitignore  # 排除缓存、本地大数据和运行输出
├── MANIFEST.in  # 源码分发包含文件规则
├── NOTICE.md  # 数据来源和使用声明
├── README.md  # 项目入口：当前方法、结果及运行说明
├── pyproject.toml  # 包元数据、依赖与命令入口
├── requirements-nmf500.txt  # 运行/测试依赖版本约束（用途由文件后缀区分）
└── requirements-scoring.txt  # 运行/测试依赖版本约束（用途由文件后缀区分）
```

## 不随仓库发布的本地内容

`work/`、`outputs/` 或 `results/` 中的全量运行目录保存训练权重、向量、逐条分类、数据库和日志；原始文献及编码器权重也属于外部运行输入。这些文件体量大，不是本结构图漏列的源码，具体输入位置与生成步骤见复现说明。删除仓库中的旧发布快照不会删除这些运行数据。

## 维护本图

新增、移动或删除文件后运行 `python tools/project_structure.py`。只扫描 Git 可见文件，不扫描原始语料；发布前还应运行核心文件校验。每个文件名后为其作用；测试数据不可用于宣称当前模型效果。
