"""Ablation, window and coverage stress tests for the multi-year method."""
from common import *
import pandas as pd,numpy as np,itertools
from scipy.stats import spearmanr
from multiyear_scoring import gates,CORE_WEIGHTS,EMERGING_WEIGHTS
R=BASE/'reliability'
z=pd.read_csv(BASE/'results/multiyear_metrics_all750.csv').set_index('category_id')
components={f:pd.read_csv(BASE/'results'/f'multiyear_{f}_components.csv').set_index('category_id') for f in ['core','emerging']}
weights={'core':CORE_WEIGHTS,'emerging':EMERGING_WEIGHTS}
flags={'core':'final_core','emerging':'final_emerging'}
review={'core':z.core_review_pass,'emerging':z.emerging_review_pass}
abl=[];detail=[];trials=[];stability=[];scenarios=[];td=[]
for family,comp in components.items():
 w=pd.Series(weights[family]);score=100*comp.dot(w)
 np.testing.assert_allclose(score,z[family+'_score'],atol=1e-9)
 mask=z.core_eligible if family=='core' else z.emerging_robust
 idx=z.index[mask];base=score.loc[idx];br=base.rank(ascending=False,method='min')
 def order(s):return s.sort_index().sort_values(ascending=False,kind='stable')
 def compare(label,s,w):
  v=s.loc[idx];rr=v.rank(ascending=False,method='min')
  row=dict(family=family,scenario=label,pool_size=len(idx),spearman=float(spearmanr(base,v).statistic),mean_abs_rank_change=float((rr-br).abs().mean()),max_abs_rank_change=float((rr-br).abs().max()),weights=json.dumps(w.to_dict()),formal_membership_changed_by_score_alone=0)
  for k in [10,25]:
   if k>len(idx):row[f'top{k}_overlap']=np.nan;row[f'top{k}_jaccard']=np.nan;continue
   a=set(order(base).head(k).index);b=set(order(v).head(k).index);row[f'top{k}_overlap']=len(a&b);row[f'top{k}_jaccard']=len(a&b)/len(a|b)
  return row,rr
 row,_=compare('baseline',score,w);abl.append(row)
 for col in comp:
  wi=w.copy();wi[col]=0;wi/=wi.sum();s=100*comp.dot(wi);row,rr=compare('remove_'+col,s,wi);abl.append(row)
  for cid in idx:detail.append(dict(family=family,scenario='remove_'+col,category_id=cid,name=z.loc[cid,'name'],baseline_rank=br[cid],rank=rr[cid],score=s[cid]))
 rng=np.random.default_rng(75020260925);ranks=[];tops=[]
 for i in range(500):
  wi=w*rng.uniform(.8,1.2,len(w));wi/=wi.sum();s=100*comp.dot(wi);row,rr=compare(f'weight_{i:03d}',s,wi);trials.append(row);ranks.append(rr);tops.append(set(order(s.loc[idx]).head(min(10,len(idx))).index))
 rankdf=pd.DataFrame(ranks)
 for cid in idx:stability.append(dict(family=family,category_id=cid,name=z.loc[cid,'name'],baseline_rank=br[cid],min_rank=rankdf[cid].min(),median_rank=rankdf[cid].median(),max_rank=rankdf[cid].max(),top10_trial_fraction=np.mean([cid in t for t in tops]) if len(idx)>=10 else np.nan,formal_selected=bool(z.loc[cid,flags[family]])))

def record(family,name,f,kind,params=None,mask=None,semantic=True,note=''):
 num=gates(f,family,params).all(axis=1) if mask is None else mask
 yes=num&review[family] if semantic else num
 baseline=set(z.index[z[flags[family]]]);ids=set(f.index[yes]);scenarios.append(dict(family=family,scenario=name,kind=kind,parameters=json.dumps(params or {},ensure_ascii=False),numeric_candidates=int(num.sum()),reviewed_selected=len(ids),baseline_count=len(baseline),retained=len(ids&baseline),retention=len(ids&baseline)/len(baseline) if baseline else np.nan,jaccard=len(ids&baseline)/len(ids|baseline) if ids|baseline else np.nan,gained=';'.join(sorted(ids-baseline)),lost=';'.join(sorted(baseline-ids)),selected_ids=';'.join(sorted(ids)),interpretation=note or '固定已审阅范围的条件压力测试；新增未审语义候选不自动入榜'))
 for cid in sorted(set(z.index[z.final_core|z.final_emerging])|ids):
  r=f.loc[cid];td.append(dict(family=family,scenario=name,category_id=cid,name=r['name'],selected=cid in ids,core_papers=r.core_papers,recent_papers=r.recent_papers,multiyear_share_ratio=r.multiyear_share_ratio,share_growth_ratio=r.share_growth_ratio,historical_peak_ratio=r.historical_peak_ratio,score=r[family+'_score']))
