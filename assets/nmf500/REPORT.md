# 500主题样本版热点重算

截止2026-06-30；输入142,000篇论文，清理后141,894篇；专利/政策共23,783条。新分类覆盖当前冻结样本。全部时间段统一使用固定NMF组件推断，增长按各期样本背景份额归一化。

核心数值候选21个，五种数据过滤均通过1个；新兴数值候选29个，五种完整门槛均通过7个；潜在跨来源数值候选5个。候选均保留主题范围与证据待审阅状态。

## 核心候选

| category_id   | name                                                                   |   core_score |   recent_papers |   multiyear_share_ratio | core_robust_candidate   |
|:--------------|:-----------------------------------------------------------------------|-------------:|----------------:|------------------------:|:------------------------|
| N0007         | Supercapacitor / Capacitance / Electrode                               |        98.71 |             118 |                0.846407 | False                   |
| N0041         | Heterojunction / Optoelectronics / Chemical engineering                |        97.96 |              81 |                0.99629  | False                   |
| N0315         | Biochar / Pulp and paper industry / Charcoal                           |        97.63 |              84 |                1.21485  | False                   |
| N0013         | Overpotential / Oxygen evolution / Catalysis                           |        97.04 |              79 |                0.903249 | False                   |
| N0021         | Perovskite (structure) / Halide / Energy conversion efficiency         |        96.54 |             130 |                1.00019  | True                    |
| N0025         | Hydrogen / Hydrogen production / Hydrogen storage                      |        96.18 |              73 |                1.11274  | False                   |
| N0033         | Membrane / Permeation / Ion exchange                                   |        94.72 |              67 |                0.992135 | False                   |
| N0172         | Thermal energy storage / Phase-change material / Latent heat           |        94.1  |              68 |                0.918395 | False                   |
| N0019         | Thermoelectric effect / Thermoelectric materials / Seebeck coefficient |        93.7  |              77 |                0.912388 | False                   |
| N0032         | Cathode / Electrolyte / Chemical engineering                           |        93.46 |              79 |                1.327    | False                   |
| N0034         | Battery (electricity) / Lithium-ion battery / Battery pack             |        92.12 |              92 |                1.22513  | False                   |
| N0031         | Anode / Electrode / Chemical engineering                               |        90.62 |              65 |                0.911151 | False                   |
| N0126         | Reduction (mathematics) / Mathematics / Oxygen reduction reaction      |        89.57 |              68 |                1.2651   | False                   |
| N0070         | Artificial neural network / Artificial intelligence / Machine learning |        89.29 |              95 |                1.21742  | False                   |
| N0269         | Sustainability / Ecology / Environmental resource management           |        87.43 |             109 |                1.9727   | False                   |

## 新兴候选

| category_id   | name                                                                           |   emerging_score |   recent_papers |   multiyear_share_ratio | emerging_robust_candidate   |
|:--------------|:-------------------------------------------------------------------------------|-----------------:|----------------:|------------------------:|:----------------------------|
| N0343         | Software deployment / Carbon capture and storage (timeline) / Scalability      |            99.75 |              98 |                 4.4947  | True                        |
| N0332         | Key (lock) / Process management / Sustainable energy                           |            99.59 |             114 |                 5.33932 | True                        |
| N0127         | Work (physics) / Mechanical engineering / Thermodynamics                       |            99.55 |              66 |                 4.30771 | False                       |
| N0193         | Robustness (evolution) / Control engineering / Robust control                  |            99.37 |             171 |                 3.43599 | True                        |
| N0358         | Raw material / Biorefinery / Metallurgy                                        |            97.21 |              33 |                 2.60903 | False                       |
| N0337         | Efficient energy use / Energy conservation / Energy accounting                 |            96.71 |              38 |                 2.16403 | False                       |
| N0339         | Modular design / Scalability / High-voltage direct current                     |            96.41 |              45 |                 2.16943 | True                        |
| N0395         | Turbulence / Turbulence kinetic energy / Reynolds number                       |            96.11 |              30 |                 2.3954  | False                       |
| N0197         | Nonlinear system / Finite element method / Structural engineering              |            95.61 |              37 |                 2.16246 | False                       |
| N0369         | Government (linguistics) / Public economics / Economic growth                  |            94.39 |              39 |                 2.40945 | False                       |
| N0293         | Transmission (telecommunications) / Transmission system / Power transmission   |            93.92 |              25 |                 2.11131 | False                       |
| N0381         | Sensitivity (control systems) / Electronic engineering / Parametric statistics |            93.73 |              38 |                 1.87707 | False                       |
| N0303         | Irradiance / Remote sensing / Solar irradiance                                 |            92.15 |              32 |                 1.87313 | False                       |
| N0408         | Monte Carlo method / Statistical physics / Computational physics               |            91.95 |              26 |                 2.65496 | False                       |
| N0138         | Context (archaeology) / Environmental economics / Energy transition            |            91.87 |              64 |                 2.04169 | True                        |

