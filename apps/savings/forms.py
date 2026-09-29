from django import forms

from .models import MonthlyContribution


class MonthlyContributionForm(forms.ModelForm):

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
            "month": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
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