import re

from .metadata_cache import metadata_cache

YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")

# Extract key:value or key="value" or key:"value" patterns
# Supports project_title, title, author, advisor, keywords
KV_PATTERN = re.compile(
    r'(?:"?)\b(project_title|title|author|advisor|keywords?)\b(?:"?)\s*[:=]\s*(?:"([^"]+)"|\'([^\']+)\'|([^\s"]+))', 
    re.IGNORECASE
)

# Comprehensive list of MFU ADT Staff / Lecturers based on the directory
# Maps common short names to their possible full formal names or just used for detection
MFU_STAFF = [
    "Nacha", "Worasak", "Pruet", "Paweena", "Kemachart", "Surapol",
    "Shanmugam", "Khwunta", "Pattaramon", "Narong", "Chayapol", "Mahamah",
    "Suppakarn", "Sirikan", "Titiya", "Teeravisit", "Prasara", "Wacharawan",
    "Nang", "Sujitra", "Vittayasak", "Tew", "Nikorn", "Soontarin", "Patcharaporn",
    "Teanjit", "Nilubon", "Waralak", "Charoenchai", "Nontawat", "Yootthapong",
    "Karn", "Thanpahtt", "Banphot", "Ratchanon", "Surapong", "Santichai",
    "Thongchai", "Roungsan", "Punnarumol", "Nattapol", "Tossapon", "Natthakan"
]

# Mapping heuristic names to exact Qdrant values based on metadata_extractor
# Add more mappings here if necessary to match the exact string in the database
ADVISOR_EXACT_MAP = {
    "Mahamah": "Dr. Mahamah Sebakor",
    "Surapol": "Aj. Surapol Vorapatratorn",
    "Tossapon": "Assoc.Prof.Wg.Cdr.Dr.Tossapon Boongoen",
    "Natthakan": "Asst.Prof.Dr.Natthakan Iam-On",
    "Suppakarn": "Asst.Prof.Suppakarn Chansareewittaya",
    "Worasak": "Asst.Prof. Worasak Rueangsirarak",
    "Paweena": "Paweena Suebsombut",
    "Kemachart": "Kemachart Kemavuthanon",
    "Khwunta": "Asst.Prof. Khwunta Kirimasthong",
    "Pattaramon": "Asst.Prof. Pattaramon Vuttipittayamongkol",
    "Shanmugam": "Prof. Shanmugam Nandagopalan",
}

AUTHOR_EXACT_MAP = {
    "teerapat": "TEERAPAT PUANGKANKHAM",
    "teerapatt": "TEERAPAT PUANGKANKHAM",
    "teerapat puangkankham": "TEERAPAT PUANGKANKHAM",
    "teerapatt puangkankham": "TEERAPAT PUANGKANKHAM",
}


def _apply_known_author_aliases(clean_query: str, filters: dict) -> str:
    if "author" in filters:
        return clean_query

    lowered = clean_query.lower()
    for alias, canonical in AUTHOR_EXACT_MAP.items():
        alias_pattern = re.compile(rf"\b{re.escape(alias)}\b", re.IGNORECASE)
        if alias_pattern.search(lowered):
            filters["author"] = canonical
            return alias_pattern.sub("", clean_query, count=1)

    author_pattern = re.compile(r"\bteerapa?t+\b", re.IGNORECASE)
    if author_pattern.search(clean_query):
        filters["author"] = "TEERAPAT PUANGKANKHAM"
        return author_pattern.sub("", clean_query, count=1)

    return clean_query


GENERIC_KEYWORD_WORDS = {
    "tracking", "system", "systems", "python", "iot", "internet", "of", "things",
    "application", "applications", "app", "management", "analysis", "monitoring",
    "design", "development", "security", "learning", "machine", "sensor", "sensors",
    "smart", "online", "service", "algorithm", "model", "detection", "mobile",
    "web", "data", "and", "in", "for", "the", "to", "with", "based", "using",
    "evaluation", "performance", "method", "project", "proposal", "paper", "study",
}

QUERY_STOP_WORDS = GENERIC_KEYWORD_WORDS | {
    "author", "authors", "advisor", "advisors", "committee", "year", "title",
    "paper", "project", "projects", "proposal", "which", "what", "where", "when", "who",
    "whom", "whose", "how", "tell", "show", "give", "retrieve", "find", "list",
    "about", "using", "used", "name", "names", "detail", "details", "information",
    "system", "systems", "development", "application",
}


def _is_generic_keyword(kw: str) -> bool:
    words = [w.strip().lower() for w in re.findall(r"[A-Za-z0-9]+", kw) if w.strip()]
    if not words:
        return True
    # If all words are in generic list
    if all(w in GENERIC_KEYWORD_WORDS for w in words):
        return True
    # Single generic word or too short
    if len(words) == 1 and (words[0] in GENERIC_KEYWORD_WORDS or len(words[0]) <= 3):
        return True
    return False


