# 技术词条级热点识别方法

本文档与代码一一对应。凡出现数值处，均可由 `config/*.json` + `outputs/terms/*.csv` 复算
（专利/政策语料条数除外，它们来自外部语料统计）；文档与代码不一致视为 bug。

```
config/technology_terms/   词典（1,811 词条 / 33 子方向）
config/energy_anchors.json 能量锚点（只用于算 lift 诊断列，默认不参与判定）
config/hotspot_rules.json  判定门槛（全部可覆盖）
config/manual_review.json  人工复核清单（只影响研究报告，不影响算法产物）
src/energy_hotspots/term_hotspots/xmatcher.py       匹配器
src/energy_hotspots/term_hotspots/extract_counts.py 三类语料计数
src/energy_hotspots/term_hotspots/hotspot_rules.py  指标与判定
src/energy_hotspots/term_hotspots/cli.py            find / report / rebuild
```

## 1. 窗口（冻结）

| 名称 | 区间 | 季度数 |
|---|---|---|
| history | 2021-07-01 .. 2026-06-30 | 20 |
| core（近三年） | 2023-07-01 .. 2026-06-30 | 12 |
| recent（近一年） | 2025-07-01 .. 2026-06-30 | 4 |
| prev（上一年） | 2024-07-01 .. 2025-06-30 | 4 |
| baseline（core 之前两年） | 2021-07-01 .. 2023-06-30 | 8 |

## 2. 计数规则

| 规则 | 做法 | 依据（实测） |
|---|---|---|
| 计数单位 | 每篇文档对每个词条至多计 1 次 | 一个词条平均 2.45 个变体（最多 6 个），按模式累加时同一篇论文被重复计入：总体虚高 7.2%，析氧反应 +119%、氧还原 +114%、析氢 +79% |
| 父子词条 | 最长匹配抑制 | 词典中 240 个中文名是其它词条的子串（石墨 ⊂ 石墨烯 / 石墨相氮化碳），不做抑制会父子重复计数 |
| 英文写法 | 分隔符归一（`-`/`_`/`/`→空格、折叠空白）+ 复数变体 | 语料 99% 以上不是中文（2026Q2：en 71,562 / zh 746），召回依赖英文写法；不归一时 `Lithium-ion battery` 命中不了 `lithium ion battery` |
| 短缩略语 | 全大写、无空格、2–6 字符走大小写敏感自动机 | 别名 `CO` 全小写匹配会把 `Co`（钴）、`co-doped` 全部计入，实测虚增 46,457 篇（占该词条计数的 58%） |
| 季度口径 | year-only 占位（1 月 1 日）按该年实际出现季度均摊 | 2024-01-01 单日 49,779 篇（正常单日约 900）；占位率 2022 年 10.4% → 2026 年 25.0%；修复后 Q1/其它季度从 3.2 倍降到 0.84–0.97 |
| 专利去重 | 按公开号全局去重 | 同一专利同时出现在聚合表与 IPC 分表 |

| 语料 | 匹配文本 | 时间口径 |
|---|---|---|
| 论文 | `clean_title + clean_abstract`（`is_retracted = 0`） | 由 `publication_date` 现算季度（不用 `works.quarter`，实测 1.7 万行与 `publication_date` 不一致） |
| 专利 | `title + abstract` | `publication_date` 年份 2021–2025 |
| 政策 | `title + text` 全文 | `publication_date`，缺则 `issue_date` |

## 3. 指标

- `hits_3y / hits_recent / hits_prev / hits_base`：窗口内命中篇数（含均摊权重）。
- `df_recent / df_prev / df_3y`：对应窗口的文档频率＝命中篇数 ÷ 同窗口语料篇数。
  近一年语料 423,464 篇，近三年 1,043,978 篇。
- `yoy = df_recent / df_prev`；`vs_3y = df_recent / df_3y`。
- `slope`：core 12 个季度 `log(df_q)` 的 OLS 斜率（有效季度 < 8 时为 0）。
- `stability`：12 个季度里命中数 ≥ 自身季度中位数一半的季度占比。
- `citation_mean`：命中论文的篇均被引。
- `patent_growth = (2024+2025 专利 + 1) / (2022+2023 专利 + 1)`，`policy_growth` 同理。
- `energy_lift`：`P(锚点|该词命中) / P(锚点)`，基准率实测 0.4085，理论上限 2.45。
  **默认只作诊断列**，不参与判定（`use_anchor_lift: false`）。原因是它依赖手工锚点表，
  且词典中 46 个词条同时是锚点（电力系统、制氢…），其 lift 恒为 1/base，不携带信息。

## 4. 判定

先做两条排除检查（只写 `excluded_reason`，不删除、不单独成类）：

- `domain_umbrella`：`df_recent ≥ background_df_max`（2.5%）。近一年语料 423,464 篇，
  2.5% ≈ 10,587 篇，即"每 40 篇能源论文就有 1 篇提到它"。实测：电池 6.77%、
  可再生能源 5.44%、电极 4.04%、一氧化碳 3.51%、储能 3.42%、锂离子电池 3.05%。
- `cross_domain`：`energy_lift < 0.85` 且 `df_3y ≥ 0.4%`（默认关闭，见上）。

在**候选域**（未被排除且有命中）内计算规模分位 `scale_pct`，然后：

| 类别 | 门槛 |
|---|---|
| **core** | `hits_3y ≥ 150` 且 `scale_pct ≥ 0.90` 且 `df_recent ≥ 0.08%` 且 `yoy ≥ 0.90` 且 `stability ≥ 0.80` |
| **emerging** | `hits_recent ≥ 120` 且 `yoy ≥ 1.30` 且 `vs_3y ≥ 1.20` 且 `slope > 0` |
| **potential** | `hits_3y ≥ 40` 且 `yoy ≥ 0.90` 且〔(`patents_recent ≥ 20` 且 `patent_growth ≥ max(1.25, yoy²)`) 或 (`policies_recent ≥ 10` 且 `policy_growth ≥ 1.20`)〕|

