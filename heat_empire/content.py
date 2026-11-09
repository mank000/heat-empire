from dataclasses import dataclass


@dataclass(frozen=True)
class HeatingSystem:
    title: str
    rows: tuple
    featured: bool = False


COMPARISON_CRITERIA = (
    ("Стоимость установки", "img/metric-installation-cost.svg"),
    ("Расход на 5 лет", "img/metric-five-year-cost.svg"),
    ("Удобство", "img/metric-comfort.svg"),
    ("Экология", "img/metric-environment.svg"),
    ("Охлаждение", "img/metric-cooling.svg"),
    ("Согласование", "img/metric-approval.svg"),
)


def comparison_rows(*ratings):
    return tuple(
        (label, icon, value, tone)
        for (label, icon), (value, tone) in zip(COMPARISON_CRITERIA, ratings, strict=True)
    )


HEATING_SYSTEMS = (
    HeatingSystem("Электрокотёл", comparison_rows(
        ("низкая", "good"), ("низкий", "bad"), ("среднее", "medium"),
        ("средняя", "medium"), ("нет", "neutral"), ("нет", "neutral"),
    )),
    HeatingSystem("Тепловой насос", comparison_rows(
        ("средняя", "medium"), ("низкий", "good"), ("максимальное", "good"),
        ("высокая", "good"), ("доступно", "good"), ("нет", "neutral"),
    ), featured=True),
    HeatingSystem("Пеллеты / дрова", comparison_rows(
        ("средняя", "medium"), ("средний", "medium"), ("среднее", "medium"),
        ("средняя", "medium"), ("нет", "neutral"), ("требуется", "medium"),
    )),
    HeatingSystem("Газовое отопление", comparison_rows(
        ("высокая", "bad"), ("средний", "medium"), ("среднее", "medium"),
        ("выбросы CO₂", "bad"), ("нет", "neutral"), ("обязательно", "bad"),
    )),
)
