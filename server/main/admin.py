from django.contrib import admin
from main.models.songs import Category, Song, Played
from main.models.profile import Profile
from main.models.schedule import ScheduleType, MemberScheduleConfig, MonthlySchedule
from main.models.hymnal import Hymn
from main.models.member import Member
admin.site.register(Category)
admin.site.register(Song)
admin.site.register(Played)

admin.site.register(Member)
admin.site.register(Profile)
admin.site.register(ScheduleType)
admin.site.register(MemberScheduleConfig)
admin.site.register(MonthlySchedule)

admin.site.register(Hymn)
