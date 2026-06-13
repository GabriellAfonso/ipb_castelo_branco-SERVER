from dependency_injector import containers, providers

from features.accounts.repositories.profile_repository import DjangoProfileRepository
from features.accounts.repositories.user_repository import DjangoUserRepository
from features.accounts.services.google_auth_service import GoogleAuthService
from features.accounts.services.login_service import LoginService
from features.accounts.services.profile_service import ProfileService
from features.accounts.services.register_service import RegisterService
from features.bible.repositories import JsonFileBibleRepository
from features.bible.services import BibleService
from features.gallery.repositories.gallery_repository import DjangoGalleryRepository
from features.gallery.services.gallery_service import GalleryService
from features.songs.repositories.hymnal_repository import DjangoHymnalRepository
from features.songs.repositories.song_repository import DjangoSongRepository
from features.songs.services.hymnal_service import HymnalService
from features.songs.services.register_plays_service import RegisterPlaysService
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
            "features.songs.views.register_plays",
            "features.songs.views.songs",
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

    song_repository = providers.Factory(DjangoSongRepository)
    hymnal_repository = providers.Factory(DjangoHymnalRepository)

    song_service = providers.Factory(SongService, repository=song_repository)
    register_plays_service = providers.Factory(RegisterPlaysService, repository=song_repository)
    hymnal_service = providers.Factory(HymnalService, repository=hymnal_repository)
