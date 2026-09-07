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
                        full_advisor = payload["advisor"].strip()
                        self.advisors.add(full_advisor)
                        for key in (full_advisor, full_advisor.lower()):
                            if key not in self.advisor_to_full:
                                self.advisor_to_full[key] = set()
                            self.advisor_to_full[key].add(full_advisor)

                        name_words = [
                            w.strip().lower()
                            for w in re.findall(r"[A-Za-z]+", full_advisor)
                            if len(w.strip()) > 3 and w.lower() not in {"prof", "asst", "assoc", "lecturer", "doctor", "aj"}
                        ]
                        for nw in name_words:
                            if nw not in self.advisor_to_full:
                                self.advisor_to_full[nw] = set()
                            self.advisor_to_full[nw].add(full_advisor)

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