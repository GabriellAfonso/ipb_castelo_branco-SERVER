from datetime import datetime
from typing import Any

from dependency_injector.wiring import Provide, inject
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from config.di import Container
from core.http.permissions import IsAdminUser
from features.songs.dtos import PlayInput
from features.songs.services.register_plays_service import (
    RegisterPlaysService,
    SongsNotFoundError,
)


class RegisterSundayPlaysAPI(APIView):
    """POST: create Played records for a given date.

    Requires: authenticated user with admin profile.

    Expected payload:
    {
      "date": "2026-02-07",
      "plays": [
        {"song_id": 12, "position": 1, "tone": "G"},
        {"song_id": 55, "position": 2, "tone": "A#"}
      ]
    }
    """

    permission_classes = [IsAdminUser]

    @inject
    def post(
        self,
        request: Request,
        register_service: RegisterPlaysService = Provide[Container.register_plays_service],
    ) -> Response:
        payload = request.data or {}
        date_str = (payload.get("date") or "").strip()
        plays_raw = payload.get("plays")

        if not date_str:
            return Response({"detail": "Missing field: date."}, status=400)
        if not isinstance(plays_raw, list) or not plays_raw:
            return Response(
                {"detail": "Missing/invalid field: plays (must be a non-empty list)."}, status=400
            )

        try:
            date_value = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        play_inputs = self._validate_play_items(plays_raw)
        if isinstance(play_inputs, Response):
            return play_inputs

        try:
            created = register_service.register(date_value, play_inputs)
        except SongsNotFoundError as e:
            return Response(
                {"detail": "Some songs were not found.", "missing_song_ids": e.missing_ids},
                status=400,
            )

        return Response({"created": created}, status=201)

    @staticmethod
    def _validate_play_items(plays_raw: list[Any]) -> list[PlayInput] | Response:
        """Parse and validate each play item from raw payload."""
        result: list[PlayInput] = []

        for idx, item in enumerate(plays_raw):
            if not isinstance(item, dict):
                return Response({"detail": f"plays[{idx}] must be an object."}, status=400)

            song_id = item.get("song_id")
            position = item.get("position")
            tone = (item.get("tone") or "").strip()

            if song_id is None or position is None:
                return Response(
                    {"detail": f"plays[{idx}] song_id/position must be integers."}, status=400
                )

            try:
                song_id_int = int(song_id)
                position_int = int(position)
            except (TypeError, ValueError):
                return Response(
                    {"detail": f"plays[{idx}] song_id/position must be integers."}, status=400
                )

            if position_int < 1 or position_int > 10:
                return Response(
                    {"detail": f"plays[{idx}] position must be between 1 and 10."}, status=400
                )

            result.append(PlayInput(song_id=song_id_int, position=position_int, tone=tone))

        return result
