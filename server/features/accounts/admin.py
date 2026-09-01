from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from features.accounts.models.profile import Profile
from features.accounts.models.user import User


admin.site.register(Profile)


@admin.register(User)
class MyUserAdmin(BaseUserAdmin):  # type: ignore[type-arg]
    # is_active is the switch that actually revokes access — SimpleJWT checks it on every
    # authenticated request. It was not in the list, so there was no way to see at a glance
    # who is blocked.
    list_display = ("username", "is_active", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets
