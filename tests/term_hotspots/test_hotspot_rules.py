"""判定层回归测试：份额口径、无静默截断、互斥分类、背景词/域外词。"""
import json
import math
from pathlib import Path

from energy_hotspots.term_hotspots.hotspot_rules import (
    BASELINE_Q, CORE_Q, DEFAULT_RULES, HISTORY_Q, PREV_Q, RECENT_Q,
    assign_percentiles, classify, compute_metrics, load_rules, summarize)


def test_default_rules_match_config():
    """DEFAULT_RULES 必须与 config/hotspot_rules.json 的非注释键逐项一致。

    config 缺失时（wheel 安装、只拷 src）会静默退回 DEFAULT_RULES；两套门槛不同，
    等于同一份代码在两种安装方式下给出两套判定。
    """
    cfg = json.loads((Path(__file__).resolve().parents[2] / "config" / "hotspot_rules.json")
                     .read_text(encoding="utf-8"))
    for section in ("core", "emerging", "potential"):
        for key, value in cfg[section].items():
            if key.startswith("_"):
                continue
            assert DEFAULT_RULES[section].get(key) == value, f"{section}.{key} 默认值与 config 不一致"
    for key in ("version", "background_df_max", "off_domain_lift_min", "cross_domain_df_min",
                "shortlist_size", "use_anchor_lift"):
        assert DEFAULT_RULES.get(key) == cfg.get(key), f"{key} 默认值与 config 不一致"


def test_windows_match_method():
    """窗口是结论的一部分：METHOD.md §1 的季度数必须与代码一致。"""
    assert [len(HISTORY_Q), len(CORE_Q), len(RECENT_Q), len(PREV_Q), len(BASELINE_Q)] == [20, 12, 4, 4, 8]
    assert BASELINE_Q[0] == "2021Q3" and BASELINE_Q[-1] == "2023Q2"
    assert BASELINE_Q[-1] < CORE_Q[0]


def flat_totals(n_per_q=100_000.0):
    return {q: n_per_q for q in HISTORY_Q}


def metrics(hits_by_quarter, totals=None, anch=None, patents=None, policies=None):
    totals = totals or flat_totals()
    return compute_metrics(hits_by_quarter, anch or {}, totals, {}, cited_sum=0.0, cited_n=0,
                           patents=patents or {}, policies=policies or {})


def test_empty_has_no_class():
    m = metrics({})
    assign_percentiles({"?": m})
    classify({"?": m})
    assert m["hotspot_class"] == ""


def test_corpus_growth_alone_does_not_create_emerging():
    """语料自身增长时，若用原始计数比较，所有词条都会自动『新兴』。

    这里词条命中数按语料同比例增长（份额不变），必须判定为『份额零增长』。
    """
    totals = {}
    for i, q in enumerate(HISTORY_Q):
        totals[q] = 100_000.0 * (1.0 + 0.05 * i)      # 语料每季度涨 5%
    hits = {q: 0.01 * totals[q] for q in HISTORY_Q}   # 份额恒定 1%
    m = metrics(hits, totals)
    assert abs(m["yoy"] - 1.0) < 0.02
    assign_percentiles({"?": m})
    classify({"?": m})
    assert not m["pass_emerging"]


def test_real_share_growth_is_emerging():
    totals = flat_totals()
    hits = {q: 200.0 for q in HISTORY_Q}
    for q in RECENT_Q:
        hits[q] = 1200.0
    m = metrics(hits, totals)
    assert m["yoy"] > 1.3
    assert m["vs_3y"] > 1.15
    assign_percentiles({"?": m})
    classify({"?": m})
    assert m["pass_emerging"]
    assert m["hotspot_class"] == "emerging"


def test_core_requires_stability_and_no_collapse():
    totals = flat_totals()
    hits = {q: 1000.0 for q in HISTORY_Q}
    m = metrics(hits, totals)
    assert m["stability"] == 1.0
    assert m["yoy"] > 0.99
    assign_percentiles({"?": m})
    classify({"?": m})
    assert m["hotspot_class"] == "core"


def test_no_cap_all_gate_passers_are_classified():
    """判定不能被『门槛 ∩ 前 N 名』截断（实测曾丢掉 emerging 24/77、potential 51/105）。

    同样满足门槛的 150 个词条必须全部拿到类别。
    """
    results = {}
    totals = flat_totals()
    for i in range(150):
        hits = {q: 200.0 for q in HISTORY_Q}
        for q in RECENT_Q:
            hits[q] = 1200.0 + i
        m = metrics(hits, totals)
        m["term"] = f"t{i}"
        results[f"t{i}"] = m
    assign_percentiles(results)
    classify(results, load_rules())
    emerging = [v for v in results.values() if v["hotspot_class"] == "emerging"]
    assert len(emerging) == 150
    assert summarize(results)["emerging"] == 150


def test_classes_are_mutually_exclusive():
    """类别必须互斥：潜在热点不能同时是核心热点。"""
    results = {}
    totals = flat_totals()
    for i, (grow, pat) in enumerate([(1.0, 500.0), (3.0, 500.0), (1.0, 5.0)]):
        hits = {q: 300.0 for q in HISTORY_Q}
        if grow > 1:
            for q in RECENT_Q:
                hits[q] = 300.0 * grow
        m = metrics(hits, totals, patents={"2024": pat, "2025": pat, "2022": 1, "2023": 1})
        m["term"] = f"t{i}"
        results[f"t{i}"] = m
    assign_percentiles(results)
    classify(results, load_rules())
    for v in results.values():
        flags = [v["is_core"], v["is_emerging"], v["is_potential"]]
        assert sum(bool(x) for x in flags) <= 1


