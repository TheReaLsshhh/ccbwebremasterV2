import base64
import binascii
import os
import logging
from io import BytesIO

from django import forms
from django.contrib import admin, messages
from django.core.files.base import ContentFile
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Max
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils import timezone
from PIL import Image

from .admin_forms import HomeSlideUploadForm

from .models import (
    AdmissionStep,
    CampusService,
    CampusOffice,
    AcademicProgram,
    HomeSlide,
    LegalPage,
    LegalSection,
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
logger = logging.getLogger(__name__)


class LegalSectionInline(admin.StackedInline):
    model = LegalSection
    extra = 0
    fields = ("title", "body", "sort_order")


@admin.register(LegalPage)
class LegalPageAdmin(admin.ModelAdmin):
    list_display = ("title", "approved_for_publication", "updated_at")
    list_filter = ("approved_for_publication",)
    search_fields = ("title", "introduction", "sections__body")
    readonly_fields = ("updated_at",)
    fields = ("slug", "title", "introduction", "approved_for_publication", "updated_at")
    inlines = (LegalSectionInline,)

    def view_on_site(self, obj):
        return reverse(f"website:{obj.slug}")


class PublishedContentAdmin(admin.ModelAdmin):
    actions = ("publish_selected", "unpublish_selected")

    @admin.action(description="Publish selected items", permissions=["change"])
    def publish_selected(self, request, queryset):
        count = queryset.update(published=True, updated_at=timezone.now())
        self.message_user(request, f"Published {count} items. Scheduled news still waits until its publication date.", messages.SUCCESS)

    @admin.action(description="Unpublish selected items", permissions=["change"])
    def unpublish_selected(self, request, queryset):
        count = queryset.update(published=False, updated_at=timezone.now())
        self.message_user(request, f"Unpublished {count} items.", messages.SUCCESS)


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
    fieldsets = (
        ("College identity", {"fields": ("site_name", "institutional_mantra", "tagline", "footer_text")}),
        ("Contact information", {"fields": ("primary_email", "phone", "address", "office_hours")}),
        ("Social and campus map", {"fields": ("facebook_url", "map_embed_url")}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()


@admin.register(PageContent)
class PageContentAdmin(PublishedContentAdmin):
    change_list_template = "admin/website/pagecontent/change_list.html"
    list_display = ("page", "body_title", "hero_title", "published", "sort_order", "updated_at")
    list_filter = ("published", "page")
    search_fields = ("hero_title", "body_title", "body_text")
    list_editable = ("published", "sort_order")
    def changelist_view(self, request, extra_context=None):
        from .views import ABOUT_MENU_ITEMS
        return super().changelist_view(request, {
            **(extra_context or {}), "about_editors": ABOUT_MENU_ITEMS,
        })

    fieldsets = (
        (None, {"fields": ("page", "published", "sort_order")}),
        (
            "Hero section",
            {
                "fields": ("hero_title", "hero_text", "banner_image"),
                "description": "Shown at the top of the public page. Upload a banner image for a background photo.",
            },
        ),
        ("About sections / Contact introduction", {
            "fields": ("body_title", "body_text"),
            "description": "Body content is used on About and Contact. Programs, news, resources, and other page content have their own editors.",
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if obj and obj.page == PageContent.HOME:
            return (
                ("Home page introduction", {
                    "fields": ("page", "published", "sort_order", "hero_title", "hero_text"),
                    "description": "Manage the welcome heading here. Use Home slideshow images to upload and order the background images independently.",
                }),
            )
        if obj:
            sections = [
                self.fieldsets[0],
                ("Page banner and introduction", {"fields": ("hero_title", "hero_text", "banner_image")}),
            ]
            if obj.page in PageContent.ABOUT_PAGE_KEYS:
                sections.append(("About section", {
                    "fields": ("body_title", "body_text"),
                    "description": "Each published record becomes a section on the selected About page, in sort order. Use separate records for Vision, Mission, Goals, and Core Values. Draft records remain private. The former About overview is retired; edit one of the five About pages instead.",
                }))
            elif obj.page == PageContent.CONTACT:
                sections.append(("Contact introduction", {"fields": ("body_text",)}))
            return tuple(sections)
        return super().get_fieldsets(request, obj)

    def view_on_site(self, obj):
        from .views import ABOUT_MENU_ITEMS
        for item in ABOUT_MENU_ITEMS:
            if obj.page == item["page"]:
                return reverse("website:about_section", kwargs={"section": item["slug"]})
        return reverse(f"website:{obj.page}")


@admin.register(HomeSlide)
class HomeSlideAdmin(PublishedContentAdmin):
    change_list_template = "admin/website/homeslide/change_list.html"
    list_display = ("thumbnail", "title", "sort_order", "published", "updated_at")
    list_display_links = ("thumbnail", "title")
    list_editable = ("sort_order", "published")
    list_filter = ("published",)
    search_fields = ("title",)
    readonly_fields = ("thumbnail",)
    fields = ("title", "image", "thumbnail", "sort_order", "published")

    @admin.display(description="Preview")
    def thumbnail(self, obj):
        if not obj.image:
            return "No image"
        return format_html('<img src="{}" alt="" class="admin-slide-thumbnail" width="144" height="72">', obj.image.url)

    def view_on_site(self, obj):
        return reverse("website:home")

    def get_urls(self):
        return [path("upload/", self.admin_site.admin_view(self.upload_images), name="website_homeslide_upload")] + super().get_urls()

    def upload_images(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        form = HomeSlideUploadForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            created = []
            try:
                with transaction.atomic():
                    order = HomeSlide.objects.aggregate(last=Max("sort_order"))["last"]
                    order = 0 if order is None else order + 1
                    for index, image in enumerate(form.cleaned_data["images"]):
                        slide = HomeSlide(
                            title=os.path.splitext(os.path.basename(image.name))[0][:200],
                            image=image, sort_order=order + index,
                            published=form.cleaned_data["published"],
                        )
                        created.append(slide)
                        slide.save()
                        self.log_addition(request, slide, "Added using multiple-image upload.")
            except Exception:
                logger.exception("Multiple Home slideshow image upload failed")
                # Storage uploads are not rolled back by the database transaction.
                for slide in created:
                    if slide.image and slide.image._committed:
                        try:
                            slide.image.delete(save=False)
                        except Exception:
                            pass
                form.add_error(None, "The images could not be saved. Please try again. No slideshow records were added.")
            else:
                self.message_user(request, f"Added {len(created)} slideshow images. Adjust their order and visibility below.", messages.SUCCESS)
                return redirect("admin:website_homeslide_changelist")
        context = {
            **self.admin_site.each_context(request), "opts": self.model._meta,
            "title": "Upload Home slideshow images", "form": form,
            "media": form.media,
        }
        return TemplateResponse(request, "admin/website/homeslide/upload.html", context)


@admin.register(FrequentlyAskedQuestion)
class FrequentlyAskedQuestionAdmin(PublishedContentAdmin):
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
class AcademicProgramAdmin(PublishedContentAdmin):
    list_display = ("name", "award", "is_featured", "updated_at", "published")
    list_editable = ("is_featured", "published")
    search_fields = ("name", "award", "description", "department")
    list_filter = ("department", "is_featured", "published")
    fieldsets = (
        ("Program identity", {"fields": ("name", "award", "department", "duration")}),
        ("Program detail page", {"fields": ("description", "career_paths", "brochure_file")}),
        ("Publishing", {"fields": ("published", "is_featured"), "description": "Featured programs are prioritized on Home. Unpublished programs are hidden from listings, details, and search."}),
    )

    def view_on_site(self, obj):
        return reverse("website:program_detail", args=[obj.pk])


@admin.register(AdmissionRequirement)
class AdmissionRequirementAdmin(PublishedContentAdmin):
    search_fields = ("title", "description")
    fieldsets = (
        ("Requirements checklist", {
            "fields": ("title", "description", "document_file"),
            "description": "These are read-only preparation instructions on Admissions. Visitors cannot tick items or save progress. Attach an official form when needed.",
        }),
        ("Publication and order", {"fields": ("published", "sort_order")}),
    )
    list_filter = ("published",)
    list_display = ("title", "sort_order", "updated_at", "published")
    list_editable = ("sort_order", "published")
    ordering = ("sort_order", "title")

    def view_on_site(self, obj):
        return reverse("website:admissions")


@admin.register(NewsEvent)
class NewsEventAdmin(PublishedContentAdmin):
    list_display = ("title", "event_date", "location", "is_featured", "published_at", "published")
    list_filter = ("is_featured", "event_date", "published")
    search_fields = ("title", "summary", "content", "location")
    list_editable = ("is_featured", "published")
    date_hierarchy = "event_date"
    fieldsets = (
        ("Story", {"fields": ("title", "summary", "content")}),
        ("Publishing", {"fields": ("published", "published_at", "is_featured"), "description": "A story appears publicly only when Published is checked and Published at has arrived. Featured stories are prioritized on Home."}),
        ("Schedule & place", {"fields": ("event_date", "location")}),
        ("Media", {"fields": ("cover_image", "attachment")}),
    )

    def view_on_site(self, obj):
        return reverse("website:news_detail", args=[obj.pk])


@admin.register(DownloadItem)
class DownloadItemAdmin(PublishedContentAdmin):
    list_display = ("title", "category", "is_featured", "updated_at", "published")
    list_filter = ("category", "is_featured", "published")
    search_fields = ("title", "description")
    list_editable = ("is_featured", "published")


@admin.register(StudentResource)
class StudentResourceAdmin(PublishedContentAdmin):
    list_filter = ("published",)
    list_editable = ("published",)
    list_display = ("title", "updated_at", "published")
    search_fields = ("title", "description")


@admin.register(FacultyStaffSection)
class FacultyStaffSectionAdmin(PublishedContentAdmin):
    list_display = ("title", "eyebrow_label", "layout", "sort_order", "published", "updated_at")
    list_filter = ("layout", "published")
    search_fields = ("title", "eyebrow_label")
    list_editable = ("sort_order", "published")
    ordering = ("sort_order", "title")


@admin.register(FacultyStaffEntry)
class FacultyStaffEntryAdmin(PublishedContentAdmin):
    form = FacultyStaffEntryAdminForm
    list_display = ("name", "section", "role", "department", "updated_at", "published")
    list_filter = ("section", "department", "published")
    search_fields = ("name", "role", "department", "bio")
    list_editable = ("section", "published")
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



@admin.register(AdmissionStep)
class AdmissionStepAdmin(PublishedContentAdmin):
    list_display = ("title", "sort_order", "published", "updated_at")
    list_editable = ("sort_order", "published")
    search_fields = ("title", "description")
    list_filter = ("published",)
    fieldsets = (
        ("Admissions instructions", {"fields": ("title", "description", "sort_order", "published")}),
        ("Optional official link", {"fields": ("link_label", "link_url")}),
    )


@admin.register(CampusService)
class CampusServiceAdmin(PublishedContentAdmin):
    list_display = ("title", "sort_order", "published", "updated_at")
    list_editable = ("sort_order", "published")
    search_fields = ("title", "description")
    list_filter = ("published",)
    fieldsets = (("Services menu and Student resources", {"fields": ("title", "description", "url", "sort_order", "published"), "description": "Published services appear in both the navigation dropdown and the Students page."}),)


@admin.register(CampusOffice)
class CampusOfficeAdmin(PublishedContentAdmin):
    list_display = ("name", "email", "phone", "published")
    list_editable = ("published",)
    search_fields = ("name", "description", "location")
    list_filter = ("published",)
    fieldsets = (
        ("Contact page directory", {"fields": ("name", "description", "sort_order", "published")}),
        ("Office contact details", {"fields": ("email", "phone", "location", "office_hours")}),
    )