`hotspot_class` 只有三个取值：`core / emerging / potential`；未入选词条该列留空，
原因写在 `excluded_reason`（另含 `below_gate`）。类别互斥，优先级
`cross_domain > domain_umbrella > emerging > core > potential`。

`potential` 的专利门槛要求专利增速不慢于论文份额增速（专利是两年比率，年化后与 `yoy` 对齐）。
只要求专利绝对增长的话，几乎所有成熟词条都会入选（电池、储能、电力系统都会混进来）。

分数（`core_score` 等）是百分位组合，**只用于同类别内排序，不参与入选**。

## 5. 发布配额与人工复核

| 概念 | 列 / 文件 | 含义 |
|---|---|---|
| 判定 | `hotspot_class` / `pass_*` | 由门槛决定，全量保留，不截断 |
| 发布配额 | `in_shortlist`（`shortlist_size`，默认 50） | 各类按类别内分数取前 N，只决定对外展示哪几条 |
| 人工复核 | `config/manual_review.json` | 从配额名单里剔除属性词、指标、机理、表征手段、通用材料、泛概念、通用方法 |

三者严格解耦：改配额不影响判定；人工复核**只读** `outputs/`，由
`tools/make_report.py` 生成 `docs/研究报告.md` 与 `docs/reviewed_hotspots.csv`，
不改写任何算法产物。复核规则见 `manual_review.json` 的 `protocol` 与 `exclude_types`。

## 6. 产物

| 文件 | 内容 |
|---|---|
| `papers_by_quarter.csv` | 词条 × 季度命中（float，含 year-only 均摊权重）、锚定命中 |
| `patents_by_year.csv` / `policies_by_year.csv` | 词条 × 年度命中 |
| `corpus_totals.csv` | 季度文档量、锚定文档量 —— 所有份额的分母 |
| `citations_by_term.csv` | 词条级引用合计 |
| `dict_snapshot.csv` / `run_meta.json` | 词典快照 / 运行元信息 |
| `terms_report.csv` | 全部 1,811 词条的判定与指标（含 `pass_*` / `in_shortlist` / `excluded_reason`） |
| `shortlist.csv` | 三类配额名单（每类前 `shortlist_size`，按类别内名次排序） |

## 7. 复现

```bash
PYTHONPATH=src python -m energy_hotspots.term_hotspots rebuild   # 全量重扫（并行，约 3 分钟）
PYTHONPATH=src python -m energy_hotspots.term_hotspots report    # 只重算报表
PYTHONPATH=src python -m energy_hotspots.term_hotspots find --term 固态电池
PYTHONPATH=src python -m pytest tests/term_hotspots -q
python tools/make_report.py                                      # 生成研究报告
```

`outputs/terms/` 下的计数与判定产物**随仓库提供**（`subtopic_report.csv` 除外，子方向聚合已迁至
[grid-bottleneck-report](https://github.com/Liangyl0428/grid-bottleneck-report)），所以 `report` 可直接重跑；
报告数字对账用该仓库的 `grid-bottleneck verify`。

环境变量：`ENERGY_CORPUS_DB`、`ENERGY_PATENT_DIR`、`ENERGY_POLICY_JSONL`、
`ENERGY_TERMS_OUT`（默认 `outputs/terms`）、`ENERGY_ANCHORS`、`ENERGY_WORKERS`。

## 8. 已知限制

1. **词条热度 ≠ 技术突破。** 统计只说明"在被索引的文献/专利/政策里被讨论得多"，
   不说明技术成熟度或产业价值。词典含"表征与测试方法"子方向，质谱、XRD 这类词条
   进入候选是词典设计使然。
2. **语料不是严格的能源全库。** 纳入分析的 154.9 万篇中约 40% 能匹配到锚点词，
   域外噪声靠 DF 阈值压制，挡不住全部。
3. **领域通用语只能挡最明显的一批。** 2.5% 阈值排除 19 条；`掺杂`（2.36%）、
   `能效`（2.16%）刚好在线下，仍留在候选池，需要人工复核。
4. **锚点表是手工的，且有自锚定问题。** 词典中 46 个词条同时是锚点，`lift ≡ 1/base`；
   锚点增删会整体平移 lift（缺材料侧锚点时 `全固态电池` 0.77，补上后 2.45）。
   因此默认不用于判定。开启后代价是 7 条材料/化学通用词进入核心名单
   （MXene、光催化、合金、异质结、储氢、共价有机框架等），并挤掉 7 条能源词。
5. **统计量替代不了语义判断。** 试过两个替代指标（子方向覆盖数、词条共现有效邻居数），
   都不成立：`微电网` 覆盖 14 个子方向、`制氢` 118.7 个有效邻居，都高于
   `掺杂`（8）和 `光催化`（70.0）。`制氢`/`微电网` 与 `掺杂`/`合金` 在统计上
   同属"能源论文里到处出现"，区分它们需要语义信息。
6. **专利与政策覆盖期不同。** 政策 6,621 条（2000–2026，其中 2013 年后 5,889 条、
   61 条无日期），专利 2021–2025，潜在热点的跨源判断受此限制。
7. **人工复核可复现但带主观性。** 规则写在 `manual_review.json`，换一个人复核会得到
   略有差异的名单。
8. **日期修复是期望值。** year-only 文档按季度均摊，单篇真实季度不可恢复；
   修复后 2025Q1 仍比其它季度低约 16%，残余原因未查明。
