"""Non-destructive WebP derivatives for locally stored uploads."""
import hashlib
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.conf import settings
from PIL import Image, ImageOps


def local_webp_url(file_field, width):
    try:
        source = Path(file_field.path)
        stat = source.stat()
        key = hashlib.sha256(f"{source}:{stat.st_mtime_ns}:{stat.st_size}:{width}".encode()).hexdigest()[:24]
        relative = f"image-variants/{key}.webp"
        destination = Path(settings.MEDIA_ROOT) / relative
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(source) as original:
                if getattr(original, "is_animated", False):
                    return ""
                image = ImageOps.exif_transpose(original)
                image.thumbnail((width, width * 4), Image.Resampling.LANCZOS)
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                temporary = None
                try:
                    with NamedTemporaryFile(dir=destination.parent, suffix=".webp", delete=False) as handle:
                        temporary = handle.name
                    image.save(temporary, "WEBP", quality=90, method=4)
                    os.replace(temporary, destination)
                finally:
                    if temporary and os.path.exists(temporary):
                        os.unlink(temporary)
        return settings.MEDIA_URL.rstrip("/") + "/" + relative
    except (AttributeError, OSError, ValueError, NotImplementedError):
        return ""
