"""Frozen analyst decisions for actually displayed diagnostic records and clauses."""
from common import *
import pandas as pd
from potential_unified import UNITS

def record_policies():
 raw=pd.read_parquet(BASE/'data/policies2026.parquet').set_index('row_id')
 old=pd.read_csv(BASE/'results/policy_review_decisions.csv').fillna('')
 rows=[]
 for cid,uid in [('C0246','U0246'),('C0650','U0650')]:
  for r in old[(old.category_id==cid)&(old.decision=='采用')].to_dict('records'):
   r.update(unit_id=uid,unit_name=UNITS[uid]['name'],review_reason='本轮重读：条款明确对应统一定义的部署/运行或系统应用；同政策组仅计一次',reviewer='Codex辅助条款复核，非独立专家')
   assert r['quote'] in raw.loc[r['row_id'],'body'];rows.append(r)
 # Exact source spans inspected in this revision, no inherited generic AI support.
 entries=[
 ('U0356_KG',5114003,'( 六 )','( 七 )',3,'2026-07-07','水电设备全生命周期健康管理和诊断明确采用知识图谱'),
 ('U0356_LLM',5114003,'( 四 )','( 五 )',3,'2026-07-07','核电专属大模型明确赋能设备监测、故障诊断与启停'),
 ('U0356_LLM',5112979,'4.电力交易智能预测与辅助决策智能体','5.城市级聚合式虚拟电厂',3,'2026-05-08','电力交易任务明确采用多模态大模型，不从一般智能决策外推'),
 ('U0246',5112979,'5.城市级聚合式虚拟电厂','6.基于AI智能决策',3,'2026-05-08','明确虚拟电厂资源聚合、负荷预测和调度研发任务'),
 ('U0246',5114003,'鼓励虚拟电厂建设运营','优化电动汽车',2,'2026-07-07','明确虚拟电厂柔性资源聚合与交易部署'),
 ]
 for uid,rid,start,end,strength,date,reason in entries:
  r=raw.loc[rid];i=r.body.index(start);j=r.body.index(end,i);quote=r.body[i:j]
  rows.append(dict(unit_id=uid,unit_name=UNITS[uid]['name'],category_id=UNITS[uid]['category_id'],row_id=rid,doc_id=r.doc_id,policy_group=r.policy_group,date=r.date,title=r.title,publisher=r.publisher,url=r.url,quote=quote,decision='采用',support_strength=strength,issue_date_reviewed=date,issue_year=2026,review_reason=reason,reviewer='Codex辅助条款复核，非独立专家'))
 # Keep explicit exclusions so a parent approval cannot silently support its children.
 for uid in ['U0356_KG','U0356_LLM']:
  r=old[(old.category_id=='C0356')&(old.row_id==5114003)].iloc[0].to_dict()
  r.update(unit_id=uid,unit_name=UNITS[uid]['name'],decision='不采用',support_strength=0,review_reason='旧条款只写智能运营决策，未明确知识图谱或大模型；改用另行实际阅读的任务条款')
  rows.append(r)
 r=raw.loc[5117664];phrase='节能策略智能问答';i=r.body.index(phrase)
 for uid in ['U0356_KG','U0356_LLM']:
  rows.append(dict(unit_id=uid,unit_name=UNITS[uid]['name'],category_id='C0356',row_id=5117664,doc_id=r.doc_id,policy_group=r.policy_group,date=r.date,title=r.title,publisher=r.publisher,url=r.url,quote=r.body[max(0,i-130):i+180],decision='不采用',support_strength=0,issue_date_reviewed='2026-02-13',issue_year=2026,review_reason='泛节能装备问答，不能直接证明电力技术运行任务支持'))
 df=pd.DataFrame(rows)
 for r in df.itertuples():assert r.quote in raw.loc[r.row_id,'body']
 save(df,'potential_unified_policy_reviews.csv')
 dump(BASE/'review/potential_unified_policy_read_log.json',df.fillna('').to_dict('records'))
 print('UNIFIED_POLICY',df[df.decision.eq('采用')].drop_duplicates(['unit_id','policy_group']).groupby('unit_id').size().to_dict())

if __name__=='__main__':record_policies()

