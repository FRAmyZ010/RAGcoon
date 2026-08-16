import os
import re
import time

import requests
from dotenv import load_dotenv

from .service import search, search_with_details

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
NO_ANSWER_TEXT = "No relevant information found in the documents."


def _is_advisor_query(question: str) -> bool:
    q = question.lower()
    return any(
        phrase in q
        for phrase in (
            "advisor",
            "advisors",
            "supervisory committee",
            "committee",
            "serve on the committee",
            "serve on committee",
            "serve on the supervisory",
            "supervisor",
            "supervise",
        )
    )


def _build_metadata_answer(scored_contexts: list[dict], question: str) -> str | None:
    if not scored_contexts or not _is_advisor_query(question):
        return None

    unique_titles: list[str] = []
    seen_titles: set[str] = set()
    unique_advisors: list[str] = []
    seen_advisors: set[str] = set()

    for item in scored_contexts:
        payload = item.get("payload", {}) or {}
        title = payload.get("project_title") or payload.get("title")
        advisor = payload.get("advisor")

        if title:
            normalized_title = str(title).strip()
            if normalized_title.lower() not in seen_titles:
                seen_titles.add(normalized_title.lower())
                unique_titles.append(normalized_title)

        if advisor:
            normalized_advisor = str(advisor).strip()
            if normalized_advisor.lower() not in seen_advisors:
                seen_advisors.add(normalized_advisor.lower())
                unique_advisors.append(normalized_advisor)

    if not unique_titles:
        return None

    project_list = ", ".join(unique_titles[:5])
    advisor_text = unique_advisors[0] if unique_advisors else "the advisor"

    if len(unique_titles) == 1:
        return f"{advisor_text} is associated with this project: {unique_titles[0]}."

    return f"{advisor_text} is associated with these projects: {project_list}."


def retrieve_context(question: str) -> list[str]:
    return search(question)


def clean_answer(answer: str) -> str:
    if not answer:
        return NO_ANSWER_TEXT

    cleaned = answer.strip()
    lower_cleaned = cleaned.lower().strip()

    if lower_cleaned.startswith("answer:"):
        cleaned = cleaned[len("answer:"):].strip()
        lower_cleaned = cleaned.lower().strip()

    # อันนี้เป็นการทำความสะอาดเพิ่มเติมเพื่อจัดการกับคำตอบที่อาจมีรูปแบบไม่ปกติ เช่น การมีคำว่า "I don't know" หรือ "unknown" ที่อาจบ่งบอกว่าไม่มีข้อมูลที่เกี่ยวข้องในเอกสาร
    normalized = re.sub(r"[\s\.\!\?]+", " ", lower_cleaned).strip()
    unknown_prefixes = (
        "i don't know",
        "i dont know",
        "i do not know",
        "unknown",
        "not found",
        "cannot determine",
        "cannot be determined",
        "no relevant information found",
    )

    if any(normalized.startswith(prefix) for prefix in unknown_prefixes):
        return NO_ANSWER_TEXT

    return cleaned or NO_ANSWER_TEXT


def get_llm_response(question: str, context_list: list[str]) -> str:
    if not context_list:
        return NO_ANSWER_TEXT
    
    print(f"\n📝 LLM Input - {len(context_list)} chunks:")
    for i, ctx in enumerate(context_list, 1):
        preview = ctx.replace("\n", " ")[:80]
        print(f"  [{i}] {preview}...")
    
    # สร้าง prompt โดยรวม context ทั้งหมดเข้าด้วยกัน
    
    context_text = "\n\n".join(context_list)
    prompt = f"""You are an assistant for a senior project document repository.
Use only the retrieved context below. Do not invent facts.
If the question asks about advisor, supervisory committee, or staff involvement, look for:
  - Full advisor names (e.g., "Dr. Mahamah Sebakor", "Aj. Surapol Vorapatratorn")
  - Project titles that match the advisor's projects
  - Supervisory committee information
If the question asks about methodology, you may summarize the methodology from the retrieved context when it mentions development process, implementation steps, workflow, objectives, system design, or technologies used.
If the context is still insufficient, reply exactly: I don't know.
Keep the answer concise and directly relevant to the question.

Context:
{context_text}

Question:
{question}

Answer:
"""

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=60,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return f"LLM request failed: {exc}"

    raw_answer = response.json().get("response", "")
    return clean_answer(raw_answer)


