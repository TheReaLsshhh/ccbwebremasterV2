from django.test import TestCase, override_settings


@override_settings(
    ALLOWED_HOSTS=["testserver", "ccbacad.dpdns.org"],
    PUBLIC_SITE_URL="https://ccbacad.dpdns.org",
    OLD_PUBLIC_HOSTS=set(),
    SECURE_SSL_REDIRECT=False,
)
class SearchIndexingTests(TestCase):
    def test_robots_txt_allows_public_crawling(self):
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        self.assertContains(response, "User-agent: Googlebot")
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
        self.assertNotIn("/admin/", body)
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
            "/about/vision-mission-goals-core-values/": "Vision, Mission, Goals, Core Values | City College of Bayawan",
            "/academics/": "Academic Programs | City College of Bayawan",
            "/admissions/": "Admissions | City College of Bayawan",
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
        self.assertContains(response, '"@type": "WebSite"', html=False)
        self.assertContains(response, '"alternateName": ["CCB", "CCB Bayawan"]', html=False)

    def test_primary_hostname_serves_without_redirect(self):
        response = self.client.get(
            "/academics/?program=education",
            HTTP_HOST="ccbacad.dpdns.org",
        )

        self.assertEqual(response.status_code, 200)

    def test_favicon_is_linked_with_google_compliant_sizes(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<link rel="icon" href="https://ccbacad.dpdns.org/static/favicon.ico" sizes="any">',
            html=False,
        )
        self.assertContains(
            response,
            'href="https://ccbacad.dpdns.org/static/images/hero-images/ccb-logo-48.png" sizes="16x16 32x32 48x48"',
            html=False,
        )
        self.assertContains(
            response,
            'rel="apple-touch-icon" href="https://ccbacad.dpdns.org/static/images/hero-images/ccb-logo-192.png"',
            html=False,
        )

    def test_favicon_ico_serves_icon(self):
        response = self.client.get("/favicon.ico")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/x-icon")
        self.assertTrue(response.content)


from datetime import timedelta
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from .models import (
    AcademicProgram, AdmissionRequirement, AdmissionStep, CampusOffice,
    CampusService, DownloadItem, FacultyStaffEntry, FacultyStaffSection,
    FrequentlyAskedQuestion, NewsEvent, StudentResource,
)


