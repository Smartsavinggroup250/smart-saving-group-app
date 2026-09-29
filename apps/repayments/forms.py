from django import forms

from .models import LoanRepayment


class LoanRepaymentForm(forms.ModelForm):
    class Meta:
        model = LoanRepayment
        fields = [
            "amount",
            "payment_method",
            "reference",
        ]

        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                    "placeholder": "Enter repayment amount",
                }
            ),
            "payment_method": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "reference": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter payment reference",
                }
            ),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]

        if amount <= 0:
            raise forms.ValidationError(
                "Repayment amount must be greater than zero."
            )

        return amount