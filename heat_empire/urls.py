from django.urls import path
from django.views.generic import TemplateView

from .content import HEATING_SYSTEMS, WORK_STAGES

urlpatterns = [
    path(
        "",
        TemplateView.as_view(
            template_name="home.html",
            extra_context={"heating_systems": HEATING_SYSTEMS, "work_stages": WORK_STAGES},
        ),
        name="home",
    ),
]
