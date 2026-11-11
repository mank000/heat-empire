from django.contrib import admin
from django.urls import path

from .views import HomeView

handler404 = "heat_empire.views.page_not_found"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", HomeView.as_view(), name="home"),
]
