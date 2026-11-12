from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import HeatingProduct, QuoteRequest, TelegramDelivery, TelegramSubscriber


class CatalogTests(TestCase):
    def test_filters_combine_and_show_only_published_models(self):
        HeatingProduct.objects.filter(slug="aux-h16-r32").update(published=False)
        response = self.client.get(reverse("catalog"), {
            "brand": ["AUX", "Hisense"], "construction": ["monoblock"],
            "supply": "three", "refrigerant": "R32", "min_power": "10",
            "outdoor": "-25", "water": "65", "sort": "-power",
        })
        self.assertEqual(
            [product.slug for product in response.context["page_obj"]], ["aux-h14-r32"]
        )
        self.assertEqual(self.client.get(reverse("catalog-detail", args=["aux-h16-r32"])).status_code, 404)

    def test_search_and_pagination_keep_selected_parameters(self):
        response = self.client.get(reverse("catalog"), {"q": "hisense 120", "page": 1})
        self.assertEqual([product.model_code for product in response.context["page_obj"]], ["AHW-120HEDS1"])
        response = self.client.get(reverse("catalog"), {"outdoor": "-25", "sort": "-power"})
        self.assertEqual(response.context["page_obj"].paginator.count, 12)
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 1)
        response = self.client.get(reverse("catalog"), {"sort": "-power"})
        self.assertContains(response, "sort=-power&amp;page=2")
        self.assertEqual(len(response.context["page_obj"]), 12)

    def test_invalid_range_is_reported_and_price_filter_uses_entered_prices(self):
        response = self.client.get(reverse("catalog"), {"min_power": "10", "max_power": "5"})
        self.assertIn("max_power", response.context["filters"].errors)
        HeatingProduct.objects.filter(slug="aux-h06-r32").update(price_rub=150000)
        response = self.client.get(reverse("catalog"), {"max_price": 160000, "sort": "price"})
        self.assertEqual([product.slug for product in response.context["page_obj"]], ["aux-h06-r32"])

    def test_boiler_category_ignores_pump_filters_and_keeps_power_filter(self):
        response = self.client.get(reverse("catalog"), {
            "category": "solid", "construction": "split", "outdoor": "-25", "min_power": "15",
        })
        self.assertEqual([product.slug for product in response.context["page_obj"]], ["zota-topol-m-20"])
        self.assertNotContains(response, 'name="outdoor"')
        self.assertContains(response, "Дрова и уголь")

    def test_boiler_search_matches_lowercase_cyrillic(self):
        response = self.client.get(reverse("catalog"), {"q": "лемакс премиум-16"})
        self.assertEqual([product.slug for product in response.context["page_obj"]], ["lemax-premium-16"])

    def test_electric_boilers_with_dual_supply_match_either_phase(self):
        for supply in ("single", "three"):
            with self.subTest(supply=supply):
                response = self.client.get(reverse("catalog"), {"category": "electric", "supply": supply})
                self.assertEqual(response.context["page_obj"].paginator.count, 2)

    def test_catalog_selection_is_saved_with_quote(self):
        pump = HeatingProduct.objects.get(slug="panasonic-wh-wdg07le5")
        url = reverse("home")
        self.assertContains(self.client.get(url, {"pump": pump.slug}), 'value="panasonic-wh-wdg07le5"')
        result = self.client.post(url, {
            "source": "section",
            "section-name": "Тест",
            "section-phone": "9001234567",
            "section-area": "120",
            "section-heating": QuoteRequest.Heating.ELECTRIC,
            "section-consent": "on",
            "section-heat_pump": pump.slug,
        })
        self.assertEqual(result.status_code, 303)
        self.assertEqual(QuoteRequest.objects.get().heat_pump, pump)

    def test_catalog_quote_uses_card_model_and_confirms_on_same_card(self):
        boiler = HeatingProduct.objects.get(slug="lemax-premium-10")
        url = reverse("catalog-detail", args=[boiler.slug])
        subscriber = TelegramSubscriber.objects.create(chat_id=123, pin_fingerprint="verified")
        self.assertContains(self.client.get(url), 'data-open-dialog="quote-dialog"')
        self.assertContains(self.client.get(url, {"request": "1"}), "open data-open-on-load")
        result = self.client.post(url, {
            "name": "Тест",
            "phone": "9001234567",
            "consent": "on",
            "heat_pump": "aux-h06-r32",
        })
        self.assertRedirects(result, url, status_code=303, fetch_redirect_response=False)
        quote = QuoteRequest.objects.get()
        self.assertEqual(quote.heat_pump, boiler)
        self.assertEqual(quote.phone, "+7 (900) 123-45-67")
        self.assertEqual(quote.source, QuoteRequest.Source.CATALOG)
        self.assertIsNone(quote.area)
        self.assertEqual(quote.heating, "")
        self.assertFalse(quote.is_processed)
        self.assertEqual(TelegramDelivery.objects.get().subscriber, subscriber)
        self.assertNotContains(self.client.get(reverse("home")), 'id="quote-success"')
        self.assertContains(self.client.get(url), "Продолжить просмотр")
        self.assertNotContains(self.client.get(url), 'id="quote-success"')

    def test_catalog_quote_reopens_for_invalid_data_and_requires_csrf(self):
        url = reverse("catalog-detail", args=["lemax-premium-10"])
        result = self.client.post(url, {"name": "Тест", "phone": "invalid"})
        self.assertContains(result, "open data-open-on-load", status_code=422)
        self.assertEqual(set(result.context["modal_form"].errors), {"phone", "consent"})
        self.assertEqual(Client(enforce_csrf_checks=True).post(url).status_code, 403)
        self.assertFalse(QuoteRequest.objects.exists())

    @override_settings(PREVIEW_MODE=True)
    def test_catalog_preview_disables_submission(self):
        url = reverse("catalog-detail", args=["lemax-premium-10"])
        self.assertContains(self.client.get(url), "Заявки не отправляются.")
        self.assertEqual(self.client.post(url, {"name": "Тест", "phone": "9001234567", "consent": "on"}).status_code, 403)
        self.assertFalse(QuoteRequest.objects.exists())


