"""Readable descriptions of task evidence and sensitivity experiments."""
from common import *
import pandas as pd
POTENTIAL_CN = {'papers_2026_jan_aug': '2026年1至8月论文记录数',
 'unit_id': '应用方向ID',
 'unit_name': '具体应用方向',
 'parent_category_id': '来源类别ID',
 'policy_groups': '统一任务部署研发政策组数',
 'policy_points': '统一任务政策证据分',
 'relative_share': '统一口径同期相对份额',
 'matched_jan_may_relative_share': '统一口径1至5月同期相对份额',
 'expanded_relative_share': '扩展口径同期相对份额',
 'expanded_matched_jan_may_relative_share': '扩展口径1至5月同期相对份额',
 'expanded_patents_2026': '扩展口径专利组数',
 'expanded_papers_2026_jan_aug': '扩展口径论文数',
 'expanded_potential_priority': '扩展口径是否通过',
 'scope_sensitivity': '范围敏感性说明',
 'evidence_tier': '潜在证据等级',
 'scope_definition': '统一纳入范围',
 'uncertainty_ratio_lower': '待判记录非对称压力下界_非置信区间',
 'uncertainty_ratio_upper': '待判记录非对称压力上界_非置信区间',
 'pending_patents': '待判专利组数',
 'pending_papers': '待判论文数',
 'patent_denominator': '同口径专利背景总量',
 'paper_denominator': '同口径论文背景总量',
 'potential_unit_ids': '对应统一分析单元',
 'potential_selected_unit_ids': '通过门槛的统一分析单元',
 'potential_evidence_tier': '统一单元证据等级',
 'unified_patents': '单一统一单元专利组数',
 'unified_papers': '单一统一单元论文数',
 'unified_applicants': '单一统一单元主体数',
 'unified_policy_groups': '单一统一单元政策组数',
 'unified_relative_share': '单一统一单元相对份额',
 'unified_matched_may_relative_share': '单一统一单元同期5月份额',
 'from_original_category': '分类目录渠道命中',
 'from_old_cross_query': '跨主题关键词渠道命中',
 'from_new_object_query': '任务对象词渠道命中',
 'rule_status': '规则初判',
 'final_status': '最终范围状态',
 'decision_basis': '范围判断依据',
 'rule_reason': '规则判断依据',
 'review_status': '样本范围判断',
 'review_reason': '样本或政策判断理由',
 'stage': '样本阶段',
 'apply_override': '是否采用样本复核判断',
 'rule_disagreement_before_correction': '规则判定与样本判断是否不同',
 'top1_trial_fraction': '第一名试验频率_非概率',
 'top1_overlap': '前1交集',
 'top1_jaccard': '前1集合Jaccard',
 'top2_overlap': '前2交集',
 'top2_jaccard': '前2集合Jaccard',
 'selected': '场景门槛通过',
 'patents': '场景专利组数',
 'papers': '场景论文数',
 'applicants': '场景主体数',
 'policies': '场景政策组数',
 'potential_evidence_score': '统一单元证据分_小池内排序非概率'}

POTENTIAL_CN.update(strict_scope_passed='仅明确相关记录时是否达标',expanded_scope_passed='加入待判断记录后是否达标',tracking_advice='建议如何处理',tracking_basis='为什么给出这一建议')

def reading_guide(units):
 """从现有判断生成逐方向阅读说明，不参与打分或资格计算。"""
 rows=[]
 for r in units.itertuples():
  strict=bool(r.potential_priority);expanded=bool(r.expanded_potential_priority)
  if strict and expanded:
   advice='可列为跟踪方向'
   basis='仅明确相关记录、加入范围待判断记录，两种范围均满足专利数、主体数、政策及两个同期份额门槛。'
  elif strict:
   advice='有条件跟踪：先核实待判断记录'
   basis=f'严格范围通过；加入待判断记录后，1—8月相对份额为{r.expanded_relative_share:.2f}，1—5月为{r.expanded_matched_jan_may_relative_share:.2f}，未满足两个窗口均≥1.25的条件。'
  else:
   advice='暂不推荐，保留观察'
   basis=f'仅确认{int(r.policy_groups)}组明确政策，未达到至少2组的条件；专利相对份额高也不能替代政策要求。' if r.policy_groups<2 else '严格范围尚未满足全部条件，具体未通过项见任务指标表中的判断依据。'
  rows.append(dict(unit_id=r.unit_id,name=r.name,strict_scope_passed=strict,expanded_scope_passed=expanded,tracking_advice=advice,tracking_basis=basis))
 return pd.DataFrame(rows)


