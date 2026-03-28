import re

def has_valid_user_filter(sql_query: str, user_id: int) -> bool:
    # 🔒 1. Bloquer les OR dangereux
    if re.search(r"\bor\b\s+1\s*=\s*1", sql_query, re.IGNORECASE):
        return False
    # 1. Extraire la clause WHERE
    match = re.search(r"\bwhere\b(.+)", sql_query, flags=re.IGNORECASE)
    if not match:
        return False

    where_clause = match.group(1)

    # 2. Vérifier user_id dans le WHERE
    pattern = rf"(?:\b\w+\.)?\buser_id\s*=\s*{user_id}\b"

    return re.search(pattern, where_clause, flags=re.IGNORECASE) is not None
