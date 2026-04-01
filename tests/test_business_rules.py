from business_rules import (
    forced_message_delivered_without_date,
    forced_message_invoiced_not_shipped,
    forced_message_shipped_not_delivered,
    get_forced_business_message,
)


def test_get_forced_business_message_shipped_without_delivery_date():
    result = get_forced_business_message(
        "Quand vais-je recevoir ma commande ?",
        [{"order_id": 11, "status": "shipped", "date_delivered": None}],
    )

    assert result == "Votre commande a bien été expédiée, mais elle n'a pas encore été livrée."


def test_get_forced_business_message_invoiced_not_shipped():
    result = get_forced_business_message(
        "Où en est la livraison de ma commande ?",
        [{"order_id": 11, "status": "invoiced", "date_shipped": None}],
    )

    assert result == "Votre commande est payée et validée, mais elle n'a pas encore été expédiée."


def test_get_forced_business_message_delivered_without_date():
    result = get_forced_business_message(
        "Mon colis est-il livré ?",
        [{"order_id": 11, "status": "delivered", "date_delivered": None}],
    )

    assert (
        result
        == "Les informations de livraison sont incomplètes. Un conseiller humain va prendre le relais."
    )


def test_get_forced_business_message_returns_none_for_non_delivery_question():
    result = get_forced_business_message(
        "Quel est l'état du paiement ?",
        [{"order_id": 11, "status": "shipped", "date_delivered": None}],
    )

    assert result is None


def test_case_function_shipped_not_delivered():
    result = forced_message_shipped_not_delivered(
        {"status": "shipped", "date_delivered": None},
        is_delivery=True,
    )
    assert result == "Votre commande a bien été expédiée, mais elle n'a pas encore été livrée."


def test_case_function_invoiced_not_shipped():
    result = forced_message_invoiced_not_shipped(
        {"status": "invoiced", "date_shipped": None},
        is_delivery=True,
    )
    assert result == "Votre commande est payée et validée, mais elle n'a pas encore été expédiée."


def test_case_function_delivered_without_date():
    result = forced_message_delivered_without_date(
        {"status": "delivered", "date_delivered": None},
        is_delivery=True,
    )
    assert (
        result
        == "Les informations de livraison sont incomplètes. Un conseiller humain va prendre le relais."
    )
