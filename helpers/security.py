import re
from typing import Optional


def _strip_sql_tail_clauses(where_clause: str) -> str:
    tail_match = re.search(
        r"\b(group\s+by|order\s+by|having|limit)\b",
        where_clause,
        flags=re.IGNORECASE,
    )
    if tail_match:
        return where_clause[: tail_match.start()].strip()
    return where_clause.strip()


def _split_and_conditions(where_clause: str) -> list[str]:
    return [
        condition.strip().strip("()").strip()
        for condition in re.split(r"\band\b", where_clause, flags=re.IGNORECASE)
        if condition.strip()
    ]


def _matches_user_id_filter(condition: str, qualifier: Optional[str], user_id: int) -> bool:
    if qualifier is None:
        pattern = rf"user_id\s*=\s*{user_id}\b"
    else:
        pattern = rf"{re.escape(qualifier)}\.user_id\s*=\s*{user_id}\b"

    return re.fullmatch(pattern, condition, flags=re.IGNORECASE) is not None


def _count_required_user_filter(
    conditions: list[str],
    qualifiers: tuple[Optional[str], ...],
    user_id: int,
) -> int:
    return sum(
        1
        for condition in conditions
        if any(
            _matches_user_id_filter(condition, qualifier, user_id)
            for qualifier in qualifiers
        )
    )


def _has_only_allowed_user_id_conditions(
    conditions: list[str],
    qualifiers: tuple[Optional[str], ...],
    user_id: int,
) -> bool:
    for condition in conditions:
        if re.search(r"\buser_id\b", condition, flags=re.IGNORECASE) is None:
            continue

        if not any(
            _matches_user_id_filter(condition, qualifier, user_id)
            for qualifier in qualifiers
        ):
            return False

    return True


def is_valid_user_sql_query(sql_query: str, user_id: int) -> bool:
    q = sql_query.strip()
    q_low = q.lower()

    # Requête de lecture uniquement.
    if not q_low.startswith("select"):
        return False

    # Patterns de contournement/injection les plus courants.
    blocked_patterns = [
        r"--",
        r"/\*",
        r"\*/",
        r";",
        r"\bunion\b",
        r"\bor\b",
        r"\bwith\b",
        r"\binsert\b",
        r"\bupdate\b",
        r"\bdelete\b",
        r"\bdrop\b",
        r"\balter\b",
        r"\btruncate\b",
        r"\blimit\b",
    ]
    if any(re.search(pattern, q_low) for pattern in blocked_patterns):
        return False

    # WHERE obligatoire.
    match = re.search(r"\bwhere\b(.+)", q, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return False

    where_clause = _strip_sql_tail_clauses(match.group(1))
    conditions = _split_and_conditions(where_clause)
    if not conditions:
        return False

    # Sous-requêtes interdites (surface d'attaque trop large).
    if re.search(r"\(\s*select\b", q_low):
        return False

    from_match = re.search(r"\bfrom\b(.+?)\bwhere\b", q, flags=re.IGNORECASE | re.DOTALL)
    if not from_match:
        return False

    from_clause = from_match.group(1)
    normalized_from = re.sub(r"\s+", " ", from_clause.strip().lower())

    # Pas de multi-table implicite.
    if "," in normalized_from:
        return False

    join_count = len(re.findall(r"\bjoin\b", normalized_from))
    if join_count > 1:
        return False

    # Sans JOIN: uniquement la table orders (avec ou sans alias).
    if join_count == 0:
        orders_match = re.search(
            r"^\s*orders(?:\s+(?:as\s+)?(?P<orders_alias>\w+))?\s*$",
            from_clause,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if orders_match is None:
            return False

        orders_alias = orders_match.group("orders_alias")
        allowed_qualifiers = tuple(dict.fromkeys((None, "orders", orders_alias)))

        if not _has_only_allowed_user_id_conditions(
            conditions,
            allowed_qualifiers,
            user_id,
        ):
            return False

        if _count_required_user_filter(conditions, allowed_qualifiers, user_id) != 1:
            return False

    # JOIN strictement limité à "orders <alias> JOIN users <alias>".
    if join_count == 1:
        join_match = re.search(
            r"""
            ^\s*orders\s+(?:as\s+)?(?P<orders_alias>\w+)\s+
            join\s+users\s+(?:as\s+)?(?P<users_alias>\w+)\s+
            on\s+(?P<on_clause>.+)$
            """,
            from_clause,
            flags=re.IGNORECASE | re.DOTALL | re.VERBOSE,
        )
        if not join_match:
            return False

        orders_alias = join_match.group("orders_alias")
        users_alias = join_match.group("users_alias")
        on_clause = re.sub(r"\s+", " ", join_match.group("on_clause").strip())

        valid_on_patterns = (
            rf"{re.escape(users_alias)}\.user_id\s*=\s*{re.escape(orders_alias)}\.user_id",
            rf"{re.escape(orders_alias)}\.user_id\s*=\s*{re.escape(users_alias)}\.user_id",
        )
        if not any(
            re.fullmatch(pattern, on_clause, flags=re.IGNORECASE)
            for pattern in valid_on_patterns
        ):
            return False

        allowed_qualifiers = (orders_alias, users_alias)
        if not _has_only_allowed_user_id_conditions(
            conditions,
            allowed_qualifiers,
            user_id,
        ):
            return False

        if _count_required_user_filter(conditions, (orders_alias,), user_id) != 1:
            return False

        if _count_required_user_filter(conditions, (users_alias,), user_id) != 1:
            return False

    return True
