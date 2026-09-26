"""Materialize documented sample-scope review and policy-family audit."""
from pathlib import Path
import hashlib
import json
import pandas as pd

from build import OUTPUT, csv, dump, safe_excel


def review(out=OUTPUT):
    decisions_path = Path(__file__).with_name('review_decisions.json')
    decisions = json.loads(decisions_path.read_text())
    metrics = pd.read_csv(out / 'hotspot_metrics.csv').set_index('category_id')
    potential = pd.read_csv(out / 'potential_metrics.csv').set_index('category_id')
    evidence = pd.read_csv(out / 'candidate_evidence.csv').fillna('')
    transfer = pd.read_parquet(out / 'transfer_evidence.parquet').set_index('doc_id')
    policy_rows = []
    for record in decisions['policy_records']:
        doc = transfer.loc[record['doc_id']]
        anchor = record['anchor']
        start = str(doc.body).find(anchor)
        if start < 0:
            raise ValueError(f'Policy review anchor not found: {record["doc_id"]} {anchor}')
        lo, hi = max(0, start - 80), min(len(doc.body), start + 600)
        quote = doc.body[lo:hi]
        policy_rows.append({**record, 'category_id': doc.category_id, 'title': doc.title, 'url': doc.url, 'recorded_date': str(doc.date.date()), 'quote_start': lo, 'quote_end': hi, 'quote': quote, 'quote_sha256': hashlib.sha256(quote.encode()).hexdigest(), 'body_sha256': hashlib.sha256(doc.body.encode()).hexdigest()})
    policies = pd.DataFrame(policy_rows)
    csv(policies, out / 'policy_evidence_review.csv')
    families = policies[policies.accepted].groupby('category_id').family.nunique()
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
    parts += ['\n核心2个方向在摘要/日期过滤下未全部达标，因此只列条件性跟踪，不能宣称稳健核心热点。8个新兴方向的“新兴”仅指样本关注份额上升，不表示技术首次出现。3个潜在方向已核读相关政策任务片段并合并同计划政策，仍缺统一专利申请主体及全量同任务审阅，因此是应用线索，不是通过原任务级全部门槛的潜在热点。\n', '\n政策审阅排除了正文落款2006年的《电网运行规则》作为近期政策支持，并合并发改能源〔2024〕1803号的重复转载。完整引文、URL、哈希及政策组见policy_evidence_review.csv。\n']
    report_path = out / 'REPORT.md'
    body = report_path.read_text().split('\n## 样本范围核读后的跟踪方向')[0]
    report_path.write_text(body + ''.join(parts))
    safe_excel({'重算范围': pd.DataFrame([{'item': k, 'value': v} for k, v in main.items()]), '核心条件跟踪': tables['core'], '新兴跟踪': tables['emerging'], '潜在应用线索': tables['potential'], '500主题全指标': metrics.reset_index(), '全部潜在线索指标': potential.reset_index(), '范围审阅': reviews.reset_index(), '政策核读与去重': policies, '代表文献': evidence, '敏感性': pd.read_csv(out / 'sensitivity.csv'), '标签统一变动': pd.read_csv(out / 'uniform_inference_changes.csv'), '迁移校准变动': pd.read_csv(out / 'transfer_recalibration_audit.csv')}, out / '500主题热点审阅结果.xlsx')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    review()
