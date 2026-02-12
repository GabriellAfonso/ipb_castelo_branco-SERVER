from dependency_injector import containers, providers

# # Repositórios (infra)
# from infrastructure.database.repositories.django_user_repository import DjangoUserRepository

# # Serviços externos (infra)
# from infrastructure.services.smtp_email_service import SmtpEmailService

# # Use cases (application)
# from core.application.use_cases.create_user import CreateUserUseCase


class Container(containers.DeclarativeContainer):

    wiring_config = containers.WiringConfiguration(
        packages=["apps.api"]  # onde a injeção poderá acontecer (views, etc.)
    )

#     # 🔹 Infra
#     user_repository = providers.Factory(DjangoUserRepository)
#     email_service = providers.Factory(SmtpEmailService)

#     # 🔹 Use Cases
#     create_user_use_case = providers.Factory(
#         CreateUserUseCase,
#         user_repo=user_repository,
#         email_service=email_service,
#     )
