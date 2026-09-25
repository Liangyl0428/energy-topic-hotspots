"""Recompute potential sensitivity on four unified task units, never old labels."""
from common import *
from potential_unified_metrics import load_records,policies,with_may,qualify,SCENARIOS
import pandas as pd,numpy as np,itertools
from scipy.stats import spearmanr

def run():
 R=BASE/'reliability';d=load_records();p=policies()
 z=pd.read_csv(BASE/'results/potential_unified_metrics.csv',float_precision='round_trip').set_index('unit_id')
 comp=z[['patent_component','applicant_component','policy_component']].copy();comp.columns=['patents','applicants','policy']
 w=np.array([.3,.2,.5]);base=100*comp.dot(w)
 np.testing.assert_allclose(base,z.potential_evidence_score,atol=1e-10)
 br=base.rank(ascending=False,method='min');selected=set(z.index[z.potential_priority])
 def order(s):return s.sort_index().sort_values(ascending=False,kind='stable')
 def compare(name,s,weights):
  rr=s.rank(ascending=False,method='min')
  out=dict(family='potential',scenario=name,pool_size=len(z),spearman=float(spearmanr(base,s).statistic),mean_abs_rank_change=float((rr-br).abs().mean()),max_abs_rank_change=float((rr-br).abs().max()),weights=json.dumps(dict(zip(comp.columns,map(float,weights)))),formal_membership_changed_by_score_alone=0)
  for k in [1,2,10,25]:
   if k>len(z):out[f'top{k}_overlap']=np.nan;out[f'top{k}_jaccard']=np.nan;continue
   a=set(order(base).head(k).index);b=set(order(s).head(k).index)
   out[f'top{k}_overlap']=len(a&b);out[f'top{k}_jaccard']=len(a&b)/len(a|b)
  out['reviewed_final_top10_overlap']=np.nan
  return out,rr
 ab=[];details=[];trials=[];rankrows=[];st=[]
 row,_=compare('baseline',base,w);ab.append(row)
 for i,key in enumerate(comp):
  wi=w.copy();wi[i]=0;wi/=wi.sum();ss=100*comp.dot(wi);row,rr=compare('remove_'+key,ss,wi);ab.append(row)
  for uid in z.index:details.append(dict(family='potential',scenario='remove_'+key,category_id=uid,unit_id=uid,name=z.loc[uid,'name'],baseline_rank=br[uid],rank=rr[uid],score=ss[uid]))
 rng=np.random.default_rng(75020260925);tops=[]
 for i in range(500):
  wi=w*rng.uniform(.8,1.2,3);wi/=wi.sum();ss=100*comp.dot(wi);row,rr=compare(f'weight_{i:03d}',ss,wi);trials.append(row);rankrows.append(rr);tops.append(order(ss).index[0])
 ranks=pd.DataFrame(rankrows)
 for uid in z.index:st.append(dict(family='potential',category_id=uid,unit_id=uid,name=z.loc[uid,'name'],baseline_rank=br[uid],min_rank=ranks[uid].min(),median_rank=ranks[uid].median(),max_rank=ranks[uid].max(),top10_trial_fraction=np.nan,top1_trial_fraction=float(np.mean(np.array(tops)==uid)),formal_selected=uid in selected))
 cases=[];topic=[]
 def record(name,frame,kind,params=None,mask=None):
  yes=qualify(frame,params) if mask is None else mask
  ids=set(frame.index[yes]);cases.append(dict(family='potential',scenario=name,kind=kind,parameters=json.dumps(params or {},ensure_ascii=False),numeric_candidates=len(ids),reviewed_selected=len(ids),baseline_count=len(selected),retained=len(ids&selected),retention=len(ids&selected)/len(selected) if selected else np.nan,jaccard=len(ids&selected)/len(ids|selected) if ids|selected else np.nan,gained=';'.join(sorted(ids-selected)),lost=';'.join(sorted(selected-ids)),selected_ids=';'.join(sorted(ids)),interpretation='统一任务集合、同源主体、任务政策重算；4个单元内条件压力测试，不是准确率或未来预测'))
  for uid,r in frame.iterrows():
   topic.append(dict(unit_id=uid,category_id=r.category_id,name=r['name'],scenario=name,kind=kind,selected=uid in ids,patents=r.patents_2026,papers=r.papers_2026_jan_aug,applicants=r.known_applicant_names,policies=r.policy_groups,relative_share=r.relative_share,matched_jan_may_relative_share=r.matched_jan_may_relative_share,score=r.potential_evidence_score))
 record('baseline',z,'baseline')
 gates={'patents':z.patents_2026.ge(50),'applicants':z.known_applicant_names.ge(20),'policies':z.policy_groups.ge(2),'relative':z.relative_share.ge(1.25),'matched_may':z.matched_jan_may_relative_share.ge(1.25)}
 for key in gates:record('remove_gate_'+key,z,'gate_ablation',mask=pd.DataFrame({k:v for k,v in gates.items() if k!=key}).all(axis=1))
 grid={'patents':[25,50,100,200,500],'applicants':[10,20,40,100],'policies':[1,2,3,4],'relative':[1.,1.25,1.5,2.,3.,5.]}
 for key,values in grid.items():
  for val in values:record(f'{key}={val}',z,'one_at_a_time',{key:val})
 for pol,ratio in itertools.product(grid['policies'],grid['relative']):record(f'policies={pol},relative={ratio}',z,'joint_grid',{'policies':pol,'relative':ratio})
 for scenario in SCENARIOS:
  f=with_may(d,p,scenario);record('unified_'+scenario,f,'potential_data_sensitivity')
 record('collapse_policy_by_publisher',with_may(d,p,publisher=True),'policy_dependence')
 for group in sorted(p.policy_group.unique()):record('drop_policy_'+group,with_may(d,p,drop_policy=group),'leave_policy_out')
 # Asymmetric label uncertainty, not confidence bounds: all pending papers valid,
 # no pending patents valid, then reverse. Counts and applicant names follow the chosen patent set.
 expanded=with_may(d,p,'expanded')
 for name,patframe,papframe in [('pending_papers_only',z,expanded),('pending_patents_only',expanded,z)]:
  f=patframe.copy();f['papers_2026_jan_aug']=papframe.papers_2026_jan_aug;f['jan_may_papers']=papframe.jan_may_papers
  f['relative_share']=(f.patents_2026+.5)/(f.patent_denominator+1)/((f.papers_2026_jan_aug+.5)/(f.paper_denominator+1))
  # Identical May denominators cancel via the baseline source ratio constant.
  mayfactor=z.matched_jan_may_relative_share/((z.jan_may_patents+.5)/(z.jan_may_papers+.5))
  f['matched_jan_may_relative_share']=(f.jan_may_patents+.5)/(f.jan_may_papers+.5)*mayfactor
  record(name,f,'classification_uncertainty')
 # Document-level deterministic removal tests recompute applicant identities.
 for fraction in [.1,.2]:
  trial=d.copy();ispat=trial.source.eq('patent')&trial.final_status.eq('strict')
  h=trial.row_id.map(lambda i:int(hashlib.sha256(f'label-stress-v1|{i}'.encode()).hexdigest()[:12],16)/16**12)
  trial.loc[ispat&h.lt(fraction),'final_status']='excluded'
  record(f'patent_positive_removal_{fraction:.0%}',with_may(trial,p),'classification_uncertainty',{'assumed_false_positive_fraction':fraction})
 tables=[(pd.DataFrame(ab),'score_ablation_summary.csv'),(pd.DataFrame(details),'score_ablation_ranks.csv'),(pd.DataFrame(trials),'weight_trials.csv'),(pd.DataFrame(st),'weight_rank_stability.csv'),(pd.DataFrame(cases),'gate_and_data_sensitivity.csv')]
 for frame,file in tables:
  old=pd.read_csv(R/file);old=old[old.family.ne('potential')]
  pd.concat([old,frame],ignore_index=True).to_csv(R/file,index=False,encoding='utf-8-sig')
 pd.DataFrame(topic).to_csv(R/'potential_unified_sensitivity_details.csv',index=False,encoding='utf-8-sig')
 comp.rename_axis('unit_id').reset_index().to_csv(R/'potential_score_components.csv',index=False,encoding='utf-8-sig')
 pd.DataFrame(cases).to_csv(R/'potential_unified_sensitivity_summary.csv',index=False,encoding='utf-8-sig')
 pub=p[p.support_strength.ge(2)].drop_duplicates(['unit_id','publisher']).groupby('unit_id').size().reindex(z.index,fill_value=0)
 pub.rename('distinct_reported_publishers').to_csv(R/'policy_publisher_sensitivity.csv')
 dump(R/'POTENTIAL_UNIFIED_EXPERIMENT_METHOD.json',dict(created_utc=now(),units=list(z.index),unit_pool_size=4,weight_trials=500,weights=[.3,.2,.5],rank_scope='四个统一任务单元内百分位；不可与旧30方向或750原类别分数直接比较。',top_k='Only top1/top2 meaningful; top10/top25 not applicable and blank.',smoothing='0.5 success,0.5 complement: denominator+1',baseline='Strict unified sets, patent>=50,applicants>=20,task-policy groups>=2,both2026JanAug and matchedJanMay ratios>=1.25',policy_window='截至8月已核成文日期，JanMay仅检验同期文献/专利覆盖，非历史政策回测。',data_scenarios=SCENARIOS,source_balance='Both sources use the same evidence scope; body-available and global dedup scenarios also rebuild background denominators.',uncertainty='Pending-label bounds and deterministic patent removal are assumption stress tests, not statistical confidence intervals.',grids=grid,scenarios=len(cases),review='Frozen samples informed explicit document corrections; heldout pre-correction disagreements retained, not independent expert accuracy.'))
 method=read(R/'EXPERIMENT_METHOD.json');method.update(potential_revision='See POTENTIAL_UNIFIED_EXPERIMENT_METHOD.json; four task units replace legacy potential pool.',rank_pool='Core/emerging unchanged; potential uses4 unified task units and top1/top2.',total_gate_and_data_scenarios=len(pd.read_csv(R/'gate_and_data_sensitivity.csv')));dump(R/'EXPERIMENT_METHOD.json',method)
 print('POTENTIAL_EXPERIMENTS',len(cases),'scenarios',len(topic),'unit results',flush=True)

if __name__=='__main__':run()
