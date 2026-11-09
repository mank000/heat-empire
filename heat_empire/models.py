import re

from django.core.validators import RegexValidator, URLValidator
from django.db import models


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
    def phone_href(self):
        return "tel:" + re.sub(r"[^+0-9]", "", self.phone)

    @property
    def messengers(self):
        return (
            ("Telegram", "img/telegram.svg", self.telegram_url),
            ("MAX", "img/max.svg", self.max_url),
            ("WhatsApp", "img/whatsapp.svg", self.whatsapp_url),
        )
