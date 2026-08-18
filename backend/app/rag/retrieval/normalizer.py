import os
import re
from dataclasses import dataclass
from functools import lru_cache

try:
    from rapidfuzz import fuzz, process
except ImportError:
    fuzz = None
    process = None

Verbosity = None
_sym_spell = None

try:
    import pkg_resources  # type: ignore
    from symspellpy import SymSpell, Verbosity

    _sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
    _dictionary_path = pkg_resources.resource_filename(
        "symspellpy", "frequency_dictionary_en_82_765.txt"
    )
    _sym_spell.load_dictionary(_dictionary_path, term_index=0, count_index=1)
except (ImportError, ModuleNotFoundError):
    _sym_spell = None


SYNONYMS = {
    "ce": "computer engineering",
    "cpe": "computer engineering",
    "se": "software engineering",
    "db": "database",
}

FUZZY_CORRECTION_TERMS = (
    "methodology",
    "pet feeder",
)
FUZZY_SCORE_CUTOFF = 88
EDGE_PUNCTUATION = "\"'`.,;:!?()[]{}<>"
ASCII_LETTER_PATTERN = re.compile(r"[a-z]")
WORD_PATTERN = re.compile(r"\S+")
TERM_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
METADATA_FIELDS = ("project_title", "author", "advisor")
METADATA_SCROLL_PAGE_SIZE = int(os.getenv("NORMALIZER_METADATA_PAGE_SIZE", "100"))
METADATA_MAX_POINTS = int(os.getenv("NORMALIZER_METADATA_MAX_POINTS", "1000"))
METADATA_STOPWORDS = {
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "the",
    "to",
    "using",
    "with",
}


@dataclass(frozen=True)
class QueryToken:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class MetadataProtection:
    phrases: frozenset[str]
    tokens: frozenset[str]


def _collapse_whitespace(query: str) -> str:
    return " ".join(query.strip().split())


def _tokenize(query: str) -> list[str]:
    return [token.text for token in _tokenize_with_spans(query)]


def _tokenize_with_spans(query: str) -> list[QueryToken]:
    tokens = []
    for match in WORD_PATTERN.finditer(query):
        raw_token = match.group()
        cleaned = raw_token.strip(EDGE_PUNCTUATION)
        if not cleaned:
            continue

        leading_punctuation = len(raw_token) - len(raw_token.lstrip(EDGE_PUNCTUATION))
        trailing_punctuation = len(raw_token) - len(raw_token.rstrip(EDGE_PUNCTUATION))
        start = match.start() + leading_punctuation
        end = match.end() - trailing_punctuation
        tokens.append(QueryToken(text=cleaned, start=start, end=end))

    return tokens


def _metadata_term_tokens(term: str) -> set[str]:
    return {
        token
        for token in TERM_TOKEN_PATTERN.findall(term.lower())
        if len(token) > 2 and token not in METADATA_STOPWORDS
    }


def _metadata_value_to_terms(value: object) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        terms = []
        for item in value:
            terms.extend(_metadata_value_to_terms(item))
        return terms

    term = _collapse_whitespace(str(value)).lower()
    return [term] if term else []


def _fetch_metadata_terms_from_qdrant() -> list[str]:
    try:
        from .config import COLLECTION_NAME, client

        terms = []
        offset = None
        points_seen = 0
        page_size = max(1, METADATA_SCROLL_PAGE_SIZE)
        max_points = max(0, METADATA_MAX_POINTS)

        while points_seen < max_points:
            points, offset = client.scroll(
                collection_name=COLLECTION_NAME,
                limit=min(page_size, max_points - points_seen),
                offset=offset,
                with_payload=list(METADATA_FIELDS),
                with_vectors=False,
            )

            if not points:
                break

            points_seen += len(points)
            for point in points:
                payload = point.payload or {}
                for field in METADATA_FIELDS:
                    terms.extend(_metadata_value_to_terms(payload.get(field)))

            if offset is None:
                break

        return terms
    except (ConnectionError, RuntimeError, TimeoutError):
        return []


