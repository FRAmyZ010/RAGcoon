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


if __name__ == "__main__":
    unittest.main()
