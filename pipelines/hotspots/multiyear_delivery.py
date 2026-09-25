"""Generate readable reports and workbooks from the current analysis tables."""
from common import *
import pandas as pd,numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font,PatternFill,Alignment
from openpyxl.utils import get_column_letter
from potential_delivery import POTENTIAL_CN,main_text,experiment_text,reading_guide
CN = {'category_id': '主题ID',
 'name': '主题名称',
 'report_rank': '榜内排序',
 'numeric_rank': '数值候选排序',
 'family': '热点类型',
 'scenario': '情景',
 'kind': '情景类型',
 'core_score': '多年核心评分',
 'emerging_score': '多年新兴评分',
 'core_papers': '核心窗口论文数',
 'core_years': '核心窗口年数',
 'recent_papers': '最近一年论文数',
 'previous_papers': '前一年论文数',
 'baseline_papers': '此前多年论文数',
 'baseline_annual_mean_papers': '此前多年年均论文数',
 'baseline_years_used': '基线年数',
 'multiyear_share_ratio': '最近一年对多年均值份额比',
 'share_growth_ratio': '最近一年同比份额比',
 'historical_peak_ratio': '最近一年对前四年最高份额比',
 'core_active_quarters': '核心窗口活跃季度数',
 'core_active_years': '核心窗口活跃年份数',
 'core_institutions': '核心窗口去重机构数',
 'recent_institutions': '最近一年去重机构数',
 'institution_expansion': '最近一年机构数对基线年均之比',
 'three_year_log_share_slope': '近三年对数份额年斜率',
 'growing_quarters': '最近一年同比增长季度数',
 'robust_min_ratio': '数据确认最小份额比',
 'share_ratio_2026_ytd': '2026年1至8月同期份额比',
 'core_review_pass': '核心样本范围审阅通过',
 'emerging_review_pass': '新兴样本范围审阅通过',
 'final_core': '核心初评入选',
 'final_emerging': '新兴初评入选',
 'core_eligible': '核心数值门槛通过',
 'emerging_robust': '新兴数值及数据确认通过',
 'paper_review_reason': '样本审阅依据与限制',
 'review_status': '评审状态',
 'trajectory': '五年轨迹解释',
 'parameters': '参数',
 'numeric_candidates': '数值候选数',
 'reviewed_selected': '固定审阅下入选数',
 'baseline_count': '实验基准入选数',
 'retained': '基准名单保留数',
 'retention': '基准名单保留比例',
 'jaccard': '集合Jaccard',
 'gained': '增加ID',
 'lost': '退出ID',
 'selected_ids': '情景入选ID',
 'interpretation': '解释限制',
 'spearman': '排名Spearman相关',
 'weights': '权重',
 'pool_size': '排名池大小',
 'mean_abs_rank_change': '平均名次变动',
 'max_abs_rank_change': '最大名次变动',
 'note': '说明',
 'reason': '范围判断依据',
 'decision': '范围判断',
 'row_id': '文献行ID',
 'title': '题名',
 'excerpt': '实际展示摘录',
 'annual_block': '年度区间',
 'review_purpose': '样本审阅目的',
 'data_scenarios_passed': '五项数据压力测试通过数',
 'robustness_grade': '数据压力测试结论',
 'core_review_basis': '核心审阅来源',
 'publication_year': '年份',
 'papers': '论文数',
 'observed_months': '覆盖月份数',
 'title_only_fraction': '仅题名比例',
 'jan1_proxy_fraction': '1月1日日期比例',
 'metadata_match_fraction': '元数据关联比例',
 'institution_metadata_fraction': '机构信息非空比例',
 'start_quarter': '年度起始季度',
 'end_quarter': '截止季度',
 'share': '年度平滑份额',
 'background': '年度论文背景总数',
 'block': '距最近年度块数',
 'status': '类别状态',
 'analysis_scope': '领域范围',
 'domain': '领域',
 'score': '情景评分',
 'core_mean_annual_share': '核心窗口年均份额',
 'baseline_mean_share': '此前多年年均份额',
 'citation_cohort_percentile': '同发表年引用百分位均值',
 'scope': '解释范围',
 'read_records': '展示阅读记录数',
 'read_row_ids': '展示阅读记录ID',
 'reviewer': '审阅方式',
 'time_sensitivity_note': '时间窗口敏感性提示',
 'baseline_rank': '基准名次',
 'rank': '实验名次',
 'min_rank': '最佳名次',
 'median_rank': '名次中位数',
 'max_rank': '最差名次',
 'top10_trial_fraction': '进入前10名的试验比例',
 'formal_selected': '基准名单是否入选',
 'formal_membership_changed_by_score_alone': '仅调分导致的入选变化数',
 'reviewed_final_top10_overlap': '审阅入选前10名交集',
 'active_quarters': '最近一年活跃季度数',
 'core_persistence': '核心窗口活跃季度占比',
 'direct_energy': '是否能源电力直接相关',
 'admissible_pool': '是否属于可分析范围',
 'emerging_eligible': '新兴基本数值条件通过',
 'growth_count_pvalue': '计数检验p值',
 'growth_count_qvalue': 'BH校正q值',
 'share_ratio_lower95': '合并背景份额比95%近似下界',
 'pooled_baseline_share': '合并背景论文份额',
 'pooled_share_ratio': '最近一年对合并背景份额比',
 'baseline_mean_institutions': '背景年度平均机构数',
 'recent_records': '最近一年元数据记录数',
 'jan1_fraction': '1月1日日期比例',
 'needs_review_fraction': '分类待复核记录比例',
 'supported_fraction': '规则支持记录比例',
 'recommended_focus': '建议跟踪任务',
 'source': '文献来源',
 'doc_id': '文献标识',
 'date': '日期',
 'applicant_names': '申请主体名称',
 'known_applicant_names': '已知申请主体数',
 'patents_2026': '2026年1至8月专利组数',
 'potential_priority': '潜在任务门槛是否通过',
 'potential_numeric_gate': '是否有关联任务通过数值门槛',
 'potential_review_category': '潜在任务范围判断',
 'potential_reason': '潜在任务依据与限制',
 'end_date': '统计截止日期',
 'applicant_metadata_fraction': '申请主体信息非空比例',
 'jan_may_patents': '1至5月专利组数',
 'jan_may_papers': '1至5月论文数',
 'patent_component': '专利数量百分位',
 'applicant_component': '申请主体数量百分位',
 'policy_component': '标准化政策强度',
 'documents': '记录数',
 'with_body': '有正文或摘要的记录数',
 'month': '月份',
 'rule_disagreement_before_correction': '规则判定与样本判断是否不同'}
