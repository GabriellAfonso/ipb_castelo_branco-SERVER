from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from features.gallery.views.upload import _build_upload_html


def _make_album(pk: int, name: str) -> MagicMock:
    album = MagicMock()
    album.pk = pk
    album.name = name
    return album


class TestBuildUploadHtml:
    @pytest.fixture(autouse=True)
    def _mock_csrf(self) -> Generator[None]:
        with patch("features.gallery.views.upload.get_token", return_value="fake-csrf-token"):
            yield

    def test_contains_form_tag(self) -> None:
        request = MagicMock()
        html = _build_upload_html(request, [])  # type: ignore[arg-type]
        assert "<form" in html
        assert 'method="post"' in html
        assert 'enctype="multipart/form-data"' in html

    def test_contains_csrf_token(self) -> None:
        request = MagicMock()
        html = _build_upload_html(request, [])  # type: ignore[arg-type]
        assert "fake-csrf-token" in html

    def test_renders_album_options(self) -> None:
        request = MagicMock()
        albums: list[Any] = [_make_album(1, "Fotos 2026"), _make_album(2, "Eventos")]
        html = _build_upload_html(request, albums)  # type: ignore[arg-type]
        assert '<option value="1">Fotos 2026</option>' in html
        assert '<option value="2">Eventos</option>' in html

    def test_no_options_when_no_albums(self) -> None:
        request = MagicMock()
        html = _build_upload_html(request, [])  # type: ignore[arg-type]
        assert "<option" not in html

    def test_renders_errors(self) -> None:
        request = MagicMock()
        html = _build_upload_html(request, [], errors=["Arquivo grande", "Formato ruim"])  # type: ignore[arg-type]
        assert "Arquivo grande" in html
        assert "Formato ruim" in html
        assert "color:red" in html

    def test_no_errors_when_none(self) -> None:
        request = MagicMock()
        html = _build_upload_html(request, [], errors=None)  # type: ignore[arg-type]
        assert "color:red" not in html

    def test_no_errors_when_empty_list(self) -> None:
        request = MagicMock()
        html = _build_upload_html(request, [], errors=[])  # type: ignore[arg-type]
        assert "color:red" not in html

    def test_contains_file_input(self) -> None:
        request = MagicMock()
        html = _build_upload_html(request, [])  # type: ignore[arg-type]
        assert 'type="file"' in html
        assert 'name="images"' in html
        assert "multiple" in html

    def test_contains_submit_button(self) -> None:
        request = MagicMock()
        html = _build_upload_html(request, [])  # type: ignore[arg-type]
        assert "Upload" in html
        assert "<button" in html
