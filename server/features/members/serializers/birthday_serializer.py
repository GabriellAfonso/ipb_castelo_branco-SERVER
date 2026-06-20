from typing import Any

from rest_framework import serializers


class BirthdayQueryParamSerializer(serializers.Serializer[Any]):
    month = serializers.IntegerField(required=True, min_value=1, max_value=12)


class BirthdayResponseSerializer(serializers.Serializer[Any]):
    name = serializers.CharField()
    gender = serializers.CharField(allow_null=True)
    birth_day = serializers.IntegerField()
