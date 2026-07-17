from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import redirect
from django.urls import reverse

from .admin_security import (
    admin_2fa_is_verified,
    admin_security_exempt_paths,
    get_staff_security_profile,
)


class CanonicalHostRedirectMiddleware:
    """Permanently redirect retired public hostnames to the canonical site URL."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_host = request.get_host().split(":", 1)[0].lower()
        if request_host in settings.OLD_PUBLIC_HOSTS:
            destination = f"{settings.PUBLIC_SITE_URL}{request.get_full_path()}"
            return HttpResponsePermanentRedirect(destination)
        return self.get_response(request)


class AdminLoginRateLimitMiddleware:
    """Throttle repeated admin login and PIN verification attempts."""

    ADMIN_POST_LIMIT = 30  # per hour for general admin saves
    ADMIN_POST_WINDOW = 3600  # 1 hour

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        admin_login_path = f"/{settings.ADMIN_URL}login/"
        admin_verify_pin_path = f"/{settings.ADMIN_URL}verify-pin/"
        admin_setup_pin_path = f"/{settings.ADMIN_URL}setup-pin/"
        admin_prefix = f"/{settings.ADMIN_URL}"

        if request.method == "POST" and request.path.startswith(admin_prefix):
            client_ip = self._client_ip(request)

            if request.path == admin_login_path:
                if self._is_rate_limited(
                    f"admin-login-attempts:{client_ip}",
                    settings.ADMIN_LOGIN_RATE_LIMIT_ATTEMPTS,
                    settings.ADMIN_LOGIN_RATE_LIMIT_WINDOW,
                ):
                    return HttpResponse(
                        "Too many admin login attempts. Please try again later.",
                        status=429,
                        content_type="text/plain",
                    )
            elif request.path in {admin_verify_pin_path, admin_setup_pin_path}:
                if self._is_rate_limited(
                    f"admin-pin-attempts:{client_ip}",
                    settings.ADMIN_PIN_RATE_LIMIT_ATTEMPTS,
                    settings.ADMIN_PIN_RATE_LIMIT_WINDOW,
                ):
                    return HttpResponse(
                        "Too many PIN attempts. Please try again later.",
                        status=429,
                        content_type="text/plain",
                    )
            else:
                cache_key = f"admin-post-attempts:{client_ip}"
                attempts = cache.get(cache_key, 0) + 1
                cache.set(cache_key, attempts, self.ADMIN_POST_WINDOW)

                if attempts > self.ADMIN_POST_LIMIT:
                    return HttpResponse(
                        "Too many requests. Please try again later.",
                        status=429,
                        content_type="text/plain",
                    )

        response = self.get_response(request)
        if (
            request.method == "POST"
            and request.path == admin_login_path
            and response.status_code in {301, 302}
        ):
            cache.delete(f"admin-login-attempts:{self._client_ip(request)}")
        return response

    @staticmethod
    def _is_rate_limited(cache_key, max_attempts, window_seconds):
        attempts = cache.get(cache_key, 0) + 1
        cache.set(cache_key, attempts, window_seconds)
        return attempts > max_attempts

    @staticmethod
    def _client_ip(request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")


class AdminTwoFactorMiddleware:
    """Require a verified 6-digit PIN before staff can use the admin dashboard."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        admin_prefix = f"/{settings.ADMIN_URL}"
        if not request.path.startswith(admin_prefix):
            return self.get_response(request)

        if request.path in admin_security_exempt_paths():
            return self.get_response(request)

        if request.user.is_authenticated and request.user.is_staff and not admin_2fa_is_verified(request):
            profile = get_staff_security_profile(request.user)
            next_param = request.get_full_path()
            if not profile.has_pin:
                setup_path = reverse("admin_setup_pin")
                if request.path != setup_path:
                    return redirect(f"{setup_path}?next={next_param}")
            else:
                verify_path = reverse("admin_verify_pin")
                if request.path != verify_path:
                    return redirect(f"{verify_path}?next={next_param}")

        return self.get_response(request)
