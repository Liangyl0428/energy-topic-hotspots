"""Frozen raw papers -> history counts and context for each scope/time cutoff."""
from common import *
import duckdb,pandas as pd
from multiyear_scoring import windows
OUT=BASE/'data/multiyear';OUT.mkdir(exist_ok=True)
c=duckdb.connect();c.execute('SET threads=4');c.execute("SET memory_limit='6GB'");c.execute('SET temp_directory='+sqlstr(BASE/'data/tmp'))
c.from_parquet(str(BASE/'data/assignments/*.parquet')).create_view('a')
c.execute('ATTACH '+sqlstr(ROOT/'analyze/data/independent_corpus.duckdb')+' AS metadata (READ_ONLY)')
c.execute("""CREATE TEMP TABLE p AS SELECT a.row_id,a.doc_id,a.category_id,try_cast(a.date AS DATE) date,
 a.title_only,a.needs_review,a.eligible_for_supported_analysis,a.cosine_to_centroid,a.distance_margin,
 coalesce(w.institutions,'') institutions,coalesce(w.cited_by_count,0) cited_by_count,w.work_id IS NOT NULL metadata_matched,
 regexp_replace(lower(coalesce(a.title,w.title,'')), '[^\\p{L}\\p{N}]','','g') title_key
 FROM a LEFT JOIN metadata.works w ON substr(a.doc_id,7)=w.work_id
 WHERE a.source='paper' AND a.category_index>=0 AND NOT a.retracted AND NOT a.template_record
 AND a.date BETWEEN '2020-01-01' AND '2026-08-31'""")
coverage=c.execute("""SELECT year(date) AS publication_year,count(*) papers,count(DISTINCT month(date)) observed_months,avg(CAST(title_only AS INT)) title_only_fraction,avg(CAST(strftime(date,'%m-%d')='01-01' AS INT)) jan1_proxy_fraction,avg(CAST(metadata_matched AS INT)) metadata_match_fraction,avg(CAST(institutions<>'' AS INT)) institution_metadata_fraction FROM p GROUP BY 1 ORDER BY 1""").df();save(coverage,'multiyear_coverage_audit.csv')
c.execute("""CREATE TEMP TABLE dedup_ids AS SELECT row_id FROM p QUALIFY row_number() OVER(PARTITION BY CASE WHEN length(title_key)>=15 THEN title_key||year(date)::varchar ELSE doc_id END ORDER BY date,row_id)=1""")
scopes={'main':'TRUE','quality':"NOT title_only AND strftime(date,'%m-%d')<>'01-01'",'geometry':'cosine_to_centroid>=0.45 AND distance_margin>=0.02','dedup':'row_id IN (SELECT row_id FROM dedup_ids)','exclude_needs_review':'NOT needs_review','supported_only':'eligible_for_supported_analysis'}
tax=pd.read_csv(BASE/'results/category_catalog.csv').set_index('category_id');ends=['2026Q2','2026Q1','2025Q4','2025Q2']
for scenario,where in scopes.items():
 c.execute('CREATE OR REPLACE TEMP VIEW s AS SELECT * FROM p WHERE '+where)
 q=c.execute("SELECT category_id,year(date)::varchar||'Q'||quarter(date)::varchar period,count(*) papers FROM s GROUP BY 1,2").df();q.to_csv(OUT/(scenario+'_quarters.csv'),index=False)
 m=c.execute("SELECT category_id,strftime(date,'%Y-%m') AS month,count(*) papers FROM s GROUP BY 1,2").df();m.to_csv(OUT/(scenario+'_months.csv'),index=False)
 c.execute("CREATE OR REPLACE TEMP TABLE inst AS SELECT category_id,date,lower(trim(n.name)) institution FROM s CROSS JOIN UNNEST(string_split(institutions,';')) n(name) WHERE trim(n.name) NOT IN ('','None','nan','[]')")
 for end in ends if scenario=='main' else ['2026Q2']:
  ws=windows(end);ctx=pd.DataFrame(index=tax.index)
  for i,w in enumerate(ws):
   start=str(pd.Period(w[0]).start_time.date());stop=str(pd.Period(w[-1]).end_time.date())
   v=c.execute('SELECT category_id,count(DISTINCT institution) n FROM inst WHERE date BETWEEN ? AND ? GROUP BY 1',[start,stop]).df().set_index('category_id').n
   ctx[f'year{i}_institutions']=v.reindex(tax.index,fill_value=0)
  ctx['recent_institutions']=ctx.year0_institutions
  for y in [1,3,5]:
   v=c.execute('SELECT category_id,count(DISTINCT institution) n FROM inst WHERE date BETWEEN ? AND ? GROUP BY 1',[str(pd.Period(ws[y-1][0]).start_time.date()),str(pd.Period(ws[0][-1]).end_time.date())]).df().set_index('category_id').n
   ctx[f'core_institutions_{y}y']=v.reindex(tax.index,fill_value=0)
  year=int(end[:4]);v=c.execute("SELECT category_id,avg(pc) citation FROM (SELECT category_id,CASE WHEN cited_by_count=0 THEN 0.0 ELSE percent_rank() OVER(PARTITION BY year(date) ORDER BY cited_by_count) END pc FROM s WHERE year(date)>=? AND year(date)<?) GROUP BY 1",[year-3,year]).df().set_index('category_id').citation
  ctx['citation_cohort_percentile']=v.reindex(tax.index,fill_value=0);ctx.to_csv(OUT/(scenario+'_'+end+'_context.csv'))
 print('MULTIYEAR_INPUT',scenario,len(q),flush=True)
c.close();dump(OUT/'INPUT_METHOD.json',dict(created=now(),scopes=scopes,endpoints=ends,coverage='2020-01..2026-08; scoring ends at complete 2026Q2',citation='Snapshot cumulative citation percentile, three prior full publication years; historical cutoffs are retrospective window diagnostics, not as-of forecasts.',dedup='Global normalized title+calendar-year; short title uses doc_id; keep earliest date,row_id',institutions='Distinct normalized name union recomputed for each scope and core horizon; emerging baseline is annual mean breadth, not 3-year union.'))
