"""核心与新兴热点的核心算法。

score(): 指标与加权评分；gates(): 逐项入选条件。
完整名单还需 multiyear_build.build() 的数据范围检查和样本判断。
代码导读见 docs/ALGORITHM.md。
"""
import numpy as np
import pandas as pd
from scipy.stats import norm

CORE_WEIGHTS={'volume':.40,'citation':.20,'institutions':.15,'persistence':.15,'current':.10}
EMERGING_WEIGHTS={'multiyear_growth':.35,'recent_growth':.25,'trend':.20,'quarter_consistency':.10,'institution_expansion':.10}

# Ignore machine-precision differences in 0--100 scores for ranking only.
RANK_DECIMALS = 10


def ranking_key(scores):
    """Canonical tie groups; retain unrounded scores for reporting and gates."""
    return scores.round(RANK_DECIMALS)


def rank_scores(scores):
    """Competition ranks: tied scores share the minimum position."""
    return ranking_key(scores).rank(ascending=False, method='min')


def ordered_scores(scores):
    """Original scores ordered by canonical score descending, then ID ascending."""
    order = ranking_key(scores).sort_index().sort_values(ascending=False, kind='stable')
    return scores.loc[order.index]


def percent(s,pool):
    ref=s[pool&s.notna()].sort_values().to_numpy()
    return pd.Series(np.searchsorted(ref,s.fillna(-np.inf),side='right')/len(ref),index=s.index).clip(0,1) if len(ref) else pd.Series(0.,index=s.index)

def bh(p):
    v=np.asarray(p);order=np.argsort(v);out=np.empty(len(v));out[order]=np.minimum(1,np.minimum.accumulate((v[order]*len(v)/np.arange(1,len(v)+1))[::-1])[::-1]);return out

def windows(end='2026Q2'):
    e=pd.Period(end,freq='Q')
    return [pd.period_range(end=e-4*i,periods=4,freq='Q').astype(str).tolist() for i in range(5)]

