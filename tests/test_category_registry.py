from backend.app.rag.embedding.category_registry import (
    normalize_categories,
    normalize_keywords,
    seed_categories,
)


def test_seed_categories_locked_order():
    seeds = seed_categories()
    assert seeds[0] == "Hardware"
    assert seeds[-1] == "Other"
    assert "Machine learning" in seeds


def test_other_exclusivity_and_max_three():
    assert normalize_categories(["Web", "Other", "IoT"]) == ["Other"]
    assert normalize_categories(["Web", "IoT", "Security", "Mobile"]) == [
        "Web",
        "IoT",
        "Security",
    ]
    assert normalize_categories([]) == ["Other"]
    assert normalize_categories(None) == ["Other"]


def test_category_case_canonicalization_and_invent():
    registry = seed_categories()
    assert normalize_categories(["web", "IOT"], registry) == ["Web", "IoT"]
    assert normalize_categories(["Edge Computing"], registry) == ["Edge Computing"]
    assert normalize_categories(["!!!"], registry) == ["Other"]


def test_normalize_keywords_caps_at_fifteen():
    raw = [f"kw{i}" for i in range(20)]
    assert len(normalize_keywords(raw)) == 15
    assert normalize_keywords("Arduino, LoRa, Arduino") == ["Arduino", "LoRa"]
