from django import forms
from django.conf import settings

from .models import ContactInquiry

try:
    from disposable_email_domains import blocklist
    _HAS_DISPOSABLE_CHECK = True
except ImportError:
    _HAS_DISPOSABLE_CHECK = False

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

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            return email

        # Check domain whitelist (Gmail and .edu.ph only)
        if not (email.endswith("@gmail.com") or email.endswith(".edu.ph")):
            raise forms.ValidationError("Email must be a Gmail account or .edu.ph institutional email.")

        # Check if email domain is on disposable email blocklist
        if _HAS_DISPOSABLE_CHECK:
            domain = email.split("@")[1]
            if domain in blocklist:
                raise forms.ValidationError("This email domain is not accepted. Please use a personal or institutional email.")

        return email
