# 结果如何验证

验证分为计算一致性、文件一致性和证据核对三个层次。

## 计算一致性

14项测试覆盖时间窗口互不重叠、背景年度隔离、计数门槛随窗口缩放、缺失数据与来源检查、并列排序和快照复算。

完整复算包含55项检查：21张文献指标、候选和轨迹表，24项潜在严格或扩展口径指标，以及10张实验表。实验包含1,500次权重扰动和172个情景。

已验证Python 3.10配合NumPy 2.2、pandas 2.3，以及Python 3.11配合NumPy 2.4、pandas 3.0；也验证了显式Haswell计算内核。环境记录见[RANKING_PORTABILITY.json](RANKING_PORTABILITY.json)，逐项结果见[REPLAY_VALIDATION.json](REPLAY_VALIDATION.json)。

## 文件一致性

两份Excel按导出清单与对应CSV逐单元格核对；文档与展示验证见[DOCUMENTATION_VALIDATION.json](DOCUMENTATION_VALIDATION.json)。公开文件的大小与SHA-256校验值见[FILE_MANIFEST.json](FILE_MANIFEST.json)。发行包解压后的独立复算记录见[ISOLATED_RELEASE_VALIDATION.json](ISOLATED_RELEASE_VALIDATION.json)。

## 数据与证据核对

数据准备阶段核对了五个年度的论文计数、三年机构并集、259个标签与适配分区的校验值，并检查了样本证据和潜在任务同源统计。相关记录见快照中的`data/MULTIYEAR_VALIDATION.json`和`data/POTENTIAL_UNIFIED_VALIDATION.json`。

这些检查说明计算与附带证据可以追溯，不代表750个主题已经通过独立专家评审，也不等同于分类准确率、检索召回率或未来预测效果。
