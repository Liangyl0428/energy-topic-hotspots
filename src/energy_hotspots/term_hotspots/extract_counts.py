# -*- coding: utf-8 -*-
"""
论文 / 专利 / 政策 三类语料的词典变体命中计数。

计数规则（每条都对应一个已确认的缺陷）：
1. **文档级去重**：每篇文档对每个词条至多计 1 次。若按命中的模式累加，一个词条
   平均有 2.45 个变体，同一篇论文会被重复计入（实测总体虚高 7.2%，析氧反应 +119%）。
   去重后 `papers` 列即文档频次（DF），与份额指标同量纲。
2. **父子词条最长匹配抑制**：词典中 240 个中文名是其它词条的子串
   （石墨 ⊂ 石墨烯、配电网 ⊂ 主动配电网），不做抑制会父子重复计数。
3. **英文复数与分隔符归一**：见 xmatcher。
4. **短缩略语大小写敏感**：`CO`（一氧化碳别名）、`ES`（储能别名）不再命中
   Co（钴）/ Co.（公司）/ Es（锿）。
5. **季度口径修正**：语料存在 year-only 日期占位（publication_date 落在 1 月 1 日），
   实测占位率 2022 年 10.4% → 2026 年 25.0%，且全部堆在 Q1，会同时伪造
   "Q1 尖峰"与"近期加速"。这类文档按该年在语料中实际出现的季度均摊（1/4、1/3），
   季度份额因此无偏；全年合计不受影响。
6. **能源语境 lift**：额外统计"命中文档中同时命中能量锚点"的比例，作为诊断列输出
   （默认不参与判定，见 config/hotspot_rules.json 的 use_anchor_lift）。

产物（默认 outputs/terms/）：
- papers_by_quarter.csv / patents_by_year.csv / policies_by_year.csv
- corpus_totals.csv（季度文档量、锚定文档量 —— 份额分母）
- citations_by_term.csv（词条级引用合计）
- dict_snapshot.csv / run_meta.json
"""
from __future__ import annotations

import csv
import glob
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import duckdb
import pandas as pd

from .tech_terms import load_terms
from .xmatcher import Aho, is_acronym_alias, suppress_contained

REPO = Path(__file__).resolve().parents[3]
DATA_ROOT = Path(os.environ.get("ENERGY_DATA_ROOT", str(REPO.parent)))
CORPUS_DB = Path(os.environ.get("ENERGY_CORPUS_DB", DATA_ROOT / "analyze/data/independent_corpus.duckdb"))
PATENT_DIR = Path(os.environ.get("ENERGY_PATENT_DIR", DATA_ROOT / "data/patent"))
POLICY_JSONL = Path(os.environ.get("ENERGY_POLICY_JSONL", DATA_ROOT / "data/policy/政策全文.jsonl"))
ANCHORS_PATH = Path(os.environ.get("ENERGY_ANCHORS", REPO / "config/energy_anchors.json"))
OUT = Path(os.environ.get("ENERGY_TERMS_OUT", REPO / "outputs/terms"))

# ---- 论文窗口（与 METHOD.md 同步冻结）------------------------------------
QUARTERS = [f"{y}Q{q}" for y in range(2021, 2027) for q in range(1, 5)][2:22]  # 2021Q3..2026Q2
PATENT_YEARS = ("2021", "2022", "2023", "2024", "2025")
WORKERS = int(os.environ.get("ENERGY_WORKERS", "0")) or min(48, (os.cpu_count() or 8))


# ---------------------------------------------------------------- 全局（fork 共享）
_AC: Aho | None = None          # 大小写不敏感自动机
_AC_CS: Aho | None = None       # 缩略语自动机（大小写敏感）
_TERMS: list = []               # pid -> TechTerm
_ANCH: Aho | None = None
_CON = None
_PATENT_OWNED: set = set()


def build_automaton(terms):
    """把词条的匹配串拆成『普通』与『短缩略语』两套模式。"""
    norm, cs = [], []
    for pid, term in enumerate(terms):
        for s in term.match_strings():
            (cs if is_acronym_alias(s) else norm).append((pid, s))
    return Aho(norm), Aho(cs, case_sensitive=True), list(terms)


def load_anchors():
    if not ANCHORS_PATH.exists():
        return [], []
    j = json.loads(ANCHORS_PATH.read_text(encoding="utf-8"))
    return j.get("anchors_zh", []), j.get("anchors_en", [])


