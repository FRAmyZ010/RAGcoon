from backend.app.rag.embedding.keyword_groups import groups_for_keywords


def test_keywords_land_in_broad_groups():
    grouped = groups_for_keywords(
        "MySQL, ESP32, React, Web Application, Machine Learning, NodeMCU ESP8266, Python, Random Forest, Access points, Analog pH sensor"
    )
    assert grouped == "Data, Hardware, Web, Machine learning, Network"


def test_blank_keywords_have_no_group():
    assert groups_for_keywords(None) == ""
    assert groups_for_keywords("   ") == ""
