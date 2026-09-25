"""潜在热点的核心统计与资格算法。

calculate(): 同任务证据与评分；qualify(): 入选条件；with_may(): 同期窗口检查。
build(): 比较严格/扩展范围，形成跟踪建议。代码导读见 docs/ALGORITHM.md。
"""
from common import *
from multiyear_scoring import ordered_scores
from potential_unified import UNITS
import pandas as pd,numpy as np

SCENARIOS=['strict','expanded','title_only_evidence','body_available','original_candidates_only','cross_candidates_only','title_year_dedup','no_manual_overrides']

def load_records():
 d=pd.read_parquet(BASE/'evidence/potential_unified_candidates.parquet')
 d['final_status']=d.rule_status;d['decision_basis']=d.rule_reason
 reviews=pd.read_csv(BASE/'results/potential_unified_document_reviews.csv').fillna('')
 overrides=reviews[reviews.apply_override.eq(True)].drop_duplicates(['unit_id','row_id'],keep='last')
 for r in overrides.itertuples():
  mask=d.unit_id.eq(r.unit_id)&d.row_id.eq(r.row_id);assert mask.sum()==1
  d.loc[mask,'final_status']=r.review_status;d.loc[mask,'decision_basis']='已展示样本语义修订：'+r.review_reason
 p=pd.read_parquet(BASE/'data/patent_metadata.parquet',columns=['row_id','applicant_names','country'])
 d=d.merge(p,on='row_id',how='left',validate='many_to_one')
 d['applicant_names']=d.applicant_names.map(lambda x:list(x) if isinstance(x,(list,np.ndarray)) else [])
 return d

def policies():
 p=pd.read_csv(BASE/'results/potential_unified_policy_reviews.csv').fillna('')
 return p[p.decision.eq('采用')].sort_values('support_strength',ascending=False).drop_duplicates(['unit_id','policy_group'])

def selected(d,scenario='strict'):
 mask=d.final_status.isin(['strict','pending']) if scenario=='expanded' else d.final_status.eq('strict')
 if scenario=='no_manual_overrides':mask=d.rule_status.eq('strict')
 if scenario=='title_only_evidence':
  # Deliberately conservative same-text-field test in BOTH sources.
  from potential_unified import classify
  mask &=pd.Series([classify(r.unit_id,r.title,'')[0]=='strict' for r in d.itertuples()],index=d.index)
 if scenario=='body_available':mask &=d.body.fillna('').str.strip().ne('')
 if scenario=='original_candidates_only':mask &=d.from_original_category
 if scenario=='cross_candidates_only':mask &=d.from_old_cross_query|d.from_new_object_query
 out=d[mask].copy()
 if scenario=='title_year_dedup':
  ids=pd.read_parquet(BASE/'data/potential_unified_global_dedup.parquet',columns=['row_id']).row_id
  out=out[out.row_id.isin(ids)]
 return out

def calculate(d,policy,scenario='strict',end='2026-08-31',publisher=False,drop_policy=None):
 """在同一任务范围内统计记录、申请主体、政策、相对份额与排序分数。"""
 den=pd.read_csv(BASE/'results'/('potential_unified_dedup_denominators.csv' if scenario=='title_year_dedup' else 'potential_unified_denominators.csv'))
 den=den[den.month.le(end[:7])];denfield='with_body' if scenario=='body_available' else 'documents'
 totals=den.groupby('source')[denfield].sum().to_dict()
 s=selected(d,scenario);s=s[s.date.le(end)]
 pp=policy.copy()
 pp=pp[pp.issue_date_reviewed.le(end)]
 if drop_policy:pp=pp[pp.policy_group.ne(drop_policy)]
 if publisher:pp=pp.drop_duplicates(['unit_id','publisher'])
 rows=[]
 for uid,u in UNITS.items():
  a=s[s.unit_id.eq(uid)];pat=a[a.source.eq('patent')];pap=a[a.source.eq('paper')];pol=pp[pp.unit_id.eq(uid)]
  applicants={str(n).strip().lower() for names in pat.applicant_names for n in names if str(n).strip()}
  npat=len(pat);npap=len(pap)
  ratio=(npat+.5)/(totals['patent']+1)/((npap+.5)/(totals['paper']+1))
  rows.append(dict(unit_id=uid,category_id=u['category_id'],name=u['name'],scenario=scenario,end_date=end,
   patents_2026=npat,papers_2026_jan_aug=npap,known_applicant_names=len(applicants),
   applicant_metadata_fraction=float(pat.applicant_names.str.len().gt(0).mean()) if len(pat) else 0,
   policy_groups=int(pol.support_strength.ge(2).sum()),policy_points=int(pol.support_strength.sum()),
   patent_denominator=int(totals['patent']),paper_denominator=int(totals['paper']),relative_share=ratio,
   pending_patents=int(((d.unit_id==uid)&(d.source=='patent')&(d.final_status=='pending')&d.date.le(end)).sum()),
   pending_papers=int(((d.unit_id==uid)&(d.source=='paper')&(d.final_status=='pending')&d.date.le(end)).sum())))
 z=pd.DataFrame(rows).set_index('unit_id')
 z['patent_component']=z.patents_2026.rank(pct=True)
 z['applicant_component']=z.known_applicant_names.rank(pct=True)
 z['policy_component']=(z.policy_points/8).clip(0,1)
 z['potential_evidence_score']=100*(.3*z.patent_component+.2*z.applicant_component+.5*z.policy_component)
 return z

