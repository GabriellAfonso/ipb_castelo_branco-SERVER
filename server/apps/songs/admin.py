from django.contrib import admin

from apps.songs.models.hymnal import Hymn
from apps.songs.models.song import Category, Played, Song

admin.site.register([Category, Song, Played, Hymn])
