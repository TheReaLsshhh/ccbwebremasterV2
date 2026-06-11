from django import forms
from django.conf import settings

import re
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


EMAIL_LOCAL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?$")
EMAIL_DOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$")
GMAIL_LOCAL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.]*[a-z0-9])?$")
REPEATED_SYMBOL_RE = re.compile(r"[._-]{2,}")
PLACEHOLDER_EMAIL_WORDS = {
    "test",
    "admin",
    "n/a",
    "na",
    "demo",
    "sample",
    "example",
    "fake",
    "temp",
    "nope",
    "idk",
}


def verify_email_with_abstract_api(email):
    """Verify email exists using Abstract API. Returns (is_valid, error_message)."""
    api_key = getattr(settings, "ABSTRACT_API_EMAIL_KEY", "")
    if not api_key:
        return True, ""  # Skip if key not configured

    try:
        url = "https://emailvalidation.abstractapi.com/v1/"
        response = requests.get(url, params={"api_key": api_key, "email": email}, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("is_valid_format", {}).get("value") is False:
            return False, "Enter a valid email address."
        if data.get("is_disposable_email", {}).get("value") is True:
            return False, "Disposable email addresses are not accepted."
        if data.get("is_mx_found", {}).get("value") is False:
            return False, "This email domain cannot receive mail."
        if data.get("is_smtp_valid", {}).get("value") is False:
            return False, "This email account could not be verified."

        deliverability = data.get("deliverability", "UNKNOWN")
        if deliverability == "UNDELIVERABLE":
            return False, "This email address does not exist or is not deliverable."
        if deliverability in {"RISKY", "UNKNOWN"}:
            return False, "This email address appears to be invalid or risky."

        return True, ""
    except requests.RequestException:
        return False, "We could not verify this email right now. Please try again later."


def validate_email_text(email):
    """Apply strict local checks before external email verification."""
    if email.count("@") != 1:
        return False, "Enter a valid email address."

    try:
        email.encode("ascii")
    except UnicodeEncodeError:
        return False, "Email contains invalid characters. Emojis and non-English symbols are not allowed."

    local_part, domain = email.lower().split("@", 1)
    if not local_part or not domain:
        return False, "Enter a valid email address."
    if len(local_part) > 64 or len(email) > 254:
        return False, "Email address is too long."
    if ".." in email:
        return False, "Email cannot contain consecutive dots."

    if not EMAIL_DOMAIN_RE.match(domain):
        return False, "Enter a valid email domain."

    if domain == "gmail.com":
        if len(local_part) < 6:
            return False, "Gmail addresses must have at least 6 characters before @gmail.com."
        if not GMAIL_LOCAL_RE.match(local_part):
            return False, "Gmail addresses can only use letters, numbers, and dots."
    elif domain.endswith(".edu.ph"):
        if not EMAIL_LOCAL_RE.match(local_part):
            return False, "Email contains invalid characters. Only letters, numbers, dots, hyphens, and underscores are allowed."
        if REPEATED_SYMBOL_RE.search(local_part):
            return False, "Email cannot contain repeated special characters."
    else:
        return False, "Email must be a Gmail account or .edu.ph institutional email."

    clean_part = re.sub(r"[._-]", "", local_part)
    if clean_part in PLACEHOLDER_EMAIL_WORDS or any(
        clean_part.startswith(word) for word in PLACEHOLDER_EMAIL_WORDS
    ):
        return False, "Placeholder email addresses are not accepted."

    return True, ""


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

        is_valid_text, error_msg = validate_email_text(email)
        if not is_valid_text:
            raise forms.ValidationError(error_msg)

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
