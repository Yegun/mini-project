from app import repo_rules

# 규칙표 값은 conftest 의 시험용 가짜 값이다 (두부·당근·우유).


def test_list_rules_returns_all_sorted_by_name(rules):
    names = [rule["name"] for rule in repo_rules.list_rules(rules)]
    assert names == sorted(["두부", "당근", "우유"])


def test_rule_has_aliases_default_storage_and_storage_info(rules):
    rule = repo_rules.find_rule_by_name(rules, "두부")
    assert rule["name"] == "두부"
    assert rule["aliases"] == ["연두부"]
    assert rule["default_storage"] == "fridge"
    assert rule["storages"]["fridge"] == {"allowed": True, "max_days": 10}
    assert rule["storages"]["room"] == {"allowed": False, "max_days": None}


def test_find_rule_by_name_needs_the_exact_name(rules):
    assert repo_rules.find_rule_by_name(rules, "두부") is not None
    assert repo_rules.find_rule_by_name(rules, "연두부") is None  # 별칭은 이름이 아니다
    assert repo_rules.find_rule_by_name(rules, "두") is None
    assert repo_rules.find_rule_by_name(rules, "없는식품") is None


def test_allowed_and_not_allowed_storages(rules):
    milk = repo_rules.find_rule_by_name(rules, "우유")
    assert repo_rules.allowed_storages(milk) == {"fridge"}
    assert repo_rules.not_allowed_storages(milk) == ["room", "freezer"]
    carrot = repo_rules.find_rule_by_name(rules, "당근")
    assert repo_rules.not_allowed_storages(carrot) == []


def test_max_days_by_storage(rules):
    tofu = repo_rules.find_rule_by_name(rules, "두부")
    assert repo_rules.max_days(tofu, "freezer") == 30
    assert repo_rules.max_days(tofu, "room") is None  # 불가한 방법
