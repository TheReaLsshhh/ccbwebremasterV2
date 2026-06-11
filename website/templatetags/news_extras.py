from django import template
from urllib.parse import urlencode, urlparse

from django.core import signing
from django.urls import NoReverseMatch, reverse

register = template.Library()

IMAGE_EXTENSIONS = frozenset(
    {"jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "avif", "ico", "tif", "tiff"}
)
DOCUMENT_EXTENSIONS = frozenset(
    {"pdf", "doc", "docx", "xls", "xlsx", "csv", "txt", "zip", "rar", "ppt", "pptx"}
)


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
