import random
from collections import defaultdict
from datetime import timedelta

from django.db.models import Count
from django.utils.timezone import now
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models.songs import Played, Song
from main.serializers import PlayedSerializer

from .utils import _not_modified_or_response


class SongsBySundayAPI(APIView):
    def get(self, request):
        qs = (
            Played.objects.select_related("song").order_by("-date", "position")
        )

        data = PlayedSerializer(qs, many=True).data
        grouped = defaultdict(list)

        for item in data:
            grouped[item["date"]].append(
                {
                    "position": item["position"],
                    "song": item["song"]["title"],
                    "artist": item["song"]["artist"],
                    "tone": item["tone"],
                }
            )

        result = [{"date": day, "songs": songs}
                  for day, songs in grouped.items()]
        return _not_modified_or_response(request, result)


class TopSongsAPI(APIView):
    def get(self, request):
        qs = (
            Played.objects.values("song__title")
            .annotate(play_count=Count("song"))
            .order_by("-play_count")
        )
        result = list(qs)
        return _not_modified_or_response(request, result)


class TopTonesAPI(APIView):
    def get(self, request):
        qs = (
            Played.objects.values("tone")
            .annotate(tone_count=Count("tone"))
            .order_by("-tone_count")
        )
        result = list(qs)
        return _not_modified_or_response(request, result)


class SuggestedSongsAPI(APIView):
    def get(self, request):
        return Response(self.get_suggested_songs())

    def get_suggested_songs(self):
        three_months_ago = now() - timedelta(days=90)
        suggested = []
        used_song_ids = set()

        recent_songs = Played.objects.filter(date__gte=three_months_ago).values_list(
            "song_id", flat=True
        )

        for position in range(1, 5):
            qs = (
                Played.objects.select_related("song")
                .filter(position=position, date__lt=three_months_ago)
                .exclude(song_id__in=recent_songs)
                .exclude(song_id__in=used_song_ids)
            )

            if qs.exists():
                chosen = random.choice(list(qs))
                used_song_ids.add(chosen.song_id)

                data = PlayedSerializer(chosen).data
                data["position"] = position  # garante o campo
                suggested.append(data)

        suggested.sort(key=lambda x: x.get("position", 0))
        return suggested