def _build_globals(terms):
    global _AC, _AC_CS, _TERMS, _ANCH
    _AC, _AC_CS, _TERMS = build_automaton(terms)
    zh, en = load_anchors()
    _ANCH = Aho(list(enumerate(zh + en)))


def _match_pids(text):
    """两套自动机合并 + 父子最长匹配抑制 + 词条去重。"""
    if _AC_CS is None:
        return _AC.search_dedup(text)
    spans = _AC.search_spans(text)
    spans += _AC_CS.search_spans(text)
    if not spans:
        return []
    spans = suppress_contained(spans)
    seen, out = set(), []
    for pid, _s, _e in spans:
        if pid not in seen:
            seen.add(pid)
            out.append(pid)
    return out


def _init_matcher(_=None):
    """fork 下自动机由父进程继承；仅在未初始化（spawn 或单进程直调）时重建。"""
    if _AC is None:
        _build_globals(load_terms())


def _init_paper_worker(_=None):
    global _CON
    _init_matcher()
    if _CON is None:
        _CON = duckdb.connect(str(CORPUS_DB), read_only=True)


def children_for_year(con):
    """每个日历年在语料中实际出现的季度（用于 year-only 日期均摊）。

    注意：`works.quarter` 列并非由 publication_date 推得（实测 17,293 行不一致，
    疑似取 article_date/preprint_date），这里一律从 publication_date 现算，
    与 `_repaired_weights` 保持同一口径。
    """
    rows = con.execute(
        "SELECT year(publication_date) AS y, quarter(publication_date) AS q, count(*) AS n "
        "FROM works WHERE is_retracted = 0 "
        "AND publication_date >= CAST('2020-01-01' AS DATE) "
        "AND publication_date < CAST('2027-01-01' AS DATE) "
        "GROUP BY 1, 2 HAVING count(*) > 0"
    ).fetchall()
    per_year = defaultdict(list)
    for year, q, _n in rows:
        per_year[int(year)].append(f"{int(year)}Q{int(q)}")
    return {y: sorted(qs) for y, qs in per_year.items()}


def _repaired_weights(pub_date, year_quarters):
    """一条文档折算成 {quarter: 权重}。

    year-only 占位（月=日=1）按该年实际出现季度均摊；其余按真实日期落季度。
    """
    y = pub_date.year
    qs = year_quarters.get(y) or []
    if pub_date.month == 1 and pub_date.day == 1 and len(qs) > 1:
        w = 1.0 / len(qs)
        return {q: w for q in qs}
    return {f"{y}Q{(pub_date.month - 1) // 3 + 1}": 1.0}


def _scan_month(task):
    year, month, year_quarters = task
    start = f"{year:04d}-{month:02d}-01"
    end = f"{year + 1:04d}-01-01" if month == 12 else f"{year:04d}-{month + 1:02d}-01"
    stat = defaultdict(float)
    term_stat = defaultdict(float)
    term_anch = defaultdict(float)
    cited_sum = defaultdict(float)
    cited_n = defaultdict(int)
    cur = _CON.execute(
        "SELECT clean_title, clean_abstract, cited_by_count, publication_date FROM works "
        "WHERE is_retracted = 0 AND publication_date >= CAST(? AS DATE) AND publication_date < CAST(? AS DATE)",
        [start, end],
    )
    seen_docs = 0
    while True:
        df = cur.fetch_df_chunk(40_000)
        if df is None or len(df) == 0:
            break
        titles = df["clean_title"].fillna("").tolist()
        abstracts = df["clean_abstract"].fillna("").tolist()
        cites = df["cited_by_count"].tolist()
        dates = df["publication_date"].tolist()
        for ct, ca, c, d in zip(titles, abstracts, cites, dates):
            text = ((ct or "") + " \n " + (ca or "")) if ca else (ct or "")
            if not text.strip() or d is None:
                continue
            seen_docs += 1
            weights = _repaired_weights(d, year_quarters)
            anchored = bool(_ANCH.search_dedup(text))
            for q, w in weights.items():
                stat[("docs", q)] += w
                if anchored:
                    stat[("anch", q)] += w
            keys = _match_pids(text)
            if not keys:
                continue
            for pid in keys:
                key = _TERMS[pid].key
                for q, w in weights.items():
                    term_stat[(key, q)] += w
                    if anchored:
                        term_anch[(key, q)] += w
                cited_sum[key] += (c or 0)
                cited_n[key] += 1
    return {"docs": seen_docs, "stat": dict(stat), "term": dict(term_stat),
            "term_anch": dict(term_anch), "cited_sum": dict(cited_sum), "cited_n": dict(cited_n)}


