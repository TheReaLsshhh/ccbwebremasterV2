from django import template
import unicodedata
from urllib.parse import urlencode, urlparse

from django.templatetags.static import static
from django.core import signing
from django.urls import NoReverseMatch, reverse

register = template.Library()

IMAGE_EXTENSIONS = frozenset(
    {"jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "avif", "ico", "tif", "tiff"}
)
DOCUMENT_EXTENSIONS = frozenset(
    {"pdf", "doc", "docx", "xls", "xlsx", "csv", "txt", "zip", "rar", "ppt", "pptx"}
)
IMAGE_TRANSFORM_DEFAULTS = "f_auto,q_auto:good,c_limit"


@register.filter
def exceeds_word_limit(value, limit):
    if not value:
        return False
    return len(value.split()) > int(limit)


@register.filter
def words_truncate(value, limit):
    if not value:
        return ""
    words = value.split()
    limit = int(limit)
    if len(words) <= limit:
        return value
    return " ".join(words[:limit])


@register.filter
def file_download_url(file_field):
    """Return a working Cloudinary download URL for stored media files.

    Document files (PDF, Word, Excel, etc.) are stored via RawMediaCloudinaryStorage
    and served from /raw/upload/ — do not rewrite those URLs.
    Image files are served from /image/upload/ — also leave those alone.
    """
    if not file_field:
        return ""

    try:
        url = file_field.url
    except Exception:
        return ""

    if not url:
        return ""

    # If it's not a Cloudinary URL, return as-is (local filesystem).
    if "res.cloudinary.com" not in url:
        return url

    path = urlparse(url).path.lower()
    extension = path.rsplit(".", 1)[-1] if "." in path else ""

    if extension in DOCUMENT_EXTENSIONS:
        try:
            signed_url = signing.Signer(salt="website.download").sign(url)
            return f"{reverse('website:cloudinary_download')}?{urlencode({'u': signed_url})}"
        except NoReverseMatch:
            return url

    return url


def _file_url(file_field):
    if not file_field:
        return ""
    if isinstance(file_field, str):
        return file_field

    try:
        return file_field.url
    except Exception:
        return ""


def _cloudinary_transform_url(url, width):
    if not url or "res.cloudinary.com" not in url or "/image/upload/" not in url:
        return url

    try:
        width = int(width)
    except (TypeError, ValueError):
        return url

    if width <= 0:
        return url

    transform = f"{IMAGE_TRANSFORM_DEFAULTS},w_{width}"
    return url.replace("/image/upload/", f"/image/upload/{transform}/", 1)


@register.filter
def optimized_image_url(file_field, width):
    return _cloudinary_transform_url(_file_url(file_field), width)


@register.filter
def optimized_image_srcset(file_field, widths):
    url = _file_url(file_field)
    if not url:
        return ""

    srcset = []
    for width in str(widths).split(","):
        width = width.strip()
        if not width:
            continue
        srcset.append(f"{_cloudinary_transform_url(url, width)} {width}w")
    return ", ".join(srcset)


@register.filter
def plain_text(value):
    """Display pasted mathematical/bold Unicode letters in the site's fonts."""
    return unicodedata.normalize("NFKC", str(value or ""))


@register.filter
def webp_image_url(file_field, width):
    try:
        width = min(2400, max(160, int(width)))
    except (ValueError, TypeError):
        return ""
    url = _file_url(file_field)
    if "res.cloudinary.com/" in url and "/image/upload/" in url:
        return url.replace("/image/upload/", f"/image/upload/f_webp,q_90,c_limit,w_{width}/", 1)
    if not file_field or isinstance(file_field, str):
        return ""
    from website.image_variants import local_webp_url
    return local_webp_url(file_field, width)


@register.inclusion_tag("website/includes/responsive_image.html")
def responsive_image(image, alt="", width=960, widths="480,960,1600", sizes="100vw", css_class="", loading="lazy", priority="auto", picture_class=""):
    variants = []
    for size in str(widths).split(","):
        size = size.strip()
        if not size.isdigit() or not 160 <= int(size) <= 2400:
            continue
        url = webp_image_url(image, int(size))
        if url:
            variants.append(f"{url} {size}w")
    return {
        "image_url": optimized_image_url(image, width),
        "image_srcset": optimized_image_srcset(image, widths) if "res.cloudinary.com/" in _file_url(image) else "",
        "webp_srcset": ", ".join(variants), "sizes": sizes,
        "image_alt": plain_text(alt), "css_class": css_class,
        "loading": loading, "priority": priority, "picture_class": picture_class,
    }


@register.filter
def webp_image_srcset(image, widths):
    variants = []
    for size in str(widths).split(","):
        size = size.strip()
        if size.isdigit() and 160 <= int(size) <= 2400:
            url = webp_image_url(image, size)
            if url:
                variants.append(f"{url} {size}w")
    return ", ".join(variants)
