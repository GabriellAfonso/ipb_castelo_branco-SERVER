"""Uploads are accepted on decoded content, never on the name the client sent."""

from io import BytesIO

import pytest
from PIL import Image

from core.domain.exceptions import ValidationError
from core.files.image_validation import MAX_IMAGE_BYTES, detect_image_extension


def _image(fmt: str = "PNG", name: str = "photo.png") -> BytesIO:
    buffer = BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format=fmt)
    buffer.seek(0)
    buffer.name = name
    return buffer


class TestAcceptedFormats:
    @pytest.mark.parametrize(
        ("fmt", "expected"),
        [("JPEG", "jpg"), ("PNG", "png"), ("WEBP", "webp"), ("GIF", "gif")],
    )
    def test_returns_the_extension_for_each_allowed_format(self, fmt: str, expected: str) -> None:
        assert detect_image_extension(_image(fmt)) == expected

    def test_ignores_the_client_filename(self) -> None:
        """Regression: a PNG named ``evil.html`` is stored as ``.png``."""
        assert detect_image_extension(_image("PNG", "evil.html")) == "png"

    def test_ignores_a_misleading_extension(self) -> None:
        assert detect_image_extension(_image("JPEG", "photo.png")) == "jpg"

    def test_rewinds_the_stream_for_the_caller(self) -> None:
        upload = _image()

        detect_image_extension(upload)

        assert upload.tell() == 0


class TestRejectedContent:
    def test_rejects_bytes_that_are_not_an_image(self) -> None:
        with pytest.raises(ValidationError, match="não é uma imagem"):
            detect_image_extension(BytesIO(b"<html><script>alert(1)</script></html>"))

    def test_rejects_svg_which_is_a_scriptable_document(self) -> None:
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'

        with pytest.raises(ValidationError, match="não é uma imagem"):
            detect_image_extension(BytesIO(svg))

    def test_rejects_an_empty_upload(self) -> None:
        with pytest.raises(ValidationError):
            detect_image_extension(BytesIO(b""))

    def test_rewinds_the_stream_even_when_it_rejects(self) -> None:
        upload = BytesIO(b"not an image")

        with pytest.raises(ValidationError):
            detect_image_extension(upload)

        assert upload.tell() == 0


class TestSizeLimit:
    def test_rejects_an_upload_over_the_limit(self) -> None:
        upload = _image()
        upload.size = MAX_IMAGE_BYTES + 1  # type: ignore[attr-defined]

        with pytest.raises(ValidationError, match="muito grande"):
            detect_image_extension(upload)

    def test_message_carries_the_offending_size_and_the_limit(self) -> None:
        upload = _image()
        upload.size = MAX_IMAGE_BYTES + 1  # type: ignore[attr-defined]

        with pytest.raises(ValidationError, match=str(MAX_IMAGE_BYTES + 1)):
            detect_image_extension(upload)

    def test_refuses_before_decoding(self) -> None:
        """An oversized upload is rejected on size, so its bytes are never decoded."""
        upload = BytesIO(b"not an image")
        upload.size = MAX_IMAGE_BYTES + 1  # type: ignore[attr-defined]

        with pytest.raises(ValidationError, match="muito grande"):
            detect_image_extension(upload)

    def test_measures_the_stream_when_size_is_absent(self) -> None:
        """A plain BytesIO has no ``size``; the Google avatar path relies on this."""
        assert detect_image_extension(_image()) == "png"

    def test_honours_a_caller_supplied_limit(self) -> None:
        with pytest.raises(ValidationError, match="muito grande"):
            detect_image_extension(_image(), max_bytes=10)
