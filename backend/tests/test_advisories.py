from mimi.advisories import pick_fixed_version

ADVS = [
    {"title": "Prototype Pollution in lodash", "vulnerable_versions": ">=3.7.0 <4.17.19"},
    {"title": "Command Injection in lodash", "vulnerable_versions": "<4.17.21"},
    {"title": "lodash vulnerable to Prototype Pollution", "vulnerable_versions": ">=4.0.0 <=4.17.23"},
]


def test_picks_class_matching_upper_bound():
    assert pick_fixed_version(ADVS, "4.17.15", "prototype_pollution") == "4.17.19"
    assert pick_fixed_version(ADVS, "4.17.15", "command_injection") == "4.17.21"


def test_ignores_non_covering_and_inclusive_bounds():
    assert pick_fixed_version(ADVS, "4.17.20", "prototype_pollution") is None


def test_published_filter():
    assert pick_fixed_version(ADVS, "4.17.15", "prototype_pollution", {"4.17.21"}) is None


def test_covering_titles_counts_inclusive_ranges_and_class():
    from mimi.advisories import covering_titles

    assert covering_titles(ADVS, "4.17.20", "prototype_pollution") == ["lodash vulnerable to Prototype Pollution"]
    assert covering_titles(ADVS, "4.17.15", "xss") == []
