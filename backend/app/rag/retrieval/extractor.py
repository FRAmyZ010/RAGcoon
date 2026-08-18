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
            for title in sorted(metadata_cache.titles, key=len, reverse=True):
                if len(title) > 3 and title.lower() in clean_query.lower():
                    filters["project_title"] = title
                    pattern = re.compile(re.escape(title), re.IGNORECASE)
                    clean_query = pattern.sub("", clean_query)
                    break

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
                    filters["advisor"] = advisor
                    pattern = re.compile(re.escape(advisor), re.IGNORECASE)
                    clean_query = pattern.sub("", clean_query)
                    break

        if "keywords" not in filters:
            for kw in sorted(metadata_cache.keywords, key=len, reverse=True):
                if len(kw) > 2 and kw.lower() in clean_query.lower():
                    full_strings = list(metadata_cache.keyword_to_full.get(kw, [kw]))
                    filters["keywords"] = full_strings if len(full_strings) > 1 else full_strings[0]
                    pattern = re.compile(re.escape(kw), re.IGNORECASE)
                    clean_query = pattern.sub("", clean_query)
                    break

        if "advisor" not in filters:
            lower_query = clean_query.lower()
            for staff in MFU_STAFF:
                if re.search(r"\b" + re.escape(staff.lower()) + r"\b", lower_query):
                    filters["advisor"] = ADVISOR_EXACT_MAP.get(staff, staff)
                    clean_query = re.sub(r"\b" + re.escape(staff) + r"\b", "", clean_query, flags=re.IGNORECASE)
                    break

        return self.validate_filters(filters)

    @staticmethod
    def normalize_query_text(clean_query: str) -> str:
        """Lowercase and collapse whitespace without re-running metadata extraction."""
        return " ".join(clean_query.split()).lower()

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
