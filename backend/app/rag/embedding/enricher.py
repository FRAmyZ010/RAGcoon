import json
import os
import re
from typing import Any, Optional

import requests
from dotenv import load_dotenv

from .category_registry import (
    MAX_KEYWORDS,
    normalize_categories,
    normalize_keywords,
    seed_categories,
)

load_dotenv()


def _ollama_generate_url() -> str:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    if base.endswith("/api"):
        base = base[: -len("/api")]
    return f"{base}/api/generate"


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
ENRICHMENT_PASSES = max(2, int(os.getenv("ENRICHMENT_PASSES", "3")))
ENRICHMENT_TIMEOUT = (
    float(os.getenv("ENRICHMENT_CONNECT_TIMEOUT", "5")),
    float(os.getenv("ENRICHMENT_READ_TIMEOUT", "90")),
)

_HEURISTIC_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("IoT", ("iot", "sensor", "lora", "mqtt", "nodemcu", "esp32", "esp8266", "watering", "smart farm")),
    ("Hardware", ("arduino", "microcontroller", "raspberry", "gpio", "robot", "hardware", "liquid flow", "meter")),
    ("Network", ("wifi", "wlan", "network", "access point", "cisco", "ble", "bluetooth", "beacon")),
    ("Web", ("web", "website", "react", "frontend", "backend", "tourist", "ticketing")),
    ("Mobile", ("mobile", "android", "ios", "flutter", "application app")),
    ("Machine learning", ("machine learning", "classification", "clustering", "neural", "prediction", "detection", "logo detection")),
    ("Security", ("security", "secure", "cyber", "authentication", "encryption", "illegitimate")),
    ("Database", ("database", "mysql", "postgres", "sql")),
    ("Automation", ("automation", "monitoring", "tracking", "locating", "vehicle access")),
]


def _fallback_enrichment(existing_keywords: Optional[str] = None) -> dict[str, Any]:
    keywords = normalize_keywords(existing_keywords)[:MAX_KEYWORDS]
    return {
        "summary": None,
        "project_type": [],
        "key_technologies": [],
        "target_problem": None,
        "keywords": keywords,
        "categories": ["Other"],
    }


def _heuristic_categories(
    project_title: Optional[str],
    existing_keywords: Optional[str],
    text: str,
    registry: list[str],
) -> list[str]:
    """Last-resort domain guess from title/keywords/abstract when LLM keeps returning Other."""
    blob = " ".join(
        part for part in [project_title or "", existing_keywords or "", text[:2000]] if part
    ).casefold()
    found: list[str] = []
    for category, needles in _HEURISTIC_RULES:
        if any(needle in blob for needle in needles):
            if category not in found:
                found.append(category)
        if len(found) >= 3:
            break
    return normalize_categories(found, registry)


def _build_prompt(
    *,
    project_title: Optional[str],
    clean_text: str,
    existing_kw_text: str,
    options_text: str,
    pass_no: int,
    total_passes: int,
    prior: dict[str, Any] | None,
) -> tuple[str, str]:
    system_prompt = (
        "You are a Senior Project Analysis Engine. Read the abstract and keywords carefully, "
        "then extract structured metadata. Respond with ONLY valid JSON."
    )

    prior_block = ""
    if prior:
        prior_block = f"""
Previous pass result (refine and improve; do NOT casually keep Other):
- previous categories: {prior.get("categories")}
- previous keywords: {prior.get("keywords")}
"""

    urgency = ""
    if pass_no > 1:
        urgency = (
            f"\nThis is pass {pass_no}/{total_passes}. "
            "The previous pass was too generic or used Other. "
            "You MUST assign a concrete category from the available list or invent a precise English name. "
            "Other is almost never acceptable when the title/abstract mentions a clear domain "
            "(web, IoT, robot, network, ML, security, monitoring, etc.).\n"
        )

    user_prompt = f"""Project Title: {project_title or 'Senior Project'}

Document Excerpt (prefer Abstract / บทคัดย่อ):
{clean_text}

Existing Keyword line (may be empty or truncated):
{existing_kw_text}
{prior_block}{urgency}
Available categories (prefer these exact names when they fit):
{options_text}

Extract the following fields into valid JSON:
1. "summary": A concise 1-2 sentence overview in the primary language of the text.
2. "project_type": A JSON array of 1-3 broad categories (legacy; may mirror "categories").
3. "key_technologies": A JSON array of technologies/frameworks/hardware mentioned.
4. "target_problem": A concise 1-sentence problem statement.
5. "keywords": A refined JSON array of up to {MAX_KEYWORDS} concise keywords (not a raw copy only).
6. "categories": A JSON array of 1-3 category names.
   Rules for categories (strict):
   - Prefer exact names from the available list when they fit.
   - If the domain is clear but missing from the list, invent a short English Title Case name (1-3 words).
   - Prefer inventing over Other whenever the topic is identifiable.
   - Use ["Other"] ONLY if the excerpt is empty/unreadable.
   - Never combine Other with another category.

JSON Format:
{{
  "summary": "...",
  "project_type": ["..."],
  "key_technologies": ["..."],
  "target_problem": "...",
  "keywords": ["..."],
  "categories": ["..."]
}}"""
    return system_prompt, user_prompt


