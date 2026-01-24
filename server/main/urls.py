from django.urls import path, include
from .views import SongsBySundayAPI, TopSongsAPI, TopTonesAPI, SuggestedSongsAPI, GenerateMonthlyScheduleAPIView
from .views import hymnalAPI, Unauthorized, RegisterSundays


app_name = 'main'

urlpatterns = [
    path('ipbcb/songs-by-sunday/',
         SongsBySundayAPI.as_view(), name='songs_by_sunday'),
    path('ipbcb/top-songs/', TopSongsAPI.as_view(), name='top_songs'),
    path('ipbcb/top-tones/', TopTonesAPI.as_view(), name='top_tones'),
    path('ipbcb/suggested-songs/',
         SuggestedSongsAPI.as_view(), name='suggested_songs'),
    path('ipbcb/generate-schedule/',
         GenerateMonthlyScheduleAPIView.as_view(), name='generate_schedule'),
    path('ipbcb/hymnal/',
         hymnalAPI.as_view(), name='hymnal'),
    # path('registrar-domingo', RegisterSundays.as_view(), name='register_sundays'),
    # path('encontrar-musicas', FindMusic.as_view(), name='find_music'),

    path('unauthorized', Unauthorized.as_view(), name='unauthorized'),
    path('register', RegisterSundays.as_view(), name='register_sundays'),
]
