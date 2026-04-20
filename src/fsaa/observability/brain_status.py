"""Socket probe for active-runtime brain status (matches ``turn_token_loop.brain_status``)."""

from __future__ import annotations

import contextlib
import json
import socket
from typing import Any

from fsaa.config.paths import FsaaPaths


def fetch_brain_status_json(
    paths: FsaaPaths,
    *,
    host: str = "127.0.0.1",
    timeout_s: float = 2.0,
) -> dict[str, Any]:
    """Send ``{"type":"status"}\\n`` over TCP; return parsed first JSON object or ``{}``."""
    port = paths.brain_status_port
    sock: socket.socket | None = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_s)
        sock.connect((host, port))
        sock.sendall(b'{"type":"status"}\n')
        data = b""
        while b"\n" not in data:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        if not data:
            return {}
        line = data.split(b"\n", 1)[0].decode("utf-8", errors="replace")
        out = json.loads(line)
        return out if isinstance(out, dict) else {}
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    finally:
        if sock is not None:
            with contextlib.suppress(OSError):
                sock.close()
