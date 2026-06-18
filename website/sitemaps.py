from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class PublicPageSitemap(Sitemap):
    protocol = "https"
    changefreq = "weekly"
    priority = 0.7

    public_pages = (
        ("website:home", 1.0),
        ("website:about", 0.7),
        ("website:admissions", 0.8),
        ("website:academics", 0.8),
        ("website:faculty", 0.6),
        ("website:students", 0.7),
        ("website:downloads", 0.7),
        ("website:news", 0.8),
        ("website:contact", 0.6),
    )

    def items(self):
        return self.public_pages

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]

    def get_urls(self, page=1, site=None, protocol=None):
        urls = super().get_urls(page=page, site=site, protocol=protocol)
        site_url = settings.PUBLIC_SITE_URL.rstrip("/")
        for url in urls:
            url["location"] = f"{site_url}{urlparse(url['location']).path}"
        return urls
