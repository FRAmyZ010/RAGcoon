"""Deprecated regex keyword→group map.

Primary category assignment is LLM + category_registry.
This module remains only for legacy imports/tests.
"""

from .category_registry import SEED_CATEGORIES

GROUPS = (
    ("Hardware", ("esp32", "esp8266", "nodemcu", "arduino", "sensor", "rfid", "raspberry", "sx1276", "gpio")),
    ("Web", ("react", "web application", "web app", "javascript", "frontend", "bootstrap", "html", "css")),
    ("Machine learning", ("machine learning", "random forest", "logistic regression", "neural", "classification")),
    ("Network", ("access point", "wifi", "wi-fi", "wlan", "lora", "cisco", "netmiko", "mqtt")),
    ("Database", ("mysql", "postgres", "postgresql", "sql", "database", "python")),
)
GROUP_ORDER = list(SEED_CATEGORIES)


def groups_for_keywords(raw: str | None) -> str:
    """Legacy helper — no longer used on the ingest primary path."""
    if not raw or not str(raw).strip():
        return ""
    found: list[str] = []
    for part in str(raw).split(","):
        folded = part.strip().casefold()
        if not folded:
            continue
        matched = False
        for name, needles in GROUPS:
            if any(needle in folded for needle in needles):
                matched = True
                if name not in found:
                    found.append(name)
        if not matched and "Other" not in found:
            found.append("Other")
    return ", ".join(found)
