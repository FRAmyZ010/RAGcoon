"""
Postgres catalog lookup for CATEGORY_LIST intent.

Skips vector retrieval: lists projects from documents.keyword_groups (+ optional
year / advisor / author filters) with pagination and fuzzy category suggestions.
"""

from __future__ import annotations

import difflib
import re
from typing import Any, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.document import Document
from app.rag.embedding.category_registry import get_categories, normalize_categories

CATEGORY_LIST_PAGE_SIZE = 10

# Filters this path can apply in Postgres. Anything else → caller should fall back to RAG.
CATALOG_SUPPORTED_FILTER_KEYS = frozenset({"category", "year", "advisor", "author"})


def catalog_unsupported_filters(filters: Optional[dict[str, Any]]) -> list[str]:
    """Return filter keys that cannot be satisfied by the Postgres catalog path."""
    if not filters:
        return []
    unsupported: list[str] = []
    for key in filters:
        if key not in CATALOG_SUPPORTED_FILTER_KEYS:
            unsupported.append(key)
    return unsupported


def can_answer_from_catalog(filters: Optional[dict[str, Any]]) -> bool:
    """True when CATEGORY_LIST can be answered from DB without hybrid retrieval."""
    return len(catalog_unsupported_filters(filters)) == 0


def _parse_category_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _resolve_category_label(db: Session, raw: str | None) -> tuple[Optional[str], list[str]]:
    """
    Resolve a user category label against the live registry.

    Returns (canonical_match_or_None, suggested_names).
    """
    if not raw or not str(raw).strip():
        registry = get_categories(db)
        return None, list(registry)[:5]

    registry = get_categories(db)
    hint = str(raw).strip()

    # Exact / seed-normalized match
    normalized = normalize_categories([hint], registry=registry)
    if normalized and normalized != ["Other"]:
        for name in normalized:
            if any(name.casefold() == reg.casefold() for reg in registry):
                # Prefer registry canonical casing
                for reg in registry:
                    if reg.casefold() == name.casefold():
                        return reg, []
                return name, []

    # Case-insensitive exact against registry (including invented)
    folded = hint.casefold()
    for reg in registry:
        if reg.casefold() == folded:
            return reg, []

    # Fuzzy suggestions
    suggestions = difflib.get_close_matches(
        hint,
        registry,
        n=5,
        cutoff=0.45,
    )
    # Also rank by substring containment
    contained = [reg for reg in registry if folded in reg.casefold() or reg.casefold() in folded]
    merged: list[str] = []
    for name in suggestions + contained:
        if name not in merged:
            merged.append(name)
    return None, merged[:5]


def _row_matches_category(keyword_groups: str | None, category: str) -> bool:
    target = category.casefold()
    return any(part.casefold() == target for part in _parse_category_list(keyword_groups))


def _year_matches(row: Document, year: Any) -> bool:
    if year is None or year == "":
        return True
    academic_year = row.academic_year
    if academic_year is None:
        return False
    try:
        return int(academic_year) == int(str(year).strip())
    except (TypeError, ValueError):
        return str(academic_year) == str(year).strip()


def _advisor_matches(row: Document, advisor: Any) -> bool:
    if not advisor:
        return True
    hay = (row.advisor or "").casefold()
    needle = str(advisor).strip().casefold()
    if not needle:
        return True
    return needle in hay or hay in needle


def _author_matches(row: Document, author: Any) -> bool:
    if not author:
        return True
    hay = (row.authors or "").casefold()
    needles = author if isinstance(author, list) else [author]
    for item in needles:
        needle = str(item).strip().casefold()
        if not needle:
            continue
        if needle not in hay:
            return False
    return True


def _document_to_catalog_item(row: Document) -> dict[str, Any]:
    categories = _parse_category_list(row.keyword_groups)
    return {
        "document_id": row.id,
        "title": (row.title or "").strip() or row.filename,
        "filename": row.filename,
        "year": row.academic_year,
        "authors": row.authors,
        "advisor": row.advisor,
        "keywords": row.keywords,
        "categories": categories,
        "supervisory_committee": row.supervisory_committee,
        "status": row.status,
    }


