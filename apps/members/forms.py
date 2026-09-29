
from django import forms
from django.contrib.auth.models import User

from .models import Member


class MemberRegistrationForm(forms.Form):

    first_name = forms.CharField(
        max_length=150,
        label="First Name"
    )

    last_name = forms.CharField(
        max_length=150,
        label="Last Name"
    )

    username = forms.CharField(
        max_length=150,
        label="Username"
    )

    email = forms.EmailField(
        required=False,
        label="Email"
    )

    password = forms.CharField(
        widget=forms.PasswordInput,
        min_length=8,
        label="Password"
    )

    phone = forms.CharField(
        max_length=20,
        label="Phone Number"
    )

    national_id = forms.CharField(
        max_length=30,
        required=False,
        label="National ID"
    )

    address = forms.CharField(
        max_length=200,
        required=False,
        label="Address"
    )

    def clean_username(self):
        username = self.cleaned_data["username"]

        if User.objects.filter(
            username=username
        ).exists():
            raise forms.ValidationError(
                "This username is already taken."
            )

        return username

    def clean_national_id(self):
        national_id = self.cleaned_data.get(
            "national_id"
        )

        if national_id and Member.objects.filter(
            national_id=national_id
        ).exists():
            raise forms.ValidationError(
                "This National ID is already registered."
            )

        return national_id
    
from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

from .models import Member


class MemberProfileForm(forms.ModelForm):

    first_name = forms.CharField(
        label="First Name",
        max_length=150,
        required=True
    )

    last_name = forms.CharField(
        label="Last Name",
        max_length=150,
        required=True
    )

    email = forms.EmailField(
        label="Email",
        required=True
    )

    class Meta:
        model = Member
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "national_id",
            "shares",
            "country",
            "province",
            "district",
            "sector",
            "cell",
            "village",
            "date_of_birth",
            "next_of_kin_name",
            "next_of_kin_phone",
            "next_of_kin_relationship",
        ]

        widgets = {
            "phone": forms.TextInput(
                attrs={
                    "placeholder": "+250 7XX XXX XXX"
                }
            ),

            "national_id": forms.TextInput(
                attrs={
                    "maxlength": "16",
                    "placeholder": "16 digit National ID"
                }
            ),

            "date_of_birth": forms.DateInput(
                attrs={
                    "type": "date"
                }
            ),

            "shares": forms.NumberInput(
                attrs={
                    "min": "1"
                }
            ),

            "country": forms.TextInput(
                attrs={
                    "placeholder": "Rwanda"
                }
            ),

            "province": forms.TextInput(
                attrs={
                    "placeholder": "Province"
                }
            ),

            "district": forms.TextInput(
                attrs={
                    "placeholder": "District"
                }
            ),

            "sector": forms.TextInput(
                attrs={
                    "placeholder": "Sector"
                }
            ),

            "cell": forms.TextInput(
                attrs={
                    "placeholder": "Cell"
                }
            ),

            "village": forms.TextInput(
                attrs={
                    "placeholder": "Village"
                }
            ),

            "next_of_kin_name": forms.TextInput(
                attrs={
                    "placeholder": "Full names"
                }
            ),

            "next_of_kin_phone": forms.TextInput(
                attrs={
                    "placeholder": "+250 7XX XXX XXX"
                }
            ),

            "next_of_kin_relationship": forms.TextInput(
                attrs={
                    "placeholder": "e.g. Spouse, Brother, Sister"
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.user:
            self.fields["first_name"].initial = (
                self.instance.user.first_name
            )

            self.fields["last_name"].initial = (
                self.instance.user.last_name
            )

            self.fields["email"].initial = (
                self.instance.user.email
            )

    def clean_national_id(self):
        national_id = self.cleaned_data.get("national_id")

        if national_id:
            if not national_id.isdigit():
                raise forms.ValidationError(
                    "National ID must contain only numbers."
                )

            if len(national_id) != 16:
                raise forms.ValidationError(
                    "National ID must contain exactly 16 digits."
                )

        return national_id

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")

        if phone and not phone.startswith("+"):
            raise forms.ValidationError(
                "Phone number must start with the country code, "
                "for example +250."
            )

        return phone

    def clean_next_of_kin_phone(self):
        phone = self.cleaned_data.get("next_of_kin_phone")

        if phone and not phone.startswith("+"):
            raise forms.ValidationError(
                "Phone number must start with the country code, "
                "for example +250."
            )

        return phone    