## 潜在候选

| category_id   | name                                                                  |   confidence_filtered_recent_patents |   confidence_filtered_policy_documents |   confidence_filtered_patent_paper_share_ratio |
|:--------------|:----------------------------------------------------------------------|-------------------------------------:|---------------------------------------:|-----------------------------------------------:|
| N0191         | Electric vehicle / Charging station / Driving range                   |                                   30 |                                      9 |                                        3.45777 |
| N0061         | Energy storage / Electrochemical energy storage / Process engineering |                                   30 |                                      7 |                                        4.65011 |
| N0412         | Electric power / Electric power industry / Electric energy            |                                   21 |                                      3 |                                        8.14804 |
| N0189         | Computer security / Cyber-physical system / Internet of Things        |                                    8 |                                      2 |                                        1.91095 |
| N0456         | Demand response / Peak demand / Load management                       |                                    8 |                                      3 |                                        2.50547 |

跨来源余弦关联仅用于线索筛选。政策是否支持同一具体任务、专利申请主体多样性仍需核读；当前不声称已满足原750版应用任务级潜在热点证据门槛。

## 敏感性

| scenario            |   papers |   core_candidates |   emerging_candidates |   core_rank_spearman |   emerging_rank_spearman |
|:--------------------|---------:|------------------:|----------------------:|---------------------:|-------------------------:|
| abstract_available  |    86940 |                 2 |                    13 |             0.948367 |                 0.920833 |
| title_year_dedup    |   141665 |                20 |                    29 |             0.999919 |                 0.999023 |
| exclude_jan1        |   123213 |                12 |                    20 |             0.996618 |                 0.980251 |
| assignment_margin   |    77955 |                 2 |                     9 |             0.934642 |                 0.896645 |
| equal_quarter_quota |   131943 |                 4 |                    18 |             0.98834  |                 0.929187 |

抽样论文每年规模为8,000或12,000，因此采用样本支持门槛，详见METHOD.json；计数没有外推为全量规模。模型训练与回放之间标签生成方式的差异已修正，变动见uniform_inference_changes.csv。历史比较属回溯描述；当前引用快照不是历史时点已知引用。

## 样本范围核读后的跟踪方向
核读代表文献后，通用词或任务混杂的数值候选暂缓认定；所有保留方向仍为AI辅助初审，未经过独立专家认定。

### 核心条件性跟踪

| category_id   | review_display_name   |   core_score |   recent_papers |   multiyear_share_ratio |
|:--------------|:----------------------|-------------:|----------------:|------------------------:|
| N0013         | 电解水析氧与析氢催化            |        97.04 |              79 |                0.903249 |
| N0172         | 相变储热材料与系统             |        94.1  |              68 |                0.918395 |
| N0019         | 热电材料与器件               |        93.7  |              77 |                0.912388 |
| N0032         | 电池正极材料与循环性能           |        93.46 |              79 |                1.327    |
| N0031         | 电池负极与界面稳定性            |        90.62 |              65 |                0.911151 |
| N0077         | 微电网控制与通信安全            |        85.39 |              62 |                0.838408 |

### 新兴跟踪

| category_id   | review_display_name   |   emerging_score |   recent_papers |   multiyear_share_ratio |
|:--------------|:----------------------|-----------------:|----------------:|------------------------:|
| N0155         | 能源设备故障诊断              |            87.04 |              54 |                 1.64962 |
| N0016         | 风能资源评估与功率预测           |            86.12 |              72 |                 1.61314 |

### 潜在应用线索

| category_id   | review_display_name   |   potential_signal_score |   reviewed_policy_family_count |
|:--------------|:----------------------|-------------------------:|-------------------------------:|
| N0191         | 电动车主题中的充电与车网互动线索      |                    96.17 |                              2 |
| N0061         | 储能主题中的系统与控制应用线索       |                    95.59 |                              2 |
| N0189         | 网络安全主题中的电力应用线索        |                    86.49 |                              2 |

本次保留核心条件跟踪6个、新兴条件跟踪2个、潜在应用线索3个。稳健标记要求通过全部五种过滤下的完整数值门槛；条件跟踪不等于稳健热点。新兴只表示样本份额增长；潜在线索仍缺申请主体多样性及全量同任务验证。

政策按实际发布日期和政策组核查，旧文重发不能作为新增支持；完整引文、URL和哈希见policy_evidence_review.csv。
