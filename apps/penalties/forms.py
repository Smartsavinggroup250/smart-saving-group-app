from django import forms

from .models import PenaltyPayment


class PenaltyPaymentForm(forms.ModelForm):

    class Meta:
        model = PenaltyPayment
        fields = [
            "amount",
            "payment_method",
            "reference",
        ]

        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "readonly": "readonly",
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
                    "placeholder": "Enter payment reference",
                }
            ),
        }

    def __init__(self, *args, penalty=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.penalty = penalty

        if penalty:
            self.fields["amount"].initial = penalty.amount

    def clean_amount(self):
        amount = self.cleaned_data["amount"]

        if not self.penalty:
            raise forms.ValidationError(
                "Penalty information is missing."
            )

        if amount != self.penalty.amount:
            raise forms.ValidationError(
                "Payment amount must match the penalty amount."
            )

        return amount