CN.update(POTENTIAL_CN)
CN.update({'candidate_id': '候选证据ID', 'current_rule_status': '规则判定状态', 'end': '结束日期', 'issue_date_reviewed': '核实的政策日期', 'issue_year': '政策年份', 'needs_review': '分类是否待复核', 'object': '任务对象匹配规则', 'original_category_id': '记录所属主题ID', 'paper_review_decision': '论文主题范围判断', 'papers_2025_jan_aug': '2025年1至8月论文数', 'policy_form': '政策形式', 'policy_group': '政策组标识', 'publisher': '发布机构', 'quote': '政策引用条款', 'retrieval_basis': '检索依据', 'review_state': '复核状态', 'share_2025_jan_aug': '2025年1至8月论文份额', 'share_2026_jan_aug': '2026年1至8月论文份额', 'shown_chars': '展示摘录字符数', 'similarity': '几何相似度', 'start': '开始日期', 'support_strength': '任务支持强度', 'task': '应用任务匹配规则', 'title_only': '是否仅有题名', 'url': '来源链接'})
for i in range(5):
 for key,label in [('papers','论文数'),('denominator','背景论文数'),('share','份额')]:CN[f'year{i}_{key}']=f'距最近{i}年度_{label}'
for scenario,label in [('quality','文本日期质量'),('geometry','几何筛查'),('dedup','题名年度去重'),('exclude_needs_review','排除待复核'),('supported_only','仅规则支持')]:
 CN[scenario+'_retained']=label+'是否保留'
 for key,term in [('multiyear_share_ratio','多年背景份额比'),('share_growth_ratio','同比份额比')]:CN[scenario+'_'+key]=label+'_'+term
for k in [1,2,10,25]:
 CN[f'top{k}_overlap']=f'前{k}名交集数';CN[f'top{k}_jaccard']=f'前{k}名集合相似度'

def safe(v):
 if isinstance(v,(dict,list,tuple)):v=json.dumps(v,ensure_ascii=False)
 if v is None or (not isinstance(v,str) and pd.isna(v)):return None
 if isinstance(v,np.generic):v=v.item()
 if isinstance(v,str):
  v=re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',v)[:30000]
  if v[:1] in '=+-@':v="'"+v
 return v

