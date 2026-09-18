import json
import os
import re
import time
from collections.abc import Generator
from typing import Any, Optional

import requests
from dotenv import load_dotenv

from .config import INTENT_CONFIG
from .service import is_boilerplate_text, search, search_with_details
from .session_manager import session_manager

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
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

    # Strip trailing reasoning meta-talk or duplicate summary tails
    cleaned = re.split(
        r"\n\s*(?:wait,\s*let me|let me check|let me verify|i need to check|to double check|the context shows|the document also mentions|in summary|to summarize|###\s*ข้อสังเกต|###\s*ตรวจสอบ|###\s*สรุป|###\s*notes)",
        cleaned,
        flags=re.IGNORECASE,
    )[0].strip()

    return cleaned or fallback_text


def _build_intent_instruction(intent: str, question: str = "") -> str:
    """Return specialized prompt instructions based on dynamic query intent."""
    q_lower = question.lower()
    if intent == "RECOMMENDATION":
        return """4. Domain Track Recommendations (Strict Evidence vs AI Projections):
   Group the retrieved projects into top 3-4 specialization tracks (e.g. "🤖 Track: AI & Data Science", "⚡ Track: IoT & Hardware Automation", "🛡️ Track: Cybersecurity & Infrastructure", "💻 Track: Web & Enterprise Platforms").

   Under each track, present the project formatted strictly into 2 clearly separated sections:
   ### [Track Name]
   #### **[Project Title]** ([Academic Year])
   📄 **ข้อมูลจริงจากเอกสาร (Document Evidence)**:
   - 🎯 **Core Objective & Problem**: [1 concise sentence on core problem and objective strictly from document].
   - 🛠️ **Tech Stack & Tools**: [List exact languages, frameworks, microcontrollers, sensors, tools (e.g. React, Flask, Arduino Mega 2560, Kali Linux, Docker, MySQL) found in document snippets].
   - 👥 **Team & Advisor**: Authors: [Author Names] | Advisor: [Advisor Name]

   💡 **ข้อเสนอแนะ & แนวทางต่อยอด (AI Recommendations)**:
   - 🚀 **Future Extensions**: [1-2 concise, actionable ideas for new students to build upon or optimize this project].
   - 🎯 **Best Suited For**: [Target student interests/strengths, e.g. Hardware/Embedded, Full-Stack, AI/Data].

5. Conclude with a 1-sentence "🧭 Career & Interest Guide".
6. Keep each bullet point concise (1-2 sentences maximum). Do not output robotic intros or placeholder tags like '[DOCUMENT 1]'."""
    elif intent == "EXPLORATORY":
        if any(w in q_lower for w in ["similar", "คล้าย", "เหมือน", "group", "กลุ่ม"]):
            return """4. Theme-Based Similarity Grouping:
   - Group ALL the retrieved projects into clear, logical domain/objective categories (e.g. "1. IoT, Automation & Hardware Systems", "2. Web & Service Management Platforms", "3. Network & Energy Optimization").
   - Under each group, list the matching projects formatted as:
     * **[Project Title]** ([Year]) - [Core objective, system operation, and key technologies based strictly on its own document text].
   - Conclude with a brief 1-2 sentence summary explaining the common objective thread among the grouped projects.
5. Do NOT output placeholder tags like '[DOCUMENT 1]' in your text; use the actual clean Project Title."""
        else:
            return """4. Enumerated Project Overview: Enumerate ALL distinct projects found in the retrieved context without omitting any:
   1. **[Project Title]** ([Year]) - [Summary of core objectives and system operation]. (Authors: [Author Names], Advisor: [Advisor Name]). Key technologies/tools: [List languages, frameworks, hardware, APIs, or libraries mentioned if available].
5. Provide a rich, informative overview covering each retrieved project concisely. Do not output repetitive filler phrases. Do not use '[DOCUMENT 1]' tags."""
    elif intent in {"DEEP_DIVE", "EXPLANATION"}:
        return """4. In-Depth Technical Breakdown: Provide a comprehensive and thorough technical analysis directly addressing the question, structured into clear sections:
   - **Project Overview & Objectives**: Core problem addressed and main goals.
   - **System Architecture & Methodology**: System workflows, design patterns, and operational steps.
   - **Tech Stack, Tools & Hardware**: Exact languages, frameworks, libraries, microcontrollers, or cloud services used.
   - **Results & Evaluation**: Expected or achieved results, testing methodologies, and deliverables.
5. Do not use '[DOCUMENT 1]' tags in your final text; use the actual Project Title."""
    elif intent == "COMPARISON":
        return """4. Comparative Synthesis & Multi-Criteria Scoring Matrix:
   Structure your comparative analysis into the following 4 clear sections:

   ### 1. Side-by-Side Feature Comparison Table
   Create a Markdown table comparing:
   | Project Title | Year | Core Objective | Tech Stack / Architecture | Key Strengths | Limitations / Challenges |

   ### 2. Multi-Criteria Scoring Matrix (Evaluation 1–10 Scale)
   Evaluate each compared project across 3 academic dimensions (Score 1.0–10.0 based strictly on document evidence):
   - **Technical Complexity & Architecture** [Weight 40%]: Depth of software/algorithms/hardware, DB schema, models.
   - **Practicality & Business Readiness** [Weight 30%]: User workflow, deployment readiness, stakeholder problem solving.
   - **System Completeness & Evaluation** [Weight 30%]: Testing completeness, evaluation metrics, methodology rigor.

   Present as a Markdown table:
   | Project Title | Technical Complexity (40%) | Practicality (30%) | System Completeness (30%) | Weighted Total Score (/10) |

   Formula: Weighted Total = (0.4 * Complexity) + (0.3 * Practicality) + (0.3 * Completeness)

   ### 3. Evidence-Based Scoring Justification & Citation Guard
   For each project, write concise 1-line justification bullets explaining its score with exact citation tags and page numbers:
   - **[Project Title]**:
     * Complexity (X.X): [Concise reason]. [อ้างอิง: <Filename.pdf> หน้า <Pages>]
     * Practicality (X.X): [Concise reason]. [อ้างอิง: <Filename.pdf> หน้า <Pages>]
     * Completeness (X.X): [Concise reason]. [อ้างอิง: <Filename.pdf> หน้า <Pages>]

   ### 4. Trade-Off Analysis & Recommendations
   Provide a concise 2-3 sentence academic synthesis explaining domain trade-offs and recommendations on when to select each project.

5. Do not write robotic intros like 'To determine...', 'From [DOCUMENT 1]...', or 'Based on the documents...'; start directly with the structured comparison."""
    elif intent == "CODE":
        return """4. Technical Code Extraction: Extract and present exact code snippets, SQL queries, algorithms, or API calls from the text in syntax-highlighted code blocks (```). Explain what each code snippet or configuration does."""
    else:  # FACTOID / FACTUAL_LOOKUP
        if any(w in q_lower for w in ["microcontroller", "sensor", "sensors", "hardware", "tool", "tools", "อุปกรณ์", "บอร์ด", "เซนเซอร์", "ไมโครคอนโทรลเลอร์", "component", "components"]):
            return """4. Structured Component Breakdown with Inline Page Citations:
   Present the components found in the retrieved documents formatted clearly with their exact Page numbers attached directly to each item:

   ### 📋 Component Summary
   - **Microcontroller**: <exact microcontroller name> [Page X] (Section name if applicable)
   - **Sensors**:
     * <sensor 1> [Page X]
     * <sensor 2> [Page X]
     * <sensor 3> [Page X]
   - **Key Associated Hardware**: <list key related modules such as valves, pumps, relays> [Page X]

   CRITICAL RULES:
   - Always append the exact [Page X] (or [หน้า X] if Thai) directly on the same line as the component name.
   - Categorize all sensors (e.g. pH sensor, EC sensor, Ultrasonic level/distance sensor) under '**Sensors**'.
   - Do NOT duplicate the list in a separate section. Stop immediately after the component list."""
        else:
            return """4. Direct Answer with Inline Page Citations:
   Provide an exact, concise factual answer directly answering the question, with the exact Page number (e.g., [Page X] or [หน้า X]) appended directly after the factual statement. Stop immediately."""