for fam in flags:
 record(fam,'baseline',z,'baseline')
 g=gates(z,fam)
 assert (g.all(axis=1)&review[fam]).equals(z[flags[fam]])
 for key in g:
  if key=='scope':continue
  record(fam,'remove_gate_'+key,z,'gate_ablation',mask=g.drop(columns=key).all(axis=1))
 record(fam,'remove_semantic_review',z,'gate_ablation',semantic=False,note='只展示数值候选范围，不是已审推荐')
grids={'core':{'annual_volume':[150,250,400],'year_fraction':[.67,1.],'quarter_fraction':[.5,.75,1.],'current_volume':[150,250,400],'current_share':[.7,.8,1.]},'emerging':{'volume':[50,100,150],'baseline':[25,50,100],'multiyear':[1.15,1.25,1.5,2.],'recent_growth':[1.,1.15,1.25],'quarters':[2,3,4],'peak':[.9,1.,1.05,1.15],'robust':[1.,1.1,1.15],'lower95':[1.,1.05,1.1],'qvalue':[.01,.05,.10]}}
for fam,grid in grids.items():
 for key,vals in grid.items():
  for v in vals:record(fam,f'{key}={v}',z,'one_at_a_time',{key:v})
for long,peak in itertools.product([1.15,1.25,1.5,2.],[.9,1.,1.05,1.15]):record('emerging',f'multiyear={long},peak={peak}',z,'joint_grid',{'multiyear':long,'peak':peak})
for scenario in ['quality','geometry','dedup','exclude_needs_review','supported_only']:
 f=pd.read_csv(BASE/'results'/('multiyear_'+scenario+'.csv')).set_index('category_id')
 # Replacement data metrics; all current semantic decisions stay frozen. Original robust gate remains for emerging.
 f['robust_min_ratio']=z.robust_min_ratio
 for fam in flags:record(fam,scenario,f,'data_sensitivity',note='本情景重新计算计数/机构/引用/分母；新兴额外保留主口径数据方向条件，不是重做所有交叉过滤组合')
for end in ['2025Q2','2025Q4','2026Q1']:
 f=pd.read_csv(BASE/'results'/f'multiyear_cutoff_{end}.csv').set_index('category_id')
 for fam in flags:record(fam,'cutoff_'+end,f,'cutoff_sensitivity',note='固定750标签及本次语义审阅的回顾性窗口诊断；仅该截止点数值门槛，不引入2026年8月确认；不是历史预测回测')
for years in [1,5]:
 f=pd.read_csv(BASE/'results'/f'multiyear_core_{years}y.csv').set_index('category_id');record('core',f'core_window_{years}y',f,'window_length',note='规模按每年250、活跃季度比例75%缩放；每年仍需150且最近一年250，窗口变动不混入固定总量门槛偏差')
for years in [2,4]:
 f=pd.read_csv(BASE/'results'/f'multiyear_baseline_{years}y.csv').set_index('category_id');f['robust_min_ratio']=z.robust_min_ratio;record('emerging',f'baseline_window_{years}y',f,'window_length',note='基线是相邻且不重叠的完整年度均值；基线计数门槛按每年50缩放；主数据确认固定')
for omit in [1,2,3]:
 f=pd.read_csv(BASE/'results'/f'multiyear_omit_baseline_{omit}.csv').set_index('category_id');f['robust_min_ratio']=z.robust_min_ratio;record('emerging',f'omit_baseline_year_{omit}',f,'leave_year_out',note='删除一个完整基线年，重算平均份额/主体广度/计数检验；最近同比、五年峰值和数据确认固定，定位基线杠杆')
for df,file in [(pd.DataFrame(abl),'score_ablation_summary.csv'),(pd.DataFrame(detail),'score_ablation_ranks.csv'),(pd.DataFrame(trials),'weight_trials.csv'),(pd.DataFrame(stability),'weight_rank_stability.csv'),(pd.DataFrame(scenarios),'gate_and_data_sensitivity.csv'),(pd.DataFrame(td),'data_sensitivity_topic_details.csv')]:df.to_csv(R/file,index=False,encoding='utf-8-sig')
dump(R/'EXPERIMENT_METHOD.json',dict(version='750-multiyear-v1',created=now(),baseline_formula_regression='all750 core/emerging formulas checked',baseline_membership_regression='exact',weight_trials_per_family=500,seed=75020260925,grids=grids,window_rules='core1/3/5years; emerging2/3/4-year disjoint annualmean baseline; three earlier endpoints; annual baseline omission',limitations='Frozen current classification, semantic decisions and citation snapshot; retrospective sensitivity, not as-of future prediction validation.'))
from potential_experiments import run
run()
print('MULTIYEAR_EXPERIMENTS',len(scenarios),'literature scenarios',flush=True)
