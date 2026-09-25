"""Workbook and report views for unified task evidence."""
from common import *
import pandas as pd
POTENTIAL_CN={
 'papers_2026_jan_aug':'2026年1至8月论文记录数','unit_id':'统一分析单元ID','unit_name':'统一分析单元名称','parent_category_id':'来源类别ID',
 'policy_groups':'统一任务部署研发政策组数','policy_points':'统一任务政策证据分',
 'relative_share':'统一口径同期相对份额','matched_jan_may_relative_share':'统一口径1至5月同期相对份额',
 'expanded_relative_share':'扩展口径同期相对份额','expanded_matched_jan_may_relative_share':'扩展口径1至5月同期相对份额',
 'expanded_patents_2026':'扩展口径专利组数','expanded_papers_2026_jan_aug':'扩展口径论文数','expanded_potential_priority':'扩展口径是否通过',
 'scope_sensitivity':'范围敏感性说明','evidence_tier':'潜在证据等级','scope_definition':'统一纳入范围',
 'uncertainty_ratio_lower':'待判记录非对称压力下界_非置信区间','uncertainty_ratio_upper':'待判记录非对称压力上界_非置信区间',
 'pending_patents':'待判专利组数','pending_papers':'待判论文数','patent_denominator':'同口径专利背景总量','paper_denominator':'同口径论文背景总量',
 'potential_unit_ids':'对应统一分析单元','potential_selected_unit_ids':'通过门槛的统一分析单元','potential_evidence_tier':'统一单元证据等级',
 'unified_patents':'单一统一单元专利组数','unified_papers':'单一统一单元论文数','unified_applicants':'单一统一单元主体数','unified_policy_groups':'单一统一单元政策组数','unified_relative_share':'单一统一单元相对份额','unified_matched_may_relative_share':'单一统一单元同期5月份额',
 'from_original_category':'原类别渠道命中','from_old_cross_query':'旧跨标签渠道命中','from_new_object_query':'新对象检索渠道命中',
 'rule_status':'规则初判','final_status':'最终范围状态','decision_basis':'范围判断依据','rule_reason':'规则判断依据',
 'review_status':'样本范围判断','review_reason':'样本或政策判断理由','stage':'样本阶段','apply_override':'是否修订自动判定','rule_disagreement_before_correction':'纠错前是否与规则不一致',
 'top1_trial_fraction':'第一名试验频率_非概率','top1_overlap':'前1交集','top1_jaccard':'前1集合Jaccard','top2_overlap':'前2交集','top2_jaccard':'前2集合Jaccard',
 'selected':'场景门槛通过','patents':'场景专利组数','papers':'场景论文数','applicants':'场景主体数','policies':'场景政策组数',
 'cross_label_relative_share':'历史宽词跨标签相对份额_不用于新潜在判定','cross_label_jan_may_relative_share':'历史非同期5月压力值_不用于新潜在判定',
 'patent_literature_relative_share':'原类别专利文献相对份额_历史诊断','potential_evidence_score':'统一单元证据分_小池内排序非概率',
}

def sheets(wb,sheet,experiment=False):
 if experiment:
  files=[('潜在统一口径实验','reliability/potential_unified_sensitivity_summary.csv'),('潜在逐单元实验依据','reliability/potential_unified_sensitivity_details.csv')]
 else:
  files=[('潜在统一单元全表','results/potential_unified_metrics.csv'),('潜在范围定义','results/potential_unified_scope.csv'),('潜在修订前后','results/potential_unified_before_after.csv'),('潜在逐条候选','results/potential_unified_record_ledger.csv'),('潜在主体证据','results/potential_unified_applicant_evidence.csv'),('潜在政策任务复核','results/potential_unified_policy_reviews.csv'),('潜在样本范围复核','results/potential_unified_document_reviews.csv'),('潜在统计分母','results/potential_unified_denominators.csv')]
 for name,file in files:sheet(wb,name,pd.read_csv(BASE/file))

