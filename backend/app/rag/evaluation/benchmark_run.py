"""Run a short preset-versus-preset benchmark for the admin page."""

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)
ANSWER_CLIP = 800

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


def _clip(text: str, limit: int = ANSWER_CLIP) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."


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
        "answer": _clip(result.get("answer") or ""),
        "sources": [str(source) for source in sources if source],
    }


def build_benchmark_summary_prompt(baseline: str, candidate: str, rows: list[dict]) -> str:
    """English prompt that asks the active model to compare both preset answers."""
    blocks = []
    for row in rows:
        blocks.append(
            "\n".join([
                f"Question: {row['query']}",
                f"Baseline score {row['baseline_score']} in {row['baseline_seconds']}s. Sources: {row['baseline_sources'] or 'none'}.",
                f"Baseline answer: {row['baseline_answer']}",
                f"Candidate score {row['candidate_score']} in {row['candidate_seconds']}s. Sources: {row['candidate_sources'] or 'none'}.",
                f"Candidate answer: {row['candidate_answer']}",
                f"Speedup: {row['speedup']}x",
            ])
        )
    return (
        "You compare two RAG presets that answered the same questions.\n"
        f"Baseline preset: {baseline}\n"
        f"Candidate preset: {candidate}\n\n"
        + "\n\n".join(blocks)
        + "\n\nWrite a short English summary in exactly three bullets:\n"
        "1. Content: how the answers differ.\n"
        "2. Sources: which documents each side cited.\n"
        "3. Speed: which side was faster, using the times above.\n"
        "Use only the answers, sources, scores, and times above. Do not invent facts."
    )


def summarize_benchmark(baseline: str, candidate: str, rows: list[dict]) -> str:
    """One extra model call. A failed summary still leaves the score table usable."""
    from app.rag.retrieval.llm_provider import get_llm_provider

    fallback = "The score table is ready. The summary model did not respond."
    try:
        text, stats = get_llm_provider().generate(
            build_benchmark_summary_prompt(baseline, candidate, rows),
            system_prompt="You summarize RAG benchmark results in English.",
            num_predict=400,
        )
    except Exception:
        logger.exception("Benchmark summary model failed")
        return fallback
    cleaned = str(text or "").strip()
    if not cleaned or "⚠️" in cleaned or (isinstance(stats, dict) and stats.get("error")):
        return fallback
    return cleaned


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
            "baseline_answer": base["answer"],
            "candidate_answer": other["answer"],
            "baseline_sources": ", ".join(base["sources"]) or "none",
            "candidate_sources": ", ".join(other["sources"]) or "none",
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
        "details": [
            {
                "id": row["id"],
                "query": row["query"],
                "baseline_score": row["baseline_score"],
                "candidate_score": row["candidate_score"],
                "baseline_seconds": row["baseline_seconds"],
                "candidate_seconds": row["candidate_seconds"],
                "speedup": row["speedup"],
            }
            for row in details
        ],
        "llm_summary": summarize_benchmark(baseline, candidate, details),
    }
