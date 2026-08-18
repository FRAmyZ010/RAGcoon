from .config import get_reranker


def normalize_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []

    min_s = min(scores)
    max_s = max(scores)

    if max_s - min_s == 0:
        return [1.0 for _ in scores]

    return [(score - min_s) / (max_s - min_s) for score in scores]


def rerank(query: str, docs_with_payload: list[dict], top_n: int) -> list[dict]:
    if not docs_with_payload:
        return []

    docs = [doc["text"] for doc in docs_with_payload]
    pairs = [[query, doc] for doc in docs]
    scores = get_reranker().predict(pairs)

    scored = list(zip(docs_with_payload, scores))
    ranked = sorted(scored, key=lambda item: item[1], reverse=True)
    top_ranked = ranked[:top_n]
    norm_scores = normalize_scores([float(score) for _, score in top_ranked])

    return [
        {"text": item["text"], "score": float(norm), "payload": item["payload"]}
        for (item, _), norm in zip(top_ranked, norm_scores)
    ]