def test_background_term_is_not_a_hotspot():
    """一氧化碳占 2026Q1 语料 7.3%、储能 5.3%——是领域本身，不是热点。"""
    totals = flat_totals()
    hits = {q: 3000.0 for q in HISTORY_Q}   # 每季度 3% 文档频率
    m = metrics(hits, totals)
    assign_percentiles({"?": m})
    classify({"?": m}, load_rules())
    assert m["is_background"]
    assert m["excluded_reason"] == "domain_umbrella"


def test_cross_domain_term_flagged():
    """真正广口径的泛化词（光催化剂 lift 0.40、单晶 0.63、合金 0.84）才判跨域。"""
    totals = flat_totals()
    hits = {q: 900.0 for q in HISTORY_Q}          # 每季度 0.9% 文档频率，满足"广泛使用"
    anch = {q: 180.0 for q in HISTORY_Q}          # 命中文档里锚点占比 20%，基准 50% -> lift 0.40
    doc_anch = {q: 50_000.0 for q in HISTORY_Q}
    m = compute_metrics(hits, anch, totals, doc_anch)
    assign_percentiles({"?": m})
    rules = load_rules()
    rules["use_anchor_lift"] = True
    classify({"?": m}, rules)
    assert m["energy_lift"] < 0.85
    assert m["excluded_reason"] == "cross_domain"


def test_narrow_low_lift_term_not_excluded():
    """窄口径词的 lift 低多半是锚点覆盖不足（锂金属负极 lift 0.56、DF 0.17%），
    不能当成跨域泛化词误杀——只打 low_anchor_coverage 标记，仍参与判定。"""
    totals = flat_totals()
    hits = {q: 250.0 for q in HISTORY_Q}          # 0.25% < 0.4% 的广度门槛
    anch = {q: 50.0 for q in HISTORY_Q}
    doc_anch = {q: 50_000.0 for q in HISTORY_Q}
    m = compute_metrics(hits, anch, totals, doc_anch)
    assign_percentiles({"?": m})
    rules = load_rules()
    rules["use_anchor_lift"] = True
    classify({"?": m}, rules)
    assert m["energy_lift"] < 0.85
    assert m["low_anchor_coverage"]
    assert not m["is_cross_domain"]
    assert m["excluded_reason"] != "cross_domain"


def test_sector_valued_terms_not_cross_domain():
    totals = flat_totals()
    hits = {q: 300.0 for q in HISTORY_Q}
    anch = {q: 270.0 for q in HISTORY_Q}     # 90% 命中带锚点
    doc_anch = {q: 50_000.0 for q in HISTORY_Q}
    m = compute_metrics(hits, anch, totals, doc_anch)
    assign_percentiles({"?": m})
    classify({"?": m}, load_rules())
    assert m["energy_lift"] > 1.5
    assert not m["is_cross_domain"]


def test_percentiles_are_computed_on_given_universe():
    results = {f"t{i}": {"hits_3y": float(i), "hits_recent": float(i), "df_recent": i / 1e5,
                         "yoy": 1.0, "vs_3y": 1.0, "slope": 0.0, "stability": 0.0,
                         "energy_lift": 1.0, "citation_mean": 0.0, "patent_growth": 1.0}
               for i in range(10)}
    assign_percentiles(results)
    assert results["t0"]["hits_3y_pct"] == 0.1
    assert results["t9"]["hits_3y_pct"] == 1.0


def test_smoothing_keeps_zero_terms_finite():
    m = metrics({q: 0.0 for q in HISTORY_Q})
    assert m["yoy"] == 0.0 or math.isfinite(m["yoy"])
    assert math.isfinite(m["vs_3y"])


def _growing_terms(n):
    out = {}
    totals = flat_totals()
    for i in range(n):
        hits = {q: 200.0 for q in HISTORY_Q}
        for q in RECENT_Q:
            hits[q] = 1200.0 + i
        m = metrics(hits, totals)
        m["term"] = f"t{i}"
        out[f"t{i}"] = m
    return out


def test_shortlist_quota_does_not_change_judgement():
    """发布配额只决定"展示哪几条"，不改变任何判定。

    曾经的做法是用 cap 直接改判定结果且不告知（77 个过门槛只发 53 个）；
    现在 in_shortlist 是纯标记：pass_* 与 hotspot_class 都不受影响。
    """
    results = _growing_terms(150)
    rules = load_rules()
    rules["shortlist_size"] = 50
    assign_percentiles(results)
    classify(results, rules)
    assert sum(1 for v in results.values() if v["hotspot_class"] == "emerging") == 150
    assert all(v["pass_emerging"] for v in results.values())
    assert sum(v["in_shortlist"] for v in results.values()) == 50
    # 短名单恰好是分数排序后的前 50
    ranked = sorted((v for v in results.values() if v["hotspot_class"] == "emerging"),
                    key=lambda v: v["rank_emerging"])
    assert all(v["in_shortlist"] == 1 for v in ranked[:50])
    assert all(v["in_shortlist"] == 0 for v in ranked[50:])


def test_shortlist_zero_means_unlimited():
    results = _growing_terms(60)
    rules = load_rules()
    rules["shortlist_size"] = 0
    assign_percentiles(results)
    classify(results, rules)
    assert sum(v["in_shortlist"] for v in results.values()) == 60
