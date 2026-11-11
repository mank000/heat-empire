from django import forms

from .models import QuoteRequest, SiteContacts
from .phones import format_phone


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
