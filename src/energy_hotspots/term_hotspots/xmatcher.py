# -*- coding: utf-8 -*-
"""
Aho-Corasick 多模式匹配器。

四条设计要点，每条都对应一个已确认的度量缺陷：

1. **实例级长度与类型**：每个注册串有独立的 instance id，再映射回词条 pid。
   若用 pid 兼作模式标识，一个词条注册多个变体时长度会互相覆盖（实测会让英文单数形
   几乎全部失效）。
2. **返回跨度**：`search_spans()` 返回 `(pid, start, end)`，使父子词条
   （石墨 / 石墨烯、配电网 / 主动配电网）可以做最长匹配抑制。
3. **ASCII 归一化**：匹配前把 `-`、`_`、`/` 统一成空格、折叠空白、英文转小写，
   模式串同样处理。语料绝大多数是非中文（实测 2026Q2 中文文档 746 / 99,553），
   中文官方名几乎必然匹配不到，实际召回依赖英文官方名与别名；否则
   "Lithium-ion battery" 无法命中 "lithium ion battery"。
4. **短缩略语大小写敏感**：字典里 `一氧化碳` 的别名是 `CO`、`储能` 是 `ES`。
   全小写匹配会让 `Co`（钴）、`Co.`（公司）、`Es`（锿）全部计入——实测这是
   `一氧化碳` 被推成全库第一热点的直接原因。全大写、无空格、2–6 字符的缩略语别名
   走独立的大小写敏感自动机。

中文模式按子串匹配（中文无词边界），英文模式要求两侧非 ASCII 字母数字下划线。
"""
from __future__ import annotations

from collections import deque
from typing import Dict, Iterable, List, Sequence, Tuple

_SEP_MAP = {ord(c): " " for c in "-_/–—"}


def normalize_text(text: str, lower: bool = True) -> str:
    """小写 + 分隔符归一 + 空白折叠。中文不受影响。lower=False 用于缩略语自动机。"""
    if not text:
        return ""
    out = text.lower() if lower else text
    out = out.translate(_SEP_MAP)
    if "  " in out or "\n" in out or "\t" in out:
        out = " ".join(out.split())
    return out


def is_acronym_alias(pattern: str) -> bool:
    """短缩略语：全大写、无空格、2–6 字符、纯 ASCII 字母。

    这类别名词形歧义极高（CO/Co、ES/Es、GO/Go），必须大小写敏感匹配。
    """
    p = (pattern or "").strip()
    if not (2 <= len(p) <= 6) or not p.isascii():
        return False
    if " " in p or not p.isalpha():
        return False
    return p.isupper()


def plural_forms(token: str) -> List[str]:
    """英文单词的常用复数形式；不追求语言学完备，只覆盖技术名词高频写法。"""
    if len(token) < 2 or not token[-1].isalpha():
        return []
    if token.endswith("y") and len(token) > 2 and token[-2] not in "aeiou":
        return [token[:-1] + "ies"]
    if token.endswith(("s", "x", "z")) or token.endswith(("ch", "sh")):
        return [token + "es"]
    return [token + "s"]


def ascii_plural_variants(pattern: str) -> List[str]:
    if not pattern or not pattern.isascii() or " " not in pattern and len(pattern) < 2:
        return []
    tokens = pattern.split(" ")
    forms = plural_forms(tokens[-1])
    return [" ".join(tokens[:-1] + [f]) for f in forms]


class Node:
    __slots__ = ("child", "fail", "out")

    def __init__(self):
        self.child: Dict[str, "Node"] = {}
        self.fail = None
        self.out: List[int] = []


def suppress_contained(spans):
    """抑制被更长命中完全覆盖的短命中（父子词条去重）。

    O(k log k) 扫描而非 O(k\u00b2) 两两比较：按起点推进，维护"起点更早的跨度里
    的最大终点" pref_end。跨度 (s, e) 被覆盖当且仅当 e <= pref_end（存在起点更早
    且终点不早于它的跨度，必然更长），或同起点存在终点更晚的跨度。
    """
    spans = list(spans)
    if len(spans) <= 1:
        return spans
    by_start = {}
    for _p, s, e in spans:
        by_start.setdefault(s, []).append(e)
    covered = set()
    pref_end = -1
    for s in sorted(by_start):
        ends = sorted(by_start[s], reverse=True)
        best_here = ends[0]
        for e in ends:
            if e <= pref_end or e < best_here:
                covered.add((s, e))
        if best_here > pref_end:
            pref_end = best_here
    return [sp for sp in spans if (sp[1], sp[2]) not in covered]


