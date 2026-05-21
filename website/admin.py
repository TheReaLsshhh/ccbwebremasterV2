from django import forms
from django.contrib import admin

from .models import (
    AcademicProgram,
    AdmissionRequirement,
    ContactInquiry,
    DownloadItem,
    FacultyStaffEntry,
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


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    form = SiteSettingsAdminForm
    list_display = ("site_name", "primary_email", "phone", "updated_at")


@admin.register(PageContent)
class PageContentAdmin(admin.ModelAdmin):
    list_display = ("page", "hero_title", "published", "updated_at")
    list_filter = ("published", "page")
    search_fields = ("hero_title", "body_title", "body_text")


@admin.register(AcademicProgram)
class AcademicProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "award", "is_featured", "updated_at")
    list_filter = ("is_featured",)
    search_fields = ("name", "award", "description")


@admin.register(AdmissionRequirement)
class AdmissionRequirementAdmin(admin.ModelAdmin):
    list_display = ("title", "sort_order", "updated_at")
    list_editable = ("sort_order",)


@admin.register(NewsEvent)
class NewsEventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_date", "location", "is_featured", "published_at")
    list_filter = ("is_featured", "event_date")
    search_fields = ("title", "summary", "content", "location")


@admin.register(DownloadItem)
class DownloadItemAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_featured", "updated_at")
    list_filter = ("category", "is_featured")
    search_fields = ("title", "description")


@admin.register(StudentResource)
class StudentResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "updated_at")
    search_fields = ("title", "description")


@admin.register(FacultyStaffEntry)
class FacultyStaffEntryAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "department", "is_leadership")
    list_filter = ("is_leadership", "department")
    search_fields = ("name", "role", "department", "bio")


@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "verified_at", "notification_sent_at", "is_resolved", "created_at")
    list_filter = ("is_resolved", "verified_at", "notification_sent_at", "created_at")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = (
        "name",
        "email",
        "subject",
        "message",
        "verification_token",
        "verification_sent_at",
        "verified_at",
        "notification_sent_at",
        "created_at",
        "updated_at",
    )
