"""mrvn URL Configuration"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

# update displayed header/title
admin.site.site_header = settings.SITE_HEADER
admin.site.site_title = settings.SITE_TITLE

urlpatterns = [
    path("", include(("commons.urls", "commons"), namespace="commons")),
    path("admin/", admin.site.urls),
    path("api/v1/", include(("agents.urls", "agents"), namespace="agents")),
]
