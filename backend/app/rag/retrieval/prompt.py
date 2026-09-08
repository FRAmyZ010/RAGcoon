import os
import re
import time

import requests
from dotenv import load_dotenv

from .service import search, search_with_details

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
NO_ANSWER_TEXT_EN = "No relevant information found in the documents."
NO_ANSWER_TEXT_TH = "ไม่พบข้อมูลที่เกี่ยวข้องในเอกสาร"
NO_ANSWER_TEXT = NO_ANSWER_TEXT_EN


def _is_thai_query(text: str) -> bool:
    """Check if the text contains Thai characters."""
    return any("\u0e00" <= char <= "\u0e7f" for char in text)


def _is_code_query(question: str) -> bool:
    q = question.lower()
    return any(
        marker in q
        for marker in (
            "code",
            "source code",
            ".php",
            ".py",
            ".js",
            ".java",
            "function",
            "query",
            "sql",
            "โค้ด",
            "คำสั่ง",
            "ฟังก์ชัน",
            "ซอร์สโค้ด",
        )
    )


def _build_code_fallback(scored_contexts: list[dict], is_thai: bool = False) -> str:
    fragments: list[str] = []
    for index, item in enumerate(scored_contexts, start=1):
        payload = item.get("payload", {}) or {}
        source = payload.get("source", "Unknown source")
        page_number = payload.get("page_number", "?")
        text = str(item.get("text", "")).strip()
        if text:
            fragments.append(
                f"[Fragment {index} | {source} | page {page_number}]\n{text}"
            )

    if not fragments:
        return NO_ANSWER_TEXT_TH if is_thai else NO_ANSWER_TEXT_EN
    header = "ชิ้นส่วนโค้ดที่ค้นพบ:\n\n" if is_thai else "Retrieved code fragments:\n\n"
    return header + "\n\n".join(fragments)


def retrieve_context(question: str) -> list[str]:
    return search(question)


def clean_answer(answer: str, is_thai: bool = False) -> str:
    fallback_text = NO_ANSWER_TEXT_TH if is_thai else NO_ANSWER_TEXT_EN

    if not answer:
        return fallback_text

    cleaned = answer.strip()
    lower_cleaned = cleaned.lower().strip()

    if lower_cleaned.startswith("answer:"):
        cleaned = cleaned[len("answer:"):].strip()
        lower_cleaned = cleaned.lower().strip()

    if lower_cleaned.startswith("คำตอบ:"):
        cleaned = cleaned[len("คำตอบ:"):].strip()
        lower_cleaned = cleaned.lower().strip()

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
        "ไม่พบข้อมูล",
        "ไม่ทราบ",
        "ไม่มีข้อมูล",
        "ไม่สามารถระบุได้",
    )

    if any(normalized.startswith(prefix) for prefix in unknown_prefixes):
        return fallback_text

    return cleaned or fallback_text


def get_llm_response(question: str, context_list: list[str]) -> str:
    is_thai = _is_thai_query(question)
    fallback_text = NO_ANSWER_TEXT_TH if is_thai else NO_ANSWER_TEXT_EN

    if not context_list:
        return fallback_text
    
    context_text = "\n\n".join(context_list)
    lang_instruction = (
        "Please respond in Thai language directly and concisely."
        if is_thai
        else "Please respond in English directly and concisely."
    )
    insufficient_reply = "ไม่พบข้อมูลที่เกี่ยวข้องในเอกสาร" if is_thai else "I don't know."

    prompt = f"""You are an assistant for a senior project document repository.
Use only the retrieved context below. Do not invent facts.

Instructions:
1. Check both the metadata headers (Project title, Author, Advisor, Committee, Year, Keywords, Source) and the document content thoroughly.
2. If the question asks for tools, frameworks, hardware, sensors, technologies, libraries, software, operating systems, or methodologies, extract and summarize all relevant items mentioned in the context (including under sections like Related Technology, System Overview, or Methodology).
3. If the context mentions specific technologies or tools used (for example, VMware Workstation, Ubuntu, Arduino, Python, etc.), state them clearly and explain how they are used based on the context.
4. If the question asks for source code or a named file, extract and reproduce the matching code from the context.
5. If the question asks "Which projects..." or "Which project reports have [advisor/author]...", always explicitly enumerate and list the exact distinct project titles found in the context (for example: "1. [Project Title A]\n2. [Project Title B]"). Never give vague or generic responses like "All project reports".
6. If the question asks about advisor, author, committee, or year, provide the accurate answer directly from the metadata or context.
7. {lang_instruction}
8. Only if the context contains absolutely no relevant information, reply exactly: {insufficient_reply}
9. Keep the answer concise and directly relevant to the question.

Context:
{context_text}

Question:
{question}

Answer:
"""

    ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT", "180"))
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "15m",
                "options": {
                    "temperature": 0,
                    "num_predict": 512,
                },
            },
            timeout=ollama_timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return f"LLM request failed: {exc}"

    raw_answer = response.json().get("response", "")
    return clean_answer(raw_answer, is_thai=is_thai)


