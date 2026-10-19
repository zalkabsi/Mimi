"""Shared test setup: import path and a no-network guard.

Tests run from the repo root as::

    python -m pytest backend/tests -q

so ``backend/`` is put on ``sys.path`` here to make ``import mimi`` work.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fail loudly if anything resolves a remote name or opens a remote socket.

    Loopback stays allowed (Windows event loops build a local socketpair for
    their wakeup pipe); anything that would leave the machine is blocked.
    """
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _host(address) -> str:
        if isinstance(address, tuple) and address:
            return str(address[0])
        return ""  # AF_UNIX / path-style address = local

    def _local(host: str) -> bool:
        return host in ("", "localhost", "::1", "0.0.0.0") or host.startswith("127.")

    def guard_connect(self, address, *args, **kwargs):
        if _local(_host(address)):
            return real_connect(self, address, *args, **kwargs)
        raise AssertionError(f"network access attempted during test: {address!r}")

    def guard_connect_ex(self, address, *args, **kwargs):
        if _local(_host(address)):
            return real_connect_ex(self, address, *args, **kwargs)
        raise AssertionError(f"network access attempted during test: {address!r}")

    def blocked(*args, **kwargs):
        raise AssertionError("network access attempted during test")

    def guard_getaddrinfo(host, *args, **kwargs):
        if _local(str(host) if host is not None else ""):
            return real_getaddrinfo(host, *args, **kwargs)
        raise AssertionError(f"name resolution attempted during test: {host!r}")

    def guard_gethostbyname(host, *args, **kwargs):
        if _local(str(host) if host is not None else ""):
            return real_gethostbyname(host, *args, **kwargs)
        raise AssertionError(f"name resolution attempted during test: {host!r}")

    real_getaddrinfo = socket.getaddrinfo
    real_gethostbyname = socket.gethostbyname

    monkeypatch.setattr(socket.socket, "connect", guard_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guard_connect_ex)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", guard_getaddrinfo)
    monkeypatch.setattr(socket, "gethostbyname", guard_gethostbyname)
    yield
