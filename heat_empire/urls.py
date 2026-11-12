from django.contrib import admin
from django.urls import path

from .catalog import catalog_detail, catalog_index
from .models import LegalPage
from .views import HomeView, legal_page

handler404 = "heat_empire.views.page_not_found"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("catalog/", catalog_index, name="catalog"),
    path("catalog/<slug:slug>/", catalog_detail, name="catalog-detail"),
    path("privacy-policy/", legal_page, {"kind": LegalPage.Kind.PRIVACY}, name="privacy-policy"),
    path("company-details/", legal_page, {"kind": LegalPage.Kind.COMPANY}, name="company-details"),
    path("", HomeView.as_view(), name="home"),
]
