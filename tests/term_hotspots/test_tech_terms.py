import pytest
from energy_hotspots.term_hotspots.tech_terms import load_terms, find_by_zh

def test_load_all_unique():
    terms = load_terms()
    assert len(terms) > 1500
    zhs = [t.zh for t in terms]
    assert len(zhs) == len(set(zhs))

def test_subtopic_parse():
    terms = load_terms()
    for t in terms[:20]:
        assert "." in t.subtopic_id
        assert t.subtopic_name

def test_missing_dictionary_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_terms(tmp_path / "no_such_dir")

def test_empty_dictionary_raises(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        load_terms(empty)

def test_find_by_zh_strict():
    terms = find_by_zh(["锂离子电池"])
    assert len(terms) == 1
    t = terms[0]
    assert t.en.lower() == "lithium-ion battery"
    assert t.match_strings()[0] == "锂离子电池"
    with pytest.raises(KeyError):
        find_by_zh(["一个不期望存在的词12345"])
