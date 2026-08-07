from typing import Any

from django.db import models
from django.utils import timezone

from core.models import ChurchService

# The `schedule_type` field names below point at ChurchService, which reads oddly on
# purpose. They surface directly as `schedule_type_id` in the rota preview and save
# payloads that the Android app sends and receives, so renaming them would change the
# wire format. See specs/007-unify-service-catalogue/research.md R-07.


class MemberScheduleConfig(models.Model):
    member = models.ForeignKey("members.Member", on_delete=models.CASCADE)
    # PROTECT so a service can never be deleted out from under its configuration.
    # Deactivate the service instead; see specs/007-unify-service-catalogue/research.md R-01.
    schedule_type = models.ForeignKey(ChurchService, on_delete=models.PROTECT)
    available = models.BooleanField(default=True)
    weight = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("member", "schedule_type")

    def __str__(self) -> str:
        return f"{self.member.name} - {self.schedule_type.name}"


class MonthlySchedule(models.Model):
    year = models.PositiveIntegerField(editable=False)
    month = models.PositiveSmallIntegerField(editable=False)

    date = models.DateField()
    # PROTECT, not CASCADE: rota rows are a record of what actually happened. Deleting a
    # service must never erase months of history — and once the service catalogue is shared
    # (feature 007), that deletion is reachable from an admin endpoint. See research.md R-01.
    schedule_type = models.ForeignKey(ChurchService, on_delete=models.PROTECT)
    member = models.ForeignKey("members.Member", on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        unique_together = ("schedule_type", "date")

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.date:
            self.year = self.date.year
            self.month = self.date.month
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.member.name} - {self.date.strftime('%d/%m/%Y')} - {self.schedule_type.name}"
