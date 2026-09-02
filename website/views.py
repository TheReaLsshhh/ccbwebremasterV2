from django.contrib import messages
from django.core.cache import cache
from django.shortcuts import render, redirect
from django.utils.html import format_html

from .models import PageContent, News, Event, Gallery, CcbWebsite
from .forms import ContactInquiryForm
from .utils import base_context, send_contact_notification_email, get_page_content

# Rate limiting constants
CONTACT_RATE_LIMIT_HOUR = 1  # max 1 submission per IP per hour
CONTACT_RATE_WINDOW_HOUR = 3600  # 1 hour in seconds
CONTACT_RATE_LIMIT_DAY = 5  # max 5 submissions per IP per day
CONTACT_RATE_WINDOW_DAY = 86400  # 24 hours in seconds

def index(request):
    context = base_context("website:index")
    context.update(
        {
            "page_content": get_page_content(PageContent.HOME),
            "news": News.objects.filter(is_published=True).order_by("-published_at")[:3],
            "events": Event.objects.filter(is_published=True).order_by("-event_date")[
                :3
            ],
        }
    )
    return render(request, "website/index.html", context)

def about(request):
    context = base_context("website:about")
    context.update({"page_content": get_page_content(PageContent.ABOUT)})
    return render(request, "website/about.html", context)

def news(request):
    context = base_context("website:news")
    context.update(
        {
            "page_content": get_page_content(PageContent.NEWS),
            "news": News.objects.filter(is_published=True).order_by("-published_at"),
        }
    )
    return render(request, "website/news.html", context)

def news_detail(request, slug):
    news = News.objects.get(slug=slug)
    context = base_context("website:news")
    context.update({"news": news})
    return render(request, "website/news_detail.html", context)

def events(request):
    context = base_context("website:events")
    context.update(
        {
            "page_content": get_page_content(PageContent.EVENTS),
            "events": Event.objects.filter(is_published=True).order_by("-event_date"),
        }
    )
    return render(request, "website/events.html", context)

def event_detail(request, slug):
    event = Event.objects.get(slug=slug)
    context = base_context("website:events")
    context.update({"event": event})
    return render(request, "website/event_detail.html", context)

def gallery(request):
    context = base_context("website:gallery")
    context.update(
        {
            "page_content": get_page_content(PageContent.GALLERY),
            "gallery": Gallery.objects.filter(is_published=True).order_by(
                "-created_at"
            ),
        }
    )
    return render(request, "website/gallery.html", context)

def contact(request):
    # Rate limiting
    ip_address = request.META.get("REMOTE_ADDR")
    if ip_address:
        hour_key = f"contact_hour_{ip_address}"
        day_key = f"contact_day_{ip_address}"
        hour_count = cache.get(hour_key, 0)
        day_count = cache.get(day_key, 0)

        if hour_count >= CONTACT_RATE_LIMIT_HOUR or day_count >= CONTACT_RATE_LIMIT_DAY:
            messages.error(request, "You have submitted this form too frequently. Please try again later.")
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
            # Increment rate limit counters
            if ip_address:
                cache.set(hour_key, hour_count + 1, CONTACT_RATE_WINDOW_HOUR)
                cache.set(day_key, day_count + 1, CONTACT_RATE_WINDOW_DAY)
            return redirect("website:contact")
        else:
            # Add non-field errors to messages framework
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)
    else:
        form = ContactInquiryForm()

    context = base_context("website:contact")
    context.update(
        {
            "page_content": get_page_content(PageContent.CONTACT),
            "form": form,
        }
    )
    return render(request, "website/contact.html", context)