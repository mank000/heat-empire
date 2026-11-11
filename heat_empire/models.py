import re

from django.core.validators import MinValueValidator, RegexValidator, URLValidator
from django.db import models

from .phones import format_phone


phone_validator = RegexValidator(
    regex=r"^\+?(?:[ .()\-\u00a0\u202f]*[0-9]){3,15}[ .()\-\u00a0\u202f]*\Z",
    message="Введите номер телефона, например +7 (924) 131-71-30.",
)
messenger_url_validator = URLValidator(schemes=["http", "https"])


class SiteContacts(models.Model):
    phone = models.CharField("Телефон", max_length=40, validators=[phone_validator])
    telegram_url = models.URLField("Ссылка на Telegram", blank=True, validators=[messenger_url_validator])
    whatsapp_url = models.URLField("Ссылка на WhatsApp", blank=True, validators=[messenger_url_validator])
    max_url = models.URLField("Ссылка на MAX", blank=True, validators=[messenger_url_validator])
    address = models.TextField("Адрес", max_length=400)

    class Meta:
        verbose_name = "Контакты сайта"
        verbose_name_plural = "Контакты сайта"
        constraints = [
            models.CheckConstraint(condition=models.Q(id=1), name="site_contacts_singleton"),
        ]

    def __str__(self):
        return "Контакты сайта"

    @property
    def phone_display(self):
        return format_phone(self.phone)

    @property
    def phone_href(self):
        return "tel:" + re.sub(r"[^+0-9]", "", self.phone_display)

    @property
    def messengers(self):
        return (
            ("Telegram", "img/telegram.svg", self.telegram_url),
            ("MAX", "img/max.svg", self.max_url),
            ("WhatsApp", "img/whatsapp.svg", self.whatsapp_url),
        )


class QuoteRequest(models.Model):
    class Heating(models.TextChoices):
        ELECTRIC = "electric", "Электрокотёл"
        GAS = "gas", "Газовое отопление"
        SOLID = "solid", "Пеллеты или дрова"
        NONE = "none", "Отопление ещё не установлено"

    class Source(models.TextChoices):
        SECTION = "section", "Форма на главной"
        MODAL = "modal", "Модальное окно"

    name = models.CharField("Имя", max_length=100)
    phone = models.CharField("Телефон", max_length=40, validators=[phone_validator])
    area = models.PositiveIntegerField("Площадь, м²", validators=[MinValueValidator(1)])
    heating = models.CharField("Текущее отопление", max_length=16, choices=Heating.choices)
    source = models.CharField("Источник", max_length=10, choices=Source.choices)
    created_at = models.DateTimeField("Дата заявки", auto_now_add=True)
    is_processed = models.BooleanField("Обработана", default=False)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "Заявка на расчёт"
        verbose_name_plural = "Заявки на расчёт"

    def __str__(self):
        return f"Заявка №{self.pk}"


class LegalPage(models.Model):
    class Kind(models.TextChoices):
        PRIVACY = "privacy-policy", "Политика конфиденциальности"
        COMPANY = "company-details", "Реквизиты компании"

    kind = models.CharField("Страница", max_length=16, choices=Kind.choices, primary_key=True)
    body = models.TextField(
        "Текст страницы",
        blank=True,
        help_text="Разделяйте абзацы пустой строкой. Текст публикуется после сохранения.",
    )

    class Meta:
        ordering = ("kind",)
        verbose_name = "Юридическая страница"
        verbose_name_plural = "Юридические страницы"

    def __str__(self):
        return self.get_kind_display()
