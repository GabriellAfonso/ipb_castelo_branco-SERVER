from django.db.models import IntegerField
from django.db.models.functions import Cast, Substr
from rest_framework.views import APIView

from main.models.hymnal import Hymn

from .utils import _not_modified_or_response


class hymnalAPI(APIView):
    def get(self, request):
        qs = (
            Hymn.objects.annotate(
                number_int=Cast(Substr("number", 1, 10), IntegerField())
            )
            .order_by("number_int", "number")
            .values("number", "title", "lyrics")
        )

        result = list(qs)
        return _not_modified_or_response(request, result)
