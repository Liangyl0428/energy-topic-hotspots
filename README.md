# 能源技术词条级热点识别

按**技术词条**识别能源领域文献/专利/政策热区。输入技术中文官方名称（需存在于内置词典），
算法用其中文官方名、英文官方名与别称/简称对三类语料做全文匹配，给出
**核心 / 新兴 / 潜在**三类热点。

判定口径全部是**份额（文档频率）**，不是原始篇数——语料本身年均增长约 24%，用原始计数算增长
会让所有词条自动"新兴"。方法与全部门槛见 [docs/METHOD.md](docs/METHOD.md)，
方法说明与三类热点名单见 [docs/研究报告.md](docs/研究报告.md)，
瓶颈与颠覆性方向分析见 [docs/电网瓶颈与颠覆性方向.md](docs/电网瓶颈与颠覆性方向.md)。

## 快速上手

```bash
python -m pip install -e '.[dev]'

# 全量重扫（并行，约 3 分钟：175 万篇论文 + 44.5 万件专利 + 7 千条政策）
PYTHONPATH=src python -m energy_hotspots.term_hotspots rebuild

# 只重算报表（不扫语料）；--print-list 打印三类名单，--shortlist N 改发布条数
PYTHONPATH=src python -m energy_hotspots.term_hotspots report --print-list

# 单条复核（分位在全词典上算，与批量结果一致）
PYTHONPATH=src python -m energy_hotspots.term_hotspots find --term 固态电池

# 测试 / 生成研究报告
PYTHONPATH=src python -m pytest tests/term_hotspots -q
python tools/make_report.py
```

## 数据位置

| 环境变量 | 默认 | 用途 |
|---|---|---|
| `ENERGY_DATA_ROOT` | 仓库上级目录 | 数据根 |
| `ENERGY_CORPUS_DB` | `<DATA_ROOT>/analyze/data/independent_corpus.duckdb` | 论文表（`works` 视图） |
| `ENERGY_PATENT_DIR` | `<DATA_ROOT>/data/patent` | 专利 CSV（按 `publication_number` 去重） |
| `ENERGY_POLICY_JSONL` | `<DATA_ROOT>/data/policy/政策全文.jsonl` | 政策全文 |
| `ENERGY_TERMS_OUT` | `outputs/terms` | 计数与报表输出目录 |
| `ENERGY_ANCHORS` | `config/energy_anchors.json` | 能量锚点（只影响诊断列） |
| `ENERGY_WORKERS` | `min(48, CPU)` | 并行进程数 |

## 配置

| 文件 | 作用 |
|---|---|
| `config/technology_terms/` | 词典：1,811 词条 / 33 子方向 / 三列（中文官方名、英文官方名、别称） |
| `config/hotspot_rules.json` | 判定门槛。改门槛不需要改代码；改完必须同步 METHOD.md |
| `config/energy_anchors.json` | 锚点词，只影响 `energy_lift` 诊断列（默认不参与判定） |
| `config/manual_review.json` | 人工复核清单，只影响研究报告 |

## 判定一览

| 类别 | 含义 | 主要依据 |
|---|---|---|
| `core` | 规模在候选域前 10%、分布稳、不衰退 | 三年命中 + 份额 + 季度稳定性 |
| `emerging` | 份额在涨，且涨得比语料快 | 份额同比 ≥ 1.30 且 近一年/近三年 ≥ 1.20 |
| `potential` | 论文侧尚未起势，专利/政策侧先加速 | 专利增速不慢于论文份额增速（或政策支路） |

未入选词条的 `hotspot_class` 留空，原因写入 `excluded_reason`：
`domain_umbrella`（近一年 DF ≥ 2.5%，领域通用语）、`cross_domain`（锚点 lift 过低，默认关闭）、
`below_gate`（未达任一门槛）。

> **判定 ≠ 发布条数。** `hotspot_class` 是门槛结果（全量保留）；`in_shortlist` 是发布配额
> （默认每类前 50）；`config/manual_review.json` 是人工复核（只作用于报告）。三者互不影响。

## 目录

| 路径 | 内容 |
|---|---|
| `src/energy_hotspots/term_hotspots/` | `tech_terms.py` 词典、`xmatcher.py` 匹配器、`extract_counts.py` 计数、`hotspot_rules.py` 判定、`cli.py` 入口 |
| `tests/term_hotspots/` | 单元测试（34 条） |
| `tools/make_report.py` | 由算法产物 + 人工复核清单生成研究报告 |
| `tools/finalize_report.py` | `report` 的兼容入口 |
| `docs/METHOD.md` | 方法、门槛、产物、限制 |
| `docs/研究报告.md`、`docs/reviewed_hotspots.csv` | 研究报告与复核名单 |
| `docs/电网瓶颈与颠覆性方向.md` | 关键是瓶颈与潜在颠覆性方向分析（基于同一批数据） |
| `outputs/terms/` | 计数产物与算法报表（`terms_report.csv` 全量、`shortlist.csv` 每类前 50） |
