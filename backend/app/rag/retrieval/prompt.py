import json
import os
import re
import time
from collections.abc import Generator
from typing import Any, Optional

import requests
from dotenv import load_dotenv

from .config import DEFAULT_NUM_CTX, INTENT_CONFIG
from .service import is_boilerplate_text, search, search_with_details
from .session_manager import session_manager

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
NO_ANSWER_TEXT_EN = "No relevant information found in the documents."
NO_ANSWER_TEXT_TH = "ไม่พบข้อมูลที่เกี่ยวข้องในเอกสาร"
NO_ANSWER_TEXT = NO_ANSWER_TEXT_EN

# Persistent HTTP session for connection pooling & low latency
_http_session = requests.Session()


def _get_intent_config(intent: str) -> dict[str, Any]:
    """Retrieve configuration settings for a given intent."""
    normalized = "FACTUAL_LOOKUP" if intent in {"FACTOID", "FACTUAL_LOOKUP"} else intent
    return INTENT_CONFIG.get(normalized, INTENT_CONFIG.get(intent, INTENT_CONFIG["FACTOID"]))


def _clean_name_spacing(name: str | None) -> str | None:
    """Clean missing spaces after dots and in CamelCase/TitleCase words."""
    if not name or not isinstance(name, str):
        return name
    cleaned = name.strip(" .:-()[]")
    cleaned = re.sub(r"\.([A-Za-z])", r". \1", cleaned)
    cleaned = re.sub(r"([a-z])([A-Z])", r"\1 \2", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .:-")
    return cleaned or None


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

    # Strip any <think>...</think> block or lingering think tags
    if "<think>" in cleaned:
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", cleaned, flags=re.DOTALL).strip()
        if "<think>" in cleaned:
            cleaned = cleaned.split("<think>")[0].strip()
    if "</think>" in cleaned:
        cleaned = cleaned.split("</think>")[-1].strip()

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

    # Strip leading reasoning meta-talk or chain-of-thought monologue if LLM started thinking out loud
    cleaned = re.sub(
        r"^(?:I need to|Let me|First, I need|To answer this|Based on the provided context, I will|Looking at the context|The question asks|In order to answer)[\s\S]*?(?=(?:##|\###|\*\*|1\.|\-))",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    # Strip intermediate reasoning scratchpad blocks (e.g. between headers and tables)
    cleaned = re.sub(
        r"(?:^|\n)(?:I need to|Let me analyze|Let me check|First, I'll identify|First, let's identify|Now I'll structure|Let me create)[\s\S]*?(?=(?:\n##|\n###|\n\||\n\*\*|\n1\.))",
        "\n",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    # Strip trailing reasoning meta-talk or duplicate summary tails
    cleaned = re.split(
        r"\n\s*(?:wait,\s*let me|let me check|let me verify|i need to check|i need to analyze|first,\s*i need|to double check|for the scoring matrix|###\s*ข้อสังเกต|###\s*ตรวจสอบ|###\s*notes)",
        cleaned,
        flags=re.IGNORECASE,
    )[0].strip()

    return cleaned or fallback_text


def _build_intent_instruction(intent: str, question: str = "") -> str:
    """Return specialized prompt instructions based on dynamic query intent."""
    q_lower = question.lower()
    if intent == "RECOMMENDATION":
        return """4. Evidence-Based Project Recommendations:
   First determine whether each candidate project has an explicit relationship to the requested domain (classify internally as DIRECT MATCH, PARTIAL MATCH, or INSUFFICIENT EVIDENCE).
   Only DIRECT MATCH and relevant PARTIAL MATCH projects may appear. Do NOT recommend a project merely because it shares generic terms (e.g. application, system, data, online).

   Structure:
   ### Recommended Projects

   #### [Project Title]
   - **Document Evidence**: [Only information explicitly documented in the retrieved context] [Source: <file>, Page <X>]
   - **Why It Fits**: [Concise 1-sentence explanation of relevance to the requested topic]
   - **Possible Extension**: [AI-generated suggestion clearly labeled as an extension, NOT a documented feature of the original project]

   ## Sources
   - [Project Title]: <Filename.pdf>, Pages: <Pages>"""
    elif intent == "EXPLORATORY":
        if any(w in q_lower for w in ["similar", "คล้าย", "เหมือน", "group", "กลุ่ม"]):
            return """4. Theme-Based Similarity Grouping:
   - Group the retrieved projects into clear, logical domain categories.
   - Under each group, list the matching projects concisely:
     * **[Project Title]** ([Year]) - [Core objective in 1 sentence] [Source: <file>, Page <X>].
   ## Sources
   - List each project source filename and pages."""
        else:
            return """4. Enumerated Project Overview: Enumerate distinct projects found in the retrieved context concisely without filler:
   1. **[Project Title]** ([Year]) - [Core objective in 1-2 concise sentences]. (Authors: [Author Names], Advisor: [Advisor Name]) [Source: <file>, Page <X>].
   ## Sources
   - List each project source filename and pages."""
    elif intent in {"DEEP_DIVE", "EXPLANATION"}:
        return """4. Structured DEEP_DIVE Analysis:
   Use this exact structure (describe ONLY documented components and relationships; if information is absent, state 'Not specified in the retrieved document.'):

   ### 📌 Project Overview
   Explain the documented purpose.

   ### 🏗️ System Architecture
   Describe ONLY documented components and relationships. (Never assume Frontend, Backend, REST API, Database, Docker, Cloud unless explicitly documented).

   ### 🔄 Data Flow
   Describe the documented flow. Use a text diagram when evidence supports it:
   Component A
       ↓
   Component B
       ↓
   Component C
   Every arrow must be supported by the document.

   ### 🛠️ Technologies & Hardware
   List ONLY explicitly documented technologies/hardware.

   ### 👤 User Interaction
   Explain documented user actions.

   ### 🔔 External Services / Notifications
   Explain documented external services.

   ### ⚠️ Not Specified
   Clearly identify architecture or technology information that is missing in the document.

   ## Sources
   - [Project Title]: <Filename.pdf>, Pages: <Pages>"""
    elif intent == "COMPARISON":
        return """4. Evidence-Based Structured Comparison:
   ONLY compare documented attributes (Project purpose, Main features, Users, Workflow, Technologies, Hardware, Software, Database, External services, Limitations, Documented results).
   DO NOT invent evaluations (NEVER assign Easy/Medium/Hard, Low/Medium/High, Simple/Complex, Better/Worse).
   If evidence is missing for an attribute, state: 'Not specified in the retrieved document.'

   ## Comparison Overview
   | Dimension | [Project A Title] | [Project B Title] |
   |---|---|---|
   | Purpose & Scope | Documented Purpose [Source: <file>, Page <X>] | Documented Purpose [Source: <file>, Page <X>] |
   | Core Features | Documented Features [Source: <file>, Page <X>] | Documented Features [Source: <file>, Page <X>] |
   | Technologies & Hardware | Documented tech stack ONLY | Documented tech stack ONLY |
   | Database | Documented DB or 'Not specified' | Documented DB or 'Not specified' |

   ## Key Differences
   - Concise bullet points comparing the core systems strictly from document evidence.

   ## Sources
   - [Project A Title]: <Filename.pdf>, Pages: <Pages>
   - [Project B Title]: <Filename.pdf>, Pages: <Pages>"""
    elif intent == "CODE":
        return """4. Code & Technical Implementation Extraction:
   - Only provide code if actual code or SQL exists in the retrieved context.
   - If the context only contains database diagrams, table descriptions, or screenshots without actual SQL, state:
     'The retrieved document contains database/schema information, but does not provide the actual SQL commands.'
   - If nothing relevant exists, state:
     'The retrieved document does not specify the requested code or SQL.'
   ## Sources
   - [Project Title]: <Filename.pdf>, Pages: <Pages>"""
    else:  # FACTOID / FACTUAL_LOOKUP
        return """4. Direct & Evidence-Grounded Answer with Citations:
   - Answer the question directly, flexibly, and accurately based ONLY on explicitly documented evidence in the retrieved context.
   - If asked for hardware, components, technologies, or tools: list all distinct items explicitly mentioned across the retrieved text as bullet points with their respective citations. Do NOT force predetermined template categories (such as microcontroller or sensor placeholders), and do NOT create placeholder bullets for unmentioned items.
   - If a requested item is not found in the document, state clearly that it is not specified (never attach a source citation to unmentioned information).
   - Every factual claim derived from a document must have an exact inline citation [Source: <filename>, Page: <X>]."""


def _calculate_token_breakdown(
    system_text: str,
    history_text: str,
    context_text: str,
    question_text: str,
    total_input_tokens: int,
    output_tokens: int,
) -> dict[str, Any]:
    """Calculate granular token breakdown proportionally mapped to the exact Ollama prompt_eval_count."""
    len_sys = len(system_text.strip())
    len_hist = len(history_text.strip())
    len_ctx = len(context_text.strip())
    len_q = len(question_text.strip())
    total_len = max(1, len_sys + len_hist + len_ctx + len_q)

    if total_input_tokens > 0:
        sys_tokens = int(round((len_sys / total_len) * total_input_tokens))
        hist_tokens = int(round((len_hist / total_len) * total_input_tokens))
        ctx_tokens = int(round((len_ctx / total_len) * total_input_tokens))
        q_tokens = max(1, total_input_tokens - (sys_tokens + hist_tokens + ctx_tokens))
    else:
        sys_tokens = int(len_sys / 3.5)
        hist_tokens = int(len_hist / 3.5)
        ctx_tokens = int(len_ctx / 3.5)
        q_tokens = max(1, int(len_q / 3.5))

    return {
        "system_instruction_tokens": sys_tokens,
        "chat_history_tokens": hist_tokens,
        "document_context_tokens": ctx_tokens,
        "user_question_tokens": q_tokens,
        "total_input_tokens": total_input_tokens or (sys_tokens + hist_tokens + ctx_tokens + q_tokens),
        "output_tokens": output_tokens,
        "context_char_length": len_ctx,
        "history_char_length": len_hist,
    }


def _build_full_prompt(
    question: str,
    context_list: list[str],
    intent: str = "FACTOID",
    chat_history: str = "",
) -> tuple[str, bool, str, int, bool, str, dict[str, str], list[str]]:
    """Construct prompt in ChatML format and return (prompt, is_thai, fallback_text, num_predict, thinking_enabled, prefill, prompt_meta, stop_tokens)."""
    is_thai = _is_thai_query(question)
    fallback_text = NO_ANSWER_TEXT_TH if is_thai else NO_ANSWER_TEXT_EN

    context_text = "\n\n".join(context_list) if context_list else ""
    lang_instruction = (
        "Please respond in Thai language directly and professionally."
        if is_thai
        else "Please respond in English directly and professionally."
    )
    insufficient_reply = "ไม่พบข้อมูลที่เกี่ยวข้องในเอกสาร" if is_thai else "I don't know."
    intent_instruction = _build_intent_instruction(intent, question)

    concise_rule = (
        "ตอบกระชับ ตรงประเด็น เอาแต่เนื้อข้อมูลสำคัญ ห้ามเกริ่นนำ ห้ามร่ายน้ำ และห้ามแสดงขั้นตอนการคิดหรือบ่นในใจเด็ดขาด"
        if is_thai
        else "Be strictly concise, direct, and factual. Give ONLY the essential substance and evidence. ZERO conversational filler, ZERO preamble, and NEVER output internal reasoning, thinking steps, or planning monologue."
    )

    system_content = f"""You are RAGcoon, a document-grounded Senior Project Analysis Agent.
Your primary objective is: MAXIMIZE FACTUAL ACCURACY, EVIDENCE GROUNDING, PROJECT ISOLATION, AND CITATION CORRECTNESS.
You answer questions using ONLY the retrieved document context below. Accuracy > completeness. Evidence > inference.

CORE PRODUCTION RULES:
1. ABSOLUTE SOURCE-GROUNDING: The retrieved context is the ONLY authoritative source. Never invent facts, technologies, databases, code, or endpoints. Never infer tech stacks (Web app ≠ React, Mobile app ≠ Flutter, ER diagram ≠ MySQL, Database ≠ PostgreSQL). If evidence is insufficient, state: 'Not specified in the retrieved document.'
2. CURRENT QUERY & FILTER ISOLATION: Never inherit project, advisor, author, or year filters from previous turns unless explicitly referenced. No explicit constraint in current query = NO FILTER.
3. PROJECT ISOLATION: Every project is an independent evidence scope. Never transfer technologies, hardware, features, authors, or advisors between projects. For comparisons, evaluate each project on its own evidence.
4. INLINE CITATION GROUNDING & EXACT PAGE NUMBERS: Every factual claim must have an inline citation: [Source: <source_file>, Page: <page_number>]. You MUST cite the EXACT page number from the excerpt header where the fact is written. For example, if "NodeMCU ESP8266" is inside an excerpt marked "PAGE: 36", you MUST cite "Page: 36". NEVER cite a title/abstract page (e.g. Page 5) for a technical component that appears on another page. Never fabricate page numbers.
5. CODE, FIGURE & DATABASE RULES: A schema is NOT SQL. Figure title ≠ complete figure content. If actual code/SQL is not present in retrieved context, state: 'The retrieved document contains database/schema information, but does not provide the actual SQL commands.'
6. RECOMMENDATION VS AI EXTENSION: Recommendations search across projects by default. Any model-generated extension must be explicitly labeled: 'AI Suggestion:' and never presented as a documented feature.
7. AGGREGATION & COUNT INTEGRITY: Top-K retrieval results do not prove repository-wide totals. If not exhaustive, state: 'I found X matching projects in the retrieved results, but this does not establish the total number of projects in the repository.'
8. NO INTERNAL REASONING: Zero preamble, zero filler, zero chain-of-thought monologue (never output 'Let me check...', 'I need to...', 'First, I will...'). Start directly with the answer.
9. NO UNSUPPORTED NUMBERS OR RATINGS: Never invent accuracy, performance metrics, percentages, or subjective ratings (never assign Easy/Medium/Hard or Low/High without explicit document proof).
10. GOLDEN RULE: When in doubt, DO NOT guess. When deciding between a useful answer that might be wrong and a limited answer that is definitely supported, ALWAYS choose the limited, evidence-grounded answer.
{intent_instruction}
{lang_instruction}
If the context contains no relevant information, reply exactly: {insufficient_reply}"""

    history_block = (
        f"Recent Conversation History:\n{chat_history.strip()}\n\n"
        if chat_history and chat_history.strip()
        else ""
    )

    user_content = f"""{history_block}Context:
{context_text}

Question:
{question}"""

    intent_cfg = _get_intent_config(intent)
    num_predict = intent_cfg.get("num_predict", 512)
    thinking_enabled = intent_cfg.get("thinking", False)

    think_block = "" if thinking_enabled else "<think>\n</think>\n"
    q_lower = question.lower()
    prefill = ""
    if intent == "COMPARISON":
        prefill = "## Comparison Overview\n| Dimension |"
    elif intent == "RECOMMENDATION":
        prefill = "## Recommended Projects\n\n### 1. "
    elif intent in {"DEEP_DIVE", "EXPLANATION"}:
        prefill = "### 📌 สรุปภาพรวมโครงงาน\n" if is_thai else "### 📌 Project Overview\n"
    elif intent == "EXPLORATORY":
        prefill = "1. **"

    model_name = OLLAMA_MODEL.lower()
    if "gemma" in model_name:
        full_user = f"{system_content}\n\n{user_content}"
        prompt = f"<start_of_turn>user\n{full_user}<end_of_turn>\n<start_of_turn>model\n{prefill}"
        stop_tokens = ["<end_of_turn>", "<start_of_turn>", "<eos>", "<|im_end|>"]
    else:
        prompt = f"<|im_start|>system\n{system_content}<|im_end|>\n<|im_start|>user\n{user_content}<|im_end|>\n<|im_start|>assistant\n{think_block}{prefill}"
        stop_tokens = ["<|im_end|>", "<|im_start|>", "<|endoftext|>", "</think>"]

    prompt_meta = {
        "system_text": system_content,
        "history_text": history_block,
        "context_text": context_text,
        "question_text": question,
    }

    return prompt, is_thai, fallback_text, num_predict, thinking_enabled, prefill, prompt_meta, stop_tokens


def get_llm_response(
    question: str,
    context_list: list[str],
    intent: str = "FACTOID",
    chat_history: str = "",
    stats_out: Optional[dict[str, Any]] = None,
) -> str:
    """Synchronous (non-streaming) LLM call with timing & performance stats extraction."""
    prompt, is_thai, fallback_text, num_predict, thinking_enabled, prefill, prompt_meta, stop_tokens = _build_full_prompt(
        question, context_list, intent=intent, chat_history=chat_history
    )

    if not context_list:
        return fallback_text

    ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT", "180"))
    start_t = time.perf_counter()
    try:
        response = _http_session.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "raw": True,
                "stream": False,
                "think": thinking_enabled,
                "keep_alive": "30m",
                "options": {
                    "temperature": 0.0,
                    "num_predict": num_predict,
                    "num_ctx": DEFAULT_NUM_CTX,
                    "stop": stop_tokens,
                },
            },
            timeout=ollama_timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return f"LLM request failed: {exc}"

    duration = time.perf_counter() - start_t
    data = response.json()
    raw_answer = (prefill + data.get("response", "")) if prefill else data.get("response", "")

    if stats_out is not None:
        p_eval = data.get("prompt_eval_count", 0)
        e_count = data.get("eval_count", 0)
        e_dur_ns = data.get("eval_duration", 0)
        gen_speed = (e_count / (e_dur_ns / 1e9)) if e_dur_ns > 0 else 0.0
        breakdown = _calculate_token_breakdown(
            prompt_meta["system_text"],
            prompt_meta["history_text"],
            prompt_meta["context_text"],
            prompt_meta["question_text"],
            p_eval,
            e_count,
        )
        stats_out.update({
            "prompt_eval_count": p_eval,
            "eval_count": e_count,
            "eval_duration_ns": e_dur_ns,
            "gen_speed_tps": gen_speed,
            "ttft_seconds": duration,
            "llm_seconds": duration,
            "thinking_enabled": thinking_enabled,
            "intent": intent,
            "token_breakdown": breakdown,
        })

    return clean_answer(raw_answer, is_thai=is_thai)


def stream_llm_response(
    question: str,
    context_list: list[str],
    intent: str = "FACTOID",
    chat_history: str = "",
    stats_out: Optional[dict[str, Any]] = None,
) -> Generator[str, None, None]:
    """Streaming LLM generator that yields text tokens in real time from Ollama."""
    prompt, is_thai, fallback_text, num_predict, thinking_enabled, prefill, prompt_meta, stop_tokens = _build_full_prompt(
        question, context_list, intent=intent, chat_history=chat_history
    )

    if not context_list:
        yield fallback_text
        return

    ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT", "180"))
    stream_start = time.perf_counter()
    ttft: Optional[float] = None

    if prefill:
        ttft = time.perf_counter() - stream_start
        yield prefill

    try:
        with _http_session.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "raw": True,
                "stream": True,
                "think": thinking_enabled,
                "keep_alive": "30m",
                "options": {
                    "temperature": 0.0,
                    "num_predict": num_predict,
                    "num_ctx": DEFAULT_NUM_CTX,
                    "stop": stop_tokens,
                },
            },
            stream=True,
            timeout=ollama_timeout,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            if ttft is None:
                                ttft = time.perf_counter() - stream_start
                            yield token
                        if chunk.get("done", False):
                            if stats_out is not None:
                                p_eval = chunk.get("prompt_eval_count", 0)
                                e_count = chunk.get("eval_count", 0)
                                e_dur_ns = chunk.get("eval_duration", 0)
                                gen_speed = (e_count / (e_dur_ns / 1e9)) if e_dur_ns > 0 else 0.0
                                breakdown = _calculate_token_breakdown(
                                    prompt_meta["system_text"],
                                    prompt_meta["history_text"],
                                    prompt_meta["context_text"],
                                    prompt_meta["question_text"],
                                    p_eval,
                                    e_count,
                                )
                                stats_out.update({
                                    "prompt_eval_count": p_eval,
                                    "eval_count": e_count,
                                    "eval_duration_ns": e_dur_ns,
                                    "gen_speed_tps": gen_speed,
                                    "ttft_seconds": ttft or (time.perf_counter() - stream_start),
                                    "thinking_enabled": thinking_enabled,
                                    "intent": intent,
                                    "token_breakdown": breakdown,
                                })
                            break
                    except json.JSONDecodeError:
                        continue
    except requests.RequestException as exc:
        yield f"LLM streaming request failed: {exc}"


def _is_boilerplate_chunk(text: str) -> bool:
    """Use centralized robust boilerplate filter."""
    return is_boilerplate_text(text)


def _prepare_rag_context(
    question: str, session_id: Optional[str] = None
) -> dict[str, Any]:
    """Unified context retrieval and document assembly for both streaming and non-streaming."""
    is_thai = _is_thai_query(question)
    fallback_text = NO_ANSWER_TEXT_TH if is_thai else NO_ANSWER_TEXT_EN

    chat_history_str = session_manager.format_history_for_prompt(session_id)
    retrieval_details = search_with_details(question, chat_history=chat_history_str)
    scored_contexts = retrieval_details["results"]
    intent = retrieval_details.get("intent", "FACTOID")
    filters = retrieval_details.get("filters", {})

    contexts: list[str] = []
    has_filter = bool(filters)

    # Dynamic Intent-Aware Context Quota & Smart Trimming
    intent_cfg = _get_intent_config(intent)
    max_context_chunks = intent_cfg.get("max_context_chunks", 4)

    if intent == "RECOMMENDATION":
        max_chunks_per_project = 2
        max_total_projects = 4
        min_score = 0.0001
    elif intent == "EXPLORATORY":
        max_chunks_per_project = 1
        max_total_projects = 15
        min_score = -1.0
    elif intent == "COMPARISON":
        max_chunks_per_project = 2
        max_total_projects = 4
        min_score = 0.0001
    elif intent in {"DEEP_DIVE", "EXPLANATION"}:
        max_chunks_per_project = max_context_chunks
        max_total_projects = 1
        min_score = 0.0001
    elif intent == "CODE":
        max_chunks_per_project = max_context_chunks
        max_total_projects = 2
        min_score = 0.0001
    else:  # FACTOID / FACTUAL_LOOKUP
        max_chunks_per_project = max_context_chunks
        max_total_projects = 3
        min_score = 0.0001

    preserve_same_project_chunks = _is_code_query(question) or intent == "CODE"

    projects_ordered: list[str] = []
    projects_data: dict[str, dict] = {}
    sources: list[str] = []

    for item in scored_contexts:
        score = float(item.get("score", 0.0))
        raw_score = item.get("raw_score")
        if raw_score is not None and float(raw_score) < -3.5 and not has_filter:
            continue
        if score < min_score and projects_data:
            continue


        payload = item.get("payload", {}) or {}
        source = payload.get("source", "Unknown source")
        project_title = payload.get("project_title") or payload.get("title") or source
        proj_key = str(source).strip() if source and source != "Unknown source" else str(project_title).strip()

        raw_snippet = str(item.get("text", "")).strip()
        raw_snippet = raw_snippet.replace("\r\n", "\n").replace("\r", "\n")
        if not raw_snippet:
            continue

        if _is_boilerplate_chunk(raw_snippet) and proj_key in projects_data and projects_data[proj_key]["snippets"]:
            continue

        if proj_key not in projects_data:
            if len(projects_ordered) >= max_total_projects:
                continue
            projects_ordered.append(proj_key)
            projects_data[proj_key] = {
                "title": project_title,
                "payload": payload,
                "snippets": [],
                "pages": set(),
            }

        page_number = payload.get("page_number")
        if page_number:
            projects_data[proj_key]["pages"].add(str(page_number))

        if not preserve_same_project_chunks:
            snippet_body = " ".join(raw_snippet.split())
        else:
            snippet_body = raw_snippet

        p_str = str(page_number) if page_number else "unavailable"
        formatted_snippet = (
            f"--- [EXCERPT START | Source: {source} | Page: {p_str}] ---\n"
            f"{snippet_body}\n"
            f"--- [END OF EXCERPT | CITE AS: [Source: {source}, Page: {p_str}]] ---"
        )

        if formatted_snippet not in projects_data[proj_key]["snippets"]:
            if len(projects_data[proj_key]["snippets"]) < max_chunks_per_project:
                projects_data[proj_key]["snippets"].append(formatted_snippet)

        if source not in sources:
            sources.append(source)

    # Multi-Section Enrichment for RECOMMENDATION: ensure each recommended project includes its concrete Tech Stack chunk
    if intent == "RECOMMENDATION":
        from .semantic import semantic_search
        for proj_key in projects_ordered[:max_total_projects]:
            proj_payload = projects_data[proj_key]["payload"]
            proj_source = proj_payload.get("source")
            filter_payload = {"source": proj_source} if proj_source else ({"project_title": proj_key} if proj_key else None)
            try:
                tech_candidates = semantic_search(
                    "Equipment Website React Node.js Express Figma Flask Docker MySQL Hardware Software microcontrollers frameworks tools",
                    top_k=4,
                    metadata_filters=filter_payload,
                )
                for tc in tech_candidates:
                    raw_t = str(tc.get("text", "")).strip()
                    if raw_t and not _is_boilerplate_chunk(raw_t):
                        t_snippet = " ".join(raw_t.split())
                        p_num = tc.get("payload", {}).get("page_number")
                        p_str = str(p_num) if p_num else "unavailable"
                        formatted_t_snippet = (
                            f"--- [EXCERPT START | Source: {proj_source or proj_key} | Page: {p_str}] ---\n"
                            f"{t_snippet}\n"
                            f"--- [END OF EXCERPT | CITE AS: [Source: {proj_source or proj_key}, Page: {p_str}]] ---"
                        )
                        if formatted_t_snippet not in projects_data[proj_key]["snippets"]:
                            projects_data[proj_key]["snippets"].append(formatted_t_snippet)
                            if p_num:
                                projects_data[proj_key]["pages"].add(str(p_num))
                            break
            except Exception:
                pass

    citations: list[dict[str, Any]] = []
    for proj_key in projects_ordered:
        proj_info = projects_data[proj_key]
        snippets = proj_info["snippets"]
        if not snippets:
            continue

        payload = proj_info["payload"]
        project_title = proj_info["title"]
        author = _clean_name_spacing(payload.get("author")) or payload.get("author")
        raw_advisor = payload.get("advisor")
        advisor = _clean_name_spacing(raw_advisor) or raw_advisor
        committee = payload.get("committee")
        if committee:
            clean_committee_items = [
                _clean_name_spacing(c) for c in committee.split(",")
                if _clean_name_spacing(c)
            ]
            committee = ", ".join(clean_committee_items) if clean_committee_items else committee
        year = payload.get("year")
        school = payload.get("school")
        program = payload.get("program")
        summary = payload.get("summary")
        project_type = payload.get("project_type")
        key_technologies = payload.get("key_technologies")
        target_problem = payload.get("target_problem")
        source = payload.get("source", "Unknown source")
        pages_list = sorted(list(proj_info["pages"]))
        pages_str = ", ".join(pages_list) if pages_list else "?"

        citations.append({
            "project_title": project_title,
            "source": source,
            "pages": pages_list,
            "pages_formatted": pages_str,
            "author": author,
            "advisor": advisor,
            "committee": committee,
            "year": year,
            "school": school,
            "program": program,
            "summary": summary,
            "project_type": project_type,
            "key_technologies": key_technologies,
            "target_problem": target_problem,
        })

        context_parts = []
        if project_title:
            context_parts.append(f"Project title: {project_title}")
        if author:
            context_parts.append(f"Author: {author}")
        if advisor:
            context_parts.append(f"Advisor: {advisor}")
        if year:
            context_parts.append(f"Year: {year}")
        if program:
            context_parts.append(f"Program: {program}")
        if summary:
            context_parts.append(f"Summary: {summary}")
        if project_type:
            cat_str = ", ".join(project_type) if isinstance(project_type, list) else str(project_type)
            context_parts.append(f"Category: {cat_str}")
        if key_technologies:
            tech_str = ", ".join(key_technologies) if isinstance(key_technologies, list) else str(key_technologies)
            context_parts.append(f"Technologies: {tech_str}")
        if source:
            context_parts.append(f"Source: {source}")

        doc_idx = len(contexts) + 1
        doc_header = f"=== [DOCUMENT {doc_idx}] : {project_title} ==="
        meta_line = " | ".join(context_parts)
        combined_content = "\n\n".join(snippets)
        doc_entry = f"{doc_header}\nMetadata: {meta_line}\nDocument Content:\n{combined_content}\n=== END OF [DOCUMENT {doc_idx}] ==="
        contexts.append(doc_entry)

    retrieval_errors = retrieval_details.get("errors", [])
    retrieval_timing = retrieval_details.get("timing", {})

    return {
        "question": question,
        "is_thai": is_thai,
        "fallback_text": fallback_text,
        "chat_history_str": chat_history_str,
        "contexts": contexts,
        "sources": sources,
        "citations": citations,
        "scored_contexts": scored_contexts,
        "retrieval_details": retrieval_details,
        "intent": intent,
        "filters": filters,
        "retrieval_errors": retrieval_errors,
        "retrieval_timing": retrieval_timing,
    }


def answer_question(question: str, session_id: Optional[str] = None) -> dict[str, object]:
    """Synchronous Question Answering with In-Memory Session Memory."""
    # 0. Prescreen Intent Routing (INT-01 Greeting, INT-02 Small Talk, INT-04 Ambiguous, INT-05 Out-of-domain, INT-07 Nonsense)
    from .prescreen import prescreen_query
    prescreen_res = prescreen_query(question, session_id=session_id)
    if prescreen_res.handled:
        session_manager.add_user_message(session_id, question)
        session_manager.add_assistant_message(session_id, prescreen_res.response)
        return {
            "question": question,
            "session_id": session_id,
            "answer": prescreen_res.response,
            "intent": prescreen_res.intent,
            "contexts": [],
            "sources": [],
            "citations": [],
            "scored_contexts": [],
            "normalized_query": question,
            "filters": {},
            "query_variants": [],
            "retrieved_count": 0,
            "errors": [],
            "timing": {
                "query_proc_seconds": 0.001,
                "retrieval_seconds": 0.0,
                "rerank_seconds": 0.0,
                "llm_seconds": 0.0,
                "total_seconds": 0.001,
            },
            "performance": {},
        }

    # If query has a greeting prefix (INT-06: Mixed Intent), search the cleaned query
    query_to_search = prescreen_res.cleaned_query if prescreen_res.greeting_prefix else question
    prep = _prepare_rag_context(query_to_search, session_id=session_id)

    contexts = prep["contexts"]
    is_thai = prep["is_thai"]
    fallback_text = prep["fallback_text"]
    retrieval_details = prep["retrieval_details"]
    retrieval_timing = prep["retrieval_timing"]
    retrieval_errors = prep["retrieval_errors"]
    intent = prep["intent"]
    scored_contexts = prep["scored_contexts"]
    sources = prep["sources"]
    citations = prep["citations"]
    chat_history_str = prep["chat_history_str"]

    if not contexts and retrieval_errors:
        error_msg = (
            "การดึงข้อมูลล้มเหลว: ไม่สามารถเชื่อมต่อกับ Qdrant ได้"
            if is_thai
            else "Retrieval failed: unable to fetch documents from Qdrant right now."
        )
        return {
            "question": question,
            "session_id": session_id,
            "answer": error_msg,
            "intent": intent,
            "contexts": [],
            "sources": [],
            "citations": [],
            "scored_contexts": [],
            "normalized_query": retrieval_details.get("normalized_query", question),
            "filters": prep["filters"],
            "query_variants": retrieval_details.get("query_variants", []),
            "retrieved_count": 0,
            "errors": retrieval_errors,
            "timing": {
                "query_proc_seconds": retrieval_timing.get("query_proc_seconds", 0.0),
                "retrieval_seconds": retrieval_timing.get("retrieval_seconds", 0.0),
                "rerank_seconds": retrieval_timing.get("rerank_seconds", 0.0),
                "llm_seconds": 0.0,
                "total_seconds": retrieval_timing.get("total_seconds", 0.0),
            },
            "performance": {},
        }

    # Add user message to session history
    session_manager.add_user_message(session_id, question)

    # Check for direct Deterministic Template Response Bypass (Ultra-fast response for pure metadata lookups)
    from .template_responder import try_generate_template_response
    template_answer = try_generate_template_response(question, prep)

    # Fast Fallback when no relevant context was found (Zero LLM wait)
    if not contexts and not template_answer:
        fallback_msg = (
            f"ขออภัยครับ ไม่พบข้อมูลเกี่ยวกับ '{question.strip()}' ในฐานข้อมูลเล่มโครงงานวิศวกรรมคอมพิวเตอร์ครับ 🦝\n\n"
            f"*(ระบบมีข้อมูลเกี่ยวกับโครงงานฮาร์ดแวร์, IoT, Web/Mobile App, และ Machine Learning ของภาควิชา หากต้องการสืบค้นหัวข้ออื่น สามารถสอบถามได้เลยครับ)*"
            if is_thai
            else f"I'm sorry, but no relevant information about '{question.strip()}' was found in the senior project documents. 🦝"
        )
        if prescreen_res.greeting_prefix:
            fallback_msg = prescreen_res.greeting_prefix + fallback_msg

        session_manager.add_assistant_message(session_id, fallback_msg)
        return {
            "question": question,
            "session_id": session_id,
            "answer": fallback_msg,
            "intent": intent,
            "contexts": [],
            "sources": [],
            "citations": [],
            "scored_contexts": [],
            "normalized_query": retrieval_details.get("normalized_query", question),
            "filters": prep["filters"],
            "query_variants": retrieval_details.get("query_variants", []),
            "retrieved_count": 0,
            "errors": [],
            "timing": {
                "query_proc_seconds": retrieval_timing.get("query_proc_seconds", 0.0),
                "retrieval_seconds": retrieval_timing.get("retrieval_seconds", 0.0),
                "rerank_seconds": retrieval_timing.get("rerank_seconds", 0.0),
                "llm_seconds": 0.0,
                "total_seconds": retrieval_timing.get("total_seconds", 0.0),
            },
            "performance": {},
        }

    if template_answer:
        answer = template_answer
        # Fast-Path Shortcut does not need page numbers in citations
        cleaned_citations = []
        for c in citations:
            c_copy = dict(c)
            c_copy["pages"] = []
            c_copy["pages_formatted"] = ""
            cleaned_citations.append(c_copy)
        citations = cleaned_citations

        llm_seconds = 0.0
        stats_out: dict[str, Any] = {
            "prompt_eval_count": 0,
            "eval_count": 0,
            "gen_speed_tps": 0.0,
            "ttft_seconds": 0.0,
            "thinking_enabled": False,
            "token_breakdown": {
                "system_instruction_tokens": 0,
                "chat_history_tokens": 0,
                "document_context_tokens": 0,
                "user_question_tokens": 0,
                "context_char_length": 0,
            },
        }
    else:
        llm_start = time.perf_counter()
        stats_out = {}
        answer = get_llm_response(
            question, contexts, intent=intent, chat_history=chat_history_str, stats_out=stats_out
        )
        llm_seconds = time.perf_counter() - llm_start

        if (intent == "CODE" or _is_code_query(question)) and answer == fallback_text:
            answer = _build_code_fallback(scored_contexts, is_thai=is_thai)

    if prescreen_res.greeting_prefix and not answer.startswith(prescreen_res.greeting_prefix.strip()):
        answer = prescreen_res.greeting_prefix + answer

    # Add assistant response to session history
    session_manager.add_assistant_message(session_id, answer)


    total_seconds = retrieval_timing.get("total_seconds", 0.0) + llm_seconds
    tb = stats_out.get("token_breakdown", {})
    perf_data = {
        "intent": intent,
        "thinking_enabled": stats_out.get("thinking_enabled", False),
        "input_tokens": stats_out.get("prompt_eval_count", 0),
        "output_tokens": stats_out.get("eval_count", 0),
        "gen_speed_tps": stats_out.get("gen_speed_tps", 0.0),
        "ttft_seconds": stats_out.get("ttft_seconds", llm_seconds),
        "llm_seconds": llm_seconds,
        "retrieval_seconds": retrieval_timing.get("retrieval_seconds", 0.0),
        "rerank_seconds": retrieval_timing.get("rerank_seconds", 0.0),
        "total_seconds": total_seconds,
        "token_breakdown": tb,
    }

    print("\n" + "=" * 60)
    print("📊 [PERFORMANCE & TOKEN BREAKDOWN]")
    print("=" * 60)
    print(f"• Intent: {intent} (Thinking: {'ON' if stats_out.get('thinking_enabled') else 'OFF'})")
    if tb:
        print(f"• 📜 System Instruction: ~{tb.get('system_instruction_tokens', 0):,} tokens")
        print(f"• 💬 Chat History (Memory): ~{tb.get('chat_history_tokens', 0):,} tokens")
        print(f"• 📄 Document Context (Qdrant): ~{tb.get('document_context_tokens', 0):,} tokens ({tb.get('context_char_length', 0):,} chars)")
        print(f"• ❓ User Question: ~{tb.get('user_question_tokens', 0):,} tokens")
    print(f"• 📥 Total Input Tokens: {stats_out.get('prompt_eval_count', 0):,} tokens")
    print(f"• 📤 Output Tokens (Answer): {stats_out.get('eval_count', 0):,} tokens")
    print(f"• ⚡ Generation Speed: {stats_out.get('gen_speed_tps', 0.0):.1f} tokens/sec")
    print(f"• ⏱️ Time to First Token (TTFT): {stats_out.get('ttft_seconds', llm_seconds):.3f}s")
    print(f"• ⏱️ LLM Time: {llm_seconds:.3f}s | Retrieval Time: {retrieval_timing.get('retrieval_seconds', 0.0) + retrieval_timing.get('rerank_seconds', 0.0):.3f}s")
    print(f"• 🏁 Total Time: {total_seconds:.3f}s")
    print("=" * 60)

    return {
        "question": question,
        "session_id": session_id,
        "answer": answer,
        "intent": intent,
        "contexts": contexts,
        "sources": sources,
        "citations": citations,
        "scored_contexts": scored_contexts,
        "normalized_query": retrieval_details.get("normalized_query", question),
        "filters": prep["filters"],
        "query_variants": retrieval_details.get("query_variants", []),
        "retrieved_count": retrieval_details.get("retrieved_count", len(scored_contexts)),
        "errors": retrieval_errors,
        "timing": {
            "query_proc_seconds": retrieval_timing.get("query_proc_seconds", 0.0),
            "retrieval_seconds": retrieval_timing.get("retrieval_seconds", 0.0),
            "rerank_seconds": retrieval_timing.get("rerank_seconds", 0.0),
            "llm_seconds": llm_seconds,
            "total_seconds": total_seconds,
        },
        "performance": perf_data,
    }


def stream_answer_question(
    question: str, session_id: Optional[str] = None
) -> Generator[dict[str, Any], None, None]:
    """
    Streaming Generator for Real-Time SSE Tokens + Citations & Timing.
    
    Yields structured events:
      - {"event": "metadata", "data": {...}} : Query intent, filters, sources, citations, retrieval timing
      - {"event": "token", "data": {"token": "..."}} : Live token chunks as they are generated
      - {"event": "done", "data": {...}} : Final complete answer, timing summary, citations, performance metrics
      - {"event": "error", "data": {"error": "..."}} : If error occurs
    """
    # 0. Prescreen Intent Routing (INT-01 Greeting, INT-02 Small Talk, INT-04 Ambiguous, INT-05 Out-of-domain, INT-07 Nonsense)
    from .prescreen import prescreen_query
    prescreen_res = prescreen_query(question, session_id=session_id)
    if prescreen_res.handled:
        session_manager.add_user_message(session_id, question)
        session_manager.add_assistant_message(session_id, prescreen_res.response)
        yield {
            "event": "metadata",
            "data": {
                "question": question,
                "session_id": session_id,
                "intent": prescreen_res.intent,
                "normalized_query": question,
                "filters": {},
                "sources": [],
                "citations": [],
                "retrieved_count": 0,
                "timing": {
                    "query_proc_seconds": 0.001,
                    "retrieval_seconds": 0.0,
                    "rerank_seconds": 0.0,
                },
            },
        }
        yield {"event": "token", "data": {"token": prescreen_res.response}}
        yield {
            "event": "done",
            "data": {
                "answer": prescreen_res.response,
                "session_id": session_id,
                "intent": prescreen_res.intent,
                "sources": [],
                "citations": [],
                "timing": {
                    "query_proc_seconds": 0.001,
                    "retrieval_seconds": 0.0,
                    "rerank_seconds": 0.0,
                    "llm_seconds": 0.0,
                    "total_seconds": 0.001,
                },
                "performance": {},
            },
        }
        return

    # If query has a greeting prefix (INT-06: Mixed Intent), search the cleaned query
    query_to_search = prescreen_res.cleaned_query if prescreen_res.greeting_prefix else question
    prep = _prepare_rag_context(query_to_search, session_id=session_id)

    contexts = prep["contexts"]
    is_thai = prep["is_thai"]
    fallback_text = prep["fallback_text"]
    retrieval_details = prep["retrieval_details"]
    retrieval_timing = prep["retrieval_timing"]
    retrieval_errors = prep["retrieval_errors"]
    intent = prep["intent"]
    scored_contexts = prep["scored_contexts"]
    sources = prep["sources"]
    citations = prep["citations"]
    chat_history_str = prep["chat_history_str"]

    if not contexts and retrieval_errors:
        error_msg = (
            "การดึงข้อมูลล้มเหลว: ไม่สามารถเชื่อมต่อกับ Qdrant ได้"
            if is_thai
            else "Retrieval failed: unable to fetch documents from Qdrant right now."
        )
        yield {"event": "error", "data": {"error": error_msg, "errors": retrieval_errors}}
        yield {
            "event": "done",
            "data": {
                "answer": error_msg,
                "session_id": session_id,
                "sources": [],
                "citations": [],
                "timing": {
                    "query_proc_seconds": retrieval_timing.get("query_proc_seconds", 0.0),
                    "retrieval_seconds": retrieval_timing.get("retrieval_seconds", 0.0),
                    "rerank_seconds": retrieval_timing.get("rerank_seconds", 0.0),
                    "llm_seconds": 0.0,
                    "total_seconds": retrieval_timing.get("total_seconds", 0.0),
                },
                "performance": {},
            },
        }
        return

    # Add user query to session manager
    session_manager.add_user_message(session_id, question)

    # Check for direct Deterministic Template Response Bypass
    from .template_responder import try_generate_template_response
    template_answer = try_generate_template_response(question, prep)

    if template_answer:
        # Fast-Path Shortcut does not need page numbers in citations
        cleaned_citations = []
        for c in citations:
            c_copy = dict(c)
            c_copy["pages"] = []
            c_copy["pages_formatted"] = ""
            cleaned_citations.append(c_copy)
        citations = cleaned_citations

    # 1. Yield Initial Metadata Event (Instant feedback on intent and retrieved documents)
    metadata_payload = {
        "question": question,
        "session_id": session_id,
        "intent": intent,
        "normalized_query": retrieval_details.get("normalized_query", question),
        "filters": prep["filters"],
        "sources": sources,
        "citations": citations,
        "retrieved_count": len(scored_contexts),
        "timing": {
            "query_proc_seconds": retrieval_timing.get("query_proc_seconds", 0.0),
            "retrieval_seconds": retrieval_timing.get("retrieval_seconds", 0.0),
            "rerank_seconds": retrieval_timing.get("rerank_seconds", 0.0),
        },
    }
    yield {"event": "metadata", "data": metadata_payload}

    # Fast Fallback when no relevant context was found (Zero LLM wait)
    if not contexts and not template_answer:
        fallback_msg = (
            f"ขออภัยครับ ไม่พบข้อมูลเกี่ยวกับ '{question.strip()}' ในฐานข้อมูลเล่มโครงงานวิศวกรรมคอมพิวเตอร์ครับ 🦝\n\n"
            f"*(ระบบมีข้อมูลเกี่ยวกับโครงงานฮาร์ดแวร์, IoT, Web/Mobile App, และ Machine Learning ของภาควิชา หากต้องการสืบค้นหัวข้ออื่น สามารถสอบถามได้เลยครับ)*"
            if is_thai
            else f"I'm sorry, but no relevant information about '{question.strip()}' was found in the senior project documents. 🦝"
        )
        if prescreen_res.greeting_prefix:
            fallback_msg = prescreen_res.greeting_prefix + fallback_msg

        yield {"event": "token", "data": {"token": fallback_msg}}
        session_manager.add_assistant_message(session_id, fallback_msg)
        yield {
            "event": "done",
            "data": {
                "answer": fallback_msg,
                "session_id": session_id,
                "intent": intent,
                "sources": [],
                "citations": [],
                "timing": {
                    "query_proc_seconds": retrieval_timing.get("query_proc_seconds", 0.0),
                    "retrieval_seconds": retrieval_timing.get("retrieval_seconds", 0.0),
                    "rerank_seconds": retrieval_timing.get("rerank_seconds", 0.0),
                    "llm_seconds": 0.0,
                    "total_seconds": retrieval_timing.get("total_seconds", 0.0),
                },
                "performance": {},
            },
        }
        return

    # Yield greeting prefix first if mixed intent
    if prescreen_res.greeting_prefix:
        yield {"event": "token", "data": {"token": prescreen_res.greeting_prefix}}

    if template_answer:
        cleaned_answer = template_answer
        llm_seconds = 0.0
        stats_out: dict[str, Any] = {
            "prompt_eval_count": 0,
            "eval_count": 0,
            "gen_speed_tps": 0.0,
            "ttft_seconds": 0.0,
            "thinking_enabled": False,
            "token_breakdown": {
                "system_instruction_tokens": 0,
                "chat_history_tokens": 0,
                "document_context_tokens": 0,
                "user_question_tokens": 0,
                "context_char_length": 0,
            },
        }
        # Yield the complete template answer token immediately
        yield {"event": "token", "data": {"token": template_answer}}
    else:
        # 2. Stream Tokens from LLM
        full_tokens: list[str] = []
        stats_out = {}
        llm_start = time.perf_counter()

        for token in stream_llm_response(
            question, contexts, intent=intent, chat_history=chat_history_str, stats_out=stats_out
        ):
            full_tokens.append(token)
            yield {"event": "token", "data": {"token": token}}

        llm_seconds = time.perf_counter() - llm_start
        raw_full_answer = "".join(full_tokens)
        cleaned_answer = clean_answer(raw_full_answer, is_thai=is_thai)

        if (intent == "CODE" or _is_code_query(question)) and cleaned_answer == fallback_text:
            cleaned_answer = _build_code_fallback(scored_contexts, is_thai=is_thai)

    if prescreen_res.greeting_prefix and not cleaned_answer.startswith(prescreen_res.greeting_prefix.strip()):
        cleaned_answer = prescreen_res.greeting_prefix + cleaned_answer

    # Add assistant response to session manager
    session_manager.add_assistant_message(session_id, cleaned_answer)


    total_seconds = retrieval_timing.get("total_seconds", 0.0) + llm_seconds
    tb = stats_out.get("token_breakdown", {})
    perf_data = {
        "intent": intent,
        "thinking_enabled": stats_out.get("thinking_enabled", False),
        "input_tokens": stats_out.get("prompt_eval_count", 0),
        "output_tokens": stats_out.get("eval_count", 0),
        "gen_speed_tps": stats_out.get("gen_speed_tps", 0.0),
        "ttft_seconds": stats_out.get("ttft_seconds", llm_seconds),
        "llm_seconds": llm_seconds,
        "retrieval_seconds": retrieval_timing.get("retrieval_seconds", 0.0),
        "rerank_seconds": retrieval_timing.get("rerank_seconds", 0.0),
        "total_seconds": total_seconds,
        "token_breakdown": tb,
    }

    # 3. Yield Final Done Event with Timing, Citations & Performance Metrics
    yield {
        "event": "done",
        "data": {
            "answer": cleaned_answer,
            "session_id": session_id,
            "intent": intent,
            "sources": sources,
            "citations": citations,
            "timing": {
                "query_proc_seconds": retrieval_timing.get("query_proc_seconds", 0.0),
                "retrieval_seconds": retrieval_timing.get("retrieval_seconds", 0.0),
                "rerank_seconds": retrieval_timing.get("rerank_seconds", 0.0),
                "llm_seconds": llm_seconds,
                "total_seconds": total_seconds,
            },
            "performance": perf_data,
        },
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
        print(f"\n❓ คำถาม: {user_query}\n")
        res = answer_question(user_query)
        print("\n💡 คำตอบ:")
        print(res["answer"])
    else:
        print("\n" + "=" * 60)
        print("🤖 RAGcoon Interactive Query CLI (พิมพ์ 'exit' หรือ 'q' เพื่อออก)")
        print("=" * 60)
        while True:
            try:
                user_query = input("\n❓ ถามคำถาม: ").strip()
                if not user_query or user_query.lower() in {"exit", "quit", "q"}:
                    print("\n👋 ลาก่อนครับ!")
                    break
                res = answer_question(user_query)
                print("\n💡 คำตอบ:")
                print(res["answer"])
            except (KeyboardInterrupt, EOFError):
                print("\n👋 ยกเลิกการทำงาน")
                break
