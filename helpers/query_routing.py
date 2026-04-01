from typing import Any, Callable, Mapping


def classify_query_from_scores(
    scores: Mapping[str, float],
    *,
    threshold: float = 0.62,
    margin: float = 0.08,
) -> str:
    if not scores:
        return "out_of_scope"

    best_label = max(scores, key=scores.get)
    best_score = float(scores[best_label])
    sorted_scores = sorted((float(value) for value in scores.values()), reverse=True)
    second_best = sorted_scores[1] if len(sorted_scores) > 1 else 0.0

    # Si la meilleure classe est hors scope, on bloque directement.
    if best_label == "out_of_scope":
        return "out_of_scope"

    # Trop faible ou trop ambigu -> hors périmètre.
    if best_score < threshold:
        return "out_of_scope"

    if (best_score - second_best) < margin:
        return "out_of_scope"

    return best_label


def classify_user_query(
    query: str,
    *,
    encode_query: Callable[[str], Any],
    example_embeddings: Mapping[str, Any],
    max_similarity: Callable[[Any, Any], float],
    threshold: float = 0.62,
    margin: float = 0.08,
) -> str:
    query_embedding = encode_query(query)

    scores = {
        label: float(max_similarity(query_embedding, embeddings))
        for label, embeddings in example_embeddings.items()
    }

    return classify_query_from_scores(scores, threshold=threshold, margin=margin)


def make_classify_user_query(
    *,
    embedding_model: Any,
    example_embeddings: Mapping[str, Any],
    util_module: Any,
) -> Callable[[str, float, float], str]:
    def classifyUserQuery(
        query: str,
        threshold: float = 0.62,
        margin: float = 0.08,
    ) -> str:
        return classify_user_query(
            query,
            encode_query=lambda q: embedding_model.encode(
                q,
                convert_to_tensor=True,
                normalize_embeddings=True,
            ),
            example_embeddings=example_embeddings,
            max_similarity=lambda query_emb, embeddings: float(
                util_module.cos_sim(query_emb, embeddings)[0].max()
            ),
            threshold=threshold,
            margin=margin,
        )

    return classifyUserQuery
