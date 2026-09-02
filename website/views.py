from django.contrib import messages
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils.html import format_html

from .forms import ContactInquiryForm
from .models import (
    AcademicProgram,
    AdmissionRequirement,
    DownloadItem,
    FacultyStaffSection,
    NewsEvent,
    PageContent,
    StudentResource,
)
from .utils import base_context, get_page_content, send_contact_notification_email

# Rate limiting constants
CONTACT_RATE_LIMIT_HOUR = 1
CONTACT_RATE_WINDOW_HOUR = 3600
CONTACT_RATE_LIMIT_DAY = 5
CONTACT_RATE_WINDOW_DAY = 86400

def service_worker(request):
    # This view is required by your urls.py but its content is not available.
    # Returning an empty response to allow the server to start.
    return HttpResponse("")

def cloudinary_download(request):
    # This view is required by your urls.py but its content is not available.
    # Returning an empty response to allow the server to start.
    return HttpResponse("")

def home(request):
    context = base_context("website:home")
    context.update(
        {
            "page_content": get_page_content(PageContent.HOME),
            "news": NewsEvent.objects.filter(is_featured=True).order_by(
                "-published_at"
            )[:3],
        }
    )
    return render(request, "website/index.html", context)

def about(request):
    context = base_context("website:about")
    context.update({"page_content": get_page_content(PageContent.ABOUT)})
    return render(request, "website/about.html", context)

def academics(request):
    context = base_context("website:academics")
    context.update(
        {
            "page_content": get_page_content(PageContent.ACADEMICS),
            "programs": AcademicProgram.objects.all(),
        }
    )
    return render(request, "website/academics.html", context)

def admissions(request):
    context = base_context("website:admissions")
    context.update(
        {
            "page_content": get_page_content(PageContent.ADMISSIONS),
            "requirements": AdmissionRequirement.objects.order_by("sort_order"),
        }
    )
    return render(request, "website/admissions.html", context)

def news(request):
    context = base_context("website:news")
    context.update(
        {
            "page_content": get_page_content(PageContent.NEWS),
            "news_items": NewsEvent.objects.order_by("-published_at"),
        }
    )
    return render(request, "website/news.html", context)

def downloads(request):
    context = base_context("website:downloads")
    context.update(
        {
            "page_content": get_page_content(PageContent.DOWNLOADS),
            "downloads": DownloadItem.objects.order_by("category", "title"),
        }
    )
    return render(request, "website/downloads.html", context)

def students(request):
    context = base_context("website:students")
    context.update(
        {
            "page_content": get_page_content(PageContent.STUDENTS),
            "resources": StudentResource.objects.order_by("title"),
        }
    )
    return render(request, "website/students.html", context)

def faculty(request):
    context = base_context("website:faculty")
    context.update(
        {
            "page_content": get_page_content(PageContent.FACULTY),
            "sections": FacultyStaffSection.objects.filter(
                published=True
            ).prefetch_related("people"),
        }
    )
    return render(request, "website/faculty.html", context)

def contact(request):
    ip_address = request.META.get("REMOTE_ADDR")
    if ip_address:
        hour_key = f"contact_hour_{ip_address}"
        day_key = f"contact_day_{ip_address}"
        hour_count = cache.get(hour_key, 0)
        day_count = cache.get(day_key, 0)

        if (
            hour_count >= CONTACT_RATE_LIMIT_HOUR
            or day_count >= CONTACT_RATE_LIMIT_DAY
        ):
            messages.error(
                request,
                "You have submitted this form too frequently. Please try again later.",
            )
            return redirect("website:contact")

    if request.method == "POST":
        form = ContactInquiryForm(request.POST)
        if form.is_valid():
            inquiry = form.save()
            send_contact_notification_email(inquiry)
            messages.success(
                request,
                format_html(
                    "Thank you for your inquiry! We will get back to you at <strong>{}</strong> soon.",
                    form.cleaned_data["email"],
                ),
            )
            if ip_address:
                cache.set(hour_key, hour_count + 1, CONTACT_RATE_WINDOW_HOUR)
                cache.set(day_key, day_count + 1, CONTACT_RATE_WINDOW_DAY)
            return redirect("website:contact")
        else:
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)
    else:
        form = ContactInquiryForm()

    context = base_context("website:contact")
    context.update(
        {"page_content": get_page_content(PageContent.CONTACT), "form": form}
    )
    return render(request, "website/contact.html", context)

# Partial views - these are required by your urls.py
# They are stubbed to call the main view to prevent crashes.
def academics_partial(request):
    return academics(request)

def admissions_partial(request):
    return admissions(request)

def downloads_partial(request):
    return downloads(request)

def students_partial(request):
    return students(request)
