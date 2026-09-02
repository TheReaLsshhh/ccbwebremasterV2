from django.contrib import messages
from django.core.cache import cache
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
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
    SiteSettings,
)
from .context_processors import search_metadata

# Rate limiting constants
CONTACT_RATE_LIMIT_HOUR = 1
CONTACT_RATE_WINDOW_HOUR = 3600
CONTACT_RATE_LIMIT_DAY = 5
CONTACT_RATE_WINDOW_DAY = 86400

def _send_contact_notification_email(inquiry):
    """Send an email notification to the admin about a new contact inquiry."""
    try:
        settings = SiteSettings.objects.first()
        if not settings or not settings.primary_email:
            return

        subject = f"New Contact Inquiry: {inquiry.subject}"
        context = {"inquiry": inquiry, "settings": settings}
        text_content = render_to_string("website/email/contact_notification.txt", context)
        html_content = render_to_string("website/email/contact_notification.html", context)

        send_mail(
            subject,
            text_content,
            settings.primary_email,
            [settings.primary_email],
            html_message=html_content,
            fail_silently=False,
        )
    except Exception:
        # Silently fail to avoid crashing the user-facing view
        pass

def service_worker(request):
    return HttpResponse("")

def cloudinary_download(request):
    return HttpResponse("")

def home(request):
    context = search_metadata(request)
    context.update(
        {
            "page_content": PageContent.objects.filter(page=PageContent.HOME).first(),
            "news": NewsEvent.objects.filter(is_featured=True).order_by(
                "-published_at"
            )[:3],
        }
    )
    return render(request, "website/index.html", context)

def about(request):
    context = search_metadata(request)
    context.update(
        {"page_content": PageContent.objects.filter(page=PageContent.ABOUT).first()}
    )
    return render(request, "website/about.html", context)

def academics(request):
    context = search_metadata(request)
    context.update(
        {
            "page_content": PageContent.objects.filter(
                page=PageContent.ACADEMICS
            ).first(),
            "programs": AcademicProgram.objects.all(),
        }
    )
    return render(request, "website/academics.html", context)

def admissions(request):
    context = search_metadata(request)
    context.update(
        {
            "page_content": PageContent.objects.filter(
                page=PageContent.ADMISSIONS
            ).first(),
            "requirements": AdmissionRequirement.objects.order_by("sort_order"),
        }
    )
    return render(request, "website/admissions.html", context)

def news(request):
    context = search_metadata(request)
    context.update(
        {
            "page_content": PageContent.objects.filter(page=PageContent.NEWS).first(),
            "news_items": NewsEvent.objects.order_by("-published_at"),
        }
    )
    return render(request, "website/news.html", context)

def downloads(request):
    context = search_metadata(request)
    context.update(
        {
            "page_content": PageContent.objects.filter(
                page=PageContent.DOWNLOADS
            ).first(),
            "downloads": DownloadItem.objects.order_by("category", "title"),
        }
    )
    return render(request, "website/downloads.html", context)

def students(request):
    context = search_metadata(request)
    context.update(
        {
            "page_content": PageContent.objects.filter(
                page=PageContent.STUDENTS
            ).first(),
            "resources": StudentResource.objects.order_by("title"),
        }
    )
    return render(request, "website/students.html", context)

def faculty(request):
    context = search_metadata(request)
    context.update(
        {
            "page_content": PageContent.objects.filter(page=PageContent.FACULTY).first(),
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
            _send_contact_notification_email(inquiry)
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

    context = search_metadata(request)
    context.update(
        {
            "page_content": PageContent.objects.filter(page=PageContent.CONTACT).first(),
            "form": form,
        }
    )
    return render(request, "website/contact.html", context)

# Partial views
def academics_partial(request):
    return academics(request)

def admissions_partial(request):
    return admissions(request)

def downloads_partial(request):
    return downloads(request)

def students_partial(request):
    return students(request)