import os
import re
import time

import requests
from dotenv import load_dotenv

from retrieval import search, search_with_details

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "tinyllama:latest")
NO_ANSWER_TEXT = "No relevant information found in the documents."


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
    
    # สร้าง prompt โดยรวม context ทั้งหมดเข้าด้วยกัน และให้คำแนะนำกับ LLM ว่าให้ใช้ข้อมูลจาก context เท่านั้นในการตอบคำถาม อันนี้จะช่วยลดโอกาสที่ LLM จะสร้างคำตอบที่ไม่เกี่ยวข้องหรือไม่ถูกต้องจากการเดา
    # อันนี้ปรับปรุง prompt ต่อได้เพื่อให้ LLM เข้าใจว่าถ้าข้อมูลใน context เช่น พวกเป็นข้อๆให้ตอบเป็นข้อๆตามนั้นได้เลย และถ้าข้อมูลใน context มีคำที่เกี่ยวข้องกับ methodology เช่น development process, implementation steps, workflow, objectives, system design, หรือ technologies used ให้สรุปข้อมูลเหล่านั้นมาเป็นคำตอบได้เลย
    # ประมาณนี้แหละ อาจจะต้องปรับปรุงเพิ่มเติมอีกทีหลังจากได้ลองกับข้อมูลจริงๆแล้วดูว่า LLM ตอบยังไงบ้าง จาก ด๋อย
    
    context_text = "\n\n".join(context_list)
    prompt = f"""You are an assistant for a senior project document repository.
Use only the retrieved context below. Do not invent facts.
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
    contexts = [item["text"] for item in scored_contexts]
    sources = [item["payload"]["source"] for item in scored_contexts]
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
