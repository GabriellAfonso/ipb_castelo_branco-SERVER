from dependency_injector.wiring import Provide, inject
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from config.di import Container
from core.http.permissions import IsMemberUser
from features.members.services.member_service import MemberService


class MemberListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsMemberUser]

    @inject
    def get(
        self,
        request: Request,
        member_service: MemberService = Provide[Container.member_service],
    ) -> Response:
        members = member_service.list_active_members()
        data = {"members": [m.model_dump() for m in members]}
        return Response(data, status=status.HTTP_200_OK)
