from mimi.stages.research import _regex_fixed_version


def test_regex_finds_fixed_version():
    text = "- Advisory | u | Fixed in 1.2.6.\n- Other | u | upgrade to 1.2.6 now\n- x | u | update to 1.0.0"
    assert _regex_fixed_version(text) == "1.2.6"


def test_regex_returns_none_without_phrase():
    assert _regex_fixed_version("affects 1.2.5") is None
