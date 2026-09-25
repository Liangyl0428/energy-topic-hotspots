"""Replace current deliverables while preserving unified potential evidence."""
from common import *
import pandas as pd,numpy as np
from multiyear_scoring import ordered_scores

def finalize():
 z=pd.read_csv(BASE/'results/multiyear_metrics_all750.csv').set_index('category_id')
 oldroot=Path(read(BASE/'audit/MULTIYEAR_BASELINE.json')['path'])
 old=pd.read_csv(oldroot/'results/hotspot_summary_all750.csv').set_index('category_id')
 # Preserve only actual patent/policy/unit fields; no stale yearly literature rankings or grades.
 keep=[c for c in old if any(w in c for w in ['patent','potential','policy','applicant','unified_','cross_label','country_count']) and c not in z]
 z=z.join(old[keep])
 quality=pd.read_csv(BASE/'results/paper_metadata_quality.csv').set_index('category_id')
 z=z.join(quality[[c for c in quality if c not in z]])
 g=pd.read_csv(BASE/'reliability/gate_and_data_sensitivity.csv')
 grades=[]
 for fam,flag in [('core','final_core'),('emerging','final_emerging')]:
  scenarios=['quality','geometry','dedup','exclude_needs_review','supported_only']
  for cid in z.index[z[flag]]:
   r=dict(family=fam,category_id=cid,name=z.loc[cid,'name'])
   for s in scenarios:
    row=g[g.family.eq(fam)&g.scenario.eq(s)].iloc[0];r[s+'_retained']=cid in str(row.selected_ids).split(';')
   r['data_scenarios_passed']=sum(r[s+'_retained'] for s in scenarios)
   r['robustness_grade']='五项均保留' if r['data_scenarios_passed']==5 else '存在数据敏感性'
   windows=['core_window_1y','core_window_5y'] if fam=='core' else ['omit_baseline_year_1','omit_baseline_year_2','omit_baseline_year_3']
   failed=[]
   for window in windows:
    row=g[g.family.eq(fam)&g.scenario.eq(window)].iloc[0]
    if cid not in str(row.selected_ids).split(';'):failed.append(window)
   r['time_sensitivity_note']='所列时间长度/删年检验均保留' if not failed else '未保留情景：'+'；'.join(failed)
   r['scope']='压力测试通过数，不是准确率或置信度'
   grades.append(r)
 gr=pd.DataFrame(grades);save(gr,'multiyear_robustness_grades.csv')
 for family,flag,score,file in [('core','final_core','core_score','core_hotspots.csv'),('emerging','final_emerging','emerging_score','emerging_hotspots.csv')]:
  d=z.loc[ordered_scores(z.loc[z[flag],score]).index].reset_index();d.insert(0,'report_rank',range(1,len(d)+1));d=d.merge(gr[gr.family.eq(family)].drop(columns=['name','family','scope']),on='category_id',how='left');save(d,file)
 save(z.reset_index(),'literature_metrics_all750.csv');save(z.reset_index(),'hotspot_summary_all750.csv')
 watch=z[(z.core_eligible&~z.final_core)|(z.emerging_robust&~z.final_emerging)|(z.share_growth_ratio.ge(1.15)&~z.final_emerging)].copy();save(watch.reset_index(),'watch_and_downgraded.csv')
 changes=[]
 for fam,flag in [('core','final_core'),('emerging','final_emerging')]:
  for cid in z.index[old[flag]|z[flag]]:
   a=bool(old.loc[cid,flag]);b=bool(z.loc[cid,flag]);changes.append(dict(family=fam,category_id=cid,name=z.loc[cid,'name'],old_selected=a,new_selected=b,change='保留' if a and b else '新增' if b else '退出',old_score=old.loc[cid,fam+'_score'],new_score=z.loc[cid,fam+'_score'],note='方法及分数定义变化，分差不可直接解释为趋势强弱变化'))
 save(pd.DataFrame(changes),'multiyear_before_after.csv')
 method=read(BASE/'data/MULTIYEAR_METHOD.json');dump(BASE/'METHOD.json',method)
 fm=read(BASE/'data/FINAL_METHOD.json');fm.update(literature_method='MULTIYEAR_METHOD.json',core=int(z.final_core.sum()),emerging=int(z.final_emerging.sum()),literature_window='core3years plus latest1year; emerging latest1year vs disjoint prior3years; five-year trajectory',semantic_pending=True);dump(BASE/'data/FINAL_METHOD.json',fm)
 print('MULTIYEAR_FINAL',len(z),int(z.final_core.sum()),int(z.final_emerging.sum()),flush=True)
if __name__=='__main__':finalize()
