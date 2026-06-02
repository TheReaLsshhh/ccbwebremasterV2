import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def csrf_trusted_origins_from_hosts(hosts):
    """Build https:// origins for Django CSRF checks (required for HTTPS admin saves)."""
    origins = set()
    for host in hosts:
        host = host.strip()
        if not host or host == "*":
            continue
        if host.startswith("."):
            origins.add(f"https://*{host}")
        else:
            origins.add(f"https://{host}")
    return sorted(origins)


SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-me")
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "").split(",") if host.strip()]

if DEBUG and os.getenv("ALLOWED_HOSTS") is None:
    ALLOWED_HOSTS = ["*", "localhost", "127.0.0.1"]

if not DEBUG and SECRET_KEY == "django-insecure-change-me":
    raise ImproperlyConfigured("Set SECRET_KEY before running in production.")

USE_CLOUDINARY = bool(os.getenv("CLOUDINARY_URL") or os.getenv("CLOUDINARY_CLOUD_NAME"))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "website",
]

if USE_CLOUDINARY:
    INSTALLED_APPS = ["cloudinary_storage", *INSTALLED_APPS, "cloudinary"]

# Dynamic Caching Backend (Redis in production with local memory fallback)
REDIS_URL = os.getenv("REDIS_URL") or os.getenv("REDIS_TLS_URL")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache" if REDIS_URL else "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": REDIS_URL or "ccb-locmem-cache",
    }
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "website.middleware.AdminLoginRateLimitMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ccbwebsite.urls"
ADMIN_URL = os.getenv("ADMIN_URL", "admin/").strip("/")
ADMIN_URL = f"{ADMIN_URL}/" if ADMIN_URL else "admin/"
ADMIN_LOGIN_RATE_LIMIT_ATTEMPTS = int(os.getenv("ADMIN_LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
ADMIN_LOGIN_RATE_LIMIT_WINDOW = int(os.getenv("ADMIN_LOGIN_RATE_LIMIT_WINDOW", "900"))

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ccbwebsite.wsgi.application"
ASGI_APPLICATION = "ccbwebsite.asgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=int(os.getenv("DATABASE_CONN_MAX_AGE", "600")),
        conn_health_checks=env_bool("DATABASE_CONN_HEALTH_CHECKS", True),
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Manila")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
WHITENOISE_USE_FINDERS = True

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

from whitenoise.storage import CompressedManifestStaticFilesStorage

class SafeCompressedManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False

STORAGES = {
    "default": {
        "BACKEND": (
            "cloudinary_storage.storage.MediaCloudinaryStorage"
            if USE_CLOUDINARY
            else "django.core.files.storage.FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": "ccbwebsite.settings.SafeCompressedManifestStaticFilesStorage",
    },
}
WHITENOISE_MANIFEST_STRICT = env_bool("WHITENOISE_MANIFEST_STRICT", False)

# Compatibility aliases for packages that still expect the legacy Django storage settings.
DEFAULT_FILE_STORAGE = STORAGES["default"]["BACKEND"]
STATICFILES_STORAGE = STORAGES["staticfiles"]["BACKEND"]

if os.getenv("CLOUDINARY_CLOUD_NAME"):
    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME", ""),
        "API_KEY": os.getenv("CLOUDINARY_API_KEY", ""),
        "API_SECRET": os.getenv("CLOUDINARY_API_SECRET", ""),
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

if not DEBUG:
    # Without trusted origins, every admin Save POST returns 403 on HTTPS (Render).
    if not CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS = csrf_trusted_origins_from_hosts(ALLOWED_HOSTS)
    else:
        CSRF_TRUSTED_ORIGINS = sorted(
            set(CSRF_TRUSTED_ORIGINS) | set(csrf_trusted_origins_from_hosts(ALLOWED_HOSTS))
        )

    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = env_bool("USE_X_FORWARDED_HOST", True)
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", "28800"))
    SESSION_EXPIRE_AT_BROWSER_CLOSE = env_bool("SESSION_EXPIRE_AT_BROWSER_CLOSE", False)
    SESSION_SAVE_EVERY_REQUEST = env_bool("SESSION_SAVE_EVERY_REQUEST", False)
    CSRF_COOKIE_SECURE = True
    # Must be readable for some admin flows; form POST still sends csrfmiddlewaretoken.
    CSRF_COOKIE_HTTPONLY = env_bool("CSRF_COOKIE_HTTPONLY", False)
    CSRF_COOKIE_SAMESITE = "Lax"
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
    SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp-relay.brevo.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "City College of Bayawan <no-reply@citycollegeofbayawan.edu.ph>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
CONTACT_INQUIRY_RECIPIENT = os.getenv("CONTACT_INQUIRY_RECIPIENT", "citycollegeofbayawan@gmail.com")
