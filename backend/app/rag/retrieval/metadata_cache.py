import re

from .config import COLLECTION_NAME, client

# Some PDFs wrap the title onto the first line that the old metadata
# extractor considered an author. Do not use those title fragments
# as author filters.
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

        self.author_to_full: dict[str, set[str]] = {}
        self.keyword_to_full: dict[str, set[str]] = {}

        self._loaded = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MetadataCache()

        return cls._instance

    def load_metadata(self):
        if self._loaded:
            return

        print("Loading metadata from Qdrant for auto-filtering...")

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
                    ],
                    with_vectors=False,
                    offset=next_offset,
                )

                for record in records:
                    total_records += 1

                    payload = record.payload

                    if not payload:
                        continue

                    # -------------------------
                    # Project Title
                    # -------------------------
                    if payload.get("project_title"):
                        self.titles.add(
                            payload["project_title"].strip()
                        )

                    if payload.get("title"):
                        self.titles.add(
                            payload["title"].strip()
                        )

                    # -------------------------
                    # Author
                    # -------------------------
                    if payload.get("author"):
                        full_author = payload["author"].strip()

                        # Authors might be comma separated
                        for author in payload["author"].split(","):
                            clean_author = author.strip()

                            if (
                                clean_author
                                and _is_likely_author_name(clean_author)
                            ):
                                self.authors.add(clean_author)

                                if clean_author not in self.author_to_full:
                                    self.author_to_full[clean_author] = set()

                                self.author_to_full[
                                    clean_author
                                ].add(full_author)

                    # -------------------------
                    # Advisor
                    # -------------------------
                    if payload.get("advisor"):
                        self.advisors.add(
                            payload["advisor"].strip()
                        )

                    # -------------------------
                    # Keywords
                    # -------------------------
                    if payload.get("keywords"):
                        full_keyword = payload["keywords"].strip()

                        for keyword in payload["keywords"].split(","):
                            clean_keyword = keyword.strip()

                            if clean_keyword:
                                self.keywords.add(clean_keyword)

                                if (
                                    clean_keyword
                                    not in self.keyword_to_full
                                ):
                                    self.keyword_to_full[clean_keyword] = set()

                                self.keyword_to_full[
                                    clean_keyword
                                ].add(full_keyword)

                # Stop when Qdrant has no more records
                if next_offset is None:
                    break

            self._loaded = True

            print(
                f"Metadata loaded from {total_records} records: "
                f"{len(self.titles)} titles, "
                f"{len(self.authors)} authors, "
                f"{len(self.advisors)} advisors, "
                f"{len(self.keywords)} keywords."
            )

        except (ConnectionError, TimeoutError, OSError, ValueError) as error:
            print(f"Error loading metadata: {error}")

            # Gracefully continue with an empty metadata cache
            # instead of failing the query pipeline.
            self.titles = set()
            self.authors = set()
            self.advisors = set()
            self.keywords = set()

            self.author_to_full = {}
            self.keyword_to_full = {}

            self._loaded = True


metadata_cache = MetadataCache.get_instance()