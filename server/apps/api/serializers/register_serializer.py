from typing import Any
from rest_framework import serializers
from core.application.dtos.auth_dtos import RegisterDTO
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from typing import TypedDict


class RegisterData(TypedDict):
    username: str
    first_name: str
    last_name: str
    password: str
    password_confirm: str


class RegisterSerializer(serializers.Serializer[RegisterData]):
    username = serializers.CharField(
        max_length=150,
        error_messages={
            "blank": _("Este campo não pode ficar em branco."),
            "required": _("Este campo é obrigatório."),
        },
    )
    first_name = serializers.CharField(
        max_length=30,
        error_messages={
            "blank": _("Este campo não pode ficar em branco."),
            "required": _("Este campo é obrigatório."),
        },
    )
    last_name = serializers.CharField(
        max_length=150,
        error_messages={
            "blank": _("Este campo não pode ficar em branco."),
            "required": _("Este campo é obrigatório."),
        },
    )
    password = serializers.CharField(
        write_only=True,
        min_length=6,
        error_messages={
            "min_length": _("A senha precisa ter ao menos 6 caracteres."),
            "blank": _("Este campo não pode ficar em branco."),
            "required": _("Este campo é obrigatório."),
        },
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        allow_blank=True,
        min_length=6,
        error_messages={
            "min_length": _("A senha precisa ter ao menos 6 caracteres."),
            "blank": _("Este campo não pode ficar em branco."),
            "required": _("Este campo é obrigatório."),
        },
    )

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        if data.get("password") != data.get("password_confirm"):
            raise serializers.ValidationError({
                "password_confirm": [_("As senhas não coincidem.")]
            })
        return data

    def create_dto(self) -> RegisterDTO:
        return RegisterDTO(
            username=self.validated_data.get("username"),
            password=self.validated_data.get("password"),
            first_name=self.validated_data.get("first_name"),
            last_name=self.validated_data.get("last_name"),
        )
