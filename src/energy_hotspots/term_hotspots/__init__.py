"""按技术词条驱动的热点识别。
输入：词典内 技术中文官方名称；算法用 zh/en/别称 在论文标题+摘要、专利标题+摘要、政策全文中检索。
"""
from .tech_terms import TechTerm, load_terms, find_by_zh, must_term_by_zh
__all__ = ["TechTerm", "load_terms", "find_by_zh", "must_term_by_zh"]
