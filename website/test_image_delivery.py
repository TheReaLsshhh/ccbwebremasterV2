import hashlib
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.template import Context, Template
from django.templatetags.static import static
from django.test import SimpleTestCase, override_settings
from PIL import Image

from .models import HomeSlide
from .templatetags.news_extras import optimized_image_url, plain_text, webp_image_url, webp_image_srcset


class ImageDeliveryTests(SimpleTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        configuration = override_settings(
            MEDIA_ROOT=self.directory.name,
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            },
        )
        configuration.enable()
        self.addCleanup(configuration.disable)

    def local_image(self):
        image = BytesIO()
        Image.new("RGB", (1000, 500), "green").save(image, "JPEG")
        slide = HomeSlide(title="Campus")
        slide.image.save("campus.jpg", ContentFile(image.getvalue()), save=False)
        return slide.image

    def test_local_webp_derivative_preserves_original(self):
        field = self.local_image()
        original = hashlib.sha256(Path(field.path).read_bytes()).hexdigest()
        url = webp_image_url(field, 480)
        destination = Path(self.directory.name) / "image-variants" / url.rsplit("/", 1)[-1]
        with Image.open(destination) as image:
            self.assertEqual(image.format, "WEBP")
            self.assertEqual(image.size, (480, 240))
        self.assertEqual(original, hashlib.sha256(Path(field.path).read_bytes()).hexdigest())
        modified = destination.stat().st_mtime_ns
        self.assertEqual(webp_image_url(field, 480), url)
        self.assertEqual(destination.stat().st_mtime_ns, modified)

    def test_cloudinary_uses_webp_with_a_negotiated_fallback(self):
        field = SimpleNamespace(url="https://res.cloudinary.com/demo/image/upload/v1/campus.jpg")
        self.assertIn("f_webp,q_90,c_limit,w_960", webp_image_url(field, 960))
        self.assertIn("f_auto,q_auto:good", optimized_image_url(field, 960))
        self.assertIn("480w", webp_image_srcset(field, "480,960,1600"))

    def test_static_development_photos_have_no_generated_fallback(self):
        self.assertEqual(webp_image_url(static("images/ccb.jpg"), 960), "")

    def test_missing_local_image_uses_original_fallback(self):
        slide = HomeSlide(image="pages/missing.jpg")
        self.assertEqual(webp_image_url(slide.image, 480), "")
        body = Template('{% load news_extras %}{% responsive_image photo %}').render(Context({"photo": slide.image}))
        self.assertNotIn('<source', body)
        self.assertIn('pages/missing.jpg', body)

    def test_picture_has_fallback_srcset_and_escaped_alt_text(self):
        field = SimpleNamespace(url="https://res.cloudinary.com/demo/image/upload/v1/campus.jpg")
        body = Template('{% load news_extras %}{% responsive_image photo alt=description loading="eager" css_class="hero-slide" %}').render(Context({"photo": field, "description": '<script>unsafe</script>'}))
        self.assertIn('type="image/webp"', body)
        self.assertIn('480w', body)
        self.assertIn('<img src=', body)
        self.assertIn('loading="eager"', body)
        self.assertNotIn('<script>unsafe', body)
        self.assertIn('&lt;script&gt;', body)

    def test_stylized_letters_use_site_fonts_without_changing_text(self):
        self.assertEqual(plain_text("\U0001d400\U0001d401\U0001d402 CCB"), "ABC CCB")

    def test_bad_width_is_ignored_and_documents_are_not_transformed(self):
        field = SimpleNamespace(url="https://res.cloudinary.com/demo/raw/upload/form.pdf")
        self.assertEqual(webp_image_url(field, 480), "")
        self.assertEqual(webp_image_url(field, "not-a-width"), "")