def _find_matching_project_title(query: str, titles: set[str]) -> tuple[str | None, str]:
    """Find matching project title, supporting exact substring, flexible spaces/punctuation, and parenthesized aliases."""
    query_lower = query.lower()

    # 1. Exact case-insensitive substring match (prioritize longer titles)
    for title in sorted(titles, key=len, reverse=True):
        if len(title) > 3 and title.lower() in query_lower:
            clean_q = re.sub(re.escape(title), "", query, flags=re.IGNORECASE)
            return title, clean_q

    # 2. Check parenthesized acronyms / nicknames (e.g. '(GEM CAR)' in title or '(BLE)')
    for title in sorted(titles, key=len, reverse=True):
        brackets = re.findall(r"\(([^)]+)\)", title)
        for b in brackets:
            b_clean = b.strip()
            if len(b_clean) >= 3 and b_clean.lower() not in QUERY_STOP_WORDS:
                b_compact = re.sub(r"[\s\-_]+", "", b_clean.lower())
                b_words = [re.escape(w) for w in b_clean.split()]
                b_regex = r"\b" + r"[\s\-_]*".join(b_words) + r"\b"

                match = re.search(b_regex, query, re.IGNORECASE)
                if match:
                    clean_q = query[:match.start()] + " " + query[match.end():]
                    return title, clean_q

                compact_match = re.search(rf"\b{re.escape(b_compact)}\b", query_lower)
                if compact_match:
                    clean_q = re.sub(rf"\b{re.escape(b_compact)}\b", "", query, flags=re.IGNORECASE)
                    return title, clean_q

    # 3. Flexible spacing match on the full title
    for title in sorted(titles, key=len, reverse=True):
        words = [re.escape(w) for w in title.split() if w.lower() not in QUERY_STOP_WORDS]
        if len(words) >= 2:
            title_regex = r"\b" + r"[\s\-_]+".join(words[:4]) + r"\b"
            match = re.search(title_regex, query, re.IGNORECASE)
            if match:
                clean_q = query[:match.start()] + " " + query[match.end():]
                return title, clean_q

    # 4. Compact substring matching for merged project name tokens (e.g. 'mfuaccesspointsenergy' in query matches 'MFU ACCESS POINTS ENERGY SAVING')
    # Extract only non-stop-word tokens from query with length >= 6
    query_tokens = [
        w.strip().lower()
        for w in re.findall(r"[A-Za-z0-9]+", query)
        if len(w.strip()) >= 6 and w.strip().lower() not in QUERY_STOP_WORDS
    ]
    for title in sorted(titles, key=len, reverse=True):
        title_compact = re.sub(r"[\s\-_.,/]+", "", title.lower())
        for token in query_tokens:
            if (token in title_compact and len(token) >= 8) or (len(title_compact) >= 8 and title_compact in token):
                clean_q = re.sub(rf"\b{re.escape(token)}\b", "", query, flags=re.IGNORECASE)
                return title, clean_q

    return None, query


