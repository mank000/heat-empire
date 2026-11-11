from django.contrib import admin
from django.db.models import Count, Q
from django.utils.text import Truncator

from .forms import SiteContactsForm
from .models import LegalPage, QuoteRequest, SiteContacts, TelegramBroadcast, TelegramDelivery, TelegramSubscriber
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
    readonly_fields = ("created_at", "name", "phone", "area", "heating", "source")

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
