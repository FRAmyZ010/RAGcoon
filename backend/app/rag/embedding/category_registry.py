"""Live document category registry (seed + LLM-invented) stored in rag_configs."""

from __future__ import annotations

import json
import logging
import re
from typing import Iterable

logger = logging.getLogger(__name__)

CATEGORIES_KEY = "document_categories"
SEED_CATEGORIES = [
    "Hardware",
    "IoT",
    "Network",
    "Web",
    "Mobile",
    "Machine learning",
    "Security",
    "Database",
    "Automation",
    "Other",
]
SEED_LOCKED = frozenset(SEED_CATEGORIES)
MAX_CATEGORIES = 3
MAX_KEYWORDS = 15

_SEED_LOOKUP = {name.casefold(): name for name in SEED_CATEGORIES}


def seed_categories() -> list[str]:
    return list(SEED_CATEGORIES)


def _canonical_from_registry(name: str, registry: list[str]) -> str | None:
    folded = name.casefold().strip()
    if not folded:
        return None
    if folded in _SEED_LOOKUP:
        return _SEED_LOOKUP[folded]
    for existing in registry:
        if existing.casefold() == folded:
            return existing
    cleaned = re.sub(r"\s+", " ", name.strip())
    if not cleaned or cleaned.casefold() == "other":
        return "Other"
    # Invented English-ish label
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9 &/\-]{1,40}", cleaned):
        return None
    return cleaned


def normalize_keywords(raw: str | list | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = re.split(r"[,،;|/、]", raw)
    elif isinstance(raw, list):
        parts = raw
    else:
        parts = [str(raw)]
    items: list[str] = []
    for part in parts:
        text = re.sub(r"\s+", " ", str(part).strip(" .;"))
        if text and text not in items:
            items.append(text)
        if len(items) >= MAX_KEYWORDS:
            break
    return items


def normalize_categories(
    raw: str | list | None,
    registry: list[str] | None = None,
) -> list[str]:
    """Validate category list: max 3; Other is exclusive."""
    registry = list(registry or SEED_CATEGORIES)
    if raw is None:
        return ["Other"]
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.split(",") if p.strip()]
    elif isinstance(raw, list):
        parts = [str(p).strip() for p in raw if str(p).strip()]
    else:
        parts = []

    resolved: list[str] = []
    for part in parts:
        canon = _canonical_from_registry(part, registry)
        if not canon:
            continue
        if canon not in resolved:
            resolved.append(canon)
        if len(resolved) >= MAX_CATEGORIES:
            break

    if not resolved:
        return ["Other"]
    if "Other" in resolved:
        return ["Other"]
    return resolved[:MAX_CATEGORIES]


def categories_to_storage(categories: Iterable[str]) -> str:
    return ", ".join(categories)


def _read_registry_payload(db) -> list[str] | None:
    from app.models.rag_config import RagConfig

    row = db.query(RagConfig).filter(RagConfig.key == CATEGORIES_KEY).one_or_none()
    if row is None or not row.value:
        return None
    try:
        payload = json.loads(row.value)
    except json.JSONDecodeError:
        logger.warning("Invalid document_categories JSON in rag_configs")
        return None
    if isinstance(payload, dict):
        names = payload.get("categories")
    else:
        names = payload
    if not isinstance(names, list):
        return None
    cleaned = [str(item).strip() for item in names if str(item).strip()]
    return cleaned or None


def _write_registry(db, categories: list[str]) -> None:
    from app.models.rag_config import RagConfig

    payload = {"categories": categories}
    raw = json.dumps(payload, ensure_ascii=False)
    row = db.query(RagConfig).filter(RagConfig.key == CATEGORIES_KEY).one_or_none()
    if row is None:
        db.add(
            RagConfig(
                key=CATEGORIES_KEY,
                value=raw,
                description="Document category registry (seed + invented)",
            )
        )
    else:
        row.value = raw
    db.commit()


def ensure_seeded(db) -> list[str]:
    """Bootstrap seed categories when the registry row is missing/empty."""
    existing = _read_registry_payload(db)
    if existing:
        # Keep seed names present even if an older row drifted
        merged: list[str] = []
        for name in SEED_CATEGORIES:
            if name not in merged:
                merged.append(name)
        for name in existing:
            canon = _canonical_from_registry(name, merged) or name.strip()
            if canon and canon not in merged:
                merged.append(canon)
        if merged != existing:
            _write_registry(db, merged)
        return merged
    seeded = seed_categories()
    _write_registry(db, seeded)
    return seeded


def get_categories(db) -> list[str]:
    return ensure_seeded(db)


def register_invented(db, names: Iterable[str]) -> list[str]:
    """Permanently add non-Other invented categories into the live registry."""
    registry = ensure_seeded(db)
    changed = False
    for raw in names:
        canon = _canonical_from_registry(str(raw), registry)
        if not canon or canon == "Other":
            continue
        if canon not in registry:
            registry.append(canon)
            changed = True
    if changed:
        _write_registry(db, registry)
    return registry


def is_seed_or_other(name: str) -> bool:
    return name.strip() in SEED_LOCKED


def list_category_entries(db) -> list[dict]:
    """Return registry rows with seed/deletable flags for the admin UI."""
    registry = ensure_seeded(db)
    return [
        {
            "name": name,
            "is_seed": name in SEED_LOCKED,
            "deletable": name not in SEED_LOCKED,
        }
        for name in registry
    ]


def delete_invented_category(db, name: str) -> dict:
    """
    Remove an invented category from the registry and strip it from documents.
    Empty category lists become Other. Seed + Other cannot be deleted.
    """
    from app.models.document import Document

    registry = ensure_seeded(db)
    canon = _canonical_from_registry(name, registry)
    if not canon or canon not in registry:
        raise KeyError(f"Category '{name}' not found")
    if canon in SEED_LOCKED:
        raise PermissionError(f"Seed category '{canon}' cannot be deleted")

    registry = [item for item in registry if item != canon]
    _write_registry(db, registry)

    remapped = 0
    rows = db.query(Document).filter(Document.keyword_groups.isnot(None)).all()
    for row in rows:
        parts = [part.strip() for part in (row.keyword_groups or "").split(",") if part.strip()]
        if not any(part.casefold() == canon.casefold() for part in parts):
            continue
        remaining = [part for part in parts if part.casefold() != canon.casefold()]
        row.keyword_groups = categories_to_storage(
            normalize_categories(remaining or ["Other"], registry)
        )
        remapped += 1
    db.commit()
    return {
        "deleted": canon,
        "documents_updated": remapped,
        "categories": registry,
    }
