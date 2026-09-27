"""Full-corpus hotspot summaries from the completed classification contract."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import duckdb
import numpy as np
import pandas as pd

REPO=Path(__file__).resolve().parents[2]
ROOT=REPO.parent
sys.path.insert(0,str(REPO/'src'))
from energy_hotspots.scoring import score, gates, windows, rank_scores


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()


def build(source,out):
    complete=json.loads((source/'COMPLETE.json').read_text())
    if complete['summary_sha256']!=sha(source/'SUMMARY.json') or complete['validation_sha256']!=sha(source/'VALIDATION.json'):
        raise ValueError('Full classification completion hash mismatch')
    summary=json.loads((source/'SUMMARY.json').read_text())
    if not all(summary[k] for k in ['full_training','full_inference','full_transfer']):
        raise ValueError('Full classification required')
    if not json.loads((source/'VALIDATION.json').read_text()).get('passed'):
        raise ValueError('Classification validation failed')
    if summary['assignments_manifest_sha256']!=sha(source/'ASSIGNMENTS_MANIFEST.json'):
        raise ValueError('Assignments manifest hash mismatch')
    manifest=json.loads((source/'ASSIGNMENTS_MANIFEST.json').read_text())
    if set(manifest['files'])!={p.name for p in (source/'assignments').glob('*.parquet')}:
        raise ValueError('Assignments file inventory mismatch')
    for name,digest in manifest['files'].items():
        if sha(source/'assignments'/name)!=digest:
            raise ValueError('Assignment hash mismatch: '+name)
    out.mkdir(parents=True,exist_ok=True)
    con=duckdb.connect();con.execute("SET threads=4; SET memory_limit='8GB'")
    db=ROOT/'analyze/data/independent_corpus.duckdb'
    con.execute(f"ATTACH '{db}' AS metadata (READ_ONLY)")
    con.execute(f"CREATE VIEW labels AS SELECT *,try_cast(date AS DATE) observation_date FROM read_parquet('{source}/assignments/*.parquet')")
    con.execute("""CREATE TABLE papers AS SELECT l.row_id,l.doc_id,l.category_id,l.topic_id,
       l.observation_date AS date,w.institutions,w.cited_by_count,year(l.observation_date) AS year
       FROM labels l JOIN metadata.works w ON replace(l.doc_id,'paper:','')=w.work_id
       WHERE l.source='paper' AND l.topic_id>=0 AND NOT l.retracted AND NOT l.template_record
       AND l.usable AND l.observation_date<='2026-06-30'""")
    tax=pd.read_csv(source/'topic_catalog.csv').set_index('category_id')
    periods=pd.period_range('2021Q3','2026Q2',freq='Q').astype(str)
    counts=con.sql("SELECT category_id,concat(year(date),'Q',quarter(date)) period,count(*) papers FROM papers WHERE date>='2021-07-01' GROUP BY ALL").df()
    grid=pd.MultiIndex.from_product([tax.index,periods],names=['category_id','period'])
    q=counts.set_index(['category_id','period']).reindex(grid,fill_value=0).reset_index()
    context=pd.DataFrame(index=tax.index)
    con.execute("""CREATE TABLE institutions AS SELECT category_id,date,lower(trim(unnest(string_split(coalesce(institutions,''),';')))) institution
        FROM papers WHERE date>='2021-07-01'""")
    con.execute("DELETE FROM institutions WHERE institution IN ('','none','nan','[]')")
    ws=windows()
    def inst_count(low,high):
        x=con.sql(f"SELECT category_id,count(DISTINCT institution) n FROM institutions WHERE date BETWEEN '{low}' AND '{high}' GROUP BY ALL").df().set_index('category_id').n
        return x.reindex(tax.index,fill_value=0)
    for i,w in enumerate(ws):
        context[f'year{i}_institutions']=inst_count(str(pd.Period(w[0]).start_time.date()),str(pd.Period(w[-1]).end_time.date()))
    context['recent_institutions']=context.year0_institutions
    for years in [1,3,5]:
        context[f'core_institutions_{years}y']=inst_count(str(pd.Period(ws[years-1][0]).start_time.date()),'2026-06-30')
    cites=con.sql("""WITH ranked AS (SELECT category_id,coalesce(cited_by_count,0) c,
       percent_rank() OVER(PARTITION BY year ORDER BY coalesce(cited_by_count,0)) pc FROM papers WHERE year BETWEEN 2023 AND 2025)
       SELECT category_id,avg(CASE WHEN c=0 THEN 0 ELSE pc END) pc FROM ranked GROUP BY ALL""").df().set_index('category_id').pc
    context['citation_cohort_percentile']=cites.reindex(tax.index,fill_value=0)
    z,cc,ec=score(tax,q,context,activity_quarter_min=25,active_year_min=150)
    for family in ['core','emerging']:
        gg=gates(z,family).drop(columns='scope')
        z[family+'_numeric_candidate']=gg.all(axis=1)
        z[family+'_failed_gates']=gg.apply(lambda r:' | '.join(r.index[~r]),axis=1)
        z[family+'_rank']=rank_scores(z[family+'_score']).astype(int)
        z[family+'_scope_approved']=False
    z['review_status']='full-corpus numeric candidates; new taxonomy scope review pending'
    # Source windows are aligned for cross-source shares; 2026-only patents cannot prove long-term emergence.
    trans=con.sql("""SELECT category_id,source,count(*) records,
       count(*) FILTER(WHERE observation_date BETWEEN '2026-01-01' AND '2026-06-30') first_half_2026,
       avg(topic_1_cosine) mean_cosine FROM labels WHERE source!='paper' AND topic_id>=0 GROUP BY ALL""").df()
    signals=tax[['topic_id','name']].copy()
    for src in ['patent','policy']:
        f=trans[trans.source.eq(src)].set_index('category_id')
        for c in ['records','first_half_2026','mean_cosine']:
            signals[src+'_'+c]=f[c].reindex(tax.index,fill_value=0)
    pn=con.sql("SELECT category_id,count(*) n FROM papers WHERE date BETWEEN '2026-01-01' AND '2026-06-30' GROUP BY ALL").df().set_index('category_id').n
    signals['papers_first_half_2026']=pn.reindex(tax.index,fill_value=0)
    a=signals.patent_first_half_2026; b=signals.papers_first_half_2026
    signals['patent_paper_share_ratio_2026H1']=((a+.5)/(a.sum()+.5*len(tax)))/((b+.5)/(b.sum()+.5*len(tax)))
    signals['policy_task_support_verified']=False
    signals['applicant_diversity_verified']=False
    signals['interpretation']='Full source association counts; policy task support and applicant diversity unverified'
    for name,f in [('topic_catalog',tax),('hotspot_metrics',z),('core_components',cc),('emerging_components',ec),('institution_citation_context',context),('cross_source_signals',signals)]:
        f.rename_axis('category_id').reset_index().to_csv(out/(name+'.csv'),index=False)
    q.to_csv(out/'quarter_counts.csv',index=False)
    trans.to_csv(out/'transfer_source_summary.csv',index=False)
    con.sql("SELECT source,count(*) records,count(*) FILTER(WHERE topic_id>=0) assigned_records FROM labels GROUP BY ALL").df().to_csv(out/'coverage.csv',index=False)
    counts_all=con.sql('SELECT count(*) FROM labels').fetchone()[0]
    if counts_all!=summary['population_records']:
        raise ValueError('Not all source records reached downstream')
    stats={'classification_input_records':counts_all,'papers_used_for_hotspot_windows':con.sql('SELECT count(*) FROM papers').fetchone()[0],
        'core_numeric_candidates':int(z.core_numeric_candidate.sum()),'emerging_numeric_candidates':int(z.emerging_numeric_candidate.sum()),
        'cutoff':'2026-06-30','classification_summary_sha256':sha(source/'SUMMARY.json'),'full_count_thresholds':True,
        'semantic_approvals_inherited':False,'potential_hotspots_verified':False,'training_used_future_years_relative_to_historical_windows':True}
    (out/'SUMMARY.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n')
    (out/'REPORT.md').write_text(f"# 全量NMF主题热点计算\n\n输入覆盖{counts_all:,}条冻结记录；核心数值候选{stats['core_numeric_candidates']}个，新兴数值候选{stats['emerging_numeric_candidates']}个。\n\n采用全量数量门槛，季度计数来自论文。范围审核未完成，数值候选尚未确认为热点。专利与论文份额采用共同2026年上半年窗口；政策相似关联不等于同任务支持。全量模型用到全部年份，因此历史趋势为回溯描述。\n")
    print(json.dumps(stats,ensure_ascii=False),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--classification',type=Path,default=ROOT/'energy-topic-identification/work/full_nmf500_20260926');p.add_argument('--output',type=Path,default=REPO/'outputs/full_nmf500_20260926');a=p.parse_args();build(a.classification,a.output)
