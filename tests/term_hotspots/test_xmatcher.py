"""匹配器回归测试：覆盖每一处已确认的度量缺陷。"""
from energy_hotspots.term_hotspots.xmatcher import (
    Aho, is_acronym_alias, normalize_text, suppress_contained)


def ac(pats, **kw):
    return Aho(list(enumerate(pats)), **kw)


# ---------------------------------------------------------------- 基本匹配
def test_cjk_substring():
    a = ac(["锂离子电池", "构网型控制", "电解水"])
    assert set(a.search("新型储能技术与装备离不开锂离子电池。")) == {0}
    assert set(a.search("《构网型控制》与电解水制氢")) == {1, 2}


def test_ascii_word_boundary():
    a = ac(["power system", "VSM", "STATCOM"])
    assert set(a.search("smart VSM control")) == {1}
    assert a.search("XVSMy") == []
    assert set(a.search("…（STATCOM）…")) == {2}
    assert a.search("power systematics") == []


def test_ascii_case_insensitive_by_default():
    a = ac(["Battery", "Electrode"])
    assert set(a.search("THE BATTERY AND electrode")) == {0, 1}


# ------------------------------------------------- 分隔符归一
def test_hyphen_and_space_normalization():
    a = ac(["Lithium-ion battery"])
    # 连字符 / 空格 / 下划线在英文技术名里高度可互换
    assert a.search("a lithium ion battery pack") == [0]
    assert a.search("lithium-ion batteries") == [0]
    assert a.search("lithium_ion_battery") == [0]
    assert normalize_text("A  LI-ION  cell") == "a li ion cell"


# ---------------------------------------------------- 复数变体
def test_plural_variants():
    a = ac(["battery", "cell", "bus", "electrode material"])
    assert a.search("many batteries") == [0]
    assert a.search("several cells") == [1]
    assert a.search("two buses") == [2]
    assert a.search("electrode materials") == [3]


def test_plural_does_not_break_singular():
    """复数变体不能覆盖单数模式的长度，否则单数匹配几乎全废。"""
    a = ac(["battery"])
    assert a.search("one battery") == [0]
    assert a.search("two batteries") == [0]


# -------------------------------------- 短缩略语大小写敏感
def test_acronym_detection():
    assert is_acronym_alias("CO")
    assert is_acronym_alias("ES")
    assert is_acronym_alias("LIB")
    assert not is_acronym_alias("Co")
    assert not is_acronym_alias("Energy storage")
    assert not is_acronym_alias("g-C3N4")
    assert not is_acronym_alias("A")


def test_acronym_case_sensitive_automaton():
    """字典里『一氧化碳』的别名是 CO；全小写匹配会把 Co（钴）全部计入。"""
    a = ac(["CO"], case_sensitive=True, add_plural=False)
    assert a.search("CO emission") == [0]
    assert a.search("Co doping in cobalt oxide") == []
    assert a.search("co-doped") == []


# ----------------------------------- 父子词条最长匹配
def test_longest_match_suppresses_parent():
    a = ac(["石墨", "石墨烯", "配电网", "主动配电网"])
    assert set(a.search_dedup("石墨烯薄膜")) == {1}
    assert set(a.search_dedup("主动配电网")) == {3}


def test_parent_kept_when_standalone_occurrence_exists():
    """同一文档里既出现子词条又出现独立的父词条，父词条必须保留。"""
    a = ac(["石墨", "石墨烯"])
    assert set(a.search_dedup("石墨烯与石墨的区别")) == {0, 1}


def test_suppress_contained_spans():
    spans = [(0, 0, 2), (1, 0, 3), (0, 5, 7)]
    kept = suppress_contained(spans)
    boxes = {(s, e) for _p, s, e in kept}
    assert (0, 2) not in boxes          # 被 [0,3) 完全覆盖
    assert (0, 3) in boxes
    assert (5, 7) in boxes              # 独立出现必须保留


# -------------------------------------------- 文档级去重
def test_document_level_dedup_across_variants():
    """同一词条的中文名 + 英文名 + 别名同时出现，只能算 1 次。"""
    # 三个变体必须属于同一个词条 pid，才是"同一词条去重"
    a = Aho([(0, "锂离子电池"), (0, "Lithium-ion battery"), (0, "LIB")])
    assert a.search_dedup("锂离子电池 LIB lithium-ion battery") == [0]
