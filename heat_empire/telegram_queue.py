from django.db import transaction
from django.utils import timezone

from .models import TelegramBroadcast, TelegramDelivery, TelegramSubscriber


def enqueue_quote_notice(quote):
    recipients = TelegramSubscriber.objects.filter(active=True).exclude(pin_fingerprint="")
    TelegramDelivery.objects.bulk_create(
        TelegramDelivery(subscriber_id=chat_id, text=f"Новая заявка №{quote.pk}. Подробности в админке.", requires_pin=True)
        for chat_id in recipients.values_list("chat_id", flat=True)
    )


@transaction.atomic
def enqueue_broadcast(broadcast_id):
    now = timezone.now()
    updated = TelegramBroadcast.objects.filter(pk=broadcast_id, queued_at__isnull=True).update(queued_at=now)
    if not updated:
        return 0
    broadcast = TelegramBroadcast.objects.get(pk=broadcast_id)
    recipients = TelegramSubscriber.objects.filter(active=True).values_list("chat_id", flat=True)
    deliveries = TelegramDelivery.objects.bulk_create(
        TelegramDelivery(subscriber_id=chat_id, broadcast=broadcast, text=broadcast.text)
        for chat_id in recipients
    )
    if not deliveries:
        TelegramBroadcast.objects.filter(pk=broadcast_id).update(queued_at=None)
    return len(deliveries)
