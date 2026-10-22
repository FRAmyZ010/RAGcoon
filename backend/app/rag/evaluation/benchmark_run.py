"""Run a short preset-versus-preset benchmark for the admin page."""

import json
import time
from pathlib import Path

GOLDEN_PATH = Path(__file__).with_name("golden_dataset.json")
HANDOFF_QUERIES = [
    "อาจารสุรพลดูแลเรื่องไรบ้าง",
    "โครงงานที่ใช้โมดูล SX1276 มีอะไรบ้าง",
    "ขั้นตอนการทำงานและการทดลองของ The LoRaWAN",
    "ใครเป็นที่ปรึกษาของ The LoRaWAN",
    "The LoRaWAN เป็นระบบประเภทไหน",
    "โครงงาน The LoRaWAN มีการเชื่อมต่อกับ Line Notify หรือไม่",
]


def load_handoff_cases(limit: int = 2) -> list[dict]:
    """Golden cases whose question is in the handoff sheet, capped for an HTTP request."""
    cases = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    wanted = set(HANDOFF_QUERIES)
    picked = [case for case in cases if case.get("query") in wanted]
    return picked[: max(1, limit)]


def _hit(sources: list[str], expected: list[str]) -> bool:
    found = {str(source).lower() for source in sources if source}
    return any(any(item.lower() in source or source in item.lower() for source in found) for item in expected)


def _run_case(case: dict, config) -> dict:
    from app.rag.retrieval.prompt import answer_question

    started = time.perf_counter()
    result = answer_question(
        case["query"],
        config=config,
        llm_provider=config.llm_provider,
        llm_model=config.llm_model,
    )
    elapsed = round(time.perf_counter() - started, 3)
    sources = list(result.get("sources") or [])
    return {
        "score": 100.0 if _hit(sources, case.get("expected_sources") or []) else 0.0,
        "seconds": elapsed,
    }


def run_preset_benchmark(baseline: str, candidate: str, limit: int = 2) -> dict:
    from app.rag.retrieval.rag_config import get_config_preset

    baseline_cfg = get_config_preset(baseline)
    candidate_cfg = get_config_preset(candidate)
    cases = load_handoff_cases(limit)
    details = []
    for case in cases:
        base = _run_case(case, baseline_cfg)
        other = _run_case(case, candidate_cfg)
        speedup = round(base["seconds"] / other["seconds"], 2) if other["seconds"] else 1.0
        details.append({
            "id": case.get("id"),
            "query": case["query"],
            "baseline_score": base["score"],
            "candidate_score": other["score"],
            "baseline_seconds": base["seconds"],
            "candidate_seconds": other["seconds"],
            "speedup": speedup,
        })
    count = len(details) or 1
    base_score = sum(item["baseline_score"] for item in details) / count
    other_score = sum(item["candidate_score"] for item in details) / count
    base_time = sum(item["baseline_seconds"] for item in details) / count
    other_time = sum(item["candidate_seconds"] for item in details) / count
    return {
        "status": "success",
        "summary": {
            "delta_score": round(other_score - base_score, 1),
            "speedup": round(base_time / other_time, 2) if other_time else 1.0,
            "baseline_score": round(base_score, 1),
            "candidate_score": round(other_score, 1),
            "cases": len(details),
        },
        "details": details,
    }
