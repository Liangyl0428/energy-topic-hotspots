# -*- coding: utf-8 -*-
"""词典装载与查询。

词典 layout: config/technology_terms/{subtopic}.csv, 3 列：技术中文官方名称,技术英文官方名称,别称/简称。
用户输入必须精确等于某行"技术中文官方名称"；算法返回 (zh, en, alias[]) 三元组 + 变体集合（用于全文匹配）。
"""
from __future__ import annotations
import csv, re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

DEFAULT_DICTIONARY = Path(__file__).resolve().parents[3] / "config" / "technology_terms"

@dataclass(frozen=True)
class TechTerm:
    zh: str
    en: str
    aliases: tuple
    subtopic_id: str
    subtopic_name: str
    @property
    def key(self) -> str: return f"{self.subtopic_id}|{self.zh}"
    @property
    def subtopic(self) -> str: return f"{self.subtopic_id} {self.subtopic_name}"
    def match_strings(self) -> List[str]:
        """用于命中的字符串集合顺序：首选中文官方名，其次英文官方名，最后别称。"""
        seen, out = set(), []
        for s in ([self.zh, self.en] + list(self.aliases)):
            s = (s or "").strip()
            if not s: continue
            if s.lower() in seen: continue
            seen.add(s.lower()); out.append(s)
        return out

def _norm_alias_cell(cell: str) -> tuple:
    parts = re.split(r"[；;|/·]", cell or "")
    return tuple(p.strip() for p in parts if p and p.strip())

def load_terms(dictionary: Path = DEFAULT_DICTIONARY) -> List[TechTerm]:
    dictionary = Path(dictionary)
    if not dictionary.is_dir():
        raise FileNotFoundError(
            f"词典目录不存在：{dictionary}。本仓库自带 config/technology_terms/，"\
            "请在源码根目录运行或使用 `pip install -e .`；非 editable 安装不会携带 config。"
        )
    files = sorted(dictionary.glob("*.csv"), key=lambda p: [float(x) for x in p.name.split(" ")[0].split(".")])
    if not files:
        raise FileNotFoundError(f"词典目录中没有 CSV：{dictionary}")
    out: List[TechTerm] = []
    zh_seen = set()
    for f in files:
        subtopic_id, subtopic_name = f.stem.split(" ", 1)
        for row in csv.DictReader(open(f, encoding="utf-8")):
            zh = (row.get("技术中文官方名称") or "").strip()
            en = (row.get("技术英文官方名称") or "").strip()
            alias = _norm_alias_cell((row.get("别称/简称") or ""))
            if not zh:
                continue
            out.append(TechTerm(zh, en, alias, subtopic_id, subtopic_name))
            zh_seen.add(zh)
    assert len(zh_seen) == len(out), f"词典存在重复中文名 {len(out)-len(zh_seen)} 行"
    return out

def find_by_zh(zhs: Iterable[str], dictionary: Path = DEFAULT_DICTIONARY) -> List[TechTerm]:
    by_zh = {t.zh: t for t in load_terms(dictionary)}
    missing = [z for z in zhs if z not in by_zh]
    if missing:
        raise KeyError(f"词典中不存在中文名称（严格匹配）：{missing}；请用 config/technology_terms/*.csv 的「技术中文官方名称」")
    return [by_zh[z] for z in zhs]

def must_term_by_zh(zh: str, dictionary: Path = DEFAULT_DICTIONARY) -> TechTerm:
    return find_by_zh([zh], dictionary)[0]
