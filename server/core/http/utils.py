import hashlib
import json
from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response


def _make_etag_from_data(data: Any) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    digest = hashlib.sha256(payload).hexdigest()
    return f'"{digest}"'


def _not_modified_or_response(
    request: Request,
    data: Any,
    status_code: int = 200,
    private: bool = False,
) -> Response:
    """Answer 304 when the caller's ETag still matches, otherwise 200 with the body.

    Pass ``private=True`` for anything that depends on who is asking. A shared cache keys
    on the URL, not on the Authorization header, so without the declaration one member's
    /api/me/profile/ response would be served to the next member asking for it. Public
    data is left undeclared on purpose, so a cache in front is free to store it.

    >>> _not_modified_or_response(request, {"name": "Ana"}, private=True).status_code
    200
    """
    etag = _make_etag_from_data(data)
    inm = request.headers.get("If-None-Match")
    inm_clean = inm.strip() if inm else None

    if inm_clean and inm_clean == etag:
        return _with_cache_headers(Response(status=304), etag, private)

    return _with_cache_headers(Response(data, status=status_code), etag, private)


def _with_cache_headers(response: Response, etag: str, private: bool) -> Response:
    """Attach the ETag, and the no-sharing declaration when the body is caller-specific."""
    response["ETag"] = etag
    if private:
        # nginx skips caching a response marked private; Vary is the second line of
        # defence if a cache is ever configured with proxy_ignore_headers.
        response["Cache-Control"] = "private, no-store"
        response["Vary"] = "Authorization"
    return response
