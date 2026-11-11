from http import HTTPStatus

from django.conf import settings
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import TemplateView

from .content import HEATING_SYSTEMS, WORK_STAGES
from .forms import QuoteRequestForm
from .models import LegalPage, QuoteRequest, SiteContacts
from .telegram_queue import enqueue_quote_notice


class HomeView(TemplateView):
    template_name = "home.html"
    extra_context = {"heating_systems": HEATING_SYSTEMS, "work_stages": WORK_STAGES}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contacts"] = SiteContacts.objects.get(pk=1)
        context["preview_mode"] = settings.PREVIEW_MODE
        context.setdefault("quote_form", QuoteRequestForm(prefix=QuoteRequest.Source.SECTION))
        context.setdefault("modal_form", QuoteRequestForm(prefix=QuoteRequest.Source.MODAL))
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(quote_received=request.session.pop("quote_received", False))
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        if settings.PREVIEW_MODE:
            return HttpResponseForbidden("В режиме предпросмотра заявки не отправляются.")

        source = request.POST.get("source")
        if source not in QuoteRequest.Source.values:
            return HttpResponseBadRequest("Неизвестная форма заявки.")

        form = QuoteRequestForm(request.POST, prefix=source)
        if form.is_valid():
            quote = form.save(commit=False)
            quote.source = source
            with transaction.atomic():
                quote.save()
                enqueue_quote_notice(quote)
            request.session["quote_received"] = True
            return HttpResponseRedirect(reverse("home"), status=HTTPStatus.SEE_OTHER)

        form_key = "modal_form" if source == QuoteRequest.Source.MODAL else "quote_form"
        context = self.get_context_data(**{form_key: form})
        return self.render_to_response(context, status=HTTPStatus.UNPROCESSABLE_ENTITY)


def page_not_found(request, exception):
    return render(request, "404.html", {"contacts": SiteContacts.objects.get(pk=1)}, status=404)


def legal_page(request, kind):
    page = get_object_or_404(LegalPage, pk=kind)
    return render(request, "legal-page.html", {"page": page, "contacts": SiteContacts.objects.get(pk=1)})
