"""Task-defined literature/patent sets, independent of the frozen 750 labels.

prepare: collect union candidates and apply transparent object/task rules.
build: apply frozen displayed-record reviews and recalculate every indicator.
"""
from common import *
import pandas as pd, numpy as np, duckdb, argparse

UNITS = {
 'U0246':dict(category_id='C0246',name='虚拟电厂资源聚合、调度与市场履约',object=r'virtual[\s-]+power[\s-]+plants?|虚拟\s*(?:发电厂|电厂)|(?:^|[^a-z])VPPs?(?:$|[^a-z])',task=r'aggregat|dispatch|schedul|bid|trad|market|pric|forecast|predict|operat|control|optim|demand|resource|management|定价|预测|聚合|调度|交易|市场|运行|运营|控制|优化|响应|资源|管理',scope='虚拟电厂资源聚合、响应、协调调度、市场交易及履约；排除纯背景提及与通用设备。'),
 'U0650':dict(category_id='C0650',name='空气源热泵设备、运行与系统应用',object=r'air[\s-]*source[\s-]*heat[\s-]*pumps?|air[\s-]*to[\s-]*(?:water|air)[\s-]*heat[\s-]*pumps?|空气源热泵|空气能热泵|\bASHPs?\b',task=r'heat|pump|thermal|defrost|热泵|供热|制冷|除霜',scope='空气源热泵设备、性能、控制、安装和系统应用；排除未明确空气源的一般热泵及仅地源/水源对象。'),
 'U0356_KG':dict(category_id='C0356',name='电力知识图谱与知识问答',object=r'knowledge[\s-]*graphs?|knowledge[\s-]*bases?\b|question[\s-]*answer|知识图谱|知识库|知识问答|智能问答|知识推理',task=r'construct|reason|retriev|answer|diagnos|decision|operat|maintenance|management|extract|问答|推理|检索|诊断|决策|运维|运行|管理|构建|抽取',scope='面向电网、电力设备、供配电或电力市场的知识图谱/知识库、知识推理与问答；排除通用BI、泛能源材料和无知识方法的优化。'),
 'U0356_LLM':dict(category_id='C0356',name='电力大模型辅助决策与运维',object=r'large[\s-]*language[\s-]*models?|\bLLMs?\b|大语言模型|大模型|语言大模型|foundation[\s-]*models?|\bGPT[-\s]?\d|chatgpt',task=r'forecast|predict|dispatch|schedul|decision|operat|maintenance|diagnos|retriev|answer|assistant|control|management|agent|optim|construct|extract|构建|抽取|校验|分析|优化|预测|调度|决策|运维|诊断|检索|问答|辅助|控制|管理|智能体',scope='大语言/基础模型用于电力运行、设备运维、预测、交易及辅助决策；排除仅给模型训练供电、比特币能耗和一般强化学习智能体。'),
}
POWER = r'power[\s-]*(?:grid|system|network|equipment|market|dispatch|distribution|plant|generation)|electric(?:al|ity)?[\s-]*(?:grid|power|system|market|equipment|load|distribution)|smart[\s-]*grid|micro[\s-]*grid|hydropower|电力|电网|配电|变电|输电|供电|电气设备|电站|发电厂'
FOCUS = r'we\s+(?:propose|present|develop|introduce|investigate)|this\s+(?:paper|study|work)\s+(?:proposes|presents|develops|investigates|introduces|focuses)|本文|本研究|本发明|本申请|本公开|本实用新型|一个实施例'
EXCLUDE_LLM = r'bitcoin|比特币|LLM\s+pretraining|LLM\s+training|training\s+(?:large[ -]+language[ -]+models|LLMs)|大模型训练供|模型训练能耗'

def hit(pattern,text):return bool(re.search(pattern,str(text),re.I))

def classify(unit,title,body):
    """按应用对象与任务证据判断：明确相关(strict)、待判断(pending)、排除(excluded)。"""
    spec=UNITS[unit];title=str(title or '');body=str(body or '')
    full=title+' '+body
    obj_t=hit(spec['object'],title); obj=hit(spec['object'],full)
    power_t=hit(POWER,title);power=hit(POWER,full)
    if hit(r'press release|^editorial|^preface',title):return 'excluded','新闻稿或编辑性文本，不计研究证据'
    if unit.startswith('U0356') and hit(r'财务|合规治理|稽查|报废物资|financial report|power[ -]*grid[ -]*inspired',title):return 'excluded','企业事务或借用电网比喻，超出电力技术运行任务'
    if not obj:return 'excluded','未发现该分析单元明确技术对象'
    if unit.startswith('U0356') and not power:return 'excluded','未发现电力对象；不能由原标签替代对象证据'
    if unit=='U0356_LLM' and hit(EXCLUDE_LLM,title):return 'excluded','训练供电或能耗任务，不是模型用于电力决策'
    if unit=='U0650' and obj_t:return 'strict','题名明确空气源热泵对象'
    if unit=='U0246' and obj_t and hit(spec['task'],title+' '+body[:500]):return 'strict','题名明确虚拟电厂且有聚合/运行/市场任务'
    if unit.startswith('U0356') and obj_t and power_t and hit(spec['task'],full):return 'strict','题名同时明确电力对象和知识/大模型技术，具有应用任务'
    # Purpose evidence must locate the object, task and power domain in one local span.
    for m in re.finditer(FOCUS,body,re.I):
        span=body[m.start():m.start()+450]
        if hit(spec['object'],span) and hit(spec['task'],span) and (not unit.startswith('U0356') or hit(POWER,span)):
            if unit=='U0356_LLM' and hit(EXCLUDE_LLM,span):continue
            return 'strict','正文研究目的/发明声明局部同时明确对象与任务'
    return 'pending','仅正文提及或题名对象/任务不完整；扩展口径纳入，严格口径不纳入'

