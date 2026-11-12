from django.db import transaction

from .telegram_queue import enqueue_quote_notice


@transaction.atomic
def save_quote_request(form, *, source, product=None):
    quote = form.save(commit=False)
    quote.source = source
    if product is not None:
        quote.heat_pump = product
    quote.save()
    enqueue_quote_notice(quote)
