from cryptography.fernet import InvalidToken
from django import forms
from django.conf import settings

from .models import QuoteRequest, SiteContacts, TelegramBotSettings, TelegramSubscriber
from .phones import format_phone
from .telegram_credentials import PIN_PATTERN, TOKEN_PATTERN, load_credentials


class FormattedPhoneField(forms.CharField):
    widget = forms.TextInput(attrs={
        "type": "tel",
        "autocomplete": "tel",
        "placeholder": "+7 (000) 000-00-00",
    })

    def to_python(self, value):
        return format_phone(super().to_python(value))


class SiteContactsForm(forms.ModelForm):
    class Meta:
        model = SiteContacts
        fields = ("phone", "telegram_url", "whatsapp_url", "max_url", "address")
        field_classes = {"phone": FormattedPhoneField}


class QuoteRequestForm(forms.ModelForm):
    consent = forms.BooleanField(
        label="Согласен на обработку персональных данных для связи по заявке",
        error_messages={"required": "Подтвердите согласие на обработку данных."},
    )

    class Meta:
        model = QuoteRequest
        fields = ("name", "phone", "area", "heating")
        field_classes = {"phone": FormattedPhoneField}
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "given-name", "placeholder": "Ваше имя"}),
            "area": forms.NumberInput(attrs={"placeholder": "Площадь, м²"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["heating"].choices = [
            ("", "Тип текущего отопления"),
            *QuoteRequest.Heating.choices,
        ]


class TelegramBotSettingsForm(forms.ModelForm):
    bot_token = forms.RegexField(
        regex=TOKEN_PATTERN, label="Токен BotFather", max_length=128, required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Оставьте поле пустым, чтобы сохранить текущий токен.",
        error_messages={"invalid": "Введите токен в формате, который выдал BotFather."},
    )
    access_pin = forms.RegexField(
        regex=PIN_PATTERN, label="PIN для уведомлений", max_length=32, required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "inputmode": "numeric"}),
        help_text="От 8 до 32 цифр. После смены PIN сотрудникам нужно ввести его заново.",
        error_messages={"invalid": "PIN должен содержать от 8 до 32 цифр."},
    )

    class Meta:
        model = TelegramBotSettings
        fields = ()

    def clean_bot_token(self):
        token = self.cleaned_data["bot_token"]
        if not token:
            return token
        if len(settings.SECRET_KEY) < 50 or settings.SECRET_KEY.startswith("django-insecure-"):
            raise forms.ValidationError("Сначала задайте стойкий DJANGO_SECRET_KEY на сервере.")
        try:
            current_token = load_credentials().token
        except InvalidToken:
            raise forms.ValidationError("Не удалось открыть текущий токен. Проверьте ключ Django на сервере.") from None
        if current_token and current_token.split(":", 1)[0] != token.split(":", 1)[0]:
            if TelegramSubscriber.objects.exists():
                raise forms.ValidationError("Для другого бота нужна отдельная база подписчиков.")
        return token
