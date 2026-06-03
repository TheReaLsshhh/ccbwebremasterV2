import re

from django import template
from urllib.parse import urlparse

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
    """Return a working Cloudinary download URL for stored media files."""
    if not file_field:
        return ""

    try:
        url = file_field.url
    except Exception:
        return ""

    if not url or "res.cloudinary.com" not in url:
        return url

    path = urlparse(url).path.lower()
    extension = path.rsplit(".", 1)[-1] if "." in path else ""

    # Older uploads used image delivery even for documents; undo raw rewrites that 404.
    if extension in DOCUMENT_EXTENSIONS and "/raw/upload/" in url:
        url = url.replace("/raw/upload/", "/image/upload/", 1)

    # Placeholder version segments often 404; latest asset is served without them.
    url = re.sub(r"/v1/", "/", url, count=1)

    return url
