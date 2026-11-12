from django.test import TestCase
from django.urls import reverse

from .models import HeatingProduct, QuoteRequest


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
        self.assertContains(response, "outdoor=-25&amp;sort=-power&amp;page=2")

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

    def test_gas_boiler_selection_uses_the_same_quote_form(self):
        boiler = HeatingProduct.objects.get(slug="lemax-premium-10")
        response = self.client.get(reverse("catalog-detail", args=[boiler.slug]))
        self.assertContains(response, "Природный газ")
        self.assertNotContains(response, "Хладагент")
        result = self.client.post(reverse("home"), {
            "source": "section",
            "section-name": "Тест",
            "section-phone": "9001234567",
            "section-area": "120",
            "section-heating": QuoteRequest.Heating.GAS,
            "section-consent": "on",
            "section-heat_pump": boiler.slug,
        })
        self.assertEqual(result.status_code, 303)
        self.assertEqual(QuoteRequest.objects.get().heat_pump, boiler)
