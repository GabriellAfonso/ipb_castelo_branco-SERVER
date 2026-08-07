"""HTTP-boundary validation for the hymnal view history endpoints.

Per-event validation deliberately lives in the ingest service, not here: a batch
must survive one bad event, and a ``ListSerializer`` would fail the whole request
on the first bad element.
"""

from typing import Any

from rest_framework import serializers

from features.songs.hymnal_history_dtos import GROUP_BY_CHOICES, GROUP_BY_SERVICE
from features.songs.models.hymnal_history import MAX_WEEKDAY, MIN_WEEKDAY

# Sanity rails an admin should get a helpful message about, not database invariants.
SETTINGS_BOUNDS: dict[str, tuple[int, int]] = {
    "min_seconds_to_count": (1, 3600),
    "collapse_window_minutes": (1, 1440),
    "max_batch_size": (1, 1000),
    "max_past_days": (1, 3650),
    "future_tolerance_minutes": (1, 1440),
    "window_grace_minutes": (1, 1440),
}


class _FromDateMixin(serializers.Serializer[Any]):
    """Adds a ``from`` field, which cannot be a class attribute — it is a keyword."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["from"] = serializers.DateField(required=False)


class IngestEnvelopeSerializer(serializers.Serializer[Any]):
    """Validates only the batch envelope. Events are validated one by one downstream."""

    events = serializers.ListField(child=serializers.DictField(), allow_empty=True)


class RejectedEventSerializer(serializers.Serializer[Any]):
    client_event_id = serializers.UUIDField()
    reason = serializers.CharField()


class IngestResultSerializer(serializers.Serializer[Any]):
    accepted = serializers.ListField(child=serializers.UUIDField())
    rejected = RejectedEventSerializer(many=True)


class OccurrenceQueryParamSerializer(_FromDateMixin):
    to = serializers.DateField(required=False)
    group_by = serializers.ChoiceField(
        choices=GROUP_BY_CHOICES, required=False, default=GROUP_BY_SERVICE
    )


class OccurrenceSerializer(serializers.Serializer[Any]):
    hymn_number = serializers.CharField()
    hymn_title = serializers.CharField()
    occurred_on = serializers.DateField()
    service_window_id = serializers.IntegerField(allow_null=True)
    service_window_name = serializers.CharField(allow_null=True)
    bucket = serializers.CharField()
    device_count = serializers.IntegerField()


class TopHymnsQueryParamSerializer(_FromDateMixin):
    to = serializers.DateField(required=False)


class TopHymnSerializer(serializers.Serializer[Any]):
    hymn_number = serializers.CharField()
    hymn_title = serializers.CharField()
    occurrence_count = serializers.IntegerField()


class HymnalHistorySettingsSerializer(serializers.Serializer[Any]):
    """Read and partial-update shape for the settings singleton."""

    min_seconds_to_count = serializers.IntegerField(required=False)
    collapse_window_minutes = serializers.IntegerField(required=False)
    max_batch_size = serializers.IntegerField(required=False)
    max_past_days = serializers.IntegerField(required=False)
    future_tolerance_minutes = serializers.IntegerField(required=False)
    window_grace_minutes = serializers.IntegerField(required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        errors: dict[str, list[str]] = {}
        for field, value in attrs.items():
            low, high = SETTINGS_BOUNDS[field]
            if value < low or value > high:
                errors[field] = [
                    f"Value {value} is out of range. Expected an integer between {low} and {high}."
                ]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class ServiceWindowSerializer(serializers.Serializer[Any]):
    """Weekday is 0=Monday ... 6=Sunday. Sunday is 6, not 0.

    Used for create and, after merging with the stored row, for partial update —
    so a PATCH touching only ``start_time`` is still checked against the existing
    ``end_time`` instead of failing at the database constraint.
    """

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=100)
    weekday = serializers.IntegerField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    active = serializers.BooleanField(required=False, default=True)

    def validate_weekday(self, value: int) -> int:
        if value < MIN_WEEKDAY or value > MAX_WEEKDAY:
            raise serializers.ValidationError(
                f"Value {value} is out of range. Expected an integer between "
                f"{MIN_WEEKDAY} (Monday) and {MAX_WEEKDAY} (Sunday)."
            )
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        start = attrs.get("start_time")
        end = attrs.get("end_time")
        if start is not None and end is not None and end <= start:
            raise serializers.ValidationError(
                {"end_time": [f"end_time {end} must be strictly after start_time {start}."]}
            )
        return attrs
