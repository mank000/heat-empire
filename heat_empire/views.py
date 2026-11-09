from django.views.generic import TemplateView

from .content import HEATING_SYSTEMS, WORK_STAGES
from .models import SiteContacts


class HomeView(TemplateView):
    template_name = "home.html"
    extra_context = {"heating_systems": HEATING_SYSTEMS, "work_stages": WORK_STAGES}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contacts"] = SiteContacts.objects.get(pk=1)
        return context
