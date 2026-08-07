"""The church's catalogue of recurring services.

Shared by the rota (`features.schedule`) and the hymn view history
(`features.songs`), which the constitution forbids importing from each other.

**Weekday convention: `1 = Sunday … 7 = Saturday`** — see `core/domain/weekday.py`.
Sunday is 1, not 0 and not 6. The two conventions in this codebase overlap
numerically, so never compare a stored weekday against `datetime.weekday()` directly.

This model took over the existing `schedule_scheduletype` table rather than being
created fresh, so the ids the Android app caches stay valid. Feature 007 moved it
here without a single row changing.
"""

from django.db import models
from django.db.models import F, Q

MIN_WEEKDAY = 1  # Sunday
MAX_WEEKDAY = 7  # Saturday


class ChurchService(models.Model):
    name = models.CharField(max_length=100)
    weekday = models.PositiveSmallIntegerField()
    start_time = models.TimeField()
    # The *scheduled* end. Hymn view matching runs past it by
    # HymnalHistorySettings.window_grace_minutes, because services run long.
    end_time = models.TimeField()
    # Is this service currently held?
    active = models.BooleanField(default=True)
    # Does it take a member rota? Independent of `active`: Escola Bíblica Dominical
    # is held every Sunday and nobody is rostered for it, so it groups hymn views
    # but never generates rota rows. Marking it inactive instead would wrongly hide
    # it from the hymnal dashboard, which is the one place it matters.
    takes_rota = models.BooleanField(default=True)

    class Meta:
        db_table = "core_churchservice"
        ordering = ["weekday", "start_time"]
        verbose_name = "church service"
        verbose_name_plural = "church services"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="church_service_end_after_start",
            ),
            models.CheckConstraint(
                condition=Q(weekday__gte=MIN_WEEKDAY) & Q(weekday__lte=MAX_WEEKDAY),
                name="church_service_weekday_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} - {self.id}"
