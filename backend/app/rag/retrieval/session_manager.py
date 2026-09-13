"""
Module: session_manager.py
Description:
    In-Memory thread-safe session conversation history manager.
    - Caches the last N turns (default 3 turns = 6 messages) per session.
    - Automatically evicts inactive sessions after TTL (default 2 hours).
    - Formats recent context for LLM prompt injection and query disambiguation.
"""

import threading
import time
from collections import OrderedDict
from typing import Any, Optional


class SessionChatManager:
    def __init__(self, max_turns: int = 3, max_sessions: int = 200, ttl_seconds: int = 7200):
        """
        :param max_turns: Number of recent turns (User + AI pairs) to preserve per session.
        :param max_sessions: Maximum concurrent sessions in memory before LRU eviction.
        :param ttl_seconds: Session expiration time in seconds (default 2 hours).
        """
        self.max_turns = max_turns
        self.max_messages = max_turns * 2
        self.max_sessions = max_sessions
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._sessions: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def _cleanup_expired_sessions(self) -> None:
        """Evict expired sessions based on TTL."""
        now = time.time()
        expired_keys = [
            sid for sid, data in self._sessions.items()
            if now - data.get("updated_at", 0) > self.ttl_seconds
        ]
        for sid in expired_keys:
            self._sessions.pop(sid, None)

    def get_history(self, session_id: Optional[str]) -> list[dict[str, str]]:
        """Get recent message history for a given session ID."""
        if not session_id:
            return []

        with self._lock:
            self._cleanup_expired_sessions()
            if session_id not in self._sessions:
                return []

            session = self._sessions[session_id]
            session["updated_at"] = time.time()
            self._sessions.move_to_end(session_id)
            return list(session.get("messages", []))

    def add_message(self, session_id: Optional[str], role: str, content: str) -> None:
        """
        Add a message (user or assistant) to the session history.
        :param session_id: Unique session identifier.
        :param role: 'user' or 'assistant'.
        :param content: Message text.
        """
        if not session_id or not content:
            return

        with self._lock:
            self._cleanup_expired_sessions()

            if session_id not in self._sessions:
                if len(self._sessions) >= self.max_sessions:
                    # Evict oldest session (LRU)
                    self._sessions.popitem(last=False)
                self._sessions[session_id] = {
                    "messages": [],
                    "created_at": time.time(),
                    "updated_at": time.time(),
                }

            session = self._sessions[session_id]
            session["updated_at"] = time.time()
            session["messages"].append({"role": role, "content": content.strip()})

            # Keep only the last N messages
            if len(session["messages"]) > self.max_messages:
                session["messages"] = session["messages"][-self.max_messages:]

            self._sessions.move_to_end(session_id)

    def add_user_message(self, session_id: Optional[str], content: str) -> None:
        self.add_message(session_id, "user", content)

    def add_assistant_message(self, session_id: Optional[str], content: str) -> None:
        self.add_message(session_id, "assistant", content)

    def format_history_for_prompt(self, session_id: Optional[str]) -> str:
        """Format the session history as a string suitable for LLM prompt context."""
        history = self.get_history(session_id)
        if not history:
            return ""

        formatted_lines = []
        for msg in history:
            speaker = "User" if msg["role"] == "user" else "Assistant"
            formatted_lines.append(f"{speaker}: {msg['content']}")

        return "\n".join(formatted_lines)

    def clear_session(self, session_id: Optional[str]) -> bool:
        """Clear a session from memory."""
        if not session_id:
            return False

        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def get_active_session_count(self) -> int:
        with self._lock:
            self._cleanup_expired_sessions()
            return len(self._sessions)


# Global singleton session manager
session_manager = SessionChatManager(max_turns=3, max_sessions=500, ttl_seconds=7200)
