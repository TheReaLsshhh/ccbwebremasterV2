import logging

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import escape

from .forms import ContactInquiryForm
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


logger = logging.getLogger(__name__)

NEWS_PAGE_SIZE = 9


def _news_page_by_id(per_page=NEWS_PAGE_SIZE):
    cache_key = f"news_page_by_id_{per_page}"
    data = cache.get(cache_key)
    if data is None:
        news_ids = list(NewsEvent.objects.order_by("-published_at").values_list("pk", flat=True))
        data = {pk: (index // per_page) + 1 for index, pk in enumerate(news_ids)}
        cache.set(cache_key, data, 3600)  # cache for 1 hour
    return data


def send_contact_verification_email(request, inquiry):
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        logger.error("Contact verification email skipped because SMTP credentials are incomplete.")
        return False

    verify_url = request.build_absolute_uri(
        reverse("website:verify_contact_inquiry", kwargs={"token": inquiry.verification_token})
    )
    recipient = settings.CONTACT_INQUIRY_RECIPIENT
    safe_name = escape(inquiry.name)
    safe_recipient = escape(recipient)
    safe_verify_url = escape(verify_url)
    html_message = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #17351d;">
            <p>Hello {safe_name},</p>
            <p>Thank you for contacting City College of Bayawan.</p>
            <p>Please verify your email address first so we can forward your inquiry to <strong>{safe_recipient}</strong>.</p>
            <p style="margin: 24px 0;">
                <a
                    href="{safe_verify_url}"
                    style="display: inline-block; padding: 12px 20px; border-radius: 999px; background: #d97706; color: #ffffff; text-decoration: none; font-weight: 700;">
                    Verify My Inquiry
                </a>
            </p>
            <p>If the button does not work, open this link:</p>
            <p><a href="{safe_verify_url}">{safe_verify_url}</a></p>
            <p>If you did not submit this inquiry, you can safely ignore this message.</p>
        </div>
    """
    text_message = (
        f"Hello {inquiry.name},\n\n"
        "Thank you for contacting City College of Bayawan.\n\n"
        f"Please verify your email address first so we can forward your inquiry to {recipient}.\n\n"
        f"Verify your inquiry here:\n{verify_url}\n\n"
        "If you did not submit this inquiry, you can safely ignore this message."
    )
    email = EmailMultiAlternatives(
        subject="Verify your City College of Bayawan inquiry",
        body=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[inquiry.email],
    )
    email.attach_alternative(html_message, "text/html")
    email.send(fail_silently=False)
    inquiry.mark_verification_sent()
    return True


def send_contact_notification_email(inquiry):
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        logger.error("Contact notification email skipped because SMTP credentials are incomplete.")
        return False

    recipient = settings.CONTACT_INQUIRY_RECIPIENT
    safe_name = escape(inquiry.name)
    safe_email = escape(inquiry.email)
    safe_subject = escape(inquiry.subject)
    safe_message = escape(inquiry.message)
    text_message = (
        "A website visitor verified their email and submitted an inquiry.\n\n"
        f"Name: {inquiry.name}\n"
        f"Email: {inquiry.email}\n"
        f"Subject: {inquiry.subject}\n\n"
        f"Message:\n{inquiry.message}"
    )
    html_message = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #17351d;">
            <p>A website visitor verified their email and submitted an inquiry.</p>
            <p><strong>Name:</strong> {safe_name}<br>
            <strong>Email:</strong> {safe_email}<br>
            <strong>Subject:</strong> {safe_subject}</p>
            <p><strong>Message:</strong></p>
            <div style="padding: 14px 16px; border-radius: 16px; background: #f8f7f3; border: 1px solid rgba(79, 75, 70, 0.12); white-space: pre-line;">{safe_message}</div>
        </div>
    """
    email = EmailMultiAlternatives(
        subject=f"Verified website inquiry: {inquiry.subject}",
        body=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
        reply_to=[inquiry.email],
    )
    email.attach_alternative(html_message, "text/html")
    email.send(fail_silently=False)
    inquiry.mark_notification_sent()
    return True


NAV_ITEMS = [
    ("Home", "website:home"),
    ("Academics", "website:academics"),
    ("Admissions", "website:admissions"),
    ("News", "website:news"),
    ("Downloads", "website:downloads"),
    ("Students", "website:students"),
    ("Faculty", "website:faculty"),
    ("About", "website:about"),
    ("Contact", "website:contact"),
]

SERVICE_DROPDOWN_ITEMS = [
    {
        "label": "College Library",
        "url": "https://sites.google.com/view/ccblearningresourcecenter/home?authuser=0",
    },
    {
        "label": "GIYA Center",
        "url": "https://www.facebook.com/profile.php?id=61577470075989",
    },
    {
        "label": "Students Affair & Students Services",
        "url": "https://www.facebook.com/profile.php?id=61582297621099",
    },
    {
        "label": "Office of the Registrar",
        "url": "https://www.facebook.com/profile.php?id=61583528066100",
    },
]

DEFAULT_PAGE_CONTENT = {
    PageContent.HOME: {
        "hero_title": "Welcome to the City College of Bayawan portal.",
        "hero_text": "Find official announcements, academic information, admission requirements, downloadable forms, and campus updates in one place.",
        "body_title": "Welcome to CCB",
        "body_text": "Stay informed through one clear and accessible public portal.",
    },
    PageContent.ACADEMICS: {
        "hero_title": "Academics",
        "hero_text": "Present degree programs, college offerings, and downloadable brochures in one clear place.",
    },
    PageContent.ADMISSIONS: {
        "hero_title": "Admissions",
        "hero_text": "Guide applicants through requirements, forms, and enrollment steps.",
    },
    PageContent.STUDENTS: {
        "hero_title": "Student Resources",
        "hero_text": "Share handbooks, forms, links, and campus support information for students.",
    },
    PageContent.FACULTY: {
        "hero_title": "Faculty & Staff",
        "hero_text": "Present leadership, instructors, offices, and campus personnel in a searchable way.",
    },
    PageContent.ABOUT: {
        "hero_title": "About City College of Bayawan",
        "hero_text": "Tell the story, mission, and direction of the institution.",
        "body_title": "Institutional Profile",
        "body_text": "Use this space to describe the college mission, vision, history, and strategic goals.",
    },
    PageContent.CONTACT: {
        "hero_title": "Contact Us",
        "hero_text": "Help students, families, and community partners reach the right office quickly.",
        "body_text": "You can change the contact details and map embed from the Site Settings section in admin.",
    },
    PageContent.NEWS: {
        "hero_title": "News & Events",
        "hero_text": "Stay updated with campus announcements, activities, and upcoming milestones.",
    },
    PageContent.DOWNLOADS: {
        "hero_title": "Downloads",
        "hero_text": "Quick access to forms, policies, and academic resources.",
    },
}


def get_site_settings():
    return cache.get_or_set(
        "site_settings", lambda: SiteSettings.objects.order_by("id").first(), 3600
    )


def get_page_content(page_key):
    return PageContent.objects.filter(page=page_key, published=True).first() or DEFAULT_PAGE_CONTENT.get(page_key, {})


def get_page_contents(page_key):
    page_contents = list(PageContent.objects.filter(page=page_key, published=True))
    if page_contents:
        return page_contents
    return [DEFAULT_PAGE_CONTENT.get(page_key, {})]


def get_service_dropdown_items():
    return [
        {
            "label": item["label"],
            "url": item["url"],
            "is_available": True,
        }
        for item in SERVICE_DROPDOWN_ITEMS
    ]


def base_context(active_page):
    return {
        "site_settings": get_site_settings(),
        "nav_items": NAV_ITEMS,
        "active_page": active_page,
        "service_menu_items": get_service_dropdown_items(),
    }


def home(request):
    news_fields = ("title", "summary", "content", "event_date", "location", "cover_image", "attachment", "published_at")
    featured_news = list(NewsEvent.objects.only(*news_fields).filter(is_featured=True)[:3])
    if not featured_news:
        featured_news = list(NewsEvent.objects.only(*news_fields)[:3])

    news_page_by_id = _news_page_by_id()
    for item in featured_news:
        item.news_page = news_page_by_id.get(item.pk, 1)

    context = base_context("website:home")
    context.update(
        {
            "page_content": get_page_content(PageContent.HOME),
            "featured_programs": AcademicProgram.objects.only("name", "award", "description", "brochure_file").filter(is_featured=True)[:3],
            "featured_news": featured_news,
        }
    )
    return render(request, "website/home.html", context)


def academics(request):
    context = base_context("website:academics")
    context.update(
        {
            "page_content": get_page_content(PageContent.ACADEMICS),
            "programs": AcademicProgram.objects.only("name", "award", "description", "brochure_file"),
        }
    )
    return render(request, "website/academics.html", context)


def admissions(request):
    context = base_context("website:admissions")
    context.update(
        {
            "page_content": get_page_content(PageContent.ADMISSIONS),
            "requirements": AdmissionRequirement.objects.only("title", "description", "document_file", "sort_order"),
        }
    )
    return render(request, "website/admissions.html", context)


def news(request):
    news_queryset = NewsEvent.objects.only("title", "summary", "content", "event_date", "location", "cover_image", "attachment", "published_at")
    paginator = Paginator(news_queryset, NEWS_PAGE_SIZE)
    news_page_by_id = _news_page_by_id()

    page_number = request.GET.get("page")
    open_news_id = None
    open_param = request.GET.get("open")
    if open_param:
        try:
            open_pk = int(open_param)
            if open_pk in news_page_by_id:
                open_news_id = open_pk
                page_number = news_page_by_id[open_pk]
        except (TypeError, ValueError):
            pass

    page_obj = paginator.get_page(page_number)

    context = base_context("website:news")
    context.update(
        {
            "page_content": get_page_content(PageContent.NEWS),
            "news_items": page_obj,
            "page_obj": page_obj,
            "open_news_id": open_news_id,
        }
    )
    return render(request, "website/news.html", context)


def downloads(request):
    # Paginate the DownloadItem list (show 12 items per page – adjust as needed for layout)
    download_queryset = DownloadItem.objects.only("category", "title", "description", "file")
    paginator = Paginator(download_queryset, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = base_context("website:downloads")
    context.update(
        {
            "page_content": get_page_content(PageContent.DOWNLOADS),
            # Pass the Page object for pagination controls
            "page_obj": page_obj,
            # Pass the items for the current page
            "downloads": page_obj.object_list,
        }
    )
    return render(request, "website/downloads.html", context)


def students(request):
    context = base_context("website:students")
    context.update(
        {
            "page_content": get_page_content(PageContent.STUDENTS),
            "resources": StudentResource.objects.only("title", "description", "link_url", "attachment"),
        }
    )
    return render(request, "website/students.html", context)


def faculty(request):
    context = base_context("website:faculty")
    context.update(
        {
            "page_content": get_page_content(PageContent.FACULTY),
            "leaders": FacultyStaffEntry.objects.only("name", "role", "department", "bio", "email", "profile_image").filter(is_leadership=True),
            "team_members": FacultyStaffEntry.objects.only("name", "role", "department", "email", "profile_image").filter(is_leadership=False),
        }
    )
    return render(request, "website/faculty.html", context)


def about(request):
    context = base_context("website:about")
    about_sections = get_page_contents(PageContent.ABOUT)
    context.update(
        {
            "page_content": about_sections[0],
            "about_sections": about_sections,
        }
    )
    return render(request, "website/about.html", context)


def contact(request):
    context = base_context("website:contact")
    form = ContactInquiryForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        try:
            inquiry = form.save()
            email_sent = send_contact_verification_email(request, inquiry)
            if email_sent:
                messages.success(
                    request,
                    f"Please check your email and click the verification link. Your inquiry will be forwarded to {settings.CONTACT_INQUIRY_RECIPIENT} after verification.",
                )
            else:
                messages.error(
                    request,
                    "Your inquiry was saved, but the verification email could not be sent yet. Please contact the office directly.",
                )
        except Exception as exc:
            logger.exception("Contact inquiry submission failed")
            if "no such table" in str(exc).lower() or "relation" in str(exc).lower():
                error_message = "The inquiry system is not ready yet. Please try again after the site finishes updating."
            elif settings.EMAIL_HOST_PASSWORD in {"", "PASTE_YOUR_NEW_BREVO_SMTP_KEY_HERE"}:
                error_message = "Your inquiry was saved, but the email service is not configured yet."
            else:
                error_message = "Your inquiry could not be sent right now. Please try again later."
            messages.error(request, error_message)
        return redirect("website:contact")

    if request.method == "POST" and form.is_valid() is False:
        context.update(
            {
                "page_content": get_page_content(PageContent.CONTACT),
                "form": form,
            }
        )
        error_messages = []
        for field_name, errors in form.errors.items():
            if field_name == "__all__":
                error_messages.extend(errors)
                continue

            label = form.fields.get(field_name).label or field_name.replace("_", " ").title()
            error_messages.extend([f"{label}: {error}" for error in errors])

        context["notification_modal"] = {
            "type": "error",
            "message": "Please correct the following before submitting again: " + " ".join(error_messages),
        }
        return render(request, "website/contact.html", context)

    context.update(
        {
            "page_content": get_page_content(PageContent.CONTACT),
            "form": form,
        }
    )

    return render(request, "website/contact.html", context)


def verify_contact_inquiry(request, token):
    inquiry = get_object_or_404(ContactInquiry, verification_token=token)
    inquiry.mark_verified()

    if not inquiry.notification_sent_at:
        try:
            email_sent = send_contact_notification_email(inquiry)
            if email_sent:
                messages.success(
                    request,
                    f"Your email has been verified and your inquiry was sent to {settings.CONTACT_INQUIRY_RECIPIENT}.",
                )
            else:
                messages.error(
                    request,
                    f"Your email was verified, but the inquiry could not be forwarded to {settings.CONTACT_INQUIRY_RECIPIENT}. Please contact the office directly.",
                )
        except Exception as exc:
            logger.exception("Contact notification email failed for inquiry %s", inquiry.pk)
            messages.error(
                request,
                f"Your email was verified, but the inquiry could not be forwarded to {settings.CONTACT_INQUIRY_RECIPIENT}. Please contact the office directly.",
            )
    else:
        messages.success(
            request,
            f"Your inquiry has already been verified and sent to {settings.CONTACT_INQUIRY_RECIPIENT}.",
        )

    return redirect("website:contact")
