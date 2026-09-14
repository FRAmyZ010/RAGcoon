"""
Interactive Terminal Chat with Live Real-Time Token Streaming & In-Memory Session Memory
"""

import json
import os
import sys
import time
from pathlib import Path

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure stdout uses utf-8 on Windows console
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# pyrefly: ignore [missing-import]
from app.rag.retrieval.prompt import stream_answer_question
# pyrefly: ignore [missing-import]
from app.rag.retrieval.session_manager import session_manager


def print_divider(char="=", length=65):
    print(char * length)


def run_interactive_streaming_chat():
    session_id = f"cli-session-{int(time.time())}"

    print_divider("=")
    print("🚀 RAGcoon Real-Time Streaming Terminal Chat (SSE Protocol)")
    print(f"🔑 Session ID: {session_id}")
    print("💡 Type 'exit' to quit | 'clear' to reset chat memory")
    print_divider("=")

    while True:
        try:
            question = input("\n👤 Question: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Exiting...")
            break

        if not question:
            continue

        if question.lower() in {"exit", "quit"}:
            print("👋 Bye!")
            break

        if question.lower() == "clear":
            session_manager.clear_session(session_id)
            print("🧹 Session memory cleared.")
            continue

        print_divider("-")
        print("🤖 [Streaming Response] : ", end="", flush=True)

        for event in stream_answer_question(question, session_id=session_id):
            event_type = event.get("event")
            event_data = event.get("data", {})

            if event_type == "metadata":
                intent = event_data.get("intent", "FACTOID")
                sources = event_data.get("sources", [])
                timing = event_data.get("timing", {})
                retrieval_t = timing.get("retrieval_seconds", 0.0) + timing.get("rerank_seconds", 0.0)
                # Print metadata preview header
                sys.stdout.write(f"\n[Intent: {intent} | Retrieved: {len(sources)} docs in {retrieval_t:.3f}s]\n\n")
                sys.stdout.flush()

            elif event_type == "token":
                token = event_data.get("token", "")
                sys.stdout.write(token)
                sys.stdout.flush()

            elif event_type == "done":
                timing = event_data.get("timing", {})
                citations = event_data.get("citations", [])
                total_t = timing.get("total_seconds", 0.0)
                llm_t = timing.get("llm_seconds", 0.0)

                print("\n\n" + "-" * 40)
                print(f"⏱️ Timing: Total {total_t:.2f}s (LLM: {llm_t:.2f}s)")
                if citations:
                    print("📄 Citations:")
                    for c in citations:
                        title = c.get("project_title", "Unknown")
                        pages = c.get("pages_formatted") or ", ".join(c.get("pages", []))
                        source = c.get("source", "")
                        print(f"   • {title} (Source: {source} | Pages: {pages})")
                print("-" * 40)

            elif event_type == "error":
                print(f"\n❌ Error: {event_data.get('error')}")


if __name__ == "__main__":
    run_interactive_streaming_chat()
