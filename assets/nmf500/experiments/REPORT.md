# NMF500 灵敏度与消融实验

{
  "seed": 20260926,
  "draws_per_family": 1500,
  "weight_multipliers": [
    0.8,
    1.2
  ],
  "top_k": 20,
  "diagnostic_scenarios": 96,
  "experiment_design": "post-hoc descriptive diagnostics; not preregistered or used to tune selection",
  "ranking": "10-decimal canonical ties; top20 ties broken by category ID; rank intervals use competition ranks, so top20_fraction can include ties beyond 20",
  "eligibility": "Weights affect ranking only. Frozen numeric gates and semantic decisions; newly passing topics remain unreviewed.",
  "uncertainty": "Perturbation intervals are scenario ranges, not statistical confidence intervals. No expert accuracy or causal claim.",
  "window_limit": "Citation cohort context fixed to 2023–2025; windows test count/institution horizons, not a full historical backtest.",
  "potential_limit": "No applicant-diversity data. Policy-family LOO is on the three reviewed leads only, not all 500 themes."
}

## 权重扰动

| family    |   ('spearman', 'min') |   ('spearman', 'median') |   ('spearman', 'max') |   ('top20_overlap', 'min') |   ('top20_overlap', 'median') |   ('top20_overlap', 'max') |   ('max_rank_shift', 'min') |   ('max_rank_shift', 'median') |   ('max_rank_shift', 'max') |
|:----------|----------------------:|-------------------------:|----------------------:|---------------------------:|------------------------------:|---------------------------:|----------------------------:|-------------------------------:|----------------------------:|
| core      |              0.996925 |                 0.999626 |              0.999986 |                       0.95 |                          1    |                          1 |                           3 |                             13 |                          36 |
| emerging  |              0.998431 |                 0.999759 |              0.999991 |                       0.9  |                          0.95 |                          1 |                           2 |                             13 |                          32 |
| potential |              0.864425 |                 0.98503  |              0.99996  |                       0.9  |                          1    |                          1 |                          10 |                             73 |                         210 |

## 逐项评分消融

| family    | kind                     | scenario                      |   spearman |   top20_overlap |   max_rank_shift |   numeric_candidates |   baseline_retained |   candidate_jaccard |   frozen_review_followups_retained |   new_numeric_candidates_pending_review |
|:----------|:-------------------------|:------------------------------|-----------:|----------------:|-----------------:|---------------------:|--------------------:|--------------------:|-----------------------------------:|----------------------------------------:|
| core      | score_component_ablation | without_volume                |   0.973084 |            0.9  |              117 |                   21 |                  21 |                   1 |                                  6 |                                       0 |
| core      | score_component_ablation | without_citation              |   0.974503 |            0.65 |               72 |                   21 |                  21 |                   1 |                                  6 |                                       0 |
| core      | score_component_ablation | without_institutions          |   0.998761 |            0.95 |               23 |                   21 |                  21 |                   1 |                                  6 |                                       0 |
| core      | score_component_ablation | without_persistence           |   0.996611 |            0.9  |               39 |                   21 |                  21 |                   1 |                                  6 |                                       0 |
| core      | score_component_ablation | without_current               |   0.997463 |            0.95 |               33 |                   21 |                  21 |                   1 |                                  6 |                                       0 |
| emerging  | score_component_ablation | without_multiyear_growth      |   0.989492 |            0.8  |               93 |                   29 |                  29 |                   1 |                                  2 |                                       0 |
| emerging  | score_component_ablation | without_recent_growth         |   0.988685 |            0.8  |               90 |                   29 |                  29 |                   1 |                                  2 |                                       0 |
| emerging  | score_component_ablation | without_trend                 |   0.992182 |            0.85 |               66 |                   29 |                  29 |                   1 |                                  2 |                                       0 |
| emerging  | score_component_ablation | without_quarter_consistency   |   0.996854 |            0.95 |               37 |                   29 |                  29 |                   1 |                                  2 |                                       0 |
| emerging  | score_component_ablation | without_institution_expansion |   0.998346 |            0.85 |               35 |                   29 |                  29 |                   1 |                                  2 |                                       0 |
| potential | score_component_ablation | without_patents               |   0.996069 |            0.9  |               65 |                    5 |                   5 |                   1 |                                  3 |                                       0 |
| potential | score_component_ablation | without_policies              |   0.996145 |            0.95 |              154 |                    5 |                   5 |                   1 |                                  3 |                                       0 |
| potential | score_component_ablation | without_relative_share        |   0.748696 |            0.8  |              272 |                    5 |                   5 |                   1 |                                  3 |                                       0 |
| potential | score_component_ablation | without_papers                |   0.802711 |            0.45 |              235 |                    5 |                   5 |                   1 |                                  3 |                                       0 |

## 时间窗口与旧门槛

| family   | kind             | scenario                           |   spearman |   top20_overlap |   max_rank_shift |   numeric_candidates |   baseline_retained |   candidate_jaccard |   frozen_review_followups_retained |   new_numeric_candidates_pending_review |
|:---------|:-----------------|:-----------------------------------|-----------:|----------------:|-----------------:|---------------------:|--------------------:|--------------------:|-----------------------------------:|----------------------------------------:|
| core     | threshold_legacy | original_750_count_rules_on_sample |   0.996255 |            0.85 |               48 |                    0 |                   0 |            0        |                                  0 |                                       0 |
| emerging | threshold_legacy | original_750_count_rules_on_sample |   1        |            1    |                0 |                    0 |                   0 |            0        |                                  0 |                                       0 |
| core     | window           | core_1y                            |   0.913697 |            0.95 |              225 |                   32 |                  21 |            0.65625  |                                  6 |                                      11 |
| core     | window           | core_5y                            |   0.976565 |            0.95 |              104 |                   10 |                  10 |            0.47619  |                                  3 |                                       0 |
| emerging | window           | baseline_2y_omit_None              |   0.987348 |            0.8  |               95 |                   22 |                  22 |            0.758621 |                                  2 |                                       0 |
| emerging | window           | baseline_4y_omit_None              |   0.993851 |            0.9  |               89 |                   28 |                  26 |            0.83871  |                                  1 |                                       2 |
| emerging | window           | baseline_3y_omit_1                 |   0.98576  |            0.75 |              112 |                   21 |                  20 |            0.666667 |                                  1 |                                       1 |
| emerging | window           | baseline_3y_omit_2                 |   0.994348 |            0.8  |              106 |                   25 |                  24 |            0.8      |                                  1 |                                       1 |
| emerging | window           | baseline_3y_omit_3                 |   0.987348 |            0.8  |               95 |                   22 |                  22 |            0.758621 |                                  2 |                                       0 |

## 政策组留一法

| category_id   | removed_family                     |   remaining_policy_families | retains_two_policy_families   |
|:--------------|:-----------------------------------|----------------------------:|:------------------------------|
| N0061         | STORAGE_ENGINEERING_QUALITY        |                           1 | False                         |
| N0061         | STORAGE_SCALEUP                    |                           1 | False                         |
| N0189         | GRID_CONNECTED_CYBER_SECURITY      |                           1 | False                         |
| N0189         | INDUSTRIAL_INTERNET_POWER_SECURITY |                           1 | False                         |
| N0191         | EV_CHARGING_EXPANSION              |                           1 | False                         |
| N0191         | VEHICLE_GRID_INTERACTION           |                           1 | False                         |

完整门槛/来源/置信过滤实验见 scenarios.csv；逐主题名单见 scenario_memberships.csv。移除语义审阅显示数值候选池大小，不代表这些候选真实有效。五种数据过滤实验另见输入目录 sensitivity.csv。
