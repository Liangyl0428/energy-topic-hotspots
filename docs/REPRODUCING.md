# 复现与运行

依赖见pyproject.toml。完整重算要求相邻主题仓库已完成全量分类，并准备analyze/data/independent_corpus.duckdb。

在共享工作区根目录：

    .venv-hotspots/bin/python energy-topic-hotspots/pipelines/full_nmf/build.py --classification energy-topic-identification/work/full_nmf500_20260926 --output energy-topic-hotspots/outputs/full_nmf500_20260926
    .venv-hotspots/bin/python energy-topic-hotspots/pipelines/full_nmf/experiments.py --classification energy-topic-identification/work/full_nmf500_20260926 --input energy-topic-hotspots/outputs/full_nmf500_20260926 --output energy-topic-hotspots/outputs/full_nmf500_20260926/experiments

入口校验分类清单、分片哈希及完整性后重算计数、机构、引用与评分。在仓库根目录检查：

    python -m pytest -q
    python tools/check_current_release.py

紧凑结果在assets/full_nmf500；逐条分类及元数据数据库不随Git分发。
