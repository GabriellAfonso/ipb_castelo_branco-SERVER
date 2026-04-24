import pytest
from django.contrib import admin


@pytest.mark.django_db
class TestAccountsAdminRegistrations:
    def test_user_registered(self) -> None:
        from features.accounts.models.user import User

        assert admin.site.is_registered(User)

    def test_profile_registered(self) -> None:
        from features.accounts.models.profile import Profile

        assert admin.site.is_registered(Profile)

    def test_user_admin_list_display(self) -> None:
        from features.accounts.models.user import User

        model_admin = admin.site._registry[User]
        assert "username" in model_admin.list_display
        assert "is_staff" in model_admin.list_display


@pytest.mark.django_db
class TestSongsAdminRegistrations:
    def test_category_registered(self) -> None:
        from features.songs.models.song import Category

        assert admin.site.is_registered(Category)

    def test_song_registered(self) -> None:
        from features.songs.models.song import Song

        assert admin.site.is_registered(Song)

    def test_played_registered(self) -> None:
        from features.songs.models.song import Played

        assert admin.site.is_registered(Played)

    def test_hymn_registered(self) -> None:
        from features.songs.models.hymnal import Hymn

        assert admin.site.is_registered(Hymn)

    def test_chord_chart_registered(self) -> None:
        from features.songs.models.chord_chart import ChordChart

        assert admin.site.is_registered(ChordChart)

    def test_lyrics_registered(self) -> None:
        from features.songs.models.lyrics import Lyrics

        assert admin.site.is_registered(Lyrics)


@pytest.mark.django_db
class TestGalleryAdminRegistrations:
    def test_album_registered(self) -> None:
        from features.gallery.models.gallery import Album

        assert admin.site.is_registered(Album)

    def test_photo_registered(self) -> None:
        from features.gallery.models.gallery import Photo

        assert admin.site.is_registered(Photo)

    def test_album_admin_has_upload_url(self) -> None:
        from features.gallery.models.gallery import Album

        model_admin = admin.site._registry[Album]
        urls = model_admin.get_urls()
        url_names = [u.name for u in urls if hasattr(u, "name")]
        assert "gallery_upload" in url_names


@pytest.mark.django_db
class TestScheduleAdminRegistrations:
    def test_schedule_type_registered(self) -> None:
        from features.schedule.models.schedule import ScheduleType

        assert admin.site.is_registered(ScheduleType)

    def test_member_schedule_config_registered(self) -> None:
        from features.schedule.models.schedule import MemberScheduleConfig

        assert admin.site.is_registered(MemberScheduleConfig)

    def test_monthly_schedule_registered(self) -> None:
        from features.schedule.models.schedule import MonthlySchedule

        assert admin.site.is_registered(MonthlySchedule)

    def test_monthly_schedule_admin_readonly_fields(self) -> None:
        from features.schedule.models.schedule import MonthlySchedule

        model_admin = admin.site._registry[MonthlySchedule]
        assert "created_at" in model_admin.readonly_fields


@pytest.mark.django_db
class TestMembersAdminRegistrations:
    def test_member_registered(self) -> None:
        from features.members.models.member import Member

        assert admin.site.is_registered(Member)

    def test_member_status_registered(self) -> None:
        from features.members.models.member import MemberStatus

        assert admin.site.is_registered(MemberStatus)

    def test_role_registered(self) -> None:
        from features.members.models.member import Role

        assert admin.site.is_registered(Role)

    def test_ministry_registered(self) -> None:
        from features.members.models.member import Ministry

        assert admin.site.is_registered(Ministry)
