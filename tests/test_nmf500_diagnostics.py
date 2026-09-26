import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('hotspot_nmf_diagnostics',REPO/'pipelines/nmf500/experiments.py')
diagnostics=importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostics)


def test_ablation_renormalizes_remaining_weights():
    c=pd.DataFrame({'a':[1.,0.],'b':[0.,1.]})
    np.testing.assert_allclose(diagnostics.reweight(c,{'a':.9,'b':.1},'a'),[0.,100.])
    with pytest.raises(ValueError):
        diagnostics.reweight(c,{'a':-1.,'b':1.})


def test_tie_break_is_deterministic():
    a=pd.Series([1.,1.,0.],index=['B','A','C'])
    assert diagnostics.ordered_scores(a).index.tolist()==['A','B','C']
    assert diagnostics.compare_scores(a,a,k=2)['top20_overlap']==1


def test_public_snapshot_replays_all_diagnostic_scenarios(tmp_path):
    diagnostics.run(REPO/'assets/nmf500',tmp_path,draws=3)
    s=pd.read_csv(tmp_path/'scenarios.csv')
    assert len(s)==96
    weights=pd.read_csv(tmp_path/'weight_draws.csv')
    assert len(weights)==9
    np.testing.assert_allclose(weights.filter(like='weight_').sum(axis=1),1.)
    assert s[s.scenario.isin(['remove_patents','remove_policies'])].numeric_candidates.eq(0).all()
    assert len(s[s.kind.eq('score_component_ablation')])==14
    assert not pd.read_csv(tmp_path/'policy_family_loo.csv').retains_two_policy_families.any()
    assert json.loads((tmp_path/'PROTOCOL.json').read_text())['draws_per_family']==3