class Aho:
    """多模式匹配。

    参数
    ----
    patterns : Sequence[Tuple[int, str]]
        (词条 pid, 模式串)。同一 pid 可注册多个模式（别名 / 复数变体）。
    case_sensitive : bool
        缩略语自动机用 True；其余用 False。
    add_plural : bool
        是否自动注册 ASCII 复数变体。
    """

    def __init__(self, patterns: Sequence[Tuple[int, str]], case_sensitive: bool = False,
                 add_plural: bool = True):
        self.root = Node()
        self.case_sensitive = case_sensitive
        self._plen: List[int] = []       # instance_id -> 长度
        self._ascii: List[bool] = []     # instance_id -> 是否英文
        self._owner: List[int] = []      # instance_id -> 词条 pid
        for pid, pat in patterns:
            self._add(pid, pat)
            if add_plural:
                for variant in ascii_plural_variants(
                        normalize_text(pat, lower=not case_sensitive)):
                    self._add(pid, variant)
        self._build()

    def _add(self, pid: int, pat: str) -> None:
        pat = normalize_text(pat, lower=not self.case_sensitive)
        if not pat:
            return
        node = self.root
        for ch in pat:
            node = node.child.setdefault(ch, Node())
        inst = len(self._owner)
        self._owner.append(pid)
        self._plen.append(len(pat))
        self._ascii.append(pat.isascii())
        node.out.append(inst)

    def _build(self) -> None:
        q = deque()
        for _ch, nxt in self.root.child.items():
            nxt.fail = self.root
            q.append(nxt)
        while q:
            node = q.popleft()
            for ch, nxt in node.child.items():
                q.append(nxt)
                fail = node.fail
                while fail is not None and ch not in fail.child:
                    fail = fail.fail
                nxt.fail = fail.child.get(ch, self.root) if fail else self.root
                if nxt.fail.out:
                    merged = list(nxt.out)
                    seen = set(merged)
                    for inst in nxt.fail.out:
                        if inst not in seen:
                            seen.add(inst)
                            merged.append(inst)
                    nxt.out = merged

    @staticmethod
    def _is_word_char(c: str) -> bool:
        return c.isalnum() or c == "_"

    def search_spans(self, text: str) -> List[Tuple[int, int, int]]:
        """返回全部 [(pid, start, end)]（同一 pid 可出现多次，用于最长匹配判定）。"""
        if not text:
            return []
        s = normalize_text(text, lower=not self.case_sensitive)
        L = len(s)
        node = self.root
        root = self.root
        plen, ascii_, owner = self._plen, self._ascii, self._owner
        hits: List[Tuple[int, int, int]] = []
        for i, ch in enumerate(s):
            while node is not root and ch not in node.child:
                node = node.fail
            node = node.child.get(ch, root)
            out = node.out
            if not out:
                continue
            for inst in out:
                end = i + 1
                start = end - plen[inst]
                if start < 0:
                    continue
                if ascii_[inst]:
                    if start > 0 and self._is_word_char(s[start - 1]):
                        continue
                    if end < L and self._is_word_char(s[end]):
                        continue
                hits.append((owner[inst], start, end))
        return hits

    def search_dedup(self, text: str, longest: bool = True) -> List[int]:
        """返回去重后的词条 pid 列表（可选父子最长匹配抑制）。"""
        hits = self.search_spans(text)
        if not hits:
            return []
        if longest:
            hits = suppress_contained(hits)
        seen, out = set(), []
        for pid, _s, _e in hits:
            if pid not in seen:
                seen.add(pid)
                out.append(pid)
        return out

    def search(self, text: str) -> List[int]:
        """只返回词条 pid 的简化接口。"""
        return self.search_dedup(text, longest=False)
