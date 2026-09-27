"""Exercise full-data aggregation and diagnostics on a constructed census."""
from pathlib import Path
import importlib.util
import json
import duckdb
import numpy as np
import pandas as pd
import pytest

REPO=Path(__file__).resolve().parents[1]


def load(name):
    spec=importlib.util.spec_from_file_location('full_'+name,REPO/'pipelines/full_nmf'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_full_experiments_recount_and_replay(tmp_path,monkeypatch):
    build=load('build');exp=load('experiments')
    monkeypatch.setattr(build,'ROOT',tmp_path);monkeypatch.setattr(exp,'ROOT',tmp_path)
    source=tmp_path/'classification';(source/'assignments').mkdir(parents=True)
    metadata=tmp_path/'analyze/data';metadata.mkdir(parents=True)
    records=[];works=[]
    for t in range(3):
        for period in pd.period_range('2021Q3','2026Q2',freq='Q'):
            for j in range(t+2):
                i=len(records)
                records.append({'row_id':i,'doc_id':f'paper:W{i}','source':'paper','date':str(period.start_time.date()),
                    'category_id':f'F{t+1:04d}','topic_id':t,'retracted':False,'template_record':False,'usable':True,
                    'title_only':j==0,'nmf_relative_margin':.15 if j else .01,'topic_1_cosine':np.nan,'top1_top2_margin':np.nan})
                works.append({'work_id':f'W{i}','institutions':f'org{t};other{j}','cited_by_count':i%11})
    for src in ['patent','policy']:
        for j in range(4):
            i=len(records)
            records.append({'row_id':i,'doc_id':f'{src}:{j}','source':src,'date':'2026-02-01',
                'category_id':'F0001','topic_id':0,'retracted':False,'template_record':False,'usable':True,
                'title_only':False,'nmf_relative_margin':np.nan,'topic_1_cosine':.8,'top1_top2_margin':.03})
    pd.DataFrame(records).to_parquet(source/'assignments/part-00000.parquet',index=False)
    frame=pd.DataFrame(works);con=duckdb.connect(str(metadata/'independent_corpus.duckdb'))
    con.register('frame',frame);con.execute('CREATE TABLE works AS SELECT * FROM frame');con.close()
    pd.DataFrame({'category_id':['F0001','F0002','F0003'],'topic_id':[0,1,2],'name':['one','two','three'],
        'domain':'待主题范围审阅','status':'全量NMF关键词主题','analysis_scope':'待主题范围审阅'}).to_csv(source/'topic_catalog.csv',index=False)
    (source/'ASSIGNMENTS_MANIFEST.json').write_text(json.dumps({'files':{'part-00000.parquet':build.sha(source/'assignments/part-00000.parquet')}}))
    summary={'full_training':True,'full_inference':True,'full_transfer':True,'population_records':len(records),
        'assignments_manifest_sha256':build.sha(source/'ASSIGNMENTS_MANIFEST.json')}
    (source/'SUMMARY.json').write_text(json.dumps(summary));(source/'VALIDATION.json').write_text('{"passed":true}')
    (source/'COMPLETE.json').write_text(json.dumps({'summary_sha256':build.sha(source/'SUMMARY.json'),
        'validation_sha256':build.sha(source/'VALIDATION.json')}))
    inp=tmp_path/'base';build.build(source,inp)
    out=tmp_path/'experiments';exp.run(source,inp,out,draws=3)
    protocol=json.loads((out/'PROTOCOL.json').read_text())
    assert protocol['full_population_records']==len(records) and protocol['full_count_thresholds']
    assert protocol['baseline_replay_passed'] and not protocol['sample_rows_or_quotas_used']
    scenarios=pd.read_csv(out/'scenarios.csv')
    assert {'score_component_ablation','gate_ablation','threshold_joint','window','data_filter','source_ablation','transfer_filter'}<=set(scenarios.kind)
    assert len(pd.read_csv(out/'weight_draws.csv'))==9
    filters=pd.read_csv(out/'data_filter_counts.csv').set_index('scenario')
    assert filters.loc['baseline','papers']==len(works)
    assert filters.loc['exclude_title_only','papers']<len(works)
    pot=pd.read_csv(out/'potential_association_baseline.csv').set_index('category_id')
    assert pot.loc['F0001','policies']==4 and pot.loc['F0001','patents']==4
    assert not pot.semantic_approval.any()
    assert len(pd.read_csv(out/'policy_document_loo.csv'))==4
    assert json.loads((out/'COMPLETE.json').read_text())['passed']
    (source/'assignments/part-00000.parquet').write_bytes(b'changed')
    with pytest.raises(ValueError,match='Assignment files changed'):exp.run(source,inp,tmp_path/'rejected',draws=1)
