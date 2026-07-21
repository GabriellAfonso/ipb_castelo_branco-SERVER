from typing import Any

from rest_framework import serializers


class MonthRangeField(serializers.Field):  # type: ignore[type-arg]
    """Accepts month as single int (M) or range (M-M).

    Returns a tuple (start_month, end_month).

    >>> field.to_internal_value("7")
    (7, 7)
    >>> field.to_internal_value("1-6")
    (1, 6)
    """

    default_error_messages = {
        "invalid_format": "Month must be in format M or M-M (e.g., 7 or 1-6).",
        "out_of_range": "Month values must be between 1 and 12.",
        "start_greater_than_end": "Start month must be less than or equal to end month.",
    }

    def to_internal_value(self, data: Any) -> tuple[int, int]:
        raw = str(data).strip()
        if not raw:
            self.fail("required")

        parts = raw.split("-")
        if len(parts) == 1:
            return self._parse_single(parts[0])
        if len(parts) == 2:
            return self._parse_range(parts[0], parts[1])
        self.fail("invalid_format")

    def _parse_single(self, value: str) -> tuple[int, int]:
        try:
            month = int(value)
        except ValueError:
            self.fail("invalid_format")
        self._validate_range(month)
        return (month, month)

    def _parse_range(self, start_raw: str, end_raw: str) -> tuple[int, int]:
        try:
            start = int(start_raw)
            end = int(end_raw)
        except ValueError:
            self.fail("invalid_format")
        self._validate_range(start)
        self._validate_range(end)
        if start > end:
            self.fail("start_greater_than_end")
        return (start, end)

    def _validate_range(self, month: int) -> None:
        if month < 1 or month > 12:
            self.fail("out_of_range")

    def to_representation(self, value: Any) -> Any:
        return value


class BirthdayQueryParamSerializer(serializers.Serializer[Any]):
    month = MonthRangeField(required=True)


class BirthdayResponseSerializer(serializers.Serializer[Any]):
    name = serializers.CharField()
    gender = serializers.CharField(allow_null=True)
    birth_month = serializers.IntegerField()
    birth_day = serializers.IntegerField()
