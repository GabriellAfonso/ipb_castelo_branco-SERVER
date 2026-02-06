import re
from datetime import datetime

from django.shortcuts import redirect, render
from django.views import View

from main.models.songs import Played, Song


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
        context = {"notes": notes, "musics": musics}
        return render(request, self.template_name, context)

    def post(self, request):
        date_str = request.POST.get("date")

        if not date_str:
            return redirect("main:register_sundays")

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
        return render(request, "main/unauthorized.html")