PARAMETERS={'volume':'最近一年论文数','annual_volume':'年均论文数门槛','year_fraction':'活跃年份比例','quarter_fraction':'活跃季度比例','current_volume':'最近一年论文数门槛','current_share':'最近同比份额比','baseline':'背景年均论文数','multiyear':'多年背景份额比','recent_growth':'同比份额比','quarters':'同比增长季度数','peak':'历史峰值份额比','robust':'数据确认最小份额比','lower95':'95%近似下界','qvalue':'BH校正q值','patents':'专利数','applicants':'主体数','policies':'政策组数','relative':'专利/论文相对份额','citation':'引用表现','institutions':'机构数','persistence':'持续活跃程度','current':'最近份额','multiyear_growth':'多年背景增长','trend':'三年份额趋势','quarter_consistency':'季度增长一致性','institution_expansion':'机构扩展','policy':'政策强度','active_years':'活跃年份','current_share':'最近同比份额比','scope':'领域范围','matched_may':'1至5月同期相对份额','data_direction':'数据方向确认'}
SCENARIO_NAMES={'baseline':'基准设置','quality':'仅保留文本和日期质量较好的记录','geometry':'按几何指标筛查','dedup':'全库同题同年去重','exclude_needs_review':'排除分类待复核记录','supported_only':'仅保留规则支持记录','remove_semantic_review':'不要求样本范围审阅通过','unified_strict':'严格任务口径','unified_expanded':'扩展任务口径','unified_title_only_evidence':'仅依据题名判断任务','unified_body_available':'仅保留有正文或摘要的记录','unified_original_candidates_only':'仅使用分类目录渠道候选','unified_cross_candidates_only':'仅使用跨主题检索候选','unified_title_year_dedup':'全库同题同年去重','unified_no_manual_overrides':'仅使用规则判定，不采用样本复核判断','collapse_policy_by_publisher':'按政策发布机构合并','pending_papers_only':'只纳入待判断论文','pending_patents_only':'只纳入待判断专利'}

def scenario_label(value):
 value=str(value)
 if value in SCENARIO_NAMES:return SCENARIO_NAMES[value]
 if value=='remove_volume':return '移除评分成分：三年平均论文份额'
 for prefix,label in [('remove_gate_','移除入选条件：'),('remove_','移除评分成分：'),('drop_policy_','移除政策组：')]:
  if value.startswith(prefix):return label+PARAMETERS.get(value[len(prefix):],value[len(prefix):])
 if value.startswith('core_window_'):return '核心窗口：'+value[len('core_window_'):].replace('y','年')
 if value.startswith('baseline_window_'):return '新兴背景窗口：'+value[len('baseline_window_'):].replace('y','年')
 if value.startswith('omit_baseline_year_'):return '剔除距最近第'+value.rsplit('_',1)[-1]+'个背景年度'
 if value.startswith('cutoff_'):return '统计截止季度：'+value[len('cutoff_'):]
 if value.startswith('weight_'):return '权重扰动第'+str(int(value[len('weight_'):])+1)+'次'
 if value.startswith('patent_positive_removal_'):return '移除严格口径专利：'+value[len('patent_positive_removal_'):]
 if '=' in value:return '；'.join(PARAMETERS.get(k,k)+'='+v for k,v in (part.split('=',1) for part in value.split(',')))
 return value

# Presentation only: source CSVs and audit records are retained verbatim.
ARCHIVE_COLUMNS={
 'patents_2026','patents_jan_may','active_patent_months','known_applicant_names',
 'applicant_metadata_fraction','country_count','patent_review_decision','patent_review_reason',
 'patent_review_pass','reviewed_policy_documents','reviewed_policy_points','policy_review_status',
 'patent_literature_relative_share','jan_may_patent_relative_share','cross_label_papers_ytd',
 'cross_label_patents_ytd','cross_label_relative_share','cross_label_jan_may_relative_share',
}