def scan_papers(term_keys=None, workers=None):
    terms = _load_filtered(term_keys)
    _build_globals(terms)
    con = duckdb.connect(str(CORPUS_DB), read_only=True)
    year_quarters = children_for_year(con)
    con.close()
    tasks = [(y, m, year_quarters) for y in range(2021, 2027) for m in range(1, 13)]

    totals = defaultdict(float)
    term_q = defaultdict(lambda: defaultdict(float))
    term_qa = defaultdict(lambda: defaultdict(float))
    cited_sum, cited_n = defaultdict(float), defaultdict(int)
    docs_seen = 0

    import multiprocessing as mp
    ctx = mp.get_context("fork")
    t0 = time.time()
    with ctx.Pool(workers or WORKERS, initializer=_init_paper_worker) as pool:
        for i, res in enumerate(pool.imap_unordered(_scan_month, tasks), 1):
            docs_seen += res["docs"]
            for (kind, q), v in res["stat"].items():
                totals[(kind, q)] += v
            for (key, q), v in res["term"].items():
                term_q[key][q] += v
            for (key, q), v in res["term_anch"].items():
                term_qa[key][q] += v
            for k, v in res["cited_sum"].items():
                cited_sum[k] += v
            for k, v in res["cited_n"].items():
                cited_n[k] += v
            if i % 12 == 0:
                print(f"  papers {i}/{len(tasks)} 批次  {time.time()-t0:.0f}s", file=sys.stderr, flush=True)
    print(f"papers: 扫描 {docs_seen:,} 篇（{time.time()-t0:.0f}s）", file=sys.stderr, flush=True)

    counts = {t.key: {q: term_q[t.key].get(q, 0.0) for q in QUARTERS} for t in terms}
    anch = {t.key: {q: term_qa[t.key].get(q, 0.0) for q in QUARTERS} for t in terms}
    qt = {q: totals[("docs", q)] for q in QUARTERS}
    qa = {q: totals[("anch", q)] for q in QUARTERS}
    return counts, anch, dict(cited_sum), dict(cited_n), qt, qa, docs_seen


# ------------------------------------------------------------------- 专利
def _init_patent(_=None):
    _init_matcher()


def _scan_patent_file(path):
    stat = defaultdict(float)
    try:
        for chunk in pd.read_csv(path, chunksize=40_000, dtype=str, on_bad_lines="skip"):
            if not {"publication_number", "publication_date", "title"}.issubset(chunk.columns):
                return dict(stat)
            abstracts = chunk["abstract"] if "abstract" in chunk.columns else pd.Series([""] * len(chunk), index=chunk.index)
            for title, abstract, pubdate, pnumber in zip(
                chunk["title"].fillna(""), abstracts.fillna(""),
                chunk["publication_date"].fillna(""), chunk["publication_number"].fillna(""),
            ):
                year = (pubdate or "")[:4]
                if year not in PATENT_YEARS:
                    continue
                if pnumber and pnumber not in _PATENT_OWNED:
                    continue
                text = ((title or "") + " \n " + (abstract or "")) if abstract else (title or "")
                if not text.strip():
                    continue
                for pid in _match_pids(text):
                    stat[(_TERMS[pid].key, year)] += 1
    except Exception as exc:  # 单文件失败不应中断全量
        print(f"warn patent {path}: {exc}", file=sys.stderr, flush=True)
    return dict(stat)


def scan_patents(term_keys=None, workers=None, dedup_by_number=True):
    """按 publication_number 全局去重（同一专利可能同时出现在聚合表与 IPC 分表）。"""
    global _PATENT_OWNED
    terms = _load_filtered(term_keys)
    _build_globals(terms)

    files = sorted(glob.glob(str(PATENT_DIR / "*.csv")))
    owned: set = set()
    for f in files:  # 排序靠前者优先拥有（聚合表在前，字段更全）
        try:
            col = pd.read_csv(f, usecols=["publication_number"], dtype=str, on_bad_lines="skip")
        except Exception:
            continue
        nums = col["publication_number"].fillna("")
        owned.update(x for x in nums if x)
    _PATENT_OWNED = owned
    print(f"patents: {len(files)} 个文件, {len(owned):,} 个唯一公开号", file=sys.stderr, flush=True)

    counts = {t.key: defaultdict(float) for t in terms}
    t0 = time.time()
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    with ctx.Pool(min(workers or WORKERS, max(len(files), 1)), initializer=_init_patent) as pool:
        for stat in pool.imap_unordered(_scan_patent_file, files):
            for (key, year), v in stat.items():
                counts[key][year] += v
    print(f"patents: 完成（{time.time()-t0:.0f}s）", file=sys.stderr, flush=True)
    return {k: dict(v) for k, v in counts.items()}


