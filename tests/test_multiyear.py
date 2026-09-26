import pandas as pd
import pytest
from energy_hotspots.scoring import score,windows
from energy_hotspots.replay import replay

@pytest.fixture
def inputs():
 idx=pd.Index(['A','B'],name='category_id')
 tax=pd.DataFrame(dict(name=['A','B'],domain=['电力','电力'],status=['方向候选']*2,analysis_scope=['能源电力直接相关']*2),index=idx)
 q=pd.DataFrame([dict(category_id=t,period=str(p),papers=n) for p in pd.period_range('2020Q1','2026Q2',freq='Q') for t,n in [('A',100),('B',300)]])
 c=pd.DataFrame(index=idx)
 for i in range(5):c[f'year{i}_institutions']=[10,30]
 for i in [1,3,5]:c[f'core_institutions_{i}y']=[10*i,30*i]
 c['recent_institutions']=[10,30];c['citation_cohort_percentile']=[.3,.7]
 return tax,q,c

def test_windows_are_disjoint():
 w=windows();assert len(set(sum(w,[])))==20
 assert w[0]==['2025Q3','2025Q4','2026Q1','2026Q2']
 assert w[3][0]=='2022Q3'

def test_constant_share_does_not_become_emerging(inputs):
 z,_,_=score(*inputs)
 assert z.multiyear_share_ratio.eq(1).all() and not z.emerging_eligible.any()
 assert z.core_eligible.all()

def test_recent_jump_never_enters_baseline(inputs):
 tax,q,c=inputs;base,_,_=score(tax,q,c)
 q.loc[q.category_id.eq('A')&q.period.isin(windows()[0]),'papers']=400
 z,_,_=score(tax,q,c)
 pd.testing.assert_series_equal(z.baseline_mean_share,base.baseline_mean_share)
 assert z.loc['A','multiyear_share_ratio']>1.5

def test_window_volume_scales_by_year(inputs):
 for years in [1,3,5]:
  z,_,_=score(*inputs,core_years=years)
  assert z.loc['A','core_papers']==400*years
  assert z.loc['A','core_active_quarters']==4*years
  assert z.core_eligible.all()

def test_missing_background_is_not_zero_filled(inputs):
 tax,q,c=inputs
 with pytest.raises(ValueError,match='Incomplete'):score(tax,q[q.period.ne('2021Q3')],c)

def test_patent_source_cannot_enter(inputs):
 tax,q,c=inputs;q['source']='paper';q.loc[0,'source']='patent'
 with pytest.raises(ValueError,match='Literature only'):score(tax,q,c)

def test_one_missing_topic_quarter_is_not_a_measured_zero(inputs):
 tax,q,c=inputs
 q=q[~(q.category_id.eq('A')&q.period.eq('2024Q1'))]
 with pytest.raises(ValueError,match='Incomplete topic-quarter'):score(tax,q,c)

@pytest.mark.parametrize('mode',['missing_row','missing_value','infinity'])
def test_incomplete_context_is_rejected(inputs,mode):
 tax,q,c=inputs
 c=c.astype(float)
 if mode=='missing_row':c=c.drop('A')
 else:c.loc['A','recent_institutions']=float('nan') if mode=='missing_value' else float('inf')
 with pytest.raises(ValueError,match='[Cc]ontext'):score(tax,q,c)

def test_unknown_hotspot_family_is_not_treated_as_emerging(inputs):
 from energy_hotspots.scoring import gates
 z,_,_=score(*inputs)
 with pytest.raises(ValueError,match='family'):gates(z,'typo')

def test_sample_activity_thresholds_do_not_change_counts_or_growth(inputs):
 tax,q,c=inputs
 q=q.copy();q['papers']=q.papers//10
 full,_,_=score(tax,q,c)
 sample,_,_=score(tax,q,c,activity_quarter_min=5,active_year_min=30)
 assert full.loc['A','core_active_quarters']==0
 assert sample.loc['A','core_active_quarters']==12
 assert sample.loc['A','core_active_years']==3
 pd.testing.assert_series_equal(full.core_papers,sample.core_papers)
 pd.testing.assert_series_equal(full.multiyear_share_ratio,sample.multiyear_share_ratio)
 assert not sample.emerging_eligible.any()

def test_multiyear_snapshot_replay(tmp_path):
 r=replay(tmp_path/'replay')
 assert r['passed'] and r['topics']==750
 assert r['core_with_recorded_reviews']==12 and r['emerging_with_recorded_reviews']==22
 assert r['potential_dual_scope_selected']==2 and r['potential_conditional_selected']==1
