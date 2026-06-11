class DomainError(Exception):
    """Base exception for all domain errors."""


class NotFoundError(DomainError):
    """Raised when a requested entity does not exist."""


class ConflictError(DomainError):
    """Raised when an operation conflicts with existing state."""


class ValidationError(DomainError):
    """Raised when input validation fails at the domain level."""


class AuthenticationError(DomainError):
    """Raised when authentication fails."""


class BibleVersionNotFound(NotFoundError):
    """Raised when a requested Bible version does not exist."""

    def __init__(self, version: str) -> None:
        super().__init__(f"Bible version not found: '{version}'")
        self.version = version


class UsernameAlreadyExistsError(ConflictError):
    def __init__(self, username: str) -> None:
        super().__init__(f"Username already exists: '{username}'")
        self.username = username


class InvalidCredentialsError(AuthenticationError):
    def __init__(self) -> None:
        super().__init__("Invalid username or password")


class InvalidGoogleTokenError(AuthenticationError):
    def __init__(self) -> None:
        super().__init__("Invalid Google token")


class UnverifiedGoogleEmailError(ValidationError):
    def __init__(self) -> None:
        super().__init__("Google account has no verified email")


class GoogleUserCreationError(DomainError):
    def __init__(self, email: str) -> None:
        super().__init__("Erro ao criar usuário.")
        self.email = email


class ProfileNotFoundError(NotFoundError):
    def __init__(self, user_id: str) -> None:
        super().__init__(f"Profile not found for user: '{user_id}'")
        self.user_id = user_id
