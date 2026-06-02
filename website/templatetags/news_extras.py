from django import template
from urllib.parse import urlparse

register = template.Library()


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
    """Return Cloudinary raw URL for non-image file downloads."""
    if not file_field:
        return ""

    try:
        url = file_field.url
    except Exception:
        return ""

    if not url or "res.cloudinary.com" not in url or "/image/upload/" not in url:
        return url

    path = urlparse(url).path.lower()
    extension = path.rsplit(".", 1)[-1] if "." in path else ""
    image_extensions = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "avif"}
    if extension in image_extensions:
        return url

    return url.replace("/image/upload/", "/raw/upload/", 1)