# ------------------------------------------------------------------- 政策
def _scan_policy_batch(batch):
    stat = defaultdict(float)
    for line in batch:
        line = line.strip()
        if not line:
            continue
        try:
            j = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = ((j.get("title") or "") + " \n " + (j.get("text") or "")).strip()
        if not text:
            continue
        year = (j.get("publication_date") or j.get("issue_date") or "")[:4]
        if not year.isdigit():
            continue
        for pid in _match_pids(text):
            stat[(_TERMS[pid].key, year)] += 1
    return dict(stat)


def scan_policies(term_keys=None, workers=None, batch=150):
    terms = _load_filtered(term_keys)
    _build_globals(terms)
    if not POLICY_JSONL.exists():
        print(f"warn policies 缺失: {POLICY_JSONL}", file=sys.stderr, flush=True)
        return {t.key: {} for t in terms}
    lines = [ln for ln in POLICY_JSONL.read_text(encoding="utf-8").splitlines() if ln.strip()]
    batches = [lines[i:i + batch] for i in range(0, len(lines), batch)]
    counts = {t.key: defaultdict(float) for t in terms}
    t0 = time.time()
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    with ctx.Pool(workers or WORKERS, initializer=_init_matcher) as pool:
        for stat in pool.imap_unordered(_scan_policy_batch, batches):
            for (key, year), v in stat.items():
                counts[key][year] += v
    print(f"policies: {len(lines):,} 条（{time.time()-t0:.0f}s）", file=sys.stderr, flush=True)
    return {k: dict(v) for k, v in counts.items()}


# ------------------------------------------------------------------- 输出
def _load_filtered(term_keys):
    terms = load_terms()
    if not term_keys:
        return terms
    keep = set(term_keys)
    return [t for t in terms if t.key in keep]


def write_outputs(paper_counts, paper_anch, cited_sum, cited_n, patent_counts,
                  policy_counts, quarter_totals, quarter_anch, docs_seen):
    OUT.mkdir(parents=True, exist_ok=True)
    terms = load_terms()
    idx = {t.key: t for t in terms}

    with open(OUT / "papers_by_quarter.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["term_id", "term", "term_en", "subtopic", "quarter", "papers", "papers_anch"])
        for key, per in paper_counts.items():
            t = idx[key]
            for q in QUARTERS:
                w.writerow([key, t.zh, t.en, t.subtopic, q, f"{per.get(q, 0.0):.4f}",
                            f"{paper_anch.get(key, {}).get(q, 0.0):.4f}"])

    # 引用是词条级合计，单独成表。若写在每一行季度记录上，按列求和会放大 20 倍。
    with open(OUT / "citations_by_term.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["term_id", "cited_sum", "cited_n"])
        for key in paper_counts:
            w.writerow([key, cited_sum.get(key, 0), cited_n.get(key, 0)])

    def _year_writer(counts, name, col):
        with open(OUT / name, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["term_id", "term", "term_en", "subtopic", "year", col])
            for key, per in counts.items():
                t = idx[key]
                for y in sorted(per.keys()):
                    w.writerow([key, t.zh, t.en, t.subtopic, y, f"{per[y]:.4f}"])

    _year_writer(patent_counts, "patents_by_year.csv", "patents")
    _year_writer(policy_counts, "policies_by_year.csv", "policies")

    with open(OUT / "corpus_totals.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["quarter", "docs", "docs_anchored", "anchored_share"])
        for q in QUARTERS:
            d = quarter_totals.get(q, 0.0)
            a = quarter_anch.get(q, 0.0)
            w.writerow([q, f"{d:.4f}", f"{a:.4f}", f"{(a / d if d else 0):.6f}"])

    with open(OUT / "dict_snapshot.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["term_id", "term", "term_en", "aliases", "subtopic"])
        for t in terms:
            w.writerow([t.key, t.zh, t.en, ";".join(t.aliases), t.subtopic])

    meta = {
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "corpus_db": str(CORPUS_DB),
        "docs_scanned": docs_seen,
        "terms": len(terms),
        "counting": {
            "doc_level_dedup": True,
            "longest_match": True,
            "ascii_normalized": True,
            "plural_variants": True,
            "acronym_case_sensitive": True,
            "year_only_date_repair": "spread over observed quarters",
        },
    }
    (OUT / "run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return OUT