def main_text(table):
 u=pd.read_csv(BASE/'results/potential_unified_metrics.csv');r=pd.read_csv(BASE/'results/potential_unified_document_reviews.csv')
 p=pd.read_csv(BASE/'results/potential_unified_policy_reviews.csv');ad=p[p.decision.eq('采用')].drop_duplicates(['unit_id','policy_group'])
 d=pd.read_csv(BASE/'results/potential_unified_decision_counts.csv');n=int(d.documents.sum())
 return f'''## 潜在应用跟踪方向（统一任务集合修订）

原三个方向改为四个明确任务单元：虚拟电厂、空气源热泵，以及从C0356拆出的电力知识图谱/知识问答和电力大模型辅助决策。750原标签不变；分析单元可跨标签检索，知识图谱与大模型可交叉，禁止把单元数量相加解释为互斥文献总量。其他旧潜在候选尚未完成此统一复核，不参与本版潜在排序；其政策线索只作历史参考。本版不是全750类潜在方向的穷尽发现。

{table(u,['unit_id','name','patents_2026','papers_2026_jan_aug','known_applicant_names','policy_groups','relative_share','matched_jan_may_relative_share','expanded_relative_share','evidence_tier'])}

**统一集合**：原类别记录、旧跨标签检索和新对象词检索取并集，按row_id去重，以同一对象/任务定义作规则筛选，再应用实际展示样本的明确修订。严格口径要求题名或局部研究目的证据，待判不计入；扩展口径加入待判。专利量和申请主体均从同一份入选专利记录计算，论文按相同任务定义独立筛选，政策逐条对应具体任务。明确不相关的财务报告、泛强化学习、模型训练/推理供电、新闻稿等不用于支持目标任务。共{n:,}条“单元×候选记录”判断，逐条理由可查；它们不是全部由人工阅读。记录数也不等于唯一研究数，同题同年全库去重作为单独压力测试。

本轮实际阅读{len(r)}条“单元×样本”题名/摘录（{r.row_id.nunique()}条不同记录），其中诊断{int(r.stage.eq('diagnostic').sum())}条、冻结规则后另抽{int(r.stage.eq('heldout').sum())}条。新样本的纠错前分歧完整保留，已发现的错误逐条修订；这是Codex辅助诊断，不是独立领域专家盲审，也不报告总体准确率。全库检索召回率未校准。政策按任务重新核对，采用{len(ad)}条“单元×政策组”关系、涉及{ad.policy_group.nunique()}个政策组；计数为已确认下限。

**主要变化**：虚拟电厂严格和扩展口径均有相对信号；空气源热泵严格口径通过，但扩展口径低于1.25，单列边界敏感的条件性跟踪；电力大模型方向不再包含整个C0356宽类；电力知识图谱虽专利相对份额高，仅确认1组明确政策支持，未过至少2组的门槛，保留观察。高比值也可能受论文样本小、体裁和语言召回不对称影响，不能解释为技术空白。

**指标与门槛**：专利≥50组、已知主体≥20、明确部署/研发政策≥2组，严格口径2026年1至8月与1至5月的同期相对份额均≥1.25。1至5月同时截取论文和专利；政策仍使用截至8月已核证据，该试验仅检查覆盖，不是历史回测。相对份额采用二元Jeffreys平滑：[（单元专利+0.5）/（合格专利总量+1）]÷[（单元论文+0.5）/（合格论文总量+1）]。四单元并非750互斥类别，因此不再使用分母+375。背景分母来自同一合格来源库，不以四单元命中数之和代替。

评分仍为30%专利数量百分位+20%主体百分位+50%政策强度（8分封顶），但百分位只在这四个统一单元内计算，不能和旧30方向分数直接比较。C0356拆分后没有可解释的单一总分，750类完整表保留对应单元ID，分数和计数到单元表查看。没有为维持旧名单预设入选数量。

严格/扩展差异、逐组删除政策、正文可用、题名证据、全库同题同年去重和专利误入压力实验见实验报告。两库地域、语言、公开时滞和采集覆盖仍未完全校准，申请主体按名称统计未作集团消歧；同一政策支持某个应用切口不表示全类专利的具体技术路线均获支持。结果是库内应用机会证据，不证明历史先行或未来成功。
'''

def experiment_text(table):
 u=pd.read_csv(BASE/'results/potential_unified_metrics.csv')
 g=pd.read_csv(BASE/'reliability/potential_unified_sensitivity_summary.csv')
 details=pd.read_csv(BASE/'reliability/potential_unified_sensitivity_details.csv')
 w=pd.read_csv(BASE/'reliability/weight_trials.csv');w=w[w.family.eq('potential')]
 a=pd.read_csv(BASE/'reliability/score_ablation_summary.csv');a=a[a.family.eq('potential')]
 data=g[g.kind.isin(['potential_data_sensitivity','classification_uncertainty','policy_dependence'])]
 lost=details[(details.kind=='leave_policy_out')&~details.selected&details.unit_id.isin(u.loc[u.potential_priority,'unit_id'])]
 return f'''## 潜在方向：统一集合后的完整重算

原潜在部分已替换：固定比较池为4个任务单元，严格基线{int(u.potential_priority.sum())}个单元通过，其中空气源热泵为边界敏感的条件性跟踪。完成{len(g)}个基线、门槛、数据与政策场景，{len(details)}条单元结果；重新进行3项评分消融和500次权重扰动。核心/新兴数值结果保持原口径。

{table(a[a.scenario.ne('baseline')],['scenario','spearman','top1_jaccard','top2_jaccard','max_abs_rank_change'])}

调权时每项权重独立乘0.8—1.2后归一；500次潜在排名相关最低{w.spearman.min():.3f}。只有4个单元，采用前1/前2及名次变化，前10/前25不适用并留空。小池相关系数离散，不能与旧30方向的0.98以上相关混为同一稳健性证据。评分排序与数值门槛分离，调分不自动改变资格。

{table(data,['scenario','baseline_count','retained','retention','lost'])}

数据场景逐次重建选中的论文、专利和申请主体集合：严格、扩展、仅题名证据、正文可用、仅原类别候选、仅跨标签候选、全库同题同年去重，以及不应用人工样本修订。正文可用和去重场景同时重算背景分母。按原类别/跨标签渠道的消融只测检索依赖，不把原类别当金标准。非对称待判上下界并非统计置信区间；10%/20%专利移除是确定性记录级误入假设，主体随记录删除重新统计，背景库保留这些记录。

门槛扫描规模、主体、政策组数及相对份额，联合网格扫描政策组×相对份额。每次政策移除均重新统计组数、强度与分数；按发布机构合并也完整重算。当前基线单元中，逐组删除政策会导致退出的单元为：{'、'.join(sorted(lost['name'].unique())) or '无'}。政策删除结果使用同一已确认政策库，不代表实际政策因果作用。

1至5月比值使用双方同期论文/专利，不再沿用旧“1至5月专利对1至8月论文”的非同期指标。政策仍截至8月，不能称为5月时点预测。专利后期覆盖稀疏、检索召回与跨来源语言差异仍是限制。严格口径通过而扩展口径退出的方向保留敏感标记，不通过调整定义维持榜单。
'''
