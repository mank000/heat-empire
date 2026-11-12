from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from heat_empire.models import HeatingProduct, ProductReview


DEMO_COUNT = 1000
DEMO_PREFIX = "heating-model-"
LEGACY_PREFIX = "demo-catalog-"
BRANDS = ("Термоконтур", "СеверТепло", "Аэротерм", "Горизонт", "Тепловектор", "НордЛиния", "Климатон", "ЭкоКонтур")
SERIES = ("Стандарт", "Комфорт", "Профи", "Оптима")
REVIEWS = (
    ("Алексей", "Подошёл по размерам, подключение прошло без проблем."),
    ("Марина", "Выбирали для загородного дома. Управление оказалось понятным."),
    ("Игорь", "Характеристики совпали с описанием. Посмотрим, как покажет себя зимой."),
    ("Елена", "Подобрали нужную мощность. Всё работает, настройки понятные."),
)


def product_content(number):
    series = SERIES[number % len(SERIES)]
    if number % 7 == 0:
        series += " для систем водяного отопления загородных домов"
    return {
        "brand": BRANDS[number % len(BRANDS)],
        "series": series,
        "model_code": f"HM-{number:04d}",
        "description": "Оборудование для водяной системы отопления. Подбор мощности зависит от теплопотерь здания.",
    }


class Command(BaseCommand):
    help = "Добавить 1000 тестовых товаров, отзывы и счётчики заказов для проверки каталога."

    def add_arguments(self, parser):
        parser.add_argument("--remove", action="store_true", help="Удалить созданные этой командой товары и отзывы.")

    @transaction.atomic
    def handle(self, *args, **options):
        demo = HeatingProduct.objects.filter(is_demo=True).filter(
            Q(slug__startswith=DEMO_PREFIX) | Q(slug__startswith=LEGACY_PREFIX)
        )
        if options["remove"]:
            count = demo.count()
            demo.delete()
            self.stdout.write(f"Удалено тестовых товаров: {count}.")
            return

        categories = HeatingProduct.Category.values
        fuels = {
            HeatingProduct.Category.ELECTRIC: "Электричество",
            HeatingProduct.Category.SOLID: "Дрова, уголь и топливные брикеты",
            HeatingProduct.Category.GAS: "Природный газ",
            HeatingProduct.Category.PELLET: "Пеллеты",
        }
        existing = dict(HeatingProduct.objects.filter(slug__startswith=DEMO_PREFIX).values_list("slug", "is_demo"))
        legacy = {
            product.slug: product
            for product in demo.filter(slug__startswith=LEGACY_PREFIX)
        }
        updated = []
        products = []
        scores = []
        for number in range(1, DEMO_COUNT + 1):
            slug = f"{DEMO_PREFIX}{number:04d}"
            previous = legacy.get(f"{LEGACY_PREFIX}{number:04d}")
            if slug in existing:
                if previous or not existing[slug]:
                    raise CommandError(f"Адрес {slug} уже занят.")
                continue
            content = product_content(number)
            if previous:
                previous.slug = slug
                for field, value in content.items():
                    setattr(previous, field, value)
                updated.append(previous)
                continue
            category = categories[(number - 1) % len(categories)]
            is_pump = category == HeatingProduct.Category.HEAT_PUMP
            ratings = [1 + ((number * 13 + index * 7) % 5) for index in range(number % 5)]
            products.append(HeatingProduct(
                slug=slug,
                category=category,
                **content,
                power_kw=4 + (number % 35),
                fuel=fuels.get(category, ""),
                supply=HeatingProduct.Supply.SINGLE if number % 2 else HeatingProduct.Supply.THREE,
                construction=HeatingProduct.Construction.MONOBLOCK if is_pump else "",
                refrigerant=HeatingProduct.Refrigerant.R32 if is_pump else "",
                min_outdoor_c=-20 - (number % 3) * 5 if is_pump else None,
                max_water_c=65 + (number % 4) * 5,
                price_rub=30000 + (number * 791) % 450000,
                order_count=(number * 97) % 350,
                review_count=len(ratings),
                rating=sum(ratings) / len(ratings) if ratings else None,
                is_demo=True,
            ))
            scores.append(ratings)

        HeatingProduct.objects.bulk_update(updated, ["slug", "brand", "series", "model_code", "description"], batch_size=100)
        if updated:
            previous_reviews = ProductReview.objects.filter(
                product_id__in=[product.pk for product in updated],
                published=True,
                body="Демонстрационный текст для проверки отображения отзывов.",
            )
            for index, (author, body) in enumerate(REVIEWS, 1):
                previous_reviews.filter(author=f"Тестовый отзыв {index}").update(author=author, body=body)

        HeatingProduct.objects.bulk_create(products, batch_size=100)
        ProductReview.objects.bulk_create([
            ProductReview(
                product=product,
                author=author,
                rating=rating,
                body=body,
                published=True,
            )
            for product, ratings in zip(products, scores, strict=True)
            for rating, (author, body) in zip(ratings, REVIEWS)
        ], batch_size=250)
        self.stdout.write(f"Добавлено: {len(products)}. Обновлено: {len(updated)}. Всего в выборке: {demo.count()}.")
