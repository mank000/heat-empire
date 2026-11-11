from django import forms
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_safe

from .models import HeatPump, SiteContacts


SORT_OPTIONS = {
    "power": ("Сначала менее мощные", ("power_kw",)),
    "-power": ("Сначала более мощные", ("-power_kw",)),
    "cold": ("Для более низких температур", ("min_outdoor_c",)),
    "water": ("Сначала с более горячей подачей", ("-max_water_c",)),
    "price": ("Сначала дешевле", (F("price_rub").asc(nulls_last=True),)),
}


class CatalogFilters(forms.Form):
    q = forms.CharField(
        label="Поиск по модели", required=False, max_length=100,
        widget=forms.TextInput(attrs={"type": "search", "placeholder": "Бренд, серия или модель"}),
    )
    brand = forms.MultipleChoiceField(label="Бренд", required=False, widget=forms.CheckboxSelectMultiple)
    construction = forms.MultipleChoiceField(
        label="Конструкция", choices=HeatPump.Construction.choices,
        required=False, widget=forms.CheckboxSelectMultiple,
    )
    min_power = forms.DecimalField(label="Мощность от, кВт", required=False, min_value=0, max_digits=6, decimal_places=2)
    max_power = forms.DecimalField(label="Мощность до, кВт", required=False, min_value=0, max_digits=6, decimal_places=2)
    supply = forms.ChoiceField(label="Питание", choices=[("", "Любое"), *HeatPump.Supply.choices], required=False)
    refrigerant = forms.ChoiceField(
        label="Хладагент", choices=[("", "Любой"), *HeatPump.Refrigerant.choices], required=False,
    )
    outdoor = forms.IntegerField(
        label="Температура воздуха, °C", required=False, min_value=-80, max_value=50,
        widget=forms.NumberInput(attrs={"placeholder": "Например, −25"}),
        help_text="Покажем модели, рассчитанные на отопление при этой температуре.",
    )
    water = forms.IntegerField(
        label="Температура подачи от, °C", required=False, min_value=1, max_value=120,
        widget=forms.NumberInput(attrs={"placeholder": "Например, 60"}),
    )
    min_price = forms.IntegerField(label="Цена от, ₽", required=False, min_value=1, max_value=1_000_000_000)
    max_price = forms.IntegerField(label="Цена до, ₽", required=False, min_value=1, max_value=1_000_000_000)
    sort = forms.ChoiceField(label="Сортировка", required=False)

    def __init__(self, *args, brands, has_prices, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["brand"].choices = [(brand, brand) for brand in brands]
        self.fields["sort"].choices = [
            (key, label) for key, (label, _) in SORT_OPTIONS.items() if key != "price" or has_prices
        ]
        if not has_prices:
            del self.fields["min_price"]
            del self.fields["max_price"]

    def clean(self):
        cleaned = super().clean()
        for unit in ("power", "price"):
            lower = cleaned.get(f"min_{unit}")
            upper = cleaned.get(f"max_{unit}")
            if lower is not None and upper is not None and lower > upper:
                self.add_error(f"max_{unit}", "Верхняя граница должна быть не меньше нижней.")
        return cleaned


@require_safe
def catalog_index(request):
    available = HeatPump.objects.filter(published=True)
    brands = available.order_by("brand").values_list("brand", flat=True).distinct()
    has_prices = available.filter(price_rub__isnull=False).exists()
    form = CatalogFilters(request.GET, brands=brands, has_prices=has_prices)
    products = available.none()
    if form.is_valid():
        filters = form.cleaned_data
        products = available
        for word in filters["q"].split():
            products = products.filter(
                Q(brand__icontains=word) | Q(series__icontains=word) | Q(model_code__icontains=word)
            )
        for field, lookup in (
            ("brand", "brand__in"), ("construction", "construction__in"),
            ("min_power", "power_kw__gte"), ("max_power", "power_kw__lte"),
            ("supply", "supply"), ("refrigerant", "refrigerant"),
            ("outdoor", "min_outdoor_c__lte"), ("water", "max_water_c__gte"),
            ("min_price", "price_rub__gte"), ("max_price", "price_rub__lte"),
        ):
            value = filters.get(field)
            if value is not None and value != "" and value != []:
                products = products.filter(**{lookup: value})
        _, ordering = SORT_OPTIONS[filters["sort"] or "power"]
        products = products.order_by(*ordering, "brand", "model_code", "pk")

    page = Paginator(products, 9).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "catalog/index.html", {
        "contacts": SiteContacts.objects.get(pk=1),
        "catalog_active": True,
        "filters": form,
        "has_prices": has_prices,
        "page_obj": page,
        "page_numbers": page.paginator.get_elided_page_range(page.number),
        "page_params": params.urlencode(),
    })


@require_safe
def catalog_detail(request, slug):
    pump = get_object_or_404(HeatPump, slug=slug, published=True)
    return render(request, "catalog/detail.html", {
        "contacts": SiteContacts.objects.get(pk=1),
        "catalog_active": True,
        "pump": pump,
    })
