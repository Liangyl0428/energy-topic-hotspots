"""Recompute sample-based hotspots from the frozen OpenAlex keyword NMF model.

Run from the source workspace: .venv-hotspots/bin/python
energy-topic-hotspots/pipelines/nmf500/build.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from threadpoolctl import threadpool_limits

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO.parent
sys.path.insert(0, str(REPO / 'src'))
from energy_hotspots.scoring import score, gates, windows, percent, rank_scores

NMF = ROOT / 'energy-topic-identification/pipelines/keyword_nmf/results'
INPUTS = ROOT / 'aaaa/openalex_keywords_nmf/models'
OUTPUT = REPO / 'outputs/nmf500'
SPLITS = {'train': 'development_train', 'validation': 'validation', 'replay': 'replay_evolution'}
CORE_GATES = {'annual_volume': 60, 'current_volume': 50}
EMERGING_GATES = {'volume': 25, 'baseline': 8}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def csv(frame, path):
    frame.to_csv(path, index=False, encoding='utf-8-sig')


def prepare_papers(out):
    model_path = NMF / 'selected_nmf.joblib'
    inputs = [model_path]
    for split, filename in SPLITS.items():
        inputs += [INPUTS / f'{split}_scored.npz', ROOT / f'aaaa/data/{filename}.parquet']
    fingerprints = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    cache, check = out / 'paper_assignments.parquet', out / 'PAPER_INPUTS.json'
    if cache.exists() and check.exists() and json.loads(check.read_text()) == fingerprints:
        return pd.read_parquet(cache)
    model = joblib.load(model_path)
    frames = []
    for split, filename in SPLITS.items():
        frame = pd.read_parquet(ROOT / f'aaaa/data/{filename}.parquet')
        x = sparse.load_npz(INPUTS / f'{split}_scored.npz')
        labels = np.full(len(frame), -1, dtype=np.int32)
        top = np.zeros(len(frame), dtype=np.float32)
        margin = np.zeros(len(frame), dtype=np.float32)
        valid = np.flatnonzero(x.getnnz(1) > 0)
        for start in range(0, len(valid), 4096):
            rows = valid[start:start + 4096]
            w = model.transform(x[rows])
            good = w.sum(1) > 1e-12
            labels[rows[good]] = w[good].argmax(1)
            best = w.max(1)
            mass = np.maximum(w.sum(1), 1e-12)
            top[rows] = best / mass
            margin[rows] = (best - np.partition(w, -2, axis=1)[:, -2]) / mass
            if start % (4096 * 5) == 0:
                print(f'UNIFORM_INFERENCE {split} {start}/{len(valid)}', flush=True)
        frame['topic_id'] = labels
        frame['category_id'] = ['N%04d' % (i + 1) if i >= 0 else '' for i in labels]
        frame['split'] = split
        frame['nmf_relative_top1'] = top
        frame['nmf_relative_margin'] = margin
        frames.append(frame)
    papers = pd.concat(frames, ignore_index=True)
    conn = duckdb.connect(str(ROOT / 'analyze/data/independent_corpus.duckdb'), read_only=True)
    conn.execute('SET threads=2')
    conn.register('requested', papers[['work_id']])
    meta = conn.sql('''SELECT w.work_id, w.institutions, w.cited_by_count,
        w.is_retracted, w.template_record FROM works w JOIN requested r USING(work_id)''').df()
    conn.close()
    papers = papers.merge(meta, on='work_id', how='left', validate='one_to_one', indicator=True)
    papers['metadata_matched'] = papers.pop('_merge').eq('both')
    papers['date'] = pd.to_datetime(papers.model_date)
    papers['period'] = papers.date.dt.to_period('Q').astype(str)
    papers['year'] = papers.date.dt.year
    papers['title_key'] = papers.clean_title.fillna('').str.casefold().str.replace(r'[^\w]', '', regex=True)
    papers.to_parquet(cache, index=False)
    dump(check, fingerprints)
    return papers


def taxonomy(papers):
    catalog = pd.read_csv(NMF / 'topic_catalog.csv')
    catalog['category_id'] = catalog.topic_id.map(lambda i: f'N{i + 1:04d}')
    catalog['name'] = catalog.top_keywords.str.split(' | ', regex=False).map(lambda v: ' / '.join(v[:3]))
    # Scope is deliberately pending: numerical candidates do not certify energy relevance.
    catalog['domain'] = '待主题范围审阅'
    catalog['status'] = 'NMF关键词主题'
    catalog['analysis_scope'] = '待主题范围审阅'
    catalog['uniform_assigned_papers'] = catalog.category_id.map(papers.category_id.value_counts()).fillna(0).astype(int)
    return catalog.set_index('category_id')


def quarterly_context(papers, tax):
    quarters = pd.period_range('2021Q3', '2026Q2', freq='Q').astype(str)
    grid = pd.MultiIndex.from_product([tax.index, quarters], names=['category_id', 'period'])
    counts = papers.groupby(['category_id', 'period']).size().reindex(grid, fill_value=0).rename('papers').reset_index()
    ctx = pd.DataFrame(index=tax.index)
    inst = papers[['category_id', 'date', 'institutions']].copy()
    inst['institution'] = inst.institutions.fillna('').str.split(';')
    inst = inst.explode('institution')
    inst['institution'] = inst.institution.fillna('').str.strip().str.casefold()
    inst = inst[~inst.institution.isin(['', 'none', 'nan', '[]'])]
    ws = windows()
    for i, window in enumerate(ws):
        lo = pd.Period(window[0], freq='Q').start_time
        hi = pd.Period(window[-1], freq='Q').end_time
        values = inst[inst.date.between(lo, hi)].groupby('category_id').institution.nunique()
        ctx[f'year{i}_institutions'] = values.reindex(tax.index, fill_value=0)
    ctx['recent_institutions'] = ctx.year0_institutions
    for years in [1, 3, 5]:
        lo = pd.Period(ws[years - 1][0], freq='Q').start_time
        hi = pd.Period(ws[0][-1], freq='Q').end_time
        values = inst[inst.date.between(lo, hi)].groupby('category_id').institution.nunique()
        ctx[f'core_institutions_{years}y'] = values.reindex(tax.index, fill_value=0)
    cites = papers[papers.year.between(2023, 2025)].copy()
    cites['pc'] = cites.groupby('year').cited_by_count.rank(pct=True)
    cites.loc[cites.cited_by_count.fillna(0).eq(0), 'pc'] = 0
    ctx['citation_cohort_percentile'] = cites.groupby('category_id').pc.mean().reindex(tax.index, fill_value=0)
    return counts, ctx


def calculate(papers, tax):
    q, context = quarterly_context(papers, tax)
    z, cc, ec = score(tax, q, context, activity_quarter_min=5, active_year_min=30)
    cg = gates(z, 'core', CORE_GATES).drop(columns='scope')
    eg = gates(z, 'emerging', EMERGING_GATES).drop(columns='scope')
    z['core_numeric_candidate'] = cg.all(axis=1)
    z['emerging_numeric_candidate'] = eg.all(axis=1)
    z['core_failed_gates'] = cg.apply(lambda r: ' | '.join(r.index[~r]), axis=1)
    z['emerging_failed_gates'] = eg.apply(lambda r: ' | '.join(r.index[~r]), axis=1)
    z['core_rank'] = rank_scores(z.core_score).astype(int)
    z['emerging_rank'] = rank_scores(z.emerging_score).astype(int)
    return z, q, context, cc, ec


def update_centers_and_transfer(papers, out):
    """Keep all downstream cosine labels consistent with the uniform paper labels."""
    sums = np.zeros((500, 1024), dtype=np.float64)
    train_sums = np.zeros_like(sums)
    valid_emb = None
    valid_labels = None
    counts = np.zeros(500, dtype=np.int64)
    for split, filename in SPLITS.items():
        ids = pd.read_parquet(ROOT / f'aaaa/data/{filename}.parquet', columns=['work_id']).work_id
        frame = papers.set_index('work_id').loc[ids]
        labels = frame.topic_id.to_numpy()
        allowed = (labels >= 0) & ~frame.is_retracted.fillna(False).to_numpy() & ~frame.template_record.fillna(False).to_numpy()
        vectors = np.load(ROOT / f'aaaa/bge_m3/models/bge_{split}.npy', mmap_mode='r')
        np.add.at(sums, labels[allowed], vectors[allowed])
        counts += np.bincount(labels[allowed], minlength=500)
        if split == 'train':
            np.add.at(train_sums, labels[allowed], vectors[allowed])
        if split == 'validation':
            valid_emb = np.asarray(vectors[allowed])
            valid_labels = labels[allowed]
    def normalize(x):
        return (x / np.maximum(np.linalg.norm(x, axis=1, keepdims=True), 1e-12)).astype(np.float32)
    centers = normalize(sums)
    train_centers = normalize(train_sums)
    active = np.flatnonzero(counts > 0)
    train_active = np.flatnonzero(np.linalg.norm(train_centers, axis=1) > 0)
    def nearest(emb, c, eligible):
        sim = np.asarray(emb) @ c[eligible].T
        order = np.argsort(-sim, axis=1, kind='stable')[:, :3]
        return eligible[order], np.take_along_axis(sim, order, axis=1)
    _, val_scores = nearest(valid_emb, train_centers, train_active)
    thresholds = {'cosine_p10': float(np.quantile(val_scores[:, 0], .1)), 'margin_p10': float(np.quantile(val_scores[:, 0]-val_scores[:, 1], .1)), 'calibration_documents': len(valid_labels), 'active_centers': len(active), 'calibration': 'uniform-NMF 2024 validation papers against uniform-NMF train-only centers; retrospective threshold, not transfer accuracy'}
    np.save(out / 'topic_centroids.npy', centers)
    np.save(out / 'train_centroids.npy', train_centers)
    dump(out / 'confidence_thresholds.json', thresholds)
    corpus = pd.read_parquet(ROOT / 'bbbb/data/model_corpus.parquet')
    mask = corpus.source.isin(['patent', 'policy']).to_numpy()
    vectors = np.load(ROOT / 'bbbb/models/embeddings.npy', mmap_mode='r')
    ids, scores = nearest(vectors[mask], centers, active)
    t = corpus.loc[mask, ['doc_id', 'source', 'title', 'date', 'split', 'origin', 'language', 'title_only']].reset_index(drop=True)
    for rank in range(3):
        t[f'topic_{rank+1}_id'] = ids[:, rank]
        t[f'topic_{rank+1}_cosine'] = scores[:, rank]
    t['top1_top2_margin'] = scores[:, 0]-scores[:, 1]
    t['low_cosine'] = scores[:, 0] < thresholds['cosine_p10']
    t['low_margin'] = t.top1_top2_margin < thresholds['margin_p10']
    t['needs_review'] = t.low_cosine | t.low_margin
    t.to_parquet(out / 'patent_policy_assignments.parquet', index=False)
    old = pd.read_parquet(NMF / 'patent_policy_assignments.parquet')[['doc_id', 'topic_1_id']]
    compare = t.merge(old, on='doc_id', suffixes=('', '_upstream'), validate='one_to_one')
    compare['label_changed'] = compare.topic_1_id.ne(compare.topic_1_id_upstream)
    audit = compare.groupby('source').agg(documents=('doc_id', 'size'), changed=('label_changed', 'sum'), changed_fraction=('label_changed', 'mean'), review_fraction=('needs_review', 'mean'), mean_cosine=('topic_1_cosine', 'mean')).reset_index()
    csv(audit, out / 'transfer_recalibration_audit.csv')
    return t


def transfer_metrics(tax, papers, out):
    t = pd.read_parquet(out / 'patent_policy_assignments.parquet')
    corpus = pd.read_parquet(ROOT / 'bbbb/data/model_corpus.parquet')
    t = t.merge(corpus[['doc_id', 'body', 'url', 'identity']], on='doc_id', validate='one_to_one')
    t['category_id'] = t.topic_1_id.map(lambda i: f'N{i + 1:04d}')
    t['date'] = pd.to_datetime(t.date, errors='coerce')
    t['within_cutoff'] = t.date.le('2026-06-30')
    t['in_recent_window'] = t.date.between('2025-07-01', '2026-06-30')
    t['in_policy_window'] = t.date.between('2023-07-01', '2026-06-30')
    t['assignment_status'] = np.where(t.needs_review, '低置信候选关联', '通过论文校准阈值的候选关联')
    t.to_parquet(out / 'transfer_evidence.parquet', index=False)
    z = tax[['topic_id', 'name', 'top_keywords']].copy()
    pwin = papers[papers.date.between('2025-07-01', '2026-06-30')]
    total_papers = len(pwin)
    z['recent_papers'] = pwin.groupby('category_id').size().reindex(z.index, fill_value=0)
    for scenario in ['all', 'confidence_filtered']:
        selected = t if scenario == 'all' else t[~t.needs_review]
        pats = selected[selected.source.eq('patent') & selected.in_recent_window]
        pols = selected[selected.source.eq('policy') & selected.in_policy_window]
        z[f'{scenario}_recent_patents'] = pats.groupby('category_id').size().reindex(z.index, fill_value=0)
        z[f'{scenario}_policy_documents'] = pols.groupby('category_id').size().reindex(z.index, fill_value=0)
        z[f'{scenario}_patent_paper_share_ratio'] = (
            (z[f'{scenario}_recent_patents'] + .5) / (len(pats) + .5 * len(tax))
            / ((z.recent_papers + .5) / (total_papers + .5 * len(tax)))
        )
        # Same Jan--May coverage in both sources, preserving their own denominators.
        pmay = pats[pats.date.between('2026-01-01', '2026-05-31')]
        wmay = pwin[pwin.date.between('2026-01-01', '2026-05-31')]
        n = pmay.groupby('category_id').size().reindex(z.index, fill_value=0)
        m = wmay.groupby('category_id').size().reindex(z.index, fill_value=0)
        z[f'{scenario}_may_share_ratio'] = (n + .5) / (len(pmay) + .5 * len(tax)) / ((m + .5) / (len(wmay) + .5 * len(tax)))
        z[f'{scenario}_may_patents'] = n
        z[f'{scenario}_may_papers'] = m
    z['patent_confident_retention'] = z.confidence_filtered_recent_patents / z.all_recent_patents.replace(0, np.nan)
    z['policy_confident_retention'] = z.confidence_filtered_policy_documents / z.all_policy_documents.replace(0, np.nan)
    pool = pd.Series(True, index=z.index)
    z['potential_signal_score'] = 100 * (
        .35 * percent(np.log1p(z.confidence_filtered_recent_patents), pool)
        + .30 * percent(np.log1p(z.confidence_filtered_policy_documents), pool)
        + .20 * percent(np.log(z.confidence_filtered_patent_paper_share_ratio), pool)
        + .15 * percent(np.log1p(z.recent_papers), pool)
    )
    z['potential_numeric_candidate'] = (
        z.recent_papers.ge(10) & z.confidence_filtered_recent_patents.ge(5)
        & z.confidence_filtered_policy_documents.ge(2)
        & z.confidence_filtered_patent_paper_share_ratio.ge(1.25)
        & z.confidence_filtered_may_share_ratio.ge(1.25)
        & z.confidence_filtered_may_patents.ge(2)
    )
    z['policy_task_support_verified'] = False
    z['applicant_diversity_verified'] = False
    z['interpretation'] = '跨来源数值信号；政策具体任务支持和专利主体多样性待审阅'
    csv(z.reset_index(), out / 'potential_metrics.csv')
    csv(z[z.potential_numeric_candidate].sort_values('potential_signal_score', ascending=False).reset_index(), out / 'potential_candidates.csv')
    return z, t


def safe_excel(sheets, path):
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        for name, frame in sheets.items():
            def clean(v):
                if isinstance(v, (list, dict, np.ndarray)):
                    v = json.dumps(list(v) if isinstance(v, np.ndarray) else v, ensure_ascii=False)
                if isinstance(v, str):
                    v = ILLEGAL_CHARACTERS_RE.sub('', v)[:32000]
                    if v.startswith(('=', '+', '-', '@')):
                        v = "'" + v
                return v
            frame.map(clean).to_excel(writer, sheet_name=name, index=False)
            ws = writer.sheets[name]
            ws.freeze_panes = 'C2'
            ws.auto_filter.ref = ws.dimensions
            for col in list(ws.columns)[:4]:
                ws.column_dimensions[col[0].column_letter].width = 28


def build(out):
    out.mkdir(parents=True, exist_ok=True)
    papers = prepare_papers(out)
    update_centers_and_transfer(papers, out)
    old = pd.read_parquet(NMF / 'paper_assignments.parquet')[['work_id', 'topic_id']]
    check = papers[['work_id', 'split', 'topic_id']].merge(old, on='work_id', suffixes=('', '_upstream'), validate='one_to_one')
    assignment_changes = check.assign(changed=check.topic_id.ne(check.topic_id_upstream)).groupby('split').changed.agg(['sum', 'mean']).reset_index()
    csv(assignment_changes, out / 'uniform_inference_changes.csv')
    base = papers[papers.topic_id.ge(0) & papers.date.le('2026-06-30') & ~papers.is_retracted.fillna(False) & ~papers.template_record.fillna(False)].copy()
    tax = taxonomy(base)
    z, q, ctx, cc, ec = calculate(base, tax)
    csv(tax.reset_index(), out / 'topic_catalog.csv')
    csv(q, out / 'quarter_counts.csv')
    csv(ctx.reset_index(), out / 'institution_citation_context.csv')
    csv(cc.rename_axis('category_id').reset_index(), out / 'core_components.csv')
    csv(ec.rename_axis('category_id').reset_index(), out / 'emerging_components.csv')
    variants = {
        'abstract_available': base[~base.title_only],
        'title_year_dedup': base.drop_duplicates(['title_key', 'year']),
        'exclude_jan1': base[base.date.dt.strftime('%m-%d').ne('01-01')],
    }
    sensitivities = []
    for name, frame in variants.items():
        zz, _, _, _, _ = calculate(frame, tax)
        z[f'{name}_core_candidate'] = zz.core_numeric_candidate
        z[f'{name}_emerging_candidate'] = zz.emerging_numeric_candidate
        z[f'{name}_multiyear_ratio'] = zz.multiyear_share_ratio
        z[f'{name}_yoy_ratio'] = zz.share_growth_ratio
        sensitivities.append({'scenario': name, 'papers': len(frame), 'core_candidates': int(zz.core_numeric_candidate.sum()), 'emerging_candidates': int(zz.emerging_numeric_candidate.sum()), 'core_rank_spearman': float(z.core_score.corr(zz.core_score, method='spearman')), 'emerging_rank_spearman': float(z.emerging_score.corr(zz.emerging_score, method='spearman'))})
    z['core_robust_candidate'] = z.core_numeric_candidate & z[[f'{n}_core_candidate' for n in variants]].all(axis=1)
    # The main strict count gates still apply; sensitivity checks demand direction persistence.
    z['emerging_robust_candidate'] = z.emerging_numeric_candidate & z[[f'{n}_{col}' for n in variants for col in ['multiyear_ratio', 'yoy_ratio']]].ge(1.1).all(axis=1)
    z['scope_review_status'] = '待主题与代表文献审阅'
    csv(z.reset_index(), out / 'hotspot_metrics.csv')
    for family in ['core', 'emerging']:
        csv(z[z[f'{family}_numeric_candidate']].sort_values(f'{family}_score', ascending=False).reset_index(), out / f'{family}_candidates.csv')
    pot, transfer = transfer_metrics(tax, base, out)
    sample_rows = []
    candidates = z.index[z.core_numeric_candidate | z.emerging_numeric_candidate].union(pot.index[pot.potential_numeric_candidate])
    for cid in candidates:
        group = base[base.category_id.eq(cid) & base.date.between('2025-07-01', '2026-06-30')]
        # Deterministic random examples, plus strongest assignment. Not a purity estimate.
        examples = pd.concat([group.sample(min(3, len(group)), random_state=17), group.nlargest(2, 'nmf_relative_margin')]).drop_duplicates('work_id')
        for r in examples.itertuples():
            sample_rows.append({'category_id': cid, 'name': tax.loc[cid, 'name'], 'source': 'paper', 'doc_id': r.work_id, 'date': str(r.date.date()), 'title': r.clean_title, 'text_excerpt': r.clean_abstract[:2500], 'confidence': r.nmf_relative_margin, 'needs_review': True})
        for source in ['patent', 'policy']:
            group = transfer[transfer.category_id.eq(cid) & transfer.source.eq(source) & ~transfer.needs_review & (transfer.in_recent_window if source == 'patent' else transfer.in_policy_window)]
            for r in group.nlargest(3, 'topic_1_cosine').itertuples():
                sample_rows.append({'category_id': cid, 'name': tax.loc[cid, 'name'], 'source': source, 'doc_id': r.doc_id, 'date': str(r.date.date()), 'title': r.title, 'text_excerpt': str(r.body)[:2500], 'confidence': r.topic_1_cosine, 'needs_review': r.needs_review})
    examples = pd.DataFrame(sample_rows)
    csv(examples, out / 'candidate_evidence.csv')
    sensitivity = pd.DataFrame(sensitivities)
    csv(sensitivity, out / 'sensitivity.csv')
    coverage = papers.groupby(['split', 'year']).agg(documents=('work_id', 'size'), metadata_fraction=('metadata_matched', 'mean'), title_only_fraction=('title_only', 'mean')).reset_index()
    csv(coverage, out / 'coverage_audit.csv')
    summary = {'topic_count': len(tax), 'input_papers': len(papers), 'eligible_papers': len(base), 'input_transfer_documents': len(transfer), 'core_numeric_candidates': int(z.core_numeric_candidate.sum()), 'core_robust_candidates': int(z.core_robust_candidate.sum()), 'emerging_numeric_candidates': int(z.emerging_numeric_candidate.sum()), 'emerging_robust_candidates': int(z.emerging_robust_candidate.sum()), 'potential_numeric_candidates': int(pot.potential_numeric_candidate.sum()), 'cutoff': '2026-06-30', 'scope': '冻结抽样语料的数值候选，非全量512万条记录结果', 'maturity_inferred_from_hotspots': False}
    dump(out / 'SUMMARY.json', summary)
    method = {'version': 'nmf500-sample-v1', 'paper_labels': 'fixed H model.transform on all splits; same transform_max_iter=200, tol=1e-4; no training W used', 'normalization': 'source-specific observed sample denominators; yearly shares; no extrapolated full-corpus counts', 'windows': {'core': ['2023-07-01', '2026-06-30'], 'recent': ['2025-07-01', '2026-06-30'], 'baseline': ['2022-07-01', '2025-06-30'], 'history': ['2021-07-01', '2026-06-30']}, 'core_thresholds': {'annual_mean_min': 60, 'recent_min': 50, 'quarter_activity_min': 5, 'each_year_min': 30, 'active_quarters_min': 9, 'yoy_min': .8}, 'emerging_thresholds': {**EMERGING_GATES, 'multiyear_ratio_min': 1.25, 'yoy_min': 1.15, 'growing_quarters_min': 3, 'historical_peak_min': 1.05, 'lower95_min': 1.05, 'BH_q_max': .05}, 'threshold_basis': 'Exploratory minimum observed sample support; frozen before examining rankings. Different from full-corpus 750-topic absolute-count gates.', 'citation': 'current snapshot cumulative citation, within publication-year sample percentile; not forward forecast', 'institutions': 'normalized observed names; sample breadth is not total institution count', 'potential': 'confidence-filtered cosine candidate association; no automatic policy task endorsement; patent/paper ratios use same temporal windows and separate source denominators', 'quality_limits': ['sample source selection and unequal within-year coverage', 'label ambiguity', 'policy domain shift', 'count-only screening intervals do not model serial dependence', 'shared trained model makes retrospective trends descriptive'], 'semantic_review': 'new NMF IDs have no inherited 750-topic review approvals'}
    dump(out / 'METHOD.json', method)
    def table(family):
        f = z[z[f'{family}_numeric_candidate']].sort_values(f'{family}_score', ascending=False).head(15)
        return f.reset_index()[['category_id', 'name', f'{family}_score', 'recent_papers', 'multiyear_share_ratio', f'{family}_robust_candidate']].to_markdown(index=False)
    report = f'''# 500主题样本版热点重算

截止2026-06-30；输入{len(papers):,}篇论文，清理后{len(base):,}篇；专利/政策共{len(transfer):,}条。新分类覆盖当前冻结样本。全部时间段统一使用固定NMF组件推断，增长按各期样本背景份额归一化。

核心数值候选{summary['core_numeric_candidates']}个，三种数据过滤均通过{summary['core_robust_candidates']}个；新兴数值候选{summary['emerging_numeric_candidates']}个，方向稳健{summary['emerging_robust_candidates']}个；潜在跨来源数值候选{summary['potential_numeric_candidates']}个。候选均保留主题范围与证据待审阅状态。

## 核心候选

{table('core')}

## 新兴候选

{table('emerging')}

## 潜在候选

{pot[pot.potential_numeric_candidate].sort_values('potential_signal_score', ascending=False).reset_index()[['category_id', 'name', 'confidence_filtered_recent_patents', 'confidence_filtered_policy_documents', 'confidence_filtered_patent_paper_share_ratio']].to_markdown(index=False)}

跨来源余弦关联仅用于线索筛选。政策是否支持同一具体任务、专利申请主体多样性仍需核读；当前不声称已满足原750版应用任务级潜在热点证据门槛。

## 敏感性

{sensitivity.to_markdown(index=False)}

抽样论文每年规模为8,000或12,000，因此采用样本支持门槛，详见METHOD.json；计数没有外推为全量规模。模型训练与回放之间标签生成方式的差异已修正，变动见uniform_inference_changes.csv。历史比较属回溯描述；当前引用快照不是历史时点已知引用。
'''
    (out / 'REPORT.md').write_text(report)
    safe_excel({'方法与范围': pd.DataFrame([{'item': k, 'value': v} for k, v in summary.items()]), '500主题目录': tax.reset_index(), '全部主题指标': z.reset_index(), '核心候选': z[z.core_numeric_candidate].sort_values('core_score', ascending=False).reset_index(), '新兴候选': z[z.emerging_numeric_candidate].sort_values('emerging_score', ascending=False).reset_index(), '潜在候选': pot[pot.potential_numeric_candidate].sort_values('potential_signal_score', ascending=False).reset_index(), '潜在全部指标': pot.reset_index(), '代表证据': examples, '敏感性': sensitivity, '样本覆盖': coverage}, out / '500主题核心新兴潜在热点.xlsx')
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    with threadpool_limits(2):
        build(args.output.resolve())
