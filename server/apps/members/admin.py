from django.contrib import admin

from apps.members.models.member import Member, MemberStatus, Ministry, Role

admin.site.register([Member, MemberStatus, Role, Ministry])
