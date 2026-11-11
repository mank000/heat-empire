from django.contrib import admin

from .models import LegalPage, QuoteRequest, SiteContacts


@admin.register(SiteContacts)
class SiteContactsAdmin(admin.ModelAdmin):
    fields = ("phone", "telegram_url", "whatsapp_url", "max_url", "address")
    actions = None

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "name", "phone", "area", "heating", "source")
    list_filter = ("source", "heating", "created_at")
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
