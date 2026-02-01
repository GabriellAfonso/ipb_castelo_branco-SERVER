# server: views.py (ou onde estiverem essas APIViews)
import hashlib
import json
from collections import defaultdict
import random
from datetime import timedelta, date
from django.utils.timezone import now
from django.db.models import Count
from rest_framework.views import APIView


from main.models.songs import Played, Song
from main.serializers import PlayedSerializer
from main.services.monthly_scheduler import generate_monthly_schedule
from main.models.schedule import MonthlySchedule
from main.models.hymnal import Hymn
from django.db.models import IntegerField
from django.db.models.functions import Cast, Substr
import re
from .serializers import RegisterSerializer
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.db.models import Q
from datetime import datetime
from django.http import HttpResponse
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.permissions import AllowAny
from django.utils import timezone


def _make_etag_from_data(data) -> str:
    payload = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return f"\"{digest}\""


def _not_modified_or_response(request, data, status_code=200, tag=""):
    etag = _make_etag_from_data(data)
    inm = request.headers.get("If-None-Match")
    inm_clean = inm.strip() if inm else None

    method = getattr(request, "method", "")
    path = getattr(request, "path", "")
    tag_txt = f"[{tag}] " if tag else ""

    if inm_clean and inm_clean == etag:
        print(
            f"{tag_txt}HTTP 304 {method} {path} (If-None-Match={inm_clean}, ETag={etag}) -> sem body")
        resp = Response(status=304)
        resp["ETag"] = etag
        return resp

    print(f"{tag_txt}HTTP 200 {method} {path} (If-None-Match={inm_clean}, ETag={etag}) -> COM body")
    resp = Response(data, status=status_code)
    resp["ETag"] = etag
    return resp


class SongsBySundayAPI(APIView):
    def get(self, request):
        qs = (
            Played.objects
            .select_related("song")
            .order_by("-date", "position")
        )

        data = PlayedSerializer(qs, many=True).data
        grouped = defaultdict(list)

        for item in data:
            grouped[item["date"]].append({
                "position": item["position"],
                "song": item["song"]["title"],
                "artist": item["song"]["artist"],
                "tone": item["tone"],
            })

        result = [
            {"date": day, "songs": songs}
            for day, songs in grouped.items()
        ]

        return _not_modified_or_response(request, result)


class TopSongsAPI(APIView):
    def get(self, request):
        qs = (
            Played.objects
            .values("song__title")
            .annotate(play_count=Count("song"))
            .order_by("-play_count")
        )
        result = list(qs)
        return _not_modified_or_response(request, result)


class TopTonesAPI(APIView):
    def get(self, request):
        qs = (
            Played.objects
            .values("tone")
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

        recent_songs = Played.objects.filter(
            date__gte=three_months_ago
        ).values_list("song_id", flat=True)

        for position in range(1, 5):
            qs = (
                Played.objects
                .select_related("song")
                .filter(position=position, date__lt=three_months_ago)
                .exclude(song_id__in=recent_songs)
                .exclude(song_id__in=used_song_ids)
            )

            if qs.exists():
                chosen = random.choice(list(qs))
                used_song_ids.add(chosen.song_id)

                data = PlayedSerializer(chosen).data
                # garante o campo position no payload (caso o serializer não inclua)
                data["position"] = position

                suggested.append(data)

        # opcional: garantir ordenação
        suggested.sort(key=lambda x: x.get("position", 0))
        return suggested


class GenerateMonthlyScheduleAPI(APIView):
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

        result = {
            "year": today.year,
            "month": today.month,
            "schedule": grouped
        }

        return _not_modified_or_response(request, result, status_code=200)


class hymnalAPI(APIView):
    def get(self, request):
        qs = (
            Hymn.objects
            .annotate(
                number_int=Cast(
                    Substr("number", 1, 10),  # pega a parte numérica inicial
                    IntegerField()
                )
            )
            .order_by("number_int", "number")
            .values("number", "title", "lyrics")
        )

        result = list(qs)
        return _not_modified_or_response(request, result)


class RegisterSundays(View):
    template_name = "main/register_sundays.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect("main:unauthorized")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        notes = ["A", "A#", "Bb", "B", "C", "C#", "Db", "D",
                 "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab"]
        musics = Song.objects.all().order_by("title")
        context = {
            "notes": notes,
            "musics": musics,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        date_str = request.POST.get("date")

        if not date_str:
            return redirect("main:register_sundays")  # ou trate erro

        date_value = datetime.strptime(date_str, "%Y-%m-%d").date()

        musics = [
            (request.POST.get("first_music"),
             request.POST.get("tone_first_music"), 1),
            (request.POST.get("second_music"),
             request.POST.get("tone_second_music"), 2),
            (request.POST.get("third_music"),
             request.POST.get("tone_third_music"), 3),
            (request.POST.get("fourth_music"),
             request.POST.get("tone_fourth_music"), 4),
        ]

        for music_text, tone, position in musics:
            if not music_text:
                continue

            cleaned_title, artist = self.clean_music_title(music_text)

            song = (
                Song.objects.filter(title=cleaned_title, artist=artist).first()
                if artist
                else Song.objects.filter(title=cleaned_title).first()
            )
            if not song:
                continue

            Played.objects.create(
                song=song,
                date=date_value,
                tone=(tone or "").strip(),
                position=position,
            )

        return redirect("main:register_sundays")

    def clean_music_title(self, title: str):
        match = re.match(r"^(.*?)\s*\[(.*?)\]\s*$", title or "")
        if match:
            cleaned_title = match.group(1).strip()
            artist = match.group(2).strip()
            return cleaned_title, artist
        return (title or "").strip(), ""


class Unauthorized(View):

    def get(self, request):
        return render(request, 'main/unauthorized.html')


# class RegisterView(APIView):
#     permission_classes = (AllowAny,)

#     def post(self, request: Request) -> Response:
#         serializer = RegisterSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({"detail": "User registered successfully"}, status=201)

#         return Response(getattr(serializer, "errors"), status=400)


class LoginAPI(APIView):
    def post(self, request: Request) -> Response:
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "token": str(refresh.access_token),
            })
        else:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


class RegisterAPI(APIView):
    authentication_classes = []  # permite acesso sem login
    permission_classes = []      # público

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"detail": "User registered successfully"}, status=201)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
