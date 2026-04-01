import sys
import os
from helpers.security import is_valid_user_sql_query
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_valid_filter_simple():
    sql = "SELECT * FROM orders WHERE user_id = 32"
    assert is_valid_user_sql_query(sql, 32) is True

def test_valid_filter_with_alias():
    sql = "SELECT * FROM orders o WHERE o.user_id = 32 AND o.status = 'shipped'"
    assert is_valid_user_sql_query(sql, 32) is True

def test_missing_where():
    sql = "SELECT * FROM orders"
    assert is_valid_user_sql_query(sql, 32) is False

def test_wrong_user():
    sql = "SELECT * FROM orders WHERE user_id = 33"
    assert is_valid_user_sql_query(sql, 32) is False

def test_or_true_blocked():
    sql = "SELECT * FROM orders WHERE user_id = 32 OR 1=1"
    assert is_valid_user_sql_query(sql, 32) is False

def test_or_other_user_blocked():
    sql = "SELECT * FROM orders WHERE user_id = 32 OR user_id = 33"
    assert is_valid_user_sql_query(sql, 32) is False

def test_union_injection_blocked():
    sql = (
        "SELECT * FROM orders WHERE user_id = 32 "
        "UNION SELECT order_id, user_id, status, date_purchase, date_shipped, date_delivered FROM orders"
    )
    assert is_valid_user_sql_query(sql, 32) is False

def test_multiple_statements_blocked():
    sql = "SELECT * FROM orders WHERE user_id = 32; SELECT * FROM users"
    assert is_valid_user_sql_query(sql, 32) is False

def test_sql_comments_blocked():
    sql = "SELECT * FROM orders WHERE user_id = 32 -- force ignore checks"
    assert is_valid_user_sql_query(sql, 32) is False

def test_valid_strict_orders_users_join_with_aliases():
    sql = (
        "SELECT o.order_id, u.address, u.city, u.zip_code "
        "FROM orders o "
        "JOIN users u ON u.user_id = o.user_id "
        "WHERE o.user_id = 32 AND u.user_id = 32"
    )
    assert is_valid_user_sql_query(sql, 32) is True

def test_reject_orders_self_join_even_with_authenticated_filter():
    sql = (
        "SELECT a.order_id, b.user_id "
        "FROM orders a "
        "JOIN orders b ON 1=1 "
        "WHERE a.user_id = 32"
    )
    assert is_valid_user_sql_query(sql, 32) is False

def test_reject_join_without_users_alias_filter():
    sql = (
        "SELECT o.order_id, u.address "
        "FROM orders o "
        "JOIN users u ON 1=1 "
        "WHERE o.user_id = 32"
    )
    assert is_valid_user_sql_query(sql, 32) is False
