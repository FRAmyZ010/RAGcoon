"""Load and store the administrator's AI configuration in rag_configs."""

import json
import logging

from sqlalchemy.orm import Session

from app.models.rag_config import RagConfig
from app.rag.retrieval.intent_config import get_all_intent_configs, update_intent_config
from app.rag.retrieval.llm_provider import set_active_llm
from app.rag.retrieval.rag_config import RAGConfig, set_active_config

logger = logging.getLogger(__name__)

INTENT_KEY = "intent_configs"
RAG_KEY = "active_rag"
LLM_KEY = "active_llm"
NAMED_PRESETS_KEY = "named_presets"
ACTIVE_PRESET_KEY = "active_preset_name"


def _read_json(db: Session, key: str):
    row = db.query(RagConfig).filter(RagConfig.key == key).one_or_none()
    if row is None or not row.value:
        return None
    return json.loads(row.value)


def _write_json(db: Session, key: str, payload, description: str) -> None:
    raw = json.dumps(payload, ensure_ascii=False)
    row = db.query(RagConfig).filter(RagConfig.key == key).one_or_none()
    if row is None:
        db.add(RagConfig(key=key, value=raw, description=description))
    else:
        row.value = raw
    db.commit()


def hydrate_runtime(db: Session) -> None:
    """Restore saved intent, RAG, and LLM choices after a process restart."""
    try:
        intents = _read_json(db, INTENT_KEY)
        if isinstance(intents, dict):
            for name, updates in intents.items():
                if isinstance(updates, dict):
                    update_intent_config(name, updates)
        rag = _read_json(db, RAG_KEY)
        if isinstance(rag, dict):
            set_active_config(RAGConfig.from_dict(rag))
        llm = _read_json(db, LLM_KEY)
        if isinstance(llm, dict) and llm.get("provider"):
            set_active_llm(llm["provider"], llm.get("model"))
    except Exception:
        logger.exception("Failed to restore saved AI configuration")


def save_intents(db: Session) -> None:
    _write_json(db, INTENT_KEY, get_all_intent_configs(), "Per-intent chat settings")


def load_saved_rag_config(db: Session) -> RAGConfig | None:
    """Return the preset an administrator applied, or None when chat should use intent settings."""
    try:
        raw = _read_json(db, RAG_KEY)
    except Exception:
        logger.exception("Failed to read the active RAG preset")
        return None
    if not isinstance(raw, dict):
        return None
    return RAGConfig.from_dict(raw)


def save_rag(db: Session, config: RAGConfig) -> None:
    _write_json(db, RAG_KEY, config.to_dict(), "Active RAG preset")


def save_llm(db: Session, provider: str, model: str) -> None:
    _write_json(db, LLM_KEY, {"provider": provider, "model": model}, "Active LLM")


def clear_saved_rag(db: Session) -> None:
    """Drop the single RAG override so chat uses the per-intent settings."""
    row = db.query(RagConfig).filter(RagConfig.key == RAG_KEY).one_or_none()
    if row is None:
        return
    db.delete(row)
    db.commit()


def load_named_presets(db: Session) -> dict:
    try:
        raw = _read_json(db, NAMED_PRESETS_KEY)
    except Exception:
        logger.exception("Failed to read named presets")
        return {}
    return raw if isinstance(raw, dict) else {}


def remember_active_preset(db: Session, name: str) -> None:
    _write_json(db, ACTIVE_PRESET_KEY, {"name": name}, "Preset currently applied to chat")


def active_preset_name(db: Session) -> str | None:
    try:
        raw = _read_json(db, ACTIVE_PRESET_KEY)
    except Exception:
        logger.exception("Failed to read the active preset name")
        return None
    if isinstance(raw, dict):
        name = raw.get("name")
        return str(name) if name else None
    return None


def delete_named_preset(db: Session, profile_name: str) -> None:
    """Remove a saved intent preset. Built-in presets are not stored here."""
    presets = load_named_presets(db)
    if profile_name not in presets:
        raise KeyError(f"Preset '{profile_name}' not found.")
    del presets[profile_name]
    _write_json(db, NAMED_PRESETS_KEY, presets, "Named intent and model presets")
    if active_preset_name(db) == profile_name:
        row = db.query(RagConfig).filter(RagConfig.key == ACTIVE_PRESET_KEY).one_or_none()
        if row is not None:
            db.delete(row)
            db.commit()


def save_named_preset(
    db: Session,
    profile_name: str,
    intents: dict,
    llm_provider: str,
    llm_model: str,
    preview_intent: str,
) -> dict:
    """Store every intent setting plus the selected model, then apply that bundle."""
    presets = load_named_presets(db)
    bundle = {
        "profile_name": profile_name,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "preview_intent": preview_intent,
        "intents": intents,
    }
    presets[profile_name] = bundle
    _write_json(db, NAMED_PRESETS_KEY, presets, "Named intent and model presets")
    apply_named_preset(db, profile_name)
    return bundle


def apply_named_preset(db: Session, profile_name: str) -> dict:
    presets = load_named_presets(db)
    bundle = presets.get(profile_name)
    if not isinstance(bundle, dict):
        raise KeyError(f"Preset '{profile_name}' not found.")
    intents = bundle.get("intents") or {}
    for intent_name, values in intents.items():
        if isinstance(values, dict):
            update_intent_config(intent_name, values)
    save_intents(db)
    provider = str(bundle.get("llm_provider") or "ollama")
    model = str(bundle.get("llm_model") or "")
    set_active_llm(provider, model)
    save_llm(db, provider, model)
    clear_saved_rag(db)
    remember_active_preset(db, profile_name)
    return bundle
