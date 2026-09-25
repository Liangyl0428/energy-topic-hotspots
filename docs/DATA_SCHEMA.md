# 多年评分输入

score命令输入CSV：

- taxonomy：唯一category_id以及name、domain、status、analysis_scope。直接能源范围值为“能源电力直接相关”。
- quarters：category_id、period（如2026Q2）、papers；每主题每季度一条，非负整数。如有source必须全为paper。需完整五年季度背景，不能把未采集季度填零。
- context：category_id；recent_institutions；core_institutions_1y、core_institutions_3y、core_institutions_5y；year0_institutions至year4_institutions；citation_cohort_percentile。

year0为最近一年，year1为前一年，以此类推。机构并集和引用统计必须对应输入季度表的过滤情景与截止时间；禁止不同范围混用。示例结构即assets快照内data/multiyear/main_2026Q2_context.csv。

`score` 返回数值评分和基本资格；正式结果还需文本/日期、几何、去重和最新同月方向确认，以及明确语义审阅。

潜在输入仍为冻结候选、候选专利主体、任务政策、样本修订、全库背景分母和去重ID子集。category_id是750主题主键，unit_id是潜在任务主键；C0356拆成两个任务，不能相加成单个类别分数。
