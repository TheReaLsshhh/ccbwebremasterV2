from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.files.base import ContentFile
from django.http import HttpResponse, Http404
from django.urls import reverse
from django.utils import timezone
from .models import AcademicProgram, NewsEvent, LegalPage, PageContent

PUBLIC_SITEMAP_PATHS = (
    ("", "weekly", "1.0"),
    ("admissions/", "weekly", "0.8"),
    ("academics/", "weekly", "0.8"),
    ("students/", "weekly", "0.7"),
    ("downloads/", "weekly", "0.7"),
    ("news/", "weekly", "0.8"),
    ("contact/", "weekly", "0.6"),
)


def robots_txt(request):
    sitemap_url = f"{settings.PUBLIC_SITE_URL.rstrip('/')}/sitemap.xml"
    content = "\n".join(
        [
            "User-agent: Googlebot",
            "Allow: /",
            "",
            "User-agent: *",
            "Allow: /",
            "",
            f"Sitemap: {sitemap_url}",
            "",
        ]
    )
    response = HttpResponse(content, content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = "public, max-age=86400, s-maxage=86400, stale-while-revalidate=604800"
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

    for route, queryset in [
        ("website:program_detail", AcademicProgram.objects.filter(published=True)),
        ("website:news_detail", NewsEvent.objects.filter(published=True, published_at__lte=timezone.now())),
    ]:
        for pk in queryset.values_list("pk", flat=True):
            url_entries.append(f"  <url><loc>{site_url}{reverse(route, args=[pk])}</loc></url>")

    from .views import ABOUT_MENU_ITEMS
    visible_about_pages = set(PageContent.objects.filter(page__in=PageContent.ABOUT_PAGE_KEYS, published=True).values_list("page", flat=True))
    for item in ABOUT_MENU_ITEMS:
        if item["page"] in visible_about_pages:
            url_entries.append(f"  <url><loc>{site_url}{reverse('website:about_section', kwargs={'section': item['slug']})}</loc></url>")

    for slug in LegalPage.objects.filter(approved_for_publication=True).values_list("slug", flat=True):
        url_entries.append(f"  <url><loc>{site_url}{reverse('website:' + slug)}</loc></url>")

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
    response["Cache-Control"] = "public, max-age=86400, s-maxage=86400, stale-while-revalidate=604800"
    return response


def favicon_ico(request):
    try:
        with staticfiles_storage.open("favicon.ico", "rb") as f:
            data = f.read()
    except (FileNotFoundError, OSError):
        raise Http404
    response = HttpResponse(data, content_type="image/x-icon")
    response["Cache-Control"] = "public, max-age=604800, s-maxage=2592000, stale-while-revalidate=31536000"
    return response
