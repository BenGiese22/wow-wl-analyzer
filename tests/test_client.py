# tests/test_client.py
import pytest
from unittest.mock import patch, MagicMock
from src.client import query


def _mock_resp(status: int, body: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return resp


def test_query_returns_data():
    resp = _mock_resp(200, {"data": {"worldData": {"expansions": []}}})
    with patch("requests.post", return_value=resp):
        result = query("tok", "{ worldData { expansions { id } } }")
    assert result == {"worldData": {"expansions": []}}


def test_query_sends_bearer_token():
    resp = _mock_resp(200, {"data": {}})
    with patch("requests.post", return_value=resp) as mock_post:
        query("mytoken", "{ rateLimitData { limitPerHour } }")
    headers = mock_post.call_args[1]["headers"]
    assert headers["Authorization"] == "Bearer mytoken"


def test_query_raises_on_graphql_errors():
    body = {"errors": [{"message": "Field not found"}, {"message": "Type mismatch"}]}
    resp = _mock_resp(200, body)
    with patch("requests.post", return_value=resp):
        with pytest.raises(RuntimeError, match="Field not found"):
            query("tok", "{ bad }")


def test_query_raises_on_http_error():
    resp = _mock_resp(500, {})
    with patch("requests.post", return_value=resp):
        with pytest.raises(Exception):
            query("tok", "{ worldData { expansions { id } } }")


def test_query_sends_variables():
    resp = _mock_resp(200, {"data": {"result": "ok"}})
    with patch("requests.post", return_value=resp) as mock_post:
        query("tok", "query ($id: Int!) { foo(id: $id) }", {"id": 42})
    payload = mock_post.call_args[1]["json"]
    assert payload["variables"] == {"id": 42}
