import re
from .config import COLLECTION_NAME, client

_NON_NAME_WORDS = {
    "and",
    "attack",
    "computer",
    "cybersecurity",
    "development",
    "energy",
    "for",
    "in",
    "low",
    "of",
    "system",
    "the",
    "wlan",
}

_TITLE_WORDS = {
    "prof",
    "professor",
    "asst",
    "assoc",
    "lecturer",
    "doctor",
    "dr",
    "aj",
    "phd",
    "wg",
    "cdr",
}


def _clean_name_spacing(name: str | None) -> str | None:
    """Clean missing spaces after dots and in CamelCase/TitleCase words from OCR/PDF."""
    if not name or not isinstance(name, str):
        return name
    cleaned = name.strip(" .:-()[]")
    cleaned = re.sub(r"\.([A-Za-z])", r". \1", cleaned)
    cleaned = re.sub(r"([a-z])([A-Z])", r"\1 \2", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .:-")
    return cleaned or None


def _is_likely_author_name(value: str) -> bool:
    words = re.findall(r"[A-Za-z]+", value)
    return (
        len(words) >= 2
        and not any(word.lower() in _NON_NAME_WORDS for word in words)
    )


class MetadataCache:
    _instance = None

    def __init__(self):
        self.titles: set[str] = set()
        self.authors: set[str] = set()
        self.advisors: set[str] = set()
        self.keywords: set[str] = set()
        self.years: set[str] = set()

        self.author_to_full: dict[str, set[str]] = {}
        self.advisor_to_full: dict[str, set[str]] = {}
        self.keyword_to_full: dict[str, set[str]] = {}

        self._loaded = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MetadataCache()
        return cls._instance

    def resolve_advisor_variants(self, advisor_input: str) -> set[str]:
        """
        Map any advisor string (e.g. 'Aj. Surapol Vorapatratorn', 'Dr. Surapol', 'Surapol')
        to all matching advisor name variants stored in Qdrant payloads.
        """
        self.load_metadata()
        if not advisor_input or not str(advisor_input).strip():
            return set()

        adv_clean = _clean_name_spacing(str(advisor_input).strip()) or str(advisor_input).strip()
        raw_words = re.findall(r"[A-Za-z]+", adv_clean)
        core_words = [
            w.lower() for w in raw_words
            if len(w) >= 3 and w.lower() not in _TITLE_WORDS
        ]

        matching_variants: set[str] = set()

        if core_words:
            for known_adv in self.advisors:
                known_clean = _clean_name_spacing(known_adv) or known_adv
                known_raw_words = re.findall(r"[A-Za-z]+", known_clean)
                known_core_words = {
                    w.lower() for w in known_raw_words
                    if len(w) >= 3 and w.lower() not in _TITLE_WORDS
                }
                if all(cw in known_core_words for cw in core_words):
                    matching_variants.add(known_adv)
                elif len(core_words) == 1 and any(cw in known_core_words for cw in core_words):
                    matching_variants.add(known_adv)
                elif any(cw in known_adv.lower() for cw in core_words):
                    matching_variants.add(known_adv)

        if matching_variants:
            return matching_variants

        mapped = self.advisor_to_full.get(adv_clean) or self.advisor_to_full.get(adv_clean.lower())
        if mapped:
            return set(mapped)

        return {adv_clean}

    def resolve_author_variants(self, author_input: str) -> set[str]:
        """
        Map author query/input to all matching author string payloads in Qdrant.
        """
        self.load_metadata()
        if not author_input or not str(author_input).strip():
            return set()

        auth_clean = str(author_input).strip()
        direct = self.author_to_full.get(auth_clean) or self.author_to_full.get(auth_clean.lower())
        if direct:
            return set(direct)

        raw_words = re.findall(r"[A-Za-z]+", auth_clean)
        core_words = [
            w.lower() for w in raw_words
            if len(w) >= 3 and w.lower() not in _NON_NAME_WORDS
        ]
        matches: set[str] = set()
        for cw in core_words:
            mapped = self.author_to_full.get(cw)
            if mapped:
                matches.update(mapped)

        return matches or {auth_clean}


    def refresh(self):
        """Force refresh the metadata cache directly from Qdrant."""
        self._loaded = False
        self.titles.clear()
        self.authors.clear()
        self.advisors.clear()
        self.keywords.clear()
        self.years.clear()
        self.author_to_full.clear()
        self.advisor_to_full.clear()
        self.keyword_to_full.clear()
        self.load_metadata()

    def load_metadata(self):
        if self._loaded:
            return

        print("Loading dynamic metadata from Qdrant for auto-filtering...")

        try:
            next_offset = None
            total_records = 0

            while True:
                records, next_offset = client.scroll(
                    collection_name=COLLECTION_NAME,
                    limit=10000,
                    with_payload=[
                        "project_title",
                        "title",
                        "author",
                        "advisor",
                        "keywords",
                        "year",
                    ],
                    with_vectors=False,
                    offset=next_offset,
                )

                for record in records:
                    total_records += 1
                    payload = record.payload
                    if not payload:
                        continue

                    # Project Title
                    if payload.get("project_title"):
                        self.titles.add(payload["project_title"].strip())
                    if payload.get("title"):
                        self.titles.add(payload["title"].strip())

                    # Author
                    if payload.get("author"):
                        full_author = payload["author"].strip()
                        for author in payload["author"].split(","):
                            clean_author = author.strip()
                            if clean_author and _is_likely_author_name(clean_author):
                                self.authors.add(clean_author)
                                for key in (clean_author, clean_author.lower()):
                                    if key not in self.author_to_full:
                                        self.author_to_full[key] = set()
                                    self.author_to_full[key].add(full_author)

                                # Map individual words (first name / last name)
                                for word in re.findall(r"[A-Za-z]+", clean_author):
                                    w_lower = word.lower()
                                    if len(w_lower) >= 3 and w_lower not in _NON_NAME_WORDS:
                                        if w_lower not in self.author_to_full:
                                            self.author_to_full[w_lower] = set()
                                        self.author_to_full[w_lower].add(full_author)

                    # Advisor
                    if payload.get("advisor"):
                        raw_advisor = payload["advisor"].strip()
                        cleaned_advisor = _clean_name_spacing(raw_advisor) or raw_advisor
                        self.advisors.add(raw_advisor)
                        self.advisors.add(cleaned_advisor)
                        for key in (raw_advisor, raw_advisor.lower(), cleaned_advisor, cleaned_advisor.lower()):
                            if key not in self.advisor_to_full:
                                self.advisor_to_full[key] = set()
                            self.advisor_to_full[key].add(raw_advisor)
                            self.advisor_to_full[key].add(cleaned_advisor)

                        name_words = [
                            w.strip().lower()
                            for w in re.findall(r"[A-Za-z]+", cleaned_advisor)
                            if len(w.strip()) >= 3 and w.lower() not in _TITLE_WORDS
                        ]
                        for nw in name_words:
                            if nw not in self.advisor_to_full:
                                self.advisor_to_full[nw] = set()
                            self.advisor_to_full[nw].add(raw_advisor)
                            self.advisor_to_full[nw].add(cleaned_advisor)

                    # Keywords
                    if payload.get("keywords"):
                        full_keyword = payload["keywords"].strip()
                        for keyword in payload["keywords"].split(","):
                            clean_keyword = keyword.strip()
                            if clean_keyword:
                                self.keywords.add(clean_keyword)
                                if clean_keyword not in self.keyword_to_full:
                                    self.keyword_to_full[clean_keyword] = set()
                                self.keyword_to_full[clean_keyword].add(full_keyword)

                    # Year
                    if payload.get("year"):
                        year_val = str(payload["year"]).strip()
                        if year_val:
                            self.years.add(year_val)

                if next_offset is None:
                    break

            self._loaded = True
            print(
                f"Dynamic metadata loaded: {len(self.titles)} titles, "
                f"{len(self.authors)} authors, "
                f"{len(self.advisors)} advisors, "
                f"{len(self.years)} years."
            )

        except Exception as error:
            print(f"Error loading metadata from Qdrant: {error}")
            self.titles = set()
            self.authors = set()
            self.advisors = set()
            self.keywords = set()
            self.years = set()
            self._loaded = True


metadata_cache = MetadataCache.get_instance()