from __future__ import annotations

from cognito.text import replace_case_insensitive, _sorted_replacements


def test_replace_case_insensitive_basic():
    result, ops = replace_case_insensitive("Hello World", {"hello": "hi"})

    assert result == "hi World"
    assert len(ops) == 1
    assert ops[0] == {"source": "hello", "target": "hi", "count": 1}


def test_replace_case_insensitive_multiple_occurrences():
    result, ops = replace_case_insensitive("foo FOO Foo", {"foo": "bar"})

    assert result == "bar bar bar"
    assert ops[0]["count"] == 3


def test_replace_case_insensitive_no_match():
    result, ops = replace_case_insensitive("hello world", {"xyz": "abc"})

    assert result == "hello world"
    assert ops == []


def test_replace_case_insensitive_accepts_iterable():
    result, ops = replace_case_insensitive("startup1", [("startup1", "startup2")])

    assert result == "startup2"
    assert len(ops) == 1


def test_replace_longest_match_first():
    result, ops = replace_case_insensitive(
        "com.example is com",
        {"com.example": "dev.service", "com": "org"},
    )

    assert result == "dev.service is org"
    assert len(ops) == 2


def test_sorted_replacements_longest_first():
    items = [("ab", "x"), ("abc", "y"), ("a", "z")]

    result = _sorted_replacements(items)

    assert [r[0] for r in result] == ["abc", "ab", "a"]
