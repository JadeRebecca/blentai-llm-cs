import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


BUSINESS_ORDER_COLUMNS = (
    "order_id",
    "status",
    "date_purchase",
    "date_shipped",
    "date_delivered",
)

DELIVERY_KEYWORDS = ("livr", "recu", "reçu", "recev", "colis", "expédi", "exped")
PAYMENT_KEYWORDS = ("paiement", "payé", "payee", "payée", "payer", "factur")
STATUS_KEYWORDS = ("statut", "etat", "état", "ou en est", "où en est")
ORDER_STATUS_VALUES = ("invoiced", "shipped", "delivered")
MONTHS_FR = {
    1: "janvier",
    2: "février",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "août",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "décembre",
}


def _format_date(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None

    for date_format in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed_date = datetime.strptime(value, date_format)
            return (
                f"{parsed_date.day} "
                f"{MONTHS_FR[parsed_date.month]} "
                f"{parsed_date.year}"
            )
        except ValueError:
            continue

    return value


def _split_select_items(select_clause: str) -> list[str]:
    items = []
    current = []
    depth = 0

    for character in select_clause:
        if character == "(":
            depth += 1
        elif character == ")" and depth > 0:
            depth -= 1
        elif character == "," and depth == 0:
            items.append("".join(current).strip())
            current = []
            continue

        current.append(character)

    if current:
        items.append("".join(current).strip())

    return items


def _selected_output_names(select_clause: str) -> set[str]:
    selected_names = set()

    for item in _split_select_items(select_clause):
        normalized_item = re.sub(r"\s+", " ", item.strip())
        lowered_item = normalized_item.lower()

        if lowered_item in {"*", "orders.*"} or re.fullmatch(r"\w+\.\*", lowered_item):
            selected_names.update(BUSINESS_ORDER_COLUMNS)
            continue

        alias_match = re.search(
            r"\bas\s+([a-zA-Z_]\w*)\s*$",
            normalized_item,
            flags=re.IGNORECASE,
        )
        if alias_match:
            selected_names.add(alias_match.group(1).lower())
            continue

        column_match = re.search(r"(?:\b\w+\.)?([a-zA-Z_]\w*)\s*$", normalized_item)
        if column_match:
            selected_names.add(column_match.group(1).lower())

    return selected_names


def _extract_orders_qualifier(from_clause: str) -> Optional[str]:
    normalized_from = re.sub(r"\s+", " ", from_clause.strip())

    join_match = re.fullmatch(
        r"orders\s+(?:as\s+)?(?P<orders_alias>\w+)\s+join\s+users\s+(?:as\s+)?\w+\s+on\s+.+",
        normalized_from,
        flags=re.IGNORECASE,
    )
    if join_match:
        return join_match.group("orders_alias")

    orders_match = re.fullmatch(
        r"orders(?:\s+(?:as\s+)?(?P<orders_alias>\w+))?",
        normalized_from,
        flags=re.IGNORECASE,
    )
    if orders_match:
        return orders_match.group("orders_alias") or "orders"

    return None


def ensure_order_business_columns(sql_query: str) -> str:
    match = re.search(
        r"^\s*select\s+(?P<select_clause>.+?)\s+from\s+(?P<from_clause>.+?)\s+where\s+(?P<where_clause>.+?)\s*$",
        sql_query,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        return sql_query

    orders_qualifier = _extract_orders_qualifier(match.group("from_clause"))
    if orders_qualifier is None:
        return sql_query

    selected_names = _selected_output_names(match.group("select_clause"))
    missing_columns = [
        column
        for column in BUSINESS_ORDER_COLUMNS
        if column.lower() not in selected_names
    ]
    if not missing_columns:
        return sql_query

    business_select_clause = ", ".join(
        f"{orders_qualifier}.{column} AS {column}"
        for column in missing_columns
    )

    return (
        f"SELECT {match.group('select_clause').strip()}, {business_select_clause} "
        f"FROM {match.group('from_clause').strip()} "
        f"WHERE {match.group('where_clause').strip()}"
    )


def is_delivery_question(query: str) -> bool:
    lowered_query = query.lower()
    return any(keyword in lowered_query for keyword in DELIVERY_KEYWORDS)


def is_payment_question(query: str) -> bool:
    lowered_query = query.lower()
    return any(keyword in lowered_query for keyword in PAYMENT_KEYWORDS)


def is_status_question(query: str) -> bool:
    lowered_query = query.lower()
    return any(keyword in lowered_query for keyword in STATUS_KEYWORDS)


def normalize_generated_sql_for_business_rules(query: str, sql_query: str) -> str:
    if not is_delivery_question(query):
        return sql_query

    def replace_invalid_status_filter(match: re.Match[str]) -> str:
        status_value = match.group("status").lower()
        if status_value in ORDER_STATUS_VALUES:
            return match.group(0)
        return ""

    return re.sub(
        r"\s+and\s+(?:\w+\.)?status\s*=\s*'(?P<status>[^']+)'",
        replace_invalid_status_filter,
        sql_query,
        flags=re.IGNORECASE,
    )


def forced_message_shipped_not_delivered(
    row: Dict[str, Any], *, is_delivery: bool
) -> Optional[str]:
    if not is_delivery:
        return None

    status_value = row.get("status")
    delivered_value = row.get("date_delivered")
    if isinstance(status_value, str) and status_value.lower() == "shipped" and delivered_value is None:
        return (
            "Votre commande a bien été expédiée, mais aucune date de livraison "
            "n'est disponible pour le moment."
        )
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


def forced_message_payment_status(
    row: Dict[str, Any], *, is_payment: bool
) -> Optional[str]:
    if not is_payment:
        return None

    status_value = row.get("status")
    if not isinstance(status_value, str):
        return None

    normalized_status = status_value.lower()
    if normalized_status == "invoiced":
        return (
            "Votre commande est payée et validée, mais elle n'a pas encore été "
            "expédiée."
        )
    if normalized_status == "shipped":
        return "Votre commande est payée et a été expédiée."
    if normalized_status == "delivered":
        return "Votre commande est payée et a été livrée."

    return None


def forced_message_order_status(
    row: Dict[str, Any], *, is_status: bool
) -> Optional[str]:
    if not is_status:
        return None

    status_value = row.get("status")
    if not isinstance(status_value, str):
        return None

    normalized_status = status_value.lower()
    if normalized_status == "invoiced":
        return (
            "Votre commande est payée et validée, mais elle n'a pas encore été "
            "expédiée."
        )

    if normalized_status == "shipped":
        shipped_date = _format_date(row.get("date_shipped"))
        if shipped_date:
            return (
                f"Votre commande a été expédiée le {shipped_date}, mais elle "
                "n'a pas encore été livrée."
            )
        return "Votre commande a été expédiée, mais elle n'a pas encore été livrée."

    if normalized_status == "delivered":
        delivered_date = _format_date(row.get("date_delivered"))
        if delivered_date:
            return f"Votre commande a été livrée le {delivered_date}."
        return "Votre commande a été livrée."

    return None


def get_forced_business_message(query: str, sql_result: List[Any]) -> Optional[str]:
    is_delivery = is_delivery_question(query)
    is_payment = is_payment_question(query)
    is_status = is_status_question(query) and not is_delivery and not is_payment

    handlers: tuple[Callable[[Dict[str, Any]], Optional[str]], ...] = (
        lambda row: forced_message_payment_status(row, is_payment=is_payment),
        lambda row: forced_message_order_status(row, is_status=is_status),
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
