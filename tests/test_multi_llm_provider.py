import sys
import os
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("backend"))

import pytest
from backend.app.rag.retrieval.llm_provider import (
    AVAILABLE_LLM_PROFILES,
    OllamaProvider,
    GeminiProvider,
    OpenAIProvider,
    get_llm_provider,
    set_active_llm,
    get_active_llm,
)
from backend.app.rag.retrieval.prompt import clean_answer


def test_available_llm_profiles():
    """Verify that all required models are registered in AVAILABLE_LLM_PROFILES."""
    profile_ids = [p["id"] for p in AVAILABLE_LLM_PROFILES]
    assert "ollama_gemma3" in profile_ids
    assert "ollama_qwen3" in profile_ids
    assert "gemini_flash" in profile_ids
    assert "openai_gpt4o_mini" in profile_ids


def test_llm_provider_factory():
    """Verify factory returns the correct provider instances."""
    ollama_prov = get_llm_provider("ollama", "qwen3:4b")
    assert isinstance(ollama_prov, OllamaProvider)
    assert ollama_prov.model_name == "qwen3:4b"

    gemini_prov = get_llm_provider("gemini", "gemini-3.5-flash")
    assert isinstance(gemini_prov, GeminiProvider)
    assert gemini_prov.model_name == "gemini-3.5-flash"

    openai_prov = get_llm_provider("openai", "gpt-4o-mini")
    assert isinstance(openai_prov, OpenAIProvider)
    assert openai_prov.model_name == "gpt-4o-mini"


def test_runtime_active_llm_switch():
    """Verify dynamic switching of active LLM provider and model."""
    set_active_llm("gemini", "gemini-3.5-flash")
    prov, mod = get_active_llm()
    assert prov == "gemini"
    assert mod == "gemini-3.5-flash"

    active_instance = get_llm_provider()
    assert isinstance(active_instance, GeminiProvider)
    assert active_instance.model_name == "gemini-3.5-flash"

    # Switch back to local Ollama
    set_active_llm("ollama", "gemma3:4b")
    prov, mod = get_active_llm()
    assert prov == "ollama"
    assert mod == "gemma3:4b"


def test_ollama_prompt_templating():
    """Verify that OllamaProvider formats prompts correctly for Gemma and Qwen."""
    gemma_op = OllamaProvider(model_name="gemma3:4b")
    formatted_g, stops_g = gemma_op._format_prompt("User query", system_prompt="System rules")
    assert "<start_of_turn>user" in formatted_g
    assert "<start_of_turn>model" in formatted_g
    assert "<end_of_turn>" in stops_g

    qwen_op = OllamaProvider(model_name="qwen3:4b")
    formatted_q, stops_q = qwen_op._format_prompt("User query", system_prompt="System rules", thinking=False)
    assert "<|im_start|>system" in formatted_q
    assert "<|im_start|>user" in formatted_q
    assert "<|im_start|>assistant" in formatted_q
    assert "<|im_end|>" in stops_q


def test_clean_answer_filters_thinking():
    """Verify that clean_answer strips <think> blocks and chain of thought monologue."""
    raw_with_think = "<think>Analyzing context... Need to find SX1276</think>โครงงานที่ใช้ SX1276 คือ The LoRaWAN [Source: 1.pdf, Page: 5]"
    cleaned = clean_answer(raw_with_think, is_thai=True)
    assert "<think>" not in cleaned
    assert "Analyzing context" not in cleaned
    assert "The LoRaWAN" in cleaned


def test_openai_missing_credits_graceful_handling():
    """Verify OpenAIProvider gracefully catches 429 quota exhaustion without crashing."""
    op = OpenAIProvider(api_key="invalid_test_key_sk")
    ans, stats = op.generate("Test prompt")
    assert "error" in stats or "⚠️" in ans
