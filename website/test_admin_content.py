from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth.models import Permission, User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import HomeSlide, PageContent, SiteSettings


@override_settings(ALLOWED_HOSTS=["testserver"], SECURE_SSL_REDIRECT=False)
class AdminContentTests(TestCase):
    def setUp(self):
        cache.clear()
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.storage_override = override_settings(
            MEDIA_ROOT=self.directory.name,
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            },
        )
        self.storage_override.enable()
        self.addCleanup(self.storage_override.disable)
        self.user = User.objects.create_superuser(username="test-editor", password="test-only-password")
        self.login(self.client, self.user)
        self.upload_url = reverse("admin:website_homeslide_upload")

    def login(self, client, user):
        client.force_login(user)
        session = client.session
        session["admin_2fa_verified"] = True
        session["admin_2fa_user_id"] = user.pk
        session.save()

    def image(self, name="campus.jpg"):
        data = BytesIO()
        Image.new("RGB", (40, 20), "green").save(data, "JPEG")
        return SimpleUploadedFile(name, data.getvalue(), content_type="image/jpeg")

    def test_dashboard_and_slide_editor_render(self):
        for url in [reverse("admin:index"), reverse("admin:website_homeslide_changelist"), reverse("admin:website_homeslide_add"), self.upload_url]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "admin/css/ccb-content.css")
        self.assertContains(self.client.get(self.upload_url), 'multiple')

    def test_existing_content_editors_show_relevant_fields(self):
        home = PageContent.objects.create(page="home", hero_title="Welcome")
        response = self.client.get(reverse("admin:website_pagecontent_change", args=[home.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="banner_image"')
        self.assertContains(response, "Home slideshow images")
        for route in ["website_academicprogram_add", "website_newsevent_add", "website_sitesettings_add", "website_campusoffice_add", "website_campusservice_add", "website_admissionstep_add"]:
            self.assertEqual(self.client.get(reverse("admin:" + route)).status_code, 200)

    def test_about_editor_filters_sections_and_publishes_to_correct_page(self):
        history = PageContent.objects.create(
            page=PageContent.ABOUT_HISTORY, hero_title="History",
            body_title="Our Beginnings", body_text="Verified college history.", published=False,
        )
        other = PageContent.objects.create(
            page=PageContent.ABOUT_TRUSTEES, hero_title="Trustees", published=False,
        )
        url = reverse("admin:website_pagecontent_changelist")
        response = self.client.get(url, {"page__exact": PageContent.ABOUT_HISTORY})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "About Page Editors")
        sections = list(response.context["cl"].queryset)
        self.assertIn(history, sections)
        self.assertTrue(all(section.page == PageContent.ABOUT_HISTORY for section in sections))
        response = self.client.post(url, {
            "action": "publish_selected", "_selected_action": [history.pk],
        })
        self.assertEqual(response.status_code, 302)
        history.refresh_from_db()
        other.refresh_from_db()
        self.assertTrue(history.published)
        self.assertFalse(other.published)
        self.assertContains(self.client.get("/about/history/"), "Verified college history.")
        response = self.client.get(reverse("admin:website_admissionrequirement_add"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visitors cannot tick items or save progress")
        self.assertContains(response, 'name="document_file"')

    def test_public_about_sections_follow_saved_sort_order(self):
        first = PageContent.objects.create(
            page=PageContent.ABOUT_HISTORY, hero_title="History",
            body_title="First Section", body_text="First verified passage.", sort_order=20,
        )
        second = PageContent.objects.create(
            page=PageContent.ABOUT_HISTORY, hero_title="History",
            body_title="Second Section", body_text="Second verified passage.", sort_order=10,
        )
        response = self.client.get("/about/history/")
        self.assertLess(response.content.index(b"Second verified passage."), response.content.index(b"First verified passage."))
        first.sort_order = 5
        first.save()
        response = self.client.get("/about/history/")
        self.assertLess(response.content.index(b"First verified passage."), response.content.index(b"Second verified passage."))

    def test_multiple_uploads_save_order_visibility_and_files(self):
        HomeSlide.objects.create(title="Existing", image="pages/existing.jpg", sort_order=10)
        response = self.client.post(self.upload_url, {"images": [self.image("first.jpg"), self.image("second.jpg")], "published": "on"})
        self.assertRedirects(response, reverse("admin:website_homeslide_changelist"))
        slides = list(HomeSlide.objects.exclude(title="Existing"))
        self.assertEqual([slide.title for slide in slides], ["first", "second"])
        self.assertEqual([slide.sort_order for slide in slides], [11, 12])
        self.assertTrue(all(slide.published and Path(slide.image.path).exists() for slide in slides))
        home = self.client.get("/")
        self.assertEqual(len(home.context["hero_slides"]), 3)

    def test_draft_upload_and_all_hidden_slides_do_not_leak(self):
        response = self.client.post(self.upload_url, {"images": [self.image("private.jpg")]})
        self.assertEqual(response.status_code, 302)
        slide = HomeSlide.objects.get()
        self.assertFalse(slide.published)
        home = self.client.get("/")
        self.assertNotContains(home, slide.image.name)
        self.assertEqual(len(home.context["hero_slides"]), 0)

    def test_invalid_image_rejects_entire_batch(self):
        invalid = SimpleUploadedFile("fake.jpg", b"not an image", content_type="image/jpeg")
        response = self.client.post(self.upload_url, {"images": [self.image(), invalid], "published": "on"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(HomeSlide.objects.exists())
        self.assertFalse(list(Path(self.directory.name).rglob("*.jpg")))

    def test_upload_limits_and_required_images(self):
        too_large = self.image()
        too_large.size = 11 * 1024 * 1024
        from .admin_forms import HomeSlideUploadForm
        for files in [[too_large], [self.image(f"{i}.jpg") for i in range(21)], []]:
            form = HomeSlideUploadForm(data={"published": True}, files={"images": files})
            self.assertFalse(form.is_valid())

    def test_failed_save_rolls_back_records_and_cleans_uploaded_files(self):
        original_save = HomeSlide.save
        calls = []

        def fail_second(slide, *args, **kwargs):
            calls.append(slide)
            if len(calls) == 2:
                raise RuntimeError("Simulated database failure")
            original_save(slide, *args, **kwargs)

        with patch.object(HomeSlide, "save", fail_second), self.assertLogs("website.admin", level="ERROR"):
            response = self.client.post(self.upload_url, {"images": [self.image("first.jpg"), self.image("second.jpg")]})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(HomeSlide.objects.exists())
        self.assertFalse(list(Path(self.directory.name).rglob("*.jpg")))

    def test_upload_requires_add_permission(self):
        staff = User.objects.create_user(username="viewer", is_staff=True)
        staff.user_permissions.add(Permission.objects.get(codename="view_homeslide"))
        self.login(self.client, staff)
        self.assertEqual(self.client.get(self.upload_url).status_code, 403)
        self.assertEqual(self.client.post(self.upload_url, {"images": [self.image()]}).status_code, 403)
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, "Home slideshow")
        self.assertNotContains(response, "Office directory")

    def test_upload_requires_login_and_pin(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.upload_url).status_code, 302)
        self.client.force_login(self.user)
        response = self.client.get(self.upload_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("setup-pin", response.url)

    def test_upload_keeps_csrf_protection(self):
        client = Client(enforce_csrf_checks=True)
        self.login(client, self.user)
        self.assertEqual(client.post(self.upload_url, {"images": [self.image()]}).status_code, 403)

    def test_bulk_unpublish_updates_public_home(self):
        slide = HomeSlide.objects.create(title="Campus", image="pages/campus.jpg")
        response = self.client.post(reverse("admin:website_homeslide_changelist"), {
            "action": "unpublish_selected", "_selected_action": [slide.pk],
        })
        self.assertEqual(response.status_code, 302)
        slide.refresh_from_db()
        self.assertFalse(slide.published)
        self.assertNotContains(self.client.get("/"), "pages/campus.jpg")

    def test_existing_home_banners_migrate_without_reupload(self):
        from importlib import import_module
        migrate = import_module("website.migrations.0013_homeslide_sitesettings_institutional_mantra").copy_home_banners
        PageContent.objects.create(page="home", hero_title="Campus", banner_image="pages/legacy.jpg", sort_order=2)
        PageContent.objects.create(page="home", hero_title="Draft", banner_image="pages/draft.jpg", sort_order=1, published=False)
        PageContent.objects.create(page="about", hero_title="About", banner_image="pages/about.jpg")
        migrate(apps, connection.schema_editor())
        slides = list(HomeSlide.objects.all())
        self.assertEqual([slide.image.name for slide in slides], ["pages/draft.jpg", "pages/legacy.jpg"])
        self.assertEqual([slide.published for slide in slides], [False, True])

    def test_mantra_setting_updates_header_and_footer(self):
        SiteSettings.objects.create(institutional_mantra="Institutional Latin text")
        response = self.client.get("/")
        self.assertContains(response, "Institutional Latin text", count=2)
