from django.urls import path
from django.views.generic import TemplateView

from .content import HEATING_SYSTEMS

urlpatterns = [
    path(
        "",
        TemplateView.as_view(
            template_name="home.html",
            extra_context={"heating_systems": HEATING_SYSTEMS},
        ),
        name="home",
    ),
]
