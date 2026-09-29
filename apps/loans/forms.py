from django import forms

from .models import Loan


class LoanApplicationForm(forms.ModelForm):

    class Meta:
        model = Loan

        fields = [
            "requested_amount",
            "duration_months",
            "purpose",
        ]

        widgets = {
            "requested_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "step": "0.01",
                    "placeholder": "Enter loan amount",
                }
            ),

            "duration_months": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "max": "60",
                }
            ),

            "purpose": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Purpose of the loan",
                }
            ),
        }

    def clean_requested_amount(self):
        amount = self.cleaned_data["requested_amount"]

        if amount <= 0:
            raise forms.ValidationError(
                "Loan amount must be greater than zero."
            )

        return amount