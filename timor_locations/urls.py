from django.contrib import admin
from django.urls import path

from timor_locations.api import api

app_name = "timor_locations"

urlpatterns = [
    path("api/", api.urls),
    path("admin/", admin.site.urls),
]
