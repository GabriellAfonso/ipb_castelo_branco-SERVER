from rest_framework import serializers
from main.models.songs import Song, Played


class SongSerializer(serializers.ModelSerializer):
    class Meta:
        model = Song
        fields = ['id', 'title', 'artist']


class PlayedSerializer(serializers.ModelSerializer):
    song = SongSerializer(read_only=True)
    date = serializers.DateField(format="%d/%m/%Y")

    class Meta:
        model = Played
        fields = ['id', 'song', 'date', 'tone', 'position']
