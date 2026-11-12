from decimal import Decimal

from django.db import migrations


AUX_SOURCE = "https://auxair.mk/heat-pump-monobloc-r32/"
HISENSE_SOURCE = "https://hisense-air.ru/product/split-integra/"
PANASONIC_SOURCE = "https://cdn.aircon.panasonic.eu/uploads/ME/Catalogues/2025/AQUAREA_leaflet_P24_scr.pdf"


def seed_catalog(apps, schema_editor):
    heat_pumps = apps.get_model("heat_empire", "HeatPump").objects.using(schema_editor.connection.alias)
    families = (
        (
            "AUX", "R32 Monobloc", "monoblock", "R32", AUX_SOURCE,
            "Моноблок «воздух–вода» для отопления и охлаждения. Гидравлическая часть встроена в наружный блок.",
            (
                ("aux-h04-r32", "ACHP-H04/4R3HA-M", "4.30", "5.20", "single", -25, 65),
                ("aux-h06-r32", "ACHP-H06/4R3HA-M", "6.35", "4.95", "single", -25, 65),
                ("aux-h08-r32", "ACHP-H08/4R3HA-M", "8.40", "5.20", "single", -25, 65),
                ("aux-h14-r32", "ACHP-H14/5R3HA-M", "14.50", "4.71", "three", -25, 65),
                ("aux-h16-r32", "ACHP-H16/5R3HA-M", "16.10", "4.51", "three", -25, 65),
            ),
        ),
        (
            "Hisense", "Hi-Therma Split / Integra", "split", "R32", HISENSE_SOURCE,
            "Наружный блок системы «воздух–вода». Для работы нужен совместимый внутренний блок Split или Integra.",
            (
                ("hisense-ahw-044hcds1", "AHW-044HCDS1", "4.40", "5.10", "single", -25, 60),
                ("hisense-ahw-080hcds1", "AHW-080HCDS1", "8.00", "4.90", "single", -25, 60),
                ("hisense-ahw-120heds1", "AHW-120HEDS1", "12.00", "4.95", "single", -25, 65),
                ("hisense-ahw-160heds1", "AHW-160HEDS1", "16.00", "4.60", "single", -25, 65),
            ),
        ),
        (
            "Panasonic", "Aquarea L", "hydraulic", "R290", PANASONIC_SOURCE,
            "Наружный блок серии L. Внутренний и наружный блоки соединены водяным контуром.",
            (
                ("panasonic-wh-wdg05le5", "WH-WDG05LE5", "5.00", "5.05", "single", -25, 75),
                ("panasonic-wh-wdg07le5", "WH-WDG07LE5", "7.00", "4.93", "single", -25, 75),
                ("panasonic-wh-wdg09le5", "WH-WDG09LE5", "9.00", "4.55", "single", -25, 75),
            ),
        ),
    )
    for brand, series, construction, refrigerant, source, description, products in families:
        for slug, model_code, power, cop, supply, outdoor, water in products:
            heat_pumps.get_or_create(slug=slug, defaults={
                "brand": brand,
                "series": series,
                "model_code": model_code,
                "construction": construction,
                "refrigerant": refrigerant,
                "source_url": source,
                "description": description,
                "power_kw": Decimal(power),
                "cop": Decimal(cop),
                "supply": supply,
                "min_outdoor_c": outdoor,
                "max_water_c": water,
            })


class Migration(migrations.Migration):
    dependencies = [("heat_empire", "0008_heat_pump_catalog")]
    operations = [migrations.RunPython(seed_catalog, migrations.RunPython.noop)]
