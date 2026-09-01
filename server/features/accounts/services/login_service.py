from django.contrib.auth import authenticate
from django.http import HttpRequest

from core.application.dtos.auth_dtos import LoginDTO, TokenDTO
from core.domain.exceptions import InvalidCredentialsError
from core.metrics import LOGIN_COUNTER
from features.accounts.auth.jwt import get_tokens_for_user


class LoginService:
    def login(self, dto: LoginDTO, request: HttpRequest) -> TokenDTO:
        """Exchange credentials for JWT tokens, or raise ``InvalidCredentialsError``.

        The ``request`` is the constitution's single named exception to "services never
        import HTTP objects". django-axes counts and blocks failed attempts per client, and
        its backend raises ``AxesBackendRequestParameterRequired`` when ``authenticate()``
        is called without one — so the parameter is the price of the lockout, not a
        convenience. See specs/008-login-brute-force-lockout/plan.md D-1.

        A locked-out caller does not reach an exception here: ``authenticate()`` returns
        None like any other failure, and ``AxesMiddleware`` replaces the 401 this raises
        with the 429 from ``core.http.lockout``.

        >>> service.login(LoginDTO(username="ana", password="..."), request).access
        'eyJhbGciOi...'
        """
        user = authenticate(request=request, username=dto.username, password=dto.password)
        if user is None:
            LOGIN_COUNTER.labels(result="failure", login_type="credentials").inc()
            raise InvalidCredentialsError()

        LOGIN_COUNTER.labels(result="success", login_type="credentials").inc()
        return get_tokens_for_user(user)