def _build_full_prompt(
    question: str,
    context_list: list[str],
    intent: str = "FACTOID",
    chat_history: str = "",
) -> tuple[str, bool, str, int, bool, str]:
    """Construct prompt in ChatML format and return (prompt, is_thai, fallback_text, num_predict, thinking_enabled, prefill_prefix)."""
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

    if intent in {"FACTOID", "FACTUAL_LOOKUP"}:
        system_content = f"""You are a precise academic document QA assistant. Use ONLY the retrieved context below.
Answer accurately and structure your response with both a clear direct summary and document evidence citations based strictly on the text.
Do not output internal reasoning monologue, robotic intros, or personal meta-talk.
{intent_instruction}
{lang_instruction}
If the context contains no relevant information, reply exactly: {insufficient_reply}"""
    else:
        system_content = f"""You are an expert AI academic assistant for a university senior project document repository.
Use ONLY the retrieved context below. Do not invent facts or extrapolate beyond what is stated.
CRITICAL INSTRUCTIONS:
1. Strict Document Independence: The context contains numbered documents (e.g. [DOCUMENT 1], [DOCUMENT 2]). You must analyze each document strictly on its own.
2. ZERO Cross-Contamination: NEVER transfer, duplicate, or copy features, functionalities, equipment, or future plans from one document into another unrelated document. Every single detail for a project must come exclusively from that project's own document block.
3. Accurate Objective & Technical Coverage:
   - Describe what each project accomplishes, its methodology/operation, and key tools/technologies used based strictly on its own document excerpt.
   - Only mention future plans/extensions if the project explicitly mentions them AND the user's question relates to future work/development. Do NOT append boilerplate phrases like '(No explicit future extensions detailed)' on general questions.
   - NEVER transfer features (like barcodes, sensors, or stock alerts) to other projects!
{intent_instruction}
6. No Robotic Meta-Talk: Never write boilerplate intros like "To determine which projects...", "From [DOCUMENT 1] : ...", or "Based on the provided documents...". Start directly with the structured answer content.
7. If the question asks for tools, frameworks, hardware, sensors, technologies, libraries, software, or methodologies, extract only what is mentioned in that specific project.
8. If the question asks about advisor, author, committee, or year, provide the accurate answer directly from the metadata.
9. {lang_instruction}
10. Only if the context contains absolutely no relevant information, reply exactly: {insufficient_reply}
11. Keep the answer accurate, well-structured, objective, and professional."""

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
    num_predict = intent_cfg.get("num_predict", 256)
    thinking_enabled = intent_cfg.get("thinking", False)

    think_block = "" if thinking_enabled else "<think>\n</think>\n"
    q_lower = question.lower()
    prefill = ""
    if intent in {"FACTOID", "FACTUAL_LOOKUP"} and any(w in q_lower for w in ["microcontroller", "sensor", "sensors", "hardware", "tool", "tools", "อุปกรณ์", "บอร์ด", "เซนเซอร์", "ไมโครคอนโทรลเลอร์", "component", "components"]):
        prefill = "### 📋 สรุปรายการอุปกรณ์\n- **ไมโครคอนโทรลเลอร์ (Microcontroller)**:" if is_thai else "### 📋 Component Summary\n- **Microcontroller**:"

    prompt = f"<|im_start|>system\n{system_content}<|im_end|>\n<|im_start|>user\n{user_content}<|im_end|>\n<|im_start|>assistant\n{think_block}{prefill}"

    return prompt, is_thai, fallback_text, num_predict, thinking_enabled, prefill


