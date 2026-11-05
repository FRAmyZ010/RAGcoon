from backend.app.rag.embedding import enricher


def test_enrichment_fallback_keeps_keywords_and_other(monkeypatch):
    monkeypatch.setattr(enricher, "ENRICHMENT_PASSES", 3)
    monkeypatch.setattr(
        enricher,
        "_call_ollama_enrichment",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("llm down")),
    )
    result = enricher.extract_project_enrichment(
        "Abstract\nA robot that avoids obstacles using ultrasonic sensors.",
        project_title="Robot avoiding obstacles",
        existing_keywords="ultrasonic, robot",
        category_options=enricher.seed_categories(),
    )
    # LLM failed all passes → heuristic should lift Robot/ultrasonic out of Other
    assert result["categories"] != ["Other"]
    assert "Hardware" in result["categories"] or "IoT" in result["categories"]
    assert result["keywords"] == ["ultrasonic", "robot"]


def test_enrichment_runs_multiple_passes(monkeypatch):
    calls = {"n": 0}

    def fake_call(**kwargs):
        calls["n"] += 1
        if calls["n"] < 2:
            return {
                "summary": "x",
                "project_type": ["Other"],
                "key_technologies": [],
                "target_problem": None,
                "keywords": ["sensor"],
                "categories": ["Other"],
            }
        return {
            "summary": "x",
            "project_type": ["IoT"],
            "key_technologies": ["Arduino"],
            "target_problem": "dry plants",
            "keywords": ["watering", "sensor", "Arduino"],
            "categories": ["IoT", "Hardware"],
        }

    monkeypatch.setattr(enricher, "ENRICHMENT_PASSES", 3)
    monkeypatch.setattr(enricher, "_call_ollama_enrichment", fake_call)
    result = enricher.extract_project_enrichment(
        "Abstract\nIntelligent watering system using soil moisture sensors.",
        project_title="Intelligent watering system",
        existing_keywords="soil moisture",
        category_options=enricher.seed_categories(),
    )
    assert calls["n"] == 3
    assert result["categories"] == ["IoT", "Hardware"]


def test_enrichment_empty_text_returns_other():
    result = enricher.extract_project_enrichment("")
    assert result["categories"] == ["Other"]
    assert result["keywords"] == []


def test_heuristic_categories_for_web_title():
    cats = enricher._heuristic_categories(
        "Web Application Tourist Guide",
        "clustering, react",
        "This project builds a website for tourists.",
        enricher.seed_categories(),
    )
    assert "Web" in cats
