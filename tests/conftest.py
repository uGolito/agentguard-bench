"""All tests fail closed on real network access, even if a local API key exists."""

import os
import socket

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    original_connect = socket.socket.connect

    if os.name == "nt":

        def internal_socketpair(*args, **kwargs):
            # Windows asyncio uses a local TCP pair as its self-wakeup pipe.
            # Only these explicitly constructed sockets may use original_connect;
            # every application connection remains blocked below.
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                listener.bind(("127.0.0.1", 0))
                listener.listen(1)
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                original_connect(client, listener.getsockname())
                server, _ = listener.accept()
            return server, client

        monkeypatch.setattr(socket, "socketpair", internal_socketpair)

    def blocked(*args, **kwargs):
        raise AssertionError("Network access is forbidden in the offline test suite")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
