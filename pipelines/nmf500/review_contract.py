"""Bind semantic decisions to the actual inference and displayed evidence."""
import hashlib

REVIEW_INPUTS = ('topic_catalog.csv', 'candidate_evidence.csv', 'hotspot_metrics.csv', 'potential_metrics.csv')


def review_fingerprints(directory):
    return {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in REVIEW_INPUTS}


def require_current_review(decisions, directory):
    if decisions.get('input_sha256') != review_fingerprints(directory):
        raise ValueError('Stale semantic review: changed taxonomy, evidence or metrics require re-review')


def require_policy_review(record, category_id, body):
    if record.get('category_id') != category_id:
        raise ValueError('Policy task review no longer matches its classified topic')
    if record.get('reviewed_body_sha256') != hashlib.sha256(body.encode()).hexdigest():
        raise ValueError('Stale policy review: changed source body requires re-review')
