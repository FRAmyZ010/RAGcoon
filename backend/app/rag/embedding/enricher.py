import json
import os
import re
from typing import Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")


STANDARD_SYSTEM_TYPES = {
    "iot": "IoT & Hardware",
    "hardware": "IoT & Hardware",
    "embedded": "IoT & Hardware",
    "embedded systems": "IoT & Hardware",
    "robotics": "IoT & Hardware",
    "web": "Web Application",
    "website": "Web Application",
    "web app": "Web Application",
    "web application": "Web Application",
    "network": "Network & Wireless",
    "networking": "Network & Wireless",
    "wireless": "Network & Wireless",
    "wireless communication": "Network & Wireless",
    "wireless lan": "Network & Wireless",
    "mobile": "Mobile Application",
    "mobile app": "Mobile Application",
    "ai": "AI & Machine Learning",
    "machine learning": "AI & Machine Learning",
    "deep learning": "AI & Machine Learning",
    "computer vision": "AI & Machine Learning",
    "cybersecurity": "Cybersecurity",
    "security": "Cybersecurity",
}


def infer_system_categories(text: str, title: str | None = None) -> list[str]:
    """Rule-based system category inference fallback."""
    combined = f"{title or ''} {text}".lower()
    categories = []

    # IoT & Hardware
    if any(k in combined for k in [
        "iot", "sensor", "sensors", "arduino", "esp32", "esp8266", "microcontroller",
        "robot", "hardware", "actuator", "watering", "flow meter", "beacon", "rfid",
        "เซนเซอร์", "ไมโครคอนโทรลเลอร์", "ฮาร์ดแวร์", "บอร์ด", "อุปกรณ์",
    ]):
        categories.append("IoT & Hardware")

    # Network & Wireless
    if any(k in combined for k in [
        "network", "wireless", "wlan", "wifi", "wi-fi", "cisco", "lora", "lorawan",
        "ble", "bluetooth", "access point", "ap map", "ssid", "sdn", "เครือข่าย", "ไร้สาย",
    ]):
        categories.append("Network & Wireless")

    # Web Application
    if any(k in combined for k in [
        "web application", "website", "web app", "web portal", "dashboard", "frontend",
        "backend", "react", "html", "php", "mysql", "stock management", "booking", "เว็บ",
    ]):
        categories.append("Web Application")

    # Mobile Application
    if any(k in combined for k in [
        "mobile app", "mobile application", "android", "ios", "smartphone", "แอปมือถือ", "โมบาย",
    ]):
        categories.append("Mobile Application")

    # AI & Machine Learning
    if any(k in combined for k in [
        "machine learning", "deep learning", "computer vision", "image processing",
        "prediction", "predict", "model", "neural", "classification", "logo detection",
        "ปัญญาประดิษฐ์",
    ]):
        categories.append("AI & Machine Learning")

    # Cybersecurity
    if any(k in combined for k in [
        "cybersecurity", "penetration testing", "vulnerability", "malicious", "attack",
        "security", "dark web", "ความปลอดภัย", "เจาะระบบ",
    ]):
        categories.append("Cybersecurity")

    return list(dict.fromkeys(categories)) if categories else ["General Software"]


def extract_project_enrichment(
    text: str,
    project_title: Optional[str] = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """
    Use lightweight local LLM to extract high-impact metadata:
      - summary (1-2 sentences)
      - project_type (standardized list of system types: IoT & Hardware, Web Application, Network & Wireless, Mobile Application, AI & Machine Learning, Cybersecurity)
      - key_technologies (list of tools/technologies, e.g. NodeMCU, RFID, MySQL)
      - target_problem (1 sentence problem statement)
    """
    fallback_categories = infer_system_categories(text, project_title)
    fallback_res: dict[str, Any] = {
        "summary": None,
        "project_type": fallback_categories,
        "key_technologies": [],
        "target_problem": None,
    }

    if not text or not str(text).strip():
        return fallback_res

    clean_text = text.strip()[:3500]

    system_prompt = (
        "You are a Senior Project Analysis Engine. Analyze the following senior project abstract/document excerpt "
        "and determine what kind of system it is (e.g. IoT, Web, Network, Mobile, AI/ML, Cybersecurity). "
        "You MUST respond with ONLY a valid JSON object matching the requested schema."
    )

    user_prompt = f"""Project Title: {project_title or 'Senior Project'}

Document Excerpt:
{clean_text}

Analyze the project and extract structured metadata:
1. "summary": A concise 1-2 sentence overview in the primary language of the text describing what the project does and how it works.
2. "project_type": A JSON array of 1-3 primary system types that best characterize what kind of system this is. Choose from standard categories:
   - "IoT & Hardware" (Sensors, Microcontrollers, Arduino, ESP32, Robotics, Beacons, Smart Devices)
   - "Web Application" (Websites, Web Portals, Dashboards, REST APIs, Web Management Systems)
   - "Network & Wireless" (WLAN, Wi-Fi, Cisco, LoRaWAN, BLE, Network Automation, Infrastructure)
   - "Mobile Application" (Android Apps, iOS Apps, Smartphone Location Tracking)
   - "AI & Machine Learning" (Image Processing, Computer Vision, Prediction Models, Machine Learning)
   - "Cybersecurity" (Penetration Testing, Vulnerability Assessment, Malicious Detection)
3. "key_technologies": A JSON array of specifically mentioned technologies, frameworks, microcontrollers, sensors, or databases (e.g. ["NodeMCU ESP8266", "RFID", "MySQL", "React"]).
4. "target_problem": A concise 1-sentence statement of the main real-world problem or pain point this project solves.

JSON Format:
{{
  "summary": "...",
  "project_type": ["IoT & Hardware", "Web Application"],
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

        # Normalize project_type and map to standard categories
        proj_types = parsed.get("project_type", [])
        if isinstance(proj_types, str):
            proj_types = [p.strip() for p in proj_types.split(",") if p.strip()]
        elif isinstance(proj_types, list):
            proj_types = [str(p).strip() for p in proj_types if str(p).strip()]
        else:
            proj_types = []

        standardized_types = []
        for pt in proj_types:
            pt_clean = pt.strip()
            pt_low = pt_clean.lower()
            std = STANDARD_SYSTEM_TYPES.get(pt_low, pt_clean)
            if std not in standardized_types:
                standardized_types.append(std)

        if not standardized_types:
            standardized_types = fallback_categories

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
            "project_type": standardized_types,
            "key_technologies": key_techs,
            "target_problem": target_problem,
        }

    except Exception as exc:
        print(f"⚠️ [Enrichment Warning] LLM enrichment skipped: {exc}")
        return fallback_res

