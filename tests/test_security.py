import sys
import os
from security import has_valid_user_filter
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_valid_filter_simple():
    sql = "SELECT * FROM orders WHERE user_id = 32"
    assert has_valid_user_filter(sql, 32) is True

def test_valid_filter_with_alias():
    sql = "SELECT * FROM orders o WHERE o.user_id = 32 AND o.status = 'shipped'"
    assert has_valid_user_filter(sql, 32) is True

def test_missing_where():
    sql = "SELECT * FROM orders"
    assert has_valid_user_filter(sql, 32) is False

def test_wrong_user():
    sql = "SELECT * FROM orders WHERE user_id = 33"
    assert has_valid_user_filter(sql, 32) is False

def test_or_true_blocked():
    sql = "SELECT * FROM orders WHERE user_id = 32 OR 1=1"
    assert has_valid_user_filter(sql, 32) is False