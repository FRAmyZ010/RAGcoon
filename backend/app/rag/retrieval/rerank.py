import math
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
    scores = get_reranker().predict(pairs, show_progress_bar=False, batch_size=32)

    scored = list(zip(docs_with_payload, scores))
    ranked = sorted(scored, key=lambda item: item[1], reverse=True)
    top_ranked = ranked[:top_n]

    best_raw = float(top_ranked[0][1]) if top_ranked else -99.0

    # If the absolute best chunk has a deeply negative cross-encoder score (< -3.5),
    # the documents are genuinely irrelevant to the query (less than 3% semantic probability).
    # Use calibrated sigmoid probability instead of boosting the highest irrelevant chunk to 1.0.
    if best_raw < -3.5:
        return [
            {
                "text": item["text"],
                "score": float(1.0 / (1.0 + math.exp(-float(score)))),
                "raw_score": float(score),
                "payload": item["payload"],
            }
            for (item, score) in top_ranked
        ]

    norm_scores = normalize_scores([float(score) for _, score in top_ranked])

    return [
        {
            "text": item["text"],
            "score": float(norm),
            "raw_score": float(score),
            "payload": item["payload"],
        }
        for (item, score), norm in zip(top_ranked, norm_scores)
    ]

