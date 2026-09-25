"""Prepare reproducible temporal supplements; display/read separately from decisions."""
from common import *
import pandas as pd,duckdb
z=pd.read_csv(BASE/'results/multiyear_metrics_all750.csv').set_index('category_id')
r=pd.read_csv(BASE/'results/semantic_review_decisions.csv');r=r[r.source.eq('paper')].set_index('category_id')
core=pd.read_csv(BASE/'results/multiyear_core_candidates.csv').head(25)
em=pd.read_csv(BASE/'results/multiyear_emerging_candidates.csv')
new=set(core.category_id)-set(r.index);new |=set(em.category_id)-set(r.index)
# Previously core-only approved objects becoming emerging candidates need a family decision too.
old_em=set(pd.read_csv(Path(read(BASE/'audit/MULTIYEAR_BASELINE.json')['path'])/'results/emerging_pre_review.csv').category_id)
new |=set(em.category_id)-old_em
# Escalated after actually reading the first historical samples.
new |= {'C0009','C0155','C0169','C0221','C0276','C0343'}
historical=set(z.index[z.final_core])-new
c=duckdb.connect();c.execute('SET threads=4');c.execute("SET memory_limit='4GB'")
c.from_parquet(str(BASE/'data/assignments/*.parquet')).create_view('a');c.execute('ATTACH '+sqlstr(ROOT/'analyze/data/independent_corpus.duckdb')+' AS metadata (READ_ONLY)')
c.register('targets',pd.DataFrame({'category_id':sorted(new|historical)}))
# Stratify by annual block; random selection independent of match-to-name.
parts=[]
for label,start,end in [('2023H2_2024H1','2023-07-01','2024-06-30'),('2024H2_2025H1','2024-07-01','2025-06-30'),('2025H2_2026H1','2025-07-01','2026-06-30')]:
 d=c.execute("""SELECT a.category_id,a.row_id,a.doc_id,a.date,a.title,coalesce(w.abstract,'') body,a.title_only,a.needs_review FROM a JOIN targets USING(category_id) LEFT JOIN metadata.works w ON substr(a.doc_id,7)=w.work_id WHERE a.source='paper' AND a.category_index>=0 AND NOT a.retracted AND NOT a.template_record AND a.date BETWEEN ? AND ? QUALIFY row_number() OVER(PARTITION BY category_id ORDER BY hash(a.doc_id||'multiyear-review-v1'),a.row_id)<=3""",[start,end]).df();d['annual_block']=label;parts.append(d)
d=pd.concat(parts,ignore_index=True);d=d[d.category_id.isin(new)|((d.annual_block!='2025H2_2026H1')&~d.duplicated(['category_id','annual_block']))].copy()
d['name']=d.category_id.map(z.name);d['review_purpose']=d.category_id.map(lambda x:'新增候选或新类型补审' if x in new else '既有核心跨年抽样核对')
d.to_parquet(BASE/'evidence/multiyear_review_samples.parquet',index=False)
# Preserve what is actually displayed, not the entire unshown abstract.
d['excerpt']=d.body.str[:650];d.drop(columns='body').to_csv(BASE/'review/multiyear_displayed_samples.csv',index=False,encoding='utf-8-sig')
for cid,s in d.groupby('category_id'):
 lines=[f'CATEGORY {cid} {s.name.iloc[0]} {s.review_purpose.iloc[0]}']
 for row in s.itertuples():lines.append(f'ROW {row.row_id} {row.annual_block} | {row.title}\n{row.excerpt}')
 (BASE/'review'/f'multiyear_{cid}.txt').write_text('\n'.join(lines)+'\n')
dump(BASE/'data/MULTIYEAR_REVIEW_DESIGN.json',dict(new_targets=sorted(new),historical_core_targets=sorted(historical),records=len(d),design='3 deterministic random records per each of3 annual blocks for new/new-family candidates; one per earlier block for accepted cores; no category-accuracy estimate',displayed_excerpt_chars=650,judgments='Written separately only after actual reading'))
print('REVIEW_SAMPLES',len(d),'new',sorted(new),'historical',len(historical),flush=True)
