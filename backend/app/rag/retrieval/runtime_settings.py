"""Saved AI Configuration values for the live chat path.

Benchmark callers do not set this context, so they keep their own arguments.
"""

import os
from contextvars import ContextVar

from .system_prompt import DEFAULT_SYSTEM_PROMPT

_current: ContextVar[dict | None] = ContextVar("chat_runtime_settings", default=None)


def activate_chat_settings(settings: dict | None):
    return _current.set(settings)


def restore_chat_settings(token) -> None:
    _current.reset(token)


def current_chat_settings() -> dict | None:
    return _current.get()


def current_llm_model() -> str:
    settings = _current.get()
    if settings and settings.get("llm_model"):
        return str(settings["llm_model"])
    return os.getenv("OLLAMA_MODEL", "gemma3:4b")


def current_temperature() -> float:
    settings = _current.get()
    if settings is not None and settings.get("temperature") is not None:
        return float(settings["temperature"])
    return 0.0


def resolve_system_prompt(built: str) -> str:
    """Use the saved prompt only when an admin changed it."""
    settings = _current.get()
    if not settings:
        return built
    saved = settings.get("system_prompt")
    if not isinstance(saved, str) or not saved.strip():
        return built
    if saved.strip() == DEFAULT_SYSTEM_PROMPT.strip():
        return built
    return saved


def current_top_k() -> int | None:
    settings = _current.get()
    if not settings or settings.get("top_k") is None:
        return None
    return int(settings["top_k"])


def current_min_score() -> float | None:
    settings = _current.get()
    if not settings or settings.get("similarity_threshold") is None:
        return None
    return float(settings["similarity_threshold"])
