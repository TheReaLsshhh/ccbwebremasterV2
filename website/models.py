import html
import os
import re
import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from PIL import Image, ImageOps

from django.conf import settings
from django.core.files.storage import FileSystemStorage

# Use Cloudinary raw storage for document files when Cloudinary is configured,
# otherwise fall back to local filesystem storage (local dev / no Cloudinary).
try:
    if getattr(settings, "USE_CLOUDINARY", False):
        from .storage import CCBRawCloudinaryStorage
        _raw_storage = CCBRawCloudinaryStorage()
    else:
        raise ImportError("Cloudinary not enabled")
except Exception:
    _raw_storage = FileSystemStorage()


def _delete_old_file_on_change(sender, instance, **kwargs):
    """Delete old file from storage when a file field is changed."""
    if not instance.pk:
        return
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    for field in instance._meta.fields:
        if isinstance(field, models.FileField):
            old_file = getattr(old_instance, field.name)
            new_file = getattr(instance, field.name)
            if old_file and old_file != new_file:
                try:
                    old_file.delete(save=False)
                except Exception:
                    pass


def _generate_unique_filename(instance, filename):
    """Generate a unique filename using UUID to avoid Cloudinary conflicts."""
    ext = os.path.splitext(filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
    return unique_name



MAX_IMAGE_SIZE = (1600, 1600)
JPEG_QUALITY = 82
PNG_COMPRESS_LEVEL = 6


def optimize_uploaded_image(image_field):
    if not image_field:
        return

    try:
        image_path = image_field.path
    except Exception:
        # Non-local storages (e.g., Cloudinary) may not expose local file paths.
        return

    if not image_path or not os.path.exists(image_path):
        return

    try:
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
    except Exception:
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
        from django.core.cache import cache
        cache.delete("site_settings")

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        from django.core.cache import cache
        cache.delete("site_settings")

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
    NEWS = "news"
    DOWNLOADS = "downloads"
    STUDENTS = "students"
    FACULTY = "faculty"
    ABOUT = "about"
    CONTACT = "contact"

    PAGE_CHOICES = [
        (HOME, "Home"),
        (ACADEMICS, "Academics"),
        (ADMISSIONS, "Admissions"),
        (NEWS, "News"),
        (DOWNLOADS, "Downloads"),
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
    brochure_file = models.FileField(
        upload_to=lambda instance, filename: f"academics/{_generate_unique_filename(instance, filename)}",
        blank=True,
        null=True,
        storage=_raw_storage,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx", "xls", "xlsx"])],
        help_text="Allowed formats: PDF, Word (.doc, .docx), Excel (.xls, .xlsx)",
    )
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class AdmissionRequirement(TimeStampedModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    document_file = models.FileField(
        upload_to=lambda instance, filename: f"admissions/{_generate_unique_filename(instance, filename)}",
        blank=True,
        null=True,
        storage=_raw_storage,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx", "xls", "xlsx"])],
        help_text="Allowed formats: PDF, Word (.doc, .docx), Excel (.xls, .xlsx)",
    )
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
    attachment = models.FileField(
        upload_to=lambda instance, filename: f"news/{_generate_unique_filename(instance, filename)}",
        blank=True,
        null=True,
        storage=_raw_storage,
    )
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
        from django.core.cache import cache
        cache.delete("news_page_by_id_9")

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        from django.core.cache import cache
        cache.delete("news_page_by_id_9")


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
    file = models.FileField(
        upload_to=lambda instance, filename: f"downloads/{_generate_unique_filename(instance, filename)}",
        storage=_raw_storage,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx", "xls", "xlsx"])],
        help_text="Allowed formats: PDF, Word (.doc, .docx), Excel (.xls, .xlsx)",
    )
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["category", "title"]

    def __str__(self):
        return self.title


class StudentResource(TimeStampedModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    link_url = models.URLField(blank=True)
    attachment = models.FileField(
        upload_to=lambda instance, filename: f"students/{_generate_unique_filename(instance, filename)}",
        blank=True,
        null=True,
        storage=_raw_storage,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx", "xls", "xlsx"])],
        help_text="Allowed formats: PDF, Word (.doc, .docx), Excel (.xls, .xlsx)",
    )

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
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Contact inquiries"

    def __str__(self):
        return f"{self.name} - {self.subject}"

    def mark_notification_sent(self):
        pass  # retained for compatibility; no-op with reCAPTCHA flow

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


WEAK_ADMIN_PINS = frozenset(
    {
        "000000",
        "111111",
        "222222",
        "333333",
        "444444",
        "555555",
        "666666",
        "777777",
        "888888",
        "999999",
        "123456",
        "654321",
        "012345",
        "543210",
        "121212",
        "112233",
    }
)


class StaffSecurityProfile(models.Model):
    """Six-digit PIN used as a second factor after admin password login."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="security_profile")
    pin_hash = models.CharField(max_length=128, blank=True)
    pin_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Staff security profile"
        verbose_name_plural = "Staff security profiles"

    def __str__(self):
        return f"Security profile for {self.user.username}"

    @property
    def has_pin(self):
        return bool(self.pin_hash)

    @staticmethod
    def validate_pin_format(pin):
        pin = (pin or "").strip()
        if not pin.isdigit() or len(pin) != 6:
            return False, "PIN must be exactly 6 digits."
        if pin in WEAK_ADMIN_PINS:
            return False, "Choose a stronger PIN. Avoid repeated or sequential digits."
        return True, pin

    def set_pin(self, pin):
        is_valid, result = self.validate_pin_format(pin)
        if not is_valid:
            raise ValueError(result)
        self.pin_hash = make_password(result)
        self.pin_updated_at = timezone.now()
        self.save(update_fields=["pin_hash", "pin_updated_at"])

    def check_pin(self, pin):
        if not self.has_pin:
            return False
        is_valid, result = self.validate_pin_format(pin)
        if not is_valid:
            return False
        return check_password(result, self.pin_hash)


# Connect pre_save signals to delete old files when file fields are changed
pre_save.connect(_delete_old_file_on_change, sender=AcademicProgram)
pre_save.connect(_delete_old_file_on_change, sender=AdmissionRequirement)
pre_save.connect(_delete_old_file_on_change, sender=NewsEvent)
pre_save.connect(_delete_old_file_on_change, sender=DownloadItem)
pre_save.connect(_delete_old_file_on_change, sender=StudentResource)
