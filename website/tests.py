from django.test import TestCase, override_settings


@override_settings(
    ALLOWED_HOSTS=["testserver", "ccbacad.dpdns.org"],
    PUBLIC_SITE_URL="https://ccbacad.dpdns.org",
    SECURE_SSL_REDIRECT=False,
)
class SearchIndexingTests(TestCase):
    def test_robots_txt_allows_public_crawling(self):
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        self.assertContains(response, "User-agent: *")
        self.assertContains(response, "Allow: /")
        self.assertNotContains(response, "Disallow: /")
        self.assertContains(response, "Sitemap: https://ccbacad.dpdns.org/sitemap.xml")

    def test_sitemap_lists_public_pages_with_absolute_urls(self):
        response = self.client.get("/sitemap.xml")
        body = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("<loc>https://ccbacad.dpdns.org/</loc>", body)
        self.assertIn("<loc>https://ccbacad.dpdns.org/academics/</loc>", body)
        self.assertIn("<loc>https://ccbacad.dpdns.org/news/</loc>", body)
        self.assertNotIn("admin", body)
        self.assertNotIn("ccb-office", body)

    def test_canonical_url_uses_current_public_path(self):
        response = self.client.get("/academics/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<link rel="canonical"\n        href="https://ccbacad.dpdns.org/academics/">',
            html=False,
        )
        self.assertNotContains(
            response,
            '<link rel="canonical"\n        href="https://ccbacad.dpdns.org/">',
            html=False,
        )
