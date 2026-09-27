"""Full-population diagnostics. Never reuse sample counts or semantic approvals."""
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
from energy_hotspots.scoring import score,gates,windows,percent,rank_scores,ordered_scores,ranking_key,CORE_WEIGHTS,EMERGING_WEIGHTS

POTENTIAL_WEIGHTS={'patents':.35,'policies':.30,'relative_share':.20,'papers':.15}
POTENTIAL_GATES={'papers':100,'patents':25,'policies':2,'relative':1.25}


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def compare(a,b):
    k=min(20,len(a))
    topa=set(ordered_scores(a).head(k).index);topb=set(ordered_scores(b).head(k).index)
    correlation=float(ranking_key(a).corr(ranking_key(b),method='spearman')) if ranking_key(a).nunique()>1 and ranking_key(b).nunique()>1 else np.nan
    return {'spearman':correlation,
        'top20_overlap':len(topa&topb)/k,'max_rank_shift':float((rank_scores(a)-rank_scores(b)).abs().max())}


def reweight(c,w):
    weights=pd.Series(w,dtype=float).reindex(c.columns)
    if weights.isna().any() or (weights<0).any() or weights.sum()<=0:raise ValueError('Invalid weights')
    return 100*c.dot(weights/weights.sum())


def potential(papers,transfer,index,low='2026-01-01',high='2026-06-30',cosine=-1.,margin=0.,remove=None):
    t=transfer[transfer.date.between(low,high)&transfer.topic_1_cosine.ge(cosine)&transfer.top1_top2_margin.ge(margin)]
    if remove:t=t[t.source.ne(remove)]
    z=pd.DataFrame(index=index)
    z['papers']=papers[papers.date.between(low,high)].groupby('category_id').size().reindex(index,fill_value=0)
    if remove=='paper':z['papers']=0
    for source in ['patent','policy']:
        z['patents' if source=='patent' else 'policies']=t[t.source.eq(source)].groupby('category_id').size().reindex(index,fill_value=0)
    z['relative']=(z.patents+.5)/(z.patents.sum()+.5*len(z))/((z.papers+.5)/(z.papers.sum()+.5*len(z)))
    return z


def potential_components(z):
    pool=pd.Series(True,index=z.index)
    return pd.DataFrame({'patents':percent(np.log1p(z.patents),pool),'policies':percent(np.log1p(z.policies),pool),
        'relative_share':percent(np.log(z.relative),pool),'papers':percent(np.log1p(z.papers),pool)})


def potential_gates(z,overrides=None):
    p={**POTENTIAL_GATES,**(overrides or {})}
    return pd.DataFrame({key:z[key].ge(value) for key,value in p.items()})


def aggregate(con,tax,condition):
    """Recompute counts, institution sets and citation cohorts after each filter."""
    con.execute('CREATE OR REPLACE TEMP VIEW selected AS SELECT * FROM papers WHERE '+condition)
    q=con.sql("SELECT category_id,concat(year(date),'Q',quarter(date)) period,count(*) papers FROM selected WHERE date>='2021-07-01' GROUP BY ALL").df()
    grid=pd.MultiIndex.from_product([tax.index,pd.period_range('2021Q3','2026Q2',freq='Q').astype(str)],names=['category_id','period'])
    q=q.set_index(['category_id','period']).reindex(grid,fill_value=0).reset_index()
    con.execute("""CREATE OR REPLACE TEMP TABLE institution_rows AS
        SELECT category_id,date,lower(trim(unnest(string_split(coalesce(institutions,''),';')))) institution
        FROM selected WHERE date>='2021-07-01'""")
    ctx=pd.DataFrame(index=tax.index)
    def institutions(lo,hi):
        f=con.sql(f"SELECT category_id,count(DISTINCT institution) n FROM institution_rows WHERE institution NOT IN ('','none','nan','[]') AND date BETWEEN '{lo}' AND '{hi}' GROUP BY ALL").df()
        return f.set_index('category_id').n.reindex(tax.index,fill_value=0)
    ws=windows()
    for i,w in enumerate(ws):ctx[f'year{i}_institutions']=institutions(pd.Period(w[0]).start_time.date(),pd.Period(w[-1]).end_time.date())
    ctx['recent_institutions']=ctx.year0_institutions
    for years in [1,3,5]:ctx[f'core_institutions_{years}y']=institutions(pd.Period(ws[years-1][0]).start_time.date(),'2026-06-30')
    cites=con.sql("""WITH ranked AS (SELECT category_id,coalesce(cited_by_count,0) c,
        percent_rank() OVER(PARTITION BY year(date) ORDER BY coalesce(cited_by_count,0)) pc FROM selected WHERE year(date) BETWEEN 2023 AND 2025)
        SELECT category_id,avg(CASE WHEN c=0 THEN 0 ELSE pc END) pc FROM ranked GROUP BY ALL""").df()
    ctx['citation_cohort_percentile']=cites.set_index('category_id').pc.reindex(tax.index,fill_value=0)
    return q,ctx