def prepare():
    c=duckdb.connect();c.execute('SET threads=4');c.execute("SET memory_limit='5GB'")
    c.from_parquet(str(BASE/'data/assignments/*.parquet')).create_view('a')
    c.from_parquet(str(CORPUS/'data/corpus/*.parquet')).create_view('raw')
    c.from_parquet(str(LABELS/'results/text_corrections/*.parquet')).create_view('tc')
    # Identical eligible-source universe supplies numerator candidates AND denominators.
    c.execute("""CREATE TEMP TABLE universe AS SELECT a.row_id,a.doc_id,a.source,a.category_id,a.date,
      a.needs_review,a.title_only,r.language,
      coalesce(tc.clean_title,a.title,r.title,'') title,coalesce(tc.clean_body,r.body,'') body
      FROM a JOIN raw r USING(row_id) LEFT JOIN tc USING(row_id)
      WHERE a.source IN ('paper','patent') AND a.category_index>=0
      AND NOT a.retracted AND NOT a.template_record
      AND a.date BETWEEN '2026-01-01' AND '2026-08-31'""")
    den=c.execute("SELECT source,left(date,7) AS month,count(*) AS documents,sum(CAST(length(trim(body))>0 AS INT)) AS with_body FROM universe GROUP BY 1,2 ORDER BY 1,2").df()
    save(den,'potential_unified_denominators.csv')
    old=pd.read_parquet(BASE/'evidence/cross_label_retrieval.parquet')
    frames=[]
    for uid,s in UNITS.items():
        oldids=old.loc[old.target_category.eq(s['category_id']) & old.date.between('2026-01-01','2026-08-31'),'row_id'].unique()
        c.register('old_ids',pd.DataFrame({'row_id':oldids}))
        patt='(?i)'+s['object']
        d=c.execute("SELECT *,category_id=? from_original_category,row_id IN (SELECT row_id FROM old_ids) from_old_cross_query,regexp_matches(title||' '||body,?) from_new_object_query FROM universe WHERE category_id=? OR row_id IN (SELECT row_id FROM old_ids) OR regexp_matches(title||' '||body,?)",[s['category_id'],patt,s['category_id'],patt]).df()
        d['unit_id']=uid;d['unit_name']=s['name'];d['parent_category_id']=s['category_id']
        assessed=[classify(uid,r.title,r.body) for r in d.itertuples()]
        d['rule_status']=[x[0] for x in assessed];d['rule_reason']=[x[1] for x in assessed]
        frames.append(d);print('UNIFIED_CANDIDATES',uid,len(d),d.groupby(['source','rule_status']).size().to_dict(),flush=True)
    all_d=pd.concat(frames,ignore_index=True)
    assert not all_d.duplicated(['unit_id','row_id']).any()
    all_d.to_parquet(BASE/'evidence/potential_unified_candidates.parquet',index=False,compression='zstd')
    dump(BASE/'data/POTENTIAL_UNIFIED_METHOD.json',dict(created_utc=now(),units=UNITS,power_pattern=POWER,focus_pattern=FOCUS,
        candidate_union='original category OR previous cross-label query OR new object query in full eligible 2026-01..08 corpus',
        strict='title object/task or local research-purpose evidence; displayed-record semantic overrides',
        expanded='strict plus pending; excluded never included',
        unit_overlap='Task units may overlap, especially knowledge graphs and LLMs; never sum as unique documents.',
        denominator='Same eligible-source universe; source totals are not the sum of retrieved unit counts.',
        smoothing='Binary Jeffreys correction: (unit_count+0.5)/(eligible_source_total+1); no750-class Dirichlet assumption.',
        review_limit='Automated evidence rules plus displayed diagnostic and held-out samples, not full manual adjudication or calibrated recall.',
        legacy_geometry_unused=True))
    # Deterministic stratified diagnostic sample; separate later holdout seed.
    samples=[]
    for (uid,source,status),d in all_d.groupby(['unit_id','source','rule_status']):
        d=d.copy();d['sample_hash']=d.row_id.map(lambda i:hashlib.sha256(f'unified-diagnostic-v1|{uid}|{i}'.encode()).hexdigest())
        samples.append(d.sort_values('sample_hash').head(8 if status=='strict' else 3))
    ss=pd.concat(samples).drop(columns='sample_hash')
    ss.to_parquet(BASE/'evidence/potential_unified_diagnostic_samples.parquet',index=False)
    c.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','build']);args=parser.parse_args()
    if args.stage=='prepare':prepare()
    else:
        from potential_unified_metrics import build
        build()
