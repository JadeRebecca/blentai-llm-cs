from typing import Any, Callable, Dict, List, Optional


DELIVERY_KEYWORDS = ("livrai", "recu", "reçu", "recev", "colis")


def is_delivery_question(query: str) -> bool:
    lowered_query = query.lower()
    return any(keyword in lowered_query for keyword in DELIVERY_KEYWORDS)


def forced_message_shipped_not_delivered(
    row: Dict[str, Any], *, is_delivery: bool
) -> Optional[str]:
    if not is_delivery:
        return None

    status_value = row.get("status")
    delivered_value = row.get("date_delivered")
    if isinstance(status_value, str) and status_value.lower() == "shipped" and delivered_value is None:
        return "Votre commande a bien été expédiée, mais elle n'a pas encore été livrée."
    return None


def forced_message_invoiced_not_shipped(
    row: Dict[str, Any], *, is_delivery: bool
) -> Optional[str]:
    if not is_delivery:
        return None

    status_value = row.get("status")
    shipped_value = row.get("date_shipped")
    if isinstance(status_value, str) and status_value.lower() == "invoiced" and shipped_value is None:
        return "Votre commande est payée et validée, mais elle n'a pas encore été expédiée."
    return None


def forced_message_delivered_without_date(
    row: Dict[str, Any], *, is_delivery: bool
) -> Optional[str]:
    if not is_delivery:
        return None

    status_value = row.get("status")
    delivered_value = row.get("date_delivered")
    if isinstance(status_value, str) and status_value.lower() == "delivered" and delivered_value is None:
        return "Les informations de livraison sont incomplètes. Un conseiller humain va prendre le relais."
    return None


def get_forced_business_message(query: str, sql_result: List[Any]) -> Optional[str]:
    is_delivery = is_delivery_question(query)

    handlers: tuple[Callable[[Dict[str, Any]], Optional[str]], ...] = (
        lambda row: forced_message_shipped_not_delivered(row, is_delivery=is_delivery),
        lambda row: forced_message_invoiced_not_shipped(row, is_delivery=is_delivery),
        lambda row: forced_message_delivered_without_date(row, is_delivery=is_delivery),
    )

    for row in sql_result:
        if not isinstance(row, dict):
            continue
        for handler in handlers:
            message = handler(row)
            if message is not None:
                return message

    return None
