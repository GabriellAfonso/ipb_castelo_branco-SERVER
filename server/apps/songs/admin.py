from django.contrib import admin

from apps.songs.models.chord_chart import ChordChart
from apps.songs.models.hymnal import Hymn
from apps.songs.models.lyrics import Lyrics
from apps.songs.models.song import Category, Played, Song

admin.site.register([Category, Song, Played, Hymn, ChordChart, Lyrics])
