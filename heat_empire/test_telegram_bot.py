from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import QuoteRequest, TelegramBroadcast, TelegramDelivery, TelegramSubscriber
from .telegram_bot import TelegramBot, TelegramError


class TelegramBotTests(TestCase):
    def setUp(self):
        self.api = Mock()
        self.bot = TelegramBot(self.api, "01234567")

    def update(self, chat_id, text, update_id, chat_type="private"):
        self.bot.handle_update({
            "update_id": update_id,
            "message": {"chat": {"id": chat_id, "type": chat_type}, "text": text},
        })

    @patch("heat_empire.telegram_bot.sleep")
    def test_broadcast_reaches_subscribers_but_quote_notice_requires_pin(self, _sleep):
        self.update(101, "/start", 1)
        self.update(101, "00000000", 2)
        self.update(101, "01234567", 3)
        self.update(102, "/start", 4)
        self.update(103, "/start", 5)
        self.update(103, "/stop", 6)
        self.update(104, "/start", 7, chat_type="group")
        self.bot.flush()
        self.api.reset_mock()

        response = self.client.post(reverse("home"), {
            "source": "section",
            "section-name": "Тестовый посетитель",
            "section-phone": "9001234567",
            "section-area": "125",
            "section-heating": QuoteRequest.Heating.ELECTRIC,
            "section-consent": "on",
        })
        self.assertEqual(response.status_code, 303)
        quote = QuoteRequest.objects.get()
        notice = TelegramDelivery.objects.get(requires_pin=True)
        self.assertEqual(notice.subscriber_id, 101)
        self.assertNotIn(quote.phone, notice.text)
        self.assertNotIn(quote.name, notice.text)

        broadcast = TelegramBroadcast.objects.create(text="Новости проекта")
        self.client.force_login(get_user_model().objects.create_superuser(username="operator"))
        list_url = reverse("admin:heat_empire_telegrambroadcast_changelist")
        for _ in range(2):
            self.assertEqual(self.client.post(list_url, {
                "action": "queue_broadcasts", "index": "0", "_selected_action": [broadcast.pk],
            }).status_code, 302)

        self.assertEqual(set(broadcast.telegramdelivery_set.values_list("subscriber_id", flat=True)), {101, 102})
        self.assertEqual(broadcast.telegramdelivery_set.count(), 2)
        self.bot.flush()
        calls = {(call.kwargs["chat_id"], call.kwargs["text"]) for call in self.api.call.call_args_list}
        self.assertEqual(calls, {(101, notice.text), (101, broadcast.text), (102, broadcast.text)})

    @patch("heat_empire.telegram_bot.sleep")
    def test_pin_lock_and_rotation_prevent_delivery(self, _sleep):
        self.update(101, "/start", 1)
        for i in range(2, 7):
            self.update(101, "неверный PIN", i)
        self.update(101, "01234567", 7)
        subscriber = TelegramSubscriber.objects.get(pk=101)
        self.assertEqual(subscriber.pin_fingerprint, "")
        self.assertIsNotNone(subscriber.pin_blocked_until)

        subscriber.pin_fingerprint = self.bot.fingerprint
        subscriber.save(update_fields=["pin_fingerprint"])
        notice = TelegramDelivery.objects.create(subscriber=subscriber, text="Заявка", requires_pin=True)
        TelegramBot(self.api, "87654321").flush()
        notice.refresh_from_db()
        self.assertEqual(notice.status, TelegramDelivery.Status.SKIPPED)
        self.assertNotIn("Заявка", [call.kwargs["text"] for call in self.api.call.call_args_list])

    def test_rate_limited_message_stays_in_queue(self):
        subscriber = TelegramSubscriber.objects.create(chat_id=101)
        delivery = TelegramDelivery.objects.create(subscriber=subscriber, text="Тест")
        self.api.call.side_effect = TelegramError(429, retry_after=12)

        self.assertEqual(self.bot.flush(), 12)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, TelegramDelivery.Status.PENDING)
        self.assertEqual(self.bot.flush(), 0)
        self.api.call.assert_called_once()
