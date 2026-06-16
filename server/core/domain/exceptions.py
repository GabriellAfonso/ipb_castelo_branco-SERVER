class DomainError(Exception):
    """Base exception for all domain errors.

    Every subclass inherits ``error_code`` for machine-readable identification
    and can override ``extra_context()`` to attach domain data to error responses.

    >>> raise DomainError("something broke")
    """

    error_code: str = "DOMAIN_ERROR"

    def extra_context(self) -> dict[str, object]:
        """Return additional domain data to include in the error response."""
        return {}


class NotFoundError(DomainError):
    """Raised when a requested entity does not exist."""

    error_code: str = "NOT_FOUND"


class ConflictError(DomainError):
    """Raised when an operation conflicts with existing state."""

    error_code: str = "CONFLICT"


class ValidationError(DomainError):
    """Raised when input validation fails at the domain level."""

    error_code: str = "VALIDATION_ERROR"


class AuthenticationError(DomainError):
    """Raised when authentication fails."""

    error_code: str = "AUTHENTICATION_FAILED"


class BibleVersionNotFound(NotFoundError):
    """Raised when a requested Bible version does not exist."""

    def __init__(self, version: str) -> None:
        super().__init__(f"Bible version not found: '{version}'")
        self.version = version

    def extra_context(self) -> dict[str, object]:
        return {"version": self.version}


class UsernameAlreadyExistsError(ConflictError):
    def __init__(self, username: str) -> None:
        super().__init__(f"Username already exists: '{username}'")
        self.username = username

    def extra_context(self) -> dict[str, object]:
        return {"username": self.username}


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

    def extra_context(self) -> dict[str, object]:
        return {"email": self.email}


class ProfileNotFoundError(NotFoundError):
    def __init__(self, user_id: str) -> None:
        super().__init__(f"Profile not found for user: '{user_id}'")
        self.user_id = user_id

    def extra_context(self) -> dict[str, object]:
        return {"user_id": self.user_id}


class ChordChartNotFoundError(NotFoundError):
    def __init__(self, pk: int) -> None:
        super().__init__(f"Chord chart not found: id={pk}")
        self.pk = pk

    def extra_context(self) -> dict[str, object]:
        return {"pk": self.pk}


class LyricsNotFoundError(NotFoundError):
    def __init__(self, pk: int) -> None:
        super().__init__(f"Lyrics not found: id={pk}")
        self.pk = pk

    def extra_context(self) -> dict[str, object]:
        return {"pk": self.pk}


class SongsNotFoundError(NotFoundError):
    """Raised when one or more songs are not found."""

    def __init__(self, missing_ids: list[int]) -> None:
        super().__init__(f"Some songs were not found: {missing_ids}")
        self.missing_ids = missing_ids

    def extra_context(self) -> dict[str, object]:
        return {"missing_song_ids": self.missing_ids}


class ScheduleOverwriteError(ValidationError):
    """Raised when trying to overwrite a schedule past the allowed window."""

    def __init__(self, month: int, year: int) -> None:
        super().__init__(
            f"A escala de {month:02d}/{year} foi criada há mais de 30 minutos. "
            "Por segurança, não é mais possível sobrescrevê-la."
        )
        self.month = month
        self.year = year