def presentation(frame):
 """Prepare reader-facing cells without altering calculation or audit inputs."""
 df=frame.copy()
 # Category-level literature views use the current task-unit conclusions.
 if 'core_score' in df and 'potential_unit_ids' in df:
  df=df.drop(columns=[c for c in df if c in ARCHIVE_COLUMNS])
  df.loc[df.potential_unit_ids.fillna('').eq(''),'potential_reason']='未纳入四个任务单元的评估范围，不作潜在热点判断'
 phrases={
  '退出多年核心并保留观察':'不纳入核心名单，列为观察方向',
  '退出多年核心':'不纳入核心名单',
  '保留既有核心但明确':'列入核心初评，但明确',
  '保留多年核心':'列入核心初评',
  '维持原降级判断':'列为观察方向，需核查任务边界',
  '保留核心并纳入持续升温':'列入核心与持续升温初评',
  '扩大九条样本':'九条样本',
  '原判断保留，少量跨年证据支持':'样本支持，跨年证据有限',
  '本次两条早期补充样本未发现明显脱离主题；结合原已读样本保留，样本少不足以证明类内纯度。':'两条较早年度样本未发现明显脱离主题；结合已读样本支持初评，样本少不足以证明类内纯度。',
  '冻结样本审阅或本次多年补审；非独立专家认定':'基于已记录的主题范围样本审阅；需独立专家复核',
  '新增候选或新类型补审':'三年度分层样本审阅',
  '既有核心跨年抽样核对':'较早年度抽样核查',
  '旧条款只写智能运营决策，未明确知识图谱或大模型；改用另行实际阅读的任务条款':'条款只写智能运营决策，未明确知识图谱或大模型，不能作为这两个任务的明确政策支持',
 }
 for col in ['reason','decision','paper_review_reason','paper_review_decision','core_review_basis','review_reason','review_purpose']:
  if col in df:
   for source,target in phrases.items():df[col]=df[col].str.replace(source,target,regex=False)
 for col in ['evidence_tier','potential_evidence_tier']:
  if col in df:
   for source,target in [('双口径支持的跟踪方向','两种纳入范围均达标，可跟踪'),('边界敏感的条件性跟踪','仅明确相关记录时达标，需核实待判断记录'),('证据不足，保留观察','未满足全部条件，暂不推荐、保留观察')]:df[col]=df[col].str.replace(source,target,regex=False)
 return df


