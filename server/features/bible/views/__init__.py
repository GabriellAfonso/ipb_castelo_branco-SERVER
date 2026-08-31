from dependency_injector.wiring import Provide, inject
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from config.di import Container
from features.bible.services import BibleService


class BibleListView(APIView):
    permission_classes = [AllowAny]

    # Both bible routes generate the operationId "bible_retrieve" otherwise, and
    # drf-spectacular resolves the clash with a numeral suffix — which would name the
    # generated Android client methods after collision order instead of intent.
    @extend_schema(operation_id="bible_versions_list")
    @inject
    def get(
        self,
        request: Request,
        bible_service: BibleService = Provide[Container.bible_service],
    ) -> Response:
        versions = bible_service.list_versions()
        return Response({"versions": versions}, status=status.HTTP_200_OK)


class BibleDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(operation_id="bible_version_retrieve")
    @inject
    def get(
        self,
        request: Request,
        name: str,
        bible_service: BibleService = Provide[Container.bible_service],
    ) -> Response:
        # BibleVersionNotFound bubbles up to custom_exception_handler
        books = bible_service.get_version(name)
        return Response(
            [book.model_dump() for book in books],
            status=status.HTTP_200_OK,
        )
