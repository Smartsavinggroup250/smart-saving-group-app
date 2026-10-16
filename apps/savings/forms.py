
from django import forms

from .models import MonthlyContribution


class MonthlyContributionForm(forms.ModelForm):
    month = forms.DateField(
        input_formats=["%Y-%m", "%Y-%m-%d"],
        widget=forms.DateInput(
            format="%Y-%m",
            attrs={
                "type": "month",
                "class": "form-control",
            },
        ),
    )

    class Meta:
        model = MonthlyContribution

        fields = [
            "month",
            "amount",
            "payment_method",
            "reference",
            "notes",
        ]

        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "1",
                }
            ),
            "payment_method": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "reference": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Payment reference",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }

    def clean_month(self):
        selected_month = self.cleaned_data["month"]
        return selected_month.replace(day=1)