def main_text(table):
 u=pd.read_csv(BASE/'results/potential_unified_metrics.csv')
 r=pd.read_csv(BASE/'results/potential_unified_document_reviews.csv')
 p=pd.read_csv(BASE/'results/potential_unified_policy_reviews.csv')
 adopted=p[p.decision.eq('采用')].drop_duplicates(['unit_id','policy_group'])
 n=int(pd.read_csv(BASE/'results/potential_unified_decision_counts.csv').documents.sum())
 return f'''## 潜在热点：哪些应用值得跟踪

潜在分析围绕四个明确任务：虚拟电厂、空气源热泵、电力知识图谱与知识问答、电力大模型辅助决策与运维。每个任务按相同定义筛选论文和专利，并逐项核对政策支持。它覆盖这四个任务，不是对750类潜在机会的穷尽发现。

四个应用方向分别统计证据，结论如下：

{table(reading_guide(u),['name','strict_scope_passed','expanded_scope_passed','tracking_advice'])}

“双口径”专指两种文献纳入范围：**只用明确相关记录**称为严格口径；**再加入范围待判断的记录**称为扩展口径。明确不相关的记录始终排除。每次计算都同时使用论文、专利与政策证据。“达标”表示全部入选条件通过，包括至少2组明确政策。

再看支持这些结论的主要指标：

{table(u,['name','patents_2026','papers_2026_jan_aug','known_applicant_names','policy_groups','relative_share','expanded_relative_share'])}

虚拟电厂和电力大模型两次计算均通过，因此可跟踪。空气源热泵的1—8月相对份额由{u.set_index('unit_id').loc['U0650','relative_share']:.2f}（严格）降到{u.set_index('unit_id').loc['U0650','expanded_relative_share']:.2f}（扩展），后者低于1.25。它的“条件性”具体指需要先核实待判断文献是否属于该方向，再决定是否推荐。知识图谱只有{int(u.set_index('unit_id').loc['U0356_KG','policy_groups'])}组明确政策，未达到至少2组，因此目前暂不推荐、保留观察。

两种范围下均通过，只说明结果对这种纳入范围变化较稳定。它并不等于已经证明技术领先，也不表示其他数据或政策压力测试全部通过。

**两种口径如何区分。** 严格口径要求题名或研究目的中有明确的任务证据；扩展口径还纳入范围待判断的记录。候选来自分类目录、跨主题关键词和任务对象词检索，合并后按记录ID去重。专利数量与申请主体由同一批入选专利计算；论文使用相同任务定义，政策对应具体应用或研发任务。

**入选条件。** 专利不少于50组、已知申请主体不少于20个、明确政策不少于2组；2026年1—8月和1—5月两个同期窗口的专利/论文相对份额都不低于1.25。相对份额为“任务专利占专利背景库的比例”除以“任务论文占论文背景库的比例”，计算采用加0.5、分母加1的平滑。比值较高表示库内专利活动相对突出，也可能受到论文样本少或检索覆盖差异影响。

任务排序使用专利数量百分位30%、主体数量百分位20%、政策强度50%（政策强度8分封顶）。百分位仅在四个任务内计算。知识图谱与大模型可共享记录，不能把任务计数直接相加，也不能为其关联主题C0356赋予一个合并总分。

**证据范围。** 共记录{n:,}条“任务×候选记录”判断，其中实际展示阅读{len(r)}条题名或摘录，涉及{r.row_id.nunique()}条不同记录。样本包括{int(r.stage.eq('diagnostic').sum())}条诊断样本和规则固定后抽取的{int(r.stage.eq('heldout').sum())}条核查样本。规则与样本判断的分歧保存在证据表中。这是模型辅助审阅，未全量人工验收，也未校准全库检索召回率。

政策证据包含{len(adopted)}条“任务×政策组”关系、{adopted.policy_group.nunique()}个政策组，计数是已确认的下限。政策截至2026年8月；1—5月窗口只检查论文与专利的同期覆盖，不是5月时点的预测。申请主体按名称统计，未完成集团归并。结果支持应用跟踪，不能据此认定技术领先或未来成功。
'''


def experiment_text(table):
 u=pd.read_csv(BASE/'results/potential_unified_metrics.csv')
 g=pd.read_csv(BASE/'reliability/potential_unified_sensitivity_summary.csv')
 details=pd.read_csv(BASE/'reliability/potential_unified_sensitivity_details.csv')
 w=pd.read_csv(BASE/'reliability/weight_trials.csv');w=w[w.family.eq('potential')]
 data=g[g.kind.isin(['potential_data_sensitivity','classification_uncertainty','policy_dependence'])]
 lost=details[details.kind.eq('leave_policy_out')&~details.selected&details.unit_id.isin(u.loc[u.potential_priority,'unit_id'])]
 return f'''## 潜在任务对范围和政策的依赖

四个任务共进行{len(g)}个门槛、数据与政策情景，形成{len(details)}条逐任务结果，并进行3项评分成分消融和500次权重扰动。基准严格口径下{int(u.potential_priority.sum())}个任务通过；其中空气源热泵需要特别关注纳入范围。

潜在任务只有4个，实验比较前1名、前2名和名次变化。前10名、前25名超过任务数，在结果表中留空。500次调权的Spearman相关最低为{w.spearman.min():.3f}；少量对象的名次交换就会明显改变相关系数，不能把这个值理解为准确率。

{table(data,['scenario','baseline_count','retained','retention'])}

每个数据情景重新统计论文、专利和申请主体。检查包括严格与扩展口径、仅题名证据、正文可用、分类目录或跨主题检索渠道、全库同题同年去重，以及不采用样本复核判断。正文可用和去重情景同时调整背景分母。检索渠道实验反映对检索来源的依赖，不把分类目录视为金标准。

待判断记录的非对称实验分别模拟“只有待判论文被纳入”和“只有待判专利被纳入”。另外按固定记录规则移除10%或20%的严格口径专利，并重算申请主体；背景库保留这些记录。这些都是假设压力测试，不是统计置信区间。

政策实验扫描政策组数与相对份额门槛，逐组删除政策，并按发布机构合并证据。逐组删除时可能失去入选资格的基准任务包括：{'、'.join(sorted(lost['name'].unique())) or '无'}。这说明判断依赖哪些已确认政策，不能解释成政策的因果效果。

1—5月检查同时截取论文和专利，政策证据截至8月。专利后期覆盖稀疏、检索召回和跨来源语言差异仍会影响结果；严格口径与扩展口径结论不一致时，应连同敏感性标记交给专家判断。
'''
