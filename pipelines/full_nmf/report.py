"""从已保存的全量实验表生成中文解读，不重新计算模型。"""
from pathlib import Path
import argparse
import json
import pandas as pd


def table(headers, rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,row))+' |\n' for row in rows)


def render(folder):
    folder=Path(folder)
    p=json.loads((folder/'PROTOCOL.json').read_text())
    s=pd.read_csv(folder/'scenarios.csv');w=pd.read_csv(folder/'weight_draws.csv')
    names={'core':'核心热点','emerging':'新兴热点','potential_association':'跨来源潜在关联'}
    text='# 热点识别：消融与灵敏度实验报告\n\n## 结论\n\n小幅调整权重时排名总体稳定，但提高文本质量和分类差距门槛会明显改变候选名单。因此，权重稳定不等于分类可靠，更不等于候选已经确认为热点。跨来源关联尤其需要人工核验。\n\n'
    text+=table(['分析对象','基准数值候选','已通过语义审核'],[(names[r.family],r.numeric_candidates,r.semantic_approvals) for r in s[s.kind=='baseline'].itertuples()])
    text+=f"\n## 范围与方法\n\n分类底座为 {p['full_population_records']:,} 条冻结记录、{p['topics']} 个主题。本次保存 {len(s)} 个确定性情景，每类另有 {p['draws_per_family']:,} 次随机权重扰动，随机种子 {p['seed']}。使用完整分类结果，不重新训练 NMF，也不是独立时间外验证。有效日期和统计窗口会限制进入各项指标的论文数量。\n\n"
    text+='## 权重扰动：排名是否稳定\n\n权重乘以 0.8–1.2 的随机系数后重新归一化。排名相关系数（Spearman）越接近 1，整体排序越一致；前 20 名重合率衡量排名池前列是否稳定，不是已确认候选的比例。\n\n'
    text+=table(['对象','最低排名相关','中位排名相关','最低前20重合率','中位前20重合率'],[(names[f],f'{g.spearman.min():.6f}',f'{g.spearman.median():.6f}',f'{g.top20_overlap.min():.0%}',f'{g.top20_overlap.median():.0%}') for f,g in w.groupby('family')])
    text+='\n[逐主题排名范围](rank_intervals.csv) 的分位数表示参数扰动范围，不是统计置信区间。\n\n## 消融及门槛变化：候选数如何变化\n\n'
    labels={'baseline':'基准','data_filter':'文本质量/分类差距过滤','gate_ablation':'取消准入门槛','score_component_ablation':'删除评分分量','threshold_joint':'联合调整门槛','threshold_one_at_time':'单项调整门槛','window':'时间窗口','aligned_window':'共同日期窗口','source_ablation':'移除来源','transfer_filter':'跨来源匹配过滤'}
    text+=table(['对象','实验类型','情景数','候选数范围'],[(names[f],labels.get(k,k),len(g),f'{g.numeric_candidates.min()}–{g.numeric_candidates.max()}') for (f,k),g in s.groupby(['family','kind'])])
    text+='\n取消门槛后候选数增多只是条件放宽，不是算法变好。删除评分分量可能改变排序，即使候选总数不变。\n\n### 论文过滤的具体影响\n\nJaccard 是两份候选名单的交集除以并集，越接近 1 越一致；只看候选总数可能掩盖成员替换。\n\n'
    scenario_names={'baseline':'不额外过滤','exclude_title_only':'排除仅标题文本','paper_margin_0025':'论文分类差距≥0.025','paper_margin_005':'论文分类差距≥0.05','paper_margin_010':'论文分类差距≥0.10'}
    text+=table(['对象','过滤条件','候选数','保留基准候选','名单Jaccard','前20重合率'],[(names[r.family],scenario_names.get(r.scenario,r.scenario),r.numeric_candidates,r.baseline_retained,f'{r.candidate_jaccard:.3f}',f'{r.top20_overlap:.0%}') for r in s[s.kind=='data_filter'].itertuples()])
    text+='\n分类差距指第一与第二候选的贡献差距。提高门槛会排除分类边界模糊的论文，过滤后重新计算机构、引用和分母。新兴候选数量相近并不代表名单不变。\n\n## 跨来源关联：不能当作已证实的支持关系\n\n删除论文、专利或政策任一来源，会令潜在关联候选归零；这部分来自最低来源数量门槛，不能解释为独立因果证据。提高余弦或前两名相似度差距门槛也会减少候选。政策文档留一只模拟逐篇撤回，不是政策族独立性检验，也不能证明政策支持同一技术任务。\n\n## 使用边界与后续复核\n\n没有测量专家语义准确率，没有确认潜在关联的政策族独立性或申请人多样性。应优先复核低分类差距、资格随门槛改变及排名波动较大的主题。时间窗口实验固定引用队列，而质量过滤实验重新计算引用队列，不能混用解释。\n\n原始数据：[全部情景](scenarios.csv)、[随机扰动](weight_draws.csv)、[过滤后文献量](data_filter_counts.csv)、[政策逐篇撤回](policy_document_loo.csv)、[实验协议与输入指纹](PROTOCOL.json)。\n'
    (folder/'REPORT.md').write_text(text)
    return text


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    render(parser.parse_args().input)
