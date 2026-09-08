from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

from .metadata_cache import metadata_cache


def build_qdrant_filter(filters: dict | None) -> Filter | None:
    if not filters:
        return None

    metadata_cache.load_metadata()
    conditions = []

    VALID_FILTER_KEYS = {"author", "advisor", "year", "project_title"}

    for key, value in filters.items():
        if key not in VALID_FILTER_KEYS:
            continue
        if value is None or value == "" or value == []:
            continue

        if key == "author":
            author_list = value if isinstance(value, list) else [value]
            all_matching_payloads = set()
            for auth in author_list:
                auth_str = str(auth).strip()
                if not auth_str:
                    continue
                full_authors = (
                    metadata_cache.author_to_full.get(auth_str)
                    or metadata_cache.author_to_full.get(auth_str.lower())
                )
                if full_authors:
                    all_matching_payloads.update(full_authors)
                else:
                    all_matching_payloads.add(auth_str)

            if len(all_matching_payloads) == 1:
                conditions.append(FieldCondition(key="author", match=MatchValue(value=list(all_matching_payloads)[0])))
            elif len(all_matching_payloads) > 1:
                conditions.append(FieldCondition(key="author", match=MatchAny(any=list(all_matching_payloads))))

        elif key == "advisor":
            advisor_list = value if isinstance(value, list) else [value]
            all_matching_advisors = set()
            for adv in advisor_list:
                adv_str = str(adv).strip()
                if not adv_str:
                    continue
                full_advisors = (
                    metadata_cache.advisor_to_full.get(adv_str)
                    or metadata_cache.advisor_to_full.get(adv_str.lower())
                )
                if full_advisors:
                    all_matching_advisors.update(full_advisors)
                else:
                    all_matching_advisors.add(adv_str)

            if len(all_matching_advisors) == 1:
                conditions.append(FieldCondition(key="advisor", match=MatchValue(value=list(all_matching_advisors)[0])))
            elif len(all_matching_advisors) > 1:
                conditions.append(FieldCondition(key="advisor", match=MatchAny(any=list(all_matching_advisors))))

        elif isinstance(value, list):
            conditions.append(FieldCondition(key=key, match=MatchAny(any=value)))
        else:
            conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

    return Filter(must=conditions) if conditions else None