class CatalogComparisonTests(TestCase):
    def test_heat_pump_comparison_preserves_selection_order(self):
        response = self.client.get(reverse("catalog-compare"), {
            "product": ["panasonic-wh-wdg07le5", "aux-h06-r32", "hisense-ahw-044hcds1"],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [product.slug for product in response.context["products"]],
            ["panasonic-wh-wdg07le5", "aux-h06-r32", "hisense-ahw-044hcds1"],
        )
        self.assertContains(response, "Хладагент")
        self.assertNotContains(response, "Цена, ₽")

    def test_boiler_comparison_shows_fuel_and_prices_when_available(self):
        slugs = ["lemax-premium-10", "lemax-premium-16"]
        HeatingProduct.objects.filter(slug__in=slugs).update(price_rub=50000)
        response = self.client.get(reverse("catalog-compare"), {"product": slugs})
        self.assertContains(response, "Природный газ", count=2)
        self.assertContains(response, "Цена, ₽")
        self.assertNotContains(response, "Хладагент")

    def test_rejects_unpublished_models_mixed_types_and_invalid_selection_size(self):
        HeatingProduct.objects.filter(slug="aux-h08-r32").update(published=False)
        for slugs in (
            ["aux-h06-r32", "aux-h08-r32"],
            ["aux-h06-r32", "lemax-premium-10"],
            ["aux-h06-r32", "aux-h06-r32"],
            ["aux-h06-r32", "aux-h04-r32", "aux-h14-r32", "aux-h16-r32"],
        ):
            with self.subTest(slugs=slugs):
                response = self.client.get(reverse("catalog-compare"), {"product": slugs})
                self.assertEqual(response.status_code, 400)
                self.assertNotContains(response, "<table", status_code=400)
