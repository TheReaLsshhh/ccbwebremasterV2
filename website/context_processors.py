from django.conf import settings


def search_metadata(request):
    site_url = settings.PUBLIC_SITE_URL.rstrip("/")
    return {
        "public_site_url": site_url,
        "canonical_url": f"{site_url}{request.path}",
    }
