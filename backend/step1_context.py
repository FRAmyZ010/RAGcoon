import os
import re

import requests
from dotenv import load_dotenv

from retrieval import search

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


def answer_question(question: str) -> tuple[list[str], str]:
    contexts = retrieve_context(question)
    answer = get_llm_response(question, contexts)
    return contexts, answer