def _parse_enrichment_payload(
    parsed: dict[str, Any],
    *,
    existing_keywords: Optional[str],
    options: list[str],
) -> dict[str, Any]:
    summary = parsed.get("summary")
    if summary and isinstance(summary, str):
        summary = summary.strip()
    else:
        summary = None

    proj_types = parsed.get("project_type", [])
    if isinstance(proj_types, str):
        proj_types = [p.strip() for p in proj_types.split(",") if p.strip()]
    elif isinstance(proj_types, list):
        proj_types = [str(p).strip() for p in proj_types if str(p).strip()]
    else:
        proj_types = []

    key_techs = parsed.get("key_technologies", [])
    if isinstance(key_techs, str):
        key_techs = [t.strip() for t in key_techs.split(",") if t.strip()]
    elif isinstance(key_techs, list):
        key_techs = [str(t).strip() for t in key_techs if str(t).strip()]
    else:
        key_techs = []

    target_problem = parsed.get("target_problem")
    if target_problem and isinstance(target_problem, str):
        target_problem = target_problem.strip()
    else:
        target_problem = None

    keywords = normalize_keywords(parsed.get("keywords"))
    if not keywords:
        keywords = normalize_keywords(existing_keywords) or normalize_keywords(key_techs)

    categories = normalize_categories(parsed.get("categories"), options)
    for name in categories:
        if name not in options and name != "Other":
            options.append(name)
    categories = normalize_categories(categories, options)

    return {
        "summary": summary,
        "project_type": proj_types,
        "key_technologies": key_techs,
        "target_problem": target_problem,
        "keywords": keywords,
        "categories": categories,
    }


def _call_ollama_enrichment(
    *,
    system_prompt: str,
    user_prompt: str,
    timeout: int | tuple[float, float],
) -> dict[str, Any]:
    response = requests.post(
        _ollama_generate_url(),
        json={
            "model": OLLAMA_MODEL,
            "prompt": (
                f"<start_of_turn>user\n{system_prompt}\n\n{user_prompt}"
                f"<end_of_turn>\n<start_of_turn>model\n"
            ),
            "format": "json",
            "stream": False,
            "keep_alive": "10m",
            "options": {
                "temperature": 0.1,
                "num_predict": 450,
            },
        },
        timeout=timeout,
    )
    response.raise_for_status()
    raw_output = response.json().get("response", "").strip()
    # Some models wrap JSON in fences; keep only the object.
    if "```" in raw_output:
        match = re.search(r"\{[\s\S]*\}", raw_output)
        if match:
            raw_output = match.group(0)
    return json.loads(raw_output)


def extract_project_enrichment(
    text: str,
    project_title: Optional[str] = None,
    existing_keywords: Optional[str] = None,
    category_options: Optional[list[str]] = None,
    timeout: int | tuple[float, float] | None = None,
) -> dict[str, Any]:
    """
    Multi-pass LLM enrichment (default 3):
    Abstract + Keywords → refined keywords + categories.
    Retries when the model returns Other or the call fails.
    """
    timeout = timeout or ENRICHMENT_TIMEOUT
    fallback_res = _fallback_enrichment(existing_keywords)

    if not text or not str(text).strip():
        return fallback_res

    clean_text = text.strip()[:3500]
    options = list(category_options or seed_categories())
    options_text = ", ".join(options)
    existing_kw_text = (existing_keywords or "").strip() or "(none)"

    best = fallback_res
    prior: dict[str, Any] | None = None

    for pass_no in range(1, ENRICHMENT_PASSES + 1):
        system_prompt, user_prompt = _build_prompt(
            project_title=project_title,
            clean_text=clean_text,
            existing_kw_text=existing_kw_text,
            options_text=options_text,
            pass_no=pass_no,
            total_passes=ENRICHMENT_PASSES,
            prior=prior,
        )
        try:
            parsed = _call_ollama_enrichment(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout=timeout,
            )
            result = _parse_enrichment_payload(
                parsed,
                existing_keywords=existing_keywords,
                options=options,
            )
            print(
                f"✅ [Enrichment] pass {pass_no}/{ENRICHMENT_PASSES} "
                f"categories={result['categories']} keywords={len(result['keywords'])}"
            )
            # Prefer a concrete category over Other; otherwise keep latest keywords/summary.
            if result["categories"] != ["Other"] or best.get("categories") == ["Other"]:
                best = result
            prior = {
                "categories": result["categories"],
                "keywords": result["keywords"],
            }
        except Exception as exc:
            print(f"⚠️ [Enrichment Warning] pass {pass_no}/{ENRICHMENT_PASSES} failed: {exc}")
            continue

    # After all LLM passes still Other → lightweight heuristic from title/keywords/abstract
    if best.get("categories") == ["Other"]:
        guessed = _heuristic_categories(project_title, existing_keywords, clean_text, options)
        if guessed != ["Other"]:
            print(f"✅ [Enrichment] heuristic categories={guessed}")
            best = {**best, "categories": guessed}
            if not best.get("keywords"):
                best["keywords"] = normalize_keywords(existing_keywords)

    return best
