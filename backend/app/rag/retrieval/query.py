import re
from typing import Dict, Tuple


YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")


def normalize_query(query: str) -> str:
    normalized = " ".join(query.strip().split())

    replacements = {
        "methology": "methodology",
        "methodolgy": "methodology",
        "petfeeder": "pet feeder",
    }

    lowered = normalized.lower()
    for src, tgt in replacements.items():
        lowered = lowered.replace(src, tgt)

    return lowered


def extract_query_and_filters(user_query: str) -> Tuple[str, Dict]:
    filters = {}

    year_match = YEAR_PATTERN.search(user_query)
    if year_match:
        filters["year"] = year_match.group()

    clean_query = YEAR_PATTERN.sub("", user_query).strip()
    return clean_query, filters
