"""How the lockout resolves a client address, under this project's own settings.

These pin the anti-spoofing control from specs/008-login-brute-force-lockout/plan.md D-6.
They exercise django-axes rather than project code on purpose: the behaviour being pinned
*is* the configuration, and every one of these settings silently degrades to something
wrong when it is mistuned — no exception is raised, attempts just land under the wrong key.
"""

from typing import Any, Optional

import pytest
from axes.helpers import get_client_ip_address
from django.http import HttpRequest
from django.test import RequestFactory

NGINX_ADDRESS = "172.18.0.2"
REAL_CLIENT = "203.0.113.7"
SPOOFED = "1.1.1.1"


def _request(remote_addr: str, forwarded_for: Optional[str] = None) -> HttpRequest:
    meta: dict[str, Any] = {"REMOTE_ADDR": remote_addr}
    if forwarded_for is not None:
        meta["HTTP_X_FORWARDED_FOR"] = forwarded_for
    return RequestFactory().post("/api/auth/login/", **meta)


def test_falls_back_to_remote_addr_without_forwarded_header() -> None:
    """Dev and the test suite send no X-Forwarded-For and must still resolve an address."""
    request = _request("10.0.0.9")

    assert get_client_ip_address(request) == "10.0.0.9"


def test_uses_forwarded_header_over_the_proxy_address() -> None:
    """Behind nginx, REMOTE_ADDR is the proxy — every client would share one bucket."""
    request = _request(NGINX_ADDRESS, REAL_CLIENT)

    assert get_client_ip_address(request) == REAL_CLIENT


def test_client_supplied_forwarded_prefix_is_ignored() -> None:
    """A client that writes its own X-Forwarded-For must not choose its own lockout key.

    nginx appends the real peer address, so the rightmost entry is the trustworthy one.
    With the default 'left-most' order this returns the spoofed value and the lockout is
    bypassable by rotating the header.
    """
    request = _request(NGINX_ADDRESS, f"{SPOOFED}, {REAL_CLIENT}")

    assert get_client_ip_address(request) == REAL_CLIENT


@pytest.mark.parametrize("forwarded", [REAL_CLIENT, f"{SPOOFED}, {REAL_CLIENT}"])
def test_address_resolves_for_every_forwarded_shape(forwarded: str) -> None:
    """Regression: AXES_IPWARE_PROXY_COUNT = 1 returned None for a single-entry header.

    That is the ordinary production request, and a None address puts every locked-out
    client into the same bucket. The setting is left unset — it is not DRF's NUM_PROXIES.
    """
    request = _request(NGINX_ADDRESS, forwarded)

    assert get_client_ip_address(request) == REAL_CLIENT
