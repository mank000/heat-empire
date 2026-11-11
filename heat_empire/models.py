import re
from decimal import Decimal

from django.core.validators import MinValueValidator, RegexValidator, URLValidator
from django.db import models
from django.utils import timezone

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
    heat_pump = models.ForeignKey(
        "HeatPump", verbose_name="Модель из каталога", on_delete=models.SET_NULL, null=True, blank=True,
    )

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


class TelegramSubscriber(models.Model):
    chat_id = models.BigIntegerField("ID чата", primary_key=True)
    active = models.BooleanField("Подписан", default=True)
    pin_fingerprint = models.CharField(max_length=64, blank=True)
    pin_attempts = models.PositiveSmallIntegerField(default=0)
    pin_blocked_until = models.DateTimeField(null=True, blank=True)
    last_update_id = models.BigIntegerField(default=0)
    joined_at = models.DateTimeField("Дата подписки", auto_now_add=True)

    class Meta:
        verbose_name = "Подписчик Telegram"
        verbose_name_plural = "Подписчики Telegram"


class TelegramBroadcast(models.Model):
    text = models.CharField("Сообщение", max_length=4096)
    queued_at = models.DateTimeField("Дата постановки в очередь", null=True, blank=True)

    class Meta:
        verbose_name = "Рассылка Telegram"
        verbose_name_plural = "Рассылки Telegram"
        ordering = ("-pk",)

    def __str__(self):
        return f"Рассылка №{self.pk}"


class TelegramDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "В очереди"
        SENT = "sent", "Отправлено"
        SKIPPED = "skipped", "Пропущено"
        FAILED = "failed", "Ошибка"

    subscriber = models.ForeignKey(TelegramSubscriber, on_delete=models.CASCADE)
    broadcast = models.ForeignKey(TelegramBroadcast, on_delete=models.CASCADE, null=True, blank=True)
    text = models.CharField(max_length=4096)
    requires_pin = models.BooleanField(default=False)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=("status", "available_at"))]


class TelegramBotSettings(models.Model):
    encrypted_token = models.TextField(blank=True)
    pin_hash = models.CharField(max_length=128, blank=True)

    class Meta:
        verbose_name = "Настройки Telegram-бота"
        verbose_name_plural = "Настройки Telegram-бота"
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="telegram_bot_settings_singleton")]

    def __str__(self):
        return "Настройки Telegram-бота"


class HeatPump(models.Model):
    class Construction(models.TextChoices):
        MONOBLOCK = "monoblock", "Моноблок"
        SPLIT = "split", "Сплит"
        HYDRAULIC = "hydraulic", "Гидравлический сплит"

    class Supply(models.TextChoices):
        SINGLE = "single", "1 фаза"
        THREE = "three", "3 фазы"

    class Refrigerant(models.TextChoices):
        R32 = "R32", "R32"
        R290 = "R290", "R290"
        R410A = "R410A", "R410A"

    brand = models.CharField("Бренд", max_length=60)
    series = models.CharField("Серия", max_length=100)
    model_code = models.CharField("Модель", max_length=80)
    slug = models.SlugField("Адрес карточки", max_length=100, unique=True)
    construction = models.CharField("Конструкция", max_length=10, choices=Construction.choices)
    supply = models.CharField("Питание", max_length=6, choices=Supply.choices)
    refrigerant = models.CharField("Хладагент", max_length=5, choices=Refrigerant.choices)
    power_kw = models.DecimalField(
        "Тепловая мощность, кВт", max_digits=6, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    cop = models.DecimalField(
        "COP", max_digits=4, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    min_outdoor_c = models.SmallIntegerField("Минимальная температура воздуха в режиме отопления, °C")
    max_water_c = models.PositiveSmallIntegerField("Максимальная температура подачи, °C")
    price_rub = models.PositiveIntegerField(
        "Цена, ₽", null=True, blank=True, validators=[MinValueValidator(1)],
        help_text="Если оставить пустым, в каталоге будет «Цена по запросу».",
    )
    description = models.TextField("Описание", blank=True)
    source_url = models.URLField("Характеристики производителя", blank=True, validators=[messenger_url_validator])
    image_url = models.URLField(
        "Ссылка на фото", max_length=500, blank=True, validators=[URLValidator(schemes=["https"])],
        help_text="HTTPS-ссылка на фото конкретной модели. Если оставить пустым, используется иллюстрация.",
    )
    published = models.BooleanField("Опубликован", default=True, db_index=True)

    class Meta:
        ordering = ("power_kw", "brand", "model_code", "pk")
        verbose_name = "Тепловой насос"
        verbose_name_plural = "Каталог тепловых насосов"

    def __str__(self):
        return f"{self.brand} {self.series} {self.model_code}"
