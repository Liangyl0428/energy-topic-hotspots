import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('review_contract', ROOT / 'pipelines/nmf500/review_contract.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def test_old_approvals_cannot_survive_changed_evidence(tmp_path):
    for name in review.REVIEW_INPUTS:
        (tmp_path / name).write_text('original evidence')
    decision = {'input_sha256': review.review_fingerprints(tmp_path)}
    review.require_current_review(decision, tmp_path)
    (tmp_path / 'candidate_evidence.csv').write_text('new topic membership')
    with pytest.raises(ValueError, match='Stale'):
        review.require_current_review(decision, tmp_path)


def test_released_review_is_bound_to_current_snapshot():
    import json
    decision = json.loads((ROOT / 'pipelines/nmf500/review_decisions_v021.json').read_text())
    review.require_current_review(decision, ROOT / 'assets/nmf500')


def test_policy_review_cannot_survive_changes_outside_displayed_excerpt():
    import hashlib
    body = 'Reviewed policy clause. Additional source context.'
    decision = {'category_id': 'N0001', 'reviewed_body_sha256': hashlib.sha256(body.encode()).hexdigest()}
    review.require_policy_review(decision, 'N0001', body)
    with pytest.raises(ValueError, match='Stale policy'):
        review.require_policy_review(decision, 'N0001', body + ' Changed context.')
    with pytest.raises(ValueError, match='classified topic'):
        review.require_policy_review(decision, 'N0002', body)


def test_released_robustness_uses_every_filter_without_certifying_semantics():
    import pandas as pd
    snapshot = ROOT / 'assets/nmf500'
    metrics = pd.read_csv(snapshot/'reviewed_hotspot_metrics.csv')
    for family in ['core', 'emerging']:
        columns = [c for c in metrics if c.endswith(f'_{family}_candidate')]
        assert len(columns) == 5
        expected = metrics[f'{family}_numeric_candidate'] & metrics[columns].all(axis=1)
        assert expected.equals(metrics[f'{family}_robust_candidate'])
        assert not (metrics[f'{family}_followup'] & metrics[f'{family}_robust_candidate']).any()
    transfer = pd.read_csv(snapshot/'transfer_scores.csv')
    assert transfer.doc_id.is_unique and len(transfer) == 23783
    assert transfer.needs_review.all()
    assert transfer.similarity_filter_passed.any()
    assert not pd.read_csv(snapshot/'reviewed_potential_metrics.csv').fully_verified_potential_hotspot.any()
