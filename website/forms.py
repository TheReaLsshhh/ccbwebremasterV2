from django import forms
from django.conf import settings

import requests

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


def verify_email_with_abstract_api(email):
    """Verify email exists using Abstract API. Returns (is_valid, error_message)"""
    api_key = getattr(settings, "ABSTRACT_API_EMAIL_KEY", "")
    if not api_key:
        return True, ""  # Skip if key not configured

    try:
        url = "https://emailvalidation.abstractapi.com/v1/"
        response = requests.get(url, params={"api_key": api_key, "email": email}, timeout=5)
        response.raise_for_status()
        data = response.json()

        # Check if email is deliverable
        deliverability = data.get("deliverability", "UNKNOWN")
        if deliverability == "UNDELIVERABLE":
            return False, "This email address does not exist or is not deliverable."
        if deliverability == "RISKY":
            return False, "This email address appears to be invalid or risky."

        return True, ""
    except requests.RequestException:
        return True, ""  # Fail gracefully if API unavailable


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

        # Verify email exists with Abstract API
        is_valid, error_msg = verify_email_with_abstract_api(email)
        if not is_valid:
            raise forms.ValidationError(error_msg)

        return email
