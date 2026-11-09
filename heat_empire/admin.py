from django.contrib import admin

from .models import SiteContacts


@admin.register(SiteContacts)
class SiteContactsAdmin(admin.ModelAdmin):
    fields = ("phone", "telegram_url", "whatsapp_url", "max_url", "address")
    actions = None

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
