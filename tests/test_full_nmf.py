"""End-to-end full-input aggregation and rejection of sample deliveries."""
import importlib.util
from pathlib import Path
import json
import sys
import duckdb
import pandas as pd
import pytest

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'src'))
spec=importlib.util.spec_from_file_location('full_hotspot_build',REPO/'pipelines/full_nmf/build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)


def test_full_aggregation_uses_all_records_and_full_volume_thresholds(tmp_path,monkeypatch):
    source=tmp_path/'classification';source.mkdir();(source/'assignments').mkdir()
    metadata=tmp_path/'analyze/data';metadata.mkdir(parents=True)
    periods=pd.period_range('2021Q3','2026Q2',freq='Q')
    papers=[{'row_id':i,'doc_id':f'paper:W{i}','source':'paper','date':str(p.start_time.date()),'category_id':'F0001',
        'topic_id':0,'retracted':False,'template_record':False,'usable':True,'topic_1_cosine':None} for i,p in enumerate(periods)]
    labels=papers+[{'row_id':20,'doc_id':'patent:P1','source':'patent','date':'2026-02-01','category_id':'F0001',
        'topic_id':0,'retracted':False,'template_record':False,'usable':True,'topic_1_cosine':.9}]
    pd.DataFrame(labels).to_parquet(source/'assignments/part-00000.parquet',index=False)
    frame=pd.DataFrame({'work_id':[f'W{i}' for i in range(20)],'institutions':['org']*20,'cited_by_count':range(20)})
    c=duckdb.connect(str(metadata/'independent_corpus.duckdb'));c.register('f',frame);c.execute('CREATE TABLE works AS SELECT * FROM f');c.close()
    pd.DataFrame([{'topic_id':0,'category_id':'F0001','name':'test','domain':'待主题范围审阅','status':'全量NMF关键词主题','analysis_scope':'待主题范围审阅'}]).to_csv(source/'topic_catalog.csv',index=False)
    (source/'ASSIGNMENTS_MANIFEST.json').write_text(json.dumps({'files':{'part-00000.parquet':build.sha(source/'assignments/part-00000.parquet')},'records':21}))
    summary={'full_training':True,'full_inference':True,'full_transfer':True,'population_records':21,
        'assignments_manifest_sha256':build.sha(source/'ASSIGNMENTS_MANIFEST.json')}
    (source/'SUMMARY.json').write_text(json.dumps(summary));(source/'VALIDATION.json').write_text('{"passed":true}')
    (source/'COMPLETE.json').write_text(json.dumps({'summary_sha256':build.sha(source/'SUMMARY.json'),'validation_sha256':build.sha(source/'VALIDATION.json')}))
    monkeypatch.setattr(build,'ROOT',tmp_path)
    out=tmp_path/'out';build.build(source,out)
    result=json.loads((out/'SUMMARY.json').read_text())
    assert result['classification_input_records']==21
    assert result['papers_used_for_hotspot_windows']==20
    assert result['core_numeric_candidates']==0
    assert pd.read_csv(out/'quarter_counts.csv').papers.sum()==20
    assert pd.read_csv(out/'cross_source_signals.csv').patent_records.iloc[0]==1
    summary['full_training']=False;(source/'SUMMARY.json').write_text(json.dumps(summary))
    (source/'COMPLETE.json').write_text(json.dumps({'summary_sha256':build.sha(source/'SUMMARY.json'),'validation_sha256':build.sha(source/'VALIDATION.json')}))
    with pytest.raises(ValueError,match='Full classification required'):
        build.build(source,tmp_path/'rejected')
