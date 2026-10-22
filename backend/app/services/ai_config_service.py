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


def save_rag(db: Session, config: RAGConfig) -> None:
    _write_json(db, RAG_KEY, config.to_dict(), "Active RAG preset")


def save_llm(db: Session, provider: str, model: str) -> None:
    _write_json(db, LLM_KEY, {"provider": provider, "model": model}, "Active LLM")
