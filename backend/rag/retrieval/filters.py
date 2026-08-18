from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue


def build_qdrant_filter(filters: dict | None) -> Filter | None:
    if not filters:
        return None

    conditions = []
    for key, value in filters.items():
        if isinstance(value, list):
            conditions.append(FieldCondition(key=key, match=MatchAny(any=value)))
        else:
            conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

    return Filter(must=conditions)
