from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import LegalPage, QuoteRequest, SiteContacts


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
            "phone": "8 900 1234567",
            "telegram_url": "https://t.me/heat_example",
            "whatsapp_url": "https://wa.me/79001234567",
            "max_url": "https://max.ru/heat_example",
            "address": "г. Санкт-Петербург,\nТестовая улица, 1",
        }
        self.assertEqual(self.client.post(change_url, new_contacts).status_code, 302)

        self.assertEqual(SiteContacts.objects.get(pk=1).phone, "+7 (900) 123-45-67")
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'href="tel:+79001234567"', count=5)
        self.assertContains(response, "<strong>+7 (900) 123-45-67</strong>", count=4, html=True)
        self.assertContains(response, new_contacts["address"])
        for field in ("telegram_url", "whatsapp_url", "max_url"):
            self.assertContains(response, f'href="{new_contacts[field]}"', count=3)


class NotFoundTests(TestCase):
    def test_unknown_path_has_custom_404_with_home_link_and_contacts(self):
        response = self.client.get("/does-not-exist/")

        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Страница не найдена", status_code=404)
        self.assertContains(response, "Вернуться на главную", status_code=404)
        self.assertContains(response, 'href="tel:+79241317130"', count=2, status_code=404)


class LegalPageTests(TestCase):
    def test_seeded_pages_are_linked_and_open(self):
        home = self.client.get(reverse("home"))
        for kind in LegalPage.Kind.values:
            with self.subTest(kind=kind):
                url = reverse(kind)
                self.assertContains(home, f'href="{url}"')
                self.assertContains(self.client.get(url), "Информация будет добавлена.")

    def test_admin_changes_publish_as_text_without_rendering_html(self):
        self.client.force_login(get_user_model().objects.create_superuser(username="editor"))
        kind = LegalPage.Kind.PRIVACY
        change_url = reverse("admin:heat_empire_legalpage_change", args=[kind])
        content = "Первый абзац.\n\nТекст с <b>тегом</b>."
        self.assertEqual(self.client.post(change_url, {"body": content}).status_code, 302)

        self.assertContains(
            self.client.get(reverse(kind)), "<p>Первый абзац.</p><p>Текст с &lt;b&gt;тегом&lt;/b&gt;.</p>", html=True
        )
        self.assertContains(self.client.get(reverse("company-details")), "Информация будет добавлена.")


class QuoteRequestTests(TestCase):
    def submission(self, source):
        return {
            "source": source,
            f"{source}-name": "Тестовая заявка",
            f"{source}-phone": "9001234567" if source == QuoteRequest.Source.SECTION else "+79001234567",
            f"{source}-area": "120",
            f"{source}-heating": QuoteRequest.Heating.ELECTRIC,
            f"{source}-consent": "on",
        }

    def test_both_forms_save_to_admin_and_show_confirmation_once(self):
        home = reverse("home")
        for source in QuoteRequest.Source.values:
            with self.subTest(source=source):
                result = self.client.post(home, self.submission(source))
                self.assertRedirects(result, home, status_code=303, fetch_redirect_response=False)
                quote = QuoteRequest.objects.get(source=source)
                self.assertEqual(quote.phone, "+7 (900) 123-45-67")
                self.assertEqual(quote.area, 120)
                self.assertFalse(quote.is_processed)
                self.assertContains(self.client.get(home), 'id="quote-success"')
                self.assertNotContains(self.client.get(home), 'id="quote-success"')

        admin_url = reverse("admin:heat_empire_quoterequest_changelist")
        self.assertEqual(self.client.get(admin_url).status_code, 302)
        self.client.force_login(get_user_model().objects.create_superuser(username="operator"))
        admin_page = self.client.get(admin_url)
        self.assertContains(admin_page, "Тестовая заявка", count=2)
        self.assertContains(admin_page, "Модальное окно")

    def test_admin_can_mark_and_filter_processed_requests(self):
        self.client.post(reverse("home"), self.submission(QuoteRequest.Source.SECTION))
        quote = QuoteRequest.objects.get()
        self.client.force_login(get_user_model().objects.create_superuser(username="operator"))
        change_url = reverse("admin:heat_empire_quoterequest_change", args=[quote.pk])
        list_url = reverse("admin:heat_empire_quoterequest_changelist")

        self.assertEqual(self.client.post(change_url, {"is_processed": "on"}).status_code, 302)
        quote.refresh_from_db()
        self.assertTrue(quote.is_processed)
        self.assertContains(self.client.get(list_url, {"is_processed__exact": "1"}), quote.name)
        self.assertNotContains(self.client.get(list_url, {"is_processed__exact": "0"}), quote.name)

        self.assertEqual(self.client.post(change_url, {}).status_code, 302)
        quote.refresh_from_db()
        self.assertFalse(quote.is_processed)

    def test_invalid_modal_reopens_with_errors_and_does_not_save(self):
        source = QuoteRequest.Source.MODAL
        data = self.submission(source)
        data.update({"modal-area": "0", "modal-heating": "invalid", "modal-consent": ""})

        response = self.client.post(reverse("home"), data)

        self.assertContains(response, "data-open-on-load", status_code=422)
        self.assertContains(response, 'value="Тестовая заявка"', status_code=422)
        self.assertEqual(set(response.context["modal_form"].errors), {"area", "heating", "consent"})
        self.assertFalse(QuoteRequest.objects.exists())

    def test_requests_require_csrf(self):
        client = Client(enforce_csrf_checks=True)

        response = client.post(reverse("home"), self.submission(QuoteRequest.Source.SECTION))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(QuoteRequest.objects.exists())

    @override_settings(PREVIEW_MODE=True)
    def test_preview_shows_forms_but_rejects_submissions(self):
        url = reverse("home")
        self.assertContains(self.client.get(url), "Заявки не отправляются.", count=2)
        self.assertEqual(self.client.post(url, self.submission(QuoteRequest.Source.SECTION)).status_code, 403)
        self.assertFalse(QuoteRequest.objects.exists())
