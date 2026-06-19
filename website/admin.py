import base64
import binascii
import os
from io import BytesIO

from django import forms
from django.contrib import admin, messages
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image

from .models import (
    AcademicProgram,
    AdmissionRequirement,
    ContactInquiry,
    DownloadItem,
    FacultyStaffEntry,
    FacultyStaffSection,
    FrequentlyAskedQuestion,
    NewsEvent,
    PageContent,
    SiteSettings,
    StudentResource,
)

admin.site.site_header = "CCB Administration"
admin.site.site_title = "CCB Admin"
admin.site.index_title = "Website Content Management"


class SiteSettingsAdminForm(forms.ModelForm):
    facebook_url = forms.CharField(required=False)
    map_embed_url = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Paste either the Google Maps embed src URL or the full iframe embed code.",
    )

    class Meta:
        model = SiteSettings
        fields = "__all__"

    def clean_facebook_url(self):
        return SiteSettings._extract_url_value(self.cleaned_data.get("facebook_url"))

    def clean_map_embed_url(self):
        return SiteSettings._extract_url_value(self.cleaned_data.get("map_embed_url"))


class FacultyStaffEntryAdminForm(forms.ModelForm):
    profile_image_cropped_data = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"class": "faculty-image-crop-data"}),
    )

    class Meta:
        model = FacultyStaffEntry
        fields = "__all__"

    class Media:
        css = {"all": ("admin/css/faculty-image-crop.css",)}
        js = ("admin/js/faculty-image-crop.js",)

    def clean_profile_image_cropped_data(self):
        data_url = (self.cleaned_data.get("profile_image_cropped_data") or "").strip()
        self._cropped_profile_image_bytes = None
        if not data_url:
            return ""

        prefix = "data:image/jpeg;base64,"
        if not data_url.startswith(prefix):
            raise forms.ValidationError("The cropped image data is invalid. Please reselect and crop the image.")

        try:
            image_bytes = base64.b64decode(data_url[len(prefix):], validate=True)
        except (binascii.Error, ValueError):
            raise forms.ValidationError("The cropped image could not be decoded. Please reselect and crop the image.")

        if len(image_bytes) > 6 * 1024 * 1024:
            raise forms.ValidationError("The cropped image is too large. Please choose a smaller image.")

        try:
            with Image.open(BytesIO(image_bytes)) as image:
                image.verify()
        except Exception:
            raise forms.ValidationError("The cropped image is not a valid image file.")

        self._cropped_profile_image_bytes = image_bytes
        return data_url

    def save(self, commit=True):
        instance = super().save(commit=False)
        cropped_image_bytes = getattr(self, "_cropped_profile_image_bytes", None)
        uploaded_image = self.files.get("profile_image")

        if cropped_image_bytes and uploaded_image:
            original_name = os.path.basename(uploaded_image.name or "profile-image.jpg")
            base_name, _extension = os.path.splitext(original_name)
            cropped_name = f"{base_name or 'profile-image'}-cropped.jpg"
            instance.profile_image.save(cropped_name, ContentFile(cropped_image_bytes), save=False)

        if commit:
            instance.save()
            self.save_m2m()

        return instance


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    form = SiteSettingsAdminForm
    list_display = ("site_name", "primary_email", "phone", "updated_at")

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()


@admin.register(PageContent)
class PageContentAdmin(admin.ModelAdmin):
    list_display = ("page", "hero_title", "published", "updated_at")
    list_filter = ("published", "page")
    search_fields = ("hero_title", "body_title", "body_text")
    list_editable = ("published",)
    fieldsets = (
        (None, {"fields": ("page", "published")}),
        (
            "Hero section",
            {
                "fields": ("hero_title", "hero_text", "banner_image"),
                "description": "Shown at the top of the public page. Upload a banner image for a background photo.",
            },
        ),
        (
            "Body section (optional)",
            {"fields": ("body_title", "body_text", "cta_text", "cta_url")},
        ),
    )


@admin.register(FrequentlyAskedQuestion)
class FrequentlyAskedQuestionAdmin(admin.ModelAdmin):
    list_display = ("question", "layout", "sort_order", "published", "updated_at")
    list_filter = ("layout", "published")
    search_fields = ("question", "answer")
    list_editable = ("sort_order", "published")
    ordering = ("layout", "sort_order", "question")
    fieldsets = (
        (None, {"fields": ("layout", "published", "sort_order")}),
        ("FAQ content", {"fields": ("question", "answer")}),
    )


@admin.register(AcademicProgram)
class AcademicProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "award", "is_featured", "updated_at")
    list_filter = ("is_featured",)
    search_fields = ("name", "award", "description")
    list_editable = ("is_featured",)


@admin.register(AdmissionRequirement)
class AdmissionRequirementAdmin(admin.ModelAdmin):
    list_display = ("title", "sort_order", "updated_at")
    list_editable = ("sort_order",)
    ordering = ("sort_order", "title")


@admin.register(NewsEvent)
class NewsEventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_date", "location", "is_featured", "published_at")
    list_filter = ("is_featured", "event_date")
    search_fields = ("title", "summary", "content", "location")
    list_editable = ("is_featured",)
    date_hierarchy = "event_date"
    fieldsets = (
        (None, {"fields": ("title", "summary", "content", "is_featured", "published_at")}),
        ("Schedule & place", {"fields": ("event_date", "location")}),
        ("Media", {"fields": ("cover_image", "attachment")}),
    )


@admin.register(DownloadItem)
class DownloadItemAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_featured", "updated_at")
    list_filter = ("category", "is_featured")
    search_fields = ("title", "description")
    list_editable = ("is_featured",)


@admin.register(StudentResource)
class StudentResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "updated_at")
    search_fields = ("title", "description")


@admin.register(FacultyStaffSection)
class FacultyStaffSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "eyebrow_label", "layout", "sort_order", "published", "updated_at")
    list_filter = ("layout", "published")
    search_fields = ("title", "eyebrow_label")
    list_editable = ("sort_order", "published")
    ordering = ("sort_order", "title")


@admin.register(FacultyStaffEntry)
class FacultyStaffEntryAdmin(admin.ModelAdmin):
    form = FacultyStaffEntryAdminForm
    list_display = ("name", "section", "role", "department", "updated_at")
    list_filter = ("section", "department")
    search_fields = ("name", "role", "department", "bio")
    list_editable = ("section",)
    autocomplete_fields = ("section",)


@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "subject",
        "is_resolved",
        "created_at",
    )
    list_filter = ("is_resolved", "created_at")
    search_fields = ("name", "email", "subject", "message")
    list_editable = ("is_resolved",)
    actions = ("mark_resolved", "mark_unresolved")
    readonly_fields = (
        "name",
        "email",
        "subject",
        "message",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Inquiry", {"fields": ("name", "email", "subject", "message", "is_resolved")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.action(description="Mark selected inquiries as resolved")
    def mark_resolved(self, request, queryset):
        updated = queryset.update(is_resolved=True, updated_at=timezone.now())
        self.message_user(request, f"{updated} inquiry(s) marked as resolved.", messages.SUCCESS)

    @admin.action(description="Mark selected inquiries as unresolved")
    def mark_unresolved(self, request, queryset):
        updated = queryset.update(is_resolved=False, updated_at=timezone.now())
        self.message_user(request, f"{updated} inquiry(s) marked as unresolved.", messages.SUCCESS)
