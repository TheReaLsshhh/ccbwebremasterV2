from django import forms
from django.conf import settings

from .models import ContactInquiry

try:
    from django_recaptcha.fields import ReCaptchaField
    from django_recaptcha.widgets import ReCaptchaV2Checkbox
    _HAS_RECAPTCHA = bool(settings.RECAPTCHA_PUBLIC_KEY and settings.RECAPTCHA_PRIVATE_KEY)
except ImportError:
    _HAS_RECAPTCHA = False


class ContactInquiryForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    if _HAS_RECAPTCHA:
        captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)

    class Meta:
        model = ContactInquiry
        fields = ["name", "email", "subject", "message"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Your full name",
                    "autocomplete": "name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "name@example.com",
                    "autocomplete": "email",
                    "inputmode": "email",
                }
            ),
            "subject": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "How can we help?",
                    "autocomplete": "off",
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Type your message here",
                    "autocomplete": "off",
                }
            ),
        }

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Invalid submission.")
        return ""
