from django.conf import settings
from django.http import HttpResponse

PUBLIC_SITEMAP_PATHS = (
    ("", "weekly", "1.0"),
    ("about/", "weekly", "0.7"),
    ("admissions/", "weekly", "0.8"),
    ("academics/", "weekly", "0.8"),
    ("faculty/", "weekly", "0.6"),
    ("students/", "weekly", "0.7"),
    ("downloads/", "weekly", "0.7"),
    ("news/", "weekly", "0.8"),
    ("contact/", "weekly", "0.6"),
)


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


def sitemap_xml(request):
    site_url = settings.PUBLIC_SITE_URL.rstrip("/")
    url_entries = []
    for path, changefreq, priority in PUBLIC_SITEMAP_PATHS:
        url_entries.append(
            "\n".join(
                [
                    "  <url>",
                    f"    <loc>{site_url}/{path}</loc>",
                    f"    <changefreq>{changefreq}</changefreq>",
                    f"    <priority>{priority}</priority>",
                    "  </url>",
                ]
            )
        )

    content = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            *url_entries,
            "</urlset>",
            "",
        ]
    )
    response = HttpResponse(content, content_type="application/xml; charset=utf-8")
    response["Cache-Control"] = "public, max-age=300"
    return response
