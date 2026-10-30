import logging
import re
from urllib.parse import urlparse, urlencode

import requests
from django.conf import settings
from django.contrib import messages
from django.core import signing
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.utils.cache import patch_cache_control
from django.utils import timezone
from django.urls import reverse
from django.utils.html import escape
from django.utils.html import format_html
from django.views.decorators.cache import never_cache

from .forms import ContactInquiryForm
from .models import (
    AdmissionStep,
    CampusService,
    CampusOffice,
    AcademicProgram,
    HomeSlide,
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


logger = logging.getLogger(__name__)

NEWS_PAGE_SIZE = 6
CLOUDINARY_DOWNLOAD_TIMEOUT = 4
PUBLIC_PAGE_CACHE_SECONDS = 300
PUBLIC_PAGE_STALE_SECONDS = 0


def render_public(request, template_name, context):
    response = render(request, template_name, context)
    patch_cache_control(
        response,
        public=True,
        max_age=PUBLIC_PAGE_CACHE_SECONDS,
        stale_while_revalidate=PUBLIC_PAGE_STALE_SECONDS,
    )
    return response


def service_worker(request):
    admin_path = f"/{settings.ADMIN_URL}"
    precache_urls = [
        static("css/site.css"),
        static("css/institutional.css"),
        static("js/college-motion.js"),
        static("js/news-modal.js"),
        static("js/ajax-refresh.js"),
        static("images/hero-images/ccb-logo-64.png"),
    ]
    precache_list = ",\n  ".join(f"{url!r}" for url in precache_urls)
    script = f"""
const CACHE_VERSION = "ccb-public-v11";
const PAGE_CACHE = `${{CACHE_VERSION}}-pages`;
const ASSET_CACHE = `${{CACHE_VERSION}}-assets`;
const PRECACHE_URLS = [
  {precache_list}
];
const ADMIN_PATH = {admin_path!r};
const NEVER_CACHE_PATHS = [
  ADMIN_PATH,
  "/admin/",
  "/contact/",
  "/download/",
  "/sw.js"
];

self.addEventListener("install", (event) => {{
  event.waitUntil(
    caches.open(ASSET_CACHE)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
}});

self.addEventListener("activate", (event) => {{
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => ![PAGE_CACHE, ASSET_CACHE].includes(key))
          .map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
}});

function isSafeGetRequest(request) {{
  return request.method === "GET" && new URL(request.url).origin === self.location.origin;
}}

function shouldBypassCache(request) {{
  const url = new URL(request.url);
  return NEVER_CACHE_PATHS.some((path) => url.pathname.startsWith(path));
}}

async function cacheFirst(request) {{
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {{
    return cachedResponse;
  }}
  const networkResponse = await fetch(request);
  if (networkResponse.ok) {{
    const cache = await caches.open(ASSET_CACHE);
    cache.put(request, networkResponse.clone());
  }}
  return networkResponse;
}}

async function networkFirst(request) {{
  const cache = await caches.open(PAGE_CACHE);
  try {{
    const response = await fetch(request);
    if (response.ok) await cache.put(request, response.clone());
    else await cache.delete(request);
    return response;
  }} catch (error) {{
    return (await cache.match(request)) || new Response("You are offline. Please reconnect to view this page.", {{ status: 503, headers: {{ "Content-Type": "text/plain" }} }});
  }}
}}

self.addEventListener("fetch", (event) => {{
  const request = event.request;
  if (!isSafeGetRequest(request) || shouldBypassCache(request)) {{
    return;
  }}

  if (request.destination === "document") {{
    event.respondWith(networkFirst(request));
    return;
  }}

  if (["style", "script", "image", "font"].includes(request.destination)) {{
    event.respondWith(cacheFirst(request));
  }}
}});
""".strip()
    response = HttpResponse(script, content_type="application/javascript; charset=utf-8")
    patch_cache_control(response, no_cache=True, must_revalidate=True, max_age=0)
    return response


def _news_page_by_id(per_page=NEWS_PAGE_SIZE):
    # Compute from the visible records so publishing and scheduled releases cannot
    # leave deep links pointing at a page from an outdated cached index.
    news_ids = NewsEvent.objects.filter(published=True, published_at__lte=timezone.now()).order_by("-published_at", "-pk").values_list("pk", flat=True)
    return {pk: (index // per_page) + 1 for index, pk in enumerate(news_ids)}


def _cloudinary_download_candidates(url):
    candidates = [url]
    if "/raw/upload/" in url:
        candidates.append(url.replace("/raw/upload/", "/image/upload/", 1))
    elif "/image/upload/" in url:
        candidates.insert(0, url.replace("/image/upload/", "/raw/upload/", 1))

    deduped_candidates = []
    for candidate in candidates:
        if candidate not in deduped_candidates:
            deduped_candidates.append(candidate)
    return deduped_candidates


def _cloudinary_url_is_available(url):
    try:
        response = requests.head(
            url,
            allow_redirects=True,
            timeout=CLOUDINARY_DOWNLOAD_TIMEOUT,
        )
        if response.status_code == 405:
            response = requests.get(
                url,
                allow_redirects=True,
                stream=True,
                timeout=CLOUDINARY_DOWNLOAD_TIMEOUT,
            )
        is_available = response.status_code < 400
        response.close()
        return is_available
    except requests.RequestException:
        return False


@never_cache
def cloudinary_download(request):
    signed_url = request.GET.get("u", "")
    try:
        url = signing.Signer(salt="website.download").unsign(signed_url)
    except signing.BadSignature:
        return HttpResponseBadRequest("Invalid download link.")

    parsed_url = urlparse(url)
    if parsed_url.scheme != "https" or parsed_url.netloc != "res.cloudinary.com":
        return HttpResponseBadRequest("Invalid download host.")

    candidates = _cloudinary_download_candidates(url)
    for candidate in candidates:
        if _cloudinary_url_is_available(candidate):
            return redirect(candidate)

    return HttpResponseNotFound(
        "This download file is unavailable. Please reupload it in the admin dashboard."
    )


def get_contact_recipient_display_name():
    default_from = getattr(settings, "DEFAULT_FROM_EMAIL", "") or ""
    match = re.match(r'\s*"?\s*(.+?)\s*"?\s*<[^>]+>\s*$', default_from)
    if match:
        return match.group(1).strip()
    return "City College of Bayawan"


def send_contact_notification_email(inquiry):
    if not getattr(settings, "BREVO_API_KEY", ""):
        logger.error("Contact notification email skipped because BREVO_API_KEY is not configured.")
        return False

    try:
        recipient = settings.CONTACT_INQUIRY_RECIPIENT
        safe_name = escape(inquiry.name)
        safe_email = escape(inquiry.email)
        safe_subject = escape(inquiry.subject)
        safe_message = escape(inquiry.message)
        text_message = (
            "A website visitor submitted an inquiry via the contact form.\n\n"
            f"Name: {inquiry.name}\n"
            f"Email: {inquiry.email}\n"
            f"Subject: {inquiry.subject}\n\n"
            f"Message:\n{inquiry.message}"
        )
        html_message = f"""
            <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #17351d;">
                <p>A website visitor submitted an inquiry via the contact form.</p>
                <p><strong>Name:</strong> {safe_name}<br>
                <strong>Email:</strong> {safe_email}<br>
                <strong>Subject:</strong> {safe_subject}</p>
                <p><strong>Message:</strong></p>
                <div style="padding: 14px 16px; border-radius: 16px; background: #f8f7f3; border: 1px solid rgba(79, 75, 70, 0.12); white-space: pre-line;">{safe_message}</div>
            </div>
        """
        email = EmailMultiAlternatives(
            subject=f"Website inquiry: {inquiry.subject}",
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
            reply_to=[inquiry.email],
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        inquiry.mark_notification_sent()
        return True
    except Exception:
        logger.exception("Failed to send contact notification email for inquiry %s", inquiry.pk)
        return False


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
        "label": "Students Affair & Services",
        "url": "https://www.facebook.com/profile.php?id=61582297621099",
    },
    {
        "label": "Office of the Registrar",
        "url": "https://www.facebook.com/profile.php?id=61583528066100",
    },
]

DEFAULT_PAGE_CONTENT = {
    PageContent.HOME: {
        "hero_title": "A brighter future begins here.",
        "hero_text": "Discover opportunities to learn, grow, and contribute to your community at City College of Bayawan.",
        "body_title": "Welcome to CCB",
        "body_text": "Stay informed through one clear and accessible public portal.",
    },
    PageContent.ACADEMICS: {
        "hero_title": "Academics",
        "hero_text": "Find your path. Explore our academic programs and discover where a CCB education can take you.",
    },
    PageContent.ADMISSIONS: {
        "hero_title": "Admissions",
        "hero_text": "Your next chapter starts here. Find the requirements and guidance to begin your CCB journey.",
    },
    PageContent.STUDENTS: {
        "hero_title": "Student Resources",
        "hero_text": "Find the resources, services, and support to make the most of life at CCB.",
    },
    PageContent.FACULTY: {
        "hero_title": "Faculty & Staff",
        "hero_text": "Meet the educators, leaders, and staff who support our college community.",
    },
    PageContent.ABOUT: {
        "hero_title": "About City College of Bayawan",
        "hero_text": "Rooted in Bayawan. Discover our college, our community, and our commitment to learning.",
        "body_title": "Institutional Profile",
        "body_text": "City College of Bayawan brings learners, educators, and the community together through education.",
    },
    PageContent.CONTACT: {
        "hero_title": "Contact Us",
        "hero_text": "Help students, families, and community partners reach the right office quickly.",
        "body_text": "Have a question about the college? Send us an inquiry or find the contact information you need below.",
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
    if CampusService.objects.exists():
        return [{"label": item.title, "description": item.description, "url": item.url, "is_available": True}
                for item in CampusService.objects.filter(published=True)]
    return [{**item, "is_available": True} for item in SERVICE_DROPDOWN_ITEMS]


def get_page_faqs(active_page):
    page_key = active_page.rsplit(":", 1)[-1]
    return FrequentlyAskedQuestion.objects.only(
        "id",
        "question",
        "answer",
        "layout",
        "sort_order",
        "published",
    ).filter(layout=page_key, published=True).exclude(answer__icontains="lorem ipsum")


def base_context(active_page):
    return {
        "site_settings": get_site_settings(),
        "nav_items": NAV_ITEMS,
        "active_page": active_page,
        "service_menu_items": get_service_dropdown_items(),
        "page_faqs": get_page_faqs(active_page),
    }


HOME_NEWS_CAROUSEL_SIZE = 10


def _home_news_carousel_items(queryset_fields):
    """Build up to ten homepage news slides for the carousel."""
    featured = list(
        NewsEvent.objects.filter(published=True, published_at__lte=timezone.now()).only(*queryset_fields).filter(is_featured=True)[:HOME_NEWS_CAROUSEL_SIZE]
    )
    if len(featured) < HOME_NEWS_CAROUSEL_SIZE:
        existing_ids = {item.pk for item in featured}
        extras = list(
            NewsEvent.objects.filter(published=True, published_at__lte=timezone.now()).only(*queryset_fields)
            .exclude(pk__in=existing_ids)
            .order_by("-published_at")[: HOME_NEWS_CAROUSEL_SIZE - len(featured)]
        )
        featured.extend(extras)

    featured = featured[:HOME_NEWS_CAROUSEL_SIZE]
    if not featured:
        return []

    news_page_by_id = _news_page_by_id()
    for item in featured:
        item.news_page = news_page_by_id.get(item.pk, 1)

    return featured


def home(request):
    news_fields = ("title", "summary", "content", "event_date", "location", "cover_image", "attachment", "published_at")
    home_news_items = _home_news_carousel_items(news_fields)

    hero_slides = [{"image": slide.image} for slide in HomeSlide.objects.filter(published=True)]
    # Use only staff-selected banners when any are published.
    if not hero_slides:
        filenames = ("ccb.jpg",) if HomeSlide.objects.exists() else ("ccb.jpg", "bg2.jpg")
        hero_slides = [{"url": static(f"images/{filename}")} for filename in filenames]

    context = base_context("website:home")
    context.update(
        {
            "page_content": get_page_content(PageContent.HOME),
            "featured_programs": AcademicProgram.objects.filter(published=True).order_by("-is_featured", "name")[:3],
            "home_news_items": home_news_items,
            "home_news_count": len(home_news_items),
            "hero_slides": hero_slides,
        }
    )
    return render_public(request, "website/home.html", context)


def academics(request):
    context = base_context("website:academics")
    context.update(
        {
            "page_content": get_page_content(PageContent.ACADEMICS),
            "programs": search_queryset(_academic_programs(), request, ("name", "award", "description", "department")),
        }
    )
    return render_public(request, "website/academics.html", context)


def _academic_programs():
    return AcademicProgram.objects.filter(published=True).only("name", "award", "description", "brochure_file", "department", "duration")


def academics_partial(request):
    response = render(
        request,
        "website/partials/academic_programs_grid.html",
        {"programs": search_queryset(_academic_programs(), request, ("name", "award", "description", "department"))},
    )
    patch_cache_control(response, public=True, max_age=PUBLIC_PAGE_CACHE_SECONDS)
    return response


def admissions(request):
    context = base_context("website:admissions")
    context.update(
        {
            "page_content": get_page_content(PageContent.ADMISSIONS),
            "requirements": _admission_requirements(),
            "admission_steps": AdmissionStep.objects.filter(published=True),
        }
    )
    return render_public(request, "website/admissions.html", context)


def _admission_requirements():
    return AdmissionRequirement.objects.filter(published=True).only("title", "description", "document_file", "sort_order")


def admissions_partial(request):
    response = render(
        request,
        "website/partials/admission_requirements_grid.html",
        {"requirements": _admission_requirements()},
    )
    patch_cache_control(response, public=True, max_age=PUBLIC_PAGE_CACHE_SECONDS)
    return response


def news(request):
    try:
        news_queryset = NewsEvent.objects.filter(published=True, published_at__lte=timezone.now()).only("title", "summary", "content", "event_date", "location", "cover_image", "attachment", "published_at")
        news_queryset = news_queryset.order_by("-published_at", "-pk")
        news_queryset = search_queryset(news_queryset, request, ("title", "summary", "content", "location"))
        paginator = Paginator(news_queryset, NEWS_PAGE_SIZE)
        news_page_by_id = {pk: (index // NEWS_PAGE_SIZE) + 1 for index, pk in enumerate(news_queryset.values_list("pk", flat=True))}

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
        return render_public(request, "website/news.html", context)
    except Exception:
        logger.exception("Unhandled error in news view")
        raise


def downloads(request):
    page_obj = _downloads_page(request)

    context = base_context("website:downloads")
    context.update(
        {
            "page_content": get_page_content(PageContent.DOWNLOADS),
            # Pass the Page object for pagination controls
            "page_obj": page_obj,
            # Pass the items for the current page
            "downloads": page_obj.object_list,
            "categories": DownloadItem.CATEGORY_CHOICES,
        }
    )
    return render_public(request, "website/downloads.html", context)


def _downloads_page(request):
    download_queryset = DownloadItem.objects.filter(published=True).only("category", "title", "description", "file")
    download_queryset = search_queryset(download_queryset, request, ("title", "description"))
    category = request.GET.get("category", "")
    if category in dict(DownloadItem.CATEGORY_CHOICES):
        download_queryset = download_queryset.filter(category=category)
    paginator = Paginator(download_queryset, 12)
    return paginator.get_page(request.GET.get("page"))


def downloads_partial(request):
    page_obj = _downloads_page(request)
    response = render(
        request,
        "website/partials/downloads_grid.html",
        {
            "page_obj": page_obj,
            "downloads": page_obj.object_list,
            "categories": DownloadItem.CATEGORY_CHOICES,
        },
    )
    patch_cache_control(response, public=True, max_age=PUBLIC_PAGE_CACHE_SECONDS)
    return response


def students(request):
    context = base_context("website:students")
    context.update(
        {
            "page_content": get_page_content(PageContent.STUDENTS),
            "resources": search_queryset(_student_resources(), request, ("title", "description")),
        }
    )
    return render_public(request, "website/students.html", context)


def _student_resources():
    return StudentResource.objects.filter(published=True).only("title", "description", "link_url", "attachment")


def students_partial(request):
    response = render(
        request,
        "website/partials/student_resources_grid.html",
        {"resources": search_queryset(_student_resources(), request, ("title", "description"))},
    )
    patch_cache_control(response, public=True, max_age=PUBLIC_PAGE_CACHE_SECONDS)
    return response


def faculty(request):
    faculty_people = FacultyStaffEntry.objects.filter(published=True).only(
        "name",
        "section",
        "role",
        "department",
        "bio",
        "email",
        "profile_image",
    ).order_by("name")
    faculty_people = search_queryset(faculty_people, request, ("name", "role", "department", "bio"))
    department = request.GET.get("department", "").strip()
    if department:
        faculty_people = faculty_people.filter(department=department)
    faculty_sections = (
        FacultyStaffSection.objects.only("title", "eyebrow_label", "layout", "sort_order")
        .filter(published=True, people__in=faculty_people)
        .distinct()
        .prefetch_related(Prefetch("people", queryset=faculty_people))
    )

    context = base_context("website:faculty")
    context.update(
        {
            "page_content": get_page_content(PageContent.FACULTY),
            "faculty_sections": faculty_sections,
            "departments": FacultyStaffEntry.objects.filter(published=True, section__published=True).exclude(department="").values_list("department", flat=True).distinct().order_by("department"),
        }
    )
    return render_public(request, "website/faculty.html", context)


def about(request):
    context = base_context("website:about")
    about_sections = get_page_contents(PageContent.ABOUT)
    context.update(
        {
            "page_content": about_sections[0],
            "about_sections": about_sections,
        }
    )
    return render_public(request, "website/about.html", context)


CONTACT_RATE_LIMIT_HOUR = 1  # max 1 submission per IP per hour
CONTACT_RATE_WINDOW_HOUR = 3600  # 1 hour in seconds
CONTACT_RATE_LIMIT_DAY = 5  # max 5 submissions per IP per day
CONTACT_RATE_WINDOW_DAY = 86400  # 24 hours in seconds


def _client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


@never_cache
def contact(request):
    context = base_context("website:contact")
    form = ContactInquiryForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        ip = _client_ip(request)
        cache_key_hour = f"contact-submissions-hour:{ip}"
        cache_key_day = f"contact-submissions-day:{ip}"

        attempts_hour = cache.get(cache_key_hour, 0)
        attempts_day = cache.get(cache_key_day, 0)

        if attempts_hour >= CONTACT_RATE_LIMIT_HOUR:
            messages.error(request, "Too many submissions. Please try again in one hour.")
            return redirect("website:contact")
        if attempts_day >= CONTACT_RATE_LIMIT_DAY:
            messages.error(request, "Daily submission limit reached. Please try again tomorrow.")
            return redirect("website:contact")

        cache.set(cache_key_hour, attempts_hour + 1, CONTACT_RATE_WINDOW_HOUR)
        cache.set(cache_key_day, attempts_day + 1, CONTACT_RATE_WINDOW_DAY)

        try:
            inquiry = form.save()
            email_sent = send_contact_notification_email(inquiry)
            if email_sent:
                display_name = get_contact_recipient_display_name()
                safe_display = escape(display_name)
                messages.success(
                    request,
                    format_html(
                        "Your inquiry has been sent to <span class='feedback-recipient-name'>{}</span>. Thank you for reaching out.",
                        safe_display,
                    ),
                    extra_tags="sticky",
                )
            else:
                messages.warning(
                    request,
                    "Your inquiry was received but could not be forwarded by email. Please contact the office directly.",
                )
        except Exception as exc:
            logger.exception("Contact inquiry submission failed")
            exc_str = str(exc).lower()
            if "no such table" in exc_str or "relation" in exc_str or "does not exist" in exc_str or "not-null" in exc_str or "null value" in exc_str:
                error_message = "The inquiry system is not ready yet. Please try again after the site finishes updating."
            else:
                error_message = "Your inquiry could not be sent right now. Please try again later."
            messages.error(request, error_message)

        return redirect("website:contact")

    if request.method == "POST" and not form.is_valid():
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

    context.update({
        "page_content": get_page_content(PageContent.CONTACT),
        "form": form,
        "offices": search_queryset(CampusOffice.objects.filter(published=True), request, ("name", "description", "location")),
        "recaptcha_public_key": getattr(settings, "RECAPTCHA_PUBLIC_KEY", ""),
    })
    return render(request, "website/contact.html", context)


def search_queryset(queryset, request, fields):
    query = request.GET.get("q", "").strip()[:200]
    if query:
        condition = Q()
        for field in fields:
            condition |= Q(**{f"{field}__icontains": query})
        queryset = queryset.filter(condition)
    return queryset


def program_detail(request, pk):
    program = get_object_or_404(AcademicProgram, pk=pk, published=True)
    context = base_context("website:academics")
    context.update({"program": program, "seo_title": f"{program.name} | City College of Bayawan",
                    "seo_description": program.description[:160]})
    return render_public(request, "website/program_detail.html", context)


def search(request):
    context = base_context("website:search")
    query = request.GET.get("q", "").strip()[:200]
    results = []
    if query:
        sources = [
            (AcademicProgram.objects.filter(published=True), ("name", "award", "description", "department"), "Program", "name", "description", "website:program_detail"),
            (NewsEvent.objects.filter(published=True, published_at__lte=timezone.now()), ("title", "summary", "content"), "News", "title", "summary", "website:news_detail"),
            (DownloadItem.objects.filter(published=True), ("title", "description"), "Download", "title", "description", "website:downloads"),
            (StudentResource.objects.filter(published=True), ("title", "description"), "Student resource", "title", "description", "website:students"),
            (FacultyStaffEntry.objects.filter(published=True, section__published=True), ("name", "role", "department"), "Faculty & staff", "name", "role", "website:faculty"),
            (CampusOffice.objects.filter(published=True), ("name", "description", "location"), "Office", "name", "description", "website:contact"),
        ]
        for queryset, fields, label, title_field, description_field, route in sources:
            for obj in search_queryset(queryset.only(title_field, description_field), request, fields):
                if route in {"website:program_detail", "website:news_detail"}:
                    url = reverse(route, args=[obj.pk])
                else:
                    url = reverse(route) + "?" + urlencode({"q": getattr(obj, title_field)})
                results.append({"title": getattr(obj, title_field), "description": getattr(obj, description_field), "label": label, "url": url})
    context.update({"query": query, "page_obj": Paginator(results, 12).get_page(request.GET.get("page")),
                    "seo_title": "Search | City College of Bayawan", "seo_description": "Search CCB academic programs, news, forms, student resources, and campus contacts.", "noindex": True})
    return render_public(request, "website/search.html", context)


def news_detail(request, pk):
    item = get_object_or_404(NewsEvent, pk=pk, published=True, published_at__lte=timezone.now())
    context = base_context("website:news")
    context.update({"item": item, "seo_title": f"{item.title} | City College of Bayawan",
                    "seo_description": item.summary[:160]})
    return render_public(request, "website/news_detail.html", context)
