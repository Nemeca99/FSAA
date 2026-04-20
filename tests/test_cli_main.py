from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from fsaa.cli import main as cli_main


def test_validate_policy_subcommand(monkeypatch: pytest.MonkeyPatch) -> None:
    assert cli_main.main(["validate-policy"]) == 0


def test_verify_subcommand(monkeypatch: pytest.MonkeyPatch) -> None:
    mock = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr("fsaa.cli.main.subprocess.run", mock)
    assert cli_main.main(["verify"]) == 0
