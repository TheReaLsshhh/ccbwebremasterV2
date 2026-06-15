from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.signals import user_logged_out
from django.core.cache import cache
from django.dispatch import receiver
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .models import StaffSecurityProfile

ADMIN_2FA_SESSION_KEY = "admin_2fa_verified"
ADMIN_2FA_USER_KEY = "admin_2fa_user_id"


def admin_2fa_is_verified(request):
    if not request.user.is_authenticated:
        return False
    return (
        request.session.get(ADMIN_2FA_SESSION_KEY) is True
        and request.session.get(ADMIN_2FA_USER_KEY) == request.user.pk
    )


def clear_admin_2fa_session(request):
    if hasattr(request, "session"):
        request.session.pop(ADMIN_2FA_SESSION_KEY, None)
        request.session.pop(ADMIN_2FA_USER_KEY, None)


def mark_admin_2fa_verified(request):
    request.session[ADMIN_2FA_SESSION_KEY] = True
    request.session[ADMIN_2FA_USER_KEY] = request.user.pk
    request.session.modified = True


def get_staff_security_profile(user):
    profile, _ = StaffSecurityProfile.objects.get_or_create(user=user)
    return profile


def admin_security_exempt_paths():
    admin_prefix = f"/{settings.ADMIN_URL}"
    return {
        f"{admin_prefix}login/",
        f"{admin_prefix}logout/",
        f"{admin_prefix}verify-pin/",
        f"{admin_prefix}setup-pin/",
    }


class AdminPinForm(forms.Form):
    pin = forms.CharField(
        label="6-digit PIN",
        max_length=6,
        min_length=6,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]{6}",
                "maxlength": "6",
                "class": "vTextField",
                "placeholder": "••••••",
            }
        ),
    )

    def clean_pin(self):
        pin = self.cleaned_data.get("pin", "").strip()
        is_valid, result = StaffSecurityProfile.validate_pin_format(pin)
        if not is_valid:
            raise forms.ValidationError(result)
        return result


class AdminSetupPinForm(forms.Form):
    pin = forms.CharField(
        label="New 6-digit PIN",
        max_length=6,
        min_length=6,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "inputmode": "numeric",
                "pattern": "[0-9]{6}",
                "maxlength": "6",
                "class": "vTextField",
            }
        ),
    )
    pin_confirm = forms.CharField(
        label="Confirm PIN",
        max_length=6,
        min_length=6,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "inputmode": "numeric",
                "pattern": "[0-9]{6}",
                "maxlength": "6",
                "class": "vTextField",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        pin = cleaned_data.get("pin", "").strip()
        pin_confirm = cleaned_data.get("pin_confirm", "").strip()
        is_valid, result = StaffSecurityProfile.validate_pin_format(pin)
        if not is_valid:
            self.add_error("pin", result)
            return cleaned_data
        if pin != pin_confirm:
            self.add_error("pin_confirm", "PIN entries do not match.")
        else:
            cleaned_data["pin"] = result
        return cleaned_data


@never_cache
@staff_member_required
@require_http_methods(["GET", "POST"])
@csrf_protect
def verify_pin(request):
    profile = get_staff_security_profile(request.user)
    if not profile.has_pin:
        return redirect("admin_setup_pin")

    if admin_2fa_is_verified(request):
        return redirect(reverse("admin:index"))

    form = AdminPinForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if profile.check_pin(form.cleaned_data["pin"]):
            mark_admin_2fa_verified(request)
            forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
            client_ip = (
                forwarded_for.split(",", 1)[0].strip()
                if forwarded_for
                else request.META.get("REMOTE_ADDR", "unknown")
            )
            cache.delete(f"admin-pin-attempts:{client_ip}")
            next_url = request.GET.get("next") or reverse("admin:index")
            return redirect(next_url)
        messages.error(request, "Incorrect PIN. Please try again.")

    return render(
        request,
        "admin/verify_pin.html",
        {
            "form": form,
            "title": "Verify PIN",
            "site_header": "CCB Administration",
            "site_title": "CCB Admin",
        },
    )


@never_cache
@staff_member_required
@require_http_methods(["GET", "POST"])
@csrf_protect
def setup_pin(request):
    profile = get_staff_security_profile(request.user)
    if profile.has_pin and admin_2fa_is_verified(request):
        return redirect(reverse("admin:index"))

    form = AdminSetupPinForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        profile.set_pin(form.cleaned_data["pin"])
        mark_admin_2fa_verified(request)
        messages.success(request, "Your admin PIN has been saved.")
        return redirect(reverse("admin:index"))

    return render(
        request,
        "admin/setup_pin.html",
        {
            "form": form,
            "title": "Set Admin PIN",
            "site_header": "CCB Administration",
            "site_title": "CCB Admin",
            "is_first_setup": not profile.has_pin,
        },
    )


@receiver(user_logged_out)
def clear_admin_2fa_on_logout(sender, request, user, **kwargs):
    if request is not None:
        clear_admin_2fa_session(request)
