# 500主题样本版热点重算

截止2026-06-30；输入142,000篇论文，清理后141,895篇；专利/政策共23,783条。新分类覆盖当前冻结样本。全部时间段统一使用固定NMF组件推断，增长按各期样本背景份额归一化。

核心数值候选8个，三种数据过滤均通过0个；新兴数值候选29个，方向稳健29个；潜在跨来源数值候选5个。候选均保留主题范围与证据待审阅状态。

## 核心候选

| category_id   | name                                                                       |   core_score |   recent_papers |   multiyear_share_ratio | core_robust_candidate   |
|:--------------|:---------------------------------------------------------------------------|-------------:|----------------:|------------------------:|:------------------------|
| N0315         | Biochar / Pulp and paper industry / Charcoal                               |        98.4  |              87 |                1.2111   | False                   |
| N0172         | Thermal energy storage / Phase-change material / Latent heat               |        95.3  |              67 |                0.885303 | False                   |
| N0166         | Thermal / Process engineering / Mechanical engineering                     |        90.76 |             117 |                1.78539  | False                   |
| N0070         | Artificial neural network / Artificial intelligence / Machine learning     |        89.49 |              85 |                1.38388  | False                   |
| N0474         | Reinforcement learning / Convergence (economics) / Artificial intelligence |        88.34 |              93 |                1.63384  | False                   |
| N0493         | Sustainable development / Economic growth / Sustainable energy             |        87.18 |              91 |                1.8731   | False                   |
| N0269         | Sustainability / Ecology / Environmental resource management               |        86.89 |              86 |                1.84576  | False                   |
| N0038         | Energy (signal processing) / Statistics / Mathematics                      |        80.92 |              94 |                1.37198  | False                   |

## 新兴候选

| category_id   | name                                                                           |   emerging_score |   recent_papers |   multiyear_share_ratio | emerging_robust_candidate   |
|:--------------|:-------------------------------------------------------------------------------|-----------------:|----------------:|------------------------:|:----------------------------|
| N0343         | Software deployment / Carbon capture and storage (timeline) / Scalability      |            99.76 |             114 |                 4.62569 | True                        |
| N0332         | Key (lock) / Process management / Sustainable energy                           |            99.47 |             125 |                 5.9441  | True                        |
| N0193         | Robustness (evolution) / Control engineering / Robust control                  |            99.47 |             142 |                 3.70051 | True                        |
| N0458         | Computation / Computational science / Finite element method                    |            99.15 |              29 |                 2.74839 | True                        |
| N0388         | Electronic structure / Valence (chemistry) / Electronic band structure         |            98.81 |              33 |                 2.60694 | True                        |
| N0337         | Efficient energy use / Energy conservation / Energy accounting                 |            97.13 |              54 |                 2.21799 | True                        |
| N0395         | Turbulence / Turbulence kinetic energy / Reynolds number                       |            96.57 |              35 |                 2.47274 | True                        |
| N0358         | Raw material / Biorefinery / Metallurgy                                        |            96.57 |              28 |                 2.45348 | True                        |
| N0339         | Modular design / Scalability / High-voltage direct current                     |            96.38 |              46 |                 2.21692 | True                        |
| N0254         | Flexibility (engineering) / Environmental economics / Prosumer                 |            94.03 |              61 |                 2.07297 | True                        |
| N0381         | Sensitivity (control systems) / Electronic engineering / Parametric statistics |            93.83 |              44 |                 1.78441 | True                        |
| N0446         | Noise (video) / Noise reduction / Phase noise                                  |            93.41 |              58 |                 2.30007 | True                        |
| N0409         | HVAC / Air conditioning / Ventilation (architecture)                           |            92.88 |              29 |                 2.07353 | True                        |
| N0160         | Faraday efficiency / Reversible hydrogen electrode / Dendrite (mathematics)    |            92.86 |              77 |                 1.66998 | True                        |
| N0087         | Process (computing) / Process engineering / Engineering                        |            92.75 |              34 |                 2.08101 | True                        |

## 潜在候选

| category_id   | name                                                                  |   confidence_filtered_recent_patents |   confidence_filtered_policy_documents |   confidence_filtered_patent_paper_share_ratio |
|:--------------|:----------------------------------------------------------------------|-------------------------------------:|---------------------------------------:|-----------------------------------------------:|
| N0191         | Electric vehicle / Charging station / Driving range                   |                                   31 |                                      8 |                                        3.4779  |
| N0061         | Energy storage / Electrochemical energy storage / Process engineering |                                   25 |                                      4 |                                        4.6667  |
| N0412         | Electric power / Electric power industry / Electric energy            |                                   17 |                                      3 |                                        5.19539 |
| N0189         | Computer security / Cyber-physical system / Internet of Things        |                                    8 |                                      2 |                                        1.99222 |
| N0029         | Power (physics) / Electric power system / Power flow                  |                                    5 |                                      3 |                                        2.37025 |

跨来源余弦关联仅用于线索筛选。政策是否支持同一具体任务、专利申请主体多样性仍需核读；当前不声称已满足原750版应用任务级潜在热点证据门槛。

## 敏感性

| scenario           |   papers |   core_candidates |   emerging_candidates |   core_rank_spearman |   emerging_rank_spearman |
|:-------------------|---------:|------------------:|----------------------:|---------------------:|-------------------------:|
| abstract_available |    86941 |                 0 |                    14 |             0.930791 |                 0.918446 |
| title_year_dedup   |   141666 |                 8 |                    29 |             0.999933 |                 0.998764 |
| exclude_jan1       |   123213 |                 4 |                    28 |             0.995599 |                 0.980193 |

抽样论文每年规模为8,000或12,000，因此采用样本支持门槛，详见METHOD.json；计数没有外推为全量规模。模型训练与回放之间标签生成方式的差异已修正，变动见uniform_inference_changes.csv。历史比较属回溯描述；当前引用快照不是历史时点已知引用。

## 样本范围核读后的跟踪方向
核读代表文献后，通用词或任务混杂的数值候选暂缓认定；所有保留方向仍为AI辅助初审，未经过独立专家认定。

### 核心条件性跟踪

| category_id   | review_display_name   |   core_score |   recent_papers |   multiyear_share_ratio |
|:--------------|:----------------------|-------------:|----------------:|------------------------:|
| N0172         | 相变材料与热能储存             |        95.3  |              67 |                0.885303 |
| N0474         | 强化学习用于微电网与能源调度        |        88.34 |              93 |                1.63384  |

### 新兴跟踪

| category_id   | review_display_name   |   emerging_score |   recent_papers |   multiyear_share_ratio |
|:--------------|:----------------------|-----------------:|----------------:|------------------------:|
| N0388         | 能源材料电子结构              |            98.81 |              33 |                 2.60694 |
| N0337         | 能源效率与节能系统             |            97.13 |              54 |                 2.21799 |
| N0395         | 湍流与聚变等离子体输运           |            96.57 |              35 |                 2.47274 |
| N0254         | 能源系统柔性与需求响应           |            94.03 |              61 |                 2.07297 |
| N0409         | 建筑暖通与热储能控制            |            92.88 |              29 |                 2.07353 |
| N0470         | 能源与材料生命周期评价           |            88.2  |              51 |                 1.70759 |
| N0155         | 电力设备与光伏故障诊断           |            87.85 |              40 |                 1.85307 |
| N0195         | 海上风电布局与运行             |            80.35 |              69 |                 1.55004 |

### 潜在应用线索

| category_id   | review_display_name   |   potential_signal_score |   reviewed_policy_family_count |
|:--------------|:----------------------|-------------------------:|-------------------------------:|
| N0191         | 电动车充电与车网互动            |                    96.25 |                              2 |
| N0061         | 新型储能系统与控制             |                    94.28 |                              2 |
| N0189         | 电力网络安全与工业互联网防护        |                    86.39 |                              2 |

核心2个方向在摘要/日期过滤下未全部达标，因此只列条件性跟踪，不能宣称稳健核心热点。8个新兴方向的“新兴”仅指样本关注份额上升，不表示技术首次出现。3个潜在方向已核读相关政策任务片段并合并同计划政策，仍缺统一专利申请主体及全量同任务审阅，因此是应用线索，不是通过原任务级全部门槛的潜在热点。

政策审阅排除了正文落款2006年的《电网运行规则》作为近期政策支持，并合并发改能源〔2024〕1803号的重复转载。完整引文、URL、哈希及政策组见policy_evidence_review.csv。
