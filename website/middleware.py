from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse


class AdminLoginRateLimitMiddleware:
    """Throttle repeated admin login attempts and general admin POST requests."""

    ADMIN_POST_LIMIT = 30  # per hour
    ADMIN_POST_WINDOW = 3600  # 1 hour

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        admin_login_path = f"/{settings.ADMIN_URL}login/"
        admin_prefix = f"/{settings.ADMIN_URL}"

        if request.method == "POST" and request.path.startswith(admin_prefix):
            client_ip = self._client_ip(request)

            # Stricter limit for login page
            if request.path == admin_login_path:
                cache_key = f"admin-login-attempts:{client_ip}"
                attempts = cache.get(cache_key, 0) + 1
                cache.set(cache_key, attempts, settings.ADMIN_LOGIN_RATE_LIMIT_WINDOW)

                if attempts > settings.ADMIN_LOGIN_RATE_LIMIT_ATTEMPTS:
                    return HttpResponse(
                        "Too many admin login attempts. Please try again later.",
                        status=429,
                        content_type="text/plain",
                    )
            else:
                # General admin POST rate limit
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
    def _client_ip(request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")
