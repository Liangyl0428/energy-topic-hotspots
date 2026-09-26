"""Frozen NMF500 diagnostics; no threshold tuning or automatic semantic approvals.

Replay from the public snapshot: python pipelines/nmf500/experiments.py
--input assets/nmf500 --output /tmp/hotspot-experiments
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))
from energy_hotspots.scoring import (CORE_WEIGHTS, EMERGING_WEIGHTS, gates,
                                    ordered_scores, percent, rank_scores,
                                    ranking_key, score)

POTENTIAL_WEIGHTS = dict(patents=.35, policies=.30, relative_share=.20, papers=.15)
CORE = dict(annual_volume=60, current_volume=50)
EMERGING = dict(volume=25, baseline=8)


def compare_scores(base, other, k=20):
    a, b = set(ordered_scores(base).head(k).index), set(ordered_scores(other).head(k).index)
    return dict(spearman=float(ranking_key(base).corr(ranking_key(other), method='spearman')),
                top20_overlap=len(a & b) / k,
                max_rank_shift=float((rank_scores(base) - rank_scores(other)).abs().max()))


def reweight(components, weights, omit=None):
    w = pd.Series(weights, dtype=float).reindex(components.columns)
    if omit is not None:
        w.loc[omit] = 0
    if w.isna().any() or (w < 0).any() or w.sum() <= 0:
        raise ValueError('Invalid weights')
    return 100 * components.dot(w / w.sum())


def potential_gates(z, params=None):
    p = dict(papers=10, patents=5, policies=2, relative=1.25, may_patents=2)
    p.update(params or {})
    return pd.DataFrame(dict(papers=z.recent_papers.ge(p['papers']),
        patents=z.confidence_filtered_recent_patents.ge(p['patents']),
        policies=z.confidence_filtered_policy_documents.ge(p['policies']),
        relative=z.confidence_filtered_patent_paper_share_ratio.ge(p['relative']),
        may_relative=z.confidence_filtered_may_share_ratio.ge(p['relative']),
        may_patents=z.confidence_filtered_may_patents.ge(p['may_patents'])))


def potential_components(z):
    pool = pd.Series(True, index=z.index)
    return pd.DataFrame(dict(
        patents=percent(np.log1p(z.confidence_filtered_recent_patents), pool),
        policies=percent(np.log1p(z.confidence_filtered_policy_documents), pool),
        relative_share=percent(np.log(z.confidence_filtered_patent_paper_share_ratio), pool),
        papers=percent(np.log1p(z.recent_papers), pool)))


def transfer_variant(z, transfer, cosine_min, margin_min, remove_source=None):
    """Recount with source-specific denominators; paper counts remain frozen."""
    out = z.copy()
    t = transfer[transfer.topic_1_cosine.ge(cosine_min) & transfer.top1_top2_margin.ge(margin_min)]
    if remove_source:
        t = t[t.source.ne(remove_source)]
    pat = t[t.source.eq('patent') & t.date.between('2025-07-01', '2026-06-30')]
    pol = t[t.source.eq('policy') & t.date.between('2023-07-01', '2026-06-30')]
    may = pat[pat.date.between('2026-01-01', '2026-05-31')]
    def counts(frame):
        return frame.groupby('category_id').size().reindex(z.index, fill_value=0)
    out['confidence_filtered_recent_patents'] = counts(pat)
    out['confidence_filtered_policy_documents'] = counts(pol)
    out['confidence_filtered_may_patents'] = counts(may)
    for rows, papers, target in [(pat, z.recent_papers, 'patent_paper_share_ratio'),
                               (may, z.confidence_filtered_may_papers, 'may_share_ratio')]:
        out['confidence_filtered_' + target] = ((counts(rows) + .5) / (len(rows) + .5 * len(z))
                                               / ((papers + .5) / (papers.sum() + .5 * len(z))))
    return out


def run(inp, output, draws=1500, seed=20260926):
    output.mkdir(parents=True, exist_ok=True)
    read = lambda name: pd.read_csv(inp / name, float_precision='round_trip').set_index('category_id')
    tax, q, ctx = read('topic_catalog.csv'), pd.read_csv(inp / 'quarter_counts.csv'), read('institution_citation_context.csv')
    z, pot = read('reviewed_hotspot_metrics.csv'), read('potential_metrics.csv')
    pot['potential_followup'] = read('reviewed_potential_metrics.csv').potential_followup
    base, cc, ec = score(tax, q, ctx, activity_quarter_min=5, active_year_min=30)
    for family in ['core', 'emerging']:
        np.testing.assert_allclose(base[family + '_score'], z[family + '_score'], atol=1e-9)
    pc = potential_components(pot)
    np.testing.assert_allclose(reweight(pc, POTENTIAL_WEIGHTS), pot.potential_signal_score)
    components = dict(core=cc, emerging=ec, potential=pc)
    weights = dict(core=CORE_WEIGHTS, emerging=EMERGING_WEIGHTS, potential=POTENTIAL_WEIGHTS)
    base_gates = dict(core=gates(base, 'core', CORE).drop(columns='scope'),
                      emerging=gates(base, 'emerging', EMERGING).drop(columns='scope'),
                      potential=potential_gates(pot))
    baseline_masks = {f: g.all(axis=1) for f, g in base_gates.items()}
    for f, m in baseline_masks.items():
        assert m.equals((pot if f == 'potential' else z)[f + '_numeric_candidate'])
    baselines = {f: reweight(c, weights[f]) for f, c in components.items()}
    followups = {f: (pot if f == 'potential' else z)[f + '_followup'] for f in components}
    metrics, memberships = [], []

    def record(family, kind, scenario, values, mask):
        orig, reviewed = baseline_masks[family], followups[family]
        union = int((orig | mask).sum())
        metrics.append(dict(family=family, kind=kind, scenario=scenario,
            **compare_scores(baselines[family], values), numeric_candidates=int(mask.sum()),
            baseline_retained=int((orig & mask).sum()),
            candidate_jaccard=float((orig & mask).sum() / union) if union else 1.,
            frozen_review_followups_retained=int((reviewed & mask).sum()),
            new_numeric_candidates_pending_review=int((mask & ~orig).sum())))
        for cid in mask.index[mask | orig | reviewed]:
            memberships.append(dict(family=family, kind=kind, scenario=scenario,
                category_id=cid, numeric_pass=bool(mask[cid]), baseline_pass=bool(orig[cid]),
                frozen_review_followup=bool(reviewed[cid])))

    perturbations, rank_intervals = [], []
    rng = np.random.default_rng(seed)
    for f, comp in components.items():
        orig = baselines[f]
        for omitted in comp:
            record(f, 'score_component_ablation', 'without_' + omitted,
                   reweight(comp, weights[f], omitted), baseline_masks[f])
        ranks = []
        for trial in range(draws):
            # Independent Uniform[0.8,1.2] multipliers, followed by normalization.
            w = pd.Series(weights[f]) * rng.uniform(.8, 1.2, len(comp.columns))
            w /= w.sum()
            values = reweight(comp, w)
            perturbations.append(dict(family=f, trial=trial, **compare_scores(orig, values),
                                      **{'weight_' + k: float(v) for k, v in w.items()}))
            ranks.append(rank_scores(values).to_numpy())
        ranks = np.asarray(ranks)
        for i, cid in enumerate(comp.index):
            rank_intervals.append(dict(family=f, category_id=cid, baseline_rank=rank_scores(orig).loc[cid],
                rank_p025=float(np.quantile(ranks[:, i], .025)), rank_median=float(np.median(ranks[:, i])),
                rank_p975=float(np.quantile(ranks[:, i], .975)), top20_fraction=float((ranks[:, i] <= 20).mean())))
        for key in base_gates[f]:
            record(f, 'gate_ablation', 'without_' + key, orig, base_gates[f].drop(columns=key).all(axis=1))
        record(f, 'semantic_review_ablation', 'numeric_only_no_scope_review', orig, baseline_masks[f])
        if f != 'potential':
            record(f, 'data_robustness', 'require_all_data_filters_or_direction', orig, z[f + '_robust_candidate'])

    for f, defaults in [('core', CORE), ('emerging', EMERGING)]:
        for factor in [.8, 1.2]:
            params = {k: v * factor for k, v in defaults.items()}
            zz, c, e = score(tax, q, ctx, activity_quarter_min=5 * factor, active_year_min=30 * factor)
            record(f, 'threshold_joint', f'count_thresholds_x{factor}', zz[f + '_score'], gates(zz, f, params).drop(columns='scope').all(axis=1))
        zz, _, _ = score(tax, q, ctx)  # Original full-corpus count thresholds.
        record(f, 'threshold_legacy', 'original_750_count_rules_on_sample', zz[f + '_score'], gates(zz, f).drop(columns='scope').all(axis=1))
    grids = {'core': dict(annual_volume=[48,72], current_volume=[40,60], current_share=[.7,.9], quarter_fraction=[.5,1.]),
             'emerging': dict(volume=[20,30], baseline=[6,10], multiyear=[1.15,1.35], recent_growth=[1.05,1.25], quarters=[2,4], peak=[1.,1.15], lower95=[1.,1.15], qvalue=[.01,.1])}
    for f, grid in grids.items():
        for key, values in grid.items():
            for value in values:
                params = {**(CORE if f == 'core' else EMERGING), key: value}
                record(f, 'threshold_one_at_time', f'{key}={value}', baselines[f], gates(base, f, params).drop(columns='scope').all(axis=1))
    for years in [1,5]:
        zz, _, _ = score(tax,q,ctx,core_years=years,activity_quarter_min=5,active_year_min=30)
        record('core','window',f'core_{years}y',zz.core_score,gates(zz,'core',CORE).drop(columns='scope').all(axis=1))
    for years, omit in [(2,None),(4,None),(3,1),(3,2),(3,3)]:
        zz, _, _ = score(tax,q,ctx,baseline_years=years,omit_baseline=omit,activity_quarter_min=5,active_year_min=30)
        record('emerging','window',f'baseline_{years}y_omit_{omit}',zz.emerging_score,gates(zz,'emerging',EMERGING).drop(columns='scope').all(axis=1))
    for key, values in dict(papers=[8,12],patents=[4,6],policies=[1,3],relative=[1.1,1.4],may_patents=[1,3]).items():
        for value in values:
            record('potential','threshold_one_at_time',f'{key}={value}',baselines['potential'],potential_gates(pot,{key:value}).all(axis=1))

    # Small, public numeric transfer table; no source bodies or vectors needed.
    transfer = pd.read_csv(inp / 'transfer_scores.csv', float_precision='round_trip')
    transfer['date'] = pd.to_datetime(transfer.date)
    threshold = json.loads((inp / 'confidence_thresholds.json').read_text())
    c, m = threshold['cosine_p10'], threshold['margin_p10']
    scenarios = [('baseline',c,m,None),('no_confidence_filter',-1.,0.,None),
                 ('no_cosine_gate',-1.,m,None),('no_margin_gate',c,0.,None),
                 ('cosine_minus_0.02',c-.02,m,None),('cosine_plus_0.02',c+.02,m,None),
                 ('margin_half',c,m*.5,None),('margin_double',c,m*2,None),
                 ('remove_patents',c,m,'patent'),('remove_policies',c,m,'policy')]
    for name, cmin, mmin, source in scenarios:
        pp = transfer_variant(pot,transfer,cmin,mmin,source)
        mask = potential_gates(pp).all(axis=1)
        if name == 'baseline':
            assert mask.equals(baseline_masks['potential'])
            for col in ['recent_patents','policy_documents','patent_paper_share_ratio','may_share_ratio','may_patents']:
                np.testing.assert_allclose(pp['confidence_filtered_'+col],pot['confidence_filtered_'+col])
        record('potential','transfer_confidence_or_source',name,reweight(potential_components(pp),POTENTIAL_WEIGHTS),mask)
    policy = pd.read_csv(inp / 'policy_evidence_review.csv')
    policy = policy[policy.accepted]
    policy_rows = []
    for cid in pot.index[pot.potential_followup]:
        own = policy[policy.category_id.eq(cid)]
        for family in sorted(own.family.unique()):
            left = own[own.family.ne(family)].family.nunique()
            policy_rows.append(dict(category_id=cid,removed_family=family,remaining_policy_families=left,
                retains_two_policy_families=bool(left>=2)))
    frames = dict(scenarios=pd.DataFrame(metrics),scenario_memberships=pd.DataFrame(memberships),
                  weight_draws=pd.DataFrame(perturbations),rank_intervals=pd.DataFrame(rank_intervals),
                  policy_family_loo=pd.DataFrame(policy_rows))
    for name, frame in frames.items():
        frame.to_csv(output / (name+'.csv'), index=False, encoding='utf-8-sig')
    weight_summary = frames['weight_draws'].groupby('family')[['spearman','top20_overlap','max_rank_shift']].agg(['min','median','max'])
    weight_summary.to_csv(output/'weight_summary.csv',encoding='utf-8-sig')
    protocol = dict(seed=seed,draws_per_family=draws,weight_multipliers=[.8,1.2],top_k=20,
        diagnostic_scenarios=len(metrics),experiment_design='post-hoc descriptive diagnostics; not preregistered or used to tune selection',
        ranking='10-decimal canonical ties; top20 ties broken by category ID; rank intervals use competition ranks, so top20_fraction can include ties beyond 20',
        eligibility='Weights affect ranking only. Frozen numeric gates and semantic decisions; newly passing topics remain unreviewed.',
        uncertainty='Perturbation intervals are scenario ranges, not statistical confidence intervals. No expert accuracy or causal claim.',
        window_limit='Citation cohort context fixed to 2023–2025; windows test count/institution horizons, not a full historical backtest.',
        potential_limit='No applicant-diversity data. Policy-family LOO is on the three reviewed leads only, not all 500 themes.')
    (output/'PROTOCOL.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n')
    report = '# NMF500 灵敏度与消融实验\n\n' + json.dumps(protocol,ensure_ascii=False,indent=2) + '\n\n## 权重扰动\n\n' + weight_summary.to_markdown() + '\n\n## 逐项评分消融\n\n' + frames['scenarios'].query("kind == 'score_component_ablation'").to_markdown(index=False) + '\n\n## 时间窗口与旧门槛\n\n' + frames['scenarios'][frames['scenarios'].kind.isin(['window','threshold_legacy'])].to_markdown(index=False) + '\n\n## 政策组留一法\n\n' + frames['policy_family_loo'].to_markdown(index=False) + '\n\n完整门槛/来源/置信过滤实验见 scenarios.csv；逐主题名单见 scenario_memberships.csv。移除语义审阅显示数值候选池大小，不代表这些候选真实有效。原有三种数据过滤实验另见输入目录 sensitivity.csv。\n'
    (output/'REPORT.md').write_text(report)
    print(json.dumps(protocol,ensure_ascii=False),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=REPO/'assets/nmf500')
    parser.add_argument('--output',type=Path,default=REPO/'outputs/nmf500/experiments')
    parser.add_argument('--draws',type=int,default=1500)
    args = parser.parse_args()
    run(args.input,args.output,args.draws)
