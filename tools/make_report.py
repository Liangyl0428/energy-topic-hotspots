# -*- coding: utf-8 -*-
"""从算法产物 + 人工复核清单生成研究报告。

原则：**只读** `outputs/`，绝不改写算法产物。
人工决策全部来自 `config/manual_review.json`，报告里逐条留痕。

用法：
    python tools/make_report.py
    python tools/make_report.py --out docs/研究报告.md
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "outputs/terms"
REVIEW = REPO / "config/manual_review.json"

CLASS_LABEL = {"core": "核心热点", "emerging": "新兴热点", "potential": "潜在热点"}
CLASS_DESC = {
    "core": "规模在候选域前 10%、12 个季度分布稳定、份额不衰退",
    "emerging": "份额同比 ≥ 1.30 且 近一年/近三年 ≥ 1.20，季度斜率 > 0",
    "potential": "论文侧未起势，但专利增速不慢于论文、或政策侧加速",
}


def fmt_pct(x):
    return f"{x * 100:.2f}%"


def load():
    rep = pd.read_csv(OUT / "terms_report.csv")
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    return rep, review


def pick(rep, review):
    """按人工清单取词条，并保持算法排名顺序。"""
    picked = {}
    for cls, keep in review["keep"].items():
        sub = rep[rep.hotspot_class == cls].set_index("term")
        missing = [t for t in keep if t not in sub.index]
        if missing:
            raise SystemExit(f"人工清单里的 {cls} 词条不在算法结果中：{missing}")
        order = sub.loc[keep].sort_values(f"rank_{cls}")
        picked[cls] = order.reset_index()
    return picked


def table(rows, cls):
    h = ("| # | 词条 | 子方向 | 三年命中 | 近一年DF | 份额同比 | 季度斜率 | 稳定性 | 专利(近2年) | 政策(近2年) | 篇均被引 |\n"
         "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    lines = [h]
    for i, r in enumerate(rows.itertuples(), 1):
        lines.append(
            f"| {i} | {r.term} | {r.subtopic} | {r.hits_3y:,.0f} | {fmt_pct(r.df_recent)} | "
            f"{r.yoy:.2f} | {r.slope:+.3f} | {r.stability:.2f} | {r.patents_recent:,.0f} | "
            f"{r.policies_recent:,.0f} | {r.citation_mean:.1f} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "docs/研究报告.md"))
    ap.add_argument("--csv", default=str(REPO / "docs/reviewed_hotspots.csv"))
    args = ap.parse_args()

    rep, review = load()
    picked = pick(rep, review)
    meta = json.loads((OUT / "run_meta.json").read_text(encoding="utf-8"))
    totals = pd.read_csv(OUT / "corpus_totals.csv").set_index("quarter")

    n_recent = totals.loc[["2025Q3", "2025Q4", "2026Q1", "2026Q2"], "docs"].sum()
    n_3y = totals.loc[[q for q in totals.index if q >= "2023Q3"], "docs"].sum()
    n_algo = {c: int((rep.hotspot_class == c).sum()) for c in CLASS_LABEL}
    n_review = {c: len(picked[c]) for c in CLASS_LABEL}

    L = []
    A = L.append
    A("# 能源技术热点研究报告\n")
    A(f"**数据截止**：{meta['built_at'][:10]}　**语料**：{meta['docs_scanned']:,} 篇论文"
      f"（2021-07 ~ 2026-06）+ 44.5 万件专利（2021–2025）+ 7,070 条政策（2013–2026）\n")
    A("**一句话结论**：在一个 1,811 条的能源技术词条词典上，用份额口径的规模/增速/稳定性指标"
      "筛出候选热点，再人工剔除属性词、指标词、表征手段和通用材料，最终得到"
      f"核心 {n_review['core']} 条、新兴 {n_review['emerging']} 条、潜在 {n_review['potential']} 条。\n")

    A("## 一、数据与方法\n")
    A("### 1.1 分析对象\n")
    A("分析单元是**技术词条**而不是论文主题：词典 `config/technology_terms/` 共 1,811 条，"
      "分属 33 个子方向（8 个常规栏目 + 基础材料类增补），每条含中文官方名、英文官方名、别称/简称。"
      "匹配时用这三类写法在论文标题+摘要、专利标题+摘要、政策全文中检索。\n")
    A("### 1.2 计数规则\n")
    A("| 项目 | 做法 | 为什么 |\n|---|---|---|\n"
      "| 计数单位 | 每篇文档对每个词条至多计 1 次 | 旧版按模式累加，一个词条 2.45 个变体，同一篇论文被重复计入（实测虚高 7.2%，个别词条 +119%） |\n"
      "| 父子词条 | 最长匹配抑制 | 词典中 240 个中文名是其它词条子串（石墨 ⊂ 石墨烯），父子重复计数会制造假热点 |\n"
      "| 英文写法 | 分隔符归一 + 复数变体 | `Lithium-ion battery` 与 `lithium ion battery` 视为同一写法 |\n"
      "| 短缩略语 | 全大写 2–6 字符走大小写敏感 | 否则别名 `CO` 会把 `Co`（钴）、`co-doped` 全部计入 |\n"
      "| 日期口径 | year-only 占位（1 月 1 日）按该年实际出现季度均摊 | 2024 年有 49,779 篇落在 1 月 1 日，直接归 Q1 会造出 3.2 倍的假尖峰 |\n"
      "| 专利去重 | 按公开号全局去重 | 同一专利同时出现在聚合表与 IPC 分表 |\n")
    A("### 1.3 指标\n")
    A(f"- **DF（文档频率）**＝命中篇数 ÷ 同窗口语料篇数。近一年语料 {n_recent:,.0f} 篇，"
      f"近三年 {n_3y:,.0f} 篇。所有增长指标都在这个份额口径上算——语料本身从 2021Q3 的 5.4 万篇/季涨到 "
      "2026Q1 的 15 万篇/季，用原始篇数算增长等于白送每个词条 24%/年。\n"
      "- **份额同比（yoy）**＝近一年 DF ÷ 上一年 DF。\n"
      "- **季度斜率**＝近三年 12 个季度 log(DF) 的最小二乘斜率。\n"
      "- **稳定性**＝12 个季度中命中数 ≥ 自身中位数一半的季度占比（与自身比，大小词条可比）。\n"
      "- **专利/政策**＝近两年 vs 前两年的数量与增速。\n")
    A("### 1.4 三类门槛\n")
    A("| 类别 | 判定 |\n|---|---|\n"
      "| 核心热点 | 三年命中 ≥ 150 且 规模在候选域前 10% 且 近一年 DF ≥ 0.08% 且 份额同比 ≥ 0.90 且 稳定性 ≥ 0.80 |\n"
      "| 新兴热点 | 近一年命中 ≥ 120 且 份额同比 ≥ 1.30 且 近一年/近三年 ≥ 1.20 且 季度斜率 > 0 |\n"
      "| 潜在热点 | 三年命中 ≥ 40 且 份额同比 ≥ 0.90 且〔专利近两年 ≥ 20 且增速 ≥ max(1.25, yoy²) 或 政策近两年 ≥ 10 且增速 ≥ 1.20〕|\n"
      "\n另有一条排除规则：近一年 DF ≥ 2.5%（约 10,600 篇）的词条判为**领域通用语**"
      "（电池 6.77%、可再生能源 5.44%、电极 4.04%、一氧化碳 3.51%、储能 3.42%），不计入热点。\n")
    A("### 1.5 发布配额与人工复核\n")
    A(f"算法对每类按类别内分数取前 50 条作为候选（实际门槛合格数为 "
      f"核心 {n_algo['core']}、新兴 {n_algo['emerging']}、潜在 {n_algo['potential']}）。"
      "本报告在候选之上**再做一次人工复核**，只保留可辨识的技术方向/系统/装备/机制，剔除七类泛词：\n")
    A("\n".join(f"- {x}" for x in review["exclude_types"]))
    A(f"\n复核后保留：核心 {n_review['core']} 条、新兴 {n_review['emerging']} 条、"
      f"潜在 {n_review['potential']} 条。**不做数量补齐**——筛完剩多少就是多少。\n")
    A("> 说明：人工复核只作用于本报告，`outputs/terms/terms_report.csv` 与 `shortlist.csv` "
      "完全是算法输出，未做任何手工改动。复核决策记录在 `config/manual_review.json`。\n")

    for cls in ("core", "emerging", "potential"):
        A(f"## 二、{CLASS_LABEL[cls]}（{n_review[cls]} 条）\n" if cls == "core"
          else f"## {'三' if cls == 'emerging' else '四'}、{CLASS_LABEL[cls]}（{n_review[cls]} 条）\n")
        A(f"判定口径：{CLASS_DESC[cls]}。\n")
        A(table(picked[cls], cls) + "\n")

    A("## 五、方法局限\n")
    A("1. **词条热度 ≠ 技术突破**。统计只能说明“在被索引的文献/专利/政策里被讨论得多”，"
      "不能说明技术成熟度或产业价值。\n"
      "2. **语料不是严格的能源全库**。该快照 175 万篇中只有 34% 能匹配到能源锚点词，"
      "域外噪声仍在，只能靠 DF 阈值压制。\n"
      "3. **领域通用语只能挡最明显的一批**。2.5% 的阈值只排除 19 条（电池、储能、电力系统等），"
      "`掺杂`（2.36%）、`能效`（2.16%）这类刚过线的词仍留在候选池里，需要人工复核。\n"
      "4. **新兴类含通用使能技术**。数字孪生、网络安全、联邦学习 的份额确实在涨（这是测出来的事实），"
      "但“算不算能源技术热点”是领域判断，本报告按“能源场景下的技术方向”保留，"
      "并把纯算法类（联邦学习、强化学习、滑模控制）剔除了。\n"
      "5. **专利与政策的覆盖期不同**。政策仅 7,070 条，专利 2021–2025，"
      "潜在热点的跨源判断受此限制。\n"
      "6. **人工复核可复现但带主观性**。剔除规则写在 `config/manual_review.json` 的 "
      "`protocol` 与 `exclude_types` 里，逐条决策可查；换一个人复核会得到略有差异的名单。\n")

    A("## 六、复现\n")
    A("```bash\n"
      "PYTHONPATH=src python -m energy_hotspots.term_hotspots rebuild   # 全量重扫（约 3 分钟，24 进程）\n"
      "PYTHONPATH=src python -m energy_hotspots.term_hotspots report    # 只重算算法报表\n"
      "python tools/make_report.py                                      # 生成本报告\n"
      "```\n")
    A("产物：`outputs/terms/terms_report.csv`（1,811 条全量判定）、`shortlist.csv`（算法前 50）、"
      "`docs/reviewed_hotspots.csv`（本报告的人工复核名单）。\n")

    Path(args.out).write_text("\n".join(L), encoding="utf-8")

    with open(args.csv, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["hotspot_class", "rank_in_class", "term", "term_en", "subtopic", "hits_3y",
                    "df_recent", "yoy", "slope", "stability", "patents_recent", "policies_recent",
                    "citation_mean"])
        for cls, rows in picked.items():
            for i, r in enumerate(rows.itertuples(), 1):
                w.writerow([cls, i, r.term, r.term_en, r.subtopic, f"{r.hits_3y:.2f}",
                            f"{r.df_recent:.6f}", f"{r.yoy:.4f}", f"{r.slope:.5f}",
                            f"{r.stability:.2f}", f"{r.patents_recent:.0f}",
                            f"{r.policies_recent:.0f}", f"{r.citation_mean:.2f}"])
    print(f"报告: {args.out}")
    print(f"名单: {args.csv}")
    print(f"核心 {n_review['core']} / 新兴 {n_review['emerging']} / 潜在 {n_review['potential']}")


if __name__ == "__main__":
    main()
