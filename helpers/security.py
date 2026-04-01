import re

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
    ]
    if any(re.search(pattern, q_low) for pattern in blocked_patterns):
        return False

    # WHERE obligatoire.
    match = re.search(r"\bwhere\b(.+)", q, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return False

    where_clause = match.group(1)

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
        if re.search(
            r"^\s*orders(?:\s+(?:as\s+)?\w+)?\s*$",
            from_clause,
            flags=re.IGNORECASE | re.DOTALL,
        ) is None:
            return False

    # Le WHERE doit contenir le user_id authentifié.
    pattern = rf"(?:\b\w+\.)?\buser_id\s*=\s*{user_id}\b"
    if re.search(pattern, where_clause, flags=re.IGNORECASE) is None:
        return False

    # Rejeter si d'autres user_id sont présents.
    found_user_ids = re.findall(
        r"(?:\b\w+\.)?\buser_id\s*=\s*(\d+)\b",
        where_clause,
        flags=re.IGNORECASE,
    )
    if any(int(found) != user_id for found in found_user_ids):
        return False

    # JOIN strictement limité à "orders <alias> JOIN users <alias>".
    if join_count == 1:
        join_match = re.search(
            r"""
            ^\s*orders\s+(?:as\s+)?(?P<orders_alias>\w+)\s+
            join\s+users\s+(?:as\s+)?(?P<users_alias>\w+)\s+
            on\s+.+$
            """,
            from_clause,
            flags=re.IGNORECASE | re.DOTALL | re.VERBOSE,
        )
        if not join_match:
            return False

        orders_alias = join_match.group("orders_alias")
        users_alias = join_match.group("users_alias")

        orders_filter_pattern = rf"\b{re.escape(orders_alias)}\.user_id\s*=\s*{user_id}\b"
        users_filter_pattern = rf"\b{re.escape(users_alias)}\.user_id\s*=\s*{user_id}\b"
        if re.search(orders_filter_pattern, where_clause, flags=re.IGNORECASE) is None:
            return False
        if re.search(users_filter_pattern, where_clause, flags=re.IGNORECASE) is None:
            return False

    return True
