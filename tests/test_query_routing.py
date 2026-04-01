from helpers.query_routing import (
    classify_query_from_scores,
    classify_user_query,
)


def test_classify_query_from_scores_returns_best_label_when_clear():
    scores = {
        "order_info": 0.91,
        "order_help": 0.51,
        "out_of_scope": 0.18,
    }

    assert classify_query_from_scores(scores) == "order_info"


def test_classify_query_from_scores_returns_out_of_scope_when_below_threshold():
    scores = {
        "order_info": 0.55,
        "order_help": 0.40,
        "out_of_scope": 0.12,
    }

    assert classify_query_from_scores(scores, threshold=0.62) == "out_of_scope"


def test_classify_query_from_scores_returns_out_of_scope_when_ambiguous_margin():
    scores = {
        "order_info": 0.80,
        "order_help": 0.77,
        "out_of_scope": 0.10,
    }

    assert classify_query_from_scores(scores, threshold=0.62, margin=0.08) == "out_of_scope"


def test_classify_query_from_scores_forces_out_of_scope_when_best_label_is_out_of_scope():
    scores = {
        "order_info": 0.50,
        "order_help": 0.40,
        "out_of_scope": 0.95,
    }

    assert classify_query_from_scores(scores) == "out_of_scope"


def test_classify_user_query_builds_scores_with_encoder_and_similarity_function():
    example_embeddings = {
        "order_info": "emb_order_info",
        "order_help": "emb_order_help",
        "out_of_scope": "emb_out_of_scope",
    }

    calls = {"encode": 0, "sim": []}

    def fake_encode(query: str):
        calls["encode"] += 1
        assert query == "Où en est ma commande ?"
        return "query_embedding"

    def fake_max_similarity(query_embedding, embeddings):
        calls["sim"].append((query_embedding, embeddings))
        score_map = {
            "emb_order_info": 0.88,
            "emb_order_help": 0.42,
            "emb_out_of_scope": 0.31,
        }
        return score_map[embeddings]

    result = classify_user_query(
        "Où en est ma commande ?",
        encode_query=fake_encode,
        example_embeddings=example_embeddings,
        max_similarity=fake_max_similarity,
    )

    assert result == "order_info"
    assert calls["encode"] == 1
    assert len(calls["sim"]) == 3
