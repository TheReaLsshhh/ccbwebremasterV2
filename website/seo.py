from django.conf import settings
from django.http import HttpResponse


def robots_txt(request):
    sitemap_url = f"{settings.PUBLIC_SITE_URL.rstrip('/')}/sitemap.xml"
    content = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "",
            f"Sitemap: {sitemap_url}",
            "",
        ]
    )
    response = HttpResponse(content, content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = "public, max-age=300"
    return response
