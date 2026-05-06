from django.urls import path

from features.bible.views import BibleDetailView, BibleListView

app_name = "bible"

urlpatterns = [
    path("api/bible/", BibleListView.as_view(), name="bible-list"),
    path("api/bible/<str:name>/", BibleDetailView.as_view(), name="bible-detail"),
]
