# tests/test_setup.py
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO


def test_setup_writes_env_file(tmp_path):
    mock_char = {"name": "Bêngi", "class_id": 4, "class_name": "Mage"}
    inputs = ["client-id", "Bêngi", "Illidan", "US", "1", "10", "18"]
    with patch("builtins.input", side_effect=iter(inputs)), \
         patch("getpass.getpass", return_value="secret123"), \
         patch("src.auth.get_access_token", return_value="tok"), \
         patch("src.character.lookup_character", return_value=mock_char), \
         patch("src.character.get_specs_for_class", return_value=["Arcane", "Fire", "Frost"]), \
         patch("src.report.console"), \
         patch("pathlib.Path.write_text") as mock_write:
        import importlib, analyze
        importlib.reload(analyze)
        from analyze import cmd_setup
        cmd_setup(MagicMock(), env_path=str(tmp_path / ".env"))
    mock_write.assert_called_once()
    written = mock_write.call_args[0][0]
    assert "Bêngi" in written
    assert "Mage" in written
    assert "Arcane" in written
    assert "encoding" in str(mock_write.call_args)


def test_setup_invalid_credentials_exits(tmp_path):
    with patch("builtins.input", side_effect=iter(["bad-id"])), \
         patch("getpass.getpass", return_value="bad-secret"), \
         patch("src.auth.get_access_token", side_effect=ValueError("Invalid WCL credentials")), \
         patch("src.report.console"), \
         pytest.raises(SystemExit):
        import analyze
        from analyze import cmd_setup
        cmd_setup(MagicMock(), env_path=str(tmp_path / ".env"))
