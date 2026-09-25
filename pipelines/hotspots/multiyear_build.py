"""Create all 750 metrics, shortlist and explicit semantic-review queues."""
from common import *
import pandas as pd,numpy as np
from multiyear_scoring import score,gates,CORE_WEIGHTS,EMERGING_WEIGHTS
D=BASE/'data/multiyear';tax=pd.read_csv(BASE/'results/category_catalog.csv').set_index('category_id')

def calculate(scenario='main',end='2026Q2',**kw):
 q=pd.read_csv(D/(scenario+'_quarters.csv'));ctx=pd.read_csv(D/(scenario+'_'+end+'_context.csv')).set_index('category_id')
 return score(tax,q,ctx,end=end,**kw)

def build():
 z,cc,ec=calculate();save(cc.rename_axis('category_id').reset_index(),'multiyear_core_components.csv');save(ec.rename_axis('category_id').reset_index(),'multiyear_emerging_components.csv')
 variants={}
 for s in ['quality','geometry','dedup','exclude_needs_review','supported_only']:
  f,_,_=calculate(s);variants[s]=f;save(f.reset_index(),'multiyear_'+s+'.csv')
  for col in ['multiyear_share_ratio','share_growth_ratio']:z[s+'_'+col]=f[col]
 m=pd.read_csv(D/'main_months.csv')
 for yr in [2025,2026]:
  v=m[m.month.between(f'{yr}-01',f'{yr}-08')].groupby('category_id').papers.sum().reindex(z.index,fill_value=0)
  z[f'papers_{yr}_jan_aug']=v;z[f'share_{yr}_jan_aug']=(v+.5)/(v.sum()+.5*len(z))
 z['share_ratio_2026_ytd']=z.share_2026_jan_aug/z.share_2025_jan_aug
 robust=[f'{s}_{c}' for s in ['quality','geometry','dedup'] for c in ['multiyear_share_ratio','share_growth_ratio']]+['share_ratio_2026_ytd']
 z['robust_min_ratio']=z[robust].min(axis=1)
 z['emerging_robust']=gates(z,'emerging').all(axis=1)
 reviews=pd.read_csv(BASE/'results/semantic_review_decisions.csv');r=reviews[reviews.source.eq('paper')].set_index('category_id')
 for flag in ['core_review_pass','emerging_review_pass']:z[flag]=r[flag].reindex(z.index).fillna(False).astype(bool)
 z['paper_review_reason']=r.reason.reindex(z.index).fillna('本轮尚无对应语义审阅；仅为数值候选')
 z['paper_review_decision']=r.decision.reindex(z.index).fillna('待专家复核')
 if (BASE/'results/multiyear_semantic_review.csv').exists():
  extra=pd.read_csv(BASE/'results/multiyear_semantic_review.csv').set_index('category_id')
  for flag in ['core_review_pass','emerging_review_pass']:
   z.loc[extra.index,flag]=extra[flag].astype(bool)
  z.loc[extra.index,'paper_review_reason']=extra.reason
  z.loc[extra.index,'paper_review_decision']=extra.decision
 z['final_core']=z.core_eligible&z.core_review_pass
 z['final_emerging']=z.emerging_robust&z.emerging_review_pass
 z['core_review_basis']=np.where(z.core_review_pass,'冻结样本审阅或本次多年补审；非独立专家认定','未通过或尚未完成核心范围审阅')
 z['review_status']=np.where(z.final_core|z.final_emerging,'已有样本依据的专家初评候选',np.where(z.core_eligible|z.emerging_robust,'数值通过，语义未通过或待复核','未过本版数值门槛'))
 save(z.reset_index(),'multiyear_metrics_all750.csv')
 for family,gate,sc in [('core','core_eligible','core_score'),('emerging','emerging_robust','emerging_score')]:
  d=z[z[gate]].sort_values(sc,ascending=False).reset_index();d.insert(0,'numeric_rank',range(1,len(d)+1));save(d,'multiyear_'+family+'_candidates.csv')
 print('MULTIYEAR_CANDIDATES',int(z.core_eligible.sum()),int(z.emerging_robust.sum()),'reviewed',int(z.final_core.sum()),int(z.final_emerging.sum()),flush=True)
 print(z[z.final_core|z.final_emerging][['name','core_papers','recent_papers','multiyear_share_ratio','historical_peak_ratio','final_core','final_emerging']].to_string(),flush=True)
 for end in ['2026Q1','2025Q4','2025Q2']:
  d,_,_=calculate(end=end);save(d.reset_index(),'multiyear_cutoff_'+end+'.csv')
 for years in [1,5]:
  d,_,_=calculate(core_years=years);save(d.reset_index(),f'multiyear_core_{years}y.csv')
 for years in [2,4]:
  d,_,_=calculate(baseline_years=years);save(d.reset_index(),f'multiyear_baseline_{years}y.csv')
 for omit in [1,2,3]:
  d,_,_=calculate(omit_baseline=omit);save(d.reset_index(),f'multiyear_omit_baseline_{omit}.csv')
 # Five nonoverlapping annual blocks per topic for expert inspection.
 rows=[]
 from multiyear_scoring import windows
 for i,w in enumerate(windows()):
  for cid,row in z.iterrows():rows.append(dict(category_id=cid,name=row['name'],block=i,start_quarter=w[0],end_quarter=w[-1],papers=row[f'year{i}_papers'],background=row[f'year{i}_denominator'],share=row[f'year{i}_share']))
 save(pd.DataFrame(rows),'multiyear_annual_trajectories.csv')
 method=dict(version='750-multiyear-v1',created=now(),core_window=['2023-07-01','2026-06-30'],recent_window=['2025-07-01','2026-06-30'],emerging_baseline=['2022-07-01','2025-06-30'],history=['2021-07-01','2026-06-30'],core_weights=CORE_WEIGHTS,emerging_weights=EMERGING_WEIGHTS,baseline='Equal mean of 3 separately normalized annual shares; disjoint from recent year',core_gates='three-year>=750, every year>=150, >=9/12 quarters each>=25, recent>=250 and recentYOYshare>=0.8; direct scope and semantic review',emerging_gates='recent>=100; baseline annual mean>=50; recent/3-year mean>=1.25; YOY>=1.15; >=3 growing quarters; 3-year slope>0; recent/previous4-year peak>=1.05; pooled-count lower95>1.05 and BHq<.05; quality/geometry/dedup long+YOY and latestYTD ratios>=1.10; semantic review',small_base='Below baseline mean50 retained as early-signal watch, not forced to pass established-growth gate',statistics='Count-only pooled-binomial approximations are screening diagnostics; no serial-dependence-adjusted confidence or causal claim.',citation='Snapshot cumulative citations, publication-year percentiles within filtered scope; historical endpoints are retrospective sensitivity, not temporal validation',potential='Unchanged unified4 task units, fixed 2026 patent/policy data; no invented historical patent series',review='Any new numeric candidates without sample scope review remain pending; thresholds not tuned to preserve old lists')
 dump(BASE/'data/MULTIYEAR_METHOD.json',method)
 return z
if __name__=='__main__':build()
