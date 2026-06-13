from django.db.models import Func, IntegerField, QuerySet, Value
from django.db.models.functions import Cast, NullIf

from features.songs.models.hymnal import Hymn


class DjangoHymnalRepository:
    """Hymnal repository using Django ORM."""

    def list_all_hymns(self) -> QuerySet[Hymn]:
        return Hymn.objects.annotate(
            number_int=Cast(
                NullIf(
                    Func(
                        "number",
                        Value("[^0-9].*"),
                        Value(""),
                        function="REGEXP_REPLACE",
                    ),
                    Value(""),
                ),
                IntegerField(),
            )
        ).order_by("number_int", "number")