def list_projects_by_category(
    db: Session,
    *,
    category: Optional[str] = None,
    year: Any = None,
    advisor: Any = None,
    author: Any = None,
    offset: int = 0,
    limit: int = CATEGORY_LIST_PAGE_SIZE,
) -> dict[str, Any]:
    """
    List catalog projects tagged with ``category``, optionally filtered further.

    When the category does not resolve, returns suggestions and an empty page
    (no invented projects).
    """
    offset = max(0, int(offset or 0))
    limit = max(1, min(int(limit or CATEGORY_LIST_PAGE_SIZE), 50))

    matched_category, suggestions = _resolve_category_label(db, category)
    if matched_category is None:
        return {
            "matched_category": None,
            "requested_category": category,
            "suggested_categories": suggestions,
            "total": 0,
            "offset": offset,
            "limit": limit,
            "has_more": False,
            "projects": [],
        }

    rows = (
        db.query(Document)
        .options(joinedload(Document.project))
        .order_by(Document.title.asc(), Document.filename.asc())
        .all()
    )

    matched: list[Document] = []
    for row in rows:
        if not _row_matches_category(row.keyword_groups, matched_category):
            continue
        if not _year_matches(row, year):
            continue
        if not _advisor_matches(row, advisor):
            continue
        if not _author_matches(row, author):
            continue
        matched.append(row)

    total = len(matched)
    page = matched[offset : offset + limit]
    return {
        "matched_category": matched_category,
        "requested_category": category,
        "suggested_categories": [],
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(page) < total,
        "projects": [_document_to_catalog_item(row) for row in page],
    }


def list_projects_from_filters(
    db: Session,
    filters: Optional[dict[str, Any]],
    *,
    offset: int = 0,
    limit: int = CATEGORY_LIST_PAGE_SIZE,
) -> dict[str, Any]:
    """Convenience wrapper using the query-processor filter dict."""
    filters = filters or {}
    return list_projects_by_category(
        db,
        category=filters.get("category"),
        year=filters.get("year"),
        advisor=filters.get("advisor"),
        author=filters.get("author"),
        offset=offset,
        limit=limit,
    )


def format_catalog_context(catalog: dict[str, Any]) -> str:
    """Render catalog page as plain text context for the answer LLM."""
    matched = catalog.get("matched_category")
    if not matched:
        requested = catalog.get("requested_category") or "(unspecified)"
        suggestions = catalog.get("suggested_categories") or []
        lines = [
            f"No exact document category match for '{requested}'.",
            "Suggested categories from the registry:",
        ]
        if suggestions:
            for name in suggestions:
                lines.append(f"- {name}")
        else:
            lines.append("- (none)")
        lines.append("Do not invent projects. Ask the user to pick a suggested category.")
        return "\n".join(lines)

    total = int(catalog.get("total") or 0)
    offset = int(catalog.get("offset") or 0)
    projects = catalog.get("projects") or []
    has_more = bool(catalog.get("has_more"))
    page_count = len(projects)
    lines = [
        f"Document category: {matched}",
        f"Total matching projects: {total}",
        f"Showing items {offset + 1}-{offset + page_count} of {total}"
        if projects
        else f"Showing items 0-0 of {total}",
        f"Projects on this page: {page_count} (the answer MUST include all {page_count} items)",
        "Answer format reminder: each item must be only `Title (Year) — Advisor` (details are in Sources).",
        "Projects:",
    ]
    if not projects:
        lines.append("- (none on this page)")
    for idx, item in enumerate(projects, start=offset + 1):
        cats = ", ".join(item.get("categories") or []) or "-"
        # Compact primary line for the LLM answer; keep full metadata on the next line for Sources-quality grounding
        lines.append(
            f"{idx}. {item.get('title') or '-'} "
            f"({item.get('year') if item.get('year') is not None else '-'}) — "
            f"{item.get('advisor') or '-'}"
        )
        lines.append(
            f"   meta: Authors: {item.get('authors') or '-'}; "
            f"Keywords: {item.get('keywords') or '-'}; "
            f"Categories: {cats}; "
            f"Filename: {item.get('filename') or '-'}"
        )
    if has_more:
        lines.append(
            f"More projects remain after this page (next offset={offset + len(projects)}). "
            "Tell the user they can ask for the next page."
        )
    else:
        lines.append("This is the last page of results.")
    return "\n".join(lines)


def looks_like_category_list_follow_up(raw_query: str) -> bool:
    """Heuristic for 'next page' / 'show more' after a category list turn."""
    if not raw_query or not raw_query.strip():
        return False
    q = raw_query.lower().strip()
    # Avoid bare substrings like "ต่อ" matching "ต่อยอด" (recommendation)
    phrase_cues = (
        "next page",
        "show more",
        "more please",
        "more projects",
        "หน้าถัดไป",
        "ขอเพิ่ม",
        "เพิ่มเติม",
        "ดูต่อ",
        "อีกหน่อย",
        "อีกหน้า",
        "หน้าต่อไป",
    )
    if any(cue in q for cue in phrase_cues):
        return True
    return bool(re.fullmatch(r"(more|next|เพิ่ม|ต่อ)\??", q))