# Explicit deviations from the initially displayed rule decision.
DOCUMENT_DECISIONS={
 ('U0246',4576119):('strict','虚拟电厂可调能力定价，属于市场履约任务'),
 ('U0246',4660579):('excluded','法律声明/系统规格材料，已读内容不足以构成目标研究证据'),
 ('U0246',4711091):('excluded','期刊卷首介绍，提及其他论文，不是目标研究'),
 ('U0246',5084901):('strict','虚拟发电厂控制器聚合负荷、储能与独立电厂，别称漏检'),
 ('U0246',4852118):('strict','虚拟电厂内部出力预测，为聚合调度提供直接输入'),
 ('U0246',4857902):('strict','明确虚拟电厂资源调控约束降维'),
 ('U0246',5095800):('strict','虚拟发电厂运营商可再生能源市场投标'),
 ('U0650',4557355):('excluded','实际研究对象是地源一体热泵，空气源仅作背景'),
 ('U0650',4962759):('strict','太阳能与空气能热泵复合系统，系统应用在范围内'),
 ('U0650',4952768):('strict','空气源热泵与相变储能耦合供冷供暖'),
 ('U0650',4988693):('strict','空气源热泵光伏辅助加热设备'),
 ('U0356_KG',4642565):('strict','水电通信安全知识图谱构建，已补读正文'),
 ('U0356_KG',4753005):('excluded','项目新闻稿，不计研究论文'),
 ('U0356_KG',4617198):('pending','题名knowledge-based不等于知识库/知识图谱；当前候选检索已剔除该前缀误匹配'),
 ('U0356_KG',4992398):('strict','车网互动实体知识图谱与语义融合'),
 ('U0356_KG',4920304):('strict','电力工程安措文档知识检索与合规校验'),
 ('U0356_KG',4853546):('strict','电力振荡传播知识图谱分析'),
 ('U0356_KG',4917683):('excluded','主体资质、数据治理与合规体系，不是具体电力运行任务'),
 ('U0356_LLM',4560663):('excluded','借用电网比喻研究LLM集群路由，不是电力应用'),
 ('U0356_LLM',4514878):('strict','明确用LLM作为分布式发电控制决策中心'),
 ('U0356_LLM',4645161):('strict','LLM智能体进行电力动态模型校验和安全筛查'),
 ('U0356_LLM',4927096):('strict','电力设备数据质量处理，明确电力模型与对象'),
 ('U0356_LLM',4939841):('strict','视觉语言模型用于带电作业风险交互监控'),
 ('U0356_LLM',4894253):('strict','大语言模型构建配电网向量知识库'),
 ('U0356_LLM',4878664):('excluded','电力企业财务报告，不是电力技术运行'),
 ('U0356_LLM',4991973):('excluded','企业稽查知识推理，不归入电力技术运行'),
 ('U0356_LLM',4932217):('excluded','报废物资回收物流评估，不是电力运行与设备运维'),
 ('U0246',4425468):('strict','多能源耦合虚拟电厂内部水电负荷预测'),
 ('U0246',4661327):('strict','正文明确提出虚拟电厂低碳调度，已补读'),
 ('U0246',5043914):('excluded','Vpp是电压变量，不是虚拟电厂'),
 ('U0246',4832351):('strict','热水器负荷聚合为虚拟发电厂，明确控制与电网协同'),
 ('U0650',4431956):('strict','丙烷物性方法明确验证空气源热泵动态循环'),
 ('U0650',4481573):('strict','医院系统方案明确空气源热泵供热配置，已补读'),
 ('U0650',5076195):('strict','正文明确空气源热泵设备结构'),
 ('U0650',4949198):('strict','正文明确空气源热泵采暖热水集成'),
 ('U0356_KG',4722397):('strict','电表状态分析明确用检索增强知识图谱'),
 ('U0356_KG',4768807):('excluded','knowledge base指知识贡献而非知识库技术，正文为一般强化学习'),
 ('U0356_KG',4901574):('strict','变电站安措四元知识图谱与推理'),
 ('U0356_KG',4938079):('strict','电能质量治理策略知识库匹配与控制'),
 ('U0356_KG',4882973):('excluded','数据法律合规与人员审计，超出技术运行任务'),
 ('U0356_KG',4889595):('pending','电力AI评测目录的通用知识结构，技术运行对应不足'),
 ('U0356_LLM',4564296):('strict','火电时序预测的本地LLM智能体，已补读'),
 ('U0356_LLM',4571581):('pending','通用工业Modbus数据验证，电力专属任务证据不足'),
 ('U0356_LLM',4488998):('pending','模型参数安全传输属于支持设施，尚未明确辅助决策任务'),
 ('U0356_LLM',4454485):('excluded','LLM推理负载用电优化，模型是负荷而不是决策方法'),
 ('U0356_LLM',5078553):('strict','智慧电网设备点表资料库通过LLM生成与分析'),
 ('U0356_LLM',4905632):('strict','电力故障分析及修复大模型和反馈微调'),
}

def record_documents():
 d=pd.read_parquet(BASE/'evidence/potential_unified_candidates.parquet').set_index(['unit_id','row_id'])
 rows=[]
 for stage,file in [('diagnostic','potential_unified_diagnostic_shown.json'),('heldout','potential_unified_holdout_to_read.json')]:
  for r in read(BASE/'review'/file):
   uid=r['unit_id'];rid=r['row_id'];key=(uid,rid)
   status,reason=DOCUMENT_DECISIONS.get(key,(r['rule_status'],{'strict':'题名及已展示内容支持该技术对象/任务；不是技术效果真实性验收','pending':'已读信息未充分明确该单元研究对象，保持待判','excluded':'已读题名/内容不满足该技术对象和电力任务'}[r['rule_status']]))
   # Match the actual displayed excerpt lengths, not the unshown source body.
   chars=300 if stage=='heldout' else 400 if uid.startswith('U0356') else 650
   if stage=='diagnostic' and rid in [4899287,4861848]:chars=0
   r['excerpt']=r['excerpt'][:chars]
   current=d.loc[key,'rule_status'] if key in d.index else 'not_in_final_candidate_union'
   rows.append(dict(**r,stage=stage,review_status=status,review_reason=reason,
    current_rule_status=current,apply_override=bool(key in d.index and status!=current),
    rule_disagreement_before_correction=status!=r['rule_status'],reviewer='Codex辅助阅读，非独立专家盲审',shown_chars=len(r['excerpt'])))
 out=pd.DataFrame(rows);assert not out.duplicated(['unit_id','row_id']).any()
 save(out,'potential_unified_document_reviews.csv')
 dump(BASE/'review/potential_unified_document_read_log.json',rows)
 print('UNIFIED_REVIEW',len(out),out.groupby(['stage','review_status']).size().to_dict())

if __name__=='__main__':record_documents()
