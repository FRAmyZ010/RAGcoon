import json
import os
import re
from typing import Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")


def extract_project_enrichment(
    text: str,
    project_title: Optional[str] = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """
    Use lightweight local LLM to extract high-impact metadata:
      - summary (1-2 sentences)
      - project_type (list of categories, e.g. IoT & Hardware, Web Application)
      - key_technologies (list of tools/technologies, e.g. NodeMCU, RFID, MySQL)
      - target_problem (1 sentence problem statement)
    """
    fallback_res: dict[str, Any] = {
        "summary": None,
        "project_type": [],
        "key_technologies": [],
        "target_problem": None,
    }

    if not text or not str(text).strip():
        return fallback_res

    clean_text = text.strip()[:3500]

    system_prompt = (
        "You are a Senior Project Analysis Engine. Analyze the following project abstract/document excerpt "
        "and extract structured metadata. You MUST respond with ONLY a valid JSON object matching the requested schema."
    )

    user_prompt = f"""Project Title: {project_title or 'Senior Project'}

Document Excerpt:
{clean_text}

Extract the following 4 fields into valid JSON:
1. "summary": A concise 1-2 sentence overview in the primary language of the text describing what the project does and how it works.
2. "project_type": A JSON array of 1-3 broad categories (e.g. ["IoT & Hardware", "Web Application", "Mobile App", "AI & Machine Learning", "Cybersecurity", "Network"]).
3. "key_technologies": A JSON array of specifically mentioned technologies, frameworks, microcontrollers, sensors, or databases (e.g. ["NodeMCU ESP8266", "RFID", "MySQL", "React"]).
4. "target_problem": A concise 1-sentence statement of the main real-world problem or pain point this project solves.

JSON Format:
{{
  "summary": "...",
  "project_type": ["..."],
  "key_technologies": ["..."],
  "target_problem": "..."
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
                    "num_predict": 300,
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

        return {
            "summary": summary,
            "project_type": proj_types,
            "key_technologies": key_techs,
            "target_problem": target_problem,
        }

    except Exception as exc:
        print(f"⚠️ [Enrichment Warning] LLM enrichment skipped: {exc}")
        return fallback_res