def answer_question(question: str) -> dict[str, object]:
    is_thai = _is_thai_query(question)
    fallback_text = NO_ANSWER_TEXT_TH if is_thai else NO_ANSWER_TEXT_EN

    retrieval_details = search_with_details(question)
    scored_contexts = retrieval_details["results"]

    contexts: list[str] = []
    seen_texts: set[str] = set()
    project_chunk_counts: dict[str, int] = {}
    
    # Check if multiple distinct projects are present in the retrieved candidates
    distinct_projects = set(
        item.get("payload", {}).get("project_title") or item.get("payload", {}).get("title")
        for item in scored_contexts
        if item.get("payload") and (item.get("payload", {}).get("project_title") or item.get("payload", {}).get("title"))
    )
    max_chunks_per_project = 2 if len(distinct_projects) > 1 else 7
    preserve_same_project_chunks = _is_code_query(question)
    sources: list[str] = []

    for item in scored_contexts:
        payload = item.get("payload", {}) or {}
        source = payload.get("source", "Unknown source")
        project_title = payload.get("project_title") or payload.get("title")
        author = payload.get("author")
        advisor = payload.get("advisor")
        committee = payload.get("committee")
        year = payload.get("year")
        keywords = payload.get("keywords")
        page_number = payload.get("page_number", "?")

        # Allow multiple chunks per project without dropping them all, while avoiding exact duplicate texts
        if project_title and not preserve_same_project_chunks:
            key = project_title.lower().strip()
            count = project_chunk_counts.get(key, 0)
            if count >= max_chunks_per_project:
                continue
            project_chunk_counts[key] = count + 1

        raw_snippet = str(item.get("text", "")).strip()
        raw_snippet = raw_snippet.replace("\r\n", "\n").replace("\r", "\n")
        if not raw_snippet:
            continue

        if not preserve_same_project_chunks:
            snippet = " ".join(raw_snippet.split())
        else:
            snippet = raw_snippet

        if snippet in seen_texts:
            continue
        seen_texts.add(snippet)

        context_parts = []
        if project_title:
            context_parts.append(f"Project title: {project_title}")
        if author:
            context_parts.append(f"Author: {author}")
        if advisor:
            context_parts.append(f"Advisor: {advisor}")
        if committee:
            context_parts.append(f"Committee: {committee}")
        if year:
            context_parts.append(f"Year: {year}")
        if keywords:
            context_parts.append(f"Keywords: {keywords}")
        if source:
            context_parts.append(f"Source: {source} (Page {page_number})")

        if context_parts:
            contexts.append(" | ".join(context_parts) + "\n" + snippet)
        else:
            contexts.append(snippet)

        if source not in sources:
            sources.append(source)

    retrieval_errors = retrieval_details["errors"]

    if not contexts and retrieval_errors:
        retrieval_timing = retrieval_details["timing"]
        error_msg = "การดึงข้อมูลล้มเหลว: ไม่สามารถเชื่อมต่อกับ Qdrant ได้" if is_thai else "Retrieval failed: unable to fetch documents from Qdrant right now."
        return {
            "question": question,
            "answer": error_msg,
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

    if _is_code_query(question) and answer == fallback_text:
        answer = _build_code_fallback(scored_contexts, is_thai=is_thai)

    retrieval_timing = retrieval_details["timing"]
    total_seconds = retrieval_timing["total_seconds"] + llm_seconds

    return {
        "question": question,
        "answer": answer,
        "contexts": contexts,
        "sources": sources,
        "scored_contexts": scored_contexts,
        "normalized_query": retrieval_details["normalized_query"],
        "filters": retrieval_details.get("filters", {}),
        "query_variants": retrieval_details["query_variants"],
        "retrieved_count": retrieval_details["retrieved_count"],
        "errors": retrieval_errors,
        "timing": {
            "query_proc_seconds": retrieval_timing.get("query_proc_seconds", 0.0),
            "retrieval_seconds": retrieval_timing["retrieval_seconds"],
            "rerank_seconds": retrieval_timing["rerank_seconds"],
            "llm_seconds": llm_seconds,
            "total_seconds": total_seconds,
        },
    }
