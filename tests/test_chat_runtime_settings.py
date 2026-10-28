"""Saved chat settings apply only inside the request context."""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("QDRANT_URL", "http://localhost")
os.environ.setdefault("QDRANT_API_KEY", "test")

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag.retrieval.runtime_settings import (
    activate_chat_settings,
    current_min_score,
    current_temperature,
    current_top_k,
    resolve_system_prompt,
    restore_chat_settings,
)
from app.rag.evaluation.benchmark_run import build_benchmark_summary_prompt, load_handoff_cases
from app.rag.retrieval.intent_config import get_intent_config, reset_intent_configs
from app.rag.retrieval.system_prompt import DEFAULT_SYSTEM_PROMPT


class ChatRuntimeSettingsTests(unittest.TestCase):
    def test_no_saved_settings_keep_built_prompt_and_routing(self):
        self.assertEqual(resolve_system_prompt("built"), "built")
        self.assertIsNone(current_top_k())
        self.assertIsNone(current_min_score())
        self.assertEqual(current_temperature(), 0.0)

    def test_saved_settings_override_only_while_active(self):
        token = activate_chat_settings({
            "llm_model": "qwen3:4b",
            "temperature": 0.4,
            "system_prompt": "Answer in one sentence.",
            "top_k": 8,
            "similarity_threshold": 0.2,
        })
        try:
            self.assertEqual(resolve_system_prompt("built"), "Answer in one sentence.")
            self.assertEqual(current_top_k(), 8)
            self.assertEqual(current_min_score(), 0.2)
            self.assertEqual(current_temperature(), 0.4)
        finally:
            restore_chat_settings(token)
        self.assertEqual(resolve_system_prompt("built"), "built")
        self.assertIsNone(current_top_k())

    def test_unchanged_default_prompt_keeps_intent_text(self):
        token = activate_chat_settings({"system_prompt": DEFAULT_SYSTEM_PROMPT, "top_k": 25})
        try:
            self.assertEqual(resolve_system_prompt("built-with-intent"), "built-with-intent")
        finally:
            restore_chat_settings(token)

class HandoffIntentMatrixTests(unittest.TestCase):
    def test_sheet_matrix_keeps_factoid_separate_from_lookup(self):
        reset_intent_configs()
        factoid = get_intent_config("FACTOID")
        lookup = get_intent_config("FACTUAL_LOOKUP")
        self.assertEqual(factoid.top_k, 15)
        self.assertEqual(factoid.max_context_chunks, 3)
        self.assertEqual(lookup.top_k, 25)
        self.assertEqual(lookup.rerank_top_n, 8)
        self.assertEqual(get_intent_config("COMPARISON").top_k, 20)
        self.assertEqual(get_intent_config("EXPLORATORY").rerank_top_n, 10)
        self.assertEqual(get_intent_config("CODE").max_context_chunks, 4)

    def test_handoff_cases_follow_the_sheet_questions(self):
        cases = load_handoff_cases(limit=2)
        self.assertEqual(len(cases), 2)
        self.assertIn(cases[0]["query"], {
            "อาจารสุรพลดูแลเรื่องไรบ้าง",
            "โครงงานที่ใช้โมดูล SX1276 มีอะไรบ้าง",
        })

    def test_benchmark_summary_prompt_includes_both_answers(self):
        prompt = build_benchmark_summary_prompt("fast_mode", "deep_academic", [{
            "query": "Who advises The LoRaWAN?",
            "baseline_score": 100,
            "candidate_score": 0,
            "baseline_seconds": 1.2,
            "candidate_seconds": 3.4,
            "speedup": 0.35,
            "baseline_answer": "Ajarn A advises it.",
            "candidate_answer": "No advisor was found.",
            "baseline_sources": "lora.pdf",
            "candidate_sources": "none",
        }])
        self.assertIn("Ajarn A advises it.", prompt)
        self.assertIn("No advisor was found.", prompt)
        self.assertIn("English", prompt)
        self.assertIn("fast_mode", prompt)
        self.assertIn("deep_academic", prompt)


if __name__ == "__main__":
    unittest.main()
