"""
Pure Python Multi-turn Context Test
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.rag.retrieval.prompt import answer_question
from app.rag.retrieval.session_manager import session_manager


def test_multiturn_pure_python():
    sid = "multi-turn-pure-demo"
    session_manager.clear_session(sid)

    print("\n🤖 Running Multi-turn AI Engine Test (Pure Python)...")

    # Turn 1
    q1 = "โปรเจกต์ PetFeeder ทำเกี่ยวกับอะไร?"
    res1 = answer_question(q1, session_id=sid)
    print(f"👤 Turn 1 User: {q1}")
    print(f"🤖 Turn 1 AI Answer: {res1.get('answer')[:100]}...")

    # Turn 2
    q2 = "แล้วใครเป็นอาจารย์ที่ปรึกษาของโปรเจกต์นี้?"
    res2 = answer_question(q2, session_id=sid)
    print(f"👤 Turn 2 User: {q2}")
    print(f"🤖 Turn 2 AI Answer: {res2.get('answer')}")

    history = session_manager.get_history(sid)
    assert len(history) == 4
    print("✅ In-Memory Session history preserved 4 messages correctly!")


if __name__ == "__main__":
    test_multiturn_pure_python()
