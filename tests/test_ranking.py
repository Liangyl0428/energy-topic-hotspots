from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from energy_hotspots.scoring import ordered_scores, ranking_key, rank_scores


@pytest.mark.parametrize('permutation', [[0, 1, 2, 3, 4], [4, 2, 0, 3, 1]])
@pytest.mark.parametrize('tail', [0.0, np.spacing(79.09861325115563)])
def test_equal_and_machine_precision_ties_have_canonical_order(permutation, tail):
    # C0271/C0378 reproduce the CPU-dependent pair from the published snapshot.
    scores = pd.Series(
        [79.09861325115563 + tail, 79.09861325115563, 80.0, 80.0, 70.0],
        index=['C0378', 'C0271', 'C0002', 'C0001', 'C0750'],
    ).iloc[permutation]
    original = scores.copy()
    ordered = ordered_scores(scores)
    assert list(ordered.index) == ['C0001', 'C0002', 'C0271', 'C0378', 'C0750']
    assert list(rank_scores(scores).loc[ordered.index]) == [1, 1, 3, 3, 5]
    pd.testing.assert_series_equal(ordered, original.loc[ordered.index])
    pd.testing.assert_series_equal(scores, original)


def test_real_score_differences_are_preserved():
    scores = pd.Series([80.0, 80.0 + 1e-8], index=['A', 'Z'])
    assert list(ordered_scores(scores).index) == ['Z', 'A']
    assert rank_scores(scores).to_dict() == {'A': 2.0, 'Z': 1.0}


def test_rank_statistics_ignore_float_tail():
    scores = pd.Series([98.21263482280433, 98.21263482280432, 79.0, 60.0])
    perturbed = scores.copy()
    perturbed.iloc[0] = scores.iloc[1]
    pd.testing.assert_series_equal(rank_scores(scores), rank_scores(perturbed))
    assert spearmanr(ranking_key(scores), ranking_key(perturbed)).statistic == 1.0


def test_pipeline_and_public_scoring_are_identical():
    root = Path(__file__).resolve().parents[1]
    assert (root/'src/energy_hotspots/scoring.py').read_bytes() == (
        root/'pipelines/hotspots/multiyear_scoring.py'
    ).read_bytes()
