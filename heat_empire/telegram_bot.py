import json
from datetime import timedelta
from hmac import compare_digest
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import TelegramDelivery, TelegramSubscriber


class TelegramError(Exception):
    def __init__(self, code, retry_after=0):
        self.code = code
        self.retry_after = retry_after
        super().__init__(f"Telegram API error ({code})")


class TelegramAPI:
    def __init__(self, token):
        self.base_url = f"https://api.telegram.org/bot{token}"

    def call(self, method, **params):
        request = Request(
            f"{self.base_url}/{method}",
            data=json.dumps(params).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            try:
                response = urlopen(request, timeout=20)
            except HTTPError as error:
                response = error
            with response:
                payload = json.load(response)
        except (OSError, URLError, ValueError):
            raise TelegramError(503) from None
        if not payload["ok"]:
            raise TelegramError(payload["error_code"], payload.get("parameters", {}).get("retry_after", 0))
        return payload["result"]


class TelegramBot:
    def __init__(self, api, pin):
        self.api = api
        self.pin = pin
        self.fingerprint = salted_hmac("heat-empire-telegram-pin", pin, algorithm="sha256").hexdigest()

    def has_access(self, subscriber):
        return subscriber.active and compare_digest(subscriber.pin_fingerprint, self.fingerprint)

    @transaction.atomic
    def handle_update(self, update):
        message = update.get("message", {})
        chat = message.get("chat", {})
        if chat.get("type") != "private" or not isinstance(message.get("text"), str):
            return
        chat_id, update_id = chat["id"], update["update_id"]
        text = message["text"].strip()
        command = text.split(maxsplit=1)[0].split("@", 1)[0] if text else ""
        if command == "/start":
            subscriber, _ = TelegramSubscriber.objects.get_or_create(chat_id=chat_id)
        else:
            subscriber = TelegramSubscriber.objects.filter(pk=chat_id).first()
        if subscriber is None or subscriber.last_update_id == update_id:
            return

        subscriber.last_update_id = update_id
        reply = self.process_message(subscriber, command, text)
        subscriber.save()
        if reply:
            TelegramDelivery.objects.create(subscriber=subscriber, text=reply)

    def process_message(self, subscriber, command, text):
        if command == "/stop":
            subscriber.active = False
            subscriber.pin_fingerprint = ""
            return None
        if command == "/start":
            subscriber.active = True
            if self.has_access(subscriber):
                return "Вы получаете рассылку и уведомления о заявках. Чтобы отписаться, отправьте /stop."
            return (
                "Вы подписаны на рассылку. Чтобы получать уведомления о новых заявках, "
                "введите PIN-код. Чтобы отписаться, отправьте /stop."
            )
        if not subscriber.active or self.has_access(subscriber) or command.startswith("/"):
            return None

        now = timezone.now()
        if subscriber.pin_blocked_until and subscriber.pin_blocked_until > now:
            return "Слишком много попыток. Попробуйте позже."
        if subscriber.pin_blocked_until:
            subscriber.pin_attempts = 0
            subscriber.pin_blocked_until = None

        if compare_digest(text.encode(), self.pin.encode()):
            subscriber.pin_fingerprint = self.fingerprint
            subscriber.pin_attempts = 0
            return "PIN принят. Вы будете получать уведомления о новых заявках."

        subscriber.pin_attempts += 1
        if subscriber.pin_attempts >= 5:
            subscriber.pin_blocked_until = now + timedelta(minutes=15)
            return "Слишком много попыток. Повторите через 15 минут."
        return "Неверный PIN-код. Попробуйте ещё раз."

    def flush(self):
        deliveries = list(TelegramDelivery.objects.filter(
            status=TelegramDelivery.Status.PENDING,
            available_at__lte=timezone.now(),
        ).order_by("available_at", "pk")[:20])
        for delivery in deliveries:
            # Refresh subscriptions so an admin change during a batch takes effect.
            subscriber = TelegramSubscriber.objects.filter(pk=delivery.subscriber_id).first()
            if subscriber is None:
                continue
            if not subscriber.active or (delivery.requires_pin and not self.has_access(subscriber)):
                delivery.status = TelegramDelivery.Status.SKIPPED
            else:
                try:
                    self.api.call("sendMessage", chat_id=subscriber.chat_id, text=delivery.text)
                except TelegramError as error:
                    self.handle_delivery_error(delivery, subscriber, error)
                    if error.code == 429:
                        return error.retry_after or 1
                    continue
                delivery.status = TelegramDelivery.Status.SENT
                sleep(0.06)
            delivery.save(update_fields=("status",))
        return 0

    @staticmethod
    def handle_delivery_error(delivery, subscriber, error):
        if error.code == 403:
            TelegramSubscriber.objects.filter(pk=subscriber.pk).update(active=False, pin_fingerprint="")
            delivery.status = TelegramDelivery.Status.SKIPPED
        elif error.code == 429:
            delivery.available_at = timezone.now() + timedelta(seconds=error.retry_after or 1)
        elif error.code >= 500 and delivery.attempts < 7:
            delivery.attempts += 1
            delivery.available_at = timezone.now() + timedelta(seconds=min(900, 5 * 2**delivery.attempts))
        elif error.code == 401:
            raise error
        else:
            delivery.status = TelegramDelivery.Status.FAILED
        delivery.save(update_fields=("status", "attempts", "available_at"))
