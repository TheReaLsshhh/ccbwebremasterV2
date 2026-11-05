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

    def test_program_logo_upload_converts_to_webp_and_preserves_alpha(self):
        from .models import AcademicProgram
        data = BytesIO()
        Image.new("RGBA", (180, 120), (30, 90, 50, 128)).save(data, "PNG")
        upload = SimpleUploadedFile("program.png", data.getvalue(), content_type="image/png")
        response = self.client.post(reverse("admin:website_academicprogram_add"), {
            "name": "Tourism", "description": "Program information", "sort_order": 0,
            "published": "on", "logo": upload, "logo_opacity": 18,
        })
        self.assertEqual(response.status_code, 302)
        program = AcademicProgram.objects.get(name="Tourism")
        self.assertTrue(program.logo.name.endswith(".webp"))
        with Image.open(program.logo.path) as image:
            self.assertEqual(image.format, "WEBP")
            self.assertEqual(image.size, (180, 120))
            self.assertEqual(image.getpixel((0, 0))[3], 128)
        for route in ["/", "/academics/", "/academics/partial/"]:
            response = self.client.get(route)
            self.assertContains(response, program.logo.url)
            self.assertContains(response, "program-card-watermark")
            self.assertContains(response, "--program-logo-opacity:18%")

    def test_program_logo_rejects_invalid_file_and_opacity(self):
        from .admin_forms import AcademicProgramAdminForm
        values = {"name": "Program", "description": "Information", "sort_order": 0, "logo_opacity": 14}
        invalid = SimpleUploadedFile("fake.png", b"not an image", content_type="image/png")
        form = AcademicProgramAdminForm(data=values, files={"logo": invalid})
        self.assertFalse(form.is_valid())
        self.assertIn("logo", form.errors)
        form = AcademicProgramAdminForm(data={**values, "logo_opacity": 100})
        self.assertFalse(form.is_valid())
        self.assertIn("logo_opacity", form.errors)

    def test_program_logo_jpeg_conversion_and_existing_file(self):
        from .admin_forms import AcademicProgramAdminForm
        values = {"name": "Program", "description": "Information", "sort_order": 0, "logo_opacity": 14}
        form = AcademicProgramAdminForm(data=values, files={"logo": self.image("logo.jpg")})
        self.assertTrue(form.is_valid(), form.errors)
        program = form.save()
        original = Path(program.logo.path).read_bytes()
        form = AcademicProgramAdminForm(data=values, instance=program)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertEqual(Path(program.logo.path).read_bytes(), original)

    def banner_crop_data(self, **overrides):
        return {
            "page": "news", "hero_title": "Campus news", "hero_text": "Latest updates",
            "sort_order": 0, "published": "on",
            "banner_position_x": 25, "banner_position_y": 70, "banner_zoom": "1.50", "banner_height": 420,
            "banner_mobile_position_x": 80, "banner_mobile_position_y": 30, "banner_mobile_zoom": "2.00", "banner_mobile_height": 300,
            **overrides,
        }

    def test_banner_crop_editor_saves_both_views_without_changing_original(self):
        page = PageContent.objects.create(page="news", hero_title="News", banner_image=self.image())
        original_name = page.banner_image.name
        original_bytes = Path(page.banner_image.path).read_bytes()
        url = reverse("admin:website_pagecontent_change", args=[page.pk])
        response = self.client.get(url)
        self.assertContains(response, "admin/js/banner-image-crop.js")
        self.assertContains(response, "Desktop banner crop")
        self.assertContains(response, "Mobile banner crop")
        self.assertContains(response, 'data-current-image="' + page.banner_image.url + '"')
        response = self.client.post(url, self.banner_crop_data())
        self.assertEqual(response.status_code, 302)
        page.refresh_from_db()
        self.assertEqual(page.banner_position_x, 25)
        self.assertEqual(page.banner_position_y, 70)
        self.assertEqual(float(page.banner_zoom), 1.5)
        self.assertEqual(page.banner_height, 420)
        self.assertEqual(page.banner_mobile_position_x, 80)
        self.assertEqual(page.banner_mobile_height, 300)
        self.assertEqual(page.banner_image.name, original_name)
        self.assertEqual(Path(page.banner_image.path).read_bytes(), original_bytes)
        response = self.client.get("/news/")
        for expected in ("--banner-x:25%", "--banner-y:70%", "--banner-zoom:1.50", "--banner-height:420px", "--banner-mobile-x:80%", "--banner-mobile-y:30%", "--banner-mobile-zoom:2.00", "--banner-mobile-height:300px"):
            self.assertContains(response, expected)
        # Decimal formatting must remain valid CSS even under comma-decimal locales.
        from django.utils.translation import override
        with override("de"):
            self.assertContains(self.client.get("/news/"), "--banner-zoom:1.50")

    def test_banner_crop_limits_reject_invalid_values(self):
        from .admin_forms import PageContentAdminForm
        for name, value in (("banner_position_x", -1), ("banner_position_y", 101), ("banner_zoom", "NaN"), ("banner_zoom", "3.1"), ("banner_height", 10000), ("banner_mobile_height", 1), ("banner_mobile_zoom", "0.5")):
            with self.subTest(name=name, value=value):
                form = PageContentAdminForm(data=self.banner_crop_data(**{name: value}))
                self.assertFalse(form.is_valid())
                self.assertIn(name, form.errors)

    def test_banner_upload_and_clear_keep_crop_editor_usable(self):
        response = self.client.post(reverse("admin:website_pagecontent_add"), {
            **self.banner_crop_data(), "banner_image": self.image("new-banner.jpg"),
        })
        self.assertEqual(response.status_code, 302)
        page = PageContent.objects.get(page="news")
        self.assertTrue(page.banner_image)
        url = reverse("admin:website_pagecontent_change", args=[page.pk])
        response = self.client.post(url, self.banner_crop_data(**{"banner_image-clear": "on"}))
        self.assertEqual(response.status_code, 302)
        page.refresh_from_db()
        self.assertFalse(page.banner_image)
        response = self.client.get("/news/")
        self.assertNotContains(response, 'class="page-hero-media"')

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
        response = self.client.get(reverse("admin:website_admissionsupport_add"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Help prospective students find application guidance")
        self.assertContains(response, 'name="destination"')

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
