"""Materialize documented sample-scope review and policy-family audit."""
from pathlib import Path
import hashlib
import json
import pandas as pd

from build import OUTPUT, csv, dump, safe_excel
from review_contract import require_current_review, require_policy_review


def review(out=OUTPUT):
    decisions_path = Path(__file__).with_name('review_decisions_v021.json')
    decisions = json.loads(decisions_path.read_text())
    require_current_review(decisions, out)
    metrics = pd.read_csv(out / 'hotspot_metrics.csv').set_index('category_id')
    potential = pd.read_csv(out / 'potential_metrics.csv').set_index('category_id')
    evidence = pd.read_csv(out / 'candidate_evidence.csv').fillna('')
    transfer = pd.read_parquet(out / 'transfer_evidence.parquet').set_index('doc_id')
    policy_rows = []
    for record in decisions['policy_records']:
        doc = transfer.loc[record['doc_id']]
        require_policy_review(record, doc.category_id, doc.body)
        anchor = record['anchor']
        start = str(doc.body).find(anchor)
        if start < 0:
            raise ValueError(f'Policy review anchor not found: {record["doc_id"]} {anchor}')
        lo, hi = max(0, start - 80), min(len(doc.body), start + 600)
        quote = doc.body[lo:hi]
        policy_rows.append({**record, 'category_id': doc.category_id, 'title': doc.title, 'url': doc.url, 'recorded_date': str(doc.date.date()), 'quote_start': lo, 'quote_end': hi, 'quote': quote, 'quote_sha256': hashlib.sha256(quote.encode()).hexdigest(), 'body_sha256': hashlib.sha256(doc.body.encode()).hexdigest()})
    policies = pd.DataFrame(policy_rows)
    csv(policies, out / 'policy_evidence_review.csv')
    eligible_policy = policies.accepted & policies.recorded_date.between('2023-07-01','2026-06-30')
    if 'reviewed_issue_date' in policies:
        known_date = policies.reviewed_issue_date.fillna('')
        eligible_policy &= known_date.eq('') | known_date.between('2023-07-01','2026-06-30')
    families = policies[eligible_policy].groupby('category_id').family.nunique()
    potential['reviewed_policy_family_count'] = families.reindex(potential.index, fill_value=0)
    potential['potential_followup'] = potential.potential_numeric_candidate & potential.index.isin(decisions['potential_followup']) & potential.reviewed_policy_family_count.ge(2)
    potential['fully_verified_potential_hotspot'] = False
    review_rows = []
    union = metrics.index[metrics.core_numeric_candidate | metrics.emerging_numeric_candidate].union(potential.index[potential.potential_numeric_candidate])
    for cid in union:
        roles = [name for name in ['core', 'emerging', 'potential'] if cid in decisions[name + '_followup']]
        labels = [decisions[name + '_followup'][cid][0] for name in roles]
        reasons = [decisions[name + '_followup'][cid][1] for name in roles]
        seen = evidence[evidence.category_id.eq(cid)]
        review_rows.append({'category_id': cid, 'review_display_name': labels[0] if labels else metrics.loc[cid, 'name'], 'core_followup': cid in decisions['core_followup'], 'emerging_followup': cid in decisions['emerging_followup'], 'potential_followup': bool(potential.loc[cid, 'potential_followup']), 'decision': '有样本依据的条件性跟踪方向' if roles else '范围过宽或样本混杂，暂缓认定', 'reason': ' | '.join(reasons) if reasons else decisions['hold_reasons'].get(cid, '未完成充分范围审阅'), 'displayed_paper_ids': ' | '.join(seen[seen.source.eq('paper')].doc_id), 'displayed_transfer_ids': ' | '.join(seen[~seen.source.eq('paper')].doc_id), 'reviewer_type': 'agent_assisted', 'expert_confirmed': False, 'topic_purity_estimated': False})
    reviews = pd.DataFrame(review_rows).set_index('category_id')
    csv(reviews.reset_index(), out / 'scope_review.csv')
    for col in ['core_followup', 'emerging_followup', 'potential_followup']:
        metrics[col] = reviews[col].reindex(metrics.index, fill_value=False)
    for family in ['core', 'emerging']:
        metrics[family + '_followup'] &= metrics[family + '_numeric_candidate']
    metrics['review_display_name'] = reviews.review_display_name.reindex(metrics.index).fillna(metrics.name)
    metrics['review_reason'] = reviews.reason.reindex(metrics.index).fillna('未进入候选范围审阅')
    metrics['scope_review_status'] = reviews.decision.reindex(metrics.index).fillna('未进入候选范围审阅')
    csv(metrics.reset_index(), out / 'reviewed_hotspot_metrics.csv')
    potential['review_display_name'] = metrics.review_display_name
    csv(potential.reset_index(), out / 'reviewed_potential_metrics.csv')
    tables = {}
    for family in ['core', 'emerging']:
        frame = metrics[metrics[family + '_followup']].sort_values(family + '_score', ascending=False).reset_index()
        csv(frame, out / f'{family}_followup.csv')
        tables[family] = frame
    tables['potential'] = potential[potential.potential_followup].sort_values('potential_signal_score', ascending=False).reset_index()
    csv(tables['potential'], out / 'potential_followup.csv')
    summary = {'reviewed_numeric_candidate_topics': len(reviews), 'core_conditional_followup': len(tables['core']), 'core_followup_passing_all_data_filters': int(tables['core'].core_robust_candidate.sum()), 'emerging_followup': len(tables['emerging']), 'potential_application_leads': len(tables['potential']), 'fully_verified_potential_hotspots': 0, 'policy_records_reviewed': len(policies), 'old_reposted_policy_excluded': int((~policies.accepted).sum()), 'scope': decisions['scope'], 'semantic_review_sha256': hashlib.sha256(decisions_path.read_bytes()).hexdigest()}
    dump(out / 'REVIEW_SUMMARY.json', summary)
    main = json.loads((out / 'SUMMARY.json').read_text())
    main.update(summary)
    dump(out / 'SUMMARY.json', main)
    parts = ['\n## 样本范围核读后的跟踪方向\n', '核读代表文献后，通用词或任务混杂的数值候选暂缓认定；所有保留方向仍为AI辅助初审，未经过独立专家认定。\n']
    for family, label in [('core', '核心条件性跟踪'), ('emerging', '新兴跟踪'), ('potential', '潜在应用线索')]:
        frame = tables[family]
        cols = ['category_id', 'review_display_name'] + (['potential_signal_score', 'reviewed_policy_family_count'] if family == 'potential' else [family + '_score', 'recent_papers', 'multiyear_share_ratio'])
        parts += [f'\n### {label}\n\n', frame[cols].to_markdown(index=False) + '\n']
    parts += [f'\n本次保留核心条件跟踪{len(tables["core"])}个、新兴条件跟踪{len(tables["emerging"])}个、潜在应用线索{len(tables["potential"])}个。稳健标记要求通过全部五种过滤下的完整数值门槛；条件跟踪不等于稳健热点。新兴只表示样本份额增长；潜在线索仍缺申请主体多样性及全量同任务验证。\n', '\n政策按实际发布日期和政策组核查，旧文重发不能作为新增支持；完整引文、URL和哈希见policy_evidence_review.csv。\n']
    report_path = out / 'REPORT.md'
    body = report_path.read_text().split('\n## 样本范围核读后的跟踪方向')[0]
    report_path.write_text(body + ''.join(parts))
    safe_excel({'重算范围': pd.DataFrame([{'item': k, 'value': v} for k, v in main.items()]), '核心条件跟踪': tables['core'], '新兴跟踪': tables['emerging'], '潜在应用线索': tables['potential'], '500主题全指标': metrics.reset_index(), '全部潜在线索指标': potential.reset_index(), '范围审阅': reviews.reset_index(), '政策核读与去重': policies, '代表文献': evidence, '敏感性': pd.read_csv(out / 'sensitivity.csv'), '标签统一变动': pd.read_csv(out / 'uniform_inference_changes.csv'), '迁移校准变动': pd.read_csv(out / 'transfer_recalibration_audit.csv')}, out / '500主题热点审阅结果.xlsx')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    review()
