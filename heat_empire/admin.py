from django.contrib import admin
from django.contrib.auth.hashers import make_password
from django.db.models import Count, Q
from django.utils.text import Truncator

from .forms import SiteContactsForm, TelegramBotSettingsForm
from .models import (
    HeatPump,
    LegalPage,
    QuoteRequest,
    SiteContacts,
    TelegramBotSettings,
    TelegramBroadcast,
    TelegramDelivery,
    TelegramSubscriber,
)
from .telegram_credentials import token_cipher
from .telegram_queue import enqueue_broadcast


@admin.register(SiteContacts)
class SiteContactsAdmin(admin.ModelAdmin):
    form = SiteContactsForm
    actions = None

    class Media:
        js = ("js/phone-format.js",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "name", "phone", "area", "heating", "source", "is_processed")
    list_filter = ("is_processed", "source", "heating", "created_at")
    search_fields = ("name", "phone")
    readonly_fields = ("created_at", "name", "phone", "area", "heating", "source", "heat_pump")

    def has_add_permission(self, request):
        return False


@admin.register(LegalPage)
class LegalPageAdmin(admin.ModelAdmin):
    fields = ("kind", "body")
    readonly_fields = ("kind",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TelegramSubscriber)
class TelegramSubscriberAdmin(admin.ModelAdmin):
    list_display = ("chat_id", "active", "joined_at")
    list_filter = ("active",)
    fields = ("chat_id", "joined_at", "active")
    readonly_fields = ("chat_id", "joined_at")

    def has_add_permission(self, request):
        return False


@admin.register(TelegramBroadcast)
class TelegramBroadcastAdmin(admin.ModelAdmin):
    list_display = ("id", "preview", "queued_at", "sent", "pending", "unsent")
    actions = ("queue_broadcasts",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            sent_total=Count("telegramdelivery", filter=Q(telegramdelivery__status=TelegramDelivery.Status.SENT)),
            pending_total=Count("telegramdelivery", filter=Q(telegramdelivery__status=TelegramDelivery.Status.PENDING)),
            unsent_total=Count("telegramdelivery", filter=Q(telegramdelivery__status__in=[
                TelegramDelivery.Status.SKIPPED, TelegramDelivery.Status.FAILED,
            ])),
        )

    @admin.display(description="Сообщение")
    def preview(self, obj):
        return Truncator(obj.text).chars(70)

    @admin.display(description="Отправлено")
    def sent(self, obj):
        return obj.sent_total

    @admin.display(description="В очереди")
    def pending(self, obj):
        return obj.pending_total

    @admin.display(description="Пропущено / ошибки")
    def unsent(self, obj):
        return obj.unsent_total

    def get_readonly_fields(self, request, obj=None):
        return ("queued_at", "text") if obj and obj.queued_at else ("queued_at",)

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(permissions=["change"], description="Поставить выбранные черновики в очередь рассылки")
    def queue_broadcasts(self, request, queryset):
        count = sum(enqueue_broadcast(pk) for pk in queryset.values_list("pk", flat=True))
        self.message_user(request, f"Поставлено в очередь сообщений: {count}.")


@admin.register(TelegramBotSettings)
class TelegramBotSettingsAdmin(admin.ModelAdmin):
    form = TelegramBotSettingsForm
    fields = ("bot_token", "access_pin", "credentials_saved")
    readonly_fields = ("credentials_saved",)
    actions = None

    @admin.display(description="Настройки из админки")
    def credentials_saved(self, obj):
        token = "токен сохранён" if obj.encrypted_token else "токен не задан"
        pin = "PIN сохранён" if obj.pin_hash else "PIN не задан"
        return f"{token}, {pin}"

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        fields = []
        if token := form.cleaned_data["bot_token"]:
            obj.encrypted_token = token_cipher().encrypt(token.encode()).decode()
            fields.append("encrypted_token")
        if pin := form.cleaned_data["access_pin"]:
            obj.pin_hash = make_password(pin)
            fields.append("pin_hash")
        if fields:
            obj.save(update_fields=fields)


@admin.register(HeatPump)
class HeatPumpAdmin(admin.ModelAdmin):
    list_display = ("brand", "model_code", "construction", "power_kw", "supply", "price_rub", "published")
    list_filter = ("published", "brand", "construction", "supply", "refrigerant")
    search_fields = ("brand", "series", "model_code")
    prepopulated_fields = {"slug": ("brand", "model_code")}
