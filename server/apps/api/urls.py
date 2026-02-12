from django.urls import path

from apps.api.views.admin_pages import RegisterSundays, Unauthorized, RegisterSundayPlaysAPI
from apps.api.views.auth import LoginAPI, RefreshTokenAPI, RegisterAPI
from apps.api.views.hymnal import hymnalAPI
from apps.api.views.profile import MeProfileAPIView, ProfilePhotoAPIView
from apps.api.views.schedule import (
    CurrentMonthlyScheduleAPI,
    MonthlySchedulePreviewAPI,
    MonthlyScheduleSaveAPI,
)
from apps.api.views.songs import (
    AllSongsAPI,
    SongsBySundayAPI,
    SuggestedSongsAPI,
    TopSongsAPI,
    TopTonesAPI,
)

app_name = "apps.api"

urlpatterns = [
    path("unauthorized", Unauthorized.as_view(), name="unauthorized"),
    path("register-sundays", RegisterSundays.as_view(), name="register_sundays"),

    # 🎵 MÚSICAS
    path("ipbcb/songs/", AllSongsAPI.as_view(), name="all_songs"),

    path("ipbcb/songs-by-sunday/",
         SongsBySundayAPI.as_view(), name="songs_by_sunday"),
    path("ipbcb/top-songs/", TopSongsAPI.as_view(), name="top_songs"),
    path("ipbcb/top-tones/", TopTonesAPI.as_view(), name="top_tones"),
    path("ipbcb/suggested-songs/",
         SuggestedSongsAPI.as_view(), name="suggested_songs"),

    # ✅ ADMIN: registrar Played via POST (precisa profile.is_admin == True)
    path("ipbcb/played/register/", RegisterSundayPlaysAPI.as_view(),
         name="register_sunday_plays"),

    # 🗓️ ESCALA (novo fluxo)
    path("ipbcb/schedule/current/",
         CurrentMonthlyScheduleAPI.as_view(), name="schedule_current"),
    path("ipbcb/schedule/preview/",
         MonthlySchedulePreviewAPI.as_view(), name="schedule_preview"),
    path("ipbcb/schedule/save/",
         MonthlyScheduleSaveAPI.as_view(), name="schedule_save"),

    # compat: endpoint antigo agora gera preview (não salva)
    path("ipbcb/generate-schedule/",
         MonthlySchedulePreviewAPI.as_view(), name="generate_schedule"),

    path("ipbcb/hymnal/", hymnalAPI.as_view(), name="hymnal"),
    path("ipbcb/auth/register/", RegisterAPI.as_view(), name="register"),
    path("ipbcb/auth/login/", LoginAPI.as_view(), name="login"),
    path("ipbcb/auth/refresh/", RefreshTokenAPI.as_view(), name="token_refresh"),
    path("ipbcb/me/profile/photo/",
         ProfilePhotoAPIView.as_view(), name="profile_photo"),
    path("ipbcb/me/profile/", MeProfileAPIView.as_view()),
]
