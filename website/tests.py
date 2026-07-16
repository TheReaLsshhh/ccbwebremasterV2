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
        self.assertEqual(response["Content-Type"], "application/xml; charset=utf-8")
        self.assertTrue(body.startswith('<?xml version="1.0" encoding="UTF-8"?>'))
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
            '<link rel="canonical" href="https://ccbacad.dpdns.org/academics/">',
            html=False,
        )
        self.assertNotContains(
            response,
            '<link rel="canonical" href="https://ccbacad.dpdns.org/">',
            html=False,
        )

    def test_public_pages_have_unique_search_metadata(self):
        expected = {
            "/": "City College of Bayawan | Official Website",
            "/about/": "About City College of Bayawan | Mission and Campus",
            "/academics/": "Academic Programs | City College of Bayawan",
            "/admissions/": "Admissions | City College of Bayawan",
            "/faculty/": "Faculty and Staff | City College of Bayawan",
            "/students/": "Student Resources | City College of Bayawan",
            "/downloads/": "Forms and Downloads | City College of Bayawan",
            "/news/": "Campus News and Events | City College of Bayawan",
            "/contact/": "Contact City College of Bayawan",
        }

        descriptions = set()
        for path, title in expected.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertContains(response, f"<title>{title}</title>", html=False)
                self.assertContains(response, '<meta name="description" content="', html=False)
                self.assertContains(response, f'<meta property="og:title" content="{title}">', html=False)
                descriptions.add(response.context["seo_description"])

        self.assertEqual(len(descriptions), len(expected))

    def test_homepage_identifies_the_college_with_structured_data(self):
        response = self.client.get("/")

        self.assertContains(response, '<script type="application/ld+json">', html=False)
        self.assertContains(response, '"@type": "CollegeOrUniversity"', html=False)
        self.assertContains(response, '"name": "City College of Bayawan"', html=False)
