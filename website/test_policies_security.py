from datetime import datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urlparse

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import LegalPage, LegalSection


@override_settings(ALLOWED_HOSTS=["testserver"], SECURE_SSL_REDIRECT=False, OLD_PUBLIC_HOSTS=set(), PUBLIC_SITE_URL="https://ccbacad.dpdns.org")
class PolicyAndSecurityTests(TestCase):
    def test_footer_links_replace_old_slogan(self):
        response = self.client.get("/")
        self.assertContains(response, 'href="/terms/"')
        self.assertContains(response, 'href="/privacy/"')
        self.assertNotContains(response, "Learning. Community. Possibility.")

    def test_seeded_policy_drafts_render_with_noindex_and_no_cache(self):
        for name in ("terms", "privacy"):
            response = self.client.get(reverse("website:" + name))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Draft for institutional review")
            self.assertIn("noindex", response["X-Robots-Tag"])
            self.assertIn("no-store", response["Cache-Control"])
            self.assertTrue(LegalPage.objects.get(slug=name).sections.exists())

    def test_only_approved_policy_pages_enter_sitemap(self):
        page = LegalPage.objects.get(slug="privacy")
        before = self.client.get("/sitemap.xml")
        self.assertNotContains(before, "<loc>https://ccbacad.dpdns.org/privacy/</loc>")
        page.approved_for_publication = True
        page.save()
        response = self.client.get("/privacy/")
        self.assertNotContains(response, "Draft for institutional review")
        self.assertNotIn("X-Robots-Tag", response)
        sitemap = self.client.get("/sitemap.xml")
        self.assertContains(sitemap, "<loc>https://ccbacad.dpdns.org/privacy/</loc>")
        self.assertNotContains(sitemap, "<loc>https://ccbacad.dpdns.org/terms/</loc>")

    def test_policy_content_is_escaped(self):
        page = LegalPage.objects.get(slug="terms")
        LegalSection.objects.create(page=page, title="Escaping", body='<script>alert("test")</script>')
        response = self.client.get("/terms/")
        self.assertNotContains(response, '<script>alert("test")</script>')
        self.assertContains(response, "&lt;script&gt;")

    def test_security_txt_uses_configured_host_and_valid_expiry(self):
        response = self.client.get("/.well-known/security.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        fields = dict(line.split(": ", 1) for line in response.content.decode().splitlines())
        self.assertEqual(fields["Contact"], "https://ccbacad.dpdns.org/contact/")
        self.assertEqual(fields["Canonical"], "https://ccbacad.dpdns.org/.well-known/security.txt")
        expires = datetime.fromisoformat(fields["Expires"].replace("Z", "+00:00"))
        self.assertGreater(expires, timezone.now())
        self.assertLessEqual(expires, timezone.now() + timedelta(days=365))

    def test_public_headers_are_effective(self):
        response = self.client.get("/")
        self.assertIn("camera=()", response["Permissions-Policy"])
        policy = response["Content-Security-Policy"]
        for directive in ["object-src 'none'", "frame-ancestors 'none'", "form-action 'self'", "https://recaptcha.google.com", "https://embed.windy.com"]:
            self.assertIn(directive, policy)

    def test_https_policy_upgrades_insecure_resources(self):
        response = self.client.get("/", secure=True)
        self.assertIn("upgrade-insecure-requests", response["Content-Security-Policy"])

    def test_admin_is_not_broken_by_public_csp(self):
        response = self.client.get(reverse("admin:login"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Content-Security-Policy", response)
        self.assertIn("Permissions-Policy", response)

    def test_legal_routes_are_excluded_from_offline_cache(self):
        response = self.client.get("/sw.js")
        for path in ('"/terms/"', '"/privacy/"', '"/.well-known/security.txt"'):
            self.assertContains(response, path)

    def test_contact_has_privacy_notice(self):
        self.assertContains(self.client.get("/contact/"), 'class="contact-privacy-notice"')

    def test_existing_external_scripts_are_in_csp_allowlist(self):
        class Scripts(HTMLParser):
            def __init__(self):
                super().__init__()
                self.sources = []

            def handle_starttag(self, tag, attrs):
                if tag == "script":
                    source = dict(attrs).get("src")
                    if source and source.startswith("https://"):
                        parsed = urlparse(source)
                        self.sources.append(f"{parsed.scheme}://{parsed.netloc}")

        for url in ("/", "/contact/"):
            response = self.client.get(url)
            parser = Scripts()
            parser.feed(response.content.decode())
            for origin in parser.sources:
                self.assertIn(origin, settings.PUBLIC_CONTENT_SECURITY_POLICY)
