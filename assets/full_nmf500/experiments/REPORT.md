# 全量主题消融与灵敏度实验

{
  "full_population_records": 5119004,
  "classification_summary_sha256": "67d7d140720a99a87ae46fcf171e34515c1629ae4a402aa116dc30b1e4683568",
  "topics": 500,
  "seed": 20260926,
  "draws_per_family": 1500,
  "families": [
    "core",
    "emerging",
    "potential_association"
  ],
  "scenarios": 113,
  "full_count_thresholds": true,
  "baseline_replay_passed": true,
  "sample_rows_or_quotas_used": false,
  "data_filters_recompute_institutions_citations_and_denominators": true,
  "semantic_approvals_inherited": false,
  "potential_association_gates": {
    "papers": 100,
    "patents": 25,
    "policies": 2,
    "relative": 1.25
  },
  "potential_gates_calibrated": false,
  "limits": [
    "Descriptive fixed-model sensitivity; not refitting NMF or an independent temporal validation.",
    "Intervals are perturbation ranges, not statistical confidence intervals. No semantic accuracy measured.",
    "Potential associations are exploratory numeric leads, not verified same-task policy support or applicant diversity.",
    "No independent policy-family annotations for the new taxonomy; document LOO is not family LOO.",
    "Time-window tests hold the 2023-2025 citation cohort fixed; data-filter tests recompute that cohort.",
    "TRL/CRL evidence remains bounded to reviewed objects; full classification does not create maturity evidence."
  ],
  "input_sha256": {
    "core_components.csv": "36a65ae1b0562ca4269faf50f865a548503f6fc958795debdce1dba15d87846b",
    "cross_source_signals.csv": "381554445aad30a6f530155729716051dbf1588d73cc233d595e56c7c669109e",
    "quarter_counts.csv": "05ba1cd9fd5c52d0957485c742b927533a4c089efc8dea5bcfe6ac9701dc9fd2",
    "transfer_source_summary.csv": "14e31af7f1b802fb97a1a1d5b0896c8dd6f7e2f77a1675f372221fd0b85d6eb3",
    "coverage.csv": "232ad8e55e2fbf329455490291c629a8521fdd6110d1cf18e1f27194be519166",
    "institution_citation_context.csv": "a45f21aebbc6ddf41b4c4d3638a682339ee708839bcd5dfcf13dbfdac97b8b53",
    "topic_catalog.csv": "9e863bf16277d30ea67f06bfe792eb08fe5477d9581a62f7981889f1b9d97029",
    "emerging_components.csv": "7dafafe2e5d522eb5e8cc36165e54ff7a404b5d538ef42fc02a5ac9e932d2d5d",
    "hotspot_metrics.csv": "32ba11475142a7a0c48ecd41352d6627edbc6b5ceeebf83d0f344498e77fdce7"
  }
}

本次重新读取全部分类记录，使用全量数量门槛；主题范围和语义需独立审核。核心／新兴分析包括评分、门槛、权重、时间窗口和文本质量／贡献差距过滤。跨来源关联包括来源消融、余弦／间隔网格、共同日期窗口和政策文档留一。潜在关联仅为待核验线索，政策族独立性与申请人多样性未取得证据，不能声称已完成这两项检验。
