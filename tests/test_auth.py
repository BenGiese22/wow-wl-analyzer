# tests/test_auth.py
import pytest
from unittest.mock import patch, MagicMock
from src.auth import get_access_token


def _mock_response(status_code: int, json_body: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def test_get_access_token_success():
    mock_resp = _mock_response(200, {"access_token": "tok123", "token_type": "Bearer"})
    with patch("requests.post", return_value=mock_resp) as mock_post:
        token = get_access_token("my-id", "my-secret")
    assert token == "tok123"
    call_kwargs = mock_post.call_args[1]
    assert call_kwargs["auth"] == ("my-id", "my-secret")
    assert call_kwargs["data"] == {"grant_type": "client_credentials"}


def test_get_access_token_invalid_credentials():
    mock_resp = _mock_response(401, {"error": "unauthorized"})
    with patch("requests.post", return_value=mock_resp):
        with pytest.raises(ValueError, match="Invalid WCL credentials"):
            get_access_token("bad", "creds")


def test_get_access_token_server_error():
    mock_resp = _mock_response(500, {})
    with patch("requests.post", return_value=mock_resp):
        with pytest.raises(Exception):
            get_access_token("id", "secret")
