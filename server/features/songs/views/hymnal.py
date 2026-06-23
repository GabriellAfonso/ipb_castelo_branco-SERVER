from dependency_injector.wiring import Provide, inject
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from config.di import Container
from core.http.utils import _not_modified_or_response
from features.songs.services.hymnal_service import HymnalService


class HymnalAPI(APIView):
    permission_classes = [AllowAny]

    @inject
    def get(
        self,
        request: Request,
        hymnal_service: HymnalService = Provide[Container.hymnal_service],
    ) -> Response:
        result = hymnal_service.list_hymns()
        return _not_modified_or_response(request, result)
