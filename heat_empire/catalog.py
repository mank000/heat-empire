import re
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_safe

from .forms import ProductReviewForm, QuoteContactForm
from .models import HeatingProduct, QuoteRequest, SiteContacts
from .quotes import save_quote_request


SORT_OPTIONS = {
    "orders": ("Сначала больше заказов", ("-order_count",)),
    "rating": ("Сначала выше рейтинг", ("-rating", "-review_count")),
    "power": ("Сначала менее мощные", ("power_kw",)),
    "-power": ("Сначала более мощные", ("-power_kw",)),
    "cold": ("Для более низких температур", (F("min_outdoor_c").asc(nulls_last=True),)),
    "water": ("Сначала с более горячей подачей", (F("max_water_c").desc(nulls_last=True),)),
    "price": ("Сначала дешевле", (F("price_rub").asc(nulls_last=True),)),
}


CATALOG_PAGE_SIZE = 12
PUMP_FILTERS = ("construction", "refrigerant", "outdoor")


class CatalogFilters(forms.Form):
    q = forms.CharField(
        label="Поиск по модели", required=False, max_length=100,
        widget=forms.TextInput(attrs={"type": "search", "placeholder": "Бренд, серия или модель"}),
    )
    brand = forms.MultipleChoiceField(label="Бренд", required=False, widget=forms.CheckboxSelectMultiple)
    construction = forms.MultipleChoiceField(
        label="Конструкция", choices=HeatingProduct.Construction.choices,
        required=False, widget=forms.CheckboxSelectMultiple,
    )
    min_power = forms.DecimalField(label="Мощность от, кВт", required=False, min_value=0, max_digits=6, decimal_places=2)
    max_power = forms.DecimalField(label="Мощность до, кВт", required=False, min_value=0, max_digits=6, decimal_places=2)
    supply = forms.ChoiceField(label="Питание", choices=[("", "Любое"), *HeatingProduct.Supply.choices], required=False)
    refrigerant = forms.ChoiceField(
        label="Хладагент", choices=[("", "Любой"), *HeatingProduct.Refrigerant.choices], required=False,
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

    def __init__(self, *args, brands, has_prices, show_pump_filters, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["brand"].choices = [(brand, brand) for brand in brands]
        self.fields["sort"].choices = [
            ("", "По мощности, от меньшей"),
            *((key, label) for key, (label, _) in SORT_OPTIONS.items()
            if key != "power" and (key != "price" or has_prices) and (key != "cold" or show_pump_filters)),
        ]
        if not show_pump_filters:
            for field in PUMP_FILTERS:
                del self.fields[field]
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
    available = HeatingProduct.objects.filter(published=True)
    category = request.GET.get("category", "")
    if category not in HeatingProduct.Category.values:
        category = ""
    if category:
        available = available.filter(category=category)
    show_pump_filters = not category or category == HeatingProduct.Category.HEAT_PUMP
    brands = available.order_by("brand").values_list("brand", flat=True).distinct()
    has_prices = available.filter(price_rub__isnull=False).exists()
    params = request.GET.copy()
    params.pop("page", None)
    if params.get("sort") == "power":
        params.pop("sort")
    if not show_pump_filters:
        for field in PUMP_FILTERS:
            params.pop(field, None)
        if params.get("sort") == "cold":
            params.pop("sort")
    if not has_prices:
        params.pop("min_price", None)
        params.pop("max_price", None)
        if params.get("sort") == "price":
            params.pop("sort")
    form = CatalogFilters(params, brands=brands, has_prices=has_prices, show_pump_filters=show_pump_filters)
    products = available.none()
    if form.is_valid():
        filters = form.cleaned_data
        products = available
        for word in filters["q"].split():
            # SQLite's case-insensitive matching only folds ASCII.
            matches = Q()
            for spelling in {word, word.lower(), word.upper(), word.title()}:
                matches |= Q(brand__icontains=spelling) | Q(series__icontains=spelling) | Q(model_code__icontains=spelling)
            products = products.filter(matches)
        for field, lookup in (
            ("brand", "brand__in"), ("construction", "construction__in"),
            ("min_power", "power_kw__gte"), ("max_power", "power_kw__lte"),
            ("refrigerant", "refrigerant"),
            ("outdoor", "min_outdoor_c__lte"), ("water", "max_water_c__gte"),
            ("min_price", "price_rub__gte"), ("max_price", "price_rub__lte"),
        ):
            value = filters.get(field)
            if value is not None and value != "" and value != []:
                products = products.filter(**{lookup: value})
        supply = filters["supply"]
        if supply:
            compatible = [supply]
            if supply in (HeatingProduct.Supply.SINGLE, HeatingProduct.Supply.THREE):
                compatible.append(HeatingProduct.Supply.EITHER)
            products = products.filter(supply__in=compatible)
        _, ordering = SORT_OPTIONS[filters["sort"] or "power"]
        products = products.order_by(*ordering, "pk").defer("description", "source_url")

    try:
        page_number = max(1, int(request.GET.get("page", "1")))
    except ValueError:
        page_number = 1
    page = Paginator(products, CATALOG_PAGE_SIZE).get_page(page_number)
    catalog_url = reverse("catalog")
    category_params = [
        (key, value)
        for key, values in params.lists()
        if key in form.fields and key != "brand"
        for value in values
    ]

    return render(request, "catalog/index.html", {
        "contacts": SiteContacts.objects.get(pk=1),
        "catalog_active": True,
        "filters": form,
        "has_prices": has_prices,
        "category": category,
        "categories": HeatingProduct.Category.choices,
        "category_params": category_params,
        "show_pump_filters": show_pump_filters,
        "reset_url": f"{catalog_url}?category={category}" if category else catalog_url,
        "page_obj": page,
        "page_numbers": page.paginator.get_elided_page_range(page.number),
        "page_params": params.urlencode(),
    })


@require_safe
def catalog_compare(request):
    slugs = list(dict.fromkeys(request.GET.getlist("product")))
    products = []
    error = ""
    rows = []
    if not 2 <= len(slugs) <= 3 or any(not re.fullmatch(r"[-a-zA-Z0-9_]{1,100}", slug) for slug in slugs):
        error = "Выберите от двух до трёх моделей для сравнения."
    else:
        published = {
            product.slug: product
            for product in HeatingProduct.objects.filter(slug__in=slugs, published=True)
        }
        products = [published[slug] for slug in slugs if slug in published]
        if len(products) != len(slugs):
            error = "Одна из выбранных моделей больше не доступна. Обновите список в каталоге."
        elif len({product.category for product in products}) != 1:
            error = "Для сравнения выберите модели одного типа."
        else:
            rows = comparison_rows(products)

    return render(request, "catalog/compare.html", {
        "contacts": SiteContacts.objects.get(pk=1),
        "catalog_active": True,
        "products": products,
        "rows": rows,
        "error": error,
    }, status=HTTPStatus.BAD_REQUEST if error else HTTPStatus.OK)


def comparison_rows(products):
    rows = [
        ("Тепловая мощность, кВт", [product.power_kw for product in products], True),
        ("Питание", [product.get_supply_display() for product in products], False),
        ("Температура подачи до, °C", [product.max_water_c for product in products], False),
    ]
    if products[0].is_heat_pump:
        rows += [
            ("Конструкция", [product.get_construction_display() for product in products], False),
            ("Хладагент", [product.get_refrigerant_display() for product in products], False),
            ("Наружная температура от, °C", [product.min_outdoor_c for product in products], False),
        ]
    else:
        rows.append(("Топливо", [product.fuel for product in products], False))
    if all(product.price_rub is not None for product in products):
        rows.append(("Цена, ₽", [product.price_rub for product in products], True))
    return rows


@require_http_methods(["GET", "HEAD", "POST"])
def catalog_detail(request, slug):
    product = get_object_or_404(HeatingProduct, slug=slug, published=True)
    detail_url = reverse("catalog-detail", args=[slug])
    quote_received = False
    review_received = False
    review_form = ProductReviewForm()
    form = QuoteContactForm()
    open_quote = request.GET.get("request") == "1"
    status = HTTPStatus.OK

    if request.method == "POST":
        if settings.PREVIEW_MODE:
            return HttpResponseForbidden("В режиме предпросмотра заявки не отправляются.")
        if request.POST.get("intent") == "review":
            review_form = ProductReviewForm(request.POST)
            if review_form.is_valid():
                review = review_form.save(commit=False)
                review.product = product
                review.save()
                request.session["catalog_review_received"] = slug
                return HttpResponseRedirect(f"{detail_url}#product-reviews", status=HTTPStatus.SEE_OTHER)
        else:
            form = QuoteContactForm(request.POST)
            if form.is_valid():
                save_quote_request(form, source=QuoteRequest.Source.CATALOG, product=product)
                request.session["catalog_quote_received"] = slug
                return HttpResponseRedirect(detail_url, status=HTTPStatus.SEE_OTHER)
            open_quote = True
        status = HTTPStatus.UNPROCESSABLE_ENTITY
    else:
        quote_received = request.session.get("catalog_quote_received") == slug
        review_received = request.session.get("catalog_review_received") == slug
        if request.method == "GET":
            if quote_received:
                request.session.pop("catalog_quote_received")
            if review_received:
                request.session.pop("catalog_review_received")

    return render(request, "catalog/detail.html", {
        "contacts": SiteContacts.objects.get(pk=1),
        "catalog_active": True,
        "product": product,
        "modal_form": form,
        "selected_pump": product,
        "catalog_quote": True,
        "quote_action": detail_url,
        "open_quote": open_quote and not quote_received,
        "quote_received": quote_received,
        "reviews": product.reviews.filter(published=True)[:10],
        "review_form": review_form,
        "review_received": review_received,
        "preview_mode": settings.PREVIEW_MODE,
    }, status=status)
