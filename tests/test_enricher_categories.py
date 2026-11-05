from backend.app.rag.embedding import enricher


def test_enrichment_fallback_keeps_keywords_and_other(monkeypatch):
    monkeypatch.setattr(
        enricher.requests,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("llm down")),
    )
    result = enricher.extract_project_enrichment(
        "Abstract\nA robot that avoids obstacles using ultrasonic sensors.",
        project_title="Robot avoiding obstacles",
        existing_keywords="ultrasonic, robot",
        category_options=enricher.seed_categories(),
    )
    assert result["categories"] == ["Other"]
    assert result["keywords"] == ["ultrasonic", "robot"]
    assert result["summary"] is None


def test_enrichment_empty_text_returns_other():
    result = enricher.extract_project_enrichment("")
    assert result["categories"] == ["Other"]
    assert result["keywords"] == []
