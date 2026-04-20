"""Brain status socket probe (mocked)."""

from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

from fsaa.config.paths import get_paths
from fsaa.observability.brain_status import fetch_brain_status_json


def test_fetch_brain_status_parses_first_json_line() -> None:
    paths = get_paths()
    fake_sock = MagicMock()
    fake_sock.recv = MagicMock(side_effect=[b'{"beat": 3, "ok": true}\n', b""])

    with patch.object(socket, "socket", return_value=fake_sock):
        out = fetch_brain_status_json(paths, timeout_s=1.0)
    assert out.get("beat") == 3
    fake_sock.sendall.assert_called_once_with(b'{"type":"status"}\n')