@lru_cache(maxsize=1)
def _load_metadata_protection() -> MetadataProtection:
    phrases = set()
    tokens = set()

    # Add MFU staff names as protected terms to prevent fuzzy correction from damaging them
    try:
        from .extractor import ADVISOR_EXACT_MAP, MFU_STAFF

        protected_advisor_terms = list(ADVISOR_EXACT_MAP.keys()) + list(
            ADVISOR_EXACT_MAP.values()
        )
        for term in protected_advisor_terms:
            phrases.add(term.lower())
            tokens.update(_metadata_term_tokens(term))
        for staff in MFU_STAFF:
            phrases.add(staff.lower())
            tokens.update(_metadata_term_tokens(staff))
    except (ImportError, ModuleNotFoundError):
        # Continue without extra advisor protection if extractor not available
        pass

    for term in _fetch_metadata_terms_from_qdrant():
        phrases.add(term)
        tokens.update(_metadata_term_tokens(term))

    return MetadataProtection(
        phrases=frozenset(phrases),
        tokens=frozenset(tokens),
    )


def _token_parts(token: str) -> set[str]:
    return set(TERM_TOKEN_PATTERN.findall(token.lower()))


def _is_protected_token(token: QueryToken, protected_terms: MetadataProtection) -> bool:
    token_parts = _token_parts(token.text)
    return any(part in protected_terms.tokens for part in token_parts)


def _protected_token_indexes(
    query: str,
    tokens: list[QueryToken],
    protected_terms: MetadataProtection,
) -> set[int]:
    protected_indexes = {
        index
        for index, token in enumerate(tokens)
        if _is_protected_token(token, protected_terms)
    }

    for phrase in protected_terms.phrases:
        if len(phrase) < 3:
            continue

        phrase_pattern = re.compile(
            rf"(?<!\w){re.escape(phrase)}(?!\w)",
            flags=re.IGNORECASE,
        )
        for match in phrase_pattern.finditer(query):
            for index, token in enumerate(tokens):
                if token.start >= match.start() and token.end <= match.end():
                    protected_indexes.add(index)

    return protected_indexes


def _apply_synonyms(
    query: str,
    protected_terms: MetadataProtection,
) -> str:
    tokens = _tokenize_with_spans(query)
    protected_indexes = _protected_token_indexes(query, tokens, protected_terms)

    normalized_tokens = []
    for index, token in enumerate(tokens):
        if index in protected_indexes:
            normalized_tokens.append(token.text)
        else:
            normalized_tokens.append(SYNONYMS.get(token.text, token.text))

    return " ".join(normalized_tokens)


def _correct_token(token: str, protected_terms: MetadataProtection, protected: bool = False) -> str:
    if protected:
        return token

    if token.isdigit() or len(token) <= 2:
        return token

    if not ASCII_LETTER_PATTERN.search(token):
        return token

    if process and fuzz and protected_terms.tokens:
        best_match = process.extractOne(token, protected_terms.tokens, scorer=fuzz.ratio)
        if best_match and best_match[1] >= 85:
            return best_match[0]

    if _sym_spell and Verbosity:
        suggestions = _sym_spell.lookup(
            token, Verbosity.CLOSEST, max_edit_distance=2
        )
        if suggestions:
            return suggestions[0].term

    return token


def _apply_fuzzy_corrections(
    query: str,
    protected_terms: MetadataProtection,
) -> str:
    tokens = _tokenize_with_spans(query)
    protected_indexes = _protected_token_indexes(query, tokens, protected_terms)

    return " ".join(
        _correct_token(token.text, protected_terms, protected=index in protected_indexes)
        for index, token in enumerate(tokens)
    )


def normalize_user_query(query: str) -> str:
    protected_terms = _load_metadata_protection()
    lowered = _collapse_whitespace(query).lower()
    synonym_expanded = _apply_synonyms(lowered, protected_terms)
    return _apply_fuzzy_corrections(synonym_expanded, protected_terms)
