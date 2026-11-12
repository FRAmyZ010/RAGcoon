"""CATEGORY_LIST answer finalizer: artifact strip + partial-list footer."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag.retrieval.prompt import finalize_category_list_answer


def test_strips_file_separator_and_appends_partial_note():
    catalog = {
        "projects": [{"title": f"P{i}"} for i in range(10)],
    }
    raw = (
        "1. **A** (2020) — beacon tracking\n"
        "2. **B** (2021) — watering robot\n"
        "3. **C** (2022) — flow meter\n"
        "4. **D** (2023) — Mr. Vas"
        "<|file_separator|>"
    )
    out = finalize_category_list_answer(
        raw,
        catalog=catalog,
        is_thai=True,
        num_predict=768,
        eval_count=760,
    )
    assert "<|file_separator|>" not in out
    assert "นี่เป็นเพียงส่วนหนึ่งเท่านั้น" in out
    assert out.count("1. **A**") == 1


def test_complete_list_no_footer():
    catalog = {"projects": [{"title": "A"}, {"title": "B"}]}
    raw = (
        "1. **A** (2020) — indoor beacon tracking.\n"
        "2. **B** (2021) — automatic plant watering."
    )
    out = finalize_category_list_answer(
        raw,
        catalog=catalog,
        is_thai=False,
        num_predict=768,
        eval_count=120,
    )
    assert "only a partial list" not in out
