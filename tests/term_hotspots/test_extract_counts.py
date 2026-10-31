"""计数层回归测试：季度口径修正（year-only 日期占位）。"""
import datetime as dt

from energy_hotspots.term_hotspots.extract_counts import (
    QUARTERS, _repaired_weights, children_for_year)


def test_real_date_lands_in_its_quarter():
    yq = {2024: ["2024Q1", "2024Q2", "2024Q3", "2024Q4"]}
    w = _repaired_weights(dt.date(2024, 5, 17), yq)
    assert w == {"2024Q2": 1.0}


def test_year_only_placeholder_is_spread():
    """1 月 1 日是 year-only 占位，不是真实的 1 月 1 日。

    实测 2024-01-01 单日 52,276 篇（正常单日约 900 篇），
    直接归 Q1 会把 Q1 抬到其它季度均值的 1.68 倍（均摊后 0.93 倍）。
    """
    yq = {2024: ["2024Q1", "2024Q2", "2024Q3", "2024Q4"]}
    w = _repaired_weights(dt.date(2024, 1, 1), yq)
    assert set(w) == set(yq[2024])
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert all(abs(v - 0.25) < 1e-9 for v in w.values())


def test_year_only_spreads_over_observed_quarters_only():
    """2026 年语料只到 Q3，占位文档就不该摊到 Q4。"""
    yq = {2026: ["2026Q1", "2026Q2", "2026Q3"]}
    w = _repaired_weights(dt.date(2026, 1, 1), yq)
    assert set(w) == {"2026Q1", "2026Q2", "2026Q3"}
    assert all(abs(v - 1 / 3) < 1e-9 for v in w.values())


def test_non_placeholder_jan_first_is_kept():
    """只有『月=日=1 且该年有多个季度』才当占位；单季度年份不动。"""
    yq = {2024: ["2024Q1"]}
    w = _repaired_weights(dt.date(2024, 1, 1), yq)
    assert w == {"2024Q1": 1.0}


def test_window_quarters_shape():
    assert QUARTERS[0] == "2021Q3"
    assert QUARTERS[-1] == "2026Q2"
    assert len(QUARTERS) == 20


def test_patent_scan_dedups_by_publication_number(tmp_path, monkeypatch):
    """同一公开号出现两次（同文件或跨文件）只能计一次。"""
    from energy_hotspots.term_hotspots import extract_counts as ec

    terms = ec.load_terms()
    ec._build_globals(terms)
    term = next(t for t in terms if t.zh == "固态电池")
    pub = "CNTEST0001A"
    path = tmp_path / "patents.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        import csv as _csv
        w = _csv.writer(fh)
        w.writerow(["publication_number", "publication_date", "title", "abstract"])
        for _ in range(2):
            w.writerow([pub, "2025-06-01", "固态电池 test", ""])

    monkeypatch.setattr(ec, "_PATENT_OWNER", {pub: str(path)})
    stat = ec._scan_patent_file(str(path))
    assert stat[(term.key, "2025")] == 1.0

    # 非拥有文件里的同一公开号必须跳过
    monkeypatch.setattr(ec, "_PATENT_OWNER", {pub: "/some/other/file.csv"})
    assert ec._scan_patent_file(str(path)) == {}