def table(df,cols):
 df=presentation(df)
 rows=['| '+' | '.join(CN.get(c,c) for c in cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
 for row in df[cols].itertuples(index=False,name=None):
  cells=[]
  for col,value in zip(cols,row):
   if pd.isna(value):text='—'
   elif isinstance(value,(bool,np.bool_)):text='是' if value else '否'
   elif col=='family':text={'core':'核心','emerging':'新兴','potential':'潜在'}.get(value,str(value))
   elif col=='scenario':text=scenario_label(value)
   elif isinstance(value,float):text=f'{value:.3f}'
   else:text=str(value)
   cells.append(text.replace('|','/').replace('\n',' '))
  rows.append('| '+' | '.join(cells)+' |')
 return '\n'.join(rows)

def deliver():
 R=BASE/'results';E=BASE/'reliability'
 save(reading_guide(pd.read_csv(R/'potential_unified_metrics.csv')),'potential_reading_guide.csv')
 z=pd.read_csv(R/'hotspot_summary_all750.csv');core=pd.read_csv(R/'core_hotspots.csv');em=pd.read_csv(R/'emerging_hotspots.csv')
 g=pd.read_csv(E/'gate_and_data_sensitivity.csv');wt=pd.read_csv(E/'weight_trials.csv');abl=pd.read_csv(E/'score_ablation_summary.csv');cov=pd.read_csv(R/'multiyear_coverage_audit.csv')
 manifest=[]
 def make(file,notes,tables,experiments=False):
  wb=Workbook();wb.remove(wb.active);spec=[]
  def sheet(name,df):
   ws=wb.create_sheet(name);ws.append([CN.get(c,c) for c in df]);ws.freeze_panes='C2'
   for row in df.itertuples(index=False,name=None):ws.append([safe(x) for x in row])
   ws.auto_filter.ref=ws.dimensions
   for cell in ws[1]:cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='164A63');cell.alignment=Alignment(wrap_text=True)
   for i,col in enumerate(df,1):ws.column_dimensions[get_column_letter(i)].width=75 if col in ['说明','情景含义'] or any(x in col for x in ['reason','excerpt','interpretation']) else 32 if col in ['name','scenario','title','review_status','trajectory'] else 20
   for row in ws.iter_rows(min_row=2):
    for cell in row:
     if isinstance(cell.value,float):cell.number_format='0.0000'
   if name=='潜在方向结论说明':
    for row in ws.iter_rows():
     for cell in row:cell.alignment=Alignment(wrap_text=True,vertical='top')
    for col,width in [('A',18),('B',42),('C',28),('D',28),('E',38),('F',75)]:ws.column_dimensions[col].width=width
    ws.row_dimensions[1].height=34
    for i in range(2,ws.max_row+1):ws.row_dimensions[i].height=75
   if name=='阅读说明':
    for row in ws.iter_rows(min_row=2):
     for cell in row:cell.alignment=Alignment(wrap_text=True,vertical='top')
    for i in range(2,ws.max_row+1):ws.row_dimensions[i].height=64
  sheet('阅读说明',pd.DataFrame(notes,columns=['项目','说明']))
  if experiments:
   codes=list(dict.fromkeys(g.scenario.tolist()+abl.scenario.tolist()))
   sheet('实验情景说明',pd.DataFrame({'情景代码':codes,'情景含义':[scenario_label(x) for x in codes]}))
  for name,path,cols in tables:
   df=presentation(pd.read_csv(BASE/path))
   if cols:df=df[cols]
   sheet(name,df);spec.append(dict(sheet=name,file=path,columns=list(df.columns)))
  used=list(dict.fromkeys(c for item in spec for c in item['columns']))
  sheet('字段对照',pd.DataFrame([(x,CN.get(x,x)) for x in used],columns=['字段','中文释义']))
  wb.save(BASE/file);manifest.append(dict(workbook=file,tables=spec))
 notes=[('核心与新兴算法','src/energy_hotspots/scoring.py：score()计算指标与评分，gates()定义入选条件；multiyear_build.py结合数据检查和样本审阅形成名单。'),('潜在热点算法','pipelines/hotspots/potential_unified_metrics.py：calculate()统计证据，qualify()检查门槛，with_may()检查同期窗口。完整导航见docs/ALGORITHM.md。'),('潜在结论怎么读','先看“潜在方向结论说明”。两次都达标=可跟踪；只在明确相关记录下达标=先核实待判断文献；尚未达标=暂不推荐、保留观察。'),('常见取值','paper=论文，patent=专利；strict=范围明确，pending=范围待判断，excluded=不属于任务范围；diagnostic=诊断样本，heldout=规则固定后抽取的核查样本。'),('如何阅读','先看核心热点、新兴热点和潜在跟踪方向；需要核查时再查看完整结果、样本、任务范围和政策依据。'),('结果',f'{len(core)}个核心、{len(em)}个新兴或持续升温初评候选。潜在评估4个具体应用方向：虚拟电厂、电力大模型可跟踪；空气源热泵需核实待判断记录；知识图谱政策证据不足，暂不推荐。'),('结果用途','供专家评审与应用跟踪。同一主题可同时满足核心和新兴条件；入选不直接证明技术首创、领先或未来成功。'),('核心时间范围','2023年7月—2026年6月，共3年；同时检查2025年7月—2026年6月的最近状态。'),('新兴时间范围','最近一年与2022年7月—2025年6月三个完整年度比较；五年轨迹覆盖2021年7月—2026年6月。'),('如何比较年份','先算每个年度的论文份额，再对背景年度取平均。2026年数据覆盖1—8月，不用其总量与全年直接比较。'),('候选与入选','数值候选只代表通过计算条件。主榜还要求样本范围审阅支持；未审或边界不清的方向在候选、观察表中列出。'),('潜在严格口径','只纳入任务证据明确的记录；专利数和申请主体来自同一批专利，论文与政策使用相同任务定义。'),('潜在扩展口径','在严格口径基础上加入范围待判断的记录，用于检查结论对任务边界的依赖。'),('审阅方式','已有样本判断来自模型辅助阅读，未全量人工清洗，也不是独立领域专家金标准。'),('实验基准','实验中的基准是本文主参数设置。保留比例表示参数或数据范围变化后仍入选的比例，不是准确率。'),('并列排名','排名时把0—100分舍入到小数点后10位；并列项按ID升序展示。实验采用并列最小名次，原始评分用于记录。'),('专家重点','核对主题边界、样本代表性、分类误差、数据覆盖和政策任务对应关系。详细方法及限制见同目录报告。')]
 corecols=['report_rank','category_id','name','core_papers','core_active_years','core_active_quarters','core_institutions','recent_papers','share_growth_ratio','core_score','robustness_grade','data_scenarios_passed','time_sensitivity_note','paper_review_reason']
 emcols=['report_rank','category_id','name','recent_papers','baseline_annual_mean_papers','multiyear_share_ratio','share_growth_ratio','historical_peak_ratio','three_year_log_share_slope','emerging_score','robustness_grade','data_scenarios_passed','time_sensitivity_note','paper_review_reason']
 tables=[('核心热点','results/core_hotspots.csv',corecols),('新兴热点','results/emerging_hotspots.csv',emcols),('潜在方向结论说明','results/potential_reading_guide.csv',None),('潜在跟踪方向','results/potential_priority.csv',None),('750类完整结果','results/hotspot_summary_all750.csv',None),('五年年度轨迹','results/multiyear_annual_trajectories.csv',None),('核心数值候选待审','results/multiyear_core_candidates.csv',None),('新兴数值候选审阅','results/multiyear_emerging_candidates.csv',None),('跨年样本审阅结论','results/multiyear_semantic_review.csv',None),('跨年已读样本','review/multiyear_displayed_samples.csv',None),('多年数据覆盖','results/multiyear_coverage_audit.csv',None),('数据稳健性分级','results/multiyear_robustness_grades.csv',None),('观察与待复核','results/watch_and_downgraded.csv',None)]
 for name,file in [('潜在任务完整指标','potential_unified_metrics.csv'),('潜在任务范围定义','potential_unified_scope.csv'),('潜在逐条候选','potential_unified_record_ledger.csv'),('潜在主体证据','potential_unified_applicant_evidence.csv'),('潜在政策任务复核','potential_unified_policy_reviews.csv'),('潜在样本范围复核','potential_unified_document_reviews.csv'),('潜在统计分母','potential_unified_denominators.csv')]:tables.append((name,'results/'+file,None))
 make('750类核心新兴潜在热点分析.xlsx',notes,tables)
 enotes=[('常见取值','paper=论文，patent=专利；strict=范围明确，pending=范围待判断，excluded=不属于任务范围；diagnostic=诊断样本，heldout=规则固定后抽取的核查样本。'),('如何阅读','先看实验情景说明，再看评分指标消融与门槛数据窗口灵敏度。每次试验的明细可用于追溯具体方向。'),('实验规模',f'{len(wt):,}次权重扰动，{len(g)}个门槛、数据、窗口和政策情景。'),('消融是什么意思','每次去掉一个评分成分，重新归一其余权重，观察排名变化；去掉一个入选条件则观察名单变化。'),('权重试验','各原权重分别乘0.8—1.2之间的随机数，再归一。每类500次；weight_000表示第1次，以此类推。'),('时间窗口','核心比较1年、3年、5年；新兴比较此前2年、3年、4年的背景。窗口计数条件按年数或季度比例设置。'),('历史截止点','检查2025Q2、2025Q4、2026Q1。标签、语义判断和引用数据固定，因此是回顾性敏感性分析，不是历史预测回测。'),('删去背景年度','逐次剔除三个背景年度中的一个，检查结果是否被某一年主导。'),('相关与保留比例','Spearman表示排名相似程度；保留比例表示基准入选方向在实验中仍入选的比例。两者都不是准确率。'),('潜在比较范围','评估4个具体应用方向：虚拟电厂、电力大模型两种纳入范围均达标；空气源热泵需核实范围；知识图谱政策证据不足。只比较前1名、前2名，前10/25名不适用。'),('并列规则','按小数点后10位确定并列；展示按ID升序，统计采用并列最小名次。')]
 make('750类热点消融实验与灵敏度分析.xlsx',enotes,[(n,'reliability/'+f,None) for n,f in [('评分指标消融','score_ablation_summary.csv'),('门槛数据窗口灵敏度','gate_and_data_sensitivity.csv'),('1500次权重试验','weight_trials.csv'),('权重排名稳定性','weight_rank_stability.csv'),('逐类别消融排名','score_ablation_ranks.csv'),('情景逐主题依据','data_sensitivity_topic_details.csv'),('潜在任务实验','potential_unified_sensitivity_summary.csv'),('潜在逐任务实验依据','potential_unified_sensitivity_details.csv')]],experiments=True)
 dump(BASE/'data/MULTIYEAR_WORKBOOK_TABLES.json',manifest)
 review=pd.read_csv(R/'multiyear_semantic_review.csv');reads=pd.read_csv(BASE/'review/multiyear_displayed_samples.csv')
 report=f'''# 能源热点分析报告

本研究对750个能源相关主题计算文献指标，并结合样本范围审阅，得到**{len(core)}个核心、{len(em)}个新兴或持续升温初评候选**。潜在应用分析评估4个具体方向：**虚拟电厂、电力大模型可列为跟踪方向；空气源热泵需先核实待判断文献；电力知识图谱目前政策证据不足，暂不推荐、保留观察。**结果供专家评估，不直接证明技术领先或未来成功。

## 方法与阅读方式

核心关注近三年的研究规模和持续性；新兴关注最近一年相对于此前多年背景的上升程度；潜在关注具体应用任务的专利、论文和政策证据。同一主题可能同时满足核心与新兴条件，三类数量不宜直接相加。

| 分析用途 | 时间范围 |
| --- | --- |
| 核心主窗口 | 2023年7月—2026年6月 |
| 最近一年 | 2025年7月—2026年6月 |
| 新兴比较背景 | 2022年7月—2025年6月，三个互不重叠的年度 |
| 五年轨迹 | 2021年7月—2026年6月 |
| 潜在任务证据 | 2026年1—8月，另检查1—5月同期文献与专利 |

每年先用主题论文数除以同期背景库规模，再比较份额。背景年度等权平均，减少不同年度收录量差异的影响。算法先检查数值条件，再结合主题范围审阅形成名单；分数主要用于排序。

## 核心热点

核心评分由三年平均份额40%、同发表年引用表现20%、三年去重机构数15%、活跃季度占比15%、最近一年份额10%组成。要求三年不少于750篇、每年不少于150篇、12季度中至少9个季度各有25篇；最近一年不少于250篇，份额不低于前一年的80%，并满足领域与样本范围要求。

{table(core,['report_rank','category_id','name','core_papers','recent_papers','core_score'])}

## 新兴与持续升温热点

新兴评分由多年背景增长35%、最近同比增长25%、三年份额趋势20%、季度增长一致性10%、机构扩展10%组成。要求最近一年不少于100篇、背景年均不少于50篇；份额至少为前三年均值的1.25倍、前一年的1.15倍，并超过前四年最高值至少5%；至少3个季度同比增长，三年趋势为正。

还需通过计数筛查与数据范围检查：合并背景份额比95%近似下界大于1.05、BH校正q值小于0.05；文本日期、几何、去重范围中的长期与同比份额比，以及最新同月份额比，均满足1.10的要求。这些检验用于筛查，没有消除时间相关性和收录偏差。

{table(em,['report_rank','category_id','name','recent_papers','multiyear_share_ratio','historical_peak_ratio','emerging_score'])}

新兴表示研究关注度上升，也可包括成熟技术的新一轮增长。低基数信号、尚未超过历史峰值的恢复，以及数值通过但范围待核查的方向，在候选或观察表中查看。

## 数据覆盖与样本范围

{table(cov,['publication_year','papers','observed_months','title_only_fraction','jan1_proxy_fraction','metadata_match_fraction'])}

2026年数据仅覆盖1—8月，不能直接用全年总量作同比。年度份额可以控制背景库规模，但不能消除语种、学科、文献类型、文本缺失和日期代理的影响。机构按名称跨年去重，引用为当前数据快照中的累计引用。

全部750类均有指标，其中{int(z.core_eligible.sum())}类通过核心数值条件，{int(z.emerging_robust.sum())}类通过新兴数值及数据方向条件。数值候选与主榜属于不同筛选阶段，核心候选尚未全部完成范围审阅。

跨年审阅记录包括{reads.category_id.nunique()}个方向、{len(reads)}条已展示的题名和最多650字符摘录，阅读记录ID与判断依据可追溯。这是模型辅助样本审阅，不是独立专家金标准，也不提供类别准确率。部分通过的宽方向仍含边界误分，详见Excel中的“跨年样本审阅结论”。

{main_text(table)}

## 专家评估建议

请优先核对主题名称是否准确概括文献范围、相邻主题是否存在重叠、样本是否支持主榜判断，并结合数据范围和政策依赖决定跟踪优先级。未入选不代表方向没有价值；对边界敏感的方向，应先检查具体证据，再解释分数。

[主分析Excel](750类核心新兴潜在热点分析.xlsx)提供完整结果与证据；[实验报告](EXPERIMENT_REPORT.md)说明名单和排名对时间窗口、参数与数据范围的敏感性。
'''
 (BASE/'REPORT.md').write_text(report)
 windows=g[g.kind.isin(['window_length','cutoff_sensitivity','leave_year_out'])];data=g[g.kind.eq('data_sensitivity')]
 experiment=f'''# 消融与灵敏度分析报告

实验检查参数、时间窗口、数据范围和政策证据发生变化时，排名与入选结果是否稳定。共进行**{len(wt):,}次权重扰动、{len(g)}个情景**：核心与新兴101个情景，潜在任务71个情景。

## 如何理解实验

“消融”指每次移除一个评分成分或入选条件，观察它对结果的影响。“灵敏度分析”指改变参数或输入范围，观察结果变化。实验基准是主分析采用的参数与数据设置。

Spearman相关衡量排名是否相似；名次变动说明单个方向的位置变化；保留比例说明基准名单中有多少方向在实验下仍入选。这些指标回答的是稳定性，不是准确率。样本范围判断在实验中固定。

## 评分成分与权重

评分成分消融会重新归一剩余权重。权重试验将每项权重分别乘以0.8—1.2之间的随机数后归一，每类500次，随机种子为75020260925。评分与入选条件分开，因此单独调权不会自动改变资格。

{table(abl[abl.scenario.ne('baseline')],['family','scenario','pool_size','spearman','max_abs_rank_change'])}

500次权重试验的最低排名相关为：核心{wt[wt.family.eq('core')].spearman.min():.4f}，新兴{wt[wt.family.eq('emerging')].spearman.min():.4f}，潜在{wt[wt.family.eq('potential')].spearman.min():.4f}。排名按小数点后10位确定并列，统计采用并列最小名次。

## 时间窗口与截止点

核心检查1年、3年、5年窗口，论文规模门槛按每年250篇设置，季度门槛按75%的比例设置。新兴检查此前2年、3年、4年的背景，并逐次剔除一个背景年度；这些背景均与最近一年不重叠。

{table(windows,['family','scenario','baseline_count','retained','retention'])}

核心在1年、3年、5年窗口下均保留12项，新兴在2年、3年、4年背景下均保留22项。逐年剔除背景时，蒸汽重整制氢与废塑料回收转化存在未保留情景，主分析Excel已列出提示。较早截止点的新兴入选较少，说明结果具有时期依赖性。

较早截止点只使用该截止点的数值条件，不加入后续1—8月确认；但分类、样本判断和引用快照固定。因此这是回顾性的窗口检查，不能解释为当时已预测到这些热点。

![时间窗口检验](figures/multiyear_windows.png)

## 数据范围检查

{table(data,['family','scenario','baseline_count','retained','retention'])}

每种数据范围都重算论文数、背景分母、机构集合和同发表年引用背景。几何情景使用分类过程中的距离指标，它不是750类准确率。新兴情景还保留主数据下的方向确认，因此属于条件压力测试，未覆盖所有过滤条件的交叉组合。某一情景未入选不等于方向无价值。

![数据范围检验](figures/multiyear_data_stress.png)

{experiment_text(table)}

## 如何使用这些结果

专家可据此区分对时间长度较稳定的方向、依赖特定年份的方向，以及对数据范围或政策证据敏感的方向。稳定性较高仍需主题范围和证据质量核查。

[实验Excel](750类热点消融实验与灵敏度分析.xlsx)包含中文情景说明、逐次权重、参数扫描及逐主题结果，可用于追溯每个判断。
'''
 (BASE/'EXPERIMENT_REPORT.md').write_text(experiment)
 (BASE/'README.md').write_text('''# 能源热点分析结果

先阅读[分析报告](REPORT.md)了解入选方向和判断依据，再用[主分析Excel](750类核心新兴潜在热点分析.xlsx)检查指标与样本。

[实验报告](EXPERIMENT_REPORT.md)解释时间窗口、权重和数据范围的影响；[实验Excel](750类热点消融实验与灵敏度分析.xlsx)提供全部情景和逐次试验。

结果包含12个核心、22个新兴或持续升温初评候选。潜在评估4个具体应用方向：虚拟电厂、电力大模型可跟踪；空气源热泵需核实待判断记录；知识图谱政策证据不足，暂不推荐。结果用于专家评审与应用跟踪。

`results`存放结果与证据表，`data/multiyear`存放论文汇总输入，`reliability`存放实验，`review`存放已展示样本。方法参数见`data/MULTIYEAR_METHOD.json`。

核心代码位置见[算法代码导读](../../../docs/ALGORITHM.md)。主分析Excel的“潜在方向结论说明”页逐项解释四个方向的结论。

离线复算和报告生成步骤见仓库的[复现指南](../../../docs/REPRODUCING.md)。
''')
 view=presentation(z)
 save(pd.DataFrame({'field':view.columns,'中文释义':[CN.get(x,x) for x in view.columns]}),'field_dictionary.csv')
 print('DELIVERY',len(core),len(em),len(g),flush=True)

if __name__=='__main__':deliver()
