from django.core.management.base import BaseCommand
from django.db import transaction

from heat_empire.models import HeatingProduct, ProductReview


DEMO_COUNT = 1000
DEMO_PREFIX = "demo-catalog-"


class Command(BaseCommand):
    help = "Добавить 1000 тестовых товаров, отзывы и счётчики заказов для проверки каталога."

    def add_arguments(self, parser):
        parser.add_argument("--remove", action="store_true", help="Удалить созданные этой командой товары и отзывы.")

    @transaction.atomic
    def handle(self, *args, **options):
        demo = HeatingProduct.objects.filter(is_demo=True, slug__startswith=DEMO_PREFIX)
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
        existing = set(HeatingProduct.objects.filter(slug__startswith=DEMO_PREFIX).values_list("slug", flat=True))
        products = []
        scores = []
        for number in range(1, DEMO_COUNT + 1):
            slug = f"{DEMO_PREFIX}{number:04d}"
            if slug in existing:
                continue
            category = categories[(number - 1) % len(categories)]
            is_pump = category == HeatingProduct.Category.HEAT_PUMP
            ratings = [1 + ((number * 13 + index * 7) % 5) for index in range(number % 5)]
            series = f"Серия {number % 8 + 1}"
            if number % 7 == 0:
                series += " с длинным названием для проверки каталога"
            products.append(HeatingProduct(
                slug=slug,
                category=category,
                brand=f"Тестовый бренд {number % 8 + 1}",
                series=series,
                model_code=f"DEMO-{number:04d}",
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
                description="Тестовая карточка. Характеристики, отзывы, цена и количество заказов сгенерированы.",
                is_demo=True,
            ))
            scores.append(ratings)

        HeatingProduct.objects.bulk_create(products, batch_size=100)
        ProductReview.objects.bulk_create([
            ProductReview(
                product=product,
                author=f"Тестовый отзыв {index}",
                rating=rating,
                body="Демонстрационный текст для проверки отображения отзывов.",
                published=True,
            )
            for product, ratings in zip(products, scores, strict=True)
            for index, rating in enumerate(ratings, 1)
        ], batch_size=250)
        self.stdout.write(f"Добавлено: {len(products)}. Всего тестовых товаров: {demo.count()}.")
