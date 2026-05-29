from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("website.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Production fallback for environments where collected static files are present
# but not served correctly by the platform-level static setup.
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT, insecure=True)
