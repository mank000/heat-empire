from django import forms

from .models import QuoteRequest


class QuoteRequestForm(forms.ModelForm):
    consent = forms.BooleanField(
        label="Согласен на обработку персональных данных для связи по заявке",
        error_messages={"required": "Подтвердите согласие на обработку данных."},
    )

    class Meta:
        model = QuoteRequest
        fields = ("name", "phone", "area", "heating")
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "given-name", "placeholder": "Ваше имя"}),
            "phone": forms.TextInput(attrs={
                "type": "tel",
                "autocomplete": "tel",
                "placeholder": "+7 (000) 000–00–00",
            }),
            "area": forms.NumberInput(attrs={"placeholder": "Площадь, м²"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["heating"].choices = [
            ("", "Тип текущего отопления"),
            *QuoteRequest.Heating.choices,
        ]
