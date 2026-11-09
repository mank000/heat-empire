from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class SiteContactsTests(TestCase):
    def test_seeded_contacts_are_visible_without_messenger_links(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, 'href="tel:+79241317130"', count=5)
        self.assertContains(response, "г. Санкт-Петербург, г. Колпино,")
        self.assertNotContains(response, 'aria-label="Telegram"')

    def test_admin_changes_are_used_in_every_contact_block(self):
        self.client.force_login(get_user_model().objects.create_superuser(username="editor"))
        change_url = reverse("admin:heat_empire_sitecontacts_change", args=[1])
        new_contacts = {
            "phone": "+7 (900) 123-45-67",
            "telegram_url": "https://t.me/heat_example",
            "whatsapp_url": "https://wa.me/79001234567",
            "max_url": "https://max.ru/heat_example",
            "address": "г. Санкт-Петербург,\nТестовая улица, 1",
        }
        self.assertEqual(self.client.post(change_url, new_contacts).status_code, 302)

        response = self.client.get(reverse("home"))
        self.assertContains(response, 'href="tel:+79001234567"', count=5)
        self.assertContains(response, "+7 (900) 123-45-67", count=4)
        self.assertContains(response, new_contacts["address"])
        for field in ("telegram_url", "whatsapp_url", "max_url"):
            self.assertContains(response, f'href="{new_contacts[field]}"', count=3)
