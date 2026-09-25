"""Project task-unit conclusions back onto a750 catalog WITHOUT merging their counts."""
from common import *
import pandas as pd,numpy as np

def integrate(z):
 u=pd.read_csv(BASE/'results/potential_unified_metrics.csv')
 z['potential_evidence_score']=np.nan
 z['potential_numeric_gate']=False;z['potential_priority']=False
 z['potential_review_category']='尚未完成统一任务口径复核，不参与本版潜在排序'
 z['potential_reason']='原类别与旧跨标签指标保留作历史诊断，不用于本版潜在判断'
 z['potential_unit_ids']='';z['potential_selected_unit_ids']='';z['potential_evidence_tier']='未统一复核'
 z['recommended_focus']=''
 for col in ['unified_patents','unified_papers','unified_applicants','unified_policy_groups','unified_relative_share','unified_matched_may_relative_share']:z[col]=np.nan
 for cid,units in u.groupby('category_id'):
  selected=units[units.potential_priority]
  z.loc[cid,'potential_unit_ids']=';'.join(units.unit_id)
  z.loc[cid,'potential_selected_unit_ids']=';'.join(selected.unit_id)
  z.loc[cid,'potential_numeric_gate']=len(selected)>0;z.loc[cid,'potential_priority']=len(selected)>0
  z.loc[cid,'potential_evidence_tier']='；'.join(units['name']+'：'+units.evidence_tier)
  z.loc[cid,'potential_review_category']='统一单元通过数值门槛，详见潜在跟踪方向' if len(selected) else '观察：统一单元证据不足'
  z.loc[cid,'potential_reason']='；'.join(units['name']+'：'+units.potential_reason+'；'+units.scope_sensitivity)
  z.loc[cid,'recommended_focus']='；'.join(selected['name'])
  # A split parent has no defensible scalar aggregate; do not take a max or add overlaps.
  if len(units)==1:
   r=units.iloc[0];z.loc[cid,'potential_evidence_score']=r.potential_evidence_score
   for target,source in [('unified_patents','patents_2026'),('unified_papers','papers_2026_jan_aug'),('unified_applicants','known_applicant_names'),('unified_policy_groups','policy_groups'),('unified_relative_share','relative_share'),('unified_matched_may_relative_share','matched_jan_may_relative_share')]:z.loc[cid,target]=r[source]
 return z

def history():
 baseline=Path(read(BASE/'audit/UNIFIED_POTENTIAL_BASELINE.json')['path'])
 h=pd.read_csv(baseline/'results/industrial_policy_reinforcement.csv')
 h['potential_evidence_score']=np.nan;h['potential_priority']=False
 h['potential_review_category']='历史产业政策线索，未完成统一集合重算'
 h['potential_reason']='历史审阅意见，不能与本次四单元排序比较；'+h.potential_reason.fillna('')
 save(h,'industrial_policy_reinforcement.csv')
