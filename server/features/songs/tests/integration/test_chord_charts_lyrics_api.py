import pytest
from rest_framework.test import APIClient

from conftest import make_admin_client, make_user, make_auth_client
from features.songs.models import Song, ChordChart, Lyrics


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def song() -> Song:
    return Song.objects.create(title="Oceans", artist="Hillsong")


@pytest.mark.django_db
class TestChordChartListView:
    def test_returns_200(self, client: APIClient, song: Song) -> None:
        ChordChart.objects.create(song=song, content="Am G C", tone="Am", instrument="Guitar")
        resp = client.get("/api/chord-charts/")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["tone"] == "Am"

    def test_empty_list(self, client: APIClient) -> None:
        resp = client.get("/api/chord-charts/")
        assert resp.status_code == 200
        assert resp.data == []


@pytest.mark.django_db
class TestChordChartDetailView:
    def test_patch_updates_content(self, song: Song) -> None:
        chart = ChordChart.objects.create(
            song=song, content="Am G C", tone="G", instrument="Violão"
        )
        admin_client, _ = make_admin_client()
        resp = admin_client.patch(
            f"/api/chord-charts/{chart.pk}/", {"content": "D Em C"}, format="json"
        )
        assert resp.status_code == 200
        assert resp.data["content"] == "D Em C"
        assert resp.data["song_id"] == song.pk
        assert resp.data["tone"] == "G"
        assert resp.data["instrument"] == "Violão"
        assert "updated_at" in resp.data

    def test_patch_returns_404_for_nonexistent(self) -> None:
        admin_client, _ = make_admin_client()
        resp = admin_client.patch("/api/chord-charts/9999/", {"content": "X"}, format="json")
        assert resp.status_code == 404

    def test_patch_returns_400_without_content(self, song: Song) -> None:
        chart = ChordChart.objects.create(
            song=song, content="Am G C", tone="G", instrument="Violão"
        )
        admin_client, _ = make_admin_client()
        resp = admin_client.patch(f"/api/chord-charts/{chart.pk}/", {}, format="json")
        assert resp.status_code == 400

    def test_patch_returns_401_unauthenticated(self, song: Song) -> None:
        chart = ChordChart.objects.create(
            song=song, content="Am G C", tone="G", instrument="Violão"
        )
        resp = APIClient().patch(f"/api/chord-charts/{chart.pk}/", {"content": "X"}, format="json")
        assert resp.status_code == 401

    def test_patch_returns_403_non_admin(self, song: Song) -> None:
        chart = ChordChart.objects.create(
            song=song, content="Am G C", tone="G", instrument="Violão"
        )
        user = make_user(username="regular")
        client = make_auth_client(user)
        resp = client.patch(f"/api/chord-charts/{chart.pk}/", {"content": "X"}, format="json")
        assert resp.status_code == 403


@pytest.mark.django_db
class TestLyricsListView:
    def test_returns_200(self, client: APIClient, song: Song) -> None:
        Lyrics.objects.create(song=song, content="Amazing grace how sweet the sound")
        resp = client.get("/api/lyrics/")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert "Amazing grace" in resp.data[0]["content"]

    def test_empty_list(self, client: APIClient) -> None:
        resp = client.get("/api/lyrics/")
        assert resp.status_code == 200
        assert resp.data == []


@pytest.mark.django_db
class TestLyricsDetailView:
    def test_patch_updates_content(self, song: Song) -> None:
        lyrics = Lyrics.objects.create(song=song, content="Old content")
        admin_client, _ = make_admin_client()
        resp = admin_client.patch(
            f"/api/lyrics/{lyrics.pk}/", {"content": "New content"}, format="json"
        )
        assert resp.status_code == 200
        assert resp.data["content"] == "New content"
        assert resp.data["song_id"] == song.pk
        assert "updated_at" in resp.data

    def test_patch_returns_404_for_nonexistent(self) -> None:
        admin_client, _ = make_admin_client()
        resp = admin_client.patch("/api/lyrics/9999/", {"content": "X"}, format="json")
        assert resp.status_code == 404

    def test_patch_returns_400_without_content(self, song: Song) -> None:
        lyrics = Lyrics.objects.create(song=song, content="Some content")
        admin_client, _ = make_admin_client()
        resp = admin_client.patch(f"/api/lyrics/{lyrics.pk}/", {}, format="json")
        assert resp.status_code == 400

    def test_patch_returns_401_unauthenticated(self, song: Song) -> None:
        lyrics = Lyrics.objects.create(song=song, content="Some content")
        resp = APIClient().patch(f"/api/lyrics/{lyrics.pk}/", {"content": "X"}, format="json")
        assert resp.status_code == 401

    def test_patch_returns_403_non_admin(self, song: Song) -> None:
        lyrics = Lyrics.objects.create(song=song, content="Some content")
        user = make_user(username="regular2")
        client = make_auth_client(user)
        resp = client.patch(f"/api/lyrics/{lyrics.pk}/", {"content": "X"}, format="json")
        assert resp.status_code == 403
