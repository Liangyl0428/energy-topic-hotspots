"""Replay all multiyear scenarios plus unified potential evidence from bundled data."""
from common import *
import pandas as pd,numpy as np,subprocess
from multiyear_build import build
from potential_unified_metrics import load_records,policies,with_may
reference=REPOSITORY/'assets/snapshot_20260925/hotspots'
checks=[]

def framecheck(name,a,b):
 try:
  pd.testing.assert_frame_equal(a,b,check_dtype=False,check_exact=False,rtol=1e-9,atol=1e-8)
  ok=True
 except AssertionError as e:print(name,str(e));ok=False
 checks.append(dict(check=name,passed=ok))

z=build()
files=['multiyear_metrics_all750.csv','multiyear_core_components.csv','multiyear_emerging_components.csv','multiyear_core_candidates.csv','multiyear_emerging_candidates.csv','multiyear_annual_trajectories.csv']
files +=['multiyear_'+s+'.csv' for s in ['quality','geometry','dedup','exclude_needs_review','supported_only']]
files +=['multiyear_cutoff_'+s+'.csv' for s in ['2025Q2','2025Q4','2026Q1']]
files +=[f'multiyear_core_{i}y.csv' for i in [1,5]]+[f'multiyear_baseline_{i}y.csv' for i in [2,4]]+[f'multiyear_omit_baseline_{i}.csv' for i in [1,2,3]]
for file in files:framecheck(file,pd.read_csv(BASE/'results'/file),pd.read_csv(reference/'results'/file))
expected=pd.read_csv(reference/'results/potential_unified_metrics.csv').set_index('unit_id');d=load_records();p=policies();strict=with_may(d,p);expanded=with_may(d,p,'expanded')
for col in strict.select_dtypes(include=['number','bool']):
 np.testing.assert_allclose(strict[col],expected.loc[strict.index,col],rtol=1e-9,atol=1e-8);checks.append(dict(check='potential/'+col,passed=True))
for col in ['patents_2026','papers_2026_jan_aug','relative_share','matched_jan_may_relative_share','potential_priority']:
 np.testing.assert_allclose(expanded[col],expected.loc[expanded.index,'expanded_'+col],rtol=1e-9,atol=1e-8);checks.append(dict(check='potential/expanded_'+col,passed=True))
expfiles=[]
if '--experiments' in sys.argv:
 subprocess.run([sys.executable,str(Path(__file__).with_name('multiyear_experiments.py'))],check=True)
 expfiles=['score_ablation_summary.csv','score_ablation_ranks.csv','weight_trials.csv','weight_rank_stability.csv','gate_and_data_sensitivity.csv','data_sensitivity_topic_details.csv','potential_score_components.csv','policy_publisher_sensitivity.csv','potential_unified_sensitivity_summary.csv','potential_unified_sensitivity_details.csv']
 for file in expfiles:framecheck('experiments/'+file,pd.read_csv(BASE/'reliability'/file),pd.read_csv(reference/'reliability'/file))
result=dict(version='750-multiyear-v1',topics=750,passed=all(x['passed'] for x in checks),checks=len(checks),literature_tables_recomputed=len(files),core_with_recorded_reviews=int(z.final_core.sum()),emerging_with_recorded_reviews=int(z.final_emerging.sum()),potential_units=4,potential_strict_selected=int(strict.potential_priority.sum()),potential_dual_scope_selected=int((strict.potential_priority&expanded.potential_priority).sum()),potential_conditional_selected=int((strict.potential_priority&~expanded.potential_priority).sum()),candidate_unit_records=len(d),experiment_files_recomputed=len(expfiles),scope='从冻结季度、情景机构并集与引用汇总重算多年指标，潜在从候选记录重算；不重检索全库，不重新专家审核；历史截止点为回顾性敏感性。',details=checks)
if expfiles:result.update(weight_trials=len(pd.read_csv(BASE/'reliability/weight_trials.csv')),sensitivity_scenarios=len(pd.read_csv(BASE/'reliability/gate_and_data_sensitivity.csv')))
dump(BASE/'REPLAY_VALIDATION.json',result);assert result['passed'];print('MULTIYEAR_REPLAY_PASSED',len(checks),flush=True)
