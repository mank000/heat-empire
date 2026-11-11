from django.contrib import admin
from django.urls import path

from .models import LegalPage
from .views import HomeView, legal_page

handler404 = "heat_empire.views.page_not_found"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("privacy-policy/", legal_page, {"kind": LegalPage.Kind.PRIVACY}, name="privacy-policy"),
    path("company-details/", legal_page, {"kind": LegalPage.Kind.COMPANY}, name="company-details"),
    path("", HomeView.as_view(), name="home"),
]
