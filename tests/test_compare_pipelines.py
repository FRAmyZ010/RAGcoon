"""
Unit tests for the Pipeline Comparison & Benchmark Engine.
"""
import pytest
from backend.app.rag.evaluation.compare_pipelines import (
    compute_jaccard_similarity,
    evaluate_output_quality,
    BENCHMARK_SCENARIOS,
)


def test_jaccard_similarity():
    # Identical
    assert compute_jaccard_similarity(["a.pdf", "b.pdf"], ["a.pdf", "b.pdf"]) == 1.0
    # Completely disjoint
    assert compute_jaccard_similarity(["a.pdf"], ["b.pdf"]) == 0.0
    # Partial overlap
    assert compute_jaccard_similarity(["a.pdf", "b.pdf"], ["b.pdf", "c.pdf"]) == pytest.approx(1 / 3)


def test_quality_scoring_rules():
    # Good modern response with citation and fast latency
    good_ans = "โครงงานนี้ใช้เทคโนโลยี LoRaWAN [Source: 1_Final.pdf, Page: 5] ในการรับส่งข้อมูล"
    good_eval = evaluate_output_quality(good_ans, latency_sec=1.2, retrieved_count=5, sources=["1_Final.pdf"])
    assert good_eval["total_score"] >= 80.0
    assert good_eval["breakdown"]["citation_score"] == 30.0
    assert good_eval["breakdown"]["cleanliness_score"] == 25.0
    assert good_eval["breakdown"]["latency_score"] == 25.0

    # Poor response with empty boilerplate marker and slow latency
    bad_ans = "### 🔔 บริการภายนอก / การแจ้งเตือนภายนอก\nไม่มีข้อมูล"
    bad_eval = evaluate_output_quality(bad_ans, latency_sec=12.0, retrieved_count=5, sources=[])
    assert bad_eval["total_score"] < 50.0
    assert bad_eval["breakdown"]["cleanliness_score"] < 25.0
    assert bad_eval["breakdown"]["latency_score"] == 5.0


def test_benchmark_scenarios_structure():
    assert len(BENCHMARK_SCENARIOS) == 7
    for sc in BENCHMARK_SCENARIOS:
        assert "scenario_id" in sc
        assert "name" in sc
        assert "query" in sc