def run(source,inp,out,draws=1500):
    if draws<1:raise ValueError('Positive perturbation count required')
    complete=json.loads((source/'COMPLETE.json').read_text())
    summary=json.loads((source/'SUMMARY.json').read_text())
    if complete['summary_sha256']!=sha(source/'SUMMARY.json') or complete['validation_sha256']!=sha(source/'VALIDATION.json'):
        raise ValueError('Classification hash mismatch')
    if not json.loads((source/'VALIDATION.json').read_text()).get('passed') or not all(summary[k] for k in ['full_training','full_inference','full_transfer']):
        raise ValueError('Completed full classification required')
    hs=json.loads((inp/'SUMMARY.json').read_text())
    if hs['classification_summary_sha256']!=complete['summary_sha256']:raise ValueError('Mismatched hotspot taxonomy')
    manifest=json.loads((source/'ASSIGNMENTS_MANIFEST.json').read_text())
    if sha(source/'ASSIGNMENTS_MANIFEST.json')!=summary['assignments_manifest_sha256']:raise ValueError('Manifest changed')
    files=sorted((source/'assignments').glob('*.parquet'))
    if {p.name for p in files}!=set(manifest['files']) or any(sha(p)!=manifest['files'][p.name] for p in files):raise ValueError('Assignment files changed')
    out.mkdir(parents=True,exist_ok=True)
    read=lambda n:pd.read_csv(inp/(n+'.csv'),float_precision='round_trip').set_index('category_id')
    tax,q,ctx=read('topic_catalog'),pd.read_csv(inp/'quarter_counts.csv'),read('institution_citation_context')
    baseline,cc,ec=score(tax,q,ctx)
    saved=read('hotspot_metrics')
    for f in ['core','emerging']:
        np.testing.assert_allclose(baseline[f+'_score'],saved[f+'_score'],atol=1e-9)
        if not gates(baseline,f).drop(columns='scope').all(axis=1).equals(saved[f+'_numeric_candidate']):raise ValueError('Baseline gates do not replay')
    con=duckdb.connect();con.execute("SET threads=2; SET memory_limit='6GB'")
    con.execute(f"SET temp_directory='{out}/spill'")
    con.execute(f"CREATE VIEW labels AS SELECT *,try_cast(date AS DATE) observation_date FROM read_parquet('{source}/assignments/*.parquet')")
    population=con.sql('SELECT count(*) FROM labels').fetchone()[0]
    if population!=summary['population_records']:raise ValueError('Population mismatch')
    con.execute(f"ATTACH '{ROOT}/analyze/data/independent_corpus.duckdb' AS metadata (READ_ONLY)")
    con.execute("""CREATE TABLE papers AS SELECT l.category_id,l.observation_date date,l.title_only,l.nmf_relative_margin,
        w.institutions,w.cited_by_count FROM labels l JOIN metadata.works w ON replace(l.doc_id,'paper:','')=w.work_id
        WHERE l.source='paper' AND l.topic_id>=0 AND l.usable AND NOT l.retracted AND NOT l.template_record AND l.observation_date<='2026-06-30'""")
    expected_papers=con.sql("SELECT count(*) FROM labels WHERE source='paper' AND topic_id>=0 AND usable AND NOT retracted AND NOT template_record AND observation_date<='2026-06-30'").fetchone()[0]
    if con.sql('SELECT count(*) FROM papers').fetchone()[0]!=expected_papers:raise ValueError('Paper metadata join lost or duplicated records')
    paper_dates=con.sql('SELECT category_id,date FROM papers').df();paper_dates['date']=pd.to_datetime(paper_dates.date)
    transfer=con.sql("SELECT doc_id,category_id,source,observation_date date,topic_1_cosine,top1_top2_margin FROM labels WHERE source!='paper' AND topic_id>=0").df()
    transfer['date']=pd.to_datetime(transfer.date)
    pot=potential(paper_dates,transfer,tax.index);pc=potential_components(pot)
    pot['numeric_candidate']=potential_gates(pot).all(axis=1);pot['semantic_approval']=False
    pot.rename_axis('category_id').reset_index().to_csv(out/'potential_association_baseline.csv',index=False)
    comps={'core':cc,'emerging':ec,'potential_association':pc}
    weights={'core':CORE_WEIGHTS,'emerging':EMERGING_WEIGHTS,'potential_association':POTENTIAL_WEIGHTS}
    bg={'core':gates(baseline,'core').drop(columns='scope'),'emerging':gates(baseline,'emerging').drop(columns='scope'),'potential_association':potential_gates(pot)}
    masks={f:g.all(axis=1) for f,g in bg.items()};values={f:reweight(c,weights[f]) for f,c in comps.items()}
    scenarios=[];members=[];perturbations=[];intervals=[]
    def record(f,kind,name,scores,mask):
        origin=masks[f];union=(origin|mask).sum()
        scenarios.append({'family':f,'kind':kind,'scenario':name,**compare(values[f],scores),
            'numeric_candidates':int(mask.sum()),'baseline_retained':int((origin&mask).sum()),
            'candidate_jaccard':float((origin&mask).sum()/union) if union else 1.,'semantic_approvals':0})
        for cid in tax.index:members.append({'family':f,'kind':kind,'scenario':name,'category_id':cid,
            'numeric_pass':bool(mask.loc[cid]),'baseline_pass':bool(origin.loc[cid]),'score':float(scores.loc[cid]),'needs_review':True})
    rng=np.random.default_rng(20260926)
    for f,c in comps.items():
        record(f,'baseline','full_population',values[f],masks[f])
        for omit in c:
            w={**weights[f],omit:0.};record(f,'score_component_ablation','without_'+omit,reweight(c,w),masks[f])
        ranks=[]
        for trial in range(draws):
            w=pd.Series(weights[f])*rng.uniform(.8,1.2,len(c.columns));w/=w.sum()
            s=reweight(c,w);ranks.append(rank_scores(s).to_numpy())
            perturbations.append({'family':f,'trial':trial,**compare(values[f],s),**{'weight_'+k:float(v) for k,v in w.items()}})
        r=np.asarray(ranks);base_r=rank_scores(values[f])
        for i,cid in enumerate(tax.index):intervals.append({'family':f,'category_id':cid,'baseline_rank':float(base_r[cid]),
            'rank_p025':float(np.quantile(r[:,i],.025)),'rank_median':float(np.median(r[:,i])),
            'rank_p975':float(np.quantile(r[:,i],.975)),'top20_fraction':float((r[:,i]<=20).mean())})
        for gate in bg[f]:record(f,'gate_ablation','without_'+gate,values[f],bg[f].drop(columns=gate).all(axis=1))
    grids={'core':{'annual_volume':[200,300],'current_volume':[200,300],'year_fraction':[.67,1.],
        'quarter_fraction':[.5,1.],'current_share':[.7,.9]},'emerging':{'volume':[80,120],'baseline':[40,60],
        'multiyear':[1.15,1.35],'recent_growth':[1.05,1.25],'quarters':[2,4],'peak':[1.,1.15],
        'lower95':[1.,1.15],'qvalue':[.01,.1],'trend':[-.01,.01]}}
    for f,grid in grids.items():
        for key,vs in grid.items():
            for v in vs:record(f,'threshold_one_at_time',f'{key}={v}',values[f],gates(baseline,f,{key:v}).drop(columns='scope').all(axis=1))
        for factor in [.8,1.2]:
            z,_,_=score(tax,q,ctx,activity_quarter_min=25*factor,active_year_min=150*factor)
            params={k:v*factor for k,v in ({'annual_volume':250,'current_volume':250} if f=='core' else {'volume':100,'baseline':50}).items()}
            record(f,'threshold_joint',f'counts_x{factor}',z[f+'_score'],gates(z,f,params).drop(columns='scope').all(axis=1))
    for years in [1,5]:
        z,_,_=score(tax,q,ctx,core_years=years);record('core','window',f'core_{years}y',z.core_score,gates(z,'core').drop(columns='scope').all(axis=1))
    for years,omit in [(2,None),(4,None),(3,1),(3,2),(3,3)]:
        z,_,_=score(tax,q,ctx,baseline_years=years,omit_baseline=omit)
        record('emerging','window',f'background_{years}y_omit_{omit}',z.emerging_score,gates(z,'emerging').drop(columns='scope').all(axis=1))
    filter_counts=[]
    for name,condition in [('baseline','TRUE'),('exclude_title_only','NOT title_only'),
        ('paper_margin_0025','nmf_relative_margin>=0.025'),('paper_margin_005','nmf_relative_margin>=0.05'),('paper_margin_010','nmf_relative_margin>=0.10')]:
        qq,ct=aggregate(con,tax,condition)
        filter_counts.append({'scenario':name,'papers':con.sql('SELECT count(*) FROM selected').fetchone()[0],
            'quarter_papers':int(qq.papers.sum())})
        # A filter removing an entire quarter cannot yield a valid trend estimate.
        if qq.groupby('period').papers.sum().le(0).any():raise ValueError('Data filter has an empty background quarter: '+name)
        z,_,_=score(tax,qq,ct)
        if name=='baseline':
            for f in ['core','emerging']:np.testing.assert_allclose(z[f+'_score'],values[f],atol=1e-9)
        for f in ['core','emerging']:record(f,'data_filter',name,z[f+'_score'],gates(z,f).drop(columns='scope').all(axis=1))
        qq.to_csv(out/(name+'_quarter_counts.csv'),index=False)
        ct.rename_axis('category_id').reset_index().to_csv(out/(name+'_context.csv'),index=False)
    for key,default in POTENTIAL_GATES.items():
        for factor in [.8,1.2]:record('potential_association','threshold_one_at_time',f'{key}_x{factor}',values['potential_association'],potential_gates(pot,{key:default*factor}).all(axis=1))
    for cosine in [-1.,.5,.6,.7]:
        for margin in [0.,.01,.02,.05]:
            z=potential(paper_dates,transfer,tax.index,cosine=cosine,margin=margin)
            record('potential_association','transfer_filter',f'cosine_{cosine}_margin_{margin}',reweight(potential_components(z),POTENTIAL_WEIGHTS),potential_gates(z).all(axis=1))
    for source_name in ['paper','patent','policy']:
        z=potential(paper_dates,transfer,tax.index,remove=source_name)
        record('potential_association','source_ablation','without_'+source_name,reweight(potential_components(z),POTENTIAL_WEIGHTS),potential_gates(z).all(axis=1))
    for high in ['2026-03-31','2026-05-31']:
        z=potential(paper_dates,transfer,tax.index,high=high)
        record('potential_association','aligned_window','2026-01-01_to_'+high,reweight(potential_components(z),POTENTIAL_WEIGHTS),potential_gates(z).all(axis=1))
    policies=transfer[transfer.source.eq('policy')&transfer.date.between('2026-01-01','2026-06-30')]
    loo=[]
    for row in policies.itertuples():
        z=pot.loc[[row.category_id],list(POTENTIAL_GATES)].copy();z['policies']-=1
        loo.append({'doc_id':row.doc_id,'category_id':row.category_id,'remaining_policy_documents':int(z.policies.iloc[0]),
            'numeric_pass_after_removal':bool(potential_gates(z).all(axis=1).iloc[0]),'independent_policy_family_test':False})
    frames={'scenarios':pd.DataFrame(scenarios),'scenario_memberships':pd.DataFrame(members),
        'weight_draws':pd.DataFrame(perturbations),'rank_intervals':pd.DataFrame(intervals),'data_filter_counts':pd.DataFrame(filter_counts),
        'policy_document_loo':pd.DataFrame(loo,columns=['doc_id','category_id','remaining_policy_documents','numeric_pass_after_removal','independent_policy_family_test'])}
    for name,f in frames.items():f.to_csv(out/(name+'.csv'),index=False)
    frames['weight_draws'].groupby('family')[['spearman','top20_overlap','max_rank_shift']].agg(['min','median','max']).to_csv(out/'weight_summary.csv')
    protocol={'full_population_records':population,'classification_summary_sha256':complete['summary_sha256'],
        'topics':len(tax),'seed':20260926,'draws_per_family':draws,'families':list(comps),'scenarios':len(scenarios),
        'full_count_thresholds':True,'baseline_replay_passed':True,'sample_rows_or_quotas_used':False,
        'data_filters_recompute_institutions_citations_and_denominators':True,'semantic_approvals_inherited':False,
        'potential_association_gates':POTENTIAL_GATES,'potential_gates_calibrated':False,
        'limits':['Descriptive fixed-model sensitivity; not refitting NMF or an independent temporal validation.',
            'Intervals are perturbation ranges, not statistical confidence intervals. No semantic accuracy measured.',
            'Potential associations are exploratory numeric leads, not verified same-task policy support or applicant diversity.',
            'No independent policy-family annotations for the new taxonomy; document LOO is not family LOO.',
            'Time-window tests hold the 2023-2025 citation cohort fixed; data-filter tests recompute that cohort.',
            'TRL/CRL evidence remains bounded to reviewed objects; full classification does not create maturity evidence.'],
        'input_sha256':{p.name:sha(p) for p in inp.glob('*.csv')}}
    (out/'PROTOCOL.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n')
    (out/'REPORT.md').write_text('# 全量主题消融与灵敏度实验\n\n'+json.dumps(protocol,ensure_ascii=False,indent=2)+
        '\n\n本次重新读取全部分类记录，使用全量数量门槛；不复用样本版实验结果或人工审核。'
        '核心／新兴分析包括评分、门槛、权重、时间窗口和文本质量／贡献差距过滤。跨来源关联包括来源消融、余弦／间隔网格、共同日期窗口和政策文档留一。'
        '潜在关联仅为待核验线索，政策族独立性与申请人多样性未取得证据，不能声称已完成这两项检验。\n')
    marker={'passed':True,'classification_summary_sha256':complete['summary_sha256'],
        'files':{p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='COMPLETE.json'}}
    (out/'COMPLETE.json').write_text(json.dumps(marker,indent=2)+'\n')
    con.close();print(json.dumps(protocol,ensure_ascii=False),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--classification',type=Path,required=True);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--draws',type=int,default=1500);a=p.parse_args()
    run(a.classification,a.input,a.output,a.draws)
