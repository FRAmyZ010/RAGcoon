"""CATEGORY_LIST intent: rule-first detection + category label extraction."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag.retrieval.llm_query_processor import (
    _detect_intent_by_rules,
    extract_category_from_query,
    process_query_with_llm,
)


def test_category_list_rule_detection_positive():
    positives = [
        "Which senior projects are in the IoT category?",
        "list projects in the Network category",
        "โปรเจกต์ในหมวด Web",
        "Show all projects in the Machine learning category",
    ]
    for q in positives:
        assert _detect_intent_by_rules(q) == "CATEGORY_LIST", q


def test_category_list_rule_detection_negative():
    # Domain / exploratory phrasing without explicit category marker
    negatives = [
        ("มีโปรเจกต์เกี่ยวกับ IoT อะไรบ้าง", "EXPLORATORY"),
        ("Could you recommend some IoT projects?", "RECOMMENDATION"),
        ("Who is the advisor of The LoRaWAN?", "FACTOID"),
    ]
    for q, expected in negatives:
        assert _detect_intent_by_rules(q) == expected, f"{q} -> expected {expected}"


def test_extract_category_from_chip_prompt():
    assert extract_category_from_query(
        "Which senior projects are in the IoT category?"
    ) == "IoT"
    assert extract_category_from_query(
        "list projects in the web category"
    ) == "Web"


def test_process_query_category_list_fast_path():
    norm_q, filters, intent = process_query_with_llm(
        "Which senior projects are in the IoT category?"
    )
    assert intent == "CATEGORY_LIST"
    assert filters.get("category") == "IoT"
    assert "project_title" not in filters
    assert "IoT" in norm_q or "category" in norm_q.lower()