@override_settings(ALLOWED_HOSTS=["testserver"], SECURE_SSL_REDIRECT=False)
class PublicWebsiteTests(TestCase):
    def setUp(self):
        cache.clear()
        self.program = AcademicProgram.objects.create(name="Community Education", description="Prepare for a career in teaching.", department="Education")
        self.hidden_program = AcademicProgram.objects.create(name="Private draft program", description="Private draft text", published=False)
        self.news = NewsEvent.objects.create(title="Campus achievement", summary="Learning together", content="The complete campus story.")
        self.hidden_news = NewsEvent.objects.create(title="Private draft news", summary="Private draft text", published=False)
        self.future_news = NewsEvent.objects.create(title="Future release", summary="Not released", published_at=timezone.now()+timedelta(days=2))
        self.section = FacultyStaffSection.objects.create(title="Teaching staff")
        self.person = FacultyStaffEntry.objects.create(name="Test Educator", role="Instructor", department="Education", section=self.section)

    def test_all_public_pages_render_with_shared_layout(self):
        for route in ["home", "academics", "admissions", "news", "downloads", "students", "contact", "search"]:
            with self.subTest(route=route):
                response = self.client.get(reverse("website:"+route))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="main-content"')
                self.assertContains(response, "css/institutional.css")
                self.assertNotContains(response, "A more structured")
                self.assertNotContains(response, "+63 000")

    def test_program_detail_uses_content_and_metadata(self):
        response = self.client.get(reverse("website:program_detail", args=[self.program.pk]))
        self.assertContains(response, "Prepare for a career in teaching.")
        self.assertContains(response, "Community Education | City College of Bayawan")
        self.assertContains(response, "Education")

    def test_unpublished_details_are_not_accessible(self):
        for route, pk in [("program_detail", self.hidden_program.pk), ("news_detail", self.hidden_news.pk), ("news_detail", self.future_news.pk)]:
            self.assertEqual(self.client.get(reverse("website:"+route, args=[pk])).status_code, 404)

    def test_home_and_news_exclude_drafts_and_future_releases(self):
        for path in ["/", "/news/"]:
            response = self.client.get(path)
            self.assertNotContains(response, "Private draft")
            self.assertNotContains(response, "Future release")
            self.assertContains(response, "Campus achievement")

    def test_search_finds_program_and_excludes_private_records(self):
        response = self.client.get("/search/", {"q": "Education"})
        self.assertContains(response, reverse("website:program_detail", args=[self.program.pk]))
        self.assertContains(response, "Community Education")
        response = self.client.get("/search/", {"q": "Private draft"})
        self.assertEqual(response.context["page_obj"].paginator.count, 0)
        response = self.client.get("/search/", {"q": "Future release"})
        self.assertEqual(response.context["page_obj"].paginator.count, 0)

    def test_search_query_is_escaped(self):
        response = self.client.get("/search/", {"q": '<script>alert(1)</script>'})
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, "&lt;script&gt;")

    def test_academic_search_and_partial_match(self):
        for path in ["/academics/", "/academics/partial/"]:
            response = self.client.get(path, {"q": "Education"})
            self.assertContains(response, "Community Education")
            self.assertNotContains(response, "Private draft program")
            response = self.client.get(path, {"q": "nonexistent"})
            self.assertNotContains(response, "Community Education")

    def test_download_filters_and_pagination_preserve_selection(self):
        for i in range(14):
            DownloadItem.objects.create(title=f"Enrollment guide {i:02}", category="form", file=f"downloads/{i}.pdf")
        DownloadItem.objects.create(title="Enrollment policy", category="policy", file="downloads/policy.pdf")
        DownloadItem.objects.create(title="Private enrollment guide", category="form", file="downloads/private.pdf", published=False)
        response = self.client.get("/downloads/", {"q": "Enrollment", "category": "form"})
        self.assertEqual(response.context["page_obj"].paginator.count, 14)
        self.assertNotContains(response, "Enrollment policy")
        self.assertNotContains(response, "Private enrollment guide")
        self.assertContains(response, "category=form")
        self.assertContains(response, "q=Enrollment")
        response = self.client.get("/downloads/partial/", {"q": "Enrollment", "category": "form", "page": 2})
        self.assertContains(response, "Enrollment guide 13")
        self.assertNotContains(response, "Enrollment guide 00")

    def test_invalid_pagination_and_category_do_not_crash(self):
        for path in ["/downloads/", "/news/", "/search/?q=education&page=nonsense"]:
            response = self.client.get(path, {"page": "nonsense", "category": "invalid"})
            self.assertEqual(response.status_code, 200)

    def test_student_search_hides_drafts(self):
        StudentResource.objects.create(title="Scholarship guide", description="Student support")
        StudentResource.objects.create(title="Private scholarship", published=False)
        for path in ["/students/", "/students/partial/"]:
            response = self.client.get(path, {"q": "scholarship"})
            self.assertContains(response, "Scholarship guide")
            self.assertNotContains(response, "Private scholarship")

    def test_faculty_frontend_is_retired_without_deleting_records(self):
        response = self.client.get("/faculty/")
        self.assertRedirects(response, "/about/administrators/", status_code=301)
        self.assertTrue(FacultyStaffEntry.objects.filter(pk=self.person.pk).exists())
        self.assertNotContains(self.client.get("/"), 'href="/faculty/"')
        self.assertEqual(self.client.get("/search/", {"q": "Test Educator"}).context["page_obj"].paginator.count, 0)
        self.assertNotContains(self.client.get("/sitemap.xml"), "/faculty/")

    def test_admissions_steps_and_checklist_are_admin_managed(self):
        AdmissionStep.objects.create(title="Book an appointment", description="Contact admissions.")
        AdmissionStep.objects.create(title="Private step", description="Draft", published=False)
        AdmissionRequirement.objects.create(title="School documents")
        AdmissionRequirement.objects.create(title="Private requirement", published=False)
        response = self.client.get("/admissions/")
        self.assertContains(response, "Book an appointment")
        self.assertContains(response, "School documents")
        self.assertNotContains(response, 'type="checkbox"')
        self.assertContains(response, 'class="requirement-marker"')
        self.assertNotContains(response, "Private step")
        self.assertNotContains(response, "Private requirement")

    def test_services_visibility_does_not_restore_hardcoded_links(self):
        service = CampusService.objects.create(title="Campus library", url="https://example.edu/library")
        self.assertContains(self.client.get("/students/"), "Campus library")
        service.published = False
        service.save()
        response = self.client.get("/students/")
        self.assertNotContains(response, "Campus library")
        self.assertNotContains(response, "GIYA Center")

    def test_office_directory_search(self):
        CampusOffice.objects.create(name="Registrar", email="registrar@example.edu", location="Main building")
        CampusOffice.objects.create(name="Private office", published=False)
        response = self.client.get("/contact/", {"q": "Registrar"})
        self.assertContains(response, 'mailto:registrar@example.edu')
        self.assertNotContains(response, "Private office")
        self.assertIn("no-store", response["Cache-Control"])

    def test_news_search_deep_link_uses_filtered_order(self):
        for i in range(8):
            NewsEvent.objects.create(title=f"Unrelated event {i}", summary="Other")
        response = self.client.get("/news/", {"q": "achievement", "open": self.news.pk})
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertEqual(response.context["open_news_id"], self.news.pk)
        response = self.client.get(reverse("website:news_detail", args=[self.news.pk]))
        self.assertContains(response, "The complete campus story.")

    def test_news_unpublishing_updates_deep_link_mapping(self):
        from .views import _news_page_by_id
        self.assertIn(self.news.pk, _news_page_by_id())
        self.news.published = False
        self.news.save()
        self.assertNotIn(self.news.pk, _news_page_by_id())

    def test_sitemap_only_includes_published_details(self):
        response = self.client.get("/sitemap.xml")
        self.assertContains(response, reverse("website:program_detail", args=[self.program.pk]))
        self.assertContains(response, reverse("website:news_detail", args=[self.news.pk]))
        for route, pk in [("program_detail", self.hidden_program.pk), ("news_detail", self.hidden_news.pk), ("news_detail", self.future_news.pk)]:
            self.assertNotContains(response, reverse("website:"+route, args=[pk]))

    def test_placeholder_faq_is_not_public(self):
        FrequentlyAskedQuestion.objects.create(question="Placeholder question", answer="Lorem ipsum dolor sit amet", layout="home")
        self.assertNotContains(self.client.get("/"), "Placeholder question")


    def test_home_slideshow_uses_published_ordered_banners(self):
        from .models import HomeSlide
        HomeSlide.objects.create(title="First banner", image="pages/first.jpg", sort_order=1)
        HomeSlide.objects.create(title="Second banner", image="pages/second.jpg", sort_order=2)
        HomeSlide.objects.create(title="Private banner", image="pages/private.jpg", sort_order=0, published=False)
        response = self.client.get("/")
        slides = response.context["hero_slides"]
        self.assertEqual([slide["image"].name for slide in slides], ["pages/first.jpg", "pages/second.jpg"])
        self.assertNotContains(response, "pages/private.jpg")
        self.assertNotContains(response, "hero-slideshow-controls")
        self.assertNotContains(response, "data-slide-pause")
        self.assertContains(response, "js/college-motion.js")


    def test_about_dropdown_has_five_destinations_on_desktop_and_mobile(self):
        from .views import ABOUT_MENU_ITEMS
        response = self.client.get("/")
        self.assertEqual(len(response.context["about_menu_items"]), 5)
        self.assertContains(response, 'id="aboutDropdown"')
        self.assertContains(response, 'id="mobileAboutMenu"')
        self.assertNotContains(response, 'href="/faculty/"')
        html = response.content.decode()
        for item in ABOUT_MENU_ITEMS:
            url = reverse("website:about_section", kwargs={"section": item["slug"]})
            self.assertGreaterEqual(html.count(f'href="{url}"'), 2)

    def test_all_about_sections_render_with_matching_titles(self):
        from .views import ABOUT_MENU_ITEMS
        for item in ABOUT_MENU_ITEMS:
            response = self.client.get(reverse("website:about_section", kwargs={"section": item["slug"]}))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["about_section_title"], item["label"])
            self.assertEqual(response.context["active_page"], "website:about")
            self.assertContains(response, 'aria-current="page"')

    def test_about_content_respects_publication_and_sitemap(self):
        from .models import PageContent
        page = PageContent.objects.filter(page=PageContent.ABOUT_HISTORY).first()
        self.assertIsNotNone(page)
        page.body_text = "An unpublished institutional history."
        page.save()
        url = reverse("website:about_section", kwargs={"section": "history"})
        response = self.client.get(url)
        self.assertNotContains(response, "An unpublished institutional history.")
        self.assertTrue(response.context["noindex"])
        self.assertNotContains(self.client.get("/sitemap.xml"), url)
        page.published = True
        page.save()
        self.assertContains(self.client.get(url), "An unpublished institutional history.")
        self.assertContains(self.client.get("/sitemap.xml"), url)

    def test_unknown_about_section_returns_404(self):
        self.assertEqual(self.client.get("/about/not-a-section/").status_code, 404)

    def test_about_editor_view_on_site_resolves_subpage(self):
        from django.contrib import admin
        from .models import PageContent
        page = PageContent.objects.filter(page=PageContent.ABOUT_TRUSTEES).first()
        self.assertEqual(admin.site._registry[PageContent].view_on_site(page), "/about/board-of-trustees/")

    def test_requirement_list_is_read_only_but_document_links_work(self):
        AdmissionRequirement.objects.create(title="Prepare this document", document_file="admissions/example.pdf")
        response = self.client.get("/admissions/")
        self.assertContains(response, 'class="requirements-list"')
        self.assertContains(response, 'class="requirement-marker"')
        self.assertContains(response, "admissions/example.pdf")
        self.assertNotContains(response, 'type="checkbox"')
        self.assertNotContains(response, 'role="checkbox"')
        self.assertNotContains(response, "Check items as you prepare")


    def test_about_overview_is_retired_and_subnavigation_has_only_five_links(self):
        from html.parser import HTMLParser
        class AboutLinks(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_navigation = False
                self.links = []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "nav" and attrs.get("class") == "about-section-navigation":
                    self.in_navigation = True
                elif tag == "a" and self.in_navigation:
                    self.links.append(attrs.get("href"))
            def handle_endtag(self, tag):
                if tag == "nav":
                    self.in_navigation = False
        self.assertRedirects(self.client.get("/about/"), "/about/vision-mission-goals-core-values/", status_code=301)
        response = self.client.get("/about/history/")
        parser = AboutLinks()
        parser.feed(response.content.decode())
        self.assertEqual(len(parser.links), 5)
        self.assertNotIn("/about/", parser.links)
        self.assertNotContains(response, 'href="/about/"')
        self.assertNotContains(response, "Rooted in Bayawan.")
