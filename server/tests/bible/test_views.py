from collections.abc import Generator

import pytest
from rest_framework.test import APIClient
from unittest.mock import patch

BIBLE_LIST_URL = "/api/bible/"
BIBLE_DETAIL_URL = "/api/bible/{name}/"

SAMPLE_BIBLE = [{"abbrev": "Gn", "name": "Gênesis", "chapters": [["No princípio..."]]}]


@pytest.fixture(autouse=True)
def mock_bibles() -> Generator[None, None, None]:
    with patch("features.bible.views.BIBLES", {"nvi": SAMPLE_BIBLE, "arc": SAMPLE_BIBLE}):
        yield


class TestBibleListView:
    def test_returns_200_without_auth(self) -> None:
        resp = APIClient().get(BIBLE_LIST_URL)
        assert resp.status_code == 200

    def test_returns_sorted_versions(self) -> None:
        resp = APIClient().get(BIBLE_LIST_URL)
        assert resp.data == {"versions": ["arc", "nvi"]}


class TestBibleDetailView:
    def test_returns_200_without_auth(self) -> None:
        resp = APIClient().get(BIBLE_DETAIL_URL.format(name="nvi"))
        assert resp.status_code == 200

    def test_returns_bible_data(self) -> None:
        resp = APIClient().get(BIBLE_DETAIL_URL.format(name="nvi"))
        assert resp.data == SAMPLE_BIBLE

    def test_unknown_version_returns_404(self) -> None:
        resp = APIClient().get(BIBLE_DETAIL_URL.format(name="unknown"))
        assert resp.status_code == 404
