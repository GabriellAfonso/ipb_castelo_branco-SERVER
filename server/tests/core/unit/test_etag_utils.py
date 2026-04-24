from django.test import RequestFactory
from rest_framework.request import Request

from core.http.utils import _make_etag_from_data, _not_modified_or_response


def _make_drf_request(if_none_match: str | None = None) -> Request:
    req = RequestFactory().get("/test/")
    if if_none_match is not None:
        req.META["HTTP_IF_NONE_MATCH"] = if_none_match
    return Request(req)


# --- _make_etag_from_data ---


def test_etag_is_quoted_hex_string() -> None:
    etag = _make_etag_from_data({"key": "value"})
    assert etag.startswith('"') and etag.endswith('"')
    inner = etag[1:-1]
    assert len(inner) == 64
    assert all(c in "0123456789abcdef" for c in inner)


def test_etag_is_deterministic() -> None:
    data = {"x": 1, "y": [2, 3]}
    assert _make_etag_from_data(data) == _make_etag_from_data(data)


def test_etag_is_independent_of_key_order() -> None:
    assert _make_etag_from_data({"a": 1, "z": 2}) == _make_etag_from_data({"z": 2, "a": 1})


def test_etag_differs_for_different_data() -> None:
    assert _make_etag_from_data({"a": 1}) != _make_etag_from_data({"a": 2})


def test_etag_handles_unicode() -> None:
    etag = _make_etag_from_data({"name": "João"})
    assert isinstance(etag, str)
    assert len(etag) == 66  # 64 hex + 2 quotes


def test_etag_handles_nested_structures() -> None:
    data = [{"nested": {"deep": None}}, {"list": [1, 2, 3]}]
    etag1 = _make_etag_from_data(data)
    etag2 = _make_etag_from_data(data)
    assert etag1 == etag2
    assert etag1.startswith('"') and etag1.endswith('"')


# --- _not_modified_or_response ---


def test_returns_200_without_if_none_match() -> None:
    data = {"items": [1, 2, 3]}
    request = _make_drf_request()
    response = _not_modified_or_response(request, data)
    assert response.status_code == 200
    assert response.data == data
    assert "ETag" in response


def test_returns_304_when_etag_matches() -> None:
    data = {"foo": "bar"}
    etag = _make_etag_from_data(data)
    request = _make_drf_request(if_none_match=etag)
    response = _not_modified_or_response(request, data)
    assert response.status_code == 304
    assert response["ETag"] == etag
    assert response.data is None


def test_returns_200_when_etag_differs() -> None:
    data = {"foo": "bar"}
    request = _make_drf_request(if_none_match='"stale-etag"')
    response = _not_modified_or_response(request, data)
    assert response.status_code == 200


def test_passes_through_custom_status_code() -> None:
    data = {"created": True}
    request = _make_drf_request()
    response = _not_modified_or_response(request, data, status_code=201)
    assert response.status_code == 201


def test_strips_whitespace_from_if_none_match() -> None:
    data = {"x": 42}
    etag = _make_etag_from_data(data)
    request = _make_drf_request(if_none_match=f"  {etag}  ")
    response = _not_modified_or_response(request, data)
    assert response.status_code == 304


def test_tag_param_does_not_affect_response() -> None:
    data = {"a": 1}
    request_no_tag = _make_drf_request()
    request_with_tag = _make_drf_request()
    resp_no_tag = _not_modified_or_response(request_no_tag, data, tag="")
    resp_with_tag = _not_modified_or_response(request_with_tag, data, tag="X")
    assert resp_no_tag.status_code == resp_with_tag.status_code
    assert resp_no_tag["ETag"] == resp_with_tag["ETag"]
