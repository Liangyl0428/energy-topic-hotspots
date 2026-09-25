# 输入数据格式

`energy-hotspots score`读取三个CSV文件：主题目录、季度论文数、机构与引用信息。以`category_id`关联同一主题。

```bash
energy-hotspots score \
  --taxonomy taxonomy.csv \
  --quarters quarters.csv \
  --context context.csv \
  --output scores.csv
```

输出文件必须尚不存在。默认截止季度为`2026Q2`，核心窗口为3年，新兴背景为此前3年；全部参数见`energy-hotspots score --help`。

## 主题目录：taxonomy.csv

| 字段 | 含义 |
| --- | --- |
| `category_id` | 唯一主题ID，如`C0246` |
| `name` | 主题名称 |
| `domain` | 所属领域 |
| `status` | 类别状态 |
| `analysis_scope` | 分析范围；直接能源范围使用“能源电力直接相关” |

[主题目录示例](../assets/snapshot_20260925/hotspots/results/category_catalog.csv)列出附带的750个主题。

## 季度论文数：quarters.csv

| 字段 | 含义 |
| --- | --- |
| `category_id` | 对应主题ID |
| `period` | 季度，如`2026Q2` |
| `papers` | 论文数，必须为非负整数 |
| `source` | 可选；提供时必须全部为`paper` |

每个“主题×季度”最多一条记录。输入需覆盖截止点之前完整五年的季度背景。只有确认该季度已采集而该主题没有记录时才能记为0；不能用0替代未采集季度。

## 机构与引用：context.csv

| 字段 | 含义 |
| --- | --- |
| `category_id` | 对应主题ID |
| `recent_institutions` | 最近一年参与机构数 |
| `core_institutions_1y`、`core_institutions_3y`、`core_institutions_5y` | 对应窗口内去重后的机构数 |
| `year0_institutions`至`year4_institutions` | 五个独立年度的机构数，`year0`为最近一年 |
| `citation_cohort_percentile` | 按发表年份比较的引用百分位均值 |

机构和引用信息必须与季度表采用相同的数据范围和截止日期。跨年机构数取并集，不能把逐年机构数简单相加。参见[机构与引用示例](../assets/snapshot_20260925/hotspots/data/multiyear/main_2026Q2_context.csv)。

## 输出与潜在任务数据

`score`输出评分和基本数值资格。完整文献流程还需文本日期、几何、去重与同月覆盖检查，并记录主题范围判断。

潜在任务采用独立的记录级证据输入，包括候选论文与专利、申请主体、任务政策、样本判断、背景分母和去重ID。`unit_id`是任务主键，`category_id`是关联的主题主键。一个主题可关联多个任务，例如`C0356`关联知识图谱和大模型两个任务；任务记录可重叠，不应合并成一个类别总分。
