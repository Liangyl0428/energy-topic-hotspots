# -*- coding: utf-8 -*-
"""
词条级热点命令行入口。

    python -m energy_hotspots.term_hotspots find --term 锂离子电池
    python -m energy_hotspots.term_hotspots find --terms-file terms.txt
    python -m energy_hotspots.term_hotspots rebuild            # 全量重扫（并行）
    python -m energy_hotspots.term_hotspots report             # 只重算报表，不扫语料
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from .tech_terms import load_terms, must_term_by_zh

REPORT_COLUMNS = [
    "term", "term_en", "subtopic", "hotspot_class", "excluded_reason", "in_shortlist",
    "pass_core", "pass_emerging", "pass_potential", "is_background", "is_cross_domain", "low_anchor_coverage",
    "hits_3y", "hits_recent", "hits_prev", "hits_base",
    "df_recent", "df_prev", "df_3y", "yoy", "vs_3y", "slope", "stability",
    "energy_lift", "energy_context", "citation_mean",
    "patents_recent", "patents_base", "patent_growth",
    "policies_recent", "policies_base", "policy_growth",
    "core_score", "emerging_score", "potential_score",
    "rank_core", "rank_emerging", "rank_potential",
]


def _fmt(v):
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, float):
        return f"{v:.6g}"
    return v


def _out_dir():
    """报表输出目录。

    不 import extract_counts：那个模块为了扫描语料在顶层 import duckdb/pandas，
    而 `report` 只需要读 CSV。共享环境里这两个包不一定装得全（实测 duckdb 缺失、
    pandas 与 numpy ABI 不匹配），报表重算不该被它们拖死。
    取值口径与 extract_counts.OUT 保持一致（ENERGY_TERMS_OUT → <repo>/outputs/terms）。
    """
    import os
    repo = Path(__file__).resolve().parents[3]
    return Path(os.environ.get("ENERGY_TERMS_OUT", repo / "outputs/terms"))


def _read_csv(path):
    """标准库读取（不依赖 pandas）：返回 list[dict]。BOM 由 utf-8-sig 处理。"""
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _load_counts():
    """读取计数产物；缺任何一件都直接报错，避免用半套数据算出错误结论。

    只用标准库 csv：报表重算不需要 pandas，而共享环境里 pandas/numpy 的
    ABI 组合并不总是可用（实测 `report` 曾因 numpy.dtype size changed 直接崩）。
    """
    out = _out_dir()
    need = ["papers_by_quarter.csv", "corpus_totals.csv", "patents_by_year.csv",
            "policies_by_year.csv", "citations_by_term.csv"]
    missing = [f for f in need if not (out / f).exists()]
    if missing:
        raise SystemExit(
            f"缺少计数产物 {missing}（期望目录 {out}）。先运行 `rebuild`，"
            f"或用 ENERGY_TERMS_OUT 指向已有输出目录。")
    totals = {}
    anch_total = {}
    for r in _read_csv(out / "corpus_totals.csv"):
        totals[r["quarter"]] = float(r["docs"])
        anch_total[r["quarter"]] = float(r.get("docs_anchored") or 0.0)
    papers_q, papers_qa = {}, {}
    for r in _read_csv(out / "papers_by_quarter.csv"):
        papers_q.setdefault(r["term_id"], {})[r["quarter"]] = float(r["papers"])
        papers_qa.setdefault(r["term_id"], {})[r["quarter"]] = float(r.get("papers_anch") or 0.0)
    cited = {}
    cites_path = out / "citations_by_term.csv"
    if cites_path.exists():
        for r in _read_csv(cites_path):
            cited[r["term_id"]] = (float(r["cited_sum"]), int(float(r["cited_n"])))
    patents = _year_table(out / "patents_by_year.csv", "patents")
    policies = _year_table(out / "policies_by_year.csv", "policies")
    return papers_q, papers_qa, cited, patents, policies, totals, anch_total


def _year_table(path, col):
    if not Path(path).exists():
        return {}
    out = {}
    for r in _read_csv(path):
        if "term_id" not in r or "year" not in r or col not in r:
            return {}
        try:
            y = str(int(float(r["year"])))
        except (TypeError, ValueError):
            continue
        out.setdefault(r["term_id"], {})[y] = float(r[col])
    return out


def build_results(rules=None, with_counts=False):
    """对全词典计算指标分位与判定（唯一入口，find / report 共用）。
    """
    from .hotspot_rules import compute_metrics, assign_percentiles, classify, load_rules
    rules = rules or load_rules()
    papers_q, papers_qa, cited, patents, policies, doc_totals, doc_anch = _load_counts()
    results = {}
    for t in load_terms():
        cs, cn = cited.get(t.key, (0.0, 0))
        m = compute_metrics(papers_q.get(t.key, {}), papers_qa.get(t.key, {}),
                            doc_totals, doc_anch, cs, cn,
                            patents.get(t.key, {}), policies.get(t.key, {}))
        m["key"], m["term"], m["term_en"], m["subtopic"] = t.key, t.zh, t.en, t.subtopic
        results[t.key] = m
    assign_percentiles(results)
    classify(results, rules)
    if with_counts:
        return results, rules, (papers_q, doc_totals)
    return results, rules


def write_report(results, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(REPORT_COLUMNS)
        for v in results.values():
            w.writerow([_fmt(v.get(c, "")) for c in REPORT_COLUMNS])
    return path


def report_term(v):
    cls = {"core": "核心热点", "emerging": "新兴热点", "potential": "潜在热点",
           "background": "背景词（领域本身，不计为热点）",
           "cross_domain": "跨域泛化词（能源语境 lift 过低）",
           "none": "未入选"}.get(v["hotspot_class"], v["hotspot_class"])
    lines = [
        f"词条: {v['term']} ({v['term_en']})  [{v['subtopic']}]",
        "",
        f"近三年命中 {v['hits_3y']:.0f} 篇   近一年 {v['hits_recent']:.0f}   上一年 {v['hits_prev']:.0f}",
        f"文档频率: 近一年 {v['df_recent']:.4%}  上一年 {v['df_prev']:.4%}  近三年 {v['df_3y']:.4%}",
        f"份额同比(yoy) {v['yoy']:.3f}   近一年/近三年 {v['vs_3y']:.3f}   季度斜率 {v['slope']:+.4f}",
        f"季度稳定性 {v['stability']:.2f}   能源语境 lift {v['energy_lift']:.2f}   篇均被引 {v['citation_mean']:.1f}",
        f"专利: 近两年 {v['patents_recent']:.0f} / 前两年 {v['patents_base']:.0f}"
        f"（{v['patent_growth']:.2f}×）   政策: 近两年 {v['policies_recent']:.0f}"
        f" / 前两年 {v['policies_base']:.0f}（{v['policy_growth']:.2f}×）",
        "",
        f"门槛: core={'✓' if v['pass_core'] else '×'}  emerging={'✓' if v['pass_emerging'] else '×'}"
        f"  potential={'✓' if v['pass_potential'] else '×'}"
        f"  background={'✓' if v['is_background'] else '×'}  cross_domain={'✓' if v['is_cross_domain'] else '×'}",
        f"判定: {cls}",
    ]
    return "\n".join(lines)


def run_find(term=None, terms_file=None, limit=None, out_csv=None, rules_path=None,
             shortlist=None, **kw):
    from .hotspot_rules import load_rules
    if terms_file:
        zhs = [ln.strip() for ln in open(terms_file, encoding="utf-8") if ln.strip()]
    elif term:
        zhs = [term]
    else:
        raise SystemExit("请用 --term 或 --terms-file 提供技术中文官方名称")
    keys = [must_term_by_zh(z).key for z in zhs]
    rules = load_rules(rules_path)
    if shortlist is not None:
        rules["shortlist_size"] = int(shortlist)
    results, _rules = build_results(rules)
    subset = {k: results[k] for k in keys if k in results}
    if not subset:
        raise SystemExit("没有可用词条")
    if len(subset) == 1 and not out_csv:
        print(report_term(next(iter(subset.values()))))
        return
    path = Path(out_csv) if out_csv else _out_dir() / "terms_report_find.csv"
    write_report(subset, path)
    print(f"已写: {path}  ({len(subset)} 词条)")


def run_report(out_csv=None, rules_path=None, shortlist=None, print_list=False, **kw):
    """重算报表。`shortlist` 只改发布配额，不改任何词条的判定。"""
    from .hotspot_rules import load_rules, summarize
    rules = load_rules(rules_path)
    if shortlist is not None:
        rules["shortlist_size"] = int(shortlist)
    results, rules = build_results(rules)
    path = write_report(results, Path(out_csv) if out_csv else _out_dir() / "terms_report.csv")
    # 对外交付用的短名单单独出一张表（按类别 + 类别内名次排序）
    order = {"core": 0, "emerging": 1, "potential": 2}
    picked = [v for v in results.values() if v.get("in_shortlist")]
    picked.sort(key=lambda v: (order.get(v["hotspot_class"], 9),
                               v.get(f"rank_{v['hotspot_class']}", 0)))
    sl_path = path.parent / "shortlist.csv"
    with open(sl_path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["hotspot_class"] + REPORT_COLUMNS)
        for v in picked:
            w.writerow([v["hotspot_class"]] + [_fmt(v.get(c, "")) for c in REPORT_COLUMNS])
    s = summarize(results)
    size = int(rules.get("shortlist_size") or 0)
    print(f"成绩单: {path}（词条 {len(results)}）")
    print(f"  判定结果：核心 {s.get('core', 0)}  新兴 {s.get('emerging', 0)}  潜在 {s.get('potential', 0)}")
    print(f"  未入选 {s.get('', 0)}：其中领域通用语 {s.get('reason_domain_umbrella', 0)}、"
          f"跨域泛化词 {s.get('reason_cross_domain', 0)}、未达门槛 {s.get('reason_below_gate', 0)}")
    print(f"  短名单已另存: {sl_path}")
    print(f"  短名单（每类前 {size if size else '不限'}，in_shortlist=1）："
          f"核心 {s.get('shortlist_core', 0)}  新兴 {s.get('shortlist_emerging', 0)}  "
          f"潜在 {s.get('shortlist_potential', 0)}")
    if print_list:
        for cls, label in (("core", "核心"), ("emerging", "新兴"), ("potential", "潜在")):
            names = [v["term"] for v in sorted(
                (x for x in results.values() if x["hotspot_class"] == cls and x["in_shortlist"]),
                key=lambda x: x[f"rank_{cls}"])]
            print(f"\n  [{label}热点 {len(names)}] " + "、".join(names))
    return path


def run_rebuild(**kw):
    from .extract_counts import (scan_papers, scan_patents, scan_policies, write_outputs,
                                 QUARTERS)
    print(f"[rebuild] 论文/专利/政策 全量重扫", flush=True)
    counts, anch, csum, cn, qt, qa, docs = scan_papers()
    patents = scan_patents()
    policies = scan_policies()
    out = write_outputs(counts, anch, csum, cn, patents, policies, qt, qa, docs)
    print(f"计数产物: {out}", flush=True)
    run_report()


def main():
    ap = argparse.ArgumentParser(prog="term-hotspots")
    sub = ap.add_subparsers(dest="cmd")
    f = sub.add_parser("find", help="按中文官方名称复核（分位在整个词典上算）")
    f.add_argument("--term")
    f.add_argument("--terms-file")
    f.add_argument("--limit", type=int)
    f.add_argument("--out-csv")
    f.add_argument("--rules")
    f.add_argument("--shortlist", type=int)
    r = sub.add_parser("report", help="不扫语料，只从计数产物重算报表")
    r.add_argument("--out-csv")
    r.add_argument("--rules")
    r.add_argument("--shortlist", type=int, help="每类发布配额（默认取 config，0=不限）")
    r.add_argument("--print-list", action="store_true", help="同时打印三类短名单的词条名")
    b = sub.add_parser("rebuild", help="全量重扫三类语料并重算报表")
    b.add_argument("--rules")
    args = ap.parse_args()
    if args.cmd == "find":
        run_find(term=args.term, terms_file=args.terms_file, limit=args.limit,
                 out_csv=args.out_csv, rules_path=args.rules, shortlist=args.shortlist)
    elif args.cmd == "report":
        run_report(out_csv=args.out_csv, rules_path=args.rules,
                   shortlist=args.shortlist, print_list=args.print_list)
    elif args.cmd == "rebuild":
        run_rebuild(rules_path=args.rules)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
