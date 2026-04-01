from helpers.business_rules import (
    ensure_order_business_columns,
    forced_message_delivered_without_date,
    forced_message_invoiced_not_shipped,
    forced_message_order_status,
    forced_message_payment_status,
    forced_message_shipped_not_delivered,
    get_forced_business_message,
    normalize_generated_sql_for_business_rules,
)


def test_ensure_order_business_columns_adds_required_fields_without_alias():
    sql = "SELECT date_shipped FROM orders WHERE user_id = 32"

    result = ensure_order_business_columns(sql)

    assert "SELECT date_shipped, orders.order_id AS order_id" in result
    assert "orders.status AS status" in result
    assert "orders.date_purchase AS date_purchase" in result
    assert "orders.date_delivered AS date_delivered" in result
    assert result.endswith("FROM orders WHERE user_id = 32")


def test_ensure_order_business_columns_does_not_duplicate_existing_fields():
    sql = "SELECT order_id, status FROM orders WHERE user_id = 32"

    result = ensure_order_business_columns(sql)

    assert result.count("order_id") == 1
    assert result.count("status") == 1
    assert "orders.date_purchase AS date_purchase" in result
    assert "orders.date_shipped AS date_shipped" in result
    assert "orders.date_delivered AS date_delivered" in result


def test_ensure_order_business_columns_uses_orders_alias():
    sql = "SELECT o.date_shipped FROM orders o WHERE o.user_id = 32"

    result = ensure_order_business_columns(sql)

    assert "o.order_id AS order_id" in result
    assert "o.status AS status" in result
    assert "o.date_delivered AS date_delivered" in result


def test_ensure_order_business_columns_uses_orders_alias_in_join():
    sql = (
        "SELECT u.address "
        "FROM orders o JOIN users u ON u.user_id = o.user_id "
        "WHERE o.user_id = 32 AND u.user_id = 32"
    )

    result = ensure_order_business_columns(sql)

    assert "SELECT u.address, o.order_id AS order_id" in result
    assert "o.status AS status" in result
    assert "o.date_delivered AS date_delivered" in result
    assert "JOIN users u ON u.user_id = o.user_id" in result


def test_ensure_order_business_columns_leaves_unmatched_sql_unchanged():
    sql = "SELECT user_id FROM users WHERE user_id = 32"

    assert ensure_order_business_columns(sql) == sql


def test_get_forced_business_message_shipped_without_delivery_date():
    result = get_forced_business_message(
        "Quand vais-je recevoir ma commande ?",
        [{"order_id": 11, "status": "shipped", "date_delivered": None}],
    )

    assert (
        result
        == "Votre commande a bien été expédiée, mais aucune date de livraison n'est disponible pour le moment."
    )


def test_get_forced_business_message_detects_livree_formulation():
    result = get_forced_business_message(
        "Quand ma commande sera-t-elle livrée ?",
        [{"order_id": 11, "status": "shipped", "date_delivered": None}],
    )

    assert (
        result
        == "Votre commande a bien été expédiée, mais aucune date de livraison n'est disponible pour le moment."
    )


def test_get_forced_business_message_detects_expediee_formulation():
    result = get_forced_business_message(
        "Ma commande est-elle expédiée ?",
        [{"order_id": 11, "status": "shipped", "date_delivered": None}],
    )

    assert (
        result
        == "Votre commande a bien été expédiée, mais aucune date de livraison n'est disponible pour le moment."
    )


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
        "Donne-moi un résumé de ma commande",
        [{"order_id": 11, "status": "shipped", "date_delivered": None}],
    )

    assert result is None


def test_get_forced_business_message_payment_status():
    result = get_forced_business_message(
        "Quel est l'état du paiement ?",
        [{"order_id": 11, "status": "shipped"}],
    )

    assert result == "Votre commande est payée et a été expédiée."


def test_get_forced_business_message_order_status_with_date():
    result = get_forced_business_message(
        "Quel est le statut de ma commande ?",
        [{"order_id": 11, "status": "shipped", "date_shipped": "2024-05-31 10:53:38"}],
    )

    assert (
        result
        == "Votre commande a été expédiée le 31 mai 2024, mais elle n'a pas encore été livrée."
    )


def test_normalize_generated_sql_removes_invalid_delivery_status_filter():
    sql = (
        "SELECT order_id, date_delivered FROM orders "
        "WHERE user_id = 1 AND status = 'en attente de livraison' ORDER BY date_purchase DESC"
    )

    result = normalize_generated_sql_for_business_rules(
        "Quand vais-je recevoir ma commande ?",
        sql,
    )

    assert "en attente de livraison" not in result
    assert result == (
        "SELECT order_id, date_delivered FROM orders "
        "WHERE user_id = 1 ORDER BY date_purchase DESC"
    )


def test_normalize_generated_sql_keeps_valid_status_filter():
    sql = "SELECT order_id FROM orders WHERE user_id = 1 AND status = 'delivered'"

    result = normalize_generated_sql_for_business_rules(
        "Quelles commandes sont déjà livrées ?",
        sql,
    )

    assert result == sql


def test_case_function_shipped_not_delivered():
    result = forced_message_shipped_not_delivered(
        {"status": "shipped", "date_delivered": None},
        is_delivery=True,
    )
    assert (
        result
        == "Votre commande a bien été expédiée, mais aucune date de livraison n'est disponible pour le moment."
    )


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


def test_case_function_payment_status():
    result = forced_message_payment_status(
        {"status": "delivered"},
        is_payment=True,
    )
    assert result == "Votre commande est payée et a été livrée."


def test_case_function_order_status():
    result = forced_message_order_status(
        {"status": "invoiced"},
        is_status=True,
    )
    assert result == "Votre commande est payée et validée, mais elle n'a pas encore été expédiée."