def answer_question(question: str) -> dict[str, object]:
    retrieval_details = search_with_details(question)
    scored_contexts = retrieval_details["results"]

    metadata_answer = _build_metadata_answer(scored_contexts, question)
    if metadata_answer:
        return {
            "question": question,
            "answer": metadata_answer,
            "contexts": [item["text"] for item in scored_contexts],
            "sources": [item.get("payload", {}).get("source", "Unknown source") for item in scored_contexts],
            "scored_contexts": scored_contexts,
            "normalized_query": retrieval_details["normalized_query"],
            "query_variants": retrieval_details["query_variants"],
            "retrieved_count": retrieval_details["retrieved_count"],
            "errors": retrieval_details["errors"],
            "timing": {
                "retrieval_seconds": retrieval_details["timing"]["retrieval_seconds"],
                "rerank_seconds": retrieval_details["timing"]["rerank_seconds"],
                "llm_seconds": 0.0,
                "total_seconds": retrieval_details["timing"]["total_seconds"],
            },
        }

    contexts: list[str] = []
    seen_projects: set[str] = set()
    sources: list[str] = []

    for item in scored_contexts:
        payload = item.get("payload", {})
        source = payload.get("source", "Unknown source")
        project_title = payload.get("project_title") or payload.get("title")
        advisor = payload.get("advisor")

        if project_title:
            key = project_title.lower().strip()
            if key in seen_projects:
                continue
            seen_projects.add(key)

        snippet = item["text"].replace("\n", " ").strip()
        context_parts = []
        if project_title:
            context_parts.append(f"Project title: {project_title}")
        if advisor:
            context_parts.append(f"Advisor: {advisor}")
        if source:
            context_parts.append(f"Source: {source}")
        if context_parts:
            contexts.append(" | ".join(context_parts) + "\n" + snippet)
        else:
            contexts.append(snippet)
        sources.append(source)

    retrieval_errors = retrieval_details["errors"]

    if not contexts and retrieval_errors:
        retrieval_timing = retrieval_details["timing"]
        return {
            "question": question,
            "answer": "Retrieval failed: unable to fetch documents from Qdrant right now.",
            "contexts": [],
            "sources": [],
            "scored_contexts": [],
            "normalized_query": retrieval_details["normalized_query"],
            "query_variants": retrieval_details["query_variants"],
            "retrieved_count": retrieval_details["retrieved_count"],
            "errors": retrieval_errors,
            "timing": {
                "retrieval_seconds": retrieval_timing["retrieval_seconds"],
                "rerank_seconds": retrieval_timing["rerank_seconds"],
                "llm_seconds": 0.0,
                "total_seconds": retrieval_timing["total_seconds"],
            },
        }

    llm_start = time.perf_counter()
    answer = get_llm_response(question, contexts)
    llm_seconds = time.perf_counter() - llm_start

    retrieval_timing = retrieval_details["timing"]
    total_seconds = retrieval_timing["total_seconds"] + llm_seconds

    return {
        "question": question,
        "answer": answer,
        "contexts": contexts,
        "sources": sources,
        "scored_contexts": scored_contexts,
        "normalized_query": retrieval_details["normalized_query"],
        "query_variants": retrieval_details["query_variants"],
        "retrieved_count": retrieval_details["retrieved_count"],
        "errors": retrieval_errors,
        "timing": {
            "retrieval_seconds": retrieval_timing["retrieval_seconds"],
            "rerank_seconds": retrieval_timing["rerank_seconds"],
            "llm_seconds": llm_seconds,
            "total_seconds": total_seconds,
        },
    }