def get_llm_response(
    question: str,
    context_list: list[str],
    intent: str = "FACTOID",
    chat_history: str = "",
    stats_out: Optional[dict[str, Any]] = None,
) -> str:
    """Synchronous (non-streaming) LLM call with timing & performance stats extraction."""
    prompt, is_thai, fallback_text, num_predict, thinking_enabled, prefill = _build_full_prompt(
        question, context_list, intent=intent, chat_history=chat_history
    )

    if not context_list:
        return fallback_text

    ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT", "180"))
    start_t = time.perf_counter()
    stop_tokens = [
        "<|im_end|>", "<|im_start|>", "<think>", "</think>",
        "\n\nWait,", "\n\nI need to check", "\n\nLet me check", "\n\nTo double check",
        "\n\nThe context shows", "\n\nThe document also mentions", "\n\nIn summary",
        "\n\nTo summarize", "\n\nSummary:", "\n\nสรุป:", "\n\n### ข้อสังเกต",
        "\n\n### ตรวจสอบ", "\n\n### สรุป", "\n\n### Notes",
    ]
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
        stats_out.update({
            "prompt_eval_count": p_eval,
            "eval_count": e_count,
            "eval_duration_ns": e_dur_ns,
            "gen_speed_tps": gen_speed,
            "ttft_seconds": duration,
            "llm_seconds": duration,
            "thinking_enabled": thinking_enabled,
            "intent": intent,
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
    prompt, is_thai, fallback_text, num_predict, thinking_enabled, prefill = _build_full_prompt(
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

    stop_tokens = [
        "<|im_end|>", "<|im_start|>", "<think>", "</think>",
        "\n\nWait,", "\n\nI need to check", "\n\nLet me check", "\n\nTo double check",
        "\n\nThe context shows", "\n\nThe document also mentions", "\n\nIn summary",
        "\n\nTo summarize", "\n\nSummary:", "\n\nสรุป:", "\n\n### ข้อสังเกต",
        "\n\n### ตรวจสอบ", "\n\n### สรุป", "\n\n### Notes",
    ]
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
                                stats_out.update({
                                    "prompt_eval_count": p_eval,
                                    "eval_count": e_count,
                                    "eval_duration_ns": e_dur_ns,
                                    "gen_speed_tps": gen_speed,
                                    "ttft_seconds": ttft or (time.perf_counter() - stream_start),
                                    "thinking_enabled": thinking_enabled,
                                    "intent": intent,
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
        max_total_projects = 6
        min_score = 0.0001
    elif intent == "COMPARISON":
        max_chunks_per_project = 2
        max_total_projects = 4
        min_score = 0.0001
    elif intent in {"DEEP_DIVE", "EXPLANATION"}:
        max_chunks_per_project = max_context_chunks
        max_total_projects = 1
        min_score = 0.0001
    elif intent == "CODE":
        max_chunks_per_project = 4
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

        page_tag = f"[Excerpt from Page {page_number}]:\n" if page_number else ""
        formatted_snippet = f"{page_tag}{snippet_body}"

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
                        if t_snippet not in projects_data[proj_key]["snippets"]:
                            projects_data[proj_key]["snippets"].append(t_snippet)
                            p_num = tc.get("payload", {}).get("page_number")
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
        keywords = payload.get("keywords")
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
            "year": year,
        })

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
            context_parts.append(f"Source: {source} (Pages: {pages_str})")

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
    prep = _prepare_rag_context(question, session_id=session_id)

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

    llm_start = time.perf_counter()
    stats_out: dict[str, Any] = {}
    answer = get_llm_response(
        question, contexts, intent=intent, chat_history=chat_history_str, stats_out=stats_out
    )
    llm_seconds = time.perf_counter() - llm_start

    if (intent == "CODE" or _is_code_query(question)) and answer == fallback_text:
        answer = _build_code_fallback(scored_contexts, is_thai=is_thai)

    # Add assistant response to session history
    session_manager.add_assistant_message(session_id, answer)

    total_seconds = retrieval_timing.get("total_seconds", 0.0) + llm_seconds
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
    }

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
    prep = _prepare_rag_context(question, session_id=session_id)

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

    # 2. Stream Tokens from LLM
    full_tokens: list[str] = []
    stats_out: dict[str, Any] = {}
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

    # Add assistant response to session manager
    session_manager.add_assistant_message(session_id, cleaned_answer)

    total_seconds = retrieval_timing.get("total_seconds", 0.0) + llm_seconds
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