def qualify(z,params=None):
 """检查规模、主体、政策组数和两个同期相对份额的全部门槛。"""
 p=params or {};out=z.patents_2026.ge(p.get('patents',50))&z.known_applicant_names.ge(p.get('applicants',20))&z.policy_groups.ge(p.get('policies',2))&z.relative_share.ge(p.get('relative',1.25))&z.matched_jan_may_relative_share.ge(p.get('relative',1.25))
 return out

def with_may(d,policy,scenario='strict',publisher=False,drop_policy=None):
 """同时计算1—8月和1—5月文献/专利指标，再判断是否达标。"""
 z=calculate(d,policy,scenario,publisher=publisher,drop_policy=drop_policy)
 may=calculate(d,policy,scenario,end='2026-05-31',publisher=publisher,drop_policy=drop_policy)
 z['matched_jan_may_relative_share']=may.relative_share
 z['jan_may_patents']=may.patents_2026;z['jan_may_papers']=may.papers_2026_jan_aug
 # As-of-August policy evidence: matched-May tests source coverage, not a historical decision/backtest.
 z['potential_priority']=qualify(z)
 return z

def build():
 d=load_records();p=policies()
 d.to_parquet(BASE/'evidence/potential_unified_decisions.parquet',index=False,compression='zstd')
 summary=d.groupby(['unit_id','source','rule_status','final_status']).size().rename('documents').reset_index();save(summary,'potential_unified_decision_counts.csv')
 z=with_may(d,p);expanded=with_may(d,p,'expanded')
 for col in ['patents_2026','papers_2026_jan_aug','relative_share','matched_jan_may_relative_share','potential_priority']:
  z['expanded_'+col]=expanded[col]
 z['uncertainty_ratio_lower']=(z.patents_2026+.5)/(z.patent_denominator+1)/((expanded.papers_2026_jan_aug+.5)/(z.paper_denominator+1))
 z['uncertainty_ratio_upper']=(expanded.patents_2026+.5)/(z.patent_denominator+1)/((z.papers_2026_jan_aug+.5)/(z.paper_denominator+1))
 z['potential_review_category']=np.where(z.potential_priority,'统一任务口径：应用机会跟踪','统一任务口径：证据不足，保留观察')
 z['potential_reason']=[(';'.join([msg for ok,msg in [(r.patents_2026>=50,'专利数不足50'),(r.known_applicant_names>=20,'主体不足20'),(r.policy_groups>=2,'明确任务政策不足2组'),(r.relative_share>=1.25,'同期相对份额不足1.25'),(r.matched_jan_may_relative_share>=1.25,'1至5月同期相对份额不足1.25')] if not ok]) or '通过统一集合下全部基准数值门槛')+'；规则与样本支持，不是全量人工验收或未来成功概率' for r in z.itertuples()]
 z['scope_definition']=[UNITS[i]['scope'] for i in z.index]
 z['evidence_tier']=np.where(z.potential_priority & z.expanded_potential_priority,'双口径支持的跟踪方向',np.where(z.potential_priority,'边界敏感的条件性跟踪','证据不足，保留观察'))
 z['scope_sensitivity']=np.where(z.expanded_potential_priority,'扩展口径亦通过','扩展口径未通过')
 z['scope_sensitivity']+=np.where(z.uncertainty_ratio_lower.ge(1.25),'；非对称待判压力下仍≥1.25','；非对称待判压力下低于1.25')
 save(z.reset_index(),'potential_unified_metrics.csv')
 output=z.loc[ordered_scores(z.loc[z.potential_priority,'potential_evidence_score']).index].reset_index();output.insert(0,'report_rank',range(1,len(output)+1));save(output,'potential_priority.csv')
 save(z[~z.potential_priority].reset_index(),'potential_unified_watch.csv')
 # Export every candidate with a reason, but text bodies stay in Parquet for size.
 fields=['unit_id','unit_name','parent_category_id','row_id','doc_id','source','category_id','date','title','from_original_category','from_old_cross_query','from_new_object_query','rule_status','final_status','decision_basis']
 save(d[fields],'potential_unified_record_ledger.csv')
 # Confirm identical patent rows generate BOTH numerator and applicant lists.
 apps=selected(d).query("source == 'patent'")[['unit_id','row_id','applicant_names']].explode('applicant_names').dropna(subset=['applicant_names'])
 save(apps,'potential_unified_applicant_evidence.csv')
 save(pd.DataFrame([dict(unit_id=k,**v) for k,v in UNITS.items()]),'potential_unified_scope.csv')
 oldroot=Path(read(BASE/'audit/UNIFIED_POTENTIAL_BASELINE.json')['path'])
 old=pd.read_csv(oldroot/'results/potential_priority.csv').set_index('category_id')
 compare=z.reset_index()[['unit_id','category_id','name','patents_2026','papers_2026_jan_aug','known_applicant_names','policy_groups','relative_share','matched_jan_may_relative_share','potential_priority']].copy()
 for col in ['patents_2026','known_applicant_names','cross_label_relative_share']:
  compare['old_parent_'+col]=compare.category_id.map(old[col])
 save(compare,'potential_unified_before_after.csv')
 print('UNIFIED_METRICS',z[['name','patents_2026','papers_2026_jan_aug','known_applicant_names','policy_groups','relative_share','matched_jan_may_relative_share','potential_priority']].to_string(),flush=True)
