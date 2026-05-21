import html
import re
import secrets

from django.db import models
from django.utils import timezone
from PIL import Image, ImageOps


MAX_IMAGE_SIZE = (1600, 1600)
JPEG_QUALITY = 82
PNG_COMPRESS_LEVEL = 6


def optimize_uploaded_image(image_field):
    if not image_field:
        return

    try:
        image_path = image_field.path
        with Image.open(image_path) as image:
            image_format = image.format
            original_size = image.size
            image = ImageOps.exif_transpose(image)
            image.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
            if image_format == "JPEG" and image.size == original_size:
                return
            save_kwargs = {"optimize": True}
            if image_format == "JPEG":
                save_kwargs["quality"] = JPEG_QUALITY
            elif image_format == "PNG":
                save_kwargs["compress_level"] = PNG_COMPRESS_LEVEL
            image.save(image_path, format=image_format, **save_kwargs)
    except (NotImplementedError, OSError, ValueError):
        return


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SiteSettings(TimeStampedModel):
    site_name = models.CharField(max_length=200, default="City College of Bayawan")
    tagline = models.CharField(max_length=255, blank=True, default="Empowering learners. Building futures.")
    hero_notice = models.CharField(max_length=255, blank=True, default="Admissions are open for the upcoming term.")
    primary_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    office_hours = models.CharField(max_length=255, blank=True)
    facebook_url = models.URLField(blank=True)
    map_embed_url = models.TextField(
        blank=True,
        help_text="Use a Google Maps embed URL for the Contact page iframe.",
    )
    footer_text = models.CharField(max_length=255, blank=True, default="City College of Bayawan")

    class Meta:
        verbose_name_plural = "Site settings"

    def __str__(self):
        return self.site_name

    def clean(self):
        super().clean()
        if self.facebook_url:
            self.facebook_url = self._extract_url_value(self.facebook_url)
        if self.map_embed_url:
            self.map_embed_url = self._extract_url_value(self.map_embed_url)

    def save(self, *args, **kwargs):
        if self.facebook_url:
            self.facebook_url = self._extract_url_value(self.facebook_url)
        if self.map_embed_url:
            self.map_embed_url = self._extract_url_value(self.map_embed_url)
        super().save(*args, **kwargs)

    @property
    def normalized_facebook_url(self):
        return self._extract_url_value(self.facebook_url)

    @property
    def normalized_map_embed_url(self):
        return self._extract_url_value(self.map_embed_url)

    @staticmethod
    def _extract_url_value(value):
        normalized = html.unescape((value or "").strip())
        if not normalized:
            return normalized

        iframe_match = re.search(r'src=["\']([^"\']+)["\']', normalized, re.IGNORECASE)
        if iframe_match:
            return iframe_match.group(1).strip()

        return normalized


class PageContent(TimeStampedModel):
    HOME = "home"
    ACADEMICS = "academics"
    ADMISSIONS = "admissions"
    STUDENTS = "students"
    FACULTY = "faculty"
    ABOUT = "about"
    CONTACT = "contact"

    PAGE_CHOICES = [
        (HOME, "Home"),
        (ACADEMICS, "Academics"),
        (ADMISSIONS, "Admissions"),
        (STUDENTS, "Students"),
        (FACULTY, "Faculty"),
        (ABOUT, "About"),
        (CONTACT, "Contact"),
    ]

    page = models.CharField(max_length=30, choices=PAGE_CHOICES)
    hero_title = models.CharField(max_length=200)
    hero_text = models.TextField(blank=True)
    body_title = models.CharField(max_length=200, blank=True)
    body_text = models.TextField(blank=True)
    cta_text = models.CharField(max_length=80, blank=True)
    cta_url = models.CharField(max_length=255, blank=True)
    banner_image = models.ImageField(upload_to="pages/", blank=True, null=True)
    published = models.BooleanField(default=True)

    class Meta:
        ordering = ["page", "created_at", "id"]

    def __str__(self):
        return self.get_page_display()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        optimize_uploaded_image(self.banner_image)


class AcademicProgram(TimeStampedModel):
    name = models.CharField(max_length=200)
    award = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    brochure_file = models.FileField(upload_to="academics/", blank=True, null=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class AdmissionRequirement(TimeStampedModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    document_file = models.FileField(upload_to="admissions/", blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "title"]

    def __str__(self):
        return self.title


class NewsEvent(TimeStampedModel):
    title = models.CharField(max_length=200)
    summary = models.TextField()
    content = models.TextField(blank=True)
    event_date = models.DateField(default=timezone.now)
    location = models.CharField(max_length=200, blank=True)
    cover_image = models.ImageField(upload_to="news/", blank=True, null=True)
    attachment = models.FileField(upload_to="news/", blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    published_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-published_at"]
        verbose_name = "News or event"
        verbose_name_plural = "News and events"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        optimize_uploaded_image(self.cover_image)


class DownloadItem(TimeStampedModel):
    ACADEMIC = "academic"
    FORM = "form"
    POLICY = "policy"
    ANNOUNCEMENT = "announcement"

    CATEGORY_CHOICES = [
        (ACADEMIC, "Academic"),
        (FORM, "Form"),
        (POLICY, "Policy"),
        (ANNOUNCEMENT, "Announcement"),
    ]

    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default=FORM)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="downloads/")
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["category", "title"]

    def __str__(self):
        return self.title


class StudentResource(TimeStampedModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    link_url = models.URLField(blank=True)
    attachment = models.FileField(upload_to="students/", blank=True, null=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class FacultyStaffEntry(TimeStampedModel):
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=200)
    department = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    profile_image = models.ImageField(upload_to="faculty/", blank=True, null=True)
    is_leadership = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "Faculty or staff entry"
        verbose_name_plural = "Faculty and staff"

    def __str__(self):
        return f"{self.name} - {self.role}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        optimize_uploaded_image(self.profile_image)


class ContactInquiry(TimeStampedModel):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    verification_token = models.CharField(max_length=64, unique=True, blank=True)
    verification_sent_at = models.DateTimeField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    notification_sent_at = models.DateTimeField(blank=True, null=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Contact inquiries"

    def __str__(self):
        return f"{self.name} - {self.subject}"

    @property
    def is_verified(self):
        return self.verified_at is not None

    def mark_verification_sent(self):
        self.verification_sent_at = timezone.now()
        self.save(update_fields=["verification_sent_at", "updated_at"])

    def mark_verified(self):
        if not self.verified_at:
            self.verified_at = timezone.now()
            self.save(update_fields=["verified_at", "updated_at"])

    def mark_notification_sent(self):
        self.notification_sent_at = timezone.now()
        self.save(update_fields=["notification_sent_at", "updated_at"])

    def save(self, *args, **kwargs):
        if not self.verification_token:
            self.verification_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)
