from dependency_injector import containers, providers

from features.accounts.repositories.profile_repository import DjangoProfileRepository
from features.accounts.repositories.user_repository import DjangoUserRepository
from features.accounts.services.google_auth_service import GoogleAuthService
from features.accounts.services.login_service import LoginService
from features.accounts.services.profile_service import ProfileService
from features.accounts.services.register_service import RegisterService
from core.time.clock import SystemClock
from features.bible.repositories import JsonFileBibleRepository
from features.bible.services import BibleService
from features.gallery.repositories.gallery_repository import DjangoGalleryRepository
from features.gallery.services.gallery_service import GalleryService
from features.members.repositories.member_repository import DjangoMemberRepository
from features.members.services.member_service import MemberService
from features.songs.repositories.hymnal_history_repository import DjangoHymnalHistoryRepository
from features.songs.repositories.hymnal_repository import DjangoHymnalRepository
from features.songs.repositories.song_repository import DjangoSongRepository
from features.songs.services.hymnal_history_config_service import HymnalHistoryConfigService
from features.songs.services.hymnal_history_ingest_service import HymnalHistoryIngestService
from features.songs.services.hymnal_history_report_service import HymnalHistoryReportService
from features.songs.services.hymnal_service import HymnalService
from features.songs.services.register_plays_service import RegisterPlaysService
from features.schedule.repositories.schedule_repository import DjangoScheduleRepository
from features.schedule.services.schedule_service import ScheduleService
from features.songs.services.song_service import SongService


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "features.accounts.views.auth",
            "features.accounts.views.profile",
            "features.bible.views",
            "features.gallery.views.gallery",
            "features.gallery.views.upload",
            "features.songs.views.hymnal",
            "features.songs.views.hymnal_history",
            "features.songs.views.register_plays",
            "features.songs.views.songs",
            "features.members.views.birthdays",
            "features.members.views.members",
            "features.schedule.views.schedule",
        ]
    )

    user_repository = providers.Factory(DjangoUserRepository)
    profile_repository = providers.Factory(DjangoProfileRepository)

    register_service = providers.Factory(RegisterService, user_repository=user_repository)
    login_service = providers.Factory(LoginService)
    google_auth_service = providers.Factory(
        GoogleAuthService,
        user_repository=user_repository,
        profile_repository=profile_repository,
    )
    profile_service = providers.Factory(ProfileService, profile_repository=profile_repository)

    bible_repository = providers.Singleton(JsonFileBibleRepository)
    bible_service = providers.Factory(BibleService, bible_repository=bible_repository)

    gallery_repository = providers.Factory(DjangoGalleryRepository)
    gallery_service = providers.Factory(GalleryService, repository=gallery_repository)

    clock = providers.Singleton(SystemClock)

    song_repository = providers.Factory(DjangoSongRepository)
    hymnal_repository = providers.Factory(DjangoHymnalRepository)
    hymnal_history_repository = providers.Factory(DjangoHymnalHistoryRepository)

    song_service = providers.Factory(SongService, repository=song_repository)
    register_plays_service = providers.Factory(RegisterPlaysService, repository=song_repository)
    hymnal_service = providers.Factory(HymnalService, repository=hymnal_repository)

    hymnal_history_ingest_service = providers.Factory(
        HymnalHistoryIngestService,
        repository=hymnal_history_repository,
        clock=clock,
    )
    hymnal_history_report_service = providers.Factory(
        HymnalHistoryReportService,
        repository=hymnal_history_repository,
    )
    hymnal_history_config_service = providers.Factory(
        HymnalHistoryConfigService,
        repository=hymnal_history_repository,
    )

    member_repository = providers.Factory(DjangoMemberRepository)
    member_service = providers.Factory(MemberService, repository=member_repository)

    schedule_repository = providers.Factory(DjangoScheduleRepository)
    schedule_service = providers.Factory(ScheduleService, repository=schedule_repository)
