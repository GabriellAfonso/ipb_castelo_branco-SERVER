from django.urls import path, include
from .views import SongsBySundayAPI, TopSongsAPI, TopTonesAPI, SuggestedSongsAPI, GenerateMonthlyScheduleAPI
from .views import hymnalAPI, Unauthorized, RegisterSundays
from .views import RegisterAPI, LoginAPI


app_name = 'main'

urlpatterns = [
    path('ipbcb/songs-by-sunday/',
         SongsBySundayAPI.as_view(), name='songs_by_sunday'),
    path('ipbcb/top-songs/', TopSongsAPI.as_view(), name='top_songs'),
    path('ipbcb/top-tones/', TopTonesAPI.as_view(), name='top_tones'),
    path('ipbcb/suggested-songs/',
         SuggestedSongsAPI.as_view(), name='suggested_songs'),
    path('ipbcb/generate-schedule/',
         GenerateMonthlyScheduleAPI.as_view(), name='generate_schedule'),
    path('ipbcb/hymnal/',
         hymnalAPI.as_view(), name='hymnal'),

    path('unauthorized', Unauthorized.as_view(), name='unauthorized'),
    path('register-sundays', RegisterSundays.as_view(), name='register_sundays'),

    path('ipbcb/auth/register/', RegisterAPI.as_view(), name='register'),
    path('ipbcb/auth/login/', LoginAPI.as_view(), name='login'),

]
