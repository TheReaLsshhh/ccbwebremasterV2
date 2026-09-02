from django import forms
from django.utils.html import format_html

from .models import ContactInquiry, PageContent

# Check if django-recaptcha is installed
try:
    from captcha.fields import ReCaptchaField
    from captcha.widgets import ExplicitReCaptchaV2Checkbox

    _HAS_RECAPTCHA = True
except ImportError:
    _HAS_RECAPTCHA = False

class ContactInquiryForm(forms.ModelForm):
    comment = forms.CharField(required=False, widget=forms.HiddenInput)

    if _HAS_RECAPTCHA:
        captcha = ReCaptchaField(
            widget=ExplicitReCaptchaV2Checkbox(
                attrs={
                    "data-callback": "onCaptchaSolved",
                    "data-expired-callback": "onCaptchaExpired",
                    "data-error-callback": "onCaptchaError",
                }
            )
        )

    class Meta:
        model = ContactInquiry
        fields = ["name", "email", "subject", "message"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Your full name",
                    "autocomplete": "name",
                    "maxlength": "100",
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
                    "maxlength": "150",
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Type your message here",
                    "autocomplete": "off",
                    "maxlength": "3000",
                }
            ),
        }

    def clean_comment(self):
        if self.cleaned_data.get("comment"):
            raise forms.ValidationError("Invalid submission.")
        return ""