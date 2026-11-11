from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import TelegramBotSettings, TelegramSubscriber
from .telegram_bot import TelegramBot
from .telegram_credentials import load_credentials


@override_settings(SECRET_KEY="local-testing-secret-only-000000000000000000000000000000")
class TelegramSettingsTests(TestCase):
    def setUp(self):
        self.url = reverse("admin:heat_empire_telegrambotsettings_change", args=[1])
        self.client.force_login(get_user_model().objects.create_superuser(username="admin"))

    def test_credentials_saved_without_exposing_secrets(self):
        token = "123:fake-test-token"
        pin = "01234567"
        self.assertEqual(self.client.post(self.url, {"bot_token": token, "access_pin": pin}).status_code, 302)
        stored = TelegramBotSettings.objects.get()
        self.assertNotIn(token, stored.encrypted_token)
        self.assertNotIn(pin, stored.pin_hash)
        self.assertTrue(check_password(pin, stored.pin_hash))

        page = self.client.get(self.url)
        self.assertNotContains(page, token)
        self.assertNotContains(page, pin)
        self.assertEqual(self.client.post(self.url, {"bot_token": "", "access_pin": ""}).status_code, 302)

        credentials = load_credentials()
        self.assertEqual(credentials.token, token)
        self.assertTrue(credentials.pin_is_hashed)
        bot = TelegramBot(Mock(), credentials.pin, credentials.pin_is_hashed)
        for update_id, message in enumerate(("/start", pin), start=1):
            bot.handle_update({
                "update_id": update_id,
                "message": {"chat": {"id": 501, "type": "private"}, "text": message},
            })
        self.assertTrue(bot.has_access(TelegramSubscriber.objects.get(pk=501)))

        denied = self.client.post(self.url, {"bot_token": "456:different-bot", "access_pin": ""})
        self.assertContains(denied, "Для другого бота нужна отдельная база подписчиков.")
        self.assertEqual(load_credentials().token, token)

    def test_non_superuser_cannot_edit_credentials(self):
        self.client.force_login(get_user_model().objects.create_user(username="staff", is_staff=True))
        self.assertEqual(self.client.get(self.url).status_code, 403)
