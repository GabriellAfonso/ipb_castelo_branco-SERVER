import re
import random
from datetime import timedelta
from django.utils.timezone import now
from django.db.models import Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status
from collections import defaultdict
from main.models.songs import Played
from main.serializers import PlayedSerializer
from main.services.monthly_scheduler import generate_monthly_schedule
from main.models.schedule import MonthlySchedule
from datetime import date


class SongsBySundayAPI(APIView):
    def get(self, request):
        qs = (
            Played.objects
            .select_related('song')
            .order_by('-date', 'position')
        )

        data = PlayedSerializer(qs, many=True).data
        grouped = defaultdict(list)

        for item in data:
            grouped[item['date']].append({
                "position": item['position'],
                "song": item['song']['title'],
                "artist": item['song']['artist'],
                "tone": item['tone'],
            })

        return Response([
            {
                "date": date,
                "songs": songs
            }
            for date, songs in grouped.items()
        ])

# class LastSongsAPI(APIView):
#     def get(self, request):
#         qs = Played.objects.select_related(
#             'song').order_by('-date', 'position')[:50]
#         return Response(PlayedSerializer(qs, many=True).data)


class TopSongsAPI(APIView):
    def get(self, request):
        qs = (
            Played.objects
            .values('song__title')
            .annotate(play_count=Count('song'))
            .order_by('-play_count')[:20]
        )
        return Response(qs)


class TopTonesAPI(APIView):
    def get(self, request):
        qs = (
            Played.objects
            .values('tone')
            .annotate(tone_count=Count('tone'))
            .order_by('-tone_count')
        )
        return Response(qs)


class SuggestedSongsAPI(APIView):
    def get(self, request):
        return Response(self.get_suggested_songs())

    def get_suggested_songs(self):
        three_months_ago = now() - timedelta(days=90)
        suggested = {}
        used_song_ids = set()

        recent_songs = Played.objects.filter(
            date__gte=three_months_ago
        ).values_list("song_id", flat=True)

        for position in range(1, 5):
            qs = (
                Played.objects
                .select_related('song')
                .filter(position=position, date__lt=three_months_ago)
                .exclude(song_id__in=recent_songs)
                .exclude(song_id__in=used_song_ids)
            )

            if qs.exists():
                chosen = random.choice(list(qs))
                used_song_ids.add(chosen.song_id)
                suggested[position] = PlayedSerializer(chosen).data

        return suggested


class GenerateMonthlyScheduleAPIView(APIView):
    def post(self, request):
        generate_monthly_schedule()

        today = date.today()

        schedules = (
            MonthlySchedule.objects
            .filter(year=today.year, month=today.month)
            .select_related("member", "schedule_type")
            .order_by("schedule_type__name", "date")
        )

        grouped = defaultdict(lambda: {"time": None, "items": []})

        for s in schedules:
            key = s.schedule_type.name

            grouped[key]["time"] = s.schedule_type.time.strftime("%H:%M")
            grouped[key]["items"].append({
                "day": s.date.day,
                "member": s.member.name
            })

        return Response({
            "year": today.year,
            "month": today.month,
            "schedule": grouped
        })
