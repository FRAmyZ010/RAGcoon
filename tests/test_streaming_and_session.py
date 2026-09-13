"""
Unit and Streaming Tests for AI Core:
1. In-Memory Session Chat History
2. Real-Time Token Generator & Stream Pipeline (Pure Python Generator)
"""

import json
import sys
from pathlib import Path

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag.retrieval.session_manager import SessionChatManager, session_manager
from app.rag.retrieval.prompt import stream_answer_question, answer_question


def test_session_manager_unit():
    print("\n🧪 Testing SessionChatManager Unit Logic...")
    mgr = SessionChatManager(max_turns=2, max_sessions=10, ttl_seconds=60)
    sid = "test-session-123"

    # Initially empty
    assert mgr.get_history(sid) == []

    # Turn 1
    mgr.add_user_message(sid, "โปรเจกต์ RFID มีอะไรบ้าง?")
    mgr.add_assistant_message(sid, "มีโปรเจกต์ Tracking and Locating System บนเว็บครับ")

    history = mgr.get_history(sid)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"

    # Turn 2
    mgr.add_user_message(sid, "แล้วใครเป็นอาจารย์ที่ปรึกษา?")
    mgr.add_assistant_message(sid, "Aj. Surapol Vorapatratorn ครับ")
    history = mgr.get_history(sid)
    assert len(history) == 4

    # Turn 3 (Should evict oldest turn since max_turns=2 => 4 messages max)
    mgr.add_user_message(sid, "ทำในปีไหน?")
    mgr.add_assistant_message(sid, "ปี 2022 ครับ")
    history = mgr.get_history(sid)
    assert len(history) == 4
    assert history[0]["content"] == "แล้วใครเป็นอาจารย์ที่ปรึกษา?"

    prompt_fmt = mgr.format_history_for_prompt(sid)
    assert "User: แล้วใครเป็นอาจารย์ที่ปรึกษา?" in prompt_fmt
    assert "Assistant: ปี 2022 ครับ" in prompt_fmt

    # Clear session
    cleared = mgr.clear_session(sid)
    assert cleared is True
    assert mgr.get_history(sid) == []
    print("✅ SessionChatManager unit test passed successfully!")


def test_streaming_generator_direct():
    print("\n🧪 Testing Pure Python Stream Generator (stream_answer_question)...")
    stream_sid = "test-direct-stream-001"
    session_manager.clear_session(stream_sid)

    events = []
    tokens = []
    
    # Call core stream generator directly
    for event in stream_answer_question("โปรเจกต์ RFID มีอะไรบ้าง", session_id=stream_sid):
        ename = event.get("event")
        edata = event.get("data", {})
        events.append(ename)
        if ename == "token":
            tokens.append(edata.get("token", ""))

    print(f"📡 Generator yielded event count: {len(events)}")
    print(f"📝 Total tokens received: {len(tokens)}")

    assert "metadata" in events, "Stream must emit 'metadata' event"
    assert "done" in events, "Stream must emit 'done' event"
    assert len(tokens) > 0, "Stream must yield token chunks"

    # Check session memory updated
    history = session_manager.get_history(stream_sid)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    print("✅ Pure Python Stream Generator verified successfully!")


if __name__ == "__main__":
    test_session_manager_unit()
    test_streaming_generator_direct()
    print("\n🎉 ALL AI CORE TESTS PASSED SUCCESSFULLY!")
