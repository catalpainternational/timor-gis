from django.urls import path

from timor_locations.api import api
from django.contrib import admin



app_name = "timor_locations"

urlpatterns = [
    path("api/", api.urls),
    path("admin/", admin.site.urls),

]
