from django.db import migrations


ZOTA = "https://zota.ru/catalog/"
ZOTA_PHOTOS = "https://s3.twcstorage.ru/zotaru-strapi-prod/zota/uploads/"
LEMAX = "https://lemax-kotel.ru"
LEMAX_SERIES = (
    "/catalog/napolnye_gazovye_kotly/energonezavisimye/"
    "stalnye_gazovye_kotly_lemaks_serii_premium/"
)

BOILER_SERIES = (
    (
        "ZOTA", "Balance V2", "electric", "Электричество", "either", 85,
        ZOTA + "electric/balance-V2", ZOTA_PHOTOS + "Balance_5adb7b6c5c.png",
        (("zota-balance-v2-6", "ZB3468421006", 6), ("zota-balance-v2-9", "ZB3468421009", 9)),
    ),
    (
        "ZOTA", "Тополь-М", "solid", "Дрова и уголь", "none", 85,
        ZOTA + "tverdotoplivnye-kotly/topol-m", ZOTA_PHOTOS + "Topol_M_catalog_1_b642939860.png",
        (("zota-topol-m-14", "TP4931121014", 14), ("zota-topol-m-20", "TP4931121020", 20)),
    ),
    (
        "ZOTA", "Pellet Black", "pellet", "Пеллеты", "single", 85,
        ZOTA + "avtomaticheskie-ugolnye-i-pelletnye-kotly/pellet-black",
        ZOTA_PHOTOS + "PELLET_BLACK_catalog_d0f1de60cc.png",
        (("zota-pellet-black-16", "PL4931123016", 16), ("zota-pellet-black-21", "PL4931123021", 21)),
    ),
)
GAS_MODELS = (
    ("lemax-premium-10", "010305", 10, "premium_10_s_ggu_12", "6e4/rn038hkvv5tse1uwn97e8574xacveglk"),
    ("lemax-premium-16", "010308", 16, "premium_16_s_ggu_19", "d67/eww7dqfwzw0wojioekqchr13m3uo1rqo"),
)


def seed_boilers(apps, schema_editor):
    products = apps.get_model("heat_empire", "HeatingProduct").objects.using(schema_editor.connection.alias)
    for brand, series, category, fuel, supply, max_water_c, source_url, image_url, models in BOILER_SERIES:
        for slug, model_code, power_kw in models:
            products.get_or_create(slug=slug, defaults={
                "brand": brand,
                "series": series,
                "model_code": model_code,
                "category": category,
                "fuel": fuel,
                "supply": supply,
                "power_kw": power_kw,
                "max_water_c": max_water_c,
                "source_url": source_url,
                "image_url": image_url,
            })

    for slug, model_code, power_kw, source_slug, image_folder in GAS_MODELS:
        products.get_or_create(slug=slug, defaults={
            "brand": "Лемакс",
            "series": f"Премиум-{power_kw}",
            "model_code": model_code,
            "category": "gas",
            "fuel": "Природный газ",
            "supply": "none",
            "power_kw": power_kw,
            "max_water_c": 90,
            "source_url": LEMAX + LEMAX_SERIES + source_slug,
            "image_url": f"{LEMAX}/upload/iblock/{image_folder}/premium_{power_kw}.jpeg",
        })


def remove_boilers(apps, schema_editor):
    slugs = [model[0] for series in BOILER_SERIES for model in series[-1]]
    slugs.extend(model[0] for model in GAS_MODELS)
    products = apps.get_model("heat_empire", "HeatingProduct").objects.using(schema_editor.connection.alias)
    products.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):
    dependencies = [("heat_empire", "0011_heating_product_categories")]

    operations = [migrations.RunPython(seed_boilers, remove_boilers)]
