from django.contrib import admin

from apps.gallery.models.gallery import Album, Photo

admin.site.register([Album, Photo])
