"""Run a short preset-versus-preset benchmark for the admin page."""

import logging
import time

logger = logging.getLogger(__name__)
ANSWER_CLIP = 800

SPEC_CASES = [
    {
        "id": "SQ-01",
        "query": "What are the SRAM and Flash memory sizes of the Arduino Mega 2560 in the Intelligent Watering System?",
        "expected_sources": ["Final document(8).pdf"],
    },
    {
        "id": "SQ-02",
        "query": "Which GPIO pins connect the RFID-RC522 reader to the NodeMCU ESP8266 in Online Vehicle Access Monitoring?",
        "expected_sources": ["13_Online-Vehicle-access-management-system-proposol3_compressed.pdf"],
    },
    {
        "id": "SQ-03",
        "query": "What are the average recall and accuracy scores achieved by the 13-feature Logistic Regression model for dormitory price prediction?",
        "expected_sources": [],
    },
    {
        "id": "SQ-04",
        "query": "How does the 5.0 GHz shutoff mechanism work in MFU Access Points Energy Saving?",
        "expected_sources": [],
    },
    {
        "id": "SQ-05",
        "query": "Compare Gem Car Tracking Application and Tracking and Locating System on Website on data transmission and alert methods.",
        "expected_sources": ["15_Pre-Project_Gem_Car2_edit2_V2.pdf"],
    },
    {
        "id": "SQ-06",
        "query": "Which project in the archive is recommended for building an automated precision NPK fertilizer and water dispensing system?",
        "expected_sources": ["Final document(8).pdf"],
    },
    {
        "id": "SQ-07",
        "query": "Which projects in the archive were advised by Dr. Mahamah Sebakor?",
        "expected_sources": [],
    },
    {
        "id": "SQ-08",
        "query": "What is the Netmiko Python code used to shut down the 5GHz interface on the Cisco WLC?",
        "expected_sources": [],
    },
]


def load_handoff_cases(limit: int | None = None) -> list[dict]:
    """English spec questions shown on the Benchmark tab. No limit runs every question."""
    if limit is None:
        return list(SPEC_CASES)
    return list(SPEC_CASES[: max(1, limit)])


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


def _average_runs(case: dict, config, repeats: int) -> dict:
    runs = [_run_case(case, config) for _ in range(repeats)]
    count = len(runs) or 1
    return {
        "score": round(sum(item["score"] for item in runs) / count, 1),
        "seconds": round(sum(item["seconds"] for item in runs) / count, 3),
        "answer": runs[-1]["answer"],
        "sources": runs[-1]["sources"],
    }


def _config_for_name(name: str):
    """Load a Presets-page profile: a built-in RAG preset, or a saved intent bundle."""
    from app.rag.retrieval.rag_config import RAGConfig, get_config_by_name

    try:
        return get_config_by_name(name)
    except KeyError:
        pass
    from app.core.database import SessionLocal
    from app.services.ai_config_service import load_named_presets

    db = SessionLocal()
    try:
        bundle = load_named_presets(db).get(name)
    finally:
        db.close()
    if not isinstance(bundle, dict):
        raise KeyError(f"Configuration profile '{name}' not found.")
    intents = bundle.get("intents") or {}
    preview_name = bundle.get("preview_intent") or next(iter(intents), "")
    preview = intents.get(preview_name) if isinstance(intents.get(preview_name), dict) else {}
    base = get_config_by_name("winner_rank1_llama3_2_3b").to_dict()
    for key, value in preview.items():
        if key in base and value is not None:
            base[key] = value
    base["profile_name"] = name
    if bundle.get("llm_provider"):
        base["llm_provider"] = bundle["llm_provider"]
    if bundle.get("llm_model"):
        base["llm_model"] = bundle["llm_model"]
    return RAGConfig.from_dict(base)


def run_preset_benchmark(baseline: str, candidate: str, limit: int | None = None, repeats: int = 5) -> dict:
    repeats = min(max(int(repeats or 5), 1), 5)
    baseline_cfg = _config_for_name(baseline)
    candidate_cfg = _config_for_name(candidate)
    cases = load_handoff_cases(limit)
    details = []
    for case in cases:
        base = _average_runs(case, baseline_cfg, repeats)
        other = _average_runs(case, candidate_cfg, repeats)
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
            "baseline_answer": row["baseline_answer"],
            "candidate_answer": row["candidate_answer"],
            "baseline_sources": row["baseline_sources"],
            "candidate_sources": row["candidate_sources"],
        }
        for row in details
    ],
        "repeats": repeats,
        "llm_summary": summarize_benchmark(baseline, candidate, details),
    }


def rank_answer_quality(preset_names: list[str] | None = None, limit: int | None = None, repeats: int = 5) -> dict:
    """Rank presets by how often the answer cites the expected document, then by time."""
    names = preset_names or [
        "winner_rank1_llama3_2_3b",
        "winner_rank2_qwen2_5_3b",
        "winner_rank3_gemma3_4b_academic",
    ]
    repeats = min(max(int(repeats or 5), 1), 5)
    cases = load_handoff_cases(limit)
    ranked = []
    for name in names:
        config = _config_for_name(name)
        rows = [_average_runs(case, config, repeats) for case in cases]
        count = len(rows) or 1
        ranked.append({
            "profile_name": name,
            "llm_model": config.llm_model,
            "score": round(sum(row["score"] for row in rows) / count, 1),
            "seconds": round(sum(row["seconds"] for row in rows) / count, 3),
            "top_k": config.top_k,
            "rerank_top_n": config.rerank_top_n,
            "max_context_chunks": config.max_context_chunks,
            "prompt_preset": config.prompt_preset,
            "questions": [
                {"query": case["query"], "score": row["score"], "seconds": row["seconds"], "answer": row["answer"]}
                for case, row in zip(cases, rows)
            ],
        })
    ranked.sort(key=lambda item: (-item["score"], item["seconds"]))
    return {"status": "success", "repeats": repeats, "ranked_by": "answer_hit_then_time", "presets": ranked}