class QueryFilterProcessor:
    """Bound the query parsing pipeline: extraction, validation, and query cleanup."""

    def __init__(self, user_query: str):
        self.user_query = user_query

    @staticmethod
    def validate_filters(filters: dict | None) -> dict:
        """Normalize filter values and reject empty values at the boundary."""
        if not filters:
            return {}

        validated: dict = {}
        for key, value in filters.items():
            if value is None:
                continue

            if isinstance(value, list):
                cleaned_values = [str(item).strip() for item in value if item is not None and str(item).strip()]
                if cleaned_values:
                    validated[key] = cleaned_values
            elif isinstance(value, str):
                cleaned_value = value.strip()
                if cleaned_value:
                    validated[key] = cleaned_value
            else:
                validated[key] = value

        return validated

    def extract_filters(self) -> dict:
        """Extract metadata filters from the user query."""
        filters: dict = {}
        clean_query = self.user_query

        for match in KV_PATTERN.finditer(self.user_query):
            key = match.group(1).lower()
            if key == "title":
                key = "project_title"
            elif key == "keyword":
                key = "keywords"

            value = match.group(2) or match.group(3) or match.group(4)
            if not value:
                continue

            if key == "advisor":
                for short_name, exact_name in ADVISOR_EXACT_MAP.items():
                    if short_name.lower() in value.lower():
                        value = exact_name
                        break

            filters[key] = value.strip()
            clean_query = clean_query.replace(match.group(0), "")

        year_match = YEAR_PATTERN.search(clean_query)
        if year_match:
            filters["year"] = year_match.group()
            clean_query = YEAR_PATTERN.sub("", clean_query)

        clean_query = _apply_known_author_aliases(clean_query, filters)

        if not filters:
            metadata_cache.load_metadata()

        if "project_title" not in filters:
            matched_title, clean_query = _find_matching_project_title(clean_query, metadata_cache.titles)
            if matched_title:
                filters["project_title"] = matched_title

        if "author" not in filters:
            for author in sorted(metadata_cache.authors, key=len, reverse=True):
                if len(author) > 3 and author.lower() in clean_query.lower():
                    full_strings = list(metadata_cache.author_to_full.get(author, [author]))
                    filters["author"] = full_strings if len(full_strings) > 1 else full_strings[0]
                    pattern = re.compile(re.escape(author), re.IGNORECASE)
                    clean_query = pattern.sub("", clean_query)
                    break

        if "advisor" not in filters:
            for advisor in sorted(metadata_cache.advisors, key=len, reverse=True):
                if len(advisor) > 3 and advisor.lower() in clean_query.lower():
                    name_words = [w.strip().lower() for w in re.findall(r"[A-Za-z]+", advisor) if len(w.strip()) > 3]
                    variants = set()
                    for nw in name_words:
                        variants.update(metadata_cache.advisor_to_full.get(nw, set()))
                    if not variants:
                        variants = {advisor}
                    filters["advisor"] = list(variants) if len(variants) > 1 else list(variants)[0]
                    pattern = re.compile(re.escape(advisor), re.IGNORECASE)
                    clean_query = pattern.sub("", clean_query)
                    break

        if "keywords" not in filters:
            for kw in sorted(metadata_cache.keywords, key=len, reverse=True):
                # Ignore generic single words or stop words from auto-locking keyword filters
                if _is_generic_keyword(kw):
                    continue

                pattern = re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
                if pattern.search(clean_query):
                    full_strings = list(metadata_cache.keyword_to_full.get(kw, [kw]))
                    filters["keywords"] = full_strings if len(full_strings) > 1 else full_strings[0]
                    clean_query = pattern.sub("", clean_query)
                    break

        if "advisor" not in filters:
            lower_query = clean_query.lower()
            for staff in MFU_STAFF:
                if re.search(r"\b" + re.escape(staff.lower()) + r"\b", lower_query):
                    variants = metadata_cache.advisor_to_full.get(staff.lower(), set())
                    if not variants:
                        exact = ADVISOR_EXACT_MAP.get(staff, staff)
                        variants = {exact}
                    filters["advisor"] = list(variants) if len(variants) > 1 else list(variants)[0]
                    clean_query = re.sub(r"\b" + re.escape(staff) + r"\b", "", clean_query, flags=re.IGNORECASE)
                    break

        return self.validate_filters(filters)

    @staticmethod
    def normalize_query_text(clean_query: str) -> str:
        """Lowercase, strip trailing dangling prepositions/punctuation, and collapse whitespace."""
        cleaned = " ".join(clean_query.split()).lower().strip(" ,;:-_")
        # Strip trailing prepositions leftover from title stripping (e.g. "in", "of", "for", "by", "on", "about", "at", "from", "with", "the")
        cleaned = re.sub(r"\s+\b(in|of|for|by|on|about|at|from|with|the|to|a|an)\b\s*$", "", cleaned, flags=re.IGNORECASE).strip(" ,;:-_")
        return " ".join(cleaned.split()).lower()

    def strip_query_filters(self, filters: dict | None = None) -> str:
        """Remove filter values from the query and keep only the textual search intent."""
        metadata_filters = self.validate_filters(filters) if filters is not None else self.extract_filters()
        clean_query = self.user_query

        for value in metadata_filters.values():
            if value is None:
                continue

            values = value if isinstance(value, list) else [value]
            for item in values:
                if not item:
                    continue
                pattern = re.compile(re.escape(str(item)), re.IGNORECASE)
                clean_query = pattern.sub("", clean_query, count=1)

        if "year" in metadata_filters:
            clean_query = YEAR_PATTERN.sub("", clean_query)

        return self.normalize_query_text(clean_query)

    def parse(self) -> tuple[str, dict]:
        """One-pass pipeline: extract filters, then clean the remaining query."""
        filters = self.extract_filters()
        clean_query = self.strip_query_filters(filters)
        return clean_query, filters


def extract_filters(user_query: str) -> dict:
    """Backward-compatible function wrapper for the processor."""
    return QueryFilterProcessor(user_query).extract_filters()


def normalize_query_text(clean_query: str) -> str:
    """Backward-compatible alias for the processor's text-normalization step."""
    return QueryFilterProcessor.normalize_query_text(clean_query)


def strip_query_filters(user_query: str, filters: dict | None) -> str:
    """Backward-compatible function wrapper for query cleanup."""
    return QueryFilterProcessor(user_query).strip_query_filters(filters)


def extract_query(user_query: str, filters: dict | None = None) -> str:
    """Backward-compatible query-cleaning wrapper."""
    if filters is not None:
        return QueryFilterProcessor(user_query).strip_query_filters(filters)
    return QueryFilterProcessor(user_query).parse()[0]


def parse_query(user_query: str) -> tuple[str, dict]:
    """Fast one-pass parser: extract filters once, then strip them from the query once."""
    return QueryFilterProcessor(user_query).parse()


def extract_query_and_filters(user_query: str) -> tuple[str, dict]:
    """Backward-compatible wrapper that keeps the old combined API."""
    return parse_query(user_query)