def score(tax,q,context,end='2026Q2',core_years=3,baseline_years=3,omit_baseline=None):
    """输入目录、季度计数及机构引用汇总；返回指标表、核心成分、新兴成分。"""
    if core_years not in [1,3,5] or baseline_years not in [2,3,4]:raise ValueError('Unsupported prespecified window')
    if not tax.index.is_unique or not set(q.category_id)<=set(tax.index):raise ValueError('Invalid taxonomy IDs')
    if q.duplicated(['category_id','period']).any():raise ValueError('Duplicate topic-quarter')
    if 'source' in q and not q.source.eq('paper').all():raise ValueError('Literature only')
    if not np.isfinite(q.papers).all() or (q.papers<0).any() or (q.papers%1!=0).any():raise ValueError('Nonnegative integer counts required')
    ws=windows(end);allq=sum(ws,[])
    if not set(allq)<=set(q.period):raise ValueError('Incomplete five-year quarterly coverage')
    n=q.pivot(index='category_id',columns='period',values='papers').reindex(index=tax.index,columns=allq).fillna(0)
    den=n.sum();K=len(tax)
    if den.le(0).any():raise ValueError('Missing quarter background')
    sm=(n+.5)/(den+.5*K)
    z=tax[['name','domain','status','analysis_scope']].copy()
    z['admissible_pool']=~tax.status.isin(['混杂待重分','外围或非研究文本'])&~tax.domain.isin(['其他基础与关联学科','制造与通用装置'])
    z['direct_energy']=tax.analysis_scope.eq('能源电力直接相关');pool=z.admissible_pool
    for i,w in enumerate(ws):
        z[f'year{i}_papers']=n[w].sum(axis=1).astype(int)
        z[f'year{i}_denominator']=int(den[w].sum())
        z[f'year{i}_share']=(z[f'year{i}_papers']+.5)/(den[w].sum()+.5*K)
    z['recent_papers']=z.year0_papers;z['previous_papers']=z.year1_papers
    z['share_growth_ratio']=z.year0_share/z.year1_share
    ids=[i for i in range(1,baseline_years+1) if i!=omit_baseline]
    if len(ids)<2:raise ValueError('Need at least two background years')
    z['baseline_years_used']=len(ids)
    z['baseline_papers']=z[[f'year{i}_papers' for i in ids]].sum(axis=1)
    z['baseline_annual_mean_papers']=z.baseline_papers/len(ids)
    z['baseline_mean_share']=z[[f'year{i}_share' for i in ids]].mean(axis=1)
    z['multiyear_share_ratio']=z.year0_share/z.baseline_mean_share
    z['historical_peak_ratio']=z.year0_share/z[[f'year{i}_share' for i in range(1,5)]].max(axis=1)
    # OLS slope of 3 disjoint annual log shares, oldest -> newest; descriptive, no p-value.
    z['three_year_log_share_slope']=(np.log(z.year0_share)-np.log(z.year2_share))/2
    z['growing_quarters']=(sm[ws[0]].to_numpy()>sm[ws[1]].to_numpy()).sum(axis=1)
    z['active_quarters']=n[ws[0]].ge(25).sum(axis=1)
    cw=sum(ws[:core_years],[])
    z['core_years']=core_years;z['core_papers']=n[cw].sum(axis=1).astype(int)
    z['core_mean_annual_share']=z[[f'year{i}_share' for i in range(core_years)]].mean(axis=1)
    z['core_active_quarters']=n[cw].ge(25).sum(axis=1)
    z['core_active_years']=z[[f'year{i}_papers' for i in range(core_years)]].ge(150).sum(axis=1)
    z['core_persistence']=z.core_active_quarters/(4*core_years)
    z['recent_institutions']=context.recent_institutions.reindex(z.index)
    z['core_institutions']=context[f'core_institutions_{core_years}y'].reindex(z.index)
    z['baseline_mean_institutions']=context[[f'year{i}_institutions' for i in ids]].mean(axis=1).reindex(z.index)
    z['institution_expansion']=(z.recent_institutions+1)/(z.baseline_mean_institutions+1)
    z['citation_cohort_percentile']=context.citation_cohort_percentile.reindex(z.index).fillna(0)
    # Count-only diagnostic compares disjoint recent vs pooled background; not trend-model confidence.
    N0=sum(z[f'year{i}_denominator'].iloc[0] for i in ids);N1=z.year0_denominator.iloc[0]
    z['pooled_baseline_share']=(z.baseline_papers+.5)/(N0+.5*K)
    z['pooled_share_ratio']=z.year0_share/z.pooled_baseline_share
    sigma=np.sqrt(1/(z.recent_papers+.5)+1/(z.baseline_papers+.5))
    z['share_ratio_lower95']=np.exp(np.log(z.pooled_share_ratio)-1.96*sigma)
    p0=(z.recent_papers+z.baseline_papers)/(N1+N0);se=np.sqrt(p0*(1-p0)*(1/N1+1/N0))
    z['growth_count_pvalue']=norm.sf(((z.recent_papers/N1-z.baseline_papers/N0)/se).fillna(0))
    z['growth_count_qvalue']=bh(z.growth_count_pvalue)
    cc=pd.DataFrame({'volume':percent(z.core_mean_annual_share,pool),'citation':percent(z.citation_cohort_percentile,pool),'institutions':percent(z.core_institutions,pool),'persistence':z.core_persistence,'current':percent(z.year0_share,pool)})
    ec=pd.DataFrame({'multiyear_growth':percent(np.log(z.multiyear_share_ratio),pool),'recent_growth':percent(np.log(z.share_growth_ratio),pool),'trend':percent(z.three_year_log_share_slope,pool),'quarter_consistency':z.growing_quarters/4,'institution_expansion':percent(z.institution_expansion,pool)})
    z['core_score']=100*cc.dot(pd.Series(CORE_WEIGHTS));z['emerging_score']=100*ec.dot(pd.Series(EMERGING_WEIGHTS))
    z['core_eligible']=gates(z,'core').all(axis=1);z['emerging_eligible']=gates(z,'emerging').all(axis=1)
    z['trajectory']=np.select([z.share_growth_ratio.lt(1),z.historical_peak_ratio.lt(1),z.multiyear_share_ratio.ge(1.25)&z.share_growth_ratio.ge(1.15)],['近期份额下降','历史峰值以下的恢复或波动','多年背景上持续抬升'],default='平稳或增长证据不足')
    z['end_quarter']=end
    return z,cc,ec

def gates(z,family,p=None):
    """逐条返回数值入选条件；调用者按行合并，并另行结合样本范围判断。"""
    p=p or {};scope=z.admissible_pool&z.direct_energy
    if family=='core':return pd.DataFrame({'scope':scope,'annual_volume':z.core_papers.ge(p.get('annual_volume',250)*z.core_years),'active_years':z.core_active_years.ge(np.ceil(p.get('year_fraction',1.)*z.core_years)),'persistence':z.core_active_quarters.ge(np.ceil(p.get('quarter_fraction',.75)*4*z.core_years)),'current_volume':z.recent_papers.ge(p.get('current_volume',250)),'current_share':z.share_growth_ratio.ge(p.get('current_share',.8))})
    out={'scope':scope,'volume':z.recent_papers.ge(p.get('volume',100)),'baseline':z.baseline_annual_mean_papers.ge(p.get('baseline',50)),'multiyear':z.multiyear_share_ratio.ge(p.get('multiyear',1.25)),'recent_growth':z.share_growth_ratio.ge(p.get('recent_growth',1.15)),'quarters':z.growing_quarters.ge(p.get('quarters',3)),'trend':z.three_year_log_share_slope.gt(p.get('trend',0)),'peak':z.historical_peak_ratio.ge(p.get('peak',1.05)),'lower95':z.share_ratio_lower95.gt(p.get('lower95',1.05)),'qvalue':z.growth_count_qvalue.lt(p.get('qvalue',.05))}
    if 'robust_min_ratio' in z:out['data_direction']=z.robust_min_ratio.ge(p.get('robust',1.1))
    return pd.DataFrame(out)
