from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin import __file__ as admin_file
from django.http import Http404
from django.urls import include, path
from django.views.static import serve
from pathlib import Path

from website.admin_security import setup_pin, verify_pin

admin_static_root = Path(admin_file).resolve().parent / "static" / "admin"


def admin_decoy_not_found(request, path=None):
    """Return 404 for the old /admin/ path so scanners do not find the dashboard."""
    raise Http404


urlpatterns = [
    path(
        "static/admin/<path:path>",
        serve,
        {"document_root": admin_static_root},
    ),
    path("admin/", admin_decoy_not_found),
    path("admin/<path:path>", admin_decoy_not_found),
    path(f"{settings.ADMIN_URL}verify-pin/", verify_pin, name="admin_verify_pin"),
    path(f"{settings.ADMIN_URL}setup-pin/", setup_pin, name="admin_setup_pin"),
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("website.urls")),
]

# Serve media files in all environments.
# With Cloudinary active, Django admin redirects to Cloudinary CDN URLs automatically.
# Without Cloudinary, this serves local files (Render ephemeral disk within session).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT, insecure=True)

# Production fallback for environments where collected static files are present
# but not served correctly by the platform-level static setup.
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT, insecure=True)
