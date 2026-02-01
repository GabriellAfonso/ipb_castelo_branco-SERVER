from rest_framework import serializers
from main.models.songs import Song, Played
from django.contrib.auth.models import User


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


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["username", "password", "password_confirm"]

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        return User.objects.create_user(**validated_data)
