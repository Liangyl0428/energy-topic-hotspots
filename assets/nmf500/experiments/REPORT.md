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
| core      |              0.996698 |                 0.999576 |              0.999981 |                       0.85 |                             1 |                          1 |                           4 |                             15 |                          31 |
| emerging  |              0.998356 |                 0.999759 |              0.999991 |                       0.95 |                             1 |                          1 |                           2 |                             14 |                          32 |
| potential |              0.840146 |                 0.983412 |              0.999915 |                       0.9  |                             1 |                          1 |                          14 |                             82 |                         227 |

## 逐项评分消融

| family    | kind                     | scenario                      |   spearman |   top20_overlap |   max_rank_shift |   numeric_candidates |   baseline_retained |   candidate_jaccard |   frozen_review_followups_retained |   new_numeric_candidates_pending_review |
|:----------|:-------------------------|:------------------------------|-----------:|----------------:|-----------------:|---------------------:|--------------------:|--------------------:|-----------------------------------:|----------------------------------------:|
| core      | score_component_ablation | without_volume                |   0.969833 |            0.8  |              122 |                    8 |                   8 |                   1 |                                  2 |                                       0 |
| core      | score_component_ablation | without_citation              |   0.973532 |            0.65 |               68 |                    8 |                   8 |                   1 |                                  2 |                                       0 |
| core      | score_component_ablation | without_institutions          |   0.998602 |            0.95 |               29 |                    8 |                   8 |                   1 |                                  2 |                                       0 |
| core      | score_component_ablation | without_persistence           |   0.996044 |            0.8  |               41 |                    8 |                   8 |                   1 |                                  2 |                                       0 |
| core      | score_component_ablation | without_current               |   0.99724  |            0.95 |               39 |                    8 |                   8 |                   1 |                                  2 |                                       0 |
| emerging  | score_component_ablation | without_multiyear_growth      |   0.988922 |            0.8  |               83 |                   29 |                  29 |                   1 |                                  8 |                                       0 |
| emerging  | score_component_ablation | without_recent_growth         |   0.988037 |            0.75 |              100 |                   29 |                  29 |                   1 |                                  8 |                                       0 |
| emerging  | score_component_ablation | without_trend                 |   0.99179  |            0.9  |               73 |                   29 |                  29 |                   1 |                                  8 |                                       0 |
| emerging  | score_component_ablation | without_quarter_consistency   |   0.997014 |            0.85 |               35 |                   29 |                  29 |                   1 |                                  8 |                                       0 |
| emerging  | score_component_ablation | without_institution_expansion |   0.998194 |            0.95 |               33 |                   29 |                  29 |                   1 |                                  8 |                                       0 |
| potential | score_component_ablation | without_patents               |   0.995449 |            0.85 |               69 |                    5 |                   5 |                   1 |                                  3 |                                       0 |
| potential | score_component_ablation | without_policies              |   0.993521 |            0.95 |              210 |                    5 |                   5 |                   1 |                                  3 |                                       0 |
| potential | score_component_ablation | without_relative_share        |   0.784553 |            0.75 |              276 |                    5 |                   5 |                   1 |                                  3 |                                       0 |
| potential | score_component_ablation | without_papers                |   0.772493 |            0.5  |              240 |                    5 |                   5 |                   1 |                                  3 |                                       0 |

## 时间窗口与旧门槛

| family   | kind             | scenario                           |   spearman |   top20_overlap |   max_rank_shift |   numeric_candidates |   baseline_retained |   candidate_jaccard |   frozen_review_followups_retained |   new_numeric_candidates_pending_review |
|:---------|:-----------------|:-----------------------------------|-----------:|----------------:|-----------------:|---------------------:|--------------------:|--------------------:|-----------------------------------:|----------------------------------------:|
| core     | threshold_legacy | original_750_count_rules_on_sample |   0.995818 |            0.85 |               50 |                    0 |                   0 |           0         |                                  0 |                                       0 |
| emerging | threshold_legacy | original_750_count_rules_on_sample |   1        |            1    |                0 |                    1 |                   1 |           0.0344828 |                                  0 |                                       0 |
| core     | window           | core_1y                            |   0.904462 |            0.75 |              203 |                   25 |                   8 |           0.32      |                                  2 |                                      17 |
| core     | window           | core_5y                            |   0.97256  |            0.85 |              120 |                    1 |                   1 |           0.125     |                                  0 |                                       0 |
| emerging | window           | baseline_2y_omit_None              |   0.986516 |            0.85 |              102 |                   29 |                  25 |           0.757576  |                                  7 |                                       4 |
| emerging | window           | baseline_4y_omit_None              |   0.993916 |            0.85 |               76 |                   26 |                  26 |           0.896552  |                                  7 |                                       0 |
| emerging | window           | baseline_3y_omit_1                 |   0.984739 |            0.85 |              107 |                   24 |                  24 |           0.827586  |                                  7 |                                       0 |
| emerging | window           | baseline_3y_omit_2                 |   0.994086 |            0.9  |               69 |                   28 |                  24 |           0.727273  |                                  6 |                                       4 |
| emerging | window           | baseline_3y_omit_3                 |   0.986516 |            0.85 |              102 |                   29 |                  25 |           0.757576  |                                  7 |                                       4 |

## 政策组留一法

| category_id   | removed_family                     |   remaining_policy_families | retains_two_policy_families   |
|:--------------|:-----------------------------------|----------------------------:|:------------------------------|
| N0061         | STORAGE_ENGINEERING_QUALITY        |                           1 | False                         |
| N0061         | STORAGE_SCALEUP                    |                           1 | False                         |
| N0189         | GRID_CONNECTED_CYBER_SECURITY      |                           1 | False                         |
| N0189         | INDUSTRIAL_INTERNET_POWER_SECURITY |                           1 | False                         |
| N0191         | EV_CHARGING_EXPANSION              |                           1 | False                         |
| N0191         | VEHICLE_GRID_INTERACTION           |                           1 | False                         |

完整门槛/来源/置信过滤实验见 scenarios.csv；逐主题名单见 scenario_memberships.csv。移除语义审阅显示数值候选池大小，不代表这些候选真实有效。原有三种数据过滤实验另见输入目录 sensitivity.csv。