def _catalog_citations(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    for item in catalog.get("projects") or []:
        categories = item.get("categories") or []
        citations.append(
            {
                "project_title": item.get("title"),
                "source": item.get("filename") or "catalog",
                "pages": [],
                "pages_formatted": "",
                "author": item.get("authors"),
                "advisor": item.get("advisor"),
                "committee": item.get("supervisory_committee"),
                "year": item.get("year"),
                "school": None,
                "program": None,
                "summary": None,
                "project_type": categories,
                "key_technologies": None,
                "target_problem": None,
                "keywords": item.get("keywords"),
                "categories": categories,
                "document_id": item.get("document_id"),
            }
        )
    return citations


def category_list_session_state(
    *,
    catalog: dict[str, Any],
    filters: dict[str, Any],
    normalized_query: str,
) -> dict[str, Any]:
    """Build session payload for follow-up 'show more' turns."""
    page_len = len(catalog.get("projects") or [])
    offset = int(catalog.get("offset") or 0)
    next_offset = offset + page_len
    kept_filters = {
        key: filters[key]
        for key in ("category", "year", "advisor", "author")
        if key in filters and filters[key] not in (None, "", [])
    }
    matched = catalog.get("matched_category")
    if matched and "category" not in kept_filters:
        kept_filters["category"] = matched
    return {
        "category": matched or kept_filters.get("category"),
        "filters": kept_filters,
        "next_offset": next_offset,
        "total": int(catalog.get("total") or 0),
        "has_more": bool(catalog.get("has_more")),
        "normalized_query": normalized_query,
    }


def remember_category_list_result(
    session_id: Optional[str],
    retrieval_details: dict[str, Any],
) -> None:
    """Persist / clear last_category_list on the shared session_manager instance."""
    from .session_manager import session_manager

    if not session_id or not retrieval_details.get("catalog_mode"):
        return
    catalog = retrieval_details.get("catalog") or {}
    if not catalog.get("matched_category"):
        # Suggestions-only: keep prior state if any; do not advance offset
        return
    state = category_list_session_state(
        catalog=catalog,
        filters=retrieval_details.get("filters") or {},
        normalized_query=retrieval_details.get("normalized_query") or "",
    )
    session_manager.set_last_category_list(session_id, state)


def build_category_list_retrieval(
    *,
    normalized_query: str,
    filters: dict[str, Any],
    query_proc_seconds: float = 0.0,
    offset: int = 0,
    limit: int = CATEGORY_LIST_PAGE_SIZE,
    db: Session | None = None,
    total_start: float | None = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Build a search_with_details-compatible payload from Postgres catalog data.
    Skips Qdrant / hybrid / rerank entirely.
    """
    import time

    owns_session = db is None
    if owns_session:
        from app.core.database import SessionLocal

        db = SessionLocal()

    started = time.perf_counter() if total_start is None else total_start
    try:
        catalog_start = time.perf_counter()
        catalog = list_projects_from_filters(db, filters, offset=offset, limit=limit)
        catalog_seconds = time.perf_counter() - catalog_start
        context = format_catalog_context(catalog)
        citations = _catalog_citations(catalog)
        sources = [
            item.get("filename") or f"document:{item.get('document_id')}"
            for item in (catalog.get("projects") or [])
        ]
        label = catalog.get("matched_category") or "category suggestions"
        results = [
            {
                "id": "category-catalog",
                "score": 1.0,
                "text": context,
                "payload": {
                    "source": "postgres_catalog",
                    "project_title": f"Category catalog: {label}",
                    "page_number": None,
                    "categories": [catalog["matched_category"]]
                    if catalog.get("matched_category")
                    else catalog.get("suggested_categories") or [],
                },
            }
        ]
        total_seconds = time.perf_counter() - started
        print(
            f"\n📦 [CATEGORY_LIST] Postgres catalog: "
            f"matched={catalog.get('matched_category')!r} "
            f"total={catalog.get('total')} page={len(catalog.get('projects') or [])} "
            f"offset={catalog.get('offset')} "
            f"in {catalog_seconds:.3f}s (vector retrieval skipped)"
        )
        payload = {
            "results": results,
            "errors": [],
            "timing": {
                "query_proc_seconds": query_proc_seconds,
                "retrieval_seconds": catalog_seconds,
                "rerank_seconds": 0.0,
                "total_seconds": total_seconds,
            },
            "normalized_query": normalized_query,
            "filters": filters,
            "intent": "CATEGORY_LIST",
            "query_variants": [],
            "retrieved_count": len(catalog.get("projects") or []),
            "fast_path_used": True,
            "catalog_mode": True,
            "catalog": catalog,
            "catalog_context": context,
            "catalog_citations": citations,
            "catalog_sources": sources,
        }
        remember_category_list_result(session_id, payload)
        return payload
    finally:
        if owns_session and db is not None:
            db.close()
