"""Explicit transport opt-in for the credential-injecting Codex Cloud proxy.

No automatic cloud detection, credential inspection or direct-network fallback.
Proxy addresses and CA paths must never enter experiment metadata or errors.
"""

import os
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx2


def http_mode() -> Literal["direct", "codex-cloud"]:
    mode = os.environ.get("AGENTGUARD_HTTP_MODE", "direct")
    if mode not in ("direct", "codex-cloud"):
        raise ValueError("AGENTGUARD_HTTP_MODE must be direct or codex-cloud")
    return mode


def _options(timeout: float) -> dict[str, Any]:
    options: dict[str, Any] = {
        "timeout": timeout,
        "follow_redirects": False,
        "verify": True,
        "trust_env": False,
    }
    if http_mode() == "codex-cloud":
        proxy = os.environ.get("HTTPS_PROXY")
        if not proxy:
            raise ValueError("codex-cloud mode requires the runtime HTTPS_PROXY")
        try:
            parsed = urlsplit(proxy)
            valid = (
                parsed.scheme in ("http", "https")
                and bool(parsed.hostname)
                and parsed.port != 0
                and parsed.path in ("", "/")
                and not parsed.query
                and not parsed.fragment
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("Invalid runtime HTTPS_PROXY configuration") from None
        # Explicit proxy prevents NO_PROXY/ALL_PROXY from creating a direct route.
        # trust_env preserves SSL_CERT_FILE/SSL_CERT_DIR and normal TLS validation.
        options.update(proxy=proxy, trust_env=True)
    return options


def sync_http_client(timeout: float) -> httpx2.Client:
    options = _options(timeout)
    try:
        return httpx2.Client(**options)
    except (ValueError, OSError, ImportError, httpx2.InvalidURL):
        raise ValueError("HTTP transport setup failed; check runtime proxy and CA trust") from None


def async_http_client(timeout: float) -> httpx2.AsyncClient:
    options = _options(timeout)
    try:
        return httpx2.AsyncClient(**options)
    except (ValueError, OSError, ImportError, httpx2.InvalidURL):
        raise ValueError("HTTP transport setup failed; check runtime proxy and CA trust") from None
