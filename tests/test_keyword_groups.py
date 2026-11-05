from backend.app.rag.embedding.keyword_groups import groups_for_keywords


def test_legacy_groups_for_keywords_still_maps():
    grouped = groups_for_keywords(
        "MySQL, ESP32, React, Web Application, Machine Learning, NodeMCU ESP8266, Python, Random Forest, Access points, Analog pH sensor"
    )
    assert grouped == "Database, Hardware, Web, Machine learning, Network"


def test_blank_keywords_have_no_group():
    assert groups_for_keywords(None) == ""
    assert groups_for_keywords("   ") == ""
