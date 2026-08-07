from datetime import timedelta

from django.utils import timezone

from core.time.clock import SystemClock


class TestSystemClock:
    def test_now_is_timezone_aware(self) -> None:
        assert SystemClock().now().tzinfo is not None

    def test_now_is_close_to_django_now(self) -> None:
        assert abs(SystemClock().now() - timezone.now()) < timedelta(seconds=5)
