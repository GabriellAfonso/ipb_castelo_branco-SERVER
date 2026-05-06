from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from features.bible.loader import BIBLES


class BibleListView(APIView):
    permission_classes = [AllowAny]

    @staticmethod
    def get(request: Request) -> Response:
        return Response({"versions": sorted(BIBLES.keys())}, status=status.HTTP_200_OK)


class BibleDetailView(APIView):
    permission_classes = [AllowAny]

    @staticmethod
    def get(request: Request, name: str) -> Response:
        if name not in BIBLES:
            return Response({"detail": "Version not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BIBLES[name], status=status.HTTP_200_OK)
