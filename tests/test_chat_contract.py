"""Chat contract: client history cap, session overwrite, and partial stream logs."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("QDRANT_URL", "http://localhost")
os.environ.setdefault("QDRANT_API_KEY", "test")
os.environ.setdefault("JWT_SECRET", "unit-test-jwt-secret-min-32-characters!!")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import BackgroundTasks
from pydantic import ValidationError

from app.rag.retrieval.session_manager import session_manager
from app.schemas.chat import ChatMessage, ChatRequest
from app.services.rag_services import process_rag_stream, sync_client_messages


def _pairs(count: int) -> list[ChatMessage]:
    messages = []
    for index in range(count):
        role = "user" if index % 2 == 0 else "assistant"
        messages.append(ChatMessage(role=role, content=f"m{index}"))
    return messages


class ChatContractTests(unittest.TestCase):
    def test_chat_request_keeps_latest_six_messages_and_rejects_bot(self):
        request = ChatRequest(query_text="now", messages=_pairs(8))

        self.assertEqual(
            [message.content for message in request.messages],
            ["m2", "m3", "m4", "m5", "m6", "m7"],
        )

        with self.assertRaises(ValidationError):
            ChatRequest(
                query_text="now",
                messages=[{"role": "bot", "content": "hello"}],
            )

    def test_sync_client_messages_replaces_cache_and_clears_when_omitted(self):
        workspace_id = "ws-contract-sync"
        session_manager.clear_session(workspace_id)
        try:
            session_manager.add_user_message(workspace_id, "stale question")
            session_manager.add_assistant_message(workspace_id, "stale answer")

            sync_client_messages(workspace_id, _pairs(8))
            history = session_manager.get_history(workspace_id)
            self.assertEqual(
                [item["content"] for item in history],
                ["m2", "m3", "m4", "m5", "m6", "m7"],
            )

            sync_client_messages(workspace_id, None)
            self.assertEqual(session_manager.get_history(workspace_id), [])
        finally:
            session_manager.clear_session(workspace_id)

    def test_stream_error_schedules_partial_answer_log(self):
        workspace_id = "ws-contract-stream"

        def fake_stream(**kwargs):
            yield {"event": "token", "data": {"token": "hello "}}
            yield {"event": "token", "data": {"token": "world"}}
            raise RuntimeError("midway")

        background_tasks = BackgroundTasks()
        with (
            patch("app.services.rag_services.stream_answer_question", side_effect=fake_stream),
            patch("app.services.rag_services.create_search_query_row", return_value=42),
        ):
            generator = process_rag_stream(
                db=None,
                query_text="current question",
                workspace_id=workspace_id,
                messages=[],
                background_tasks=background_tasks,
            )
            with self.assertRaisesRegex(RuntimeError, "midway"):
                list(generator)

        self.assertEqual(len(background_tasks.tasks), 1)
        logged = background_tasks.tasks[0].kwargs
        self.assertEqual(logged["query_id"], 42)
        self.assertEqual(logged["workspace_id"], workspace_id)
        self.assertEqual(logged["query_text"], "current question")
        self.assertEqual(logged["answer_text"], "hello world")
        session_manager.clear_session(workspace_id)


if __name__ == "__main__":
    unittest.main()
