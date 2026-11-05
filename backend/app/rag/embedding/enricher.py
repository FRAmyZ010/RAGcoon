import json
import os
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

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")


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


def extract_project_enrichment(
    text: str,
    project_title: Optional[str] = None,
    existing_keywords: Optional[str] = None,
    category_options: Optional[list[str]] = None,
    timeout: int | tuple[float, float] = (3, 30),
) -> dict[str, Any]:
    """
    Use lightweight local LLM to extract high-impact metadata:
      - summary, project_type, key_technologies, target_problem (legacy fields)
      - keywords (refined list from Abstract + existing Keyword line)
      - categories (from seed/registry; may invent English names)
    """
    fallback_res = _fallback_enrichment(existing_keywords)

    if not text or not str(text).strip():
        return fallback_res

    clean_text = text.strip()[:3500]
    options = list(category_options or seed_categories())
    options_text = ", ".join(options)
    existing_kw_text = (existing_keywords or "").strip() or "(none)"

    system_prompt = (
        "You are a Senior Project Analysis Engine. Analyze the following project abstract/document excerpt "
        "and extract structured metadata. You MUST respond with ONLY a valid JSON object matching the requested schema."
    )

    user_prompt = f"""Project Title: {project_title or 'Senior Project'}

Document Excerpt (prefer Abstract / บทคัดย่อ):
{clean_text}

Existing Keyword line (may be empty or truncated):
{existing_kw_text}

Available categories (prefer these exact names; invent a short new English category ONLY if none fit):
{options_text}

Extract the following fields into valid JSON:
1. "summary": A concise 1-2 sentence overview in the primary language of the text describing what the project does and how it works.
2. "project_type": A JSON array of 1-3 broad categories (legacy; may mirror "categories").
3. "key_technologies": A JSON array of specifically mentioned technologies, frameworks, microcontrollers, sensors, or databases.
4. "target_problem": A concise 1-sentence statement of the main real-world problem or pain point this project solves.
5. "keywords": A refined JSON array of up to {MAX_KEYWORDS} concise keywords (not a raw copy of the Keyword line only). Use English when the abstract is English.
6. "categories": A JSON array of 1-3 category names from the available list above. Use exactly ["Other"] when nothing else fits. Never combine Other with another category.

JSON Format:
{{
  "summary": "...",
  "project_type": ["..."],
  "key_technologies": ["..."],
  "target_problem": "...",
  "keywords": ["..."],
  "categories": ["..."]
}}"""

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": f"<start_of_turn>user\n{system_prompt}\n\n{user_prompt}<end_of_turn>\n<start_of_turn>model\n",
                "format": "json",
                "stream": False,
                "keep_alive": "10m",
                "options": {
                    "temperature": 0.0,
                    "num_predict": 400,
                },
            },
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        raw_output = data.get("response", "").strip()

        # Parse JSON output
        parsed = json.loads(raw_output)

        # Normalize summary
        summary = parsed.get("summary")
        if summary and isinstance(summary, str):
            summary = summary.strip()
        else:
            summary = None

        # Normalize project_type
        proj_types = parsed.get("project_type", [])
        if isinstance(proj_types, str):
            proj_types = [p.strip() for p in proj_types.split(",") if p.strip()]
        elif isinstance(proj_types, list):
            proj_types = [str(p).strip() for p in proj_types if str(p).strip()]
        else:
            proj_types = []

        # Normalize key_technologies
        key_techs = parsed.get("key_technologies", [])
        if isinstance(key_techs, str):
            key_techs = [t.strip() for t in key_techs.split(",") if t.strip()]
        elif isinstance(key_techs, list):
            key_techs = [str(t).strip() for t in key_techs if str(t).strip()]
        else:
            key_techs = []

        # Normalize target_problem
        target_problem = parsed.get("target_problem")
        if target_problem and isinstance(target_problem, str):
            target_problem = target_problem.strip()
        else:
            target_problem = None

        keywords = normalize_keywords(parsed.get("keywords"))
        if not keywords:
            keywords = normalize_keywords(existing_keywords) or normalize_keywords(key_techs)

        categories = normalize_categories(parsed.get("categories"), options)
        # Keep registry options aware of invented names for this response
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

    except Exception as exc:
        print(f"⚠️ [Enrichment Warning] LLM enrichment skipped: {exc}")
        return fallback_res
