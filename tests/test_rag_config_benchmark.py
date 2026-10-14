import sys
import os
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("backend"))

import pytest
import json
from backend.app.rag.retrieval.rag_config import (
    RAGConfig,
    CONFIG_PRESETS,
    get_config_preset,
    get_active_config,
    set_active_config,
)
from backend.app.rag.evaluation.config_benchmark import (
    load_golden_dataset,
    _check_retrieval_hit,
    _calculate_phrase_recall,
    _check_hallucination_guard,
    run_benchmark_on_item,
)
from backend.app.rag.retrieval.llm_provider import (
    AVAILABLE_LLM_PROFILES,
    get_active_llm,
    set_active_llm,
    get_llm_provider,
    OllamaProvider,
    GeminiProvider,
    OpenAIProvider,
)


def test_rag_config_dataclass_and_presets():
    """Verify RAGConfig creation, dict serialization, and preset existence."""
    cfg = RAGConfig(top_k=20, rerank_top_n=7, enable_hybrid=True, prompt_preset="concise")
    assert cfg.top_k == 20
    assert cfg.rerank_top_n == 7
    assert cfg.enable_hybrid is True
    assert cfg.prompt_preset == "concise"

    d = cfg.to_dict()
    assert d["top_k"] == 20
    assert d["prompt_preset"] == "concise"

    restored = RAGConfig.from_dict(d)
    assert restored.top_k == 20
    assert restored.prompt_preset == "concise"

    # Presets verification
    expected_presets = [
        "precision_hybrid",
        "fast_mode",
        "deep_academic",
        "ablation_dense_only",
        "ablation_no_rerank",
        "ablation_no_filter",
        "model_qwen3",
        "model_gemini",
        "model_openai",
    ]
    for p_name in expected_presets:
        assert p_name in CONFIG_PRESETS, f"Preset '{p_name}' should exist in CONFIG_PRESETS"
        preset = get_config_preset(p_name)
        assert isinstance(preset, RAGConfig)
        assert preset.profile_name == p_name


def test_golden_dataset_structure():
    """Verify that golden_dataset.json contains valid test cases."""
    dataset = load_golden_dataset()
    assert len(dataset) >= 15, "Golden dataset should have at least 15 ground truth cases"

    for item in dataset:
        assert "id" in item
        assert "query" in item
        assert "expected_sources" in item
        assert "key_phrases" in item
        assert "should_reject" in item
        assert isinstance(item["expected_sources"], list)
        assert isinstance(item["key_phrases"], list)


def test_metric_calculation_helpers():
    """Test retrieval hit rate, phrase recall, and hallucination guard calculations."""
    # 1. Retrieval Hit
    expected = ["1_6031501044_6031501061_FinalProject.pdf"]
    retrieved_match = ["1_6031501044_6031501061_FinalProject.pdf", "other.pdf"]
    retrieved_miss = ["unrelated.pdf"]

    assert _check_retrieval_hit(retrieved_match, expected) is True
    assert _check_retrieval_hit(retrieved_miss, expected) is False
    assert _check_retrieval_hit([], []) is True

    # 2. Key Phrase Recall
    text = "โครงงานนี้ใช้เทคโนโลยี LoRa ร่วมกับ ESP32 และโมดูล SX1276"
    assert _calculate_phrase_recall(text, ["LoRa", "ESP32", "SX1276"]) == 100.0
    assert _calculate_phrase_recall(text, ["LoRa", "Arduino"]) == 50.0
    assert _calculate_phrase_recall(text, ["Raspberry Pi"]) == 0.0

    # 3. Hallucination Guard
    rejected_ans = "ขออภัยครับ ไม่พบข้อมูลเกี่ยวกับเรื่องนี้ในเอกสาร"
    hallucinated_ans = "โครงงานนี้เชื่อมต่อกับระบบภายนอกเรียบร้อยแล้ว"
    assert _check_hallucination_guard(rejected_ans, should_reject=True) is True
    assert _check_hallucination_guard(hallucinated_ans, should_reject=True) is False
    assert _check_hallucination_guard(hallucinated_ans, should_reject=False) is True


def test_multi_llm_profiles_and_routing():
    """Verify that LLM providers can be switched and instantiated."""
    profile_ids = [p["id"] for p in AVAILABLE_LLM_PROFILES]
    assert "ollama_gemma3" in profile_ids
    assert "ollama_qwen3" in profile_ids
    assert "gemini_flash" in profile_ids
    assert "openai_gpt4o_mini" in profile_ids

    # Provider factory test
    ollama_p = get_llm_provider("ollama", "qwen3:4b")
    assert isinstance(ollama_p, OllamaProvider)
    assert ollama_p.model_name == "qwen3:4b"

    gemini_p = get_llm_provider("gemini", "gemini-3.5-flash")
    assert isinstance(gemini_p, GeminiProvider)

    openai_p = get_llm_provider("openai", "gpt-4o-mini")
    assert isinstance(openai_p, OpenAIProvider)


def test_fast_path_benchmark_execution():
    """Verify execution of a fast-path ground truth test case under fast_mode."""
    dataset = load_golden_dataset()
    gt04 = next(tc for tc in dataset if tc["id"] == "GT-04")
    cfg = get_config_preset("fast_mode")

    result = run_benchmark_on_item(gt04, cfg)
    assert result["success"] is True
    assert result["fast_path_used"] is True
    assert result["hit_rate"] == 1.0
    assert result["quality_score"] >= 80.0
    assert "Suppakarn" in result["answer"] or "ที่ปรึกษา" in result["answer"